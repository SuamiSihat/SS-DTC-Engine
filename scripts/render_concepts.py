#!/usr/bin/env python3
"""Concept product photos: the real product, a generated scene (AWS Bedrock), nothing else changed.

Usage:
  python scripts/render_concepts.py batches/<batch>/concept_spec.json [--only 36,57] [--res 2k|4k]
         [--engine nova|stability|mock] [--benchmark [N]] [--dry-run] [--force] [--skip-small] [--workers N]
Spec:    skills/product-concept-photo/references/spec-format.md
Prompts: skills/product-concept-photo/references/prompt-library.json (ids 1-60, 15 categories x 4)

Product integrity (the point of this script):
  1. Cut-out = original RGB pixels + an alpha mask (rembg). The RGB is never edited.
  2. The product is placed once, scaled down evenly (never up, never stretched or rotated).
  3. The engine generates the scene around it (Nova Canvas OUTPAINTING/PRECISE or Stability Inpaint).
  4. 4K: the 2K result is upscaled (Stability Conservative Upscale) and resized to the exact 4K size.
  5. Scene-only grade (film looks), then the ORIGINAL product pixels are pasted back on top.
  6. Every fully opaque product pixel is compared with the source; any difference = REJECT.

Sizes  2k: 16:9 2048x1152, 9:16 1152x2048, 4:5 1600x2000, 1:1 2032x2032 (Nova limit < 4.19 MP)
       4k: 16:9 3840x2160, 9:16 2160x3840, 4:5 3072x3840, 1:1 3072x3072 (scene made at 2K, then upscaled)
Writes batches/<batch>/renders/concepts/: <NAME>_<aspect>.png masters, delivery/<NAME>_<aspect>.jpg (Meta sizes),
       concept_index.csv, review_sheet_NN.jpg, review_notes.md. Work files in batches/<batch>/work/concepts/.
Auth (config.env, never in git): AWS_BEARER_TOKEN_BEDROCK (Bedrock API key) or an AWS profile via boto3.
`--engine mock` makes a fake scene with no API call (for testing the pipeline).
"""
import argparse, base64, csv, io, json, os, pathlib, random, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT / "skills" / "product-concept-photo" / "references" / "prompt-library.json"
PREFIX = {"drmitring": "DMR", "menss": "MNS", "mensculine": "MSC", "rejal": "RJL", "ssclinic": "SSC", "pertabi": "PTB"}
SIZES = {"2k": {"16:9": (2048, 1152), "9:16": (1152, 2048), "4:5": (1600, 2000), "1:1": (2032, 2032)},
         "4k": {"16:9": (3840, 2160), "9:16": (2160, 3840), "4:5": (3072, 3840), "1:1": (3072, 3072)}}
DELIVERY = {"16:9": (1920, 1080), "9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080)}
CODE = {"16:9": "16x9", "9:16": "9x16", "4:5": "4x5", "1:1": "1x1"}
STORY_TOP, STORY_BOTTOM = 250 / 1920, 340 / 1920      # Stories/Reels UI, fraction of height
ANGLES = {"front": "eye-level straight-on camera view", "three-quarter": "eye-level three-quarter camera view",
          "top-down": "camera directly overhead looking straight down", "low": "slightly low camera angle looking up",
          "unboxing": "eye-level camera view"}
DEFAULT_MODELS = {"nova": "amazon.nova-canvas-v1:0", "stability": "us.stability.stable-image-inpaint-v1:0",
                  "upscale": "us.stability.stable-conservative-upscale-v1:0"}
KEEP_ALPHA = 200          # alpha >= this is "product" for the engine mask
FONT_DIRS = [r"C:\Windows\Fonts", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"), "/usr/share/fonts/truetype/poppins"]
PRINT_LOCK = threading.Lock()
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def say(*a):
    with PRINT_LOCK:
        print(*a, flush=True)


def read_env():
    env = {}
    p = ROOT / "config.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith(("AWS_", "IMAGE_", "COST_", "NOVA_", "STABILITY_", "UPSCALE_"))})
    return env


def cost(env, key):
    v = env.get(key, "")
    try:
        return float(v)
    except ValueError:
        return None


class SafeDict(dict):
    def __missing__(self, k):
        return "{" + k + "}"


# ---------- Bedrock ----------
class BedrockError(Exception):
    def __init__(self, code, msg):
        super().__init__(f"{code}: {msg}"); self.code, self.msg = code, msg


class Bedrock:
    """InvokeModel over HTTPS with a Bedrock API key (AWS_BEARER_TOKEN_BEDROCK), or boto3 with an AWS profile."""
    def __init__(self, env):
        self.region = env.get("AWS_REGION") or "us-east-1"
        tok = env.get("AWS_BEARER_TOKEN_BEDROCK", "")
        self.token = "" if (not tok or tok.startswith("PASTE")) else tok
        self.client = None
        if not self.token:
            try:
                import boto3
                from botocore.config import Config
                prof = env.get("AWS_PROFILE") or None
                sess = boto3.Session(profile_name=prof) if prof else boto3.Session()
                self.client = sess.client("bedrock-runtime", region_name=self.region,
                                          config=Config(read_timeout=300, connect_timeout=30, retries={"max_attempts": 1}))
            except ImportError:
                sys.exit("No Bedrock credentials: set AWS_BEARER_TOKEN_BEDROCK in config.env, or pip install boto3 and set AWS_PROFILE.")

    def _once(self, model_id, body):
        data = json.dumps(body).encode("utf-8")
        if self.token:
            url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{urllib.parse.quote(model_id, safe='')}/invoke"
            req = urllib.request.Request(url, data=data, method="POST", headers={
                "Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {self.token}"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                raise BedrockError(e.code, e.read().decode("utf-8", "replace")[:400])
        from botocore.exceptions import ClientError
        try:
            r = self.client.invoke_model(modelId=model_id, body=data, contentType="application/json", accept="application/json")
            return json.loads(r["body"].read())
        except ClientError as e:
            err = e.response.get("Error", {})
            code = 429 if err.get("Code") in ("ThrottlingException", "ServiceQuotaExceededException") else \
                e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 400)
            raise BedrockError(code, f"{err.get('Code')}: {err.get('Message', '')[:400]}")

    def invoke(self, model_id, body):
        for attempt in range(6):
            try:
                return self._once(model_id, body)
            except BedrockError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(min(60, 4 * 2 ** attempt)); continue
                raise
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 2:
                    time.sleep(10); continue
                raise BedrockError("network", str(e))


def b64png(img):
    buf = io.BytesIO(); img.save(buf, "PNG"); return base64.b64encode(buf.getvalue()).decode("ascii")


def unb64(s):
    return Image.open(io.BytesIO(base64.b64decode(s))).convert("RGB")


# ---------- engines: return (scene RGB image or None, reason) ----------
def engine_nova(bed, models, canvas, keep, prompt, negative, seed, cfg_scale):
    mask = Image.fromarray(np.where(keep, 0, 255).astype(np.uint8)).convert("RGB")   # black = keep, white = generate
    body = {"taskType": "OUTPAINTING",
            "outPaintingParams": {"image": b64png(canvas), "maskImage": b64png(mask), "outPaintingMode": "PRECISE",
                                  "text": prompt, "negativeText": negative},
            "imageGenerationConfig": {"numberOfImages": 1, "quality": "premium", "cfgScale": cfg_scale, "seed": seed % 2147483646}}
    r = bed.invoke(models["nova"], body)
    if r.get("error") or not r.get("images"):
        return None, f"filtered: {r.get('error') or 'no image returned'}"
    return unb64(r["images"][0]), ""


def engine_stability(bed, models, canvas, keep, prompt, negative, seed, cfg_scale):
    mask = Image.fromarray(np.where(keep, 0, 255).astype(np.uint8))                 # white = inpaint, black = keep
    body = {"prompt": prompt, "negative_prompt": negative, "image": b64png(canvas), "mask": b64png(mask),
            "seed": seed % 4294967294, "output_format": "png", "style_preset": "photographic", "grow_mask": 3}
    r = bed.invoke(models["stability"], body)
    fr = (r.get("finish_reasons") or [None])[0]
    if fr or not r.get("images"):
        return None, f"filtered: {fr or 'no image returned'}"
    return unb64(r["images"][0]), ""


def engine_mock(bed, models, canvas, keep, prompt, negative, seed, cfg_scale):
    """Fake scene: gradient + noise, and it deliberately tints the product too, so the paste-back is tested."""
    rng = np.random.default_rng(seed)
    W, H = canvas.size
    c1, c2 = rng.integers(40, 220, 3), rng.integers(40, 220, 3)
    t = np.linspace(0, 1, H)[:, None, None]
    g = (c1 * (1 - t) + c2 * t) * np.ones((1, W, 1)) + rng.normal(0, 6, (H, W, 3))
    out = np.where(keep[..., None], np.asarray(canvas, dtype=float) * 0.9 + 12, g)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), ""


ENGINES = {"nova": engine_nova, "stability": engine_stability, "mock": engine_mock}


def upscale(bed, models, img, prompt, negative, seed, target, mock=False):
    """Stability Conservative Upscale, then an exact resize to the 4K target. Returns (image, note)."""
    note = ""
    if mock:
        out = img.resize(target, Image.LANCZOS)
        return out, "mock upscale"
    src = img
    for attempt in (0, 1):
        body = {"image": b64png(src), "prompt": prompt[:2000], "negative_prompt": negative, "creativity": 0.2,
                "seed": seed % 4294967294, "output_format": "png"}
        try:
            r = bed.invoke(models["upscale"], body)
            break
        except BedrockError as e:
            if attempt == 0 and e.code == 400 and src.width * src.height > 1_048_576:
                f = (1_048_576 / (src.width * src.height)) ** 0.5
                src = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
                note = f"upscale input reduced to {src.width}x{src.height} (API size limit)"
                continue
            raise
    fr = (r.get("finish_reasons") or [None])[0]
    if fr or not r.get("images"):
        raise BedrockError("filtered", f"upscale {fr or 'no image'}")
    up = unb64(r["images"][0])
    if up.width < target[0] or up.height < target[1]:
        note = (note + "; " if note else "") + f"upscaler returned {up.width}x{up.height}, scene resized up to target"
    return up.resize(target, Image.LANCZOS), note


# ---------- cut-outs (alpha only; RGB untouched) ----------
_SESSION = {}

def cutout(src, dst, model):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return Image.open(dst).convert("RGBA")
    img = ImageOps.exif_transpose(Image.open(src))
    if img.mode in ("RGBA", "LA") and np.asarray(img.getchannel("A")).min() < 250:
        rgba = img.convert("RGBA")                         # already a cut-out
    else:
        rgb = img.convert("RGB")
        from rembg import new_session, remove
        if model not in _SESSION:
            _SESSION[model] = new_session(model)
        probe = rgb
        if max(rgb.size) > 2048:                           # mask on a smaller copy (memory), mask scaled back up
            f = 2048 / max(rgb.size)
            probe = rgb.resize((round(rgb.width * f), round(rgb.height * f)), Image.LANCZOS)
        mask = remove(probe, session=_SESSION[model], only_mask=True).convert("L")
        if mask.size != rgb.size:
            mask = mask.resize(rgb.size, Image.LANCZOS)
        rgba = rgb.copy(); rgba.putalpha(mask)
    a = np.asarray(rgba.getchannel("A"))
    ys, xs = np.where(a > 8)
    if not len(xs):
        sys.exit(f"BLOCK cut-out of {src.name} is empty (no product found)")
    rgba = rgba.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    dst.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(dst)
    return rgba


# ---------- layout ----------
def pick_source(item, sources, angle):
    ok = lambda k: k in sources and (angle is None or sources[k].get("angle") == angle)
    for k in item["src"]:
        if k == "*":
            for kk in sources:
                if ok(kk):
                    return kk
        elif ok(k):
            return k
    return None


def layout(items, cut, W, H):
    """items: [{key, cx, by, h, wmax}] -> boxes on a W x H canvas, scale relative to the cut-out's own pixels."""
    boxes = []
    for it in items:
        c = cut[it["key"]]
        s = min(it["h"] * H / c.height, it.get("wmax", 0.8) * W / c.width)
        w, h = max(1, round(c.width * s)), max(1, round(c.height * s))
        boxes.append({"key": it["key"], "scale": s, "w": w, "h": h,
                      "x": round(it["cx"] * W - w / 2), "y": round(it["by"] * H - h)})
    return boxes


def map_boxes(boxes, f):
    """Same placement on a canvas f times smaller (exact aspect, so one factor)."""
    out = []
    for b in boxes:
        w, h = max(1, round(b["w"] / f)), max(1, round(b["h"] / f))
        out.append(dict(b, scale=b["scale"] / f, w=w, h=h, x=round(b["x"] / f), y=round(b["y"] / f)))
    return out


def product_layer(boxes, cut, W, H):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for b in boxes:
        c = cut[b["key"]]
        if (b["w"], b["h"]) != c.size:
            c = c.convert("RGBa").resize((b["w"], b["h"]), Image.LANCZOS).convert("RGBA")   # premultiplied: no edge halo
        one = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        one.paste(c, (b["x"], b["y"]))
        layer = Image.alpha_composite(layer, one)
    return layer


def contact_shadow(scene, boxes, strength=0.28):
    W, H = scene.size
    sh = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sh)
    for b in boxes:
        cx, by = b["x"] + b["w"] / 2, b["y"] + b["h"]
        rw, rh = b["w"] * 0.42, max(4, b["h"] * 0.035)
        d.ellipse((cx - rw, by - rh, cx + rw, by + rh), fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(max(4, H * 0.012)))
    arr = np.asarray(scene, dtype=float) * (1 - strength * np.asarray(sh, dtype=float)[..., None] / 255)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def plain_bg(kind, W, H):
    if kind == "white":
        return Image.new("RGB", (W, H), (255, 255, 255))
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H / 2)) ** 2).clip(0, 1.4) / 1.4
    lo = 236 if kind == "radial" else 200
    v = 255 - (255 - lo) * r ** 1.6
    return Image.fromarray(np.repeat(v[..., None], 3, 2).astype(np.uint8))


# ---------- scene-only grades ----------
def vignette(arr, amount):
    H, W = arr.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.414
    return arr * (1 - amount * r[..., None] ** 2)


def grade(img, kind, seed):
    if not kind:
        return img
    rng = np.random.default_rng(seed)
    a = np.asarray(img, dtype=float)
    lum = a @ [0.299, 0.587, 0.114]
    if kind == "film35":
        a = lum[..., None] + (a - lum[..., None]) * 0.78
        a = a * 0.9 + 14 + np.array([7, 2, -6])
        a = vignette(a, 0.25) + rng.normal(0, 7, a.shape[:2])[..., None]
    elif kind == "polaroid":
        a = lum[..., None] + (a - lum[..., None]) * 0.85
        a = a * 0.82 + 34 + np.array([10, 5, -12])
        a = vignette(a, 0.35) + rng.normal(0, 3, a.shape[:2])[..., None]
    elif kind == "bw":
        x = lum / 255
        x = x + 0.18 * (x - 0.5) * (1 - abs(2 * x - 1))     # gentle S-curve
        a = np.repeat((x * 255)[..., None], 3, 2) + rng.normal(0, 4, a.shape[:2])[..., None]
    elif kind == "vhs":
        s = max(2, a.shape[1] // 480)
        a[..., 0] = np.roll(a[..., 0], s, 1); a[..., 2] = np.roll(a[..., 2], -s, 1)
        a = a * 0.88 + 18
        a[::3] *= 0.92
        a = a + rng.normal(0, 5, a.shape[:2])[..., None]
    else:
        raise SystemExit(f"unknown grade '{kind}'")
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


# ---------- prompts ----------
def trim(text, n=1024):
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(",", 1)[0]
    return cut


def compose(p, spec, slug, src_meta, lib):
    ov = spec.get("overrides", {}).get(str(p["id"]), {})
    scene = ov.get("scene") or p.get("overrides", {}).get(slug) or p["scene"]
    light = src_meta.get("light") or spec.get("light") or "soft even studio light"
    scene = scene.format_map(SafeDict(product=spec["product"], palette=spec.get("palette_hint") or "soft neutral tones",
                                      props=spec.get("props", ""), light=light))
    parts = [scene]
    if ov.get("extra"):
        parts.append(ov["extra"])
    parts += [ANGLES.get(src_meta.get("angle"), "eye-level camera view"), f"light on the product: {light}",
              "photorealistic commercial photograph, true-to-life scale, physically correct contact shadows and reflections"]
    text = ". ".join(x.strip().rstrip(".") for x in parts if x)
    neg = lib["negative_hands"] if p.get("hands") else lib["negative_base"]
    extra = ", ".join(x for x in (lib.get("brand_negative", {}).get(slug), spec.get("negative_extra")) if x)
    return text, trim(neg + (", " + extra if extra else ""))


# ---------- gate ----------
def check_brand(slug, texts, tf):
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return []
    tf.parent.mkdir(parents=True, exist_ok=True)
    tf.write_text("\n".join(texts), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_brand.py"), "--brand", slug, "--texts", str(tf), "--json"],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return [(x["level"], x["msg"]) for x in json.loads(r.stdout)]
    except Exception:
        return [("BLOCK", f"check_brand.py failed: {(r.stdout + r.stderr).strip()[:300]}")]


def gate(spec, slug, work):
    blocks, reviews, info = [], [], []
    if str(spec.get("ai_imagery", "")).lower() != "approved":
        blocks.append("Spec must set \"ai_imagery\": \"approved\" (from the brief, with a budget).")
    prod = (spec.get("product") or "").strip()
    if not prod:
        blocks.append("Spec needs \"product\": a neutral description (shape, colour, material, real size; no claims).")
    elif len(prod) > 300:
        blocks.append("Keep \"product\" under 300 characters (Bedrock prompt limit is 1024).")
    ovs = spec.get("overrides", {}).values()
    texts = [prod, spec.get("palette_hint", ""), spec.get("props", ""), spec.get("light", "")]
    texts += [o.get(k, "") for o in ovs for k in ("scene", "extra")]
    for lvl, msg in check_brand(slug, texts, work / "concept_texts.txt"):
        if lvl == "BLOCK" and "not an advertisable" in msg:
            reviews.append(f"{msg} Concept photos allowed (2026-11-16); use for partner/community material only.")
        elif lvl == "BLOCK":
            blocks.append(msg)
        elif lvl == "REVIEW":
            reviews.append(msg)
        else:
            info.append(msg)
    pack = spec.get("pack_text") or []
    if not pack:
        reviews.append("pack_text is empty: read the text printed on the real pack and list it in the spec (the gate cannot see pack text).")
    for lvl, msg in check_brand(slug, pack, work / "concept_pack_text.txt"):
        if lvl in ("BLOCK", "REVIEW") and " in: " in msg:
            reviews.append(f"PACK TEXT ({lvl} if typed as copy) printed on the real product: {msg}. A person decides if this pack can run.")
    reviews.append("Every image is a real product in an AI-generated scene (ai_scene=yes). Never present it as a real customer, "
                   "result or proof. Check whether Meta requires the 'AI info' label for the placement.")
    if slug == "ssclinic":
        reviews.append("SS Clinic: only a physical item named in the brief; no doctor, treatment or clinic claim in the scene.")
    return blocks, reviews, info


# ---------- plan ----------
def select_ids(spec, lib, only):
    all_ids = [p["id"] for p in lib["prompts"]]
    if only:
        ids = {int(x) for x in str(only).split(",") if x.strip()}
    else:
        ids = set()
        if spec.get("preset"):
            if spec["preset"] not in lib["presets"]:
                sys.exit(f"unknown preset '{spec['preset']}' (have: {', '.join(lib['presets'])})")
            ids |= set(lib["presets"][spec["preset"]])
        pr = spec.get("prompts")
        if pr == "all":
            ids |= set(all_ids)
        elif isinstance(pr, list):
            ids |= set(pr)
        ids |= {p["id"] for p in lib["prompts"] if p["cat"] in spec.get("categories", [])}
        ids = ids or set(all_ids)
    bad = sorted(ids - set(all_ids))
    if bad:
        sys.exit(f"unknown prompt id(s): {bad}")
    return sorted(ids)


def build_plan(spec, lib, slug, sources, cut, res, only):
    """sources: {key: {file, angle, light}}; cut: {key: RGBA cut-out}. Returns shots and the reasons others were left out."""
    by_id = {p["id"]: p for p in lib["prompts"]}
    shots, skipped, small, warns, errors = [], [], [], [], []
    base_seed = int(spec.get("seed", 1000))
    for i in select_ids(spec, lib, only):
        p = by_id[i]
        ov = spec.get("overrides", {}).get(str(i), {})
        name = f"{PREFIX.get(slug, slug[:3].upper())}-C{p['cat']:02d}-{i:02d}"
        aspect = ov.get("aspect") or p.get("aspect") or lib["categories"][str(p["cat"])]["aspect"]
        if aspect not in CODE:
            errors.append(f"{name}: aspect '{aspect}' not supported ({', '.join(CODE)})"); continue
        place = ov.get("place") or p["place"]
        items = lib["placements"][place] if isinstance(place, str) else place
        angle = ov.get("angle", p.get("angle"))
        reason = None
        for n in p.get("needs", []):
            if n == "props" and not spec.get("props"):
                reason = "needs 'props' in the spec (only ingredients/items from brand.json product_facts)"
            elif n.startswith("src:") and n[4:] not in sources:
                reason = f"needs a real '{n[4:]}' source photo"
        placed = []
        for it in items:
            k = pick_source(it, sources, angle)
            if k:
                placed.append(dict(it, key=k))
        if not reason and len(placed) < p.get("min_items", 1):
            want = f"'{angle}' " if angle else ""
            reason = f"needs {p.get('min_items', 1)} {want}source photo(s) matching {[it['src'] for it in items]}"
        if not reason and p.get("min_source_px"):
            px = max(max(cut[it["key"]].size) for it in placed)
            if px < p["min_source_px"]:
                reason = f"needs a source cut-out of at least {p['min_source_px']} px (largest is {px} px)"
        if reason:
            skipped.append(f"{name} (#{i} {p['title']}): {reason}"); continue
        W, H = SIZES[res][aspect]
        boxes = layout(placed, cut, W, H)
        for b in boxes:
            if b["scale"] > 1.0001:
                need = round(cut[b["key"]].height * b["scale"])
                small.append(f"{name}: source '{b['key']}' is {cut[b['key']].height} px tall, needs {need} px at {res} "
                             f"({b['scale']:.2f}x). Supply a larger photo{', use --res 2k' if res == '4k' else ''} or --skip-small.")
        if aspect == "9:16":
            for b in boxes:
                if b["y"] / H < STORY_TOP or (b["y"] + b["h"]) / H > 1 - STORY_BOTTOM:
                    warns.append(f"{name}: product enters the story UI zone (top 250 / bottom 340 px at 1080x1920)")
        meta = sources[placed[0]["key"]]
        mode = p.get("mode", "scene")
        prompt, neg = compose(p, spec, slug, meta, lib) if mode == "scene" else ("", "")
        if len(prompt) > 1024:
            errors.append(f"{name}: prompt is {len(prompt)} chars (max 1024); shorten 'product', 'light' or the override"); continue
        flags = list(p.get("flags", [])) + (ov.get("flags") or [])
        if p.get("hands"):
            flags.append("Hands in shot: check fingers, grip and that nothing crosses the product")
        shots.append({"id": i, "cat": p["cat"], "title": p["title"], "name": name, "aspect": aspect, "W": W, "H": H,
                      "boxes": boxes, "mode": mode, "plain": p.get("plain"), "prompt": prompt, "neg": neg,
                      "grade": ov.get("grade", p.get("grade")), "float": p.get("float", False),
                      "also_transparent": p.get("also_transparent", False), "flags": flags,
                      "seed": int(ov.get("seed", base_seed + i * 7919)), "sources": sorted({b["key"] for b in boxes})})
    return shots, skipped, small, warns, errors


# ---------- render ----------
FIELDS = ["name", "prompt_id", "category", "title", "aspect", "resolution", "engine", "model_id", "seed", "file",
          "delivery_file", "product_scale", "integrity", "filtered", "cost_usd", "ai_scene", "sources", "flags", "notes"]


def render_shot(s, ctx, engine, out_dir, dry=False, force=False):
    res, cut = ctx["res"], ctx["cut"]
    code = CODE[s["aspect"]]
    work = ctx["work"] / "concepts" / s["name"]
    master = out_dir / f"{s['name']}_{code}.png"
    done = work / f"result_{engine}_{res}.json"
    if master.exists() and done.exists() and not force and not dry:
        with Image.open(master) as im:
            same_size = im.size == (s["W"], s["H"])
    if master.exists() and done.exists() and not force and not dry and same_size:
        row = json.loads(done.read_text(encoding="utf-8")); row["notes"] = (row.get("notes") or "") + " (kept from earlier run)"
        return row
    W, H = s["W"], s["H"]
    plain = s["mode"] == "plain"
    eng = "none" if plain else engine
    model_id = "" if plain or engine == "mock" else ctx["models"][engine]
    row = {"name": s["name"], "prompt_id": s["id"], "category": s["cat"], "title": s["title"], "aspect": s["aspect"],
           "resolution": res, "engine": eng, "model_id": model_id, "seed": s["seed"], "file": "", "delivery_file": "",
           "product_scale": round(max(b["scale"] for b in s["boxes"]), 3), "integrity": "", "filtered": 0, "cost_usd": "",
           "ai_scene": "no" if plain else "yes", "sources": ",".join(s["sources"]), "flags": " | ".join(s["flags"]), "notes": ""}
    notes, spend = [], 0.0
    layer = product_layer(s["boxes"], cut, W, H)
    work.mkdir(parents=True, exist_ok=True)
    if plain:
        if dry:
            row["integrity"] = "dry-run"; return row
        scene = contact_shadow(plain_bg(s["plain"], W, H), s["boxes"], 0.22)
    else:
        if res == "4k":
            gW, gH = SIZES["2k"][s["aspect"]]
            gboxes = map_boxes(s["boxes"], W / gW)
            glayer = product_layer(gboxes, cut, gW, gH)
        else:
            gW, gH, glayer = W, H, layer
        canvas = Image.new("RGB", (gW, gH), (128, 128, 128))
        canvas.paste(glayer, (0, 0), glayer)
        keep = np.asarray(glayer.getchannel("A")) >= KEEP_ALPHA
        canvas.save(work / "input.png")
        Image.fromarray(np.where(keep, 0, 255).astype(np.uint8)).save(work / "mask_black_is_product.png")
        (work / "prompt.txt").write_text(f"{s['prompt']}\n\nNEGATIVE: {s['neg']}\n", encoding="utf-8")
        if dry:
            row["integrity"] = "dry-run"; row["notes"] = f"{len(s['prompt'])} chars, generate {gW}x{gH}"; return row
        scene = None
        for attempt in range(3):
            seed = s["seed"] + attempt * 101
            img, why = ENGINES[engine](ctx["bed"], ctx["models"], canvas, keep, s["prompt"], s["neg"], seed, ctx["cfg_scale"])
            if img is not None:
                scene, row["seed"] = img, seed
                spend += ctx["cost"].get(engine) or 0
                break
            row["filtered"] += 1; notes.append(why)
        if scene is None:
            row["integrity"] = "FILTERED"; row["notes"] = "; ".join(notes); return row
        if scene.size != (gW, gH):
            notes.append(f"engine returned {scene.width}x{scene.height}, resized to {gW}x{gH}")
            scene = scene.resize((gW, gH), Image.LANCZOS)
        scene.save(work / f"scene_{engine}.png")
        if res == "4k":
            comp = Image.alpha_composite(scene.convert("RGBA"), glayer).convert("RGB")
            scene, note = upscale(ctx["bed"], ctx["models"], comp, s["prompt"], s["neg"], row["seed"], (W, H), engine == "mock")
            spend += 0 if engine == "mock" else (ctx["cost"].get("upscale") or 0)
            if note:
                notes.append(note)
    scene = grade(scene, s["grade"], s["seed"])                       # scene only
    final = Image.alpha_composite(scene.convert("RGBA"), layer).convert("RGB")   # original product pixels on top
    la, fa = np.asarray(layer), np.asarray(final)
    solid = la[..., 3] == 255
    diff = int(np.abs(fa[solid].astype(int) - la[..., :3][solid].astype(int)).max()) if solid.any() else -1
    row["integrity"] = "PASS" if diff == 0 else "REJECT"
    if diff != 0:
        notes.append("product pixels differ from the source" if diff > 0 else "no fully opaque product pixels (check the cut-out)")
        out_dir = out_dir / "rejected"
    out_dir.mkdir(parents=True, exist_ok=True)
    master = out_dir / f"{s['name']}_{code}.png"
    final.save(master)
    row["file"] = str(master.relative_to(ctx["batch_dir"])).replace("\\", "/")
    if diff == 0:
        dd = out_dir / "delivery"; dd.mkdir(exist_ok=True)
        dj = dd / f"{s['name']}_{code}.jpg"
        final.resize(DELIVERY[s["aspect"]], Image.LANCZOS).save(dj, quality=95, subsampling=0)
        row["delivery_file"] = str(dj.relative_to(ctx["batch_dir"])).replace("\\", "/")
        if s["also_transparent"]:
            layer.save(out_dir / f"{s['name']}_{code}_transparent.png")
    known = plain or engine == "mock" or ctx["cost"].get(engine) is not None
    row["cost_usd"] = round(spend, 4) if known else ""
    row["notes"] = "; ".join(notes)
    done.write_text(json.dumps(row, indent=1), encoding="utf-8")
    return row


def safe_render(s, ctx, engine, out_dir, dry, force):
    t = time.time()
    try:
        row = render_shot(s, ctx, engine, out_dir, dry, force)
    except BedrockError as e:
        row = {"name": s["name"], "prompt_id": s["id"], "category": s["cat"], "title": s["title"], "aspect": s["aspect"],
               "resolution": ctx["res"], "engine": engine, "integrity": "ERROR", "notes": str(e)[:300], "ai_scene": "yes",
               "flags": " | ".join(s["flags"])}
    say(f"  {row['name']} {row['aspect']} {row['integrity']} ({time.time() - t:.0f}s)" + (f" {row['notes']}" if row.get("notes") and row["integrity"] != "PASS" else ""))
    return row


# ---------- review sheets ----------
def sheet_font(size):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / "Poppins-Regular.ttf"
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def tile(path, label, cw=520, ch=400):
    t = Image.new("RGB", (cw, ch + 34), "white")
    if path and pathlib.Path(path).exists():
        im = Image.open(path).convert("RGB"); im.thumbnail((cw, ch))
        t.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))
    else:
        ImageDraw.Draw(t).rectangle((0, 0, cw - 1, ch - 1), outline=(200, 200, 200))
    ImageDraw.Draw(t).text((6, ch + 6), label[:62], fill=(20, 20, 20), font=sheet_font(17))
    return t


def grid(rows_of_tiles, titles, out):
    cw = max((sum(t.width for t in r) + 20 * (len(r) + 1) for r in rows_of_tiles), default=400)
    rh = [max((t.height for t in r), default=60) + 44 for r in rows_of_tiles]
    sheet = Image.new("RGB", (cw, sum(rh) + 20), (238, 238, 238))
    d, y = ImageDraw.Draw(sheet), 10
    for r, title, h in zip(rows_of_tiles, titles, rh):
        d.text((20, y), title, fill=(0, 0, 0), font=sheet_font(22))
        x = 20
        for t in r:
            sheet.paste(t, (x, y + 34)); x += t.width + 20
        y += h
    sheet.save(out, quality=85)


def review_sheets(rows, lib, batch_dir, out_dir):
    cats = sorted({r["category"] for r in rows})
    made = []
    for n, k in enumerate(range(0, len(cats), 4), 1):
        group = cats[k:k + 4]
        rt = [[tile(batch_dir / r["file"] if r.get("file") else None, f"{r['name']} {r['title']} [{r['integrity']}]")
               for r in rows if r["category"] == c] for c in group]
        titles = [f"Cat {c}: {lib['categories'][str(c)]['name']}" for c in group]
        out = out_dir / f"review_sheet_{n:02d}.jpg"; grid(rt, titles, out); made.append(out)
    return made


# ---------- main ----------
DEFAULT_ANGLE = {"top": "top-down", "unboxing": "unboxing"}


def load_sources(spec, batch_dir, work, model):
    """spec["sources"]: {key: "path"} or {key: {"file", "angle", "light"}} -> (meta, cut-outs)."""
    raw = spec.get("sources") or {}
    if not raw:
        sys.exit('BLOCK spec needs "sources": real product photos, e.g. {"front": "assets/front.jpg"}')
    meta, cut, missing = {}, {}, []
    for k, v in raw.items():
        v = {"file": v} if isinstance(v, str) else dict(v)
        f = pathlib.Path(v["file"])
        f = f if f.is_absolute() else batch_dir / f
        if not f.exists():
            missing.append(f"{k}: {f}"); continue
        v.setdefault("angle", DEFAULT_ANGLE.get(k, "front"))
        if v["angle"] not in ANGLES:
            sys.exit(f"BLOCK source '{k}': angle '{v['angle']}' not one of {', '.join(ANGLES)}")
        meta[k] = v
        cut[k] = cutout(f, work / "concepts" / "cutouts" / f"{k}.png", model)
    if missing:
        sys.exit("BLOCK source photo(s) not found:\n  " + "\n  ".join(missing))
    return meta, cut


def estimate(shots, engine, res, costs):
    """USD for one successful pass (filtered retries cost extra). None if a needed price is not set."""
    n = sum(s["mode"] != "plain" for s in shots)
    if engine == "mock" or not n:
        return 0.0
    per = [costs.get(engine)] + ([costs.get("upscale")] if res == "4k" else [])
    return None if any(c is None for c in per) else round(n * sum(per), 2)


def write_index(rows, path):
    """Merge with the existing index so a --only run updates its shots and keeps the rest. Returns all rows."""
    old = []
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as fh:
            old = list(csv.DictReader(fh))
    new = {(r["name"], r["aspect"]) for r in rows}
    merged = [r for r in old if (r["name"], r["aspect"]) not in new] + rows
    merged.sort(key=lambda r: (int(r["prompt_id"]), r["aspect"]))
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, restval="", extrasaction="ignore")
        w.writeheader(); w.writerows(merged)
    for r in merged:
        r["category"] = int(r["category"])
    return merged


def run(shots, ctx, engine, out_dir, a):
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        return list(ex.map(lambda s: safe_render(s, ctx, engine, out_dir, a.dry_run, a.force), shots))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--only", help="comma-separated prompt ids, e.g. 36,57")
    ap.add_argument("--res", choices=list(SIZES))
    ap.add_argument("--engine", choices=list(ENGINES))
    ap.add_argument("--benchmark", nargs="?", type=int, const=3, metavar="N",
                    help="render the first N shots (default 3) with nova AND stability side by side")
    ap.add_argument("--dry-run", action="store_true", help="gate, plan and prompts only; no API calls")
    ap.add_argument("--force", action="store_true", help="re-render shots that already have a result")
    ap.add_argument("--skip-small", action="store_true", help="leave out shots whose source photo would be scaled up")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()

    sp = pathlib.Path(a.spec).resolve()
    spec = json.loads(sp.read_text(encoding="utf-8"))
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    slug = spec.get("brand") or sys.exit('BLOCK spec needs "brand" (one slug per batch)')
    batch_dir, env = sp.parent, read_env()
    work = batch_dir / "work"
    res = a.res or spec.get("resolution", "2k")
    engine = a.engine or spec.get("engine", "nova")
    if res not in SIZES or engine not in ENGINES:
        sys.exit(f"resolution must be one of {list(SIZES)}, engine one of {list(ENGINES)}")

    blocks, reviews, info = gate(spec, slug, work)
    for m in info: say("INFO:", m)
    for m in reviews: say("REVIEW:", m)
    for m in blocks: say("BLOCK:", m)
    if blocks:
        sys.exit("\nGate failed: fix the BLOCK items above (never reword a claim to get around a block). Nothing rendered.")

    sources, cut = load_sources(spec, batch_dir, work, spec.get("cutout_model", "birefnet-general-lite"))
    shots, skipped, small, warns, errors = build_plan(spec, lib, slug, sources, cut, res, a.only)
    for m in errors: say("ERROR:", m)
    if errors:
        sys.exit("\nPlan has errors; nothing rendered.")
    if small:
        for m in small: say("TOO SMALL:", m)
        if not a.skip_small:
            sys.exit("\nSource photos too small for this resolution (the product is never scaled up). Nothing rendered.")
        shots = [s for s in shots if max(b["scale"] for b in s["boxes"]) <= 1.0001]
    for m in skipped: say("SKIPPED:", m)
    for m in warns: say("WARN:", m)
    if not shots:
        sys.exit("No shots to render.")

    costs = {k: cost(env, f"COST_{k.upper()}") for k in ("nova", "stability", "upscale")}
    engines = (["mock"] if engine == "mock" else ["nova", "stability"]) if a.benchmark else [engine]
    if a.benchmark:
        shots = [s for s in shots if s["mode"] != "plain"][:max(1, a.benchmark)]
    est = [estimate(shots, e, res, costs) for e in engines]
    est_total = None if None in est else round(sum(est), 2)
    budget = spec.get("budget_usd")
    if est_total is None:
        reviews.append("Cost unknown: set COST_NOVA / COST_STABILITY / COST_UPSCALE (USD per image) in config.env to check the budget.")
    elif budget is not None and est_total > float(budget) and not a.dry_run:
        sys.exit(f"BLOCK estimated cost ${est_total} is over the brief budget ${budget}. Use --only, a preset or --res 2k.")
    say(f"\nPlan: {len(shots)} shot(s) x {', '.join(engines)} at {res}; "
        f"est. ${est_total if est_total is not None else '?'}" + (f" of ${budget} budget" if budget is not None else ""))

    needs_api = not a.dry_run and any(e != "mock" for e in engines) and any(s["mode"] != "plain" for s in shots)
    models = dict(DEFAULT_MODELS, **{k: env[f"{k.upper()}_MODEL_ID"] for k in DEFAULT_MODELS if env.get(f"{k.upper()}_MODEL_ID")})
    ctx = {"res": res, "cut": cut, "work": work, "models": models, "bed": Bedrock(env) if needs_api else None,
           "cost": costs, "cfg_scale": float(spec.get("cfg_scale", 6.5)), "batch_dir": batch_dir}

    base_out = batch_dir / "renders" / "concepts"
    rows, sheets = [], []
    for e in engines:
        out_dir = base_out / "benchmark" / e if a.benchmark else base_out
        out_dir.mkdir(parents=True, exist_ok=True)
        say(f"\n{e}:")
        er = run(shots, ctx, e, out_dir, a)
        rows += er
        if not a.dry_run:
            for old in out_dir.glob("review_sheet_*.jpg"):
                old.unlink()
            sheets += review_sheets(write_index(er, out_dir / "concept_index.csv"), lib, batch_dir, out_dir)

    counts = {k: sum(r.get("integrity") == k for r in rows) for k in ("PASS", "REJECT", "FILTERED", "ERROR", "dry-run")}
    spent = round(sum(float(r["cost_usd"]) for r in rows if r.get("cost_usd") not in ("", None)), 4)
    if not a.dry_run:
        notes = ["# Review notes (render_concepts.py)", "", f"- Brand: {slug} | engine(s): {', '.join(engines)} | {res}",
                 "- Results: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v),
                 f"- Spend: ${spent}" + (" (some prices unknown)" if est_total is None else ""),
                 "", "## Human review"] + [f"- [ ] {m}" for m in dict.fromkeys(reviews)]
        notes += ["", "## Per-shot flags"] + ([f"- {r['name']}: {r['flags']}" for r in rows if r.get("flags")] or ["- none"])
        notes += ["", "## Not rendered"] + ([f"- {m}" for m in skipped + small] or ["- none"])
        notes += ["", "## Warnings"] + ([f"- {m}" for m in warns] or ["- none"])
        bad = [r for r in rows if r.get("integrity") in ("REJECT", "FILTERED", "ERROR")]
        notes += ["", "## Failed"] + ([f"- {r['name']} ({r.get('engine', '')}): {r['integrity']} {r.get('notes', '')}" for r in bad] or ["- none"])
        notes_dir = base_out / "benchmark" if a.benchmark else base_out
        (notes_dir / "review_notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    say(f"\n{len(rows)} result(s): " + ", ".join(f"{v} {k}" for k, v in counts.items() if v)
        + ("" if a.dry_run else f"; spend ${spent}; {len(sheets)} review sheet(s) in {base_out}"))
    sys.exit(1 if counts["REJECT"] or counts["ERROR"] else 0)


if __name__ == "__main__":
    main()

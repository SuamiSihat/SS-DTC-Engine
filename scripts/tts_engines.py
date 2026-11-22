#!/usr/bin/env python3
"""TTS engines for direction videos: edge-tts (default, free), Azure AI Speech and ElevenLabs (both with word timings).

Azure needs AZURE_SPEECH_KEY and AZURE_SPEECH_REGION (e.g. southeastasia) and the azure-cognitiveservices-speech
package. ElevenLabs needs ELEVENLABS_API_KEY. Keys are Windows user environment variables, never in the repo.
Only the script text is sent to the provider.

Spec block (render_direction.py / direction_social.py):
  "tts": {"engine": "azure", "voice": "ms-MY-Osman:DragonHDLatestNeural", "rate": "+5%"}
  "tts": {"engine": "elevenlabs", "voice_id": "...", "model": "eleven_multilingual_v2",
          "settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "speed": 1.05}}

Voice auditions:
  tts_engines.py azure-samples OUT_DIR "text" [--voices name,name,...] [--rate +5%]
  tts_engines.py voices                                   list the ElevenLabs account's voices
  tts_engines.py samples OUT_DIR "text" [--voices id,id,...] [--model ...] [--speed 1.05]   (ElevenLabs)
"""
import argparse, base64, json, os, pathlib, re, sys, urllib.error, urllib.request
from xml.sax.saxutils import escape

API = "https://api.elevenlabs.io/v1"
AZURE_AUDITION = ["ms-MY-Osman:DragonHDLatestNeural", "ms-MY-Yasmin:DragonHDLatestNeural", "ms-MY-OsmanNeural", "ms-MY-YasminNeural"]
DEFAULT_MODEL = "eleven_multilingual_v2"
# neutral, conversational read: mid stability, no style exaggeration
DEFAULT_SETTINGS = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": 1.05}
# ElevenLabs premade voices used for auditions when the account has no Malay-labelled voice
AUDITION_FALLBACK = ["nPczCjzI2devNBz1zQrb", "cjVigY5qzO86Huf0OWal", "iP95p4xoKVk53GoZ742B"]


def _key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        sys.exit("ELEVENLABS_API_KEY is not set. Add it as a Windows user environment variable (never in the repo), "
                 "then restart Zed / the terminal so it is picked up.")
    return k


def _req(path, body=None):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                 headers={"xi-api-key": _key(), "Content-Type": "application/json", "Accept": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs HTTP {e.code} on {path.split('?')[0]}: {e.read().decode('utf-8', 'replace')[:400]}")


def split_alignment(chars, starts, ends):
    """Character alignment -> (sentences, words), each [[start, end, text], ...] in seconds."""
    words, sents, w, s = [], [], None, None
    for i, (c, a, b) in enumerate(zip(chars, starts, ends)):
        if c.isspace():
            if w:
                words.append(w); w = None
        else:
            w = [w[0], b, w[2] + c] if w else [a, b, c]
        if not c.isspace():
            s = [s[0], b, s[2] + c] if s else [a, b, c]
        elif s:
            s[2] += c
        nxt = chars[i + 1] if i + 1 < len(chars) else " "
        if c in ".?!" and nxt.isspace() and s:
            sents.append([s[0], s[1], s[2].strip()]); s = None
    if w:
        words.append(w)
    if s and s[2].strip():
        sents.append([s[0], s[1], s[2].strip()])
    return sents, words


def elevenlabs(text, cfg, mp3):
    model = cfg.get("model", DEFAULT_MODEL)
    body = {"text": text, "model_id": model, "voice_settings": dict(DEFAULT_SETTINGS, **cfg.get("settings", {}))}
    if cfg.get("language_code") and "v2_5" in model:  # language enforcement exists on the v2.5 models only
        body["language_code"] = cfg["language_code"]
    if cfg.get("seed") is not None:
        body["seed"] = cfg["seed"]
    r = _req(f"/text-to-speech/{cfg['voice_id']}/with-timestamps?output_format=mp3_44100_128", body)
    pathlib.Path(mp3).write_bytes(base64.b64decode(r["audio_base64"]))
    al = r.get("alignment") or r.get("normalized_alignment")
    if not al:
        return [], []
    return split_alignment(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"])


def azure(text, cfg, mp3):
    """Azure AI Speech via the Speech SDK; word (and sentence) boundary events give the caption timings."""
    try:
        import azure.cognitiveservices.speech as sdk
    except ImportError:
        sys.exit("Azure Speech SDK missing: python -m pip install --user azure-cognitiveservices-speech")
    key, region = os.environ.get("AZURE_SPEECH_KEY", "").strip(), os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        sys.exit("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not set. Add them as Windows user environment variables "
                 "(setx NAME \"value\"), never in the repo, then restart Zed / the terminal.")
    sc = sdk.SpeechConfig(subscription=key, region=region)
    sc.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)
    sc.set_property(sdk.PropertyId.SpeechServiceResponse_RequestSentenceBoundary, "true")
    syn = sdk.SpeechSynthesizer(speech_config=sc, audio_config=sdk.audio.AudioOutputConfig(filename=str(mp3)))
    words, sents = [], []

    def on_boundary(evt):
        a = evt.audio_offset / 1e7; b = a + evt.duration.total_seconds()
        if evt.boundary_type == sdk.SpeechSynthesisBoundaryType.Word:
            words.append([a, b, evt.text])
        elif evt.boundary_type == sdk.SpeechSynthesisBoundaryType.Sentence:
            sents.append([a, b, evt.text.strip()])
    syn.synthesis_word_boundary.connect(on_boundary)
    voice = cfg["voice"]; lang = cfg.get("lang", "-".join(voice.split("-")[:2]))
    body = escape(text)
    if cfg.get("rate") and cfg["rate"] not in ("+0%", "0%"):
        body = f'<prosody rate="{cfg["rate"]}">{body}</prosody>'
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
            f'<voice name="{voice}">{body}</voice></speak>')
    r = syn.speak_ssml_async(ssml).get()
    if r.reason != sdk.ResultReason.SynthesizingAudioCompleted:
        c = r.cancellation_details
        sys.exit(f"Azure TTS failed for {voice}: {c.reason} {c.error_details}")
    del syn  # closes the output file
    if not sents and words:  # derive sentences from the words if the service sent none
        cur = None
        for a, b, w in words:
            cur = [cur[0], b, cur[2] + " " + w] if cur else [a, b, w]
            if re.search(r"[.?!]$", w):
                sents.append(cur); cur = None
        if cur:
            sents.append(cur)
    return sents, words


def synth(engine, text, cfg, mp3):
    return {"azure": azure, "elevenlabs": elevenlabs}[engine](text, cfg, mp3)


def map_words(display, say_words, dur):
    """Word timings for the displayed text. The spoken text may differ ("UOA" -> "U O A"): words are matched one to
    one when the counts agree, otherwise each displayed word is placed by its character position, interpolated over
    the spoken words' character positions and times."""
    disp = display.split()
    if len(disp) == len(say_words):
        return [[a, b, d] for (a, b, _), d in zip(say_words, disp)]
    if not say_words:
        tot, t, out = sum(len(d) + 1 for d in disp), 0.0, []
        for d in disp:
            l = dur * (len(d) + 1) / tot; out.append([t, t + l, d]); t += l
        return out
    pos, c = [], 0.0  # (char start, char end, t start, t end) of each spoken word, as fractions of the line
    for a, b, w in say_words:
        pos.append((c, c + len(w), a, b)); c += len(w) + 1
    stot = c - 1

    def at(frac):
        x = frac * stot
        for c0, c1, a, b in pos:
            if x <= c1:
                return a + (b - a) * max(0.0, min(1.0, (x - c0) / max(c1 - c0, 1)))
        return pos[-1][3]
    dtot, c, out = sum(len(d) for d in disp) + len(disp) - 1, 0.0, []
    for d in disp:
        out.append([at(c / dtot), at((c + len(d)) / dtot), d]); c += len(d) + 1
    return out


def cmd_voices(_):
    for v in _req("/voices").get("voices", []):
        lab = v.get("labels") or {}
        print(f"{v['voice_id']}  {v.get('name', '')[:28]:28s}  {v.get('category', ''):10s}  "
              + ", ".join(f"{k}={lab[k]}" for k in ("language", "accent", "gender", "age", "descriptive") if lab.get(k)))


def cmd_samples(a):
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    if a.voices:
        ids = a.voices.split(",")
    else:
        vs = _req("/voices").get("voices", [])
        malay = [v["voice_id"] for v in vs if re.search(r"malay|melayu|\bms\b|malaysia", json.dumps(v.get("labels") or {}) + v.get("name", ""), re.I)]
        have = {v["voice_id"] for v in vs}
        ids = (malay + [i for i in AUDITION_FALLBACK if i in have])[:a.max]
    names = {v["voice_id"]: v.get("name", v["voice_id"]) for v in _req("/voices").get("voices", [])}
    for vid in ids:
        nm = re.sub(r"[^A-Za-z0-9]+", "_", names.get(vid, vid)).strip("_")
        mp3 = out / f"sample_{nm}_{vid}.mp3"
        elevenlabs(a.text, {"voice_id": vid, "model": a.model, "settings": {"speed": a.speed}}, mp3)
        print("OK", mp3.name)


def cmd_azure_samples(a):
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    for v in (a.voices.split(",") if a.voices else AZURE_AUDITION):
        mp3 = out / f"sample_azure_{re.sub(r'[^A-Za-z0-9]+', '_', v).strip('_')}.mp3"
        try:
            _, words = azure(a.text, {"voice": v, "rate": a.rate}, mp3)
            print(f"OK {mp3.name} ({len(words)} word timings)")
        except SystemExit as e:
            print(f"SKIP {v}: {e}")


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("azure-samples"); z.add_argument("out_dir"); z.add_argument("text")
    z.add_argument("--voices", help="comma-separated Azure voice names (default: Osman/Yasmin HD and Neural)")
    z.add_argument("--rate", default="+0%")
    sub.add_parser("voices")
    s = sub.add_parser("samples"); s.add_argument("out_dir"); s.add_argument("text")
    s.add_argument("--voices", help="comma-separated voice ids (default: Malay-labelled voices, then premade fallbacks)")
    s.add_argument("--model", default=DEFAULT_MODEL); s.add_argument("--speed", type=float, default=1.05)
    s.add_argument("--max", type=int, default=3)
    a = ap.parse_args()
    {"voices": cmd_voices, "samples": cmd_samples, "azure-samples": cmd_azure_samples}[a.cmd](a)


if __name__ == "__main__":
    main()

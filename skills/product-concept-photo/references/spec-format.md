# Concept spec format (`batches/<batch>/concept_spec.json`)

```json
{
  "brand": "drmitring",
  "ai_imagery": "approved",
  "budget_usd": 20,
  "product": "a rectangular green and white retail box, about 12 cm tall, matte card",
  "pack_text": ["Dr. MIT Ring", "Condom fastener"],
  "sources": {
    "front": "assets/front.jpg",
    "top": {"file": "assets/top.jpg", "angle": "top-down", "light": "soft overhead window light"},
    "out": "assets/ring-out.png"
  },
  "preset": "meta-feed",
  "palette_hint": "soft green and white tones",
  "props": "",
  "resolution": "2k",
  "engine": "nova",
  "overrides": {"36": {"aspect": "9:16", "extra": "morning light"}}
}
```

Top level
| Field | Required | Notes |
| --- | --- | --- |
| `brand` | yes | one slug per batch |
| `ai_imagery` | yes | must be `"approved"` (from the brief) or the gate BLOCKs |
| `budget_usd` | no | BLOCK if the estimate is over it. The estimate needs `COST_*` in `config.env`; without them it is a REVIEW item |
| `product` | yes | neutral description: shape, colour, material, real size. No claims. Max 300 characters |
| `pack_text` | yes | the text printed on the real pack, read by a person. Screened by `check_brand.py` as REVIEW |
| `sources` | yes | real product photos, see below |
| `preset` / `prompts` / `categories` | no | shot selection, combined. `prompts`: list of ids or `"all"`. Default: every prompt |
| `palette_hint`, `light`, `negative_extra` | no | fill `{palette}`, `{light}` and the negative prompt |
| `props` | no | only items listed in `brand.json` `product_facts`. Prompts with `needs: props` are skipped without it |
| `resolution`, `engine` | no | defaults `2k`, `nova`; the `--res` / `--engine` flags win |
| `seed`, `cfg_scale` | no | defaults 1000 and 6.5 |
| `cutout_model` | no | rembg model, default `birefnet-general-lite` |
| `overrides` | no | per prompt id (string key): `scene`, `extra`, `aspect`, `place`, `angle`, `grade`, `seed`, `flags` |

`sources`
- Key = role used by the placements in `prompt-library.json`: `front`, `box`, `out` (product out of the box), `top`, `unboxing`, `lowkey`, `hires`. `*` in a placement means any source.
- Value = a path (relative to the batch folder) or `{"file", "angle", "light"}`.
- `angle`: `front`, `three-quarter`, `top-down`, `low`, `unboxing`. Default: `top` = `top-down`, `unboxing` = `unboxing`, others `front`. Prompts that ask for an angle only use sources with that angle.
- A transparent PNG is used as-is; any other photo is cut out with rembg (alpha only, RGB never changed). Cut-outs are cached in `work/concepts/cutouts/`.
- The product is never scaled up. The plan stops with TOO SMALL when a source is too small for the size (`--skip-small` leaves those shots out). Macro prompts also need `min_source_px`.

Config (`config.env`, never in git)
| Key | Notes |
| --- | --- |
| `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION` | Bedrock API key, or `AWS_PROFILE` with boto3 |
| `COST_NOVA`, `COST_STABILITY`, `COST_UPSCALE` | USD per image, for the budget check and `cost_usd` |
| `NOVA_MODEL_ID`, `STABILITY_MODEL_ID`, `UPSCALE_MODEL_ID` | override the default model ids |

Runs
- `--dry-run`: gate, plan and prompts (`work/concepts/<NAME>/prompt.txt`), no API calls.
- `--engine mock`: fake scene, no cost; tests the paste-back and integrity check.
- `--benchmark [N]`: the first N scene shots (default 3) with both nova and stability, in `renders/concepts/benchmark/<engine>/`.
- `--only 36,57` re-runs those shots; `concept_index.csv` keeps the other rows. Finished shots are kept unless `--force` (or the size changed).
- Exit 1 if any shot is REJECT (product pixels changed) or ERROR.

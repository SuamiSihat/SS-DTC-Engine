# Batch spec (work/spec.json) used by scripts/render_batch.py
```
{
 "brand": "ssclinic", "look": "editorial",   // optional: film look on inserts, settings in brands/<slug>/look.json
 "batch": "<batch>", "prefix": "SSC", "fps": 30,
 "mode": "educational",                         // PLANNED, SS Clinic only: "educational" (default) or "kol_ad"
 "kkliu": null,                                  // PLANNED, required for "kol_ad": KKLIU approval number of this posting
 "lower_third": {"name": "Dr Rak", "title": "Men's Health Doctor"},
 "end_card": {"line": "Jumpa doktor untuk pemeriksaan", "cta": "", "dur": 2.8},  // Educational: neutral close, no clinic CTA
 "clips": [{
   "id": "001", "n": "01", "src": "D:/.../drrak_test_001.MP4",
   "words": "work/words/drrak_001.json",         // Whisper JSON with word timestamps
   "fixes": {"sarab": "saraf"},                    // spelling fixes for captions
   "segments": [[start, end], ...],                // kept source ranges, snapped to word boundaries
   "headline": "*Mitos* atau *fakta?* ...",        // *gold* keywords
   "broll": [{"kind": "quote", "src": [s, e], "text": "<verbatim real review>", "by": "Pelanggan, WhatsApp"}],  // optional, see skills/dtc-broll
   "hooks": {"B": {"segment": [s, e], "headline": "..."}, "C": {"headline": "..."}},
   "variants": [                                 // read with --variants (see SKILL.md, Variant mode; gate in scripts/variants.py)
     {"id": "TOFU-B-story", "funnel": "TOFU", "hook": "B", "style": "story", "product": "care_cream",
      "segments": [[s, e], ...]},               // optional: this variant's source ranges (default: the clip's segments)
     {"id": "BOFU-C-clean", "funnel": "BOFU", "hook": "C", "style": "clean", "product": "care_cream",
      "price_ref": "Menss Care Cream - Sologrip (1 Unit)"}   // BOFU: product name from prices.json, never a typed price
   ]
 }]
}
```
Run: `python scripts/render_batch.py batches/<batch>/work/spec.json [--only 001] [--versions ABC]`, or `--variants [--check]` for variant mode
Versions: A master, B cold open (best line first), C topic visual (first segment in a navy panel layout).
Then `python scripts/check_sync.py --timeline batches/<batch>/renders/<name>.timeline.json` for every file.

SS Clinic end card: in Educational mode the end card carries a neutral line and an empty CTA. Never "Kami Check & Rawat" / "Datang ke SS Clinic" on a doctor video (decision 2026-10-21). KOL ads use the wording approved in the KKLIU application.

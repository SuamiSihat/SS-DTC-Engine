# Batch spec (work/spec.json) used by scripts/render_batch.py
```
{
 "brand": "ssclinic", "look": "editorial",   // optional: film look on inserts, settings in brands/<slug>/look.json
 "batch": "<batch>", "prefix": "SSC", "fps": 30,
 "lower_third": {"name": "Dr Rak", "title": "Men's Health Doctor"},
 "end_card": {"line": "Kami Check & Rawat", "cta": "Datang ke SS Clinic", "dur": 2.8},
 "clips": [{
   "id": "001", "n": "01", "src": "D:/.../drrak_test_001.MP4",
   "words": "work/words/drrak_001.json",         // Whisper JSON with word timestamps
   "fixes": {"sarab": "saraf"},                    // spelling fixes for captions
   "segments": [[start, end], ...],                // kept source ranges, snapped to word boundaries
   "headline": "*Mitos* atau *fakta?* ...",        // *gold* keywords
   "broll": [{"kind": "quote", "src": [s, e], "text": "<verbatim real review>", "by": "Pelanggan, WhatsApp"}],  // optional, see skills/dtc-broll
   "hooks": {"B": {"segment": [s, e], "headline": "..."}, "C": {"headline": "..."}}
 }]
}
```
Run: `python scripts/render_batch.py batches/<batch>/work/spec.json [--only 001] [--versions ABC]`
Versions: A master, B cold open (best line first), C topic visual (first segment in a navy panel layout).
Then `python scripts/check_sync.py --timeline batches/<batch>/renders/<name>.timeline.json` for every file.

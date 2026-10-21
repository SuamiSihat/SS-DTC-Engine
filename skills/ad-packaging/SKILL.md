---
name: ad-packaging
description: Package finished ad videos into one folder per Meta ad set with clear names and an Ad Index.csv. Use at the end of a batch after QA and human sign-off.
---

# Ad packaging
- One folder per ad set (one per source video/topic): `NN - Topic Name/`
- Versions: A = master, B = cold open hook, C = topic visual hook, D = proof hook
- File name pattern: `DMR<NN>_<A|B|C|D>_<Master|Hook-ColdOpen|Hook-TopicVisual|Hook-Proof>.mp4`
  Keep names short (Windows path limits).
- Variant mode (planned): `<PREFIX><NN>_<FUNNEL>-<HOOK>-<Style>.mp4`, e.g. `DMR07_TOFU-B-Energy.mp4`. Count per ad set = number of variants built, not a fixed 4.
- `Ad Index.csv` columns: File, Opening headline, Background, Sec, Engine version, Batch, Funnel, Hook, Style, Mode, KKLIU. Leave Funnel/Hook/Style empty for A-D batches; Mode and KKLIU are for SS Clinic (KKLIU required for every KOL ad file).
  Template: `index-template.csv`. Background type in the row lets us compare Meta results by background.
- Copy to the NAS deliver folder from local disk at the end; verify file count (4 per ad set for A-D batches, or the planned variant count) and sizes. SS Clinic KOL ads without a KKLIU number are not delivered.

---
name: ad-packaging
description: Package finished ad videos into one folder per Meta ad set with clear names and an Ad Index.csv. Use at the end of a batch after QA and human sign-off.
---

# Ad packaging
- One folder per ad set (one per source video/topic): `NN - Topic Name/`
- Versions: A = master, B = cold open hook, C = topic visual hook, D = proof hook
- File name pattern: `DMR<NN>_<A|B|C|D>_<Master|Hook-ColdOpen|Hook-TopicVisual|Hook-Proof>.mp4`
  Keep names short (Windows path limits).
- `Ad Index.csv` columns: File, Opening headline, Background, Sec, Engine version, Batch.
  Template: `index-template.csv`. Background type in the row lets us compare Meta results by background.
- Copy to the NAS deliver folder from local disk at the end; verify file count (4 per ad set) and sizes.

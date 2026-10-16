---
name: sync-qa
description: Automated audio and picture sync check of every final video against the raw footage. Use after rendering and before delivery; never skip it.
---

# Sync QA
Run `python scripts/check_sync.py <final.mp4> <raw.mp4> [--max-offset 0.04]` on EVERY final file.
PASS means audio offset vs raw is within the limit (default 0.04 s, about one frame at 25 fps).
Any FAIL blocks delivery: fix the render and re-run.

Before first use on a new machine, prove the checker works: shift a copy by 0.2 s and by 2 s and
confirm both FAIL (`--selftest` in the script does this on synthetic audio).
Write results to `batches/<batch>/qa/sync_report.txt`.

Note: this is a starter implementation. Validate it on real footage and extend it (e.g. per-segment
checks and picture-frame matching) before relying on it.

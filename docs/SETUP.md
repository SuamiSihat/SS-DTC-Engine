# Technical Setup Guide

For the person installing the engine on a PC. Everyone else can skip this document.

## One-time setup (per user / per machine)
1. Install Claude Code and sign in (needs a plan with enough usage).
2. Clone this repo (private): `git clone https://github.com/SuamiSihat/SS-DTC-Engine.git SS-DTC-Engine`
3. Run setup: Windows `powershell -ExecutionPolicy Bypass -File setup/setup.ps1`, Mac/Linux `bash setup/setup.sh`
4. Copy `config.example.env` to `config.env` and set your NAS paths.
5. Set `DESIGN_SYSTEM_ROOT` in `config.env` and run `python scripts/sync_brand_assets.py`. It copies the latest logos, patterns and doctor-consent status from the SuamiSihat Design System into `brands/<slug>/` (git-ignored; assets are under the proprietary licence). Re-run before every batch. Add `prices.json` per product brand.
6. Install the skills into Claude Code: `python scripts/install_skills.py` (copies `skills/` to `.claude/skills/`; re-run after changing a skill).
7. Self-test: `python setup/check_env.py` and `python scripts/check_sync.py --selftest`
8. Stock b-roll (optional): create free API keys at pexels.com/api and pixabay.com/api/docs, put them in `config.env` (`PEXELS_API_KEY`, `PIXABAY_API_KEY`) with `BROLL_LIBRARY` (NAS folder), then run `python scripts/stock_fetch.py fetch-model` (YuNet face model, newest default for OpenCV 5) and `python scripts/stock_fetch.py selftest`. Keys stay in `config.env`, which git ignores.

## Running a batch
1. Drop raw clips on the NAS `incoming/<batch-name>/`.
2. Copy `briefs/_TEMPLATE.md` to `briefs/<batch-name>.md` and fill it in (one message of full direction).
3. Run the brand gate: `python scripts/check_brand.py --brand <slug> --texts <lines.txt> --doctor "<doctor name>"`. Fix any BLOCK.
4. Open this folder in Claude Code and prompt:
   `Run batch <batch-name> from briefs/<batch-name>.md. Send me all files when done.`
5. Claude edits, renders and runs sync-qa. A person watches every final WITH SOUND and signs off.
6. Approved ad sets are copied to the NAS `deliver/` folder.

## Running a batch (technical steps)
1. Drop raw clips on the NAS `incoming/<batch-name>/`.
2. Copy `briefs/_TEMPLATE.md` to `briefs/<batch-name>.md` and fill it in.
3. Run the brand check: `python scripts/check_brand.py --brand <slug> --texts <lines.txt> --doctor "<doctor name>"`. Fix any BLOCK.
4. Open this folder in Claude Code and prompt: `Run batch <batch-name> from briefs/<batch-name>.md. Send me all files when done.`
5. A person reviews every final video with sound and signs off.
6. Approved ad sets are copied to the NAS `deliver/` folder.

## Maintenance rules
- Footage and renders never go in git (see `.gitignore`).
- Render on local disk, copy to NAS at the end.
- Lessons go in `lessons.md` and into the skills via pull request. The skill owner approves.
- Tag releases (v1.0, v1.1) and record the version in each batch's Ad Index.csv.

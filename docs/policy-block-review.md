# Policy screen: which rules should BLOCK? (for the regulatory adviser)

Prepared 2026-11-18 for the FIX-06 review (due 2026-12-10). NOT legal advice. The adviser and brand owner decide; nothing here is applied yet.

## How the screen works today
- `scripts/check_brand.py` runs on every hook, caption and on-screen line before rendering and again on final text.
- **BLOCK** stops the batch. Today only the brand's own `banned_terms` in `brands/<slug>/brand.json` block (SS Clinic already blocks `countdown`, `last slot(s)`, `slot terakhir`, `mati pucuk`, `lemah batin`, `pancut awal`, `keras dalam 1 sesi`, `tadalafil`, `fitrah`).
- **REVIEW** lists the line for a person to decide. Every rule in `scripts/policy_rules.py` is REVIEW only.
- It is a keyword screen: it cannot see context, images, popups or the text printed on packs. A BLOCK on a word that has innocent uses stops good lines too, so each candidate below shows real false positives.

## Candidates (tested 2026-11-18 on sample lines)
| Rule | Basis | Correct hits | False hits found | Option A | Option B |
|---|---|---|---|---|---|
| `before-after` (all brands) | MAB 2/2019 (services); Meta restricted; TikTok: no misleading comparisons | "Sebelum dan selepas rawatan" | "Before and after meals" (rare in ad copy) | BLOCK for all brands | BLOCK for SS Clinic only |
| `cure-guarantee` (all) | Meta unrealistic outcomes; TikTok no promised results; MMC 5.14 no cure claims | "Dijamin sembuh dalam 7 hari" | "100% silikon" (material), "dalam 3 hari bekerja" (shipping), "proses sembuh luka" (doctor's education) | BLOCK only the guarantee words: `dijamin`, `jaminan`, `guarantee(d)`, `pasti berjaya/berkesan`, `kekal selamanya`, `cure(d)`; keep `100%`, timeframes and `sembuh` as REVIEW | Keep all REVIEW |
| `testimonial` (SS Clinic) | MAB guideline 5.3; SS Clinic modes (meta-policy 1a) | "Testimoni pesakit kami" | "Ramai pesakit cakap mereka malu..." (doctor's real speech) | BLOCK `testimoni*`, `testimonial*`, `ulasan/review pesakit` for SS Clinic; keep "pesakit cakap" REVIEW | Keep REVIEW |
| `inducement` (SS Clinic) | MAB guideline 7.0 | "Diskaun 50% bulan ini" | "Maklumat terhad" (limited information), "sugar-free" | BLOCK `diskaun`, `discount`, `promosi`, `promo`, `% off` for SS Clinic; keep `terhad`, `free`, `offer` REVIEW | Keep REVIEW |
| `superlative` (SS Clinic) | MAB guideline 5.2; MMC 2.6 | "Klinik terbaik di Shah Alam" | "Yang paling penting, jangan malu" | BLOCK `terbaik`, `nombor 1`, `no. 1`, `number one`, `the best` for SS Clinic; keep `paling ...` REVIEW | Keep REVIEW |
| `explicit-anatomy` (all) | TikTok bans explicit body-part terms in ads; Meta adult review risk | "zakar", "penis" | "Batang serai" (lemongrass) | BLOCK `zakar`, `penis`, `kemaluan` on TikTok outputs only (drop `batang`) | Keep REVIEW |

## Recommended to stay REVIEW (context decides)
- `personal-attribute`: also flags the neutral line "Jika anda mengalami simptom, jumpa doktor".
- `sexual-function`: "panjang" and "besar" have everyday uses; Dr. MIT Ring's 2026-10-16 decision allows performance wording.
- `impotence-treatment`: doctors may educate on ED (Meta allows with 18+); the clinic-ad risk is already a SS Clinic banned term (`mati pucuk`).
- `promo-credentials`: "pakar" depends on the doctor's actual registration; the adviser should say which titles are allowed.
- Testimonial rule for product brands: real reviews are allowed with names blurred.

## Questions for the adviser (please answer in writing)
1. For each row above: Option A, Option B, or a different word list?
2. Should SS Clinic Educational posts (organic, real doctor) and KOL ads use the same BLOCK list?
3. May a doctor say "boleh sembuh" / "boleh dirawat" about a condition in Educational content (MMC 5.4 evidence-based discussion)?
4. TikTok: until a TikTok Malaysia rep confirms in writing, should SS Clinic, Dr. MIT Ring and the MENSS rings be Meta-only (see `meta-policy.md` section 2b)?

## How the decision will be applied
- SS Clinic-only BLOCKs: add the agreed words to `banned_terms` in `brands/ssclinic/brand.json` (no code change).
- All-brand BLOCKs: add a level to that rule in `scripts/policy_rules.py` and a test in `tests/test_gate.py`.
- Platform-only BLOCKs (TikTok): need a `--platform` option in `check_brand.py` first.
- Record the decision, adviser name and date in each brand's `decision_log`.

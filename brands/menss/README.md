# MENSS
- **Live product site**: https://menss.co/ (currently featuring **Menss Care Cream**, KKM NOT: `NOT250807222K`)
- **Parent ecosystem hub**: https://suamisihat.com.my/
- **Source**: SuamiSihat Design System v3.6.1, brand guideline v1.0 (16 Oct 2026). Machine-readable rules are in `brand.json`.

Put the supplied brand files here (download the latest from the SuamiSihat Design System, staff login required; never reuse an old copy):
- `logos/`: official logo files listed in brand.json -> logo.files
- `pattern.svg` (if the brand has one)
- fonts (Poppins etc.) installed system-wide
- `prices.json`: synced from https://menss.co/ (re-verify before each batch):
  - **Menss Care Cream — Sologrip (1 Unit)**: RM 89.00 (normal RM 99.00)
  - **Menss Care Cream — Double Power (2 Unit)**: RM 169.00 (normal RM 198.00)
  - **Menss Care Cream — Triple Impact (3 Unit)**: RM 249.00 (normal RM 297.00)

Claims status: TBC - no claims guidance supplied
Doctor consent ref: `doctor_consent_ref` in brand.json (null = not on file).
Update `brand.json` only when the brand owner issues a new guideline version.

## Products and video rules
Machine-readable: `product_rules` in brand.json.

| Product | Angles | Styles | Not allowed |
| --- | --- | --- | --- |
| Menss Care Cream (live on `menss.co`, `NOT250807222K`) | Daily intimate skin care, hydration & skin barrier protection, non-numbing / non-hot formula, how to apply (1-2 hours before or daily after shower) | Clean, Story | Crude slang (`pancut awal`), medical/treatment/cure claims, unapproved Physta®/BioKesum® clinical claims without licensor & brand-owner sign-off |
| Penile Pump | How it works, safe use, build quality, discreet delivery | Clean, Story | Size, performance or treatment results; inflation or pressure metaphors; device shown in use |
| FRESH Wash | Daily grooming routine, freshness, beside everyday grooming items | Clean (bright), Story | Infection, cure or treatment wording; invented statistics |
| MENSS Ring (blue) | Usage steps, sizing, care, discretion | Clean, Story | Performance or size promises; mixing with Dr. MIT Ring (green) |

**Live-site copy caution (`menss.co`)**: The live landing page includes strong performance and premature-ejaculation phrases (e.g. *"Pancut Awal"*, *"prestasi seksual lelaki"*, *"kekerasan dan ketahanan"*, *"disokong kajian klinikal"* for Tongkat Ali Physta® and BioKesum®). Do NOT copy those phrases into ad scripts unless cleared by the brand owner; always run `scripts/check_brand.py` and keep topical cosmetic positioning (`NOT250807222K`).

MENSS Ring and Dr. MIT Ring are separate brands with different rules: never in the same batch or video. The engine currently tracks the lime Dr. MIT Ring only; add a blue colour track before the first MENSS Ring batch.

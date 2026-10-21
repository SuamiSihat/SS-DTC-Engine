# MENSS
Source: SuamiSihat Design System v3.6.1, brand guideline v1.0 (16 Oct 2026). Machine-readable rules are in `brand.json`.

Put the supplied brand files here (download the latest from the SuamiSihat Design System, staff login required; never reuse an old copy):
- `logos/`: official logo files listed in brand.json -> logo.files
- `pattern.svg` (if the brand has one)
- fonts (Poppins etc.) installed system-wide
- `prices.json` for product brands (copy from the live site; see ../prices.example.json)

Claims status: TBC - no claims guidance supplied
Doctor consent ref: `doctor_consent_ref` in brand.json (null = not on file).
Update `brand.json` only when the brand owner issues a new guideline version.

## Products and video rules
Machine-readable: `product_rules` in brand.json.

| Product | Angles | Styles | Not allowed |
| --- | --- | --- | --- |
| Penile Pump | How it works, safe use, build quality, discreet delivery | Clean, Story | Size, performance or treatment results; inflation or pressure metaphors; device shown in use |
| FRESH Wash | Daily grooming routine, freshness, beside everyday grooming items | Clean (bright), Story | Infection, cure or treatment wording; invented statistics |
| MENSS Ring (blue) | Usage steps, sizing, care, discretion | Clean, Story | Performance or size promises; mixing with Dr. MIT Ring (green) |

MENSS Ring and Dr. MIT Ring are separate brands with different rules: never in the same batch or video. The engine currently tracks the lime Dr. MIT Ring only; add a blue colour track before the first MENSS Ring batch.

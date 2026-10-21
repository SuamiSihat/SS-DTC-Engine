# SuamiSihat DTC Engine

A shared workspace that helps the Creative Department turn raw talking-head footage into Meta-ready video ads (Reels) and structured Masterclass educational series quickly, consistently and within each brand's guidelines.

## What it does

Give the engine a set of raw clips and a short brief. It supports two primary workflows:
- **DTC Reels (`dtc-reels-editor`)**: Removes pauses and filler, adds captions, headlines, offer cards and backgrounds, and produces several opening hooks for each 9:16 vertical video (`1080x1920`).
- **Masterclass Series (`masterclass-editor`)**: Turns doctor or presenter lecture footage into a **5-episode educational series (`EP01`–`EP05`)** plus a **mandatory Series Trailer** (containing a highlight clip from every episode), rendered in both **16:9 (`1920x1080`)** and **9:16 (`1080x1920`)** with episode/chapter title cards, split-screen slide/diagram callouts, and numbered key-takeaway summary cards.

Every video is checked by automated QA gates and reviewed by a person before it is used.

In our first trial (Dr. MIT Ring, October 2026), 10 raw clips became 40 ready-to-review ads in under four hours.

## Brands covered

Each brand has its own rules for colours, logos, tone of voice and wording that must not be used. The engine applies the rules of one brand per batch.

| Brand / Hub | Slug | Live website | Focus & products |
| --- | --- | --- | --- |
| **SuamiSihat® (Ecosystem Hub)** | — | https://suamisihat.com.my/ | Parent men's health portal, clinic locator & SuamiSihat Store (`Herbs & Supplements`, `Condoms & Wearables`, `Raw Herbs & Superfoods`, `Coffee & Drinks`) |
| **Dr. MIT Ring** | `drmitring` | https://drmitring.com/ | Male Intimacy Technology (M.I.T.) green silicone ring (`Alpha Starter` 2 rings, `Power Duo` 4 rings, `Impact Trio` 6 rings) |
| **MENSS** | `menss` | https://menss.co/ | Intimate wellness & personal care: **Menss Care Cream** (`NOT250807222K`, live on `menss.co`), **Penile Pump**, **FRÉSH Wash**, **MENSS Ring (blue)** |
| **REJAL** | `rejal` | https://rejal.co/ | Heritage functional foods: **Bawang Lanang + Madu Tualang** (35g, 250g), **Rejal Madu Tualang**, **Stevia** |
| **SS Clinic** | `ssclinic` | https://suamisihat.clinic/ | Men's health clinics (Subang Jaya & Kota Bharu): Educational mode (real doctor, no clinic CTA) or KOL ad mode (hired KOL, KKLIU per posting) |
| **Mensculine** | `mensculine` | *(Export marketplaces)* | International English topical care brand (export counterpart to Menss Care Cream) |
| **PERTABI** | `pertabi` | *(Partner NGO)* | Persatuan Taat Bersama Isteri Malaysia — community partner only (not an advertisable product brand) |

## How a batch works

1. **Prepare the footage.** Place the raw clips in a new batch folder on the NAS.
2. **Write the brief.** Copy `briefs/_TEMPLATE.md`, fill in the brand, the topic of each clip, the doctor appearing (if any) and the offer (or 5-episode chapter structure for Masterclass series).
3. **Run the batch.** Ask the engine to run it. The brand rules are checked first, and anything that breaks them is flagged before editing begins.
4. **Review.** A team member watches every video with sound, checks wording, doctor details, prices and sync, and approves or requests changes.
5. **Deliver.** Approved videos are organised into ad-set or Masterclass series folders on the NAS together with an index sheet.

## Responsibilities that stay with people

The engine speeds up editing. It does not replace judgement. People remain responsible for:

- Confirming the doctor appearing in an ad or lesson is appointed by SuamiSihat and has given written consent where required.
- Approving health and product claims with the brand owner.
- Confirming prices and offers in `brands/<slug>/prices.json` match the live website (`drmitring.com`, `menss.co`, `rejal.co`).
- Blurring customer names in proof screenshots.
- Choosing the SS Clinic content mode, and getting KKLIU approval for every SS Clinic KOL ad before it runs.
- Giving final sign-off on every video before it is published.

## What is in this folder

| Folder or file | Purpose |
| --- | --- |
| `briefs/` | Brief template and completed briefs |
| `brands/` | Rules for each brand (`brand.json`, `README.md`, `look.json`, `prices.json`: colours, tone, wording to avoid, doctor policy, per-product video rules, live websites) |
| `skills/` | The engine's editing instructions (`dtc-reels-editor`, `masterclass-editor`, `dtc-broll`, `brand-rules`, `hook-backgrounds`, `sync-qa`, `ad-packaging`) |
| `lessons.md` | Notes from past batches so mistakes are not repeated |
| `docs/SETUP.md` | Installation guide for the person setting up a PC |
| `CLAUDE.md` | Standing instructions the engine follows in every session |

## Getting started

Installation is done once per computer by the person responsible for setup. Please follow [docs/SETUP.md](docs/SETUP.md). After that, team members only need to open the folder, complete a brief and request a batch.

## Questions and feedback

Please raise issues, suggestions and lessons learned with the Head of Creative so they can be added to the engine for everyone.

*Internal use only. Brand assets and claims guidance remain the property of SuamiSihat.*

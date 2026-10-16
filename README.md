# SuamiSihat DTC Engine

A shared workspace that helps the Creative Department turn raw talking-head footage into Meta-ready video ads (Reels) quickly, consistently and within each brand's guidelines.

## What it does

Give the engine a set of raw clips and a short brief. It prepares the edits: removes pauses and filler, adds captions, headlines, offer cards and backgrounds, and produces several opening hooks for each video. Every video is then checked by a person before it is used.

In our first trial (Dr. MIT Ring, October 2026), 10 raw clips became 40 ready-to-review ads in under four hours.

## Brands covered

Dr. MIT Ring, Mensculine, MENSS, PERTABI, REJAL and SS Clinic. Each brand has its own rules for colours, logos, tone of voice and wording that must not be used. The engine applies the rules of one brand per batch.

## How a batch works

1. **Prepare the footage.** Place the raw clips in a new batch folder on the NAS.
2. **Write the brief.** Copy `briefs/_TEMPLATE.md`, fill in the brand, the topic of each clip, the doctor appearing (if any) and the offer.
3. **Run the batch.** Ask the engine to run it. The brand rules are checked first, and anything that breaks them is flagged before editing begins.
4. **Review.** A team member watches every video with sound, checks wording, doctor details, prices and sync, and approves or requests changes.
5. **Deliver.** Approved videos are organised into ad-set folders on the NAS together with an index sheet.

## Responsibilities that stay with people

The engine speeds up editing. It does not replace judgement. People remain responsible for:

- Confirming the doctor appearing in an ad is appointed by SuamiSihat and has given written consent where required.
- Approving health and product claims with the brand owner.
- Confirming prices and offers are current.
- Blurring customer names in proof screenshots.
- Giving final sign-off on every video before it is published.

## What is in this folder

| Folder or file | Purpose |
| --- | --- |
| `briefs/` | Brief template and completed briefs |
| `brands/` | Rules for each brand (colours, tone, wording to avoid, doctor policy) |
| `skills/` | The engine's editing instructions |
| `lessons.md` | Notes from past batches so mistakes are not repeated |
| `docs/SETUP.md` | Installation guide for the person setting up a PC |
| `CLAUDE.md` | Standing instructions the engine follows in every session |

## Getting started

Installation is done once per computer by the person responsible for setup. Please follow [docs/SETUP.md](docs/SETUP.md). After that, team members only need to open the folder, complete a brief and request a batch.

## Questions and feedback

Please raise issues, suggestions and lessons learned with the Head of Creative so they can be added to the engine for everyone.

*Internal use only. Brand assets and claims guidance remain the property of SuamiSihat.*

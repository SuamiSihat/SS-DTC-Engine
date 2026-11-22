# Batch brief: ssc-navigation-03
Brand slug (one of: drmitring, mensculine, menss, pertabi, rejal, ssclinic): ssclinic
Date: 2026-11-21
Requested by: Haru

## Footage
- Source: D:\SynologyDrive\SS-DTC\incoming\03-ssc-navigation\VID_20261115_112929.mp4 (local copy: batches/ssc-navigation-03/raw/route_raw.mp4)
- Number of clips: 1 (5:01.6, 1920x1080 landscape, 30 fps, phone original; same route take as ssc-direction-01, which used the 640x360 WhatsApp copy)
- Speaker(s): none on camera. New voice-over only.

## Per-topic direction
| Clip | Topic | Best hook line (if known) | Background idea | Notes |
| --- | --- | --- | --- | --- |
| route_raw | Navigation video: Federal Highway -> UOA Business Park -> SS Clinic door | "Ini cara ke SS Clinic Subang Jaya, dari Lebuhraya Persekutuan" | Real route footage only | Storyboard and VO = ssc-direction-01 as rendered (incoming/03-ssc-navigation/storyboard.md, vo_script.md) |

## Clinic location (from ssc-direction-01, confirmed by Haru 2026-11-16)
- Name on video: SS Clinic Subang Jaya
- Address: SuamiSihat Clinic, 8-3A, 51A, Jalan Pengaturcara, UOA Business Park, Seksyen U1, 40150 Shah Alam, Selangor
- Floor: Level 1, The Podium, next to Ali, Muthu & Ah Hock Cafe. Lift to Level 1; out of the lift turn left.
- Parking: 2 SuamiSihat / SS Clinic reserved bays next to the EV chargers. Number plate scanned on entry; pay by debit/credit card when leaving.
- Phone: 03-6044 1878 (front desk)
- Opening hours: 10:00 AM - 5:00 PM, end card "Waktu operasi: 10:00 pagi - 5:00 petang"

## Creative direction
- Goal: a driver/visitor can follow the route without getting lost.
- Market: general-bm. Language: BM.
- Voice-over: text-to-speech (edge-tts ms-MY-OsmanNeural, +10%)
- Funnel stage: BOFU / utility
- Outputs: videos, 16:9 1920x1080 and 9:16 1080x1920, plus WhatsApp 720x1280 (about 10 MB, scaled down from the 9:16 files; added after the main render)
- Music: energetic bed, ducked under the VO (requested by Haru 2026-11-21). Candidate: "2tech-audio-happier.mp3" (130 BPM) from GV-Assets/4.0 Teams Works/Audio, licence TBC. No-music versions delivered as well.

## Offer
- None. No price, offer, review count or superlative.
- Ignore incoming/03-ssc-navigation/COPY.md: it is an unrelated stamina-product template (product hook, "50,000 lelaki" social proof) and is not used.

## Compliance (decide BEFORE the run)
- SS Clinic content mode: clinic navigation video (same decision as ssc-direction-01, Haru 2026-11-16). No doctor, no claims, offer, price or review.
- KKLIU approval number: none supplied. Open point: public posting or boosting may count as a clinic advertisement under MAB rules.
- Doctor appearing: none
- Claims approved by brand owner: n/a (no claims in the copy)
- Bystanders: same skips as ssc-direction-01 (4:03.5-4:12, 4:31-4:37, 4:40-4:46.5, 4:50.5 onward)
- Hooks needing review: none
- AI voice: TikTok needs the AIGC label (meta-policy.md 2b)

## Delivery
- Send ALL files when done (not samples): yes
- Deliver to: D:\SynologyDrive\SS-DTC\deliver\ssc-navigation-03\

## v2 update (requested by Haru 2026-11-22)
- Accent #F4A261 -> #FCE53D, this batch only (spec "accent"; brands/ssclinic/brand.json unchanged).
- A. Social cut, 9:16 only, Vox-style fast edit for TikTok / IG (`work/social_spec.json`, `scripts/direction_social.py`). Hook 1: "Sini SS Clinic Subang Jaya / CARA NAK SAMPAI".
- B. Full guide v2, 16:9 + 9:16, v1 VO lines, tighter pacing (`work/direction_spec_v2.json`).
- Voice: Azure AI Speech (Haru 2026-11-22, instead of ElevenLabs), default ms-MY-Osman:DragonHDLatestNeural (preview), final voice picked from auditions. Still AI voice: TikTok AIGC label.
- Music: same track (only one in the library), from its high-energy section (16 s), louder, lighter ducking, cuts on the beat. Licence still TBC.
- Open (Haru / brand owner): TikTok posting for a medical institution, MAB / KKLIU for discovery-style posting.
- Deliver to: D:\SynologyDrive\SS-DTC\deliver\ssc-navigation-03\v2\

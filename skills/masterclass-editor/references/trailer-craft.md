# Trailer craft (EP00_Trailer + EP00_Teaser)

How to cut the Masterclass trailer so it sells the series instead of summarising it.
Sources: MasterClass trailer blueprint (3-act mini-movie, A/B-cam, slow b-roll, music arc, sparse type, sign-off) and IFH 181 *Trailer Editing Techniques* (Chris, FilmEditingPro): the series is not the trailer, full line breakdowns, cut audio first, line-moment-line rhythm, nothing resolves.

Status: craft rules apply now to planning and manual edits. Fields marked **PLANNED** are not read by `scripts/render_masterclass.py` yet (it still renders a fixed linear sequence with no music bed).

## 1. The series is not the trailer
- The trailer's only job: make a man want to watch EP01. It is not a table of contents.
- Order follows the 3-act arc, not EP01 -> EP05. Coverage rule stays: every episode contributes at least one real line, and the curriculum card still lists all episodes in order.
- For every line, shot and card ask: **what does this promise the viewer?** If the answer is "nothing", cut it. Record the answer in `promise` in the line bank.

## 2. Breakdown before editing (line bank + visual bank)
Do this after transcription, before any cut.
- `work/trailer_linebank.json` (**PLANNED** generator; build by hand from transcripts until then): every usable spoken sentence from all episodes, one row each:
  `{"id": "EP03_L014", "ep": "EP03", "s": 41.20, "e": 45.80, "text": "...", "tags": ["question"], "promise": "you'll learn why blood flow matters", "resolves": false, "standalone": true}`
- Tags: `question`, `myth`, `promise` ("dalam siri ini saya akan..."), `number`, `quote` (short memorable line), `stakes` (what happens if ignored), `steps`, `answer`, `signoff`.
- `standalone: false` if the line needs the sentence before it to make sense. Never use those alone.
- `work/trailer_visualbank.json`: A-cam wide, punch-in faces, B-cam profile (if shot), hands/gesture close-ups, slow-motion b-roll, diagram reveals, room/set details. Each with source, in/out, and a mood tag (`calm`, `focus`, `reveal`).
- Pick from the banks non-linearly. Episode order inside the source is irrelevant.

## 3. Cut audio first
Build `work/trailer_audio_map.json` (**PLANNED**) before placing any picture:
1. Choose the music cue (licensed library only; request stems where possible).
2. Lay the dialogue lines on the timeline against the music: Act I over the minimal intro, the turn line exactly where the beat comes in, Act III lines on the build.
3. Mark the "moments" (gaps between lines) and the hard music stop.
4. Close your eyes and listen. If the audio alone doesn't work, picture won't save it.
5. Only then fill picture: sync lines get their own source video; moments get b-roll, cards or reaction shots.
Speech rule unchanged: each line keeps its own source audio, never sped up, never re-voiced; every segment passes `check_sync.py`.

## 4. The 3-act structure
| Act | 16:9 trailer (60-90 s) | 9:16 teaser (25-40 s) | Content | Music |
| --- | --- | --- | --- | --- |
| I Hook & problem | 0-20 s | 0-6 s | Cold-open `question`/`myth` line, doctor lower third, 1-2 `stakes` lines. State the problem, not the answer. | Ambient pad or slow piano, near-silent under speech |
| Title | ~20 s | ~6 s | Signature card `[NAMA] MENGAJAR [TOPIK]` (e.g. `DR RAK MENGAJAR KESIHATAN LELAKI`) + series title | Breath, single hit |
| II Promise | 20-55 s | 6-20 s | The doctor's own `promise` line ("Dalam siri ini..."), then lines from different episodes alternating with moments | Rhythmic pulse or soft orchestral swell enters on the turn |
| III Climax | 55-80 s | 20-32 s | Fast montage of 1-line hits (`quote`, `number`, `myth`) covering the remaining episodes, cut on the beat; curriculum card | Driving build to crescendo |
| Sign-off | last 5-8 s | last 4-6 s | Music stops dead on the final spoken word. Doctor's recorded sign-off, then neutral end card | Silence / room tone |

- No promise line or sign-off in the footage = skip that beat. Never invent, assemble or synthesise one from separate words. Add them to the shoot list (section 9) instead.
- The 9:16 teaser is a separate cut, not a crop of the 16:9 trailer: Act I + title + 3-4 Act III hits. Coverage rule applies to the 16:9 trailer and the curriculum card; the teaser may show fewer episodes.

## 5. Line - moment - line
In Acts I and II never stack lines back to back. Pattern:
`line -> moment (0.5-1.5 s) -> line -> moment -> line`
A moment is a breath of style with no speech: slow b-roll, a hand gesture, a diagram drawing itself, a punch-in on the doctor listening/thinking, a kinetic word, a music accent. In Act III moments shrink to 0.2-0.5 s and cuts land on the beat.

## 6. Nothing resolves (with a compliance guard)
- Prefer `question`, `myth`, `stakes` and `promise` lines. Avoid `answer` lines; the answer belongs to the episode.
- End mini-sequences on the question, then cut away (to black, to a card, or to another episode's line).
- **Meaning gate (hard rule):** a trailer cut may stop *before* an answer, but never inside a sentence in a way that drops a qualifier ("jika", "untuk sesetengah", "berjumpa doktor dulu") or flips the meaning. Every line must be a complete thought the doctor would sign off on as said. Health claims never get cut into implied promises of results.
- Never imply treatment, cure or clinic services (SS Clinic Educational mode rules still apply).

## 7. Picture & look
- A-cam wide as the base; punch-ins (`1.25-1.35x`) on emotional or key lines; B-cam profile for candid reactions if available.
- Slow motion only on b-roll without sync audio (shot at 50/60 fps, conformed to 30). Speed ramps on b-roll only. The doctor's speech is never retimed.
- Grade: apply the SS Editorial finishing layer (`editorial-film-edit`) or the brand grade: low contrast, slightly lifted blacks, warm skin. Same grade across all trailer shots.
- Type is sparse: signature card, doctor lower third, episode badges (small), curriculum card, end card. Max one kinetic word/phrase per moment, and only words the doctor actually says.
- Do not copy MasterClass's logo, wordmark, typeface or card layout; use the brand's own palette and Poppins.

## 8. Sound design & mix
- Music: licensed library track only, never trending/commercial songs. Duck to -18 to -22 dB under speech; let it rise in the moments. Hard stop on the last spoken word, then room tone.
- SFX via `scripts/sound_design.py`, low level: soft whoosh into title card, low hit on the signature card and curriculum card, subtle risers into Act III. Isolated foley only when the doctor names the action on screen (pen on paper, page turn).
- Loudness: master to -14 LUFS integrated, true peak <= -1 dBTP for social; dialogue always intelligible on phone speakers.
- Always also deliver a no-music version (`_nomusic`) so the team can swap tracks or post without music.

## 9. Shoot list that makes trailers possible (give to production)
- One clean **promise line**: "Dalam siri ini, saya akan terangkan ..." (2-3 takes).
- One **sign-off**: "Saya Dr Rak, dan ini Masterclass SuamiSihat." (if the brand approves the wording).
- B-cam at ~45 degrees for profile reactions.
- 60 fps b-roll: hands, writing, diagrams, the set, doctor walking in / reading notes. No explicit anatomy, no pills, no distressed men.
- 30 s of room tone per setup.

## 10. Versions & review
- Cut at least two trailer versions before review: **A story-led** (more Act I/II lines) and **B style-led** (shorter Act I, longer montage). Reviewers pick; keep notes on why.
- Watch once with sound off and once eyes closed. Sound off must still read (lower third + cards); eyes closed must still tell the arc.
- Spoiler check: no episode's key answer or full takeaway list is spoken in the trailer (the curriculum card lists topics, not answers).

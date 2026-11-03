# Masterclass batch spec (`work/spec_masterclass.json`)

Used to plan and render a **5-episode Masterclass series** (`EP01`–`EP05`) plus its **mandatory Series Trailer** (`EP00_Trailer`, containing a clip from every episode) in both **16:9** (`1920x1080`) and **9:16** (`1080x1920`).

```json
{
  "brand": "ssclinic",
  "mode": "educational",
  "look": null,
  "batch": "drrak-masterclass-01",
  "prefix": "SSC-MC01",
  "fps": 30,
  "formats": ["16x9", "9x16"],
  "series": {
    "title": "Memahami Kesihatan Intim & Vitaliti Suami",
    "subtitle": "Siri Masterclass 5 Episod Berasaskan Bukti",
    "episode_count": 5
  },
  "lower_third": {
    "name": "Dr Rak",
    "title": "Men's Health Doctor"
  },
  "end_card": {
    "line": "Jumpa doktor untuk pemeriksaan jika ada simptom",
    "cta": "",
    "dur": 3.0
  },
  "trailer": {
    "id": "EP00_Trailer",
    "title": "Trailer Siri Masterclass: 5 Topik Utama Kesihatan Lelaki",
    "order": "arc",
    "versions": ["A_story", "B_style"],
    "linebank": "work/trailer_linebank.json",
    "audio_map": "work/trailer_audio_map.json",
    "music": {
      "src": "//Ssnas/drm/SS-DTC/library/music/<licensed_cue>.wav",
      "license": "<library + licence id>",
      "duck_db": -20,
      "turn_at": 20.0,
      "hard_stop": "last_spoken_word",
      "nomusic_version": true
    },
    "signature_card": {
      "line": "DR RAK MENGAJAR KESIHATAN LELAKI",
      "kicker": "SUAMISIHAT MASTERCLASS · 5 EPISOD",
      "dur": 3.0
    },
    "lines": [
      {"act": "I",   "episode_id": "EP01", "segment": [1.20, 4.50],  "tag": "myth",     "headline": "*Mitos* atau *fakta:* masih ada morning wood, masalah tak serius?"},
      {"act": "I",   "episode_id": "EP04", "segment": [3.20, 9.80],  "tag": "stakes",   "badge": "EPISOD 04 · Bahaya Ubat Tidak Berdaftar"},
      {"act": "II",  "episode_id": "EP01", "segment": [0.00, 0.00],  "tag": "promise",  "note": "only if the doctor recorded a promise line; else omit"},
      {"act": "II",  "episode_id": "EP02", "segment": [5.40, 11.80], "tag": "question", "badge": "EPISOD 02 · Punca Fizikal vs Psikologi"},
      {"act": "III", "episode_id": "EP03", "segment": [10.00, 13.10], "tag": "quote",   "badge": "EPISOD 03 · Aliran Darah, Saraf & Metabolik"},
      {"act": "III", "episode_id": "EP05", "segment": [6.00, 8.90],  "tag": "quote",    "badge": "EPISOD 05 · Langkah Pemeriksaan & Gaya Hidup"}
    ],
    "moments": [
      {"after_line": 0, "dur": 1.0, "kind": "broll_slowmo", "src": "visualbank:hands_notes_01"},
      {"after_line": 1, "dur": 0.8, "kind": "punch_in_listen"}
    ],
    "sign_off": {"episode_id": null, "segment": null, "note": "doctor's recorded sign-off only"},
    "teaser_9x16": {
      "id": "EP00_Teaser",
      "lines": [0, 4, 5],
      "target_s": [25, 40]
    },
    "curriculum_card": {
      "title": "5 EPISOD DALAM SIRI INI",
      "hold_s": 4.5,
      "bullets": [
        "01 · Mitos atau Fakta: Ereksi Pagi",
        "02 · Cara Bezakan Punca Fizikal vs Psikologi",
        "03 · Kaitan Aliran Darah, Saraf & Kesihatan Badan",
        "04 · Risiko Ubat Kuat Tidak Berdaftar Dalam Talian",
        "05 · Bila Perlu Pemeriksaan Doktor & Langkah Awal"
      ]
    }
  },
  "episodes": [
    {
      "id": "EP01",
      "number": "EPISOD 01 / 05",
      "title": "Mitos atau Fakta: Morning Wood",
      "src": "//Ssnas/drm/SS-DTC/incoming/drrak-masterclass-01/drrak_mc_ep01.MP4",
      "words": "work/transcripts/drrak_mc_ep01.json",
      "facetrack": "work/facetrack_ep01.json",
      "fixes": {"sarab": "saraf"},
      "chapters": [
        {
          "id": "EP01_ch01",
          "number": "BAB 01",
          "title": "Apa Maksud Ereksi Pagi?",
          "segments": [[1.20, 18.40], [20.10, 42.80]],
          "hook_9x16": {
            "segment": [1.20, 5.10],
            "headline": "*Mitos* atau *fakta:* masih ada morning wood, masalah tak serius?"
          },
          "callouts": [
            {
              "kind": "myth_fact",
              "src": [6.00, 14.50],
              "layout_16x9": "split_right",
              "layout_9x16": "card",
              "label": "MITOS vs FAKTA",
              "points": [
                "Mitos: Ada morning wood = tiada masalah langsung",
                "Fakta: Aliran darah & fungsi saraf masih perlu dinilai"
              ]
            }
          ]
        }
      ],
      "episode_takeaways": {
        "title": "RINGKASAN EPISOD 01",
        "hold_s": 4.0,
        "bullets": [
          "Ereksi pagi bukan jaminan tiada isu kesihatan",
          "Faktor aliran darah dan saraf main peranan utama",
          "Periksa awal jika kualiti ereksi mula berubah"
        ]
      }
    },
    {
      "id": "EP02",
      "number": "EPISOD 02 / 05",
      "title": "Punca Fizikal vs Psikologi",
      "src": "//Ssnas/drm/SS-DTC/incoming/drrak-masterclass-01/drrak_mc_ep02.MP4",
      "words": "work/transcripts/drrak_mc_ep02.json",
      "facetrack": "work/facetrack_ep02.json",
      "fixes": {},
      "chapters": [],
      "episode_takeaways": {
        "title": "RINGKASAN EPISOD 02",
        "hold_s": 4.0,
        "bullets": []
      }
    },
    {
      "id": "EP03",
      "number": "EPISOD 03 / 05",
      "title": "Aliran Darah, Saraf & Kesihatan Metabolik",
      "src": "//Ssnas/drm/SS-DTC/incoming/drrak-masterclass-01/drrak_mc_ep03.MP4",
      "words": "work/transcripts/drrak_mc_ep03.json",
      "facetrack": "work/facetrack_ep03.json",
      "fixes": {},
      "chapters": [],
      "episode_takeaways": {
        "title": "RINGKASAN EPISOD 03",
        "hold_s": 4.0,
        "bullets": []
      }
    },
    {
      "id": "EP04",
      "number": "EPISOD 04 / 05",
      "title": "Bahaya Ubat Tidak Berdaftar Dalam Talian",
      "src": "//Ssnas/drm/SS-DTC/incoming/drrak-masterclass-01/drrak_mc_ep04.MP4",
      "words": "work/transcripts/drrak_mc_ep04.json",
      "facetrack": "work/facetrack_ep04.json",
      "fixes": {},
      "chapters": [],
      "episode_takeaways": {
        "title": "RINGKASAN EPISOD 04",
        "hold_s": 4.0,
        "bullets": []
      }
    },
    {
      "id": "EP05",
      "number": "EPISOD 05 / 05",
      "title": "Langkah Pemeriksaan & Gaya Hidup Sihat",
      "src": "//Ssnas/drm/SS-DTC/incoming/drrak-masterclass-01/drrak_mc_ep05.MP4",
      "words": "work/transcripts/drrak_mc_ep05.json",
      "facetrack": "work/facetrack_ep05.json",
      "fixes": {},
      "chapters": [],
      "episode_takeaways": {
        "title": "RINGKASAN EPISOD 05",
        "hold_s": 4.0,
        "bullets": []
      }
    }
  ]
}
```

## Pre-render & QA checklist
1. **Trailer completeness gate**: Confirm `trailer.lines` uses **every episode** in `episodes` (`EP01` through `EP05`) at least once, each line uses that episode's own source clip and audio, no `promise`/`sign_off` entry has a placeholder segment, and `music.license` is filled (or `music` is removed for a no-music trailer).
2. **Trailer meaning gate**: Read every `trailer.lines[*]` segment as cut. Each must be a complete thought, keep its qualifiers, not imply a result or clinic service, and not speak an episode's key answer (`references/trailer-craft.md` §6).
3. **Brand & policy gate**: Extract all text from `series`, `trailer` (`signature_card`, `lines[*].headline`, `lines[*].badge`, `curriculum_card.bullets`), `episodes[*]` (`title`, `chapters[*].title`, `hook_9x16.headline`, `callouts[*].points`, `episode_takeaways.bullets`), and transcripts into `batches/<batch>/work/texts.txt`, then run:
   `python scripts/check_brand.py --brand <slug> --texts batches/<batch>/work/texts.txt --doctor "Dr Rak"`
4. **Post-render QA**: Verify every 16:9 and 9:16 output file (Trailer + Teaser + all 5 Episodes + 9:16 Cutdowns):
   - `python scripts/check_sync.py <rendered.mp4> <raw.mp4> --max-offset 0.04`
   - `python scripts/check_layout.py batches/<batch>/renders/9x16/<name>.timeline.json` (for 9:16 Trailer and 9:16 cutdowns)
   - `ffprobe` resolution check (`1920,1080` for 16:9; `1080,1920` for 9:16).

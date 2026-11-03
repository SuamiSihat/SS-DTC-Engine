# Batch brief: masterclass-hairul
Brand slug: ssclinic
Content mode: educational (SuamiSihat Masterclass — fitness & lifestyle coaching by Coach Hairul; no clinic solicitation CTA, no offers/discounts)
Date: 2026-10-21
Requested by: Head of Creative

## Footage
- NAS folder: `\\Ssnas\drm\SS-DTC\incoming\masterclass-hairul\`
  - `EP1/` (21 clips, `C3668.MP4`–`C3692.MP4`)
  - `EP2/` (17 clips, `C3694.MP4`–`C3714.MP4`)
  - `EP3/` (9 clips, `C3715.MP4`–`C3723.MP4`)
  - `EP4/` (16 clips, `C3725.MP4`–`C3741.MP4`)
  - `EP5/` (12 clips, `C3742.MP4`–`C3754.MP4`)
  - `broll/` (111 clips: `DJI_0473`–`DJI_0558` 45° B-camera + `IMG_1715`–`IMG_1745` detail cutaways)
- Speaker: **Coach Hairul** (`Coach Hairul, Personal Trainer · SuamiSihat Masterclass`) — fitness trainer (not a medical doctor).
- Transcripts: `batches/masterclass-hairul/work/transcripts/` (Malay, Faster-Whisper `small`, word-level timestamps).
- Note on `MR. HAIRUL_MASTERCLASS CONTENT PLOT.pdf`: The file on the NAS was 0 bytes; the 5-episode plot and 3 practical steps per episode were reconstructed verbatim from Coach Hairul's recorded takes across `EP1`–`EP5`.

## 5-Episode Curriculum & Mandatory Series Trailer

| ID | Episode Title | Core Problem & Root Cause | 3 Practical Takeaways (from speech) |
| --- | --- | --- | --- |
| **EP00 (Trailer)** | **Siri Masterclass: 5 Kunci Tenaga & Kecergasan Lelaki 40-an** | Highlight clip from **every episode (`EP01`–`EP05`)** + 5-Episode Curriculum Card | Overview of Protein, Jisim Otot, Gaya Hidup Aktif, Tidur & Stres, Kawalan Kalori |
| **EP01** | **Protein Harian & Tenaga Lelaki Sibuk** | Makan ikut selera seperti umur 20-an; kurang protein menyebabkan otot susut, metabolisme & tenaga turun | 1. Pastikan setiap hidangan tinggi protein (ayam, ikan, telur, daging)<br>2. Kurangkan makanan ultra-proses & minuman manis<br>3. Sesuaikan karbohidrat mengikut tahap aktiviti harian |
| **EP02** | **Jaga Jisim Otot: Latihan Beban vs Kardio** | Selepas umur 40 otot cepat susut; terlalu fokus kardio sahaja tanpa latihan beban menurunkan jisim otot & metabolisme | 1. Masukkan latihan beban (*strength training*) 2–4 kali seminggu<br>2. Fokus senaman kompaun (*squat, deadlift, bench press, lat pulldown*)<br>3. Pantau progres dari segi tenaga, *mood*, selera & *fitting* baju |
| **EP03** | **Gaya Hidup Aktif & Langkah Harian (NEAT)** | Harapkan gym semata-mata tetapi kurang pergerakan harian di luar waktu senaman | 1. Tingkatkan kiraan langkah harian secara berperingkat (sasaran 6,000–10,000 langkah)<br>2. Jadikan aktiviti harian sebagai *booster* (parkir jauh sedikit, naik tangga)<br>3. Gabungkan latihan beban, kardio & pergerakan harian |
| **EP04** | **Tidur Berkualiti, Recovery & Kawalan Stres** | Protein & gym cukup tetapi gagal kerana kurang tidur dan stres tinggi mengganggu pemulihan (*recovery*) | 1. Dapatkan tidur berkualiti sekurang-kurangnya 6–8 jam sehari<br>2. Sediakan hari *active recovery* (*brisk walk*, regangan, yoga)<br>3. Urus tekanan kerja & harian supaya hormon kekal seimbang |
| **EP05** | **Kawal Kalori & Konsistensi Jangka Panjang** | Fokus satu perkara sahaja (gym/lari) tetapi abaikan keseimbangan kalori masuk vs keluar (minuman manis seperti teh tarik/kopi tarik) | 1. Ambil kira keseimbangan kalori masuk dan kalori keluar setiap hari<br>2. Kurangkan kalori cecair manis (teh tarik, kopi tarik)<br>3. Kekalkan gabungan latihan beban 2–4 kali seminggu & protein mencukupi |

## Output Formats (`masterclass-editor`)
1. **16:9 (`1920x1080`, 25 fps)**:
   - `SSC-MC_EP00_Trailer_16x9.mp4` (Mandatory Series Trailer with clips from `EP01`–`EP05`)
   - `SSC-MC_EP01_Protein_16x9.mp4` through `SSC-MC_EP05_Kalori_16x9.mp4` (5 Full Masterclass Episodes with Chapter Title Cards, 60/40 Split-Screen Slide/Diagram Callouts, Numbered Key-Takeaway Cards, sentence subtitles + `.srt`/`.vtt` sidecars)
2. **9:16 (`1080x1920`, 25 fps)**:
   - `SSC-MC_EP00_Trailer_9x16.mp4` (Vertical Series Trailer with clips from `EP01`–`EP05`)
   - `SSC-MC_EP01_Protein_9x16.mp4` through `SSC-MC_EP05_Kalori_9x16.mp4` (5 Vertical Episode Cutdowns with Hook Headline, Safe-Zone Callout Card, Word-by-Word Burned Captions, Numbered Key-Takeaway Card, and End Card)

## Creative & Brand Direction (`ssclinic` / SuamiSihat Masterclass)
- Palette: Deep Prussian Navy (`#022057`), Clinical Navy (`#0F4C75`), Pure White (`#FFFFFF`), Warm Clinic Gold (`#F4A261`), Azure Energy (`#21A1F7`) following 60:30:10 balance.
- Lower third: `Coach Hairul` / `Personal Trainer · SuamiSihat Masterclass`
- End card: SuamiSihat Clinic / SuamiSihat Masterclass logo + neutral closing line `Kekal Konsisten · Panduan Gaya Hidup Sihat SuamiSihat Masterclass` (no clinic solicitation CTA, no prices/offers).

## Delivery
- Render locally in `batches/masterclass-hairul/renders/`
- Run `check_brand.py`, `check_sync.py`, and `check_layout.py` on all outputs
- Deliver to: `\\Ssnas\drm\SS-DTC\deliver\masterclass-hairul\`

# Safe zones (1080x1920)
Verified against third-party guides on 2026-10-21 (not an official Meta or TikTok page; re-check each quarter and replace with the official spec if found):
- Instagram/Facebook Reels (ads): top 14% (about 270 px), bottom 35% (about 672 px), left/right 6% (about 65 px). Reels ads with a disclaimer: keep bottom 768 px clear.
- Stories: top 14%, bottom 20% (about 384 px), sides 6%.
- TikTok: top 240 px, bottom 660 px, left/right 120 px; right-hand action column about 300 px wide from y = 840 down.
- Sources: adnova.ai/blogs/meta-ad-safe-zones-guide, upload-post.com/tools/safe-zone-checker.
Combined safe rectangle for Reels + TikTok: x 120-960, y 270-1248 (y 270-1152 when a disclaimer shows).
Check every overlay for overflow and safe-zone problems in the frame-grid QA. See `dtc-broll`.

# Windows setup (PowerShell). Review before running. Needs winget (Windows 10/11).
$ErrorActionPreference = "Stop"
Write-Host "== DMR Reels Engine setup =="
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Python.Python.3.11 -e
winget install --id Git.Git -e
Write-Host "Close and reopen PowerShell if python/ffmpeg are not found, then re-run this script."
python -m pip install --user numpy scipy opencv-python openai-whisper "rembg[cpu]"
if (-not (Test-Path config.env)) { Copy-Item config.example.env config.env }
Write-Host "Install Poppins font for all users (brands/<slug>/ or the Design System fonts). Keep file names short (Windows path limits)."
python scripts/install_skills.py
python setup/check_env.py

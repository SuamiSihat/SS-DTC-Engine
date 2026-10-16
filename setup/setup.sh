#!/usr/bin/env bash
# Mac/Linux setup. Review before running. Installs tools, then runs the self-test.
set -e
echo "== DMR Reels Engine setup =="
if [ "$(uname)" = "Darwin" ]; then
  command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
  brew install ffmpeg node python git
else
  sudo apt-get update && sudo apt-get install -y ffmpeg nodejs npm python3 python3-pip git
fi
python3 -m pip install --user numpy scipy opencv-python openai-whisper "rembg[cpu]"
[ -f config.env ] || cp config.example.env config.env
echo "Install Poppins font system-wide (brands/<slug>/ or the Design System fonts)."
python3 scripts/install_skills.py
python3 setup/check_env.py

#!/usr/bin/env bash
# Strigano setup for Kali / Debian. Installs the external forensics tools and
# the strigano package. Safe to re-run.
#
#   chmod +x scripts/setup-kali.sh
#   ./scripts/setup-kali.sh
#
set -euo pipefail

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

echo "[*] Installing system packages (apt)..."
$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv pipx \
  libimage-exiftool-perl binwalk foremost steghide \
  tesseract-ocr ffmpeg libsndfile1 \
  ruby ruby-dev build-essential

echo "[*] Installing zsteg (ruby gem)..."
if ! command -v zsteg >/dev/null 2>&1; then
  $SUDO gem install zsteg --no-document
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Installing strigano from ${REPO_DIR} ..."
if command -v pipx >/dev/null 2>&1; then
  pipx install --force "${REPO_DIR}"
  echo "[+] Installed via pipx. The 'strigano' command is on your PATH."
else
  python3 -m venv "${REPO_DIR}/.venv"
  "${REPO_DIR}/.venv/bin/pip" install --upgrade pip
  "${REPO_DIR}/.venv/bin/pip" install -e "${REPO_DIR}"
  echo "[+] Installed into ${REPO_DIR}/.venv"
  echo "    Run with: ${REPO_DIR}/.venv/bin/strigano check"
fi

echo
echo "[*] Verifying external tools:"
strigano check 2>/dev/null || "${REPO_DIR}/.venv/bin/strigano" check
echo
echo "[+] Done. Start the web UI with:  strigano serve"

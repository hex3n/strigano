"""Central configuration, resolved from the package location and environment.

Nothing here depends on the current working directory, so the tool behaves the
same whether launched with ``uvicorn``, ``python -m strigano.cli`` or the
installed ``strigano`` console script.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "web" / "static"
TEMPLATES_DIR = PACKAGE_DIR / "web" / "templates"


def _output_dir() -> Path:
    """Where generated artifacts (bitplanes, carved files, spectrograms) go.

    Defaults to ``strigano_output`` under the current directory so a pip
    installed copy never writes into site-packages. Override with
    ``STRIGANO_OUTPUT``.
    """
    env = os.environ.get("STRIGANO_OUTPUT")
    base = Path(env) if env else Path.cwd() / "strigano_output"
    return base.resolve()


OUTPUT_DIR = _output_dir()

# Upload ceiling for the web UI, in bytes. Override with STRIGANO_MAX_UPLOAD.
MAX_UPLOAD_BYTES = int(os.environ.get("STRIGANO_MAX_UPLOAD", str(100 * 1024 * 1024)))

# External tool command names. Each is overridable with STRIGANO_<TOOL>, e.g.
# STRIGANO_EXIFTOOL=/opt/exiftool/exiftool, which is how you point the Windows
# PC at a specific binary without touching PATH.
TOOLS: dict[str, str] = {
    "exiftool": os.environ.get("STRIGANO_EXIFTOOL", "exiftool"),
    "binwalk": os.environ.get("STRIGANO_BINWALK", "binwalk"),
    "foremost": os.environ.get("STRIGANO_FOREMOST", "foremost"),
    "steghide": os.environ.get("STRIGANO_STEGHIDE", "steghide"),
    "zsteg": os.environ.get("STRIGANO_ZSTEG", "zsteg"),
    "tesseract": os.environ.get("STRIGANO_TESSERACT", "tesseract"),
    "ffprobe": os.environ.get("STRIGANO_FFPROBE", "ffprobe"),
    "ffmpeg": os.environ.get("STRIGANO_FFMPEG", "ffmpeg"),
}

# Flag formats the OCR and metadata scanners look for. Add the event format at
# the start of a CTF, or set STRIGANO_FLAG_PREFIXES="fort,myctf" to extend it.
_DEFAULT_FLAG_PREFIXES = [
    "flag", "ctf", "picoctf", "htb", "inctf", "shell", "fort",
]
_env_prefixes = os.environ.get("STRIGANO_FLAG_PREFIXES", "")
FLAG_PREFIXES = _DEFAULT_FLAG_PREFIXES + [
    p.strip() for p in _env_prefixes.split(",") if p.strip()
]

# Default subprocess timeout in seconds for external tools.
TOOL_TIMEOUT = int(os.environ.get("STRIGANO_TOOL_TIMEOUT", "60"))

# Spectrogram time-resolution cap. The heatmap is downsampled to at most this
# many time columns, so the generated HTML stays small no matter how long the
# clip is. Override with STRIGANO_SPECTRO_MAXCOLS.
SPECTRO_MAX_COLS = int(os.environ.get("STRIGANO_SPECTRO_MAXCOLS", "1500"))

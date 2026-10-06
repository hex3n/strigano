"""Strigano: a stego and forensics triage multi-tool for CTFs.

Image and audio analysis with a shared core, exposed through both a FastAPI
web UI and a command line interface. External tools (exiftool, binwalk,
foremost, steghide, zsteg, tesseract, ffprobe) are optional: when one is not
installed the relevant section degrades gracefully instead of failing the run.
"""

__version__ = "2.0.0"

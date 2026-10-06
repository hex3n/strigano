"""Orchestration: the single entry points the web UI and CLI both call."""

from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path

from .. import config
from . import external, images, ocr
from .audio import audio_strings, build_spectrogram_html, ffprobe_metadata
from .flags import find_flags
from .result import AudioReport, ImageReport


def secure_filename(name: str) -> str:
    """Reduce an arbitrary upload name to a safe single path component."""
    name = os.path.basename((name or "").replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    return (name or "upload")[:200]


def _new_run_dir(display_name: str) -> tuple[str, Path]:
    """Create a unique output subdirectory for one analysis run."""
    stem = secure_filename(Path(display_name).stem) or "run"
    run_id = f"{stem}-{uuid.uuid4().hex[:8]}"
    run_dir = config.OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_id, run_dir


def _scan_text_flags(*chunks: str) -> list[str]:
    found: list[str] = []
    for chunk in chunks:
        for flag in find_flags(chunk):
            if flag not in found:
                found.append(flag)
    return found


def analyze_image(source_path: str, display_name: str, password: str = "") -> ImageReport:
    run_id, run_dir = _new_run_dir(display_name)
    safe_name = secure_filename(display_name)
    local = run_dir / safe_name
    shutil.copyfile(source_path, local)
    local_str = str(local)

    report = ImageReport(filename=safe_name, output_prefix=run_id)

    # Metadata and exiftool.
    report.metadata = external.exiftool_metadata(local_str)
    report.tools.append(external.exiftool_text(local_str))

    # Bitplanes and superimposed views (pure Pillow/numpy, always available).
    try:
        report.bitplanes, report.extras = images.save_bitplanes(local_str, run_dir)
        report.superimposed = images.superimpose_bitplanes(run_dir)
    except Exception as exc:
        report.errors.append(f"Bitplane extraction failed: {exc}")

    # Appended data after EOF.
    try:
        report.appended_file = images.extract_appended_data(local_str, run_dir)
    except Exception as exc:
        report.errors.append(f"Appended-data scan failed: {exc}")

    # Strings.
    try:
        report.strings_ascii, report.strings_utf16 = images.extract_strings(local_str)
    except Exception as exc:
        report.errors.append(f"String extraction failed: {exc}")

    # OCR flags over the generated bitplanes.
    bitplane_paths = [str(run_dir / name) for name in report.bitplanes]
    ocr_hits = ocr.scan_images_for_flags(bitplane_paths)
    # Report image paths relative to the output root for linking.
    report.flags = [
        (str(Path(p).relative_to(config.OUTPUT_DIR)).replace("\\", "/"), flag)
        for p, flag in ocr_hits
    ]

    # Text-based flags from metadata values and strings.
    meta_text = "\n".join(str(v) for v in report.metadata.values())
    for flag in _scan_text_flags(meta_text, "\n".join(report.strings_ascii)):
        pair = ("(text)", flag)
        if pair not in report.flags:
            report.flags.append(pair)

    # External carving/stego tools.
    report.tools.append(external.binwalk(local_str, run_dir))
    report.tools.append(external.foremost(local_str, run_dir))
    report.tools.append(external.steghide(local_str, run_dir, password))
    report.tools.append(external.zsteg(local_str))

    return report


def analyze_audio(source_path: str, display_name: str) -> AudioReport:
    run_id, run_dir = _new_run_dir(display_name)
    safe_name = secure_filename(display_name)
    local = run_dir / safe_name
    shutil.copyfile(source_path, local)
    local_str = str(local)

    report = AudioReport(filename=safe_name, output_prefix=run_id, audio_file=safe_name)

    report.metadata = ffprobe_metadata(local_str)

    try:
        report.spectrogram_file = build_spectrogram_html(local_str, run_dir)
    except Exception as exc:
        report.errors.append(f"Spectrogram failed: {exc}")

    try:
        report.strings = audio_strings(local_str)
    except Exception as exc:
        report.errors.append(f"String extraction failed: {exc}")

    report.flags = _scan_text_flags(report.metadata, "\n".join(report.strings))
    return report

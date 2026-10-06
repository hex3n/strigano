"""Image operations that need no external tools: Pillow and numpy only."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

COLORS = ("red", "green", "blue")


def save_bitplanes(
    image_path: str | Path, out_dir: str | Path
) -> tuple[list[str], list[str]]:
    """Write the 8 bitplanes per RGB channel plus gray/channel variants.

    Returns ``(bitplane_names, extra_names)``, each relative to ``out_dir``.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    arr = np.asarray(img)  # shape (H, W, 3), uint8

    written: list[str] = []
    for ci, color in enumerate(COLORS):
        channel = arr[:, :, ci]
        for bit in range(8):
            plane = (((channel >> bit) & 1) * 255).astype(np.uint8)
            name = f"{color}_bit{bit}.png"
            Image.fromarray(plane, mode="L").save(out / name)
            written.append(name)

    # Grayscale and per-channel helper views, handy for quick visual stego.
    gray = img.convert("L")
    gray.save(out / "gray.png")
    ImageOps.invert(gray).save(out / "gray_inverted.png")
    ImageEnhance.Contrast(gray).enhance(3.0).save(out / "gray_contrast.png")
    extras = ["gray.png", "gray_inverted.png", "gray_contrast.png"]

    r, g, b = img.split()
    for short, channel in zip(("r", "g", "b"), (r, g, b)):
        channel.save(out / f"{short}_channel.png")
        ImageOps.invert(channel).save(out / f"{short}_inverted.png")
        extras += [f"{short}_channel.png", f"{short}_inverted.png"]

    return written, extras


def superimpose_bitplanes(out_dir: str | Path) -> list[str]:
    """Merge the three same-bit planes back into one RGB image per bit."""
    out = Path(out_dir)
    written: list[str] = []
    for bit in range(8):
        try:
            r = Image.open(out / f"red_bit{bit}.png").convert("L")
            g = Image.open(out / f"green_bit{bit}.png").convert("L")
            b = Image.open(out / f"blue_bit{bit}.png").convert("L")
        except FileNotFoundError:
            continue
        name = f"superimposed_bit{bit}.png"
        Image.merge("RGB", (r, g, b)).save(out / name)
        written.append(name)
    return written


def extract_appended_data(image_path: str | Path, out_dir: str | Path) -> str | None:
    """Carve any bytes that follow the real end of a PNG or JPEG.

    JPEG can contain several ``FFD9`` markers (thumbnails), so the last one is
    treated as the true end of image rather than the first.
    """
    path = Path(image_path)
    data = path.read_bytes()
    ext = path.suffix.lower()

    if ext == ".png":
        iend = b"\x49\x45\x4e\x44\xae\x42\x60\x82"  # IEND chunk + CRC
        idx = data.find(iend)
        end = idx + len(iend) if idx != -1 else -1
    elif ext in (".jpg", ".jpeg"):
        idx = data.rfind(b"\xff\xd9")
        end = idx + 2 if idx != -1 else -1
    else:
        return None

    if end == -1 or end >= len(data):
        return None

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "appended.bin").write_bytes(data[end:])
    return "appended.bin"


def extract_strings(
    filepath: str | Path, min_length: int = 4
) -> tuple[list[str], list[str]]:
    """Return (ASCII, UTF-16LE) printable strings of at least ``min_length``."""
    ascii_re = re.compile(rb"[\x20-\x7e]{%d,}" % min_length)
    utf16_re = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % min_length)

    data = Path(filepath).read_bytes()
    ascii_found = [m.decode("ascii", "ignore") for m in ascii_re.findall(data)]
    utf16_found = [m.decode("utf-16le", "ignore") for m in utf16_re.findall(data)]
    return ascii_found, utf16_found

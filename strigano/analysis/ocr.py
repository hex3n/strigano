"""OCR-based flag detection over generated bitplanes.

Both the ``pytesseract`` Python package and the ``tesseract`` binary are
optional. If either is missing, scanning returns no hits rather than raising,
so a box without tesseract still produces a full report minus the OCR pass.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .. import tools
from .flags import FLAG_REGEX

try:  # pytesseract is optional
    import pytesseract

    _HAVE_PYTESSERACT = True
except Exception:  # pragma: no cover - import guard
    pytesseract = None
    _HAVE_PYTESSERACT = False

_WHITELIST = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}!?$@.-"
)


def ocr_available() -> bool:
    """True only when both the binding and the tesseract binary are present."""
    return _HAVE_PYTESSERACT and tools.is_available("tesseract")


def _preprocess(img_path: str) -> Image.Image | None:
    try:
        img = Image.open(img_path).convert("L")
        img = ImageOps.invert(img)
        return img.point(lambda x: 255 if x > 100 else 0)
    except Exception:
        return None


def scan_images_for_flags(image_paths: list[str]) -> list[tuple[str, str]]:
    """Run OCR over each image and return ``(image_path, flag)`` hits."""
    if not ocr_available():
        return []

    # Point pytesseract at the resolved binary so PATH quirks do not bite.
    binary = tools.resolve("tesseract")
    if binary:
        pytesseract.pytesseract.tesseract_cmd = binary

    config = f"--psm 6 -c tessedit_char_whitelist={_WHITELIST}"
    detected: list[tuple[str, str]] = []
    seen: set[str] = set()

    for img_path in image_paths:
        if not Path(img_path).exists():
            continue
        img = _preprocess(img_path)
        if img is None:
            continue
        try:
            width, height = img.size
            passes = [
                pytesseract.image_to_string(img, config=config),
                pytesseract.image_to_string(ImageOps.invert(img), config=config),
                pytesseract.image_to_string(
                    img.crop((0, 0, width // 2, height // 2)), config=config
                ),
            ]
        except Exception:
            continue

        for text in passes:
            for match in FLAG_REGEX.findall(text):
                clean = match.strip()
                if len(clean) < 6 or "{" not in clean or "}" not in clean:
                    continue
                if clean not in seen:
                    seen.add(clean)
                    detected.append((img_path, clean))

    return detected

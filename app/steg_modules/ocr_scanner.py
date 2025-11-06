from typing import List, Tuple
from PIL import Image, ImageOps
import pytesseract
import re
import os
from Levenshtein import distance as levenshtein

def preprocess_image(img_path: str) -> Image.Image:
    """
    Preprocess image for better OCR:
    - Convert to grayscale
    - Invert colors
    - Binarize (thresholding)
    """
    try:
        img = Image.open(img_path).convert("L")
        img = ImageOps.invert(img)
        img = img.point(lambda x: 255 if x > 100 else 0)
        return img
    except Exception as e:
        print(f"[!] Error preprocessing {img_path}: {e}")
        return None

def scan_images_for_flags(image_paths: List[str]) -> List[Tuple[str, str]]:
    flag_regex = re.compile(
        r"(flag\{.*?\}|picoCTF\{.*?\}|HTB\{.*?\}|CTF\{.*?\}|FLAG\{.*?\}|SHELL\{.*?\}|synt\{.*?\})",
        re.IGNORECASE
    )
    detected = []
    seen_flags = set()
    whitelist = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}!?$@.-"

    for img_path in image_paths:
        try:
            img = preprocess_image(img_path)
            if img is None:
                continue

            config = f'--psm 6 -c tessedit_char_whitelist={whitelist}'

            text_normal = pytesseract.image_to_string(img, config=config)
            text_inverted = pytesseract.image_to_string(ImageOps.invert(img), config=config)
            width, height = img.size
            cropped = img.crop((0, 0, width // 2, height // 2))
            text_crop = pytesseract.image_to_string(cropped, config=config)

            combined_text = "\n".join([text_normal, text_inverted, text_crop])
            matches = flag_regex.findall(combined_text)

            for match in matches:
                clean = match.strip()
                # Simple heuristics to filter garbage
                if len(clean) < 12:
                    continue
                if not ("{" in clean and "}" in clean):
                    continue
                if any(c.isdigit() for c in clean) and any(c.isalpha() for c in clean):
                    if clean not in seen_flags:
                        seen_flags.add(clean)
                        detected.append((img_path, clean))

        except Exception as e:
            print(f"[!] OCR error on {img_path}: {e}")

    return detected



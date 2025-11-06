import cv2
import pytesseract
import re
import os
from PIL import Image
import numpy as np

# Match multiple CTF flag patterns (customize as needed)
FLAG_REGEX = re.compile(r'(ctf|flag|picoctf|inctf|htb)\{[^\}]+\}', re.IGNORECASE)

def scan_bitplanes_for_flags(original_img_path, output_dir="static/bitplanes"):
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(original_img_path)
    b, g, r = cv2.split(img)

    flagged_images = []
    found_flags = []

    for color_name, channel in zip(["blue", "green", "red"], [b, g, r]):
        for bit in range(8):
            # Extract bitplane
            bit_mask = 1 << bit
            plane = cv2.bitwise_and(channel, bit_mask)
            bit_img = np.where(plane > 0, 255, 0).astype(np.uint8)

            # Stack to 3 channels so pytesseract can read it
            bitplane_3ch = cv2.merge([bit_img] * 3)

            # Save the image
            plane_filename = f"{color_name}_bit{bit}.png"
            full_path = os.path.join(output_dir, plane_filename)
            cv2.imwrite(full_path, bitplane_3ch)

            # OCR
            pil_img = Image.fromarray(bitplane_3ch)
            ocr_result = pytesseract.image_to_string(pil_img).strip()

            # Check for flags
            matches = FLAG_REGEX.findall(ocr_result)
            if matches:
                flagged_images.append(plane_filename)
                found_flags.append((plane_filename, ocr_result))

    return flagged_images, found_flags

import os
from PIL import Image, ImageChops

def superimpose_bitplanes(output_dir):
    for bit in range(8):  # 0 through 7
        try:
            r = Image.open(os.path.join(output_dir, f"red_bit{bit}.png")).convert("L")
            g = Image.open(os.path.join(output_dir, f"green_bit{bit}.png")).convert("L")
            b = Image.open(os.path.join(output_dir, f"blue_bit{bit}.png")).convert("L")

            rgb = Image.merge("RGB", (r, g, b))
            rgb.save(os.path.join(output_dir, f"superimposed_bit{bit}.png"))
        except FileNotFoundError:
            print(f"[!] Missing bitplane files for bit{bit}, skipping.")

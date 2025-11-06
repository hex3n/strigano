from PIL import Image, ImageEnhance, ImageOps
import os

def extract_rgb_bitplanes(image_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    img = Image.open(image_path).convert('RGB')
    r, g, b = img.split()

    for i in range(8):
        for color, channel in zip(['red', 'green', 'blue'], [r, g, b]):
            bitplane = channel.point(lambda p: (p >> i) & 1 and 255)
            filename = os.path.join(output_dir, f"{color}_bit{i}.png")
            bitplane.save(filename)

    # Add grayscale variants
    gray = img.convert('L')
    gray.save(os.path.join(output_dir, "gray.png"))
    ImageOps.invert(gray).save(os.path.join(output_dir, "gray_inverted.png"))
    ImageEnhance.Contrast(gray).enhance(3.0).save(os.path.join(output_dir, "gray_contrast.png"))

    for color, channel in zip(['r', 'g', 'b'], [r, g, b]):
        channel.save(os.path.join(output_dir, f"{color}_channel.png"))
        ImageOps.invert(channel).save(os.path.join(output_dir, f"{color}_inverted.png"))

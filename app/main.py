from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.steg_modules.rgb_bitplanes import extract_rgb_bitplanes
from app.steg_modules.exif_metadata import extract_exif_metadata
from app.steg_modules.binwalk_runner import run_binwalk
from app.steg_modules.ocr_scanner import scan_images_for_flags
from app.steg_modules.appended_data import extract_appended_data
from app.steg_modules.strings_extractor import extract_strings
from app.steg_modules.foremost_runner import run_foremost
from app.steg_modules.steghide_runner import run_steghide
from app.steg_modules.zsteg_runner import run_zsteg
from app.steg_modules.exiftool_runner import run_exiftool
from fastapi import Form


import shutil
import base64
import codecs
import binascii

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="/static/css/style.css">
        <title>Strigano</title>
    </head>
    <body>
        <h2>Upload an image for Steganography Analysis</h2>
        <form action="/upload" enctype="multipart/form-data" method="post">
            <input name="file" type="file"><br>
            <input name="password" type="text" placeholder="Optional password"><br>
            <input type="submit" value="Upload">
        </form>

        <h2 style="color: #66ccff;">Upload an audio file for Forensics Analysis</h2>
        <form action="/audio" method="post" enctype="multipart/form-data" style="border: 1px solid #66ccff; padding: 20px; margin-bottom: 30px;">
        <input type="file" name="audio_file" accept=".wav,.mp3,.flac" style="border: 1px solid #66ccff; color: #66ccff;" required>
        <br><br>
        <input type="submit" value="Upload Audio" style="border: 1px solid #66ccff; color: #66ccff;">
        </form>

    </body>
    </html>
    """

    
# --- Encoding detectors ---
def try_base64_decode(s):
    try:
        decoded = base64.b64decode(s).decode("utf-8")
        if decoded.isprintable():
            return ("Base64", decoded)
    except Exception:
        pass
    return None

def try_hex_decode(s):
    try:
        cleaned = s.replace(" ", "")
        if len(cleaned) % 2 == 0:
            decoded = binascii.unhexlify(cleaned).decode("utf-8")
            if decoded.isprintable():
                return ("Hex", decoded)
    except Exception:
        pass
    return None

import re

def try_rot13_decode(s):
    try:
        # Skip if string has special characters or digits (not typical ROT13 candidates)
        if not re.fullmatch(r"[A-Za-z/\-_\.]+", s):
            return None

        decoded = codecs.decode(s, "rot_13")

        # Require that decoded has at least one word-like token
        if decoded != s and re.search(r"[aeiouAEIOU]", decoded):
            return ("ROT13", decoded)
    except Exception:
        pass
    return None



@app.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile = File(...), password: str = Form(default="")):
    filename = file.filename
    upload_path = f"static/output/{filename}"
    
    # Save uploaded file
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract metadata and bitplanes
    metadata = extract_exif_metadata(upload_path)
    extract_rgb_bitplanes(upload_path, "static/output")

    from app.steg_modules.superimposer import superimpose_bitplanes
    superimpose_bitplanes("static/output")

    # Binwalk HTML starts empty
    binwalk_html = ""

    # Appended Data
    appended_file = extract_appended_data(upload_path, "static/output")
    if appended_file:
        binwalk_html += f"<p>🚨 Appended data detected: <a href='/static/output/{appended_file}' download>{appended_file}</a></p>"

    # Collect bitplane paths
    bitplane_paths = [
        f"static/output/{color}_bit{bit}.png"
        for color in ["red", "green", "blue"]
        for bit in range(8)
    ] + [
        "static/output/gray.png", "static/output/gray_inverted.png", "static/output/gray_contrast.png",
        "static/output/r_channel.png", "static/output/g_channel.png", "static/output/b_channel.png",
        "static/output/r_inverted.png", "static/output/g_inverted.png", "static/output/b_inverted.png"
    ]

    # OCR
    detected_pairs = scan_images_for_flags(bitplane_paths)
    detected_flags = [flag for _, flag in detected_pairs]
    flagged_images = {img for img, _ in detected_pairs}
    flagged_dict = dict(detected_pairs)

    # Binwalk on full image
    extracted_files, binwalk_output_full = run_binwalk(upload_path, "static/output")
    binwalk_html += "<h3>Binwalk</h3><pre style='background-color:#111;padding:10px;border:1px solid #66ff99;'>"
    binwalk_html += binwalk_output_full + "</pre>"

    if extracted_files:
        binwalk_html += "<p>Extracted Files:</p><ul>"
        for f in extracted_files:
            binwalk_html += f"<li><a href='/static/output/{f}' download>{f}</a></li>"
        binwalk_html += "</ul>"
    else:
        binwalk_html += "<p>No extracted files.</p>"
    binwalk_html += "<hr>"

    # Run Foremost
    foremost_files, foremost_log = run_foremost(upload_path, "static/output")

    foremost_html = "<h3 style='color:#99ff66;'>Foremost</h3><pre style='background-color:#111;padding:10px;border:1px solid #66ff99;'>"
    if foremost_files:
        foremost_html += f"<p><a href='/static/output/foremost/audit.txt' download>📄 Download audit log</a></p>"
        foremost_html += "<ul>"
        for f in foremost_files:
            foremost_html += f"<li><a href='/static/output/{f}' download>{f}</a></li>"
        foremost_html += "</ul>"
    else:
        foremost_html += "No files recovered by Foremost."
    foremost_html += "</pre><hr>"

    # Steghide (with password)
    steghide_success, steghide_msg, steghide_file = run_steghide(upload_path, "static/output", password=password)

    steghide_html = "<h3 style='color:#ff6699;'>Steghide</h3><pre style='background-color:#111;padding:10px;border:1px solid #ff6699;'>"
    if steghide_success and steghide_file:
        steghide_html += f"{steghide_msg}<br><a href='/static/output/{steghide_file}' download>📥 Download extracted file</a>"
    else:
        steghide_html += steghide_msg
    steghide_html += "</pre><hr>"

    # Run zsteg
    zsteg_output = run_zsteg(upload_path)

    zsteg_html = "<h3>Zsteg</h3><pre style='background-color:#111;padding:10px;border:1px solid #66ff99;'>"
    zsteg_html += zsteg_output if zsteg_output else "No output from zsteg."
    zsteg_html += "</pre><hr>"

    # Strings
    ascii_strings, unicode_strings = extract_strings(upload_path)

    strings_html = "<h3>Strings (ASCII)</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
    strings_html += "\n".join(ascii_strings[:100])
    strings_html += "</pre>"

    if unicode_strings:
        strings_html += "<h3>Strings (UTF-16LE)</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
        strings_html += "\n".join(unicode_strings[:50])
        strings_html += "</pre>"

    strings_html += "<hr>"

    # Flags
    flag_html = ""
    if detected_flags:
        flag_html += "<h2 style='color:#ff66cc;'>🎯 Detected Flags (OCR)</h2><ul>"
        for flag in detected_flags:
            flag_html += f"<li><code>{flag}</code></li>"
        flag_html += "</ul><hr>"

    # Metadata + decoding
    metadata_html = "<h3>Exif Metadata</h3><table border='1' cellpadding='4'>"
    for key, value in metadata.items():
        decoded_note = ""
        if isinstance(value, str) and len(value) >= 8:
            for decoder in (try_base64_decode, try_hex_decode, try_rot13_decode):
                result = decoder(value)
                if result:
                    method, decoded = result
                    decoded_note += f"<br><span style='color:#cc66ff;'>ENCODING DETECTED ({method}). DECODED TEXT: {decoded}</span>"
                    break
        metadata_html += f"<tr><td><b>{key}</b></td><td>{value}{decoded_note}</td></tr>"
    metadata_html += "</table><hr>"

    # ExifTool
    exiftool_output = run_exiftool(upload_path)
    exiftool_html = "<h3>ExifTool Output</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
    exiftool_html += exiftool_output + "</pre><hr>"

    # Bitplanes
    bitplane_html = ""
    for color in ["red", "green", "blue"]:
        bitplane_html += f"""
        <h3>{color.capitalize()} Channel</h3>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px;">
        """
        for bit in range(8):
            plane_filename = f"static/output/{color}_bit{bit}.png"
            highlight = "5px solid #ff66cc" if plane_filename in flagged_images else "1px solid #ccc"
            flag_caption = (
                f"<br><small style='color:#ff66cc;'>🔍 {flagged_dict[plane_filename]}</small>"
                if plane_filename in flagged_dict else ""
            )
            bitplane_html += f"""
            <div style="text-align:center;">
                <img src="/{plane_filename}" class="zoomable" onclick="zoomImage('/{plane_filename}')" style="width: 350px; height: auto; border: {highlight};">
                <small>{color}_bit{bit}</small>
                {flag_caption}
            </div>
            """
        bitplane_html += "</div><hr>"

    # Superimposed
    super_html = """
    <h3>Superimposed RGB Channels</h3>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px;">
    """
    for bit in range(8):
        filename = f"static/output/superimposed_bit{bit}.png"
        super_html += f"""
        <div style="text-align:center;">
            <img src="/{filename}" class="zoomable" onclick="zoomImage('/{filename}')" style="width: 350px; height: auto; border: 2px solid #888;">
            <small>superimposed_bit{bit}</small>
        </div>
        """
    super_html += "</div><hr>"

    # Return HTML
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="/static/css/style.css">
        <title>Strigano</title>
        <style>
            img.zoomable:hover {{ cursor: zoom-in; }}
            #zoom-overlay {{
                display: none; position: fixed; top: 0; left: 0;
                width: 100vw; height: 100vh;
                background-color: rgba(0,0,0,0.95);
                justify-content: center; align-items: center; z-index: 9999;
            }}
            #zoom-overlay img {{ max-width: 95%; max-height: 95%; border: 4px solid white; }}
        </style>
        <script>
            function zoomImage(src) {{
                const overlay = document.getElementById("zoom-overlay");
                const zoomImg = document.getElementById("zoom-img");
                zoomImg.src = src;
                overlay.style.display = "flex";
            }}
            function closeZoom() {{
                document.getElementById("zoom-overlay").style.display = "none";
            }}
        </script>
    </head>
    <body>
        {flag_html}
        <h2>File uploaded: {filename}</h2>
        {metadata_html}
        {exiftool_html}
        {bitplane_html}
        {super_html}
        {binwalk_html}
        {foremost_html}
        {steghide_html}
        {zsteg_html}
        {strings_html}
        <a href="/">Upload another</a>
        <div id="zoom-overlay" onclick="closeZoom()"><img id="zoom-img" src=""></div>
    </body>
    </html>
    """)


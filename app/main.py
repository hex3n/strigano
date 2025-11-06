from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
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
import shutil, base64, codecs, binascii, re, os

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
            <input name="file" type="file" accept="image/*" required><br><br>
            <input name="password" type="text" placeholder="Optional password"><br><br>
            <input type="submit" value="Upload">
        </form>

        <h2 style="color: #66ccff;">Upload an audio file for Forensics Analysis</h2>
        <form action="/audio" method="post" enctype="multipart/form-data"
              style="border: 1px solid #66ccff; padding: 20px; margin-bottom: 30px;">
            <input type="file" name="file" accept=".wav,.mp3,.flac" required
                   style="border: 1px solid #66ccff; color: #66ccff;">
            <br><br>
            <input type="submit" value="Analyze Audio" style="border: 1px solid #66ccff; color: #66ccff;">
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


def try_rot13_decode(s):
    try:
        if not re.fullmatch(r"[A-Za-z/\-_\.]+", s):
            return None
        decoded = codecs.decode(s, "rot_13")
        if decoded != s and re.search(r"[aeiouAEIOU]", decoded):
            return ("ROT13", decoded)
    except Exception:
        pass
    return None


# ===========================
# IMAGE ANALYSIS ROUTE
# ===========================
@app.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile = File(...), password: str = Form(default="")):
    filename = file.filename
    upload_path = f"static/output/{filename}"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract metadata + bitplanes
    metadata = extract_exif_metadata(upload_path)
    extract_rgb_bitplanes(upload_path, "static/output")

    from app.steg_modules.superimposer import superimpose_bitplanes
    superimpose_bitplanes("static/output")

    binwalk_html = ""
    appended_file = extract_appended_data(upload_path, "static/output")
    if appended_file:
        binwalk_html += f"<p>🚨 Appended data detected: <a href='/static/output/{appended_file}' download>{appended_file}</a></p>"

    bitplane_paths = [
        f"static/output/{color}_bit{bit}.png"
        for color in ["red", "green", "blue"]
        for bit in range(8)
    ]

    detected_pairs = scan_images_for_flags(bitplane_paths)
    detected_flags = [flag for _, flag in detected_pairs]
    flagged_images = {img for img, _ in detected_pairs}
    flagged_dict = dict(detected_pairs)

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

    zsteg_output = run_zsteg(upload_path)
    zsteg_html = "<h3>Zsteg</h3><pre style='background-color:#111;padding:10px;border:1px solid #66ff99;'>"
    zsteg_html += zsteg_output if zsteg_output else "No output from zsteg."
    zsteg_html += "</pre><hr>"

    ascii_strings, unicode_strings = extract_strings(upload_path)
    strings_html = "<h3>Strings (ASCII)</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
    strings_html += "\n".join(ascii_strings[:100]) + "</pre>"

    if unicode_strings:
        strings_html += "<h3>Strings (UTF-16LE)</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
        strings_html += "\n".join(unicode_strings[:50]) + "</pre>"
    strings_html += "<hr>"

    flag_html = ""
    if detected_flags:
        flag_html += "<h2 style='color:#ff66cc;'>🎯 Detected Flags (OCR)</h2><ul>"
        for flag in detected_flags:
            flag_html += f"<li><code>{flag}</code></li>"
        flag_html += "</ul><hr>"

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

    exiftool_output = run_exiftool(upload_path)
    exiftool_html = "<h3>ExifTool Output</h3><pre style='max-height:300px; overflow:auto; background-color:#111; border:1px solid #66ff99; padding:10px;'>"
    exiftool_html += exiftool_output + "</pre><hr>"

    # Bitplanes
    bitplane_html = ""
    for color in ["red", "green", "blue"]:
        bitplane_html += f"<h3>{color.capitalize()} Channel</h3><div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;'>"
        for bit in range(8):
            plane_filename = f"static/output/{color}_bit{bit}.png"
            highlight = "5px solid #ff66cc" if plane_filename in flagged_images else "1px solid #ccc"
            flag_caption = f"<br><small style='color:#ff66cc;'>🔍 {flagged_dict.get(plane_filename, '')}</small>" if plane_filename in flagged_dict else ""
            bitplane_html += f"<div style='text-align:center;'><img src='/{plane_filename}' class='zoomable' style='width:350px; border:{highlight};'>{flag_caption}</div>"
        bitplane_html += "</div><hr>"

    # Superimposed
    super_html = "<h3>Superimposed RGB Channels</h3><div style='display:grid;grid-template-columns:repeat(4,1fr);gap:16px;'>"
    for bit in range(8):
        filename = f"static/output/superimposed_bit{bit}.png"
        super_html += f"<div style='text-align:center;'><img src='/{filename}' style='width:350px;border:2px solid #888;'><small>superimposed_bit{bit}</small></div>"
    super_html += "</div><hr>"

    return HTMLResponse(f"""
    <html><head><link rel='stylesheet' href='/static/css/style.css'><title>Strigano</title></head>
    <body>{flag_html}<h2>File uploaded: {filename}</h2>
    {metadata_html}{exiftool_html}{bitplane_html}{super_html}{binwalk_html}{foremost_html}{steghide_html}{zsteg_html}{strings_html}
    <a href='/'>Upload another</a></body></html>
    """)
# ===========================
# AUDIO FORENSICS ROUTE
# ===========================
@app.post("/audio", response_class=HTMLResponse)
async def audio_analysis(file: UploadFile = File(...)):
    filename = file.filename
    upload_path = f"static/output/{filename}"

    os.makedirs("static/output", exist_ok=True)
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    from app.steg_modules.audio_analyzer import analyze_audio
    results = analyze_audio(upload_path)

    html = f"<h2 style='color:#66ccff;'>Audio Forensics Report for {filename}</h2>"

    for key, value in results.items():
        if key == "SpectrogramPath" and isinstance(value, str) and value.endswith(".html"):
            rel = value.replace("static/", "")
            html += f"""
        <h3>Spectrogram</h3>
        <div style="text-align:center; margin:20px;">
            <div style="margin-bottom:10px;">
                <button onclick="toggleContrast()"
                        style="padding:6px 10px; background:#222; color:#66ccff; border:1px solid #66ccff; margin-right:6px;">
                    Contrast
                </button>
                <button onclick="toggleInvert()"
                        style="padding:6px 10px; background:#222; color:#ff6699; border:1px solid #ff6699;">
                    Invert
                </button>
            </div>
            <iframe id="spectroFrame" src="/static/{rel}"
                    style="width:96%; height:760px; border:2px solid #66ff99; border-radius:4px;"></iframe>
        </div>
        <script>
        function getPlot() {{
            const frame = document.getElementById("spectroFrame").contentWindow.document;
            return frame.querySelector("div.plotly");
        }}
        function toggleContrast() {{
            const p = getPlot(); if(!p) return;
            const z = [].concat(...p.data[0].z).sort((a,b)=>a-b);
            const q = q=>z[Math.floor(q*z.length)];
            const on = p.layout._contrastOn = !p.layout._contrastOn;
            Plotly.restyle(p, {{
                zmin:[on?q(0.05):null],
                zmax:[on?q(0.95):null]
            }});
        }}
        function toggleInvert() {{
            const p = getPlot(); if(!p) return;
            const inv = p.layout._invertOn = !p.layout._invertOn;
            Plotly.restyle(p, {{colorscale: inv?"Inferno_r":"Inferno"}});
        }}
        </script>
        """
        elif isinstance(value, str):
            html += f"<h4>{key}</h4><pre>{value}</pre>"
        elif isinstance(value, list):
            html += f"<h4>{key}</h4><ul>" + "".join(f"<li>{v}</li>" for v in value) + "</ul>"



    # --- AUDIO PLAYER SECTION ---
    html += f"""
    <hr>
    <h3 style="color:#66ccff;">Audio Playback</h3>
    <div style="text-align:center; margin:20px;">
        <audio id="audioPlayer" controls src="/{upload_path}"
               style="width:80%; border:1px solid #66ff99; border-radius:4px;"></audio>
        <div style="margin-top:15px; display:flex; justify-content:center; gap:10px;">
            <button onclick="changeSpeed(0.5)" style="padding:5px 10px; background:#222; color:#66ff99; border:1px solid #66ff99;">🐢 0.5x</button>
            <button onclick="changeSpeed(1)" style="padding:5px 10px; background:#222; color:#66ccff; border:1px solid #66ccff;">🔄 Reset</button>
            <button onclick="changeSpeed(2)" style="padding:5px 10px; background:#222; color:#ffcc00; border:1px solid #ffcc00;">⚡ 2x</button>
            <button onclick="reverseAudio()" style="padding:5px 10px; background:#222; color:#ff6699; border:1px solid #ff6699;">⏪ Reverse</button>
        </div>
    </div>

    <script>
    let scale = 1;
    let contrast = false;
    let inverted = false;

    // Stretch controls
    function stretch(delta) {{
        const input = document.getElementById("stretchInput");
        if (delta === 0) {{
            scale = parseFloat(input.value) || 1;
        }} else {{
            scale += delta * 0.2;
            if (scale < 0.2) scale = 0.2;
            input.value = scale.toFixed(1);
        }}
        document.getElementById("spectrogram").style.transform = `scaleX(${{scale}})`;
    }}
    document.addEventListener("DOMContentLoaded", () => {{
        const input = document.getElementById("stretchInput");
        if (input) input.addEventListener("change", () => stretch(0));
    }});

    function toggleContrast() {{
        contrast = !contrast;
        updateFilters();
    }}
    function toggleInvert() {{
        inverted = !inverted;
        updateFilters();
    }}
    function updateFilters() {{
        const img = document.getElementById("spectrogram");
        let filters = [];
        if (contrast) filters.push("contrast(200%)");
        if (inverted) filters.push("invert(100%)");
        img.style.filter = filters.join(" ");
    }}

    // --- Audio Controls ---
    const player = document.getElementById("audioPlayer");
    function changeSpeed(rate) {{
        player.playbackRate = rate;
    }}

    async function reverseAudio() {{
        const audioCtx = new AudioContext();
        const response = await fetch(player.src);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
        for (let i = 0; i < audioBuffer.numberOfChannels; i++) {{
            Array.prototype.reverse.call(audioBuffer.getChannelData(i));
        }}
        const reversed = audioCtx.createBufferSource();
        reversed.buffer = audioBuffer;
        reversed.connect(audioCtx.destination);
        reversed.start(0);
    }}
    </script>
    """

    html += "<hr><a href='/'>Return to main menu</a>"
    return HTMLResponse(
        content=f"<html><head><link rel='stylesheet' href='/static/css/style.css'></head>"
                f"<body>{html}</body></html>"
    )
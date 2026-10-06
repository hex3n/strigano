# strigano

**A lightweight stego and forensics triage multi-tool for CTFs, built for speed.**

strigano is a super-fast alternative to **Aperi'Solve** (image stego) and
**Audacity** (audio spectrogram). You run it locally, drop a file in, and read the
result in seconds.

Built and maintained by **hex3n**.
If you find this tool useful, i'd really appreciate a Star on this repo. Thank you and have fun
---

## What it replaces

- **Aperi'Solve, for images:** bitplanes for every RGB channel, superimposed
  per-bit views, grayscale and channel variants, appended-data carving, EXIF,
  strings, and the standard tools (exiftool, binwalk, foremost, steghide,
  zsteg), all on one results page, served from your own machine.
- **Audacity, for audio:** an interactive dual-channel spectrogram, container
  metadata, and embedded strings, without launching an editor.

Plus OCR flag detection across every bitplane, matching configurable flag
formats, so an in-plane flag is often read for you.

## Run it (web UI)

This is the way strigano is meant to run: a local web server.

```
strigano serve
```

or the explicit form, if you prefer driving uvicorn yourself:

```
uvicorn strigano.web.server:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 and drop in an image or an audio file. Use
`--host 0.0.0.0` to reach it from your Kali VM or another machine, `--port` to
change the port.

## Automation (CLI)

For scripting and quick one-offs without the browser. Same engine, same output.

```
strigano image challenge.png
strigano image challenge.png --password hunter2
strigano image challenge.png --json > report.json
strigano audio challenge.wav
strigano check
```

Artifacts (bitplanes, carved files, spectrogram) are written under
`./strigano_output/<name>-<id>/`, or wherever `--out` / `STRIGANO_OUTPUT` point.

## Try it

The `examples/` folder ships two carriers to prove it out:

- `demo_image.png` looks like a plain gradient but hides `fort{bitplane_stego}`
  in the blue channel LSB. Upload it, then look at the `blue_bit0` plane.
- `demo_spectro.wav` spells `STRIGANO` in its spectrogram. Upload it and open
  the spectrogram panel.

## Install

### Kali / Debian (full toolchain)

```
./scripts/setup-kali.sh
strigano check
```

Installs exiftool, binwalk, foremost, steghide, zsteg, tesseract and ffmpeg,
then installs strigano via pipx (or a venv fallback).

### Windows (Python features, reduced tool set)

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .
strigano serve
```

Bitplanes, strings, appended data, the spectrogram and metadata run on Windows.
For OCR, install the Tesseract Windows build and put `tesseract.exe` on PATH.
The Linux-only tools (binwalk, foremost, steghide, zsteg) show as missing and
are skipped. `strigano check` shows the current state.

### Docker (full toolchain, nothing to install)

```
docker build -t strigano .
docker run --rm -p 8000:8000 -v "$PWD/out:/data" strigano
```

Then open http://localhost:8000.

## External tools

| Tool | Used for | Install (Kali) |
|---|---|---|
| exiftool | metadata | `apt install libimage-exiftool-perl` |
| binwalk | embedded file carving | `apt install binwalk` |
| foremost | file recovery | `apt install foremost` |
| steghide | JPEG/WAV extraction | `apt install steghide` |
| zsteg | PNG/BMP LSB stego | `gem install zsteg` |
| tesseract | OCR flag detection | `apt install tesseract-ocr` |
| ffmpeg | MP3 decode for spectrogram | `apt install ffmpeg` |

Any tool not present is skipped rather than fatal.

## Configuration

Environment variables, all optional:

| Variable | Effect |
|---|---|
| `STRIGANO_OUTPUT` | output directory (default `./strigano_output`) |
| `STRIGANO_FLAG_PREFIXES` | extra flag prefixes, comma separated, e.g. `fort,myctf` |
| `STRIGANO_MAX_UPLOAD` | web upload size cap in bytes |
| `STRIGANO_TOOL_TIMEOUT` | per-tool subprocess timeout in seconds |
| `STRIGANO_<TOOL>` | absolute path to a specific binary, e.g. `STRIGANO_EXIFTOOL` |

Set the event flag format at the start of a CTF so detection catches it:

```
export STRIGANO_FLAG_PREFIXES="fort"
```

## License

MIT. See `LICENSE`.

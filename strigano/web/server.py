"""The FastAPI application. Launch with strigano serve or uvicorn."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import __version__, config, tools
from ..analysis import engine

app = FastAPI(title="Strigano", version=__version__)

# Ensure the writable output root exists before it is mounted.
config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Packaged read-only assets, and the writable generated-output tree.
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(config.OUTPUT_DIR)), name="output")

templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


def _save_upload(upload: UploadFile) -> tuple[str, str]:
    """Stream an upload to a temp file with a size cap. Returns (path, name)."""
    display = upload.filename or "upload"
    suffix = Path(display).suffix
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large.")
                out.write(chunk)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return tmp, display


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"tools": tools.tool_status(), "version": __version__}
    )


@app.get("/tools")
def tool_status():
    return JSONResponse(tools.tool_status())


# Sync defs run in a threadpool, so the blocking tool subprocesses do not
# stall the event loop.
@app.post("/upload", response_class=HTMLResponse)
def upload(request: Request, file: UploadFile = File(...), password: str = Form("")):
    tmp, display = _save_upload(file)
    try:
        report = engine.analyze_image(tmp, display, password)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return templates.TemplateResponse(
        request, "image_report.html", {"r": report}
    )


@app.post("/audio", response_class=HTMLResponse)
def audio(request: Request, file: UploadFile = File(...)):
    tmp, display = _save_upload(file)
    try:
        report = engine.analyze_audio(tmp, display)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return templates.TemplateResponse(
        request, "audio_report.html", {"r": report}
    )

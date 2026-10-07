"""Wrappers around the external forensics tools, all optional.

Each returns a ToolSection so the report renders a uniform block:
the output when the tool ran, or a clear "not installed" note when it did not.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .. import tools
from .result import ToolSection


def _unavailable(name: str) -> ToolSection:
    return ToolSection(name=name, available=False, ok=False,
                       note=f"{name} is not installed on this host.")


def exiftool_metadata(path: str) -> dict:
    """Return parsed EXIF/metadata as a dict, or a single Notice entry."""
    res = tools.run_tool("exiftool", ["-json", path])
    if not res.available:
        return {"Notice": "exiftool is not installed on this host."}
    if not res.ok or not res.stdout.strip():
        return {"Notice": "No readable metadata or unsupported format."}
    try:
        return json.loads(res.stdout)[0]
    except (ValueError, IndexError):
        return {"Notice": "exiftool returned unparseable output."}


def exiftool_text(path: str) -> ToolSection:
    res = tools.run_tool("exiftool", [path])
    if not res.available:
        return _unavailable("exiftool")
    return ToolSection(
        name="exiftool", available=True, ok=res.ok,
        output=res.stdout if res.ok else (res.stderr or res.error),
    )


def binwalk(path: str, out_dir: str | Path) -> ToolSection:
    """Run binwalk -e and collect carved files (v2 and v3 layouts)."""
    out = Path(out_dir)
    base = Path(path).name

    # Clean any prior extraction dirs for this file (both naming schemes).
    for pattern in (f"_{base}.extracted", f"{base}.extracted"):
        stale = out / pattern
        if stale.exists():
            shutil.rmtree(stale, ignore_errors=True)

    # Run inside out_dir so extraction lands there regardless of binwalk version.
    res = tools.run_tool("binwalk", ["-e", str(Path(path).resolve())], cwd=str(out))
    if not res.available:
        return _unavailable("binwalk")

    files: list[str] = []
    for pattern in (f"_{base}.extracted", f"{base}.extracted"):
        extracted = out / pattern
        if extracted.is_dir():
            for fp in extracted.rglob("*"):
                if fp.is_file():
                    files.append(str(fp.relative_to(out)).replace("\\", "/"))

    return ToolSection(
        name="binwalk", available=True, ok=res.ok,
        output=res.stdout or res.stderr, files=sorted(files),
    )


def foremost(path: str, out_dir: str | Path) -> ToolSection:
    out = Path(out_dir)
    dest = out / "foremost"
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    res = tools.run_tool("foremost", ["-i", path, "-o", str(dest)])
    if not res.available:
        return _unavailable("foremost")

    files: list[str] = []
    if dest.exists():
        for fp in dest.rglob("*"):
            if fp.is_file() and fp.name != "audit.txt":
                files.append(str(fp.relative_to(out)).replace("\\", "/"))

    audit = dest / "audit.txt"
    output = audit.read_text(errors="ignore") if audit.exists() else (
        res.stdout or res.stderr
    )
    return ToolSection(
        name="foremost", available=True, ok=res.ok,
        output=output, files=sorted(files),
    )


def steghide(path: str, out_dir: str | Path, password: str = "") -> ToolSection:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    extracted = out / "steghide_extracted.bin"

    res = tools.run_tool(
        "steghide",
        ["extract", "-sf", path, "-xf", str(extracted), "-f", "-p", password or ""],
    )
    if not res.available:
        return _unavailable("steghide")

    ok = extracted.exists() or "wrote extracted data" in res.stdout.lower()
    section = ToolSection(
        name="steghide", available=True, ok=ok,
        output=(res.stdout or res.stderr or "").strip(),
    )
    if extracted.exists():
        section.files = [extracted.name]
    elif not ok:
        section.note = "No embedded data recovered (wrong password or none present)."
    return section


def zsteg(path: str) -> ToolSection:
    # zsteg only understands PNG and BMP; skip other inputs cleanly.
    if Path(path).suffix.lower() not in (".png", ".bmp"):
        return ToolSection(
            name="zsteg", available=tools.is_available("zsteg"), ok=False,
            note="zsteg only supports PNG and BMP inputs.",
        )
    res = tools.run_tool("zsteg", ["-a", path])
    if not res.available:
        return _unavailable("zsteg")
    return ToolSection(
        name="zsteg", available=True, ok=res.ok,
        output=(res.stdout or res.stderr).strip() or "No zsteg output.",
    )

"""Structured result types returned by the analysis core.

Both the web templates and the CLI consume these, so the two front ends can
never drift in what they report. Everything is plain data, JSON serialisable
via to_dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolSection:
    """One external-tool result as presented in a report."""

    name: str
    available: bool
    ok: bool
    output: str = ""
    files: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "ok": self.ok,
            "output": self.output,
            "files": self.files,
            "note": self.note,
        }


@dataclass
class ImageReport:
    filename: str
    output_prefix: str = ""           # relative dir under the output root
    metadata: dict = field(default_factory=dict)
    exiftool_text: str = ""
    bitplanes: list[str] = field(default_factory=list)       # relative file names
    superimposed: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)          # gray/channel variants
    appended_file: str | None = None
    strings_ascii: list[str] = field(default_factory=list)
    strings_utf16: list[str] = field(default_factory=list)
    flags: list[tuple[str, str]] = field(default_factory=list)   # (image, flag)
    tools: list[ToolSection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "output_prefix": self.output_prefix,
            "metadata": self.metadata,
            "exiftool_text": self.exiftool_text,
            "bitplanes": self.bitplanes,
            "superimposed": self.superimposed,
            "extras": self.extras,
            "appended_file": self.appended_file,
            "strings_ascii": self.strings_ascii,
            "strings_utf16": self.strings_utf16,
            "flags": [{"image": i, "flag": f} for i, f in self.flags],
            "tools": [t.to_dict() for t in self.tools],
            "errors": self.errors,
        }


@dataclass
class AudioReport:
    filename: str
    output_prefix: str = ""
    metadata: str = ""
    spectrogram_file: str | None = None      # relative .html path
    audio_file: str | None = None            # relative copy for playback
    strings: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "output_prefix": self.output_prefix,
            "metadata": self.metadata,
            "spectrogram_file": self.spectrogram_file,
            "audio_file": self.audio_file,
            "strings": self.strings,
            "flags": self.flags,
            "errors": self.errors,
        }

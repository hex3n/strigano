"""Command line interface. Installed as the strigano console script."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config, tools


def _apply_out(out: str | None) -> None:
    if out:
        config.OUTPUT_DIR = Path(out).resolve()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _print_tools() -> None:
    print("External tool availability:")
    for name, ok in tools.tool_status().items():
        print(f"  [{'+' if ok else '-'}] {name:<10} {'ready' if ok else 'missing'}")


def cmd_check(_: argparse.Namespace) -> int:
    _print_tools()
    return 0


def cmd_image(args: argparse.Namespace) -> int:
    from .analysis import engine

    if not Path(args.file).is_file():
        print(f"No such file: {args.file}", file=sys.stderr)
        return 2
    _apply_out(args.out)
    report = engine.analyze_image(args.file, Path(args.file).name, args.password or "")

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"\n== strigano image report: {report.filename} ==")
    out_run = config.OUTPUT_DIR / report.output_prefix
    print(f"Artifacts: {out_run}")
    if report.flags:
        print("\nDetected flags:")
        for img, flag in report.flags:
            print(f"  {flag}   <- {img}")
    else:
        print("\nNo flags auto-detected.")
    print(f"\nBitplanes written: {len(report.bitplanes)}  "
          f"Superimposed: {len(report.superimposed)}  Extras: {len(report.extras)}")
    if report.appended_file:
        print(f"Appended data carved: {report.appended_file}")
    print("\nTool results:")
    for t in report.tools:
        if not t.available:
            status = "not installed (skipped)"
        elif t.ok:
            status = "ok"
        elif t.note:
            status = t.note
        else:
            status = "no result"
        suffix = f"  ({len(t.files)} file(s))" if t.files else ""
        print(f"  {t.name:<10} {status}{suffix}")
    print(f"\nStrings: {len(report.strings_ascii)} ASCII, "
          f"{len(report.strings_utf16)} UTF-16LE")
    if report.errors:
        print("\nErrors:")
        for e in report.errors:
            print(f"  {e}")
    return 0


def cmd_audio(args: argparse.Namespace) -> int:
    from .analysis import engine

    if not Path(args.file).is_file():
        print(f"No such file: {args.file}", file=sys.stderr)
        return 2
    _apply_out(args.out)
    report = engine.analyze_audio(args.file, Path(args.file).name)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"\n== strigano audio report: {report.filename} ==")
    print(f"Artifacts: {config.OUTPUT_DIR / report.output_prefix}")
    if report.spectrogram_file:
        print(f"Spectrogram: {report.spectrogram_file}")
    if report.flags:
        print("\nDetected flags:")
        for flag in report.flags:
            print(f"  {flag}")
    print(f"\nStrings extracted: {len(report.strings)}")
    if report.errors:
        print("\nErrors:")
        for e in report.errors:
            print(f"  {e}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    _apply_out(args.out)
    uvicorn.run(
        "strigano.web.server:app",
        host=args.host, port=args.port, reload=args.reload,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="strigano", description=__doc__)
    p.add_argument("--version", action="version", version=f"strigano {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("check", help="show external tool availability")
    pc.set_defaults(func=cmd_check)

    pi = sub.add_parser("image", help="analyze an image file")
    pi.add_argument("file")
    pi.add_argument("-p", "--password", help="steghide password")
    pi.add_argument("-o", "--out", help="output directory")
    pi.add_argument("--json", action="store_true", help="emit JSON")
    pi.set_defaults(func=cmd_image)

    pa = sub.add_parser("audio", help="analyze an audio file")
    pa.add_argument("file")
    pa.add_argument("-o", "--out", help="output directory")
    pa.add_argument("--json", action="store_true", help="emit JSON")
    pa.set_defaults(func=cmd_audio)

    ps = sub.add_parser("serve", help="run the web UI")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8000)
    ps.add_argument("--reload", action="store_true")
    ps.add_argument("-o", "--out", help="output directory")
    ps.set_defaults(func=cmd_serve)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

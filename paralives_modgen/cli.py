"""Command-line interface for paralives-modgen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .guid import new_guid
from .parser import Collection, Setting, parse
from .serializer import serialize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modgen", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="Parse a .setting file and print as JSON")
    p_parse.add_argument("file", type=Path)

    p_verify = sub.add_parser(
        "verify", help="Round-trip every .setting in a directory; report mismatches"
    )
    p_verify.add_argument("path", type=Path, help="Directory or single file")
    p_verify.add_argument(
        "--show-diff", action="store_true", help="Print unified diffs for mismatches"
    )

    sub.add_parser("guid", help="Print a fresh random GUID")

    args = parser.parse_args(argv)

    if args.cmd == "parse":
        return _cmd_parse(args.file)
    if args.cmd == "verify":
        return _cmd_verify(args.path, args.show_diff)
    if args.cmd == "guid":
        print(new_guid())
        return 0
    return 1


def _cmd_parse(path: Path) -> int:
    text = path.read_text()
    setting = parse(text)
    json.dump(_to_jsonable(setting), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Setting):
        return {
            "_setting_type": obj.setting_type,
            "_body": _to_jsonable(obj.body),
        }
    if isinstance(obj, Collection):
        return [
            {"_index": idx, **_to_jsonable(data)} for idx, data in obj.items
        ]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _cmd_verify(path: Path, show_diff: bool) -> int:
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.glob("*.setting"))
    else:
        print(f"Not found: {path}", file=sys.stderr)
        return 2

    if not files:
        print(f"No .setting files found at {path}", file=sys.stderr)
        return 2

    ok = 0
    parse_fail = 0
    roundtrip_mismatch = 0
    for f in files:
        original = f.read_text()
        try:
            setting = parse(original)
        except Exception as e:
            parse_fail += 1
            print(f"[PARSE ERROR] {f.name}: {e}")
            continue
        emitted = serialize(setting)
        if emitted == original:
            ok += 1
        else:
            roundtrip_mismatch += 1
            print(f"[ROUND-TRIP MISMATCH] {f.name}")
            if show_diff:
                import difflib

                diff = difflib.unified_diff(
                    original.splitlines(keepends=True),
                    emitted.splitlines(keepends=True),
                    fromfile=f"{f.name} (original)",
                    tofile=f"{f.name} (emitted)",
                    n=2,
                )
                sys.stdout.writelines(diff)
                print()

    total = len(files)
    print(
        f"\nResult: {ok}/{total} byte-identical, "
        f"{roundtrip_mismatch} mismatched, {parse_fail} unparseable"
    )
    return 0 if (parse_fail == 0 and roundtrip_mismatch == 0) else 1

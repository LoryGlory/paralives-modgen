"""Serialize parsed Setting objects back to `.setting` text.

Round-trip target: parse(serialize(parse(text))) == parse(text), and ideally
serialize(parse(text)) == text byte-for-byte.
"""

from __future__ import annotations

from typing import Any

from .parser import Collection, FieldList, Item, ScalarWithBody, Setting


def serialize(setting: Setting, trailing_newline: bool = True) -> str:
    """Emit a Setting as the original `.setting` text."""
    lines: list[str] = []
    lines.append(f"#Setting.{setting.setting_type}")
    _emit_block(setting.body, indent=1, out=lines)
    text = "\n".join(lines)
    if trailing_newline:
        text += "\n"
    return text


def _emit_block(body: FieldList | dict[str, Any], indent: int, out: list[str]) -> None:
    """Emit a block of `=Field:Value` lines at the given indent.

    Accepts either a FieldList (preserves source order and duplicate keys)
    or a plain dict (convenience for hand-built mod content)."""
    pad = " " * indent
    for key, value in body.items():
        if isinstance(value, Collection):
            out.append(f"{pad}={key}")
            _emit_collection(value, indent=indent + 1, out=out)
        elif isinstance(value, ScalarWithBody):
            out.append(f"{pad}={key}:{value.value}")
            _emit_value_body(value.body, indent=indent + 1, out=out)
        elif isinstance(value, (FieldList, dict)):
            out.append(f"{pad}={key}")
            _emit_block(value, indent=indent + 1, out=out)
        elif value == "":
            out.append(f"{pad}={key}")
        else:
            out.append(f"{pad}={key}:{value}")


def _emit_value_body(body: Any, indent: int, out: list[str]) -> None:
    if isinstance(body, Collection):
        _emit_collection(body, indent=indent, out=out)
    elif isinstance(body, (FieldList, dict)):
        _emit_block(body, indent=indent, out=out)


def _emit_collection(collection: Collection, indent: int, out: list[str]) -> None:
    """Emit `sN` (if sized) then each item with its marker."""
    pad = " " * indent
    if collection.declared_size is not None:
        out.append(f"{pad}s{collection.declared_size}")
    for item in collection.items:
        _emit_item(item, indent=indent, out=out)


def _emit_item(item: Item, indent: int, out: list[str]) -> None:
    pad = " " * indent
    if item.marker == "i" and item.inline_value is not None:
        out.append(f"{pad}i{item.key}:{item.inline_value}")
    else:
        out.append(f"{pad}{item.marker}{item.key}")
    _emit_block(item.fields, indent=indent + 1, out=out)

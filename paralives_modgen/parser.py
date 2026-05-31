"""Parse Paralives .setting files into Python data structures.

Format:

    #Setting.<TypeName>
     =ScalarField:Value
     =CollectionField
      s<size>
      i<index>
       =NestedField:Value

Indentation is single-space, each level = +1 space. Collections are
declared by an `=Name` field with no value, followed by an optional
`s<N>` size marker and then a sequence of item blocks.

## Item marker forms

Inside a collection, an item can be opened with one of three markers:

- `i<index>` — positional item (the original form).
- `i<index>:<value>` — positional item with an inline scalar value
  (seen in `Thoughts.setting` and a few others).
- `@<GUID>` — item identified by its explicit GUID rather than position.
  Used by mods to add new items to base collections.
- `g<GUID>` — *extension* of an existing entity in the collection.
  Its fields are merged onto the entity already declared with that GUID
  elsewhere. Extension contexts skip the `s<N>` size declaration.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


class ParseError(Exception):
    """Raised when a .setting file can't be parsed."""


# Valid item-marker characters. Order matters only for error messages.
MARKERS = ("i", "@", "g")


class FieldList:
    """Ordered list of (key, value) pairs with dict-like access.

    Allows duplicate keys — required because some base-game `.setting`
    files declare the same field twice in one block (e.g. Actions.setting
    has `=CharacterIndex` twice on a single Action; Interactions.setting
    has `=GUID` twice on the FlexMuscle interaction). A plain dict would
    silently drop the first occurrence and break round-trip.

    Dict-like access (`fl[key]`, `key in fl`, `fl[key] = value`) operates
    on the FIRST occurrence — convenient for the common case where keys
    are unique. Use `append(key, value)` from parsers to preserve all
    occurrences faithfully.
    """

    __slots__ = ("_items",)

    def __init__(self, items: list[tuple[str, Any]] | None = None) -> None:
        self._items: list[tuple[str, Any]] = list(items) if items else []

    def append(self, key: str, value: Any) -> None:
        """Always append, preserving duplicates. Used by the parser."""
        self._items.append((key, value))

    def __getitem__(self, key: str) -> Any:
        for k, v in self._items:
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Replace the first occurrence, or append if not present (dict-like)."""
        for i, (k, _) in enumerate(self._items):
            if k == key:
                self._items[i] = (key, value)
                return
        self._items.append((key, value))

    def __delitem__(self, key: str) -> None:
        for i, (k, _) in enumerate(self._items):
            if k == key:
                del self._items[i]
                return
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return any(k == key for k, _ in self._items)

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FieldList):
            return self._items == other._items
        if isinstance(other, dict):
            # Equal to a dict only if no duplicate keys.
            seen = set()
            for k, _ in self._items:
                if k in seen:
                    return False
                seen.add(k)
            return dict(self._items) == other
        return NotImplemented

    def __hash__(self) -> int:
        return NotImplemented  # mutable, like dict

    def __repr__(self) -> str:
        return f"FieldList({self._items!r})"

    def items(self) -> Iterator[tuple[str, Any]]:
        """Iterate (key, value) pairs in source order. Preserves duplicates."""
        return iter(self._items)

    def keys(self) -> Iterator[str]:
        return (k for k, _ in self._items)

    def values(self) -> Iterator[Any]:
        return (v for _, v in self._items)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def has_duplicate_keys(self) -> bool:
        seen: set[str] = set()
        for k, _ in self._items:
            if k in seen:
                return True
            seen.add(k)
        return False


@dataclass
class Item:
    """A collection item.

    Attributes:
      marker: one of 'i', '@', 'g'. See module docstring.
      key:    the integer carried by the marker — index for 'i',
              GUID for '@' / 'g'.
      fields: nested field map.
      inline_value: present only for the `iN:value` form.
    """

    marker: str = "i"
    key: int = 0
    fields: FieldList = field(default_factory=lambda: FieldList())
    inline_value: str | None = None


@dataclass
class Collection:
    """A collection field (=Name followed by sN + iX/@GUID/gGUID blocks).

    `declared_size` is the integer from the `s<N>` line, or `None` when
    the source had no size marker (extension contexts). We preserve the
    original value rather than recomputing because base-game files
    sometimes have stale sizes (e.g. Video.setting declares s7 with 6
    items).
    """

    items: list[Item] = field(default_factory=list)
    declared_size: int | None = None

    def __iter__(self):
        return iter(self.items)


@dataclass
class ScalarWithBody:
    """A field that has both a scalar value AND nested content.

    Rare but real: e.g., Actions.setting has `=ExtraItemLocatorToLocomotionTo:0`
    followed by an indented `s0` (orphan empty collection).
    """

    value: str
    body: Any  # dict or Collection


@dataclass
class Setting:
    """Top-level parsed .setting file."""

    setting_type: str
    body: FieldList


def parse(text: str) -> Setting:
    """Parse a `.setting` file's full text into a Setting."""
    lines = text.splitlines()
    if not lines:
        raise ParseError("Empty file")
    header = lines[0]
    if not header.startswith("#Setting."):
        raise ParseError(f"Missing '#Setting.X' header (got: {header!r})")
    setting_type = header[len("#Setting.") :]
    body, consumed = _parse_block(lines, start=1, indent=1)
    if consumed != len(lines) and any(line.strip() for line in lines[consumed:]):
        raise ParseError(
            f"Unexpected content after main block at line {consumed + 1}: "
            f"{lines[consumed]!r}"
        )
    return Setting(setting_type=setting_type, body=body)


def _leading_spaces(line: str) -> int:
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        else:
            break
    return n


def _parse_block(
    lines: list[str], start: int, indent: int
) -> tuple[FieldList, int]:
    """Parse a block of `=Field:Value` lines at the given indent."""
    result = FieldList()
    i = start
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        line_indent = _leading_spaces(lines[i])
        if line_indent < indent:
            return result, i
        if line_indent > indent:
            raise ParseError(
                f"Unexpected over-indent at line {i + 1}: "
                f"expected {indent}, got {line_indent}: {lines[i]!r}"
            )
        name, value, i = _parse_one_field(lines, i, indent)
        result.append(name, value)
    return result, i


def _parse_one_field(
    lines: list[str], i: int, indent: int
) -> tuple[str, Any, int]:
    """Parse one `=Field…` line (possibly with body) and return (name, value, next_i)."""
    line = lines[i]
    content = line[indent:]
    if not content.startswith("="):
        raise ParseError(f"Expected '=Field' at line {i + 1}, got: {line!r}")
    field_body = content[1:]

    if ":" in field_body:
        name, value = field_body.split(":", 1)
        body_indent = _peek_body_indent(lines, i + 1, indent)
        if body_indent is not None:
            body, next_i = _parse_value_body(lines, i + 1, body_indent)
            return name, ScalarWithBody(value=value, body=body), next_i
        return name, value, i + 1

    name = field_body
    body_indent = _peek_body_indent(lines, i + 1, indent)
    if body_indent is None:
        return name, "", i + 1
    body, next_i = _parse_value_body(lines, i + 1, body_indent)
    return name, body, next_i


def _peek_body_indent(lines: list[str], start: int, parent_indent: int) -> int | None:
    nb = _next_nonblank(lines, start)
    if nb is None:
        return None
    body_indent = _leading_spaces(lines[nb])
    return body_indent if body_indent > parent_indent else None


def _parse_value_body(
    lines: list[str], start: int, indent: int
) -> tuple[Any, int]:
    """Parse the body that follows a field — Collection (sized or sizeless) or FieldList."""
    nb = _next_nonblank(lines, start)
    if nb is None:
        return FieldList(), start
    content = lines[nb][indent:]
    if content.startswith("s") and content[1:].isdigit():
        return _parse_collection(lines, start, indent, has_size_marker=True)
    if _marker_for(content) is not None:
        # Collection without an s<N> declaration (extension context).
        return _parse_collection(lines, start, indent, has_size_marker=False)
    return _parse_block(lines, start, indent)


def _marker_for(content: str) -> str | None:
    """Return the marker character ('i', '@', or 'g') if `content` opens an
    item block; else None."""
    if not content:
        return None
    head, rest = content[0], content[1:]
    if head not in MARKERS:
        return None
    # `iN` and `iN:value` both legal; '@'/'g' have GUID after.
    if head == "i":
        digits = rest.split(":", 1)[0]
        return head if digits.isdigit() else None
    return head if rest.isdigit() else None


def _parse_collection(
    lines: list[str], start: int, indent: int, *, has_size_marker: bool
) -> tuple[Collection, int]:
    """Parse a collection. If `has_size_marker`, the first non-blank line at
    `indent` must be `s<N>`; otherwise items start immediately."""
    i = _next_nonblank(lines, start)
    if i is None:
        raise ParseError("Expected collection body, got end of file")
    declared_size: int | None = None
    if has_size_marker:
        line = lines[i]
        if _leading_spaces(line) != indent:
            raise ParseError(
                f"Expected sN at indent {indent}, got: {line!r}"
            )
        content = line[indent:]
        if not (content.startswith("s") and content[1:].isdigit()):
            raise ParseError(f"Expected sN line at line {i + 1}, got: {line!r}")
        declared_size = int(content[1:])
        i += 1
    items: list[Item] = []
    while True:
        item_info = _try_parse_item(lines, i, indent)
        if item_info is None:
            break
        item, i = item_info
        items.append(item)
    return Collection(items=items, declared_size=declared_size), i


def _try_parse_item(
    lines: list[str], i: int, indent: int
) -> tuple[Item, int] | None:
    """Try to parse one collection item starting at line i.

    Returns (item, next_i) or None if no recognised item is at the expected indent.
    """
    nb = _next_nonblank(lines, i)
    if nb is None:
        return None
    line = lines[nb]
    line_indent = _leading_spaces(line)
    if line_indent < indent:
        return None
    if line_indent > indent:
        raise ParseError(
            f"Unexpected over-indent in collection at line {nb + 1}: "
            f"expected {indent}, got {line_indent}: {line!r}"
        )
    content = line[indent:]
    marker = _marker_for(content)
    if marker is None:
        return None
    marker_body = content[1:]
    inline_value: str | None = None
    if marker == "i" and ":" in marker_body:
        key_str, inline_value = marker_body.split(":", 1)
    else:
        key_str = marker_body
    if not key_str.isdigit():
        return None
    key = int(key_str)
    item_fields, next_i = _parse_block(lines, nb + 1, indent + 1)
    return Item(marker=marker, key=key, fields=item_fields, inline_value=inline_value), next_i


def _next_nonblank(lines: list[str], start: int) -> int | None:
    i = start
    while i < len(lines):
        if lines[i].strip():
            return i
        i += 1
    return None

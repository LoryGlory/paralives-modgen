# paralives-modgen

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Paralives 1.0 EA](https://img.shields.io/badge/paralives-1.0%20EA-purple.svg)](https://store.steampowered.com/app/1118520/Paralives/)
[![Round-trip 138/159](https://img.shields.io/badge/round--trip-138%2F159-brightgreen.svg)](#round-trip-fidelity)
[![Status: early](https://img.shields.io/badge/status-early-orange.svg)](#status)

A Python library and CLI for parsing, manipulating, and emitting [Paralives](https://store.steampowered.com/app/1118520/Paralives/) `.setting` files.

If you're writing a content mod for Paralives and want to **generate** mod files programmatically — from a YAML config, from a CSV of items, or as part of a build pipeline — this gives you direct, type-checked access to the underlying `.setting` format that the in-game Control Panel hides.

## Why this exists

Paralives ships its base game data as a giant directory of plain-text `.setting` files (`Main.mod/Settings/*.setting`), and mods are authored in the same format. The official Control Panel UI is great for clicking together a few entities, but it doesn't help when you want to:

- Override 50 furniture items with computed values
- Clone an existing entity 20 times with different parameters
- Generate `Translations.setting` entries from a localization spreadsheet
- Write a build script that regenerates a mod from a YAML spec

modgen gives you the file format as a Python data structure, so you can do all of the above with a few dozen lines of code.

## Install

Requires Python 3.11+.

```bash
pip install git+https://github.com/LoryGlory/paralives-modgen.git
```

Or, for a zero-install workflow with [`uv`](https://docs.astral.sh/uv/), drop this PEP 723 metadata into the top of your build script:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "paralives-modgen @ git+https://github.com/LoryGlory/paralives-modgen.git",
# ]
# ///
```

Then `uv run build.py` auto-installs and executes.

(Not yet on PyPI.)

## Quickstart

```python
from paralives_modgen import parse, serialize
from paralives_modgen.parser import Collection, Item, Setting, FieldList

# Read the base game's Needs definition
text = open("path/to/Main.mod/Settings/Needs.setting").read()
needs = parse(text)

# Find the Sleep need and print its base replenish rate
for item in needs.body["AllNeeds"].items:
    if item.fields.get("DisplayName") == "Sleep":
        print(item.fields["BaseReplenishSpeedInUnitsPerHour"])
        break

# Build a new mod that adds one Boost via the @<GUID> merge syntax
mod = Setting(
    setting_type="Boosts",
    body=FieldList([("AllBoosts", Collection(
        items=[Item(marker="@", key=1234567890123456789, fields=FieldList([
            ("GUID",        "1234567890123456789"),
            ("DisplayName", "MyMod_ExampleBoost"),
            ("BoostType",   "1"),
            ("BoostValue",  "0"),
            ("Duration",    "60"),
        ]))],
        declared_size=1,
    ))]),
)
print(serialize(mod))
```

## CLI

```bash
modgen parse path/to/Foo.setting       # parse + print as JSON
modgen verify path/to/Settings/        # round-trip every file; report mismatches
modgen guid                            # emit a fresh random 64-bit GUID
```

## The `.setting` format

Plain text, indent-sensitive, single-space per level:

```
#Setting.<TypeName>
 =FieldName:ScalarValue
 =CollectionField
  s<size>             ← optional size declaration
  i<index>            ← positional item
   =NestedField:Value
  @<GUID>             ← collection-extension item identified by GUID
  g<GUID>             ← extension block: merge fields onto an existing entity
```

The three item-marker forms:

- **`i<index>`** — positional item. The original form. Used when you author a brand-new entity from scratch.
- **`@<GUID>`** — item identified by an explicit GUID. **This is the merge syntax** for mods adding new items to a base game collection. Using `i<index>` instead causes the game to REPLACE the entire base collection (silently). Learned the hard way.
- **`g<GUID>`** — extension of an existing entity. Inside a `g<GUID>` block, sub-collections appear without `s<N>` markers and use `@<GUID>` for added items.

## Round-trip fidelity

The acid test for a format library: can it parse a file and emit it back byte-for-byte? Current numbers on the 159 base game `.setting` files (Paralives 1.0.0):

| Result | Count |
|---|---|
| Byte-identical | **138 / 159** |
| Parses but emits with cosmetic differences | 1 |
| Unparseable (mostly `#XxxxBasedOnState` files with non-`#Setting.` headers) | 20 |

All files that content modders actually touch (`Actions.setting`, `Interactions.setting`, `Items.setting`, `Needs.setting`, `Boosts.setting`, `Translations.setting`, etc.) round-trip cleanly.

## Architecture

```
paralives_modgen/
  parser.py          .setting -> Setting / Collection / Item / FieldList
  serializer.py      Setting -> .setting text (round-trip aim: byte-identical)
  guid.py            Fresh 64-bit GUID generation via secrets
  cli.py             `modgen` argparse entrypoint
```

Key data types:

- **`Setting`** — a parsed file (header type + body)
- **`Collection`** — sized (`s<N>`) or sizeless collection of `Item`s
- **`Item`** — a collection member with `marker`/`key` (`i123`, `@123…`, `g123…`) and nested `fields`
- **`FieldList`** — ordered list of `(name, value)` pairs with dict-like API. Preserves duplicate field keys (required for round-tripping files like `Actions.setting` where some entities declare the same field twice).
- **`ScalarWithBody`** — rare edge case where a field has both a scalar value and nested content.

## Status

Early. Built in week 1 of Paralives Early Access while developing a content mod (BedComfortTiers — currently private). The library and the mod co-evolved: the mod stress-tested every parser feature, and the parser gained features as the mod's needs grew.

API may shift before v1.0. Issues and PRs welcome.

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

- Paralives Studio for shipping a moddable game with a transparent data format
- The base game files at `Main.mod/Settings/` for being the only documentation of the format
- Mod #22 [ParalivesModTool](https://www.nexusmods.com/paralives/mods/22) on Nexus — orthogonal scope (texture/mesh swap) but proved that non-content tools have a home in the Paralives modding ecosystem

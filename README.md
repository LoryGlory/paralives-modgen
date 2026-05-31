# modgen — Paralives mod generator

Hand-written `.setting` files are tedious and error-prone. This tool parses, manipulates, and emits Paralives `.setting` files programmatically.

## Status: v0.1 (parser + roundtrip)

The first job is to **fully understand the `.setting` format** by writing a parser that round-trips every base-game file byte-identical. Once that's solid, generation, manipulation, and templating follow naturally.

## Format overview

Plain text, indent-sensitive:

```
#Setting.<TypeName>
 =FieldName:ScalarValue
 =CollectionField
  s<size>
  i<index>
   =NestedField:Value
   =AnotherNested:Value
```

- Header line: `#Setting.<TypeName>`
- Scalar field: `<indent>=Name:Value`
- Collection field: `<indent>=Name` (no value on same line)
  - Followed by `<indent+1>s<size>` declaring item count
  - Then N blocks of `<indent+1>i<index>` containing nested fields
- Indentation: each level = 1 additional space
- GUID values: 19-digit positive integers, used as references between entities

### Extension syntax (mods extending existing entities)

When Control Panel writes a patch to an existing entity, it uses two
forms in addition to plain `i<index>`:

- **`g<GUID>`** — sibling of `i<index>` inside a collection. Targets the
  existing entity with that GUID and **adds/overrides** the nested fields.
  No `s<size>` declaration needed; treated as additive.
- **`@<GUID>`** — collection item identified by explicit GUID rather than
  by position. Appears inside `g<GUID>` extension blocks when adding
  new items to a sub-collection.

Example — adding an Outcome to a previously-declared Action:
```
  g3847562918374625981
   =Outcomes
    @3658370084533209955
     =GUID:3658370084533209955
     =Type:15
     =Timing:1
     =NeedToAffect:4125638617189434272
     =NeedReliefValue:0.5
```

modgen v0.1 doesn't yet parse/emit `g`/`@` markers — see roadmap.

### Discovered Outcome Type integers

| Int | Name | Fields |
|---|---|---|
| `15` | `RelieveNeedInUnitsPerHour` | `NeedToAffect`, `NeedReliefValue`, `Timing` |
| `330` | (Self-contained "is relieving Sleep" — used by base SleepInBed) | (no params) |

Timing enum: `0=Start, 1=During, 2=End, 3=EndOrCancel, 4=Cancel, 5=Prestart, 6=OnFinalDone`

See [`paralives_modgen/parser.py`](paralives_modgen/parser.py) for the authoritative grammar.

## Install

```bash
cd modgen
pip install -e .
```

Python 3.11+. No external dependencies.

## CLI

```bash
# Parse one file and print as JSON
modgen parse path/to/Foo.setting

# Verify round-trip on every .setting file in a directory
modgen verify path/to/Settings/

# Generate a fresh GUID
modgen guid
```

## Roadmap

| Version | Scope |
|---|---|
| v0.1 | Parser, serializer, round-trip verification, CLI |
| v0.2 | `g<GUID>` + `@<GUID>` syntax for extension patches; ordered key support for duplicate fields |
| v0.3 | All 159 base-game files round-trip byte-identical |
| v0.4 | Mod skeleton generator (manifest + Settings/ folder) |
| v0.5 | High-level config DSL (YAML/TOML → .setting bundle) |
| v0.6 | Schema introspection (auto-extract field shapes per entity type) |

## Project layout

```
modgen/
├── pyproject.toml
├── paralives_modgen/
│   ├── __init__.py
│   ├── parser.py       .setting → dict
│   ├── serializer.py   dict → .setting
│   ├── guid.py         GUID generation + registry
│   └── cli.py          argparse entry point
└── tests/
    └── test_roundtrip.py
```

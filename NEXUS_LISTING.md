# paralives-modgen — Nexus listing draft

## Title
**paralives-modgen — Python library & CLI for `.setting` file authoring**

## Short description
For modders: parse, manipulate, and emit Paralives `.setting` files programmatically. Build mods from YAML/CSV, automate bulk overrides, script the Control Panel.

## Full description

> **This is a developer tool**, not a content mod. If you're a player, you don't need to install this.

paralives-modgen is a Python library and CLI for working with Paralives' `.setting` file format programmatically. If you want to script mod generation — overriding 50 items from a spreadsheet, cloning an entity 20 times with computed parameters, generating translation entries from a localization file — this gives you the format as a Python data structure.

### What it does

- **Parses** any `.setting` file into typed Python dataclasses (`Setting`, `Collection`, `Item`, `FieldList`)
- **Emits** them back as `.setting` text with byte-identical round-trip on 138 of 159 base game files
- **Natively supports** the `@<GUID>` collection-merge and `g<GUID>` entity-extension syntax used by mods that add to base game collections (rather than replacing them)
- **CLI:** `modgen parse <file>`, `modgen verify <dir>`, `modgen guid`
- Pure stdlib, no external dependencies

### Why this exists

The official Control Panel UI is great for clicking together a few entities. It doesn't help when you want to:

- Override 50 furniture items with computed values
- Clone an existing entity 20 times with different parameters
- Generate `Translations.setting` entries from a CSV
- Write a build script that regenerates a mod from a YAML spec
- Diff your hand-authored `.setting` output against the Control Panel's output to learn the format

### Source & install

**Primary home: [github.com/LoryGlory/paralives-modgen](https://github.com/LoryGlory/paralives-modgen)** — the Nexus listing exists for discoverability; the actual install is from GitHub.

```bash
pip install git+https://github.com/LoryGlory/paralives-modgen.git
```

Or via [uv](https://docs.astral.sh/uv/) with PEP 723 inline metadata in your build script:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "paralives-modgen @ git+https://github.com/LoryGlory/paralives-modgen.git",
# ]
# ///
```

Then `uv run build.py` auto-installs and runs.

### Compatibility

- **Paralives 1.0 Early Access** (tested against game version 19867)
- Python 3.11+
- macOS / Linux / Windows

### Schema discoveries baked in

The hard-won knowledge from week 1 of EA, encoded so other modders don't have to relearn it:

- `@<GUID>` adds to existing collections — `i<index>` SILENTLY REPLACES them (this footgun cost the dev half a day)
- Internal sub-item GUIDs are global identifiers — must be unique across the entire game namespace
- Outcome Type:330 is engine-hardcoded to base SleepInBed — won't fire on cloned actions

See the [README](https://github.com/LoryGlory/paralives-modgen/blob/main/README.md) for the full format docs.

### License

MIT.

---

## Tags

`tool`, `utility`, `python`, `library`, `cli`, `modders resources`, `framework`, `sdk`, `parser`

## Category suggestions

**Nexus:** Utilities / Miscellaneous (no dedicated Tools category exists for Paralives yet)

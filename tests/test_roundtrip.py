"""Round-trip tests: serialize(parse(x)) == x byte-for-byte where possible."""

from __future__ import annotations

from pathlib import Path

import pytest

from paralives_modgen import parse, serialize


REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = REPO_ROOT / "reference-settings"


def _sample_files() -> list[Path]:
    if not REFERENCE_DIR.exists():
        return []
    candidates = ["Needs.setting", "Boosts.setting"]
    return [REFERENCE_DIR / name for name in candidates if (REFERENCE_DIR / name).exists()]


@pytest.mark.parametrize("path", _sample_files(), ids=lambda p: p.name)
def test_byte_identical_roundtrip(path: Path) -> None:
    original = path.read_text()
    setting = parse(original)
    emitted = serialize(setting)
    assert emitted == original, (
        f"Round-trip mismatch for {path.name}.\n"
        f"First diverging char index: "
        f"{next((i for i, (a, b) in enumerate(zip(emitted, original)) if a != b), -1)}"
    )


def test_parse_minimal_synthetic() -> None:
    text = (
        "#Setting.Foo\n"
        " =Bar:Hello\n"
        " =List\n"
        "  s2\n"
        "  i0\n"
        "   =Name:First\n"
        "  i1\n"
        "   =Name:Second\n"
    )
    setting = parse(text)
    assert setting.setting_type == "Foo"
    assert setting.body["Bar"] == "Hello"
    coll = setting.body["List"]
    assert len(coll.items) == 2
    assert coll.items[0].marker == "i"
    assert coll.items[0].key == 0
    assert coll.items[0].fields == {"Name": "First"}
    assert coll.items[0].inline_value is None
    assert serialize(setting) == text


def test_parse_at_guid_addition() -> None:
    """A collection can be extended by `@<GUID>` items (used by mods)."""
    text = (
        "#Setting.Foo\n"
        " =List\n"
        "  s1\n"
        "  @123456789012345678\n"
        "   =Name:Modded\n"
    )
    setting = parse(text)
    item = setting.body["List"].items[0]
    assert item.marker == "@"
    assert item.key == 123456789012345678
    assert item.fields == {"Name": "Modded"}
    assert serialize(setting) == text


def test_parse_g_guid_sizeless_extension() -> None:
    """`g<GUID>` extension blocks live in sizeless collections (no s<N>)."""
    text = (
        "#Setting.Foo\n"
        " =Items\n"
        "  g111222333444555666\n"
        "   =Outcomes\n"
        "    @777888999000111222\n"
        "     =GUID:777888999000111222\n"
        "     =Type:15\n"
    )
    setting = parse(text)
    items = setting.body["Items"]
    assert items.declared_size is None
    g_item = items.items[0]
    assert g_item.marker == "g"
    assert g_item.key == 111222333444555666
    outcomes = g_item.fields["Outcomes"]
    assert outcomes.declared_size is None
    assert outcomes.items[0].marker == "@"
    assert outcomes.items[0].key == 777888999000111222
    assert serialize(setting) == text

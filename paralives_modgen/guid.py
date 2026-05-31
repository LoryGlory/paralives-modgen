"""GUID generation for Paralives mod content.

Paralives GUIDs are 64-bit signed integers, rendered as positive 18-19 digit
numbers in `.setting` files. Range observed in base game: 1 to ~9.2 × 10^18.

We generate uniformly random values from the 19-digit range
(10^18, 9 × 10^18) — avoiding the bottom of the range where the base
game's deliberately small values (e.g., Main.mod's GUID:1) live.
"""

from __future__ import annotations

import secrets

MIN_GUID = 10**18
MAX_GUID = 9_000_000_000_000_000_000  # 9 × 10^18, safely inside int64 max


def new_guid() -> int:
    """Generate a fresh random 64-bit GUID using a CSPRNG."""
    # secrets.randbelow gives us cryptographic-quality randomness.
    span = MAX_GUID - MIN_GUID
    return MIN_GUID + secrets.randbelow(span)

"""UUIDv7 (RFC 9562): time-ordered ids, so B-tree inserts stay local. Python 3.10 has no uuid.uuid7()."""

from __future__ import annotations

import os
import time
import uuid

_last_ms = 0
_counter = 0


def uuid7() -> uuid.UUID:
    global _last_ms, _counter
    ms = time.time_ns() // 1_000_000
    if ms <= _last_ms:  # same millisecond (or clock went back): keep ids monotonic
        ms = _last_ms
        _counter = (_counter + 1) & 0xFFF
        if _counter == 0:
            ms += 1
    else:
        _counter = int.from_bytes(os.urandom(2), "big") & 0x7FF
    _last_ms = ms
    rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
    value = (ms & ((1 << 48) - 1)) << 80 | 0x7 << 76 | _counter << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)

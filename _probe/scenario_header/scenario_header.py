# -*- coding: utf-8 -*-
"""scenario_header.py -- deterministic structural locator for the RAW-DEFLATE stream
inside Age of Empires II: Definitive Edition scenario files (.aoe2scenario / .scx).

Pure Python stdlib (struct + zlib).  Does NOT import AoE2ScenarioParser.
Read-only: this module never writes to any file.

BACKGROUND / WHY THIS MODULE EXISTS
------------------------------------
An .aoe2scenario file is:  <uncompressed structured header> + <one RAW DEFLATE stream>
(wbits = -15; no zlib header, no adler32 trailer).

The file begins with a 4-byte ASCII scenario version ("1.53", "1.59", ...) but the
*length* of the structured header is variable (it contains two variable-length
fields: `scenario_instructions` and `creator_name`), so the deflate stream start
cannot be found by a constant offset, and a naive byte-offset brute force finds
mostly spurious matches (short bogus streams that happen to decode a few hundred
bytes before erroring out).

The field order below is taken from AoE2ScenarioParser's per-version
`versions/DE/v*/structure.json` (FileHeader retrievers), verified against the raw
bytes of real files (see SCENARIO_HEADER_REPORT.md).

CRITICAL CORRECTION (this is the whole point of the module)
-----------------------------------------------------------
The library's `structure.json` describes what *the library* writes, and it says
`individual_victories_used` exists only in 1.36/1.37 (removed in 1.40).  That is
NOT the rule that real game-shipped files follow: 1.35 files DO carry the field
(value 0) and 1.53 / 1.54 / 1.59 files DO NOT.  So field presence is decided here
by *structural validation + deflate acceptance*, not by a version allowlist.
"""

from __future__ import annotations

import struct
import zlib

__all__ = [
    "parse_file_header",
    "locate_deflate",
    "deflate_offset",
    "decompress_body",
    "MAGIC_UNKNOWN_VALUE",
]

# `unknown_value` is a constant sentinel the game writes into every FileHeader.
MAGIC_UNKNOWN_VALUE = 1000  # 0x3E8 == b"\xE8\x03\x00\x00"

# The two candidate FileHeader layouts, named by whether the deprecated
# `individual_victories_used` field is present.
LAYOUT_WITH_IVU = "with_individual_victories_used"
LAYOUT_WITHOUT_IVU = "without_individual_victories_used"

# Versions whose on-disk layout is *observed* to carry individual_victories_used.
# Used only to order candidate attempts; never to reject a layout.
_IVU_HINT_VERSIONS = frozenset({"1.35", "1.36", "1.37"})

_MAX_AMOUNT = 64          # amount_of_unknown_numbers sanity bound
_MAX_CREATOR_LEN = 256    # creator_name str32 byte-length sanity bound
_MAX_INSTRUCTIONS_LEN = 1 << 22  # 4 MiB sanity bound


class HeaderParseError(ValueError):
    """Raised when bytes cannot be interpreted as a plausible FileHeader."""


def _u32(b: bytes, off: int) -> int:
    if off + 4 > len(b):
        raise HeaderParseError(f"u32 read past end of file at offset {off}")
    return struct.unpack_from("<I", b, off)[0]


def _s32(b: bytes, off: int) -> int:
    if off + 4 > len(b):
        raise HeaderParseError(f"s32 read past end of file at offset {off}")
    return struct.unpack_from("<i", b, off)[0]


def _str32(b: bytes, off: int, max_len: int, what: str):
    """u32 byte-length prefix followed by that many raw bytes."""
    n = _u32(b, off)
    off += 4
    if n > max_len:
        raise HeaderParseError(f"{what}: implausible length {n}")
    if off + n > len(b):
        raise HeaderParseError(f"{what}: length {n} runs past end of file")
    return b[off:off + n], off + n


def parse_file_header(b: bytes, layout: str) -> dict:
    """Parse the uncompressed FileHeader of an .aoe2scenario file.

    Returns a dict of every field plus `deflate_offset` (== first byte of the
    RAW DEFLATE stream) and `header_bytes` (the raw header slice).

    Raises HeaderParseError when `layout` is inconsistent with the bytes.
    """
    if len(b) < 8:
        raise HeaderParseError("file too small to be a scenario")
    version = b[0:4].decode("ascii", "replace")
    # NOTE (measured): the version tag is NOT reliable.  Real shipped files contain
    # corrupted tags such as b"1.5\x00" (K1_Tamerlane_5.aoe2scenario inside
    # kcam1.aoe2campaign).  We therefore only require the "1." major-minor prefix
    # and let the structural parse + deflate acceptance be the real gate.
    if not (len(version) == 4 and version[0] == "1" and version[1] == "."):
        raise HeaderParseError(f"bad version tag {b[0:4]!r}")

    h = {"version": version, "_size": len(b)}
    off = 4
    h["header_length"] = _u32(b, off); off += 4
    h["savable"] = _s32(b, off); off += 4
    h["timestamp_of_last_save"] = _u32(b, off); off += 4
    instr, off = _str32(b, off, _MAX_INSTRUCTIONS_LEN, "scenario_instructions")
    h["scenario_instructions"] = instr

    if layout == LAYOUT_WITH_IVU:
        h["individual_victories_used"] = _u32(b, off); off += 4
    elif layout != LAYOUT_WITHOUT_IVU:
        raise HeaderParseError(f"unknown layout {layout!r}")

    h["player_count"] = _u32(b, off); off += 4
    h["unknown_value"] = _u32(b, off); off += 4
    h["unknown_value_2"] = _u32(b, off); off += 4
    amount = _u32(b, off); off += 4
    h["amount_of_unknown_numbers"] = amount
    if amount > _MAX_AMOUNT:
        raise HeaderParseError(f"amount_of_unknown_numbers implausible: {amount}")
    nums = []
    for _ in range(amount):
        nums.append(_u32(b, off)); off += 4
    h["unknown_numbers"] = nums
    creator, off = _str32(b, off, _MAX_CREATOR_LEN, "creator_name")
    h["creator_name"] = creator
    h["trigger_count"] = _u32(b, off); off += 4

    h["deflate_offset"] = off
    h["header_bytes"] = b[:off]
    h["layout"] = layout
    return h


def _plausible(h: dict) -> bool:
    """Structural sanity of a parsed header, independent of the deflate stream."""
    if h["unknown_value"] != MAGIC_UNKNOWN_VALUE:
        return False
    if not (0 < h["player_count"] <= 16):
        return False
    if not (0 <= h["amount_of_unknown_numbers"] <= _MAX_AMOUNT):
        return False
    if len(h["scenario_instructions"]) > _MAX_INSTRUCTIONS_LEN:
        return False
    if len(h["creator_name"]) > _MAX_CREATOR_LEN:
        return False
    if h["deflate_offset"] >= h["_size"]:
        return False
    return True


def decompress_body(b: bytes, offset: int):
    """Raw-inflate b[offset:].  Returns (data, eof, error_message)."""
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        out = d.decompress(b[offset:])
        out += d.flush()
    except zlib.error as e:
        return b"", False, f"zlib.error: {e}"
    if not d.eof:
        return out, False, "stream did not reach end-of-stream (truncated / wrong offset)"
    return out, True, None


def candidate_layouts(version: str):
    """Order the two layouts by the version string hint (hint only, never a veto)."""
    if version in _IVU_HINT_VERSIONS:
        return (LAYOUT_WITH_IVU, LAYOUT_WITHOUT_IVU)
    return (LAYOUT_WITHOUT_IVU, LAYOUT_WITH_IVU)


def locate_deflate(b: bytes, version: str | None = None, min_output: int = 1000):
    """Deterministically locate the RAW DEFLATE stream start of a scenario.

    Strategy (no brute-force byte scanning):
      1. read the 4-byte version tag;
      2. parse the FileHeader with each candidate layout, in hint order;
      3. keep only layouts that are *structurally* plausible
         (unknown_value == 1000, sane counts, in-bounds);
      4. the winner is the one whose candidate offset actually raw-inflates to
         end-of-stream with at least `min_output` bytes.

    Returns (header_or_None, data_or_None, diagnostics_dict).
    """
    diag = {"version": None, "attempts": [], "reason": None}
    try:
        ver = version or b[0:4].decode("ascii")
    except Exception:
        diag["reason"] = "cannot decode version tag"
        return None, None, diag
    diag["version"] = ver

    fallback = None
    for layout in candidate_layouts(ver):
        try:
            h = parse_file_header(b, layout)
        except HeaderParseError as e:
            diag["attempts"].append({"layout": layout, "error": str(e)})
            continue
        if h["deflate_offset"] >= len(b):
            diag["attempts"].append({"layout": layout, "error": "deflate_offset past EOF",
                                     "deflate_offset": h["deflate_offset"]})
            continue
        struct_ok = _plausible(h)
        data, eof, err = decompress_body(b, h["deflate_offset"])
        diag["attempts"].append({
            "layout": layout,
            "deflate_offset": h["deflate_offset"],
            "structurally_plausible": struct_ok,
            "unknown_value": h["unknown_value"],
            "player_count": h["player_count"],
            "amount_of_unknown_numbers": h["amount_of_unknown_numbers"],
            "creator_len": len(h["creator_name"]),
            "decompress_eof": eof,
            "decompress_bytes": len(data),
            "error": err,
        })
        if eof and len(data) >= min_output and struct_ok:
            return h, data, diag
        if eof and len(data) >= min_output and fallback is None:
            fallback = (h, data)
    if fallback is not None:
        return fallback[0], fallback[1], diag
    diag["reason"] = "no candidate layout produced an end-of-stream raw deflate stream"
    return None, None, diag


def deflate_offset(b: bytes, version: str | None = None):
    h, data, diag = locate_deflate(b, version)
    return (h["deflate_offset"] if h else None), diag


# ---------------------------------------------------------------------------
# AoE2ScenarioParser-compatible oracle path (optional, for cross-checking only)
# ---------------------------------------------------------------------------
def library_oracle(path: str):
    """If AoE2ScenarioParser is importable, return (ok, deflate_offset_of_first_body).

    The library does not expose the header length directly, so we measure it by
    re-compressing... instead we simply report whether `AoE2Scenario.from_file`
    succeeds and the length of `_file_header`.  Purely a cross-check.
    """
    try:
        from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    except Exception as e:  # pragma: no cover
        return None, f"library not importable: {e}"
    try:
        s = AoE2DEScenario.from_file(path)
        fh = getattr(s, "_file_header", None)
        return {"header_len": len(fh) if fh is not None else None,
                "version": getattr(s, "scenario_version", None)}, None
    except Exception as e:  # pragma: no cover
        return None, f"{type(e).__name__}: {e}"

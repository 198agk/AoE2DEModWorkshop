# -*- coding: utf-8 -*-
"""header_layout.py -- DETERMINISTIC structural locator for the RAW-DEFLATE stream
inside Age of Empires II: Definitive Edition scenario files.

Pure stdlib (struct + zlib).  Does NOT import AoE2ScenarioParser.
READ-ONLY: never writes anything.

=============================================================================
THE ANSWER (one line)
=============================================================================
    deflate_offset = HEADER_LAYOUT[savable].size(bytes)

`savable` is the little-endian signed int32 at byte offset 8.  It is a
FORMAT-GENERATION number written by the game.  It is NOT the library's
`savable` field (that is a different, per-version cosmetic default: 6 in
every shipped v1.36..v1.59 schema).  The real file's savable selects the
header grammar outright:

    savable  layout      generation                       seen in
    -------  ----------  -------------------------------  -------------------
       2     L_SHORT     legacy short                     1.21
       3     L_LONG_NC   legacy long, no creator_name     1.21
       4     L_LONG_C    legacy long + creator_name       1.33
       5     M_IVU       modern + individual_victories    1.35, 1.36, 1.37
       6     M_NOIVU     modern, IVU removed              1.40 .. 1.59

There is NO search, NO brute force, NO candidate loop.  savable picks the
grammar; the grammar's variable-length str32 fields are read to their
declared length and the stream starts at the first byte after the last
field.  One read of one int32 decides everything.

WHY BRUTE FORCE FAILED (the falsified strategy)
-----------------------------------------------
Scanning every byte offset for something that raw-inflates finds thousands
of *spurious* streams: at most offsets a short garbage deflate block happens
to decode a few hundred bytes before hitting an invalid code.  Only the true
offset decodes the entire body AND reaches end-of-stream with d.eof == True.
The report previously cited "0 hits across the first 200,000 offsets" for
The Siege -- that measurement was taken against the wrong acceptance test
(and the wrong offset 4).  The true offset is 83.

STRUCTURAL DIFFERENCE: pre-1.36 vs 1.36+
----------------------------------------
Common prefix (all generations):
    version            c4      bytes 0..4      ASCII "1.53" etc. (sometimes corrupt)
    header_length      u32     bytes 4..8
    savable            s32     bytes 8..12     -> SELECTS THE LAYOUT
    timestamp_of_last_save u32 bytes 12..16
    scenario_instructions  str32  (u32 byte length + that many raw bytes)

  * Lengths here are BYTE lengths, not code-point counts and NOT NUL-padded.
    `default0.aoe2scenario` (1.59) has a 1107-byte UTF-8 (CJK) instruction
    blob, which is why its stream starts at 1183, not near 80.
  * A u32-at-a-time walk starting at offset 4 is INVALID for every file whose
    scenario_instructions length is not a multiple of 4 -- it walks off the
    true field grid and prints garbage (2048, 256000, 512, ...).
  * Legacy files (savable 2/3/4) in addition carry, right after the
    instructions, a u32 whose name is not documented anywhere; measured 0 in
    every legacy file examined.
  * `individual_victories_used` is NOT gated on the version tag.  It is gated
    on savable: present iff savable == 5.  Real 1.35 files carry it, real
    1.53/1.59 files do not; the library only knows 1.36/1.37 because those
    are the only IVU-era versions it ships schemas for.
  * L_LONG_NC/L_LONG_C keep the `unknown_value == 1000` sentinel and the
    `unknown_numbers` array; L_SHORT has NEITHER.
  * Trigger count is absent from all legacy variants and from L_LONG_*;
    it exists only in the modern layouts.
"""

from __future__ import annotations

import struct
import zlib

__all__ = [
    "SAVABLE_LAYOUT", "LOCATE_FAILED",
    "read_version", "read_savable", "field_offsets", "locate",
    "inflate_body", "parse_header", "HeaderParseError",
]

VERSION = 0          # c4
HEADER_LENGTH = 4    # u32
SAVABLE = 8          # s32   <-- the selector
TIMESTAMP = 12       # u32
INSTRUCTIONS = 16    # str32 (variable) -- everything after is at a variable offset

SENTINEL_UNKNOWN_VALUE = 1000   # 0x3E8, written by the game in "modern" grammars

MAX_AMOUNT = 64
MAX_CREATOR = 256
MAX_INSTRUCTIONS = 1 << 22      # 4 MiB

L_SHORT = "L_SHORT"
L_LONG_NC = "L_LONG_NC"
L_LONG_C = "L_LONG_C"
M_IVU = "M_IVU"
M_NOIVU = "M_NOIVU"

SAVABLE_LAYOUT = {
    2: L_SHORT,
    3: L_LONG_NC,
    4: L_LONG_C,
    5: M_IVU,
    6: M_NOIVU,
}

LOCATE_FAILED = "LOCATE_FAILED"


class HeaderParseError(ValueError):
    """The bytes do not satisfy the grammar selected by `savable`."""


# ---------------------------------------------------------------------------
# primitive readers
# ---------------------------------------------------------------------------
def _need(b: bytes, off: int, n: int, what: str) -> None:
    if off < 0 or off + n > len(b):
        raise HeaderParseError(f"{what}: need {n} bytes at {off}, file is {len(b)}")


def _u32(b: bytes, off: int, what: str = "u32") -> int:
    _need(b, off, 4, what)
    return struct.unpack_from("<I", b, off)[0]


def _s32(b: bytes, off: int, what: str = "s32") -> int:
    _need(b, off, 4, what)
    return struct.unpack_from("<i", b, off)[0]


def _str32(b: bytes, off: int, cap: int, what: str):
    n = _u32(b, off, what + ".length")
    off += 4
    if n > cap:
        raise HeaderParseError(f"{what}: length {n} exceeds cap {cap}")
    _need(b, off, n, what)
    return b[off:off + n], off + n


def read_version(b: bytes) -> str:
    """4-byte ASCII version tag.  Measured to be UNRELIABLE: a real shipped
    campaign member carries b'1.5\\x00'.  Never gate a decision on it."""
    return b[0:4].decode("ascii", "replace")


def read_savable(b: bytes) -> int:
    """The layout selector.  One read; this is the whole algorithm."""
    return _s32(b, SAVABLE, "savable")


# ---------------------------------------------------------------------------
# the grammar
# ---------------------------------------------------------------------------
def field_offsets(b: bytes, layout: str) -> dict:
    """Walk the FileHeader for `layout` and return every field offset/size.

    Raises HeaderParseError if the bytes do not fit the grammar.
    """
    _need(b, 0, INSTRUCTIONS, "FileHeader prefix")

    o = 4
    f = {}
    f["header_length"] = (o, 4); o += 4
    f["savable"] = (o, 4); o += 4
    f["timestamp_of_last_save"] = (o, 4); o += 4

    instr, o = _str32(b, o, MAX_INSTRUCTIONS, "scenario_instructions")
    f["scenario_instructions"] = (INSTRUCTIONS, 4 + len(instr))

    if layout == L_SHORT:
        # ...instructions, <legacy u32>, player_count
        f["legacy_unknown_after_instructions"] = (o, 4); o += 4
        f["player_count"] = (o, 4); o += 4
        pc = _u32(b, o - 4, "player_count")
        return _finish(f, o, layout, instr, b"", [], pc, None)

    # every other legacy/modern grammar carries these
    if layout in (L_LONG_NC, L_LONG_C):
        f["legacy_unknown_after_instructions"] = (o, 4); o += 4
    elif layout == M_IVU:
        f["individual_victories_used"] = (o, 4); o += 4
    elif layout != M_NOIVU:
        raise HeaderParseError(f"unknown layout {layout!r}")

    f["player_count"] = (o, 4)
    pc = _u32(b, o, "player_count"); o += 4

    f["unknown_value"] = (o, 4)
    uv = _u32(b, o, "unknown_value"); o += 4
    if uv != SENTINEL_UNKNOWN_VALUE:
        raise HeaderParseError(
            f"{layout}: unknown_value is {uv}, expected {SENTINEL_UNKNOWN_VALUE}")

    f["unknown_value_2"] = (o, 4); o += 4
    f["amount_of_unknown_numbers"] = (o, 4)
    amount = _u32(b, o, "amount_of_unknown_numbers"); o += 4
    if amount > MAX_AMOUNT:
        raise HeaderParseError(f"amount_of_unknown_numbers implausible: {amount}")
    f["unknown_numbers"] = (o, 4 * amount)
    nums = [_u32(b, o + 4 * i, "unknown_numbers") for i in range(amount)]
    o += 4 * amount

    creator = b""
    if layout in (L_LONG_C, M_IVU, M_NOIVU):
        f["creator_name"] = (o, None)
        creator, o = _str32(b, o, MAX_CREATOR, "creator_name")
        f["creator_name"] = (f["creator_name"][0], 4 + len(creator))

    trig = None
    if layout in (M_IVU, M_NOIVU):
        f["trigger_count"] = (o, 4)
        trig = _u32(b, o, "trigger_count"); o += 4

    return _finish(f, o, layout, instr, creator, nums, pc, trig)


def _finish(f, o, layout, instr, creator, nums, pc, trig):
    f["_deflate_offset"] = (o, 0)
    f["_layout"] = layout
    f["_instructions"] = instr
    f["_creator"] = creator
    f["_numbers"] = nums
    f["_player_count"] = pc
    f["_trigger_count"] = trig
    return f


def parse_header(b: bytes, layout: str | None = None) -> dict:
    """Parse the FileHeader; `layout` defaults to SAVABLE_LAYOUT[savable]."""
    if layout is None:
        layout = SAVABLE_LAYOUT.get(read_savable(b))
        if layout is None:
            raise HeaderParseError(f"no grammar registered for savable={read_savable(b)}")
    return field_offsets(b, layout)


def inflate_body(b: bytes, offset: int):
    """RAW-inflate b[offset:].  Returns (data, reached_eof, error_or_None).

    wbits = -15: raw DEFLATE, no zlib header, no adler32 trailer.
    """
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        out = d.decompress(b[offset:])
        out += d.flush()
    except zlib.error as e:
        return b"", False, f"zlib.error: {e}"
    if not d.eof:
        return out, False, "stream did not reach end-of-stream"
    return out, True, None


# ---------------------------------------------------------------------------
# THE locator: dispatch on savable.  No candidates, no scanning.
# ---------------------------------------------------------------------------
def locate(b: bytes, min_output: int = 1000):
    """Return (deflate_offset, layout, body_bytes, diagnostics).

    deflate_offset is None when savable is unregistered or the grammar is
    inconsistent with the bytes.  No byte-offset search is performed.
    """
    diag = {"version": read_version(b), "savable": None, "reason": None}
    try:
        sav = read_savable(b)
    except HeaderParseError as e:
        diag["reason"] = f"cannot read savable: {e}"
        return None, None, None, diag
    diag["savable"] = sav

    layout = SAVABLE_LAYOUT.get(sav)
    if layout is None:
        diag["reason"] = f"savable={sav} has no registered grammar"
        return None, None, None, diag

    try:
        h = field_offsets(b, layout)
    except HeaderParseError as e:
        diag["reason"] = f"{layout}: {e}"
        return None, None, None, diag

    off = h["_deflate_offset"][0]
    if off >= len(b):
        diag["reason"] = f"{layout}: deflate offset {off} >= file size {len(b)}"
        return None, layout, None, diag

    data, eof, err = inflate_body(b, off)
    if not eof:
        diag["reason"] = f"{layout}: inflation at {off} failed: {err}"
        return off, layout, None, diag
    if len(data) < min_output:
        diag["reason"] = f"{layout}: inflated only {len(data)} bytes at {off}"
        return off, layout, data, diag

    return off, layout, data, diag

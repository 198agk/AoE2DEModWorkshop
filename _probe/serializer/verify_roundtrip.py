# -*- coding: utf-8 -*-
"""Prove the AoE2 DE .dat re-serializer is byte-exact and idempotent.

Two loops are run against the real BASE file:

  Loop 1 (round-trip)   decompress -> parse -> serialize -> compare to the
                        original decompressed bytes.  Reports sha256 of both
                        streams, the first differing offset with +/-32 bytes of
                        hex context, and the total differing byte count.

  Loop 2 (idempotence)  parse -> serialize -> parse the serialized output ->
                        serialize again.  The two serializations must be
                        identical; this proves the writer is idempotent AND
                        that the parsed model is lossless with respect to it.
                        All model counters from the SECOND parse are printed so
                        any drift is visible (civs / techs / effects /
                        graphics / units / sounds / terrains).

Also asserts the writer's internal model-vs-original mismatch count is 0 and
that the writer consumed exactly the raw stream (no skipped or repeated bytes).

Run:  python verify_roundtrip.py [path-to-dat]
Exit: 0 on full success, 1 on any failure.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import contextlib
import _gamepaths as GP
import hashlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))

import parse_dat
import write_dat

DEFAULT_BASE = (GP.DAT_DIR +
                r"\empires2_x2_p1.dat")

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CONTEXT = 32

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def parse_bytes(data):
    """Parse a decompressed stream, suppressing the parser's stage logging."""
    p = parse_dat.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        stats = p.parse()
    return p, stats

def compare(a, b, label_a="A", label_b="B"):
    """Return (equal, first_diff, diff_count, n_common)."""
    n = min(len(a), len(b))
    first = None
    count = 0
    # fast path: locate the first difference by comparing in blocks
    step = 1 << 16
    off = 0
    while off < n and first is None:
        end = min(n, off + step)
        if a[off:end] != b[off:end]:
            for i in range(off, end):
                if a[i] != b[i]:
                    first = i
                    break
        off = end
    if first is not None:
        count = sum(1 for i in range(first, n) if a[i] != b[i])
    equal = (first is None) and (len(a) == len(b))
    return equal, first, count, n

def hex_context(data, off, width=CONTEXT):
    lo = max(0, off - width)
    hi = min(len(data), off + width)
    out = []
    for row in range(lo, hi, 16):
        chunk = data[row:min(hi, row + 16)]
        h = " ".join("%02X" % c for c in chunk)
        t = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        mark = " <-- " if row <= off < row + 16 else "     "
        out.append("    %08X  %-47s  %s%s" % (row, h, t, mark))
    return "\n".join(out)

def counters(stats):
    """Every counter that would move if parsing had drifted."""
    civs = stats["civs"]
    units = sum(len(c["units"]) for c in civs)
    unit_ptrs = sum(c.get("unit_pointers_total", 0) for c in civs)
    return {
        "civs": len(civs),
        "unit_objects": units,
        "unit_pointers": unit_ptrs,
        "techs": len(stats["techs"]),
        "effects": len(stats["effects"]),
        "effect_commands": sum(len(e["commands"]) for e in stats["effects"]),
        "graphics": len(stats["graphics"]),
        "graphic_count_field": stats.get("graphic_count"),
        "sounds": len(stats["sounds"]),
        "sound_items": sum(len(s["items"]) for s in stats["sounds"]),
        "unit_headers": len(stats["unit_headers"]),
        "terrain_restrictions": len(stats["terrain_restrictions"]),
        "player_colours": len(stats["player_colours"]),
        "terrains": len(stats.get("terrain_block", {}).get("terrains", [])),
        "deltas": sum(len(g.get("deltas", [])) for g in stats["graphics"]),
    }

def main(argv):
    base = argv[1] if len(argv) > 1 else DEFAULT_BASE
    ok = True
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("=" * 78)
    say("AoE2 DE .dat re-serializer verification")
    say("=" * 78)
    say("source        : %s" % base)

    raw, how = write_dat.load_dat(base)
    say("decompression : %s" % how)
    say("raw size      : %d bytes" % len(raw))
    say("raw sha256    : %s" % sha256(raw))
    say()

    # ------------------------------------------------------------------
    # Loop 1: parse -> serialize, compare to original
    # ------------------------------------------------------------------
    say("-" * 78)
    say("LOOP 1 -- round-trip: parse -> serialize -> compare to original")
    say("-" * 78)
    p1, st1 = parse_bytes(raw)
    say("parsed        : final offset %d  leftover %d"
        % (p1.r.pos, len(raw) - p1.r.pos))
    if p1.r.pos != len(raw):
        say("!! parser did not consume the whole stream")
        ok = False

    out1, rep1 = write_dat.serialize_dat(st1, raw=raw, strict=True)
    say("serialized    : %d bytes" % len(out1))
    say("out sha256    : %s" % sha256(out1))
    say("model bytes   : %d (%.2f%%)" % (rep1["model_bytes"], rep1["model_pct"]))
    say("opaque bytes  : %d (%.2f%%) in %d verbatim sites"
        % (rep1["opaque_bytes"], rep1["opaque_pct"], rep1["opaque_sites"]))
    say("writer raw consumed : %d / %d" % (rep1["raw_consumed"], len(raw)))
    say("model-vs-raw mismatches : %d" % rep1["model_vs_original_mismatches"])

    if rep1["model_vs_original_mismatches"] != 0:
        fm = rep1["first_model_mismatch"]
        say("!! first model mismatch at raw offset 0x%06X (%d): kind=%s"
            % (fm[0], fm[0], fm[2]))
        say("   model : %s" % fm[3].hex())
        say("   raw   : %s" % fm[4].hex())
        say("   context (model):")
        say(hex_context(fm[3], 0, min(32, len(fm[3]))))
        ok = False
    if rep1["raw_consumed"] != len(raw):
        say("!! writer consumed %d raw bytes, expected %d"
            % (rep1["raw_consumed"], len(raw)))
        ok = False

    equal, first, ndiff, ncommon = compare(out1, raw, "serialized", "original")
    say("identical     : %s" % ("YES" if equal else "NO"))
    if not equal:
        ok = False
        if first is not None:
            say("first diff at : 0x%06X (%d)" % (first, first))
            say("   original context:")
            say(hex_context(raw, first))
            say("   serialized context:")
            say(hex_context(out1, first))
        say("differing bytes : %d of %d compared (len A=%d len B=%d)"
            % (ndiff, ncommon, len(out1), len(raw)))
    say()

    # ------------------------------------------------------------------
    # Loop 2: parse the serialized output again and re-serialize
    # ------------------------------------------------------------------
    say("-" * 78)
    say("LOOP 2 -- idempotence: parse(serialized) -> serialize again")
    say("-" * 78)
    p2, st2 = parse_bytes(out1)
    say("re-parse      : final offset %d  leftover %d"
        % (p2.r.pos, len(out1) - p2.r.pos))
    if p2.r.pos != len(out1):
        say("!! re-parse did not consume the whole stream (drift!)")
        ok = False

    out2, rep2 = write_dat.serialize_dat(st2, raw=out1, strict=True)
    say("reserialized  : %d bytes" % len(out2))
    say("out2 sha256   : %s" % sha256(out2))
    say("model bytes   : %d (%.2f%%)" % (rep2["model_bytes"], rep2["model_pct"]))
    say("opaque bytes  : %d (%.2f%%) in %d verbatim sites"
        % (rep2["opaque_bytes"], rep2["opaque_pct"], rep2["opaque_sites"]))
    say("model-vs-raw mismatches : %d" % rep2["model_vs_original_mismatches"])

    eq2, first2, ndiff2, nc2 = compare(out2, out1, "serialization 2",
                                       "serialization 1")
    say("serialization1 == serialization2 : %s" % ("YES" if eq2 else "NO"))
    if not eq2:
        ok = False
        if first2 is not None:
            say("first diff at : 0x%06X (%d)" % (first2, first2))
            say(hex_context(out1, first2))
        say("differing bytes : %d of %d" % (ndiff2, nc2))
    say()

    # ------------------------------------------------------------------
    # Counter comparison between the two parses
    # ------------------------------------------------------------------
    say("-" * 78)
    say("COUNTERS (parse 1 vs parse 2 -- any change means model drift)")
    say("-" * 78)
    c1 = counters(st1)
    c2 = counters(st2)
    drifted = []
    say("  %-26s %12s %12s   %s" % ("counter", "parse 1", "parse 2", "same?"))
    for k in c1:
        same = c1[k] == c2[k]
        if not same:
            drifted.append(k)
        say("  %-26s %12s %12s   %s"
            % (k, c1[k], c2[k], "yes" if same else "NO <<<"))
    if drifted:
        say("!! counters drifted: %s" % ", ".join(drifted))
        ok = False
    say()

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    say("=" * 78)
    if ok and equal and eq2:
        say("VERDICT: BYTE-EXACT ROUND-TRIP ACHIEVED")
    else:
        say("VERDICT: NOT ACHIEVED")
    say("=" * 78)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "verify_roundtrip.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0 if (ok and equal and eq2) else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

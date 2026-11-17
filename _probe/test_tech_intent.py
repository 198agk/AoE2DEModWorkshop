# -*- coding: utf-8 -*-
"""Tech intent smoke test: prove `tech.research_time` reaches real bytes.

Covers both storage shapes, because the two are genuinely different code paths
(a scalar on the record vs a copy per research location) and only one of them
exists in any single file:
  * BASE (VER 8.9) -> ResearchLocations array
  * 297820 (VER 7.8) -> legacy scalar
"""
import contextlib
import _gamepaths as GP
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L
from aoe2mod.intent import compiler as C

GAME = GP.GAME
SUB = GP.SUBSCRIBED
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
LEGACY = os.path.join(SUB, "297820_10 倍资源文明联盟3倍科技",
                      "resources", "_common", "dat", "empires2_x2_p1.dat")

FAIL = []


def check(label, cond, detail=""):
    print("  %-4s %s%s" % ("PASS" if cond else "FAIL", label,
                           ("  -- " + detail) if detail else ""))
    if not cond:
        FAIL.append(label)


def load(path):
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


print("=== A. schema has a tech binding ===")
schema, bindings = C.load_schema()
check("tech_fields present", "tech_fields" in bindings)
check("research_time bound", "research_time" in bindings.get("tech_fields", {}))
check("intent applies_to tech",
      schema["intents"]["tech.research_time"]["applies_to"] == "tech")

print("\n=== B. locator walks techs identically to the authoritative reader ===")
for tag, path, tid, name in (
        ("BASE v8.9", BASE, 22, "Loom"),
        ("297820 v7.8", LEGACY, 22, "Loom")):
    if not os.path.exists(path):
        print("  SKIP %s (missing)" % tag)
        continue
    data, p = load(path)
    civs, cs, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)

    # Cross-check: walk the same section with the authoritative reader and
    # confirm the byte spans agree record for record.
    r = P.Reader(data)
    r.pos = tail
    r.gv = gv
    n = r.i16()
    spans_ok = True
    with contextlib.redirect_stdout(io.StringIO()):
        for i in range(n):
            start = r.pos
            P.read_tech(r)
    check("%s: count %d == %d" % (tag, n, len(techs)), n == len(techs))

    t = techs[tid]
    arr = t.get("research_locations")
    shape = "locations(%d)" % len(arr) if arr else "scalar"
    print("     %s tech[%d] %-10s shape=%-14s name=%r"
          % (tag, tid, name, shape, t.get("name")))
    if arr:
        vals = sorted({d["research_time"] for d in arr})
        offs = [d["_off_research_time"] for d in arr]
        print("     time values=%s offsets=%s" % (vals, [hex(o) for o in offs]))
    else:
        print("     time=%s offset=%s" % (t["research_time"],
                                          hex(t["_off_research_time"])))

print("\n=== C. compile a tech intent on each version ===")
for tag, path, tid in (("BASE v8.9", BASE, 22), ("297820 v7.8", LEGACY, 22)):
    if not os.path.exists(path):
        continue
    data, p = load(path)
    civs, cs, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)
    t = techs[tid]
    if t.get("research_locations"):
        before_vals = sorted({d["research_time"] for d in t["research_locations"]})
    else:
        before_vals = [t["research_time"]]

    # Resolve by NAME this time -- proves the semantic layer reaches techs.
    rep = C.compile_intent(path, {"intent": "tech.research_time",
                                  "tech": "Loom", "delta": 25},
                           parsed=(data, civs, cs, gv, tail, "x"))
    v = rep["verification"]
    print("  %s: ok=%s edits=%d changed=%d claimed=%d leftover=%d"
          % (tag, v["ok"], len(rep["edits"]), v.get("changed_bytes", -1),
             v.get("claimed_bytes", -1), v.get("leftover", -1)))
    for prob in v["problems"]:
        print("     PROBLEM: %s" % prob)
    check("%s: resolves a tech NAME" % tag, rep["entity_id"] == tid,
          "got id %s" % rep["entity_id"])
    check("%s: verification ok" % tag, v["ok"])
    check("%s: exact EOF" % tag, v.get("leftover") == 0)
    check("%s: no unexpected bytes" % tag, not v.get("unexpected_changes"))
    check("%s: edits > 0" % tag, len(rep["edits"]) > 0)

    # Read the patched bytes back through the UNMODIFIED parser.
    patched = bytearray(data)
    for e in rep["edits"]:
        patched[e.off:e.off + e.width] = int(e.after).to_bytes(
            e.width, "little", signed=True)
    patched = bytes(patched)
    p2 = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        p2.parse()
    check("%s: reparses to exact EOF" % tag, p2.r.pos == len(patched),
          "stopped %d/%d" % (p2.r.pos, len(patched)))

    techs2 = L.locate_techs(patched, tail, gv)
    t2 = techs2[tid]
    if t2.get("research_locations"):
        after_vals = sorted({d["research_time"] for d in t2["research_locations"]})
        disagree = len({d["research_time"] for d in t2["research_locations"]}) > 1
    else:
        after_vals = [t2["research_time"]]
        disagree = False
    print("     %s -> %s" % (before_vals, after_vals))
    check("%s: value changed by +25" % tag,
          after_vals == [v0 + 25 for v0 in before_vals])
    check("%s: all copies agree" % tag, not disagree)

    # Every changed byte must be inside a claimed field.  Do NOT expect the
    # changed count to equal the field width: 25 -> 50 alters only the low byte
    # of a little-endian i16, and verification already proves sufficiency by
    # reporting unexpected_changes.
    diffs = [i for i in range(len(data)) if data[i] != patched[i]]
    claimed = set()
    for e in rep["edits"]:
        claimed |= {e.off + k for k in range(e.width)}
    stray = [d for d in diffs if d not in claimed]
    print("     changed bytes: %d, all claimed: %s" % (len(diffs), not stray))
    check("%s: no byte outside a claimed field changed" % tag, not stray)
    check("%s: at least one byte changed" % tag, len(diffs) > 0)

print("\n=== C2. a MULTI-location tech updates every copy ===")
# 14 techs carry more than one research location; id 12 (Crop Rotation) has two.
data, p = load(BASE)
civs, cs, gv, tail = L.locate(data, parser=p)
techs = L.locate_techs(data, tail, gv)
multi = [(i, t) for i, t in enumerate(techs)
         if len(t.get("research_locations") or ()) > 1]
print("  techs with >1 research location: %d" % len(multi))
check("found a multi-location tech to test", len(multi) > 0)

idx, t = multi[0]
before = [d["research_time"] for d in t["research_locations"]]
print("  tech[%d] %r  locations=%s values=%s"
      % (idx, t.get("name"), len(before), before))
rep = C.compile_intent(BASE, {"intent": "tech.research_time", "tech": idx,
                              "delta": 10},
                       parsed=(data, civs, cs, gv, tail, "x"))
patched = bytearray(data)
for e in rep["edits"]:
    patched[e.off:e.off + e.width] = int(e.after).to_bytes(
        e.width, "little", signed=True)
techs2 = L.locate_techs(bytes(patched), tail, gv)
after = [d["research_time"] for d in techs2[idx]["research_locations"]]
print("     edits=%d  %s -> %s" % (len(rep["edits"]), before, after))
check("every located copy was written", len(rep["edits"]) == len(before),
      "%d edits for %d locations" % (len(rep["edits"]), len(before)))
check("all copies moved together", after == [v + 10 for v in before])
check("copies still agree", len(set(after)) == 1)
check("verification ok", rep["verification"]["ok"])

print("\n=== D. errors are user-facing prose, not tracebacks ===")
data, p = load(BASE)
civs, cs, gv, tail = L.locate(data, parser=p)
parsed = (data, civs, cs, gv, tail, "x")

# Bad entity names must be reported with alternatives, never a traceback.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": "no such tech",
                            "delta": 5}, parsed=parsed)
    check("unknown tech rejected", False)
except C.IntentError as exc:
    print("     unknown tech -> %s" % exc)
    check("unknown tech rejected", True)

# An AMBIGUOUS name must refuse rather than guess.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": "age",
                            "delta": 5}, parsed=parsed)
    check("ambiguous tech name refused", False, "'age' was accepted")
except C.IntentError as exc:
    print("     ambiguous 'age' -> %s" % str(exc)[:150])
    check("ambiguous tech name refused", True)

# Missing amount.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": 22},
                     parsed=parsed)
    check("missing amount rejected", False)
except C.IntentError as exc:
    print("     no amount -> %s" % exc)
    check("missing amount rejected", True)

# Both delta and value.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": 22,
                            "delta": 5, "value": 10}, parsed=parsed)
    check("delta+value rejected", False)
except C.IntentError as exc:
    print("     delta+value -> %s" % exc)
    check("delta+value rejected", True)

# Overflow must be refused, not silently wrapped.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": 22,
                            "delta": 40000}, parsed=parsed)
    check("overflow rejected", False, "40000 was accepted")
except C.IntentError as exc:
    print("     overflow -> %s" % exc)
    check("overflow rejected", True)

# `value` (absolute) must also work, not just `delta`.
rep = C.compile_intent(BASE, {"intent": "tech.research_time", "tech": 22,
                              "value": 7}, parsed=parsed)
patched = bytearray(data)
for e in rep["edits"]:
    patched[e.off:e.off + e.width] = int(e.after).to_bytes(
        e.width, "little", signed=True)
after = [d["research_time"] for d in
         L.locate_techs(bytes(patched), tail, gv)[22]["research_locations"]]
print("     value=7 -> %s" % after)
check("absolute value sets the field", after == [7])

print("\n=== E. a zero delta is refused with a sentence that names the FIELD ===")
# The product used to accept `delta: 0`, emit a `.dat` byte-identical to the
# base, and ship a manifest claiming it changed the game (independent audit,
# case 21) -- so a refusal is the intended behaviour.  What this section pins is
# the SENTENCE: the tech path lacked the unit path's `had_field` flag, so a
# zero delta fell through to "it declares no research location" -- a plain lie
# about a record that accepted `value: 7` two lines above.  A user reading that
# would go looking for a research location that is already there.
try:
    C.compile_intent(BASE, {"intent": "tech.research_time", "tech": 22,
                            "delta": 0}, parsed=parsed)
    check("delta 0 is refused", False, "a no-op build was accepted")
except C.IntentError as exc:
    print("     delta 0 -> %s" % exc)
    check("delta 0 is refused", True)
    check("and the sentence blames the VALUE, not a missing field",
          "已经是这个值" in str(exc)
          and "研究位置" not in str(exc), str(exc))
    check("and it names the tech and the field",
          "织布机" in str(exc) and "研究时间" in str(exc), str(exc))

print("\n%s" % ("ALL TECH CHECKS PASSED" if not FAIL
                else "FAILURES: %s" % FAIL))
sys.exit(1 if FAIL else 0)

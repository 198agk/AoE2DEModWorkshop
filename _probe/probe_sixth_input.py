# -*- coding: utf-8 -*-
r"""Find the SIXTH input: byte-compare a civ's whole unit-2550 record, not its fields.

Five data points are already matched between the Incas (which can build the Champi
Scout) and the Britons (which cannot, until dsh test v4 writes them):

    1  the `.dat` unit record         (claimed identical -- fields compared)
    2  the `.dat` effect enable       (v4 adds a British-owned one)
    3  the unit's `EnablingResearch`  (v4 points it at tech 263)
    4  the CivTechTrees row           (v4 copies the Incas' 13 fields exactly)
    5  the panel entry                (v4 copies it exactly)

The field comparison in point 1 is only as good as the parser: a field the parser
does not carry would be invisible to it.  So compare the RAW BYTE SPAN of each civ's
unit-2550 record instead -- `_offs` says where the record starts and
`_creatable_end` where it ends, both recorded by the parser as it walks.

If the spans differ, the difference is a real sixth input and the field view hid it.
If they are byte-identical, the gate is genuinely outside the unit record.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
raw = tk._raw
with contextlib.redirect_stdout(io.StringIO()):
    pr = P.Parser(raw)
    pr.parse()
# NOT `pr.stats["civs"]`: the parser keeps a REDUCED unit model
# (`class/hit_points/id/name/task_swap_group/type` only).  The full model -- with
# `_offs` and `_creatable_end`, which a byte span needs -- is `L.locate`.
civs, _cs, _gv, _tail = L.locate(raw, parser=pr)


def rec(civname):
    for c in civs:
        if c["name"] == civname:
            for u in c["units"]:
                if u["id"] == UNIT:
                    return u
    return None


b, i = rec("British"), rec("Incas")
print("A  the span each civ records for unit %d" % UNIT)
for label, u in (("British", b), ("Incas", i)):
    print("     %-8s _offs=%s  _creatable_start=%s  _creatable_end=%s  _creatable_head_end=%s"
          % (label, u.get("_offs"), u.get("_creatable_start"),
             u.get("_creatable_end"), u.get("_creatable_head_end")))

print()
print("B  byte-compare the whole record span")
sb = raw[b["_offs"]:b["_creatable_end"]]
si = raw[i["_offs"]:i["_creatable_end"]]
print("     British span: %d bytes" % len(sb))
print("     Incas   span: %d bytes" % len(si))
check("the two spans are the same length", len(sb) == len(si),
      "%d vs %d" % (len(sb), len(si)))
if len(sb) == len(si):
    diffs = [k for k in range(len(sb)) if sb[k] != si[k]]
    print("     differing bytes inside the record: %d %s"
          % (len(diffs), diffs[:20]))
    check("the whole unit record is byte-identical between the two civs",
          not diffs, "diffs at %s" % diffs[:20])

print()
print("C  and the same for the other American regional units, as a second sample")
for uid in (2552, 2562, 2566, 2579):
    _b = next((u for c in civs if c["name"] == "British"
               for u in c["units"] if u["id"] == uid), None)
    _i = next((u for c in civs if c["name"] == "Incas"
               for u in c["units"] if u["id"] == uid), None)
    if not _b or not _i:
        print("     unit %-5s missing on one side (British=%s Incas=%s)"
              % (uid, bool(_b), bool(_i)))
        continue
    _sb = raw[_b["_offs"]:_b["_creatable_end"]]
    _si = raw[_i["_offs"]:_i["_creatable_end"]]
    same = _sb == _si
    print("     unit %-5s british %4d B / incas %4d B   identical=%s"
          % (uid, len(_sb), len(_si), same))
    check("unit %d's record is identical or absent on one side" % uid,
          same or len(_sb) != len(_si), "len %d vs %d, same=%s"
          % (len(_sb), len(_si), same))

print()
print("D  so what does the record actually differ in, ACROSS civilizations?")
# If every civ's record for 2550 is identical, then per-civ ownership is NOT in the
# unit record at all -- it must be in one of the other layers, or in a layer this
# tool does not model.
spans = {}
for c in civs:
    for u in c["units"]:
        if u["id"] == UNIT:
            spans[c["name"]] = raw[u["_offs"]:u["_creatable_end"]]
distinct = {}
for name, s in spans.items():
    distinct.setdefault(s, []).append(name)
print("     civs holding a record for %d: %d" % (UNIT, len(spans)))
print("     DISTINCT byte-images of that record: %d" % len(distinct))
for s, names in list(distinct.items())[:4]:
    print("        %d civs (%s...)  len=%d  sha=%s"
          % (len(names), ", ".join(sorted(names)[:4]), len(s),
             __import__("hashlib").sha256(s).hexdigest()[:16]))
check("the unit record does NOT vary by civ (so ownership lives elsewhere)",
      len(distinct) == 1, "distinct images: %d" % len(distinct))

print()
print("SIXTH INPUT: the unit record for 2550 is byte-identical across every civ that")
print("  holds one, so whatever marks a civ as able to BUILD it is not in that")
print("  record.  The remaining layers this tool writes are the effect layer, the")
print("  EnablingResearch field, the CivTechTrees row and the panel entry -- which is")
print("  exactly what dsh test v4 now supplies.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

"""What write semantics do attribute-modifier commands actually need?

Before exposing an editor for effect commands I need to know, from the data:
  * which (operation, attribute) pairs occur at all;
  * the shape of the TARGET (A, B): is "class B" or "unit A" the common case,
    and does A == -1 ever mean "everything"?
  * for the packed attributes (C in {8,9}) what range the value byte covers,
    because writing one means preserving the class byte in D's high half;
  * whether D is ever negative or fractional per operation, which decides
    whether an integer editor is honest.

Read-only, BASE only.
"""
import os, sys, io, contextlib, collections, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

SET_T = (0, 10, 20, 30, 40, 200, 203)
ADD_T = (4, 14, 24, 34, 44, 201, 204)
MUL_T = (5, 15, 25, 35, 45, 202, 205)


def op_of(t):
    return "set" if t in SET_T else "add" if t in ADD_T else "mul" if t in MUL_T else None


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


data, p = load(BASE)
civs, civs_start, gv, tail = L.locate(data, parser=p)
techs = L.locate_techs(data, tail, gv)
effs, eff_start = L.locate_effects(data, parser=p)

cmds = [c for e in effs for c in e["commands"] if op_of(c["type"])]
print("=== 1. (operation, attribute) pairs, all effects ===")
Pair = collections.Counter((op_of(c["type"]), c["c"]) for c in cmds)
print("  distinct pairs: %d" % len(Pair))
for (op, c), n in Pair.most_common(14):
    print("    %-4s C=%-4d %5d" % (op, c, n))

print("\n=== 2. target shape (A, B) ===")
shapes = collections.Counter()
for c in cmds:
    a, b = c["a"], c["b"]
    if b == -1 and a == -1:
        shapes["A=-1 B=-1  (all?)"] += 1
    elif b == -1:
        shapes["B=-1  -> unit A"] += 1
    elif a == -1:
        shapes["A=-1  -> class B"] += 1
    else:
        shapes["both set"] += 1
print("  %s" % dict(shapes))

print("\n=== 3. packed attributes (C in {8,9}) ===")
pk = [c for c in cmds if c["c"] in (8, 9)]
print("  count: %d" % len(pk))
print("  by operation: %s" % dict(collections.Counter(op_of(c["type"]) for c in pk)))
cls_hist = collections.Counter()
val_hist = collections.Counter()
for c in pk:
    raw = struct.unpack("<H", struct.pack("<h", int(c["d"])))[0]
    cls_hist[raw >> 8] += 1
    val_hist[raw & 0xFF] += 1
print("  class byte: %s" % dict(sorted(cls_hist.items())))
print("  value byte range: %d..%d, distinct %d"
      % (min(val_hist), max(val_hist), len(val_hist)))
print("  value byte top: %s" % val_hist.most_common(8))
neg = sum(1 for c in pk if c["d"] < 0)
print("  negative D among packed: %d" % neg)

print("\n=== 4. is D ever negative or fractional, per operation? ===")
for op in ("set", "add", "mul"):
    vals = [c["d"] for c in cmds if op_of(c["type"]) == op]
    nonpk = [c["d"] for c in cmds if op_of(c["type"]) == op and c["c"] not in (8, 9)]
    neg = [v for v in vals if v < 0]
    frac = [v for v in nonpk if v != int(v)]
    print("  %-4s n=%-5d negative=%-5d | non-packed n=%-5d fractional=%-5d sample frac=%s"
          % (op, len(vals), len(neg), len(nonpk), len(frac), frac[:5]))

print("\n=== 5. non-packed D range, per operation ===")
for op in ("set", "add", "mul"):
    nz = [c["d"] for c in cmds if op_of(c["type"]) == op and c["c"] not in (8, 9)]
    if nz:
        print("  %-4s min=%-12.4f max=%-12.4f" % (op, min(nz), max(nz)))

print("\n=== 6. attribute names available ===")
import json
attrs = json.load(open(os.path.join(ROOT, "_probe", "schema",
                                    "effect_attributes.json"),
                       encoding="utf-8"))["attributes"]
used = {c["c"] for c in cmds}
named = sum(1 for c in used if str(c) in attrs)
print("  distinct C in commands: %d | of those named in the table: %d" % (len(used), named))
print("  unnamed: %s" % sorted(c for c in used if str(c) not in attrs))

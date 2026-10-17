# -*- coding: utf-8 -*-
"""Focused dump: the two exe int32 tables that contain the villager family,
their exact extents, and the dat tsg=3 group identity."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import struct, sys, os
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P, intent_patch as IP

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
b = open(EXE, "rb").read()

NM = {83: "VMBAS", 293: "VFBAS", 1810: "SVMBAS", 56: "VMFIS", 57: "VFFIS",
      118: "VMBLD", 212: "VFBLD", 120: "VMFOR", 354: "VFFOR", 122: "VMHUN",
      216: "VFHUN", 123: "VMLUM", 218: "VFLUM", 124: "VMMIN", 220: "VFMIN",
      579: "VMGLD", 581: "VFGLD", 259: "VMFAR", 214: "VFFAR", 592: "VMSHE",
      590: "VFSHE", 156: "VMREP", 222: "VFREP", 206: "VMDL", 1891: "VFHER",
      1892: "VMHER", 2333: "VMGLD2", 2334: "VFGLD2", 2714: "VMREPAIRER",
      2715: "VFREPAIRER"}
FAMILY = set(NM)
out = []
def p(s=""):
    out.append(s)

# ---------------------------------------------------------------- table dump
def region(name, start, count, stride=4):
    p("\n=== %s @0x%X ===" % (name, start))
    vals = [struct.unpack_from("<i", b, start + stride * k)[0] for k in range(count)]
    p("  values: %s" % vals)
    # pair view
    p("  as (a,b) pairs:")
    for k in range(0, count - 1, 2):
        a, c = vals[k], vals[k + 1]
        p("    [%2d] %5d %-12s  %5d %-12s" % (k, a, NM.get(a, ""), c, NM.get(c, "")))
    return vals

# walk backwards from 0x32B1DD0 to find the table start: values are all < 3000
def table_extent(center):
    s = center
    while s - 4 >= 0 and 0 < struct.unpack_from("<i", b, s - 4)[0] < 3000:
        s -= 4
    e = center
    while e + 4 <= len(b) and 0 < struct.unpack_from("<i", b, e)[0] < 3000:
        e += 4
    return s, e

for c in (0x32B1DD0, 0x3232E50):
    s, e = table_extent(c)
    p("\n### maximal 0<v<3000 int32 run containing 0x%X : [0x%X .. 0x%X) = %d values"
      % (c, s, e, (e - s) // 4))
    vals = [struct.unpack_from("<i", b, s + 4 * k)[0] for k in range((e - s) // 4)]
    p("  %s" % vals)
    fam = [v for v in vals if v in FAMILY]
    p("  family ids present (%d): %s" % (len(fam), fam))
    p("  as pairs:")
    for k in range(0, len(vals) - 1, 2):
        a, d = vals[k], vals[k + 1]
        p("    %5d %-12s | %5d %-12s" % (a, NM.get(a, ""), d, NM.get(d, "")))

# how many raw int32 between the two tables?  are they the same table twice?
s1, e1 = table_extent(0x32B1DD0)
s2, e2 = table_extent(0x3232E50)
v1 = [struct.unpack_from("<i", b, s1 + 4 * k)[0] for k in range((e1 - s1) // 4)]
v2 = [struct.unpack_from("<i", b, s2 + 4 * k)[0] for k in range((e2 - s2) // 4)]
p("\n### are the two tables equal? %s" % (sorted(v1) == sorted(v2)))
p("  table A (0x%X) len=%d" % (s1, len(v1)))
p("  table B (0x%X) len=%d" % (s2, len(v2)))
p("  A - B = %s" % sorted(set(v1) - set(v2)))
p("  B - A = %s" % sorted(set(v2) - set(v1)))

# ---------------------------------------------------------------- tsg=3 ids
p("\n\n" + "=" * 70)
p("dat: what are the tsg=3 units?")
p("=" * 70)
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
data, how = P.load_dat(BASE)
civs, civs_start, gv, tail = IP.locate(data)
p("gv=%s civs=%d" % (gv, len(civs)))
seen = {}
for c in civs:
    for u in c["units"]:
        if u["id"] not in seen:
            seen[u["id"]] = (u["name"], u["type"], u["class"], u["hit_points"])
for uid in (13, 2147, 2171, 2356, 2630):
    p("  unit %-6d %s" % (uid, seen.get(uid, "ABSENT")))

with open(_HERE_PATH("_probe", "taskfamily", "exe_tables_dump.txt"),
          "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("\n".join(out[:400]))
print("\n... (full dump -> exe_tables_dump.txt, %d lines)" % len(out))

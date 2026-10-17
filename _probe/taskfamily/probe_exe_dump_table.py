# -*- coding: utf-8 -*-
"""Dump the two exe structures that contain the villager family ids as int32.

Hit 1: 0x3232E50  -> int32 run [259,214,122,216,56,57,123,218,118,212,156,222,
                                  592,590,120,354,124,220,579,581,...]
Hit 2: 0x32B1DD0  -> int32 run [118,212,259,214,83,293,122,216,123,218,...]

Both are unmistakably the villager task-variant family, so this is a REAL
engine-side table, not coincidence.  This script measures its extent, stride,
and boundaries so the claim can be stated precisely.
"""
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
b = open(EXE, "rb").read()

FAMILY = {56, 57, 83, 118, 120, 122, 123, 124, 156, 206, 212, 214, 216, 218,
          220, 222, 259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892,
          2333, 2334}
# names for readability
NM = {83: "83 VMBAS", 293: "293 VFBAS", 1810: "1810 SVMBAS",
      56: "56 VMFIS", 57: "57 VFFIS", 118: "118 VMBLD", 212: "212 VFBLD",
      120: "120 VMFOR", 354: "354 VFFOR", 122: "122 VMHUN", 216: "216 VFHUN",
      123: "123 VMLUM", 218: "218 VFLUM", 124: "124 VMMIN", 220: "220 VFMIN",
      579: "579 VMGLD", 581: "581 VFGLD", 259: "259 VMFAR", 214: "214 VFFAR",
      592: "592 VMSHE", 590: "590 VFSHE", 156: "156 VMREP", 222: "222 VFREP",
      206: "206 VMDL", 1891: "1891 VFHER", 1892: "1892 VMHER",
      2333: "2333 VMGLD2", 2334: "2334 VFGLD2"}


def dump(center, before=0x40, after=0x1C0, stride=4):
    lo = center - before
    hi = center + after
    print("\n" + "=" * 78)
    print("REGION around 0x%X   [0x%X .. 0x%X)  stride %d" % (center, lo, hi, stride))
    print("=" * 78)
    n = (hi - lo) // stride
    for k in range(n):
        o = lo + k * stride
        v = struct.unpack_from("<i", b, o)[0]
        f = struct.unpack_from("<f", b, o)[0]
        mark = ""
        if v in FAMILY:
            mark = "   <== FAMILY %s" % NM[v]
        print("  0x%08X  +0x%04X  i32=%-8d f32=%-14.4g%s"
              % (o, o - center, v, f, mark))


print("### HIT 2 first, it looks like a clean (male,female) pair table")
dump(0x32B1DD0)
print("\n\n### HIT 1")
dump(0x3232E50)

# --- extract maximal int32 runs whose values are all in 0..3000 -----------
print("\n" + "=" * 78)
print("MAXIMAL small-int32 RUNS (0 < v < 3000) over the whole .rdata, "
      "length >= 8 values; report which contain >=3 FAMILY ids")
print("=" * 78)


def runs(lo_sec, hi_sec):
    out = []
    o = lo_sec
    while o + 4 <= hi_sec:
        v = struct.unpack_from("<i", b, o)[0]
        if 0 < v < 3000:
            s = o
            vals = []
            while o + 4 <= hi_sec:
                v = struct.unpack_from("<i", b, o)[0]
                if 0 < v < 3000:
                    vals.append(v)
                    o += 4
                else:
                    break
            if len(vals) >= 8:
                out.append((s, vals))
        else:
            o += 4
    return out


# .rdata = rawptr 0x03196000 .. +0x00C0D000
RS = 0x03196000
RE = RS + 0x00C0D000
rs = runs(RS, RE)
print("total runs >= 8 values: %d" % len(rs))
fam_runs = []
for s, vals in rs:
    hit = [v for v in vals if v in FAMILY]
    if len(hit) >= 3:
        fam_runs.append((s, vals, hit))
print("runs containing >= 3 family ids: %d" % len(fam_runs))
for s, vals, hit in fam_runs:
    print("\n  @0x%X  len=%d  family_hits=%d" % (s, len(vals), len(hit)))
    print("    all values : %s" % vals)
    print("    as names   : %s" % [NM.get(v, str(v)) for v in vals])

print("\nDONE")

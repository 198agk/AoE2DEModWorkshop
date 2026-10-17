import os, sys, io, json, struct
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
r = P.Reader(data)
p = P.Parser(data)
st = p.parse()
# r is now positioned at end of stage 10 = end of file. Re-seek to stage10 start.
stage10 = [s for s in p.stage_offsets if s[0].startswith("10")][0]
r.pos = stage10[1]
w("stage10 start=%d  end=%d  file=%d" % (stage10[1], stage10[2], len(data)))

def keep_group(r):
    n = r.u8()
    return list(r.i32_array(n)) if n else []

def keep_common(r):
    return {"SlotsUsed": r.i32(), "UnitResearch": list(r.i32_array(10)), "Mode": list(r.i32_array(10))}

w("time_slice=%d kill=%d/%d hp=%d/%d raze=%d/%d" % (r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32()))
ages_n = r.u8(); bld_n = r.u8(); unit_n = r.i16(); res_n = r.u8(); tug = r.i32()
w("COUNTS ages=%d buildings=%d units=%d research=%d total_unit_tech_groups=%d" % (ages_n, bld_n, unit_n, res_n, tug))

w("\n--- AGES (read_tech_tree_age)")
ages = []
for k in range(ages_n):
    a = {}
    a["ID"] = r.i32()
    a["Status"] = r.u8()
    a["Buildings"] = keep_group(r); a["Units"] = keep_group(r); a["Techs"] = keep_group(r)
    a["common"] = keep_common(r)
    a["NumBuildingLevels"] = r.u8()
    a["BuildingsPerZone"] = list(r.raw(10)); a["GroupLengthPerZone"] = list(r.raw(10))
    a["MaxAgeLength"] = r.u8()
    a["LineMode"] = r.i32()
    ages.append(a)
    w("  age ID=%s status=%s bld=%s units=%s techs=%s NumBldLevels=%s MaxAgeLen=%s LineMode=%s"
      % (a["ID"], a["Status"], a["Buildings"], a["Units"], a["Techs"], a["NumBuildingLevels"], a["MaxAgeLength"], a["LineMode"]))

def conn(r, kind):
    c = {}
    c["ID"] = r.i32(); c["Status"] = r.u8()
    if kind == "b":
        c["g1"] = keep_group(r); c["g2"] = keep_group(r); c["g3"] = keep_group(r)
        c["common"] = keep_common(r)
        c["LocationInAge"] = r.u8()
        c["UnitsTechsTotal"] = list(r.raw(P.AGES)); c["UnitsTechsFirst"] = list(r.raw(P.AGES))
        c["LineMode"] = r.i32(); c["EnablingResearch"] = r.i32()
    elif kind == "u":
        c["UpperBuilding"] = r.i32(); c["common"] = keep_common(r); c["VerticalLine"] = r.i32()
        c["g1"] = keep_group(r)
        c["LocationInAge"] = r.i32(); c["RequiredResearch"] = r.i32()
        c["LineMode"] = r.i32(); c["EnablingResearch"] = r.i32()
    else:
        c["UpperBuilding"] = r.i32()
        c["g1"] = keep_group(r); c["g2"] = keep_group(r); c["g3"] = keep_group(r)
        c["common"] = keep_common(r); c["VerticalLine"] = r.i32()
        c["LocationInAge"] = r.i32(); c["LineMode"] = r.i32()
    return c

w("\n--- BUILDING CONNECTIONS")
blds = [conn(r, "b") for _ in range(bld_n)]
for c in blds[:40]:
    w("  ID=%-6s status=%-3s groups=%s,%s,%s LocInAge=%-3s LineMode=%-3s EnabRes=%-5s"
      % (c["ID"], c["Status"], c["g1"][:6], c["g2"][:6], c["g3"][:6], c["LocationInAge"], c["LineMode"], c["EnablingResearch"]))

w("\n--- UNIT CONNECTIONS (first 40)")
units = [conn(r, "u") for _ in range(unit_n)]
for c in units[:40]:
    w("  ID=%-6s status=%-3s UpperBld=%-5s VertLine=%-4s grp=%-24s LocInAge=%-3s ReqRes=%-5s LineMode=%-3s EnabRes=%-5s"
      % (c["ID"], c["Status"], c["UpperBuilding"], c["VerticalLine"], c["g1"][:8], c["LocationInAge"], c["RequiredResearch"], c["LineMode"], c["EnablingResearch"]))

w("\n--- RESEARCH CONNECTIONS (first 40)")
res = [conn(r, "r") for _ in range(res_n)]
for c in res[:40]:
    w("  ID=%-6s status=%-3s UpperBld=%-5s VertLine=%-4s LocInAge=%-3s LineMode=%-3s groups=%s,%s,%s"
      % (c["ID"], c["Status"], c["UpperBuilding"], c["VerticalLine"], c["LocationInAge"], c["LineMode"], c["g1"][:8], c["g2"][:8], c["g3"][:8]))

w("\nfinal pos=%d file=%d exact=%s" % (r.pos, len(data), r.pos == len(data)))

w("\n=== .dat tech-tree connection ID sets")
w("building IDs (%d distinct): %s" % (len(set(c["ID"] for c in blds)), sorted(set(c["ID"] for c in blds))))
w("unit IDs (%d distinct): %s" % (len(set(c["ID"] for c in units)), sorted(set(c["ID"] for c in units))))
w("research IDs (%d distinct): %s" % (len(set(c["ID"] for c in res)), sorted(set(c["ID"] for c in res))))
w("repeated unit IDs? %s" % (len(units) != len(set(c["ID"] for c in units))))
from collections import Counter
dup = [k for k, v in Counter(c["ID"] for c in units).items() if v > 1]
w("unit ID dups: %d  e.g. %s" % (len(dup), dup[:20]))

json.dump({"ages": ages, "buildings": blds, "units": units, "research": res},
          open(os.path.join(OUT, "s25_dat_techtree.json"), "w", encoding="utf-8"), ensure_ascii=False)
open(os.path.join(OUT, "s25_dat_techtree.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[-5000:])

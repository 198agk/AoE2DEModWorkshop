import re, io, os

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
buf = open(EXE, "rb").read()
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def dump(lo, hi, label, maxs=60, minlen=3):
    seg = buf[lo:hi]
    strs = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, seg):
        strs.append((lo + m.start(), m.group().decode("ascii")))
    w("\n=== %s  [%d..%d] %d strings" % (label, lo, hi, len(strs)))
    for off, s in strs[:maxs]:
        w("  @%-9d %s" % (off, s))

# region around the futuravailableunits key cluster
dump(53369800, 53371500, "REGION-53370k (futuravailableunits schema?)", 90, 3)

# region right at the filename cluster 52798000-52801000
dump(52798500, 52801100, "REGION-52798k filename cluster", 110, 3)

# region around civTechTrees.json @53352056
dump(53351500, 53353200, "REGION-civTechTrees.json", 70, 3)

# region around selection_group_def absence / radial
for pat in ["radial_data", "RadialData", "radial", "selectiongroup", "SelectionGroup",
            "selection_group_def.json", "chronicles_selection_group"]:
    p = pat.lower().encode()
    n = buf.lower().count(p)
    w("\n  str %-35s n=%d" % (pat, n))

# find how the game might name the selection group file: look for "_def.json" or "%s_def"
for pat in ["_def.json", "%s_def", "radial_", "Radial", "SELECTION_GROUP", "GameScreen::setup_radial"]:
    p = pat.encode()
    n = buf.count(p)
    w("  raw %-35s n=%d" % (pat, n))

dump(53259300, 53260100, "REGION-hotkeys.json + following", 60, 3)

open(os.path.join(OUT, "s15_regions.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

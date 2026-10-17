import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
buf = open(EXE, "rb").read()
low = buf.lower()
OUT = _HERE_PATH("_probe", "json_layer")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def find_all(pat, cap=8):
    pb = pat.encode("utf-8")
    res = []
    s = 0
    while len(res) < cap:
        i = low.find(pb.lower(), s)
        if i < 0:
            break
        res.append(i)
        s = i + 1
    return res

groups = {
    "futuravailableunits.json keys": ["RequiredAge", "PrereqTech", "PrereqIconSet", "PrereqIconIndex",
                                      "PrereqBuilding", "PrereqIcon", "RequiredTechs", "Buildings",
                                      "BuildingID", "TechID", "UnitID", "Available", "Gaia", "FullTechCiv"],
    "unitlines.json keys": ["UnitLines", "IDChain", "LineID", "Identifier", "Hint",
                            "DefConsts", "LineIDs have to be between"],
    "linkedUnits.json keys": ["Data", "Units", "Lü Bu", "Guan Yu", "Arariboia", "Kongming"],
    "linkedTechs.json keys": ["LinkedTechs", "MutuallyExclusive", "Toggleable", "Cycle", "Comment",
                              "Instant", "Local", "StartingTech", "424001", "Satrapies"],
    "sharedbuildings.json keys": ["FirstUnitID", "FirstBuildingID", "SecondUnitID", "SecondBuildingID", "Huskarl"],
    "selection_group_def.json keys": ["selection_group", "group_list", "item_list", "radial_data",
                                      "all_land_military", "OBJECT_GROUP_ARCHER", "OBJECT_GROUP_SOLDIER",
                                      "label"],
    "unitcategories.json keys": ["CavalryArchers", "SiegeWeapons", "Warboats", "Monks",
                                 "Ballista Elephant", "Warrior Priest", "Zakare"],
    "AIConsts/airesourcetypes keys": ["DefConsts", "Defines", "ResourceTypes", "Types", "Resource",
                                      "jump-end-of-file", "DE-GAME-AGE2", "Forage Bush", "Javelina"],
    "selection_group filename variants": ["selection_group", "chronicles_selection_group", "selection group"],
}

for gname, pats in groups.items():
    w("\n### %s" % gname)
    for p in pats:
        f = find_all(p, 3)
        w("   %-34s n=%d  offsets=%s" % (p, len(f), f))
        for i in f[:1]:
            w("        ctx: %s" % repr(buf[max(0, i - 70): i + 110]))

# also: does the exe contain the exact base filename strings at all yet with 0 keys because CamelCase?
w("\n\n### re-test: full literal windows after each filename, NO key filtering (all printable strings >=2)")
names = ["futuravailableunits.json", "linkedUnits.json", "paphosfutureavailableunits.json",
         "unitlines.json", "linkedTechs.json", "sharedbuildings.json", "AIConsts.json",
         "airesourcetypes.json", "unitcategories.json", "sounds.json", "hotkeys.json",
         "civilizations.json", "eras.json", "buttons.json", "maps.json", "dropsites.json",
         "objreplacement.json", "civTechTrees.json", "CivTechTrees/%s.json"]
for n in names:
    i = low.find(n.lower().encode())
    if i < 0:
        w("\n--- %s : NOT FOUND" % n)
        continue
    seg = buf[i + len(n): i + len(n) + 700]
    strs = re.findall(rb"[\x20-\x7e]{2,}", seg)
    w("\n--- %s @%d" % (n, i))
    w("     " + " | ".join(s.decode() for s in strs[:30]))

open(os.path.join(OUT, "s14_keytest.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

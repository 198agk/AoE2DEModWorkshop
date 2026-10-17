import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def win(lo, hi, label):
    w("=" * 90)
    w(label)
    w("=" * 90)
    for m in re.finditer(rb"[ -~]{4,}", exe[lo:hi]):
        w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))
    w("")

win(52600050, 52600600, "AIResourceTypes.json window")
win(52798800, 52799400, "linkedUnits / futuravailableunits / unitcategories cluster")
win(52553150, 52553400, "sounds.json window")
win(52828560, 52829200, "CivTechTrees end + shadow.col")
# search for the selection-group load: look at how 'PlayerColor'/'radial' area is used
win(52378800, 52379000, "Radial @52378896")
win(52475850, 52476050, "Radial @52475944")
win(53450850, 53451100, "adapter_blacklist.json window")
# history.json is in widgetui, keys confirmed. Check if 'selection' json names exist
for nm in (b"selection_group", b"selectiongroups", b"SelectionGroup", b"radial_data",
           b"item_list", b"is_building", b"SelectionGroupDef", b"selection_group_def"):
    w("  %-22s exe count=%d" % (nm.decode(), exe.count(nm)))
open(os.path.join(OUT, "s50_windows2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

import os, io, re, json
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=" * 90)
w("DD. Where is 'selection_group' / 'radial_data' / 'is_building' mentioned on disk?")
w("=" * 90)
needles = ["selection_group", "radial_data", "is_building", "item_list", "selection_group_def"]
hits = {n: [] for n in needles}
for root, dirs, files in os.walk(GAME):
    if any(s in root.lower() for s in ("\\_packages", "\\drs\\", "\\sound\\")):
        continue
    for fn in files:
        ext = os.path.splitext(fn)[1].lower()
        if ext not in (".json", ".txt", ".xml", ".lua", ".xs", ".ini", ".cfg", ".py", ".js", ".html"):
            continue
        fp = os.path.join(root, fn)
        try:
            if os.path.getsize(fp) > 6_000_000: continue
            t = open(fp, "rb").read().decode("utf-8", "ignore")
        except Exception:
            continue
        for n in needles:
            if n in t:
                hits[n].append(os.path.relpath(fp, GAME))
for n in needles:
    w("  %-22s files=%d  %s" % (n, len(hits[n]), hits[n][:8]))

w("")
w("=" * 90)
w("EE. widgetui selection-group-ish / radial files")
w("=" * 90)
for root, dirs, files in os.walk(os.path.join(GAME, "widgetui")):
    for fn in files:
        low = fn.lower()
        if "select" in low or "radial" in low:
            fp = os.path.join(root, fn)
            w("  %-70s %9d B" % (os.path.relpath(fp, GAME), os.path.getsize(fp)))

w("")
w("=" * 90)
w("FF. maps.json: 'maps.txt' next to it?  Build an overlay map of the dat dir")
w("=" * 90)
for root, dirs, files in os.walk(GAME):
    for fn in files:
        if fn.lower().endswith(".txt") and ("map" in fn.lower()):
            fp = os.path.join(root, fn)
            w("  %-70s %9d B" % (os.path.relpath(fp, GAME), os.path.getsize(fp)))

w("")
w("=" * 90)
w("GG. CivTechTrees: how does the engine pick a civ file?  (%s vs registry)")
w("=" * 90)
# Does the exe contain a per-civ list of tech tree names, i.e. 'BRITONS' uppercase?
for k in ("BRITONS", "FRANKS", "MAGYAR", "KHITANS", "SAXONS", "VARANGIANS"):
    w("  %-12s exe=%s" % (k, k.encode() in exe))
# look at where 'GetRandomCivName' region lists civ names
lo, hi = 52829120, 52829600
w("  window @52829120..52829600: (already dumped) - next block after CivTechTrees has NO civ names")

w("")
w("=" * 90)
w("HH. tech_tree_name values (CivTechTrees file stems): in exe?")
w("=" * 90)
civs = json.loads(open(os.path.join(BASE, "civilizations.json"), "rb").read().decode("utf-8-sig"))["civilization_list"]
ttn = [c["tech_tree_name"] for c in civs]
present = [t for t in ttn if t.encode() in exe]
absent = [t for t in ttn if t.encode() not in exe]
w("  n=%d present_in_exe=%d absent=%d" % (len(ttn), len(present), len(absent)))
w("  present: %s" % present)
w("  absent: %s" % absent)

w("")
w("=" * 90)
w("II. .dat-dir 'shadow.col' vs CivTechTrees key 'shadow.col' - the true meaning")
w("=" * 90)
w("  shadow.col exists on disk: %s (%d B)" % (
    os.path.exists(os.path.join(BASE, "shadow.col")), os.path.getsize(os.path.join(BASE, "shadow.col"))))
w("  => 'shadow.col' at 52829104 is the NEXT unrelated .rdata string, not a JSON key.")
open(os.path.join(OUT, "s52_selgroup.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

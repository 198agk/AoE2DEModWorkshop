import os, io
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

NEEDLES = [b"selection_group_def", b"chronicles_selection_group_def", b"_selection_group",
           b"selection_group", b"radial_data", b"hotkeys.json", b"HotKeys.hkp",
           b"morematerials", b"futuravailableunits", b"civTechTrees"]
w("=== RAW-BYTE search for filename literals across EVERY file in the game + user tree ===")
hits = {n: [] for n in NEEDLES}
scanned = 0
for top in (GAME, USER):
    for root, dirs, files in os.walk(top):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                sz = os.path.getsize(fp)
                if sz == 0 or sz > 400_000_000: continue
                b = open(fp, "rb").read()
            except Exception:
                continue
            scanned += 1
            for n in NEEDLES:
                if n in b:
                    hits[n].append((os.path.relpath(fp, top), sz))
w("  files scanned = %d" % scanned)
for n in NEEDLES:
    w("")
    w("  --- %s : %d hits ---" % (n.decode(), len(hits[n])))
    for p, s in hits[n][:14]:
        w("      %-72s %10d B" % (p, s))
open(os.path.join(OUT, "s67_rawscan.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

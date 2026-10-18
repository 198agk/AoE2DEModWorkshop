# -*- coding: utf-8 -*-
"""Re-measure the two label/icon denominators the docs quote."""
import sys, io, os, json
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
G = r"d:\games\steam\steamapps\common\AoE2DE"

from aoe2mod.dat import parser as P
raw, how = P.load_dat(os.path.join(G, "resources", "_common", "dat", "empires2_x2_p1.dat"))
d = P.Parser(raw).parse()
gfx = d["graphics"] if "graphics" in d else d.get("graphics")
print("graphics slots:", len(gfx))

files = Counter()
for g in gfx:
    f = g.get("file")
    if f:
        files[f] += 1
print("distinct file strings:", len(files))
print("records with a file string:", sum(files.values()))

# which records point at each file, and how many distinct NAME labels per file
by_file = defaultdict(set)
for g in gfx:
    f = g.get("file")
    if f:
        by_file[f].add(g.get("name"))
multi = [f for f, s in by_file.items() if len(s) > 1]
print("files pointed at by >1 distinct name label:", len(multi))

# same but counting raw record multiplicity
recs = defaultdict(int)
for g in gfx:
    if g.get("file"):
        recs[g["file"]] += 1
print("files named by >1 record:", sum(1 for v in recs.values() if v > 1))

print()
print("=== icons.json resolution ===")
ic = json.load(open(os.path.join(G, "widgetui", "icons.json"), encoding="utf-8-sig"))
tot = 0
res = 0
missing = []
for seg, tab in ic.items():
    if not isinstance(tab, dict):
        continue
    for k, v in tab.items():
        if v in (None, "", "None"):
            continue
        tot += 1
        cands = [
            os.path.join(G, "widgetui", v),
            os.path.join(G, "widgetui", "textures", v),
            os.path.join(G, v),
        ]
        if any(os.path.exists(c) for c in cands):
            res += 1
        else:
            missing.append(v)
print("non-empty:", tot, "resolved (naive join):", res, "%.1f%%" % (100.0 * res / tot))
print("missing sample:", missing[:8])
# try basename anywhere in widgetui
idx = {}
for dp, dn, fn in os.walk(os.path.join(G, "widgetui")):
    for f in fn:
        idx.setdefault(f.lower(), os.path.join(dp, f))
res2 = sum(1 for seg, tab in ic.items() if isinstance(tab, dict)
           for k, v in tab.items()
           if v not in (None, "", "None") and os.path.basename(str(v)).lower() in idx)
print("resolved (basename in widgetui):", res2, "%.1f%%" % (100.0 * res2 / tot))

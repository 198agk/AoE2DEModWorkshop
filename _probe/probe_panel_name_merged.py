"""The cache's Name for the Chronicles civs: is it `Name String ID` resolved
against ALL locale files (including the Paphos one), not just the main table?

`key-value-strings-utf8.txt` has no 405xxx ids; `key-value-paphos-strings-utf8.txt`
has them (405052 = 'Bowman').  The tree row for ACHAEMENIDS unit 4 carries
`Name String ID` 405052 and the generic `Name` 'Archer'.  If the cache shows
'Bowman', the name source is the resolved string id over the merged table.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')


def merged(locale):
    out = {}
    for path in sorted(glob.glob(os.path.join(
            GAME, "resources", locale, "strings", "key-value", "*.txt"))):
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                m = LINE.match(ln)
                if m:
                    out[int(m.group(1))] = m.group(2)
    return out


en = merged("en")
print("merged en ids: %d (405052 -> %r)" % (len(en), en.get(405052)))
print()

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)
trees = CT.load_trees(tk.game_root)

hit = row_hit = miss = 0
samples = []
for stem, tree in trees.items():
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    obj = panels[key]["obj"]
    rows = {}
    for r in CT.unit_rows(tree):
        rows.setdefault(r.get("Node ID"), r)
    for blk in BP.buildings(obj, key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            r = rows.get(e.get("ID"))
            if r is None:
                continue
            sid = r.get("Name String ID")
            text = en.get(sid) if sid is not None else None
            if text is not None and text == e.get("Name"):
                hit += 1
            elif e.get("Name") == r.get("Name"):
                row_hit += 1
            else:
                miss += 1
                if len(samples) < 8:
                    samples.append((stem, e.get("ID"), e.get("Name"),
                                    r.get("Name"), sid, text))
tot = hit + row_hit + miss
print("Name == merged_en[Name String ID] : %d / %d (%.2f%%)"
      % (hit, tot, 100.0 * hit / tot))
print("Name == row['Name']               : %d" % row_hit)
print("neither                           : %d" % miss)
for s in samples:
    print("   %s" % (s,))
print()
if miss == 0:
    print("CACHE NAME SOURCE: the resolved `Name String ID` over the merged "
          "locale table.")
else:
    print("STILL UNEXPLAINED: %d entries" % miss)

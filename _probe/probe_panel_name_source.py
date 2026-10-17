"""Where does the cache's `Name` come from -- the row's Name, or its string id?

170 of 3,122 entries disagree with the tree row's own `Name` (the Chronicles civs
rename Archer to Bowman, Militia to Levy).  The row carries `Name String ID`, so
the question is answerable: load the string table and compare.
"""
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


def strings(locale):
    out = {}
    path = os.path.join(GAME, "resources", locale, "strings", "key-value",
                        "key-value-strings-utf8.txt")
    with open(path, "r", encoding="utf-8") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


en = strings("en")
zh = strings("zh")
print("en strings %d, zh strings %d" % (len(en), len(zh)))
print()

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)
trees = CT.load_trees(tk.game_root)

match_en = match_row = neither = 0
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
                match_en += 1
            elif e.get("Name") == r.get("Name"):
                match_row += 1
            else:
                neither += 1
                if len(samples) < 8:
                    samples.append((stem, e.get("ID"), e.get("Name"),
                                    r.get("Name"), sid, text))
print("Name == en_strings[Name String ID] : %d" % match_en)
print("Name == row['Name']                : %d" % match_row)
print("neither                            : %d" % neither)
for s in samples:
    print("   %s" % (s,))
print()

# and for the civs where they differ, check zh naming too
n_zh = n_zh_row = 0
for stem, tree in trees.items():
    if stem not in ("ACHAEMENIDS", "ATHENIANS", "SPARTANS", "PURU", "THRACIANS",
                    "MACEDONIANS"):
        continue
    key = BP.civ_key_for(panels, stem)
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
            if en.get(sid) == e.get("Name"):
                n_zh += 1
                if zh.get(sid) != e.get("Name"):
                    n_zh_row += 1
print("Chronicles entries whose Name is the ENGLISH string: %d; of those, "
      "the Chinese string differs: %d" % (n_zh, n_zh_row))
print("  => the cache is built from the ENGLISH string table, not the user's "
      "locale.")

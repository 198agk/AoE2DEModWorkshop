# -*- coding: utf-8 -*-
"""Collisions WITHIN ONE UNIT's own art -- the scope that actually matters.

The previous test grouped every graphics record sharing a stem, which mixes in
regional variants that need not be resolvable for any single unit.  A key only
loses a file if two files in the SAME unit's file list map to it.
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mod.api as A
from aoe2mod.game import sprites as S

tk = A.open_toolkit(); tk._ensure()
g = tk._stats["graphics"]; civs = tk._parsed[1]
idx = S.art_index(tk.game_root, g)

byfile = {}
for rec in g:
    f = (rec.get("file") or "").strip()
    n = (rec.get("name") or "").strip()
    if f and f != "None":
        byfile.setdefault(f, n)

PAREN = re.compile(r"\(([^)]*)\)\s*$")


def label_of(f):
    n = byfile.get(f)
    if n:
        m = PAREN.search(n)
        if m:
            return m.group(1).strip().lower()
    return None


def token_key(f):
    return S.token_of(f)


def label_key(f):
    return label_of(f) or S.token_of(f)


# collect the distinct file-lists actually seen for units, per civ
def unit_arts():
    seen = {}
    for c in civs:
        for u in c.get("units", ()):
            a = idx.art(u)
            if a and a.get("kind") == "loose" and a.get("files"):
                seen[(u.get("id"), a["stem"])] = a["files"]
    return seen


arts = unit_arts()
print("distinct (unit id, stem) art lists: %d" % len(arts))

for nm, keyf in (("raw filename token", token_key), ("engine label", label_key)):
    ncoll = 0
    lost = 0
    no_key = 0
    examples = []
    for (uid, stem), files in arts.items():
        seen = collections.defaultdict(list)
        for f in files:
            k = keyf(f)
            if not k:
                no_key += 1
                continue
            seen[k].append(f)
        for k, grp in seen.items():
            if len(grp) > 1:
                ncoll += 1
                lost += len(grp) - 1
                if len(examples) < 5:
                    examples.append((uid, stem, k, grp))
    print("%-22s colliding keys: %4d   files dropped: %4d   files with no key: %d"
          % (nm, ncoll, lost, no_key))
    for e in examples:
        print("        unit %-5d %-22s %-10s %s" % e)

print()
print("=== file counts per art ===")
c = collections.Counter(len(v) for v in arts.values())
print(sorted(c.items()))

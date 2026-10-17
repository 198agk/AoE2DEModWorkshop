# -*- coding: utf-8 -*-
"""What does a family-wide reskin cost, and what fraction of the villager's life
does a given donor actually cover?  Decides the default scope and the honest
warning text."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
from aoe2mod.dat import families as F
from aoe2mod.game import sprites as S

tk = A.open_toolkit()
tk._ensure()
ix = tk._reskin_art()
civs = tk._parsed[1]
F.warm(tk._stats, game_root=tk.game_root)
fams = F.build_families(civs)
DRS = os.path.join(tk.game_root, "resources", "_common", "drs", "graphics")

recs = {}
for civ in civs:
    for u in civ["units"]:
        recs.setdefault(u["id"], u)

records = [83, 224, 1810, 1875, 293, 295]   # villager-ish id set for scale
print("=== size of a family-wide reskin ===")
for name, ids in (("villager family", sorted(fams.get(83) or [83])),):
    files = set()
    for uid in ids:
        a = ix.art(recs.get(uid))
        if not a or a.get("kind") != "loose":
            continue
        for f in a["files"]:
            files.add(f)
    total = 0
    missing = 0
    for f in sorted(files):
        p1 = os.path.join(DRS, f + ".sld")
        p2 = os.path.join(DRS, f[:-3] + "_x2.sld") if f.endswith("_x1") else None
        for p in (p1, p2):
            if p and os.path.exists(p):
                total += os.path.getsize(p)
            else:
                missing += 1
    print("  %-18s %d distinct x1 files -> %d files on disk, %.1f MB, %d missing"
          % (name, len(files), 2 * len(files) - missing, total / 1e6, missing))
    print("  the v10 single-record version wrote 20 files / 18.9 MB")

print()
print("=== donor coverage over the whole villager family ===")
need = set()
for uid in sorted(fams.get(83) or [83]):
    a = ix.art(recs.get(uid))
    if a and a.get("kind") == "loose":
        need |= {k for k in a["tokens"]}
need.discard(None)
print("  the family needs %d animation key(s): %r" % (len(need), sorted(need)))

cands = []
for uid in sorted(recs):
    a = ix.art(recs[uid])
    if not a or a.get("kind") != "loose":
        continue
    got = set(a["tokens"])
    cov = need & got
    if len(cov) >= 6:
        # how many villager family members could be filled completely?
        full = 0
        partial = 0
        for vid in sorted(fams.get(83) or [83]):
            va = ix.art(recs.get(vid))
            if not va or va.get("kind") != "loose":
                continue
            if set(va["tokens"]) <= got:
                full += 1
            elif set(va["tokens"]) & got:
                partial += 1
        cands.append((len(cov), full, partial, uid, a["stem"], sorted(need - got)))
cands.sort(key=lambda t: (-t[1], -t[0], t[3]))
print("  best donors by 'family members fully covered':")
for cov, full, partial, uid, stem, miss in cands[:10]:
    print("      %-6d %-26s covers %2d/%d keys, %2d members fully, %2d partly, missing %r"
          % (uid, stem, cov, len(need), full, partial, miss))

# -*- coding: utf-8 -*-
r"""Is the tree's `Use Type: Tech` `Node ID` really the `.dat` tech index?

Earlier the project asserted it was, on this evidence:

  * `tech node ids outside the .dat tech array: 0`   <- a RANGE test
  * `row Name String ID == dat LanguageDLLName + 10000` for 5,081/5,244

A range test cannot separate "index into the same array" from "a different
numbering that happens to fall in range".  And the 34/35 case looks like a
counterexample:

  .dat tech 34 = 'War Galley'            .dat tech 35 = 'Galleon'
  tree Node 34 = 'Warships'              tree Node 35 = 'Galleons'
  panel Techs  = 34 -> '中型战船' (War Galley), 35 -> '重型战船' (Galleon)

Decide by identity per-row, not by count.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LANG = {}
kd = os.path.join(GAME, "resources", "en", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(kd, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                LANG.setdefault(int(k.strip()), v[1:-1])

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_dat = tk._tech_records()
trees = CT.load_trees(GAME)

print("A  .dat tech 22 is Loom -- find the tree row that means Loom")
br = trees["BRITONS"]
targets = {}
for r in CT.tech_rows(br):
    nid = r.get("Node ID")
    targets[nid] = (r.get("Name"), r.get("Name String ID"))
for nid in (22, 34, 35, 8, 12, 200, 201, 211):
    print("   tree Node %-5s Name=%-24r NameStringID=%s"
          % (nid, targets.get(nid, (None, None))[0],
             targets.get(nid, (None, None))[1]))

print()
print("B  the +10000 hypothesis, tested row by row for BRITONS")
rows = list(CT.tech_rows(br))
matched, mismatched, nolang = 0, [], 0
for r in rows:
    nid, sid = r.get("Node ID"), r.get("Name String ID")
    if nid is None or nid >= len(_dat) or sid is None:
        continue
    dll = (_dat[nid] or {}).get("LanguageDLLName")
    if not dll:
        nolang += 1
        continue
    if sid == dll + 10000:
        matched += 1
    else:
        mismatched.append((nid, r.get("Name"), sid, dll, LANG.get(sid)))
print("   rows: %d   +10000 matches: %d   mismatches: %d   no dat language: %d"
      % (len(rows), matched, len(mismatched), nolang))
for nid, nm, sid, dll, loc in mismatched[:15]:
    dn = (_dat[nid] or {}).get("name")
    print("      Node %-5s tree=%-24r(sid %s)  .dat=%-24r(dll %s) localized=%r"
          % (nid, nm, sid, dn, dll, loc))

print()
print("C  the 34/35 case in full")
for nid in (34, 35):
    d = _dat[nid] or {}
    r = CT.row_for(br, nid, CT.TECH_USE_TYPES) or {}
    print("   Node %-4s tree Name=%-14r NameStringID=%-8s | .dat internal=%-14r "
          "LanguageDLLName=%-6s localized=%r"
          % (nid, r.get("Name"), r.get("Name String ID"), d.get("name"),
             d.get("LanguageDLLName"), LANG.get(d.get("LanguageDLLName") or 0)))
# what does the tree's own name for node 34 mean?
print("   LANG[17034]=%r  LANG[17035]=%r  LANG[7000]=%r"
      % (LANG.get(17034), LANG.get(17035), LANG.get(7000)))

print()
print("D  so: how many tree Tech node ids map to a DIFFERENT .dat technology?")
allrows = {}
for s, t in trees.items():
    for r in CT.tech_rows(t):
        nid = r.get("Node ID")
        allrows.setdefault(nid, set()).add(r.get("Name"))
tot = diff = same = 0
examples = []
for nid in sorted(allrows):
    if nid is None or nid >= len(_dat):
        continue
    dn = (_dat[nid] or {}).get("name")
    tnames = {x for x in allrows[nid] if x}
    if not dn or not tnames:
        continue
    tot += 1
    if dn in tnames:
        same += 1
    else:
        diff += 1
        if len(examples) < 20:
            examples.append((nid, dn, sorted(tnames)[:3]))
print("   node ids where a .dat tech exists AND a tree name exists: %d" % tot)
print("   tree name == .dat internal name                        : %d" % same)
print("   tree name != .dat internal name                        : %d" % diff)
for nid, dn, tn in examples:
    print("      Node %-5s .dat=%-26r tree=%s" % (nid, dn, tn))

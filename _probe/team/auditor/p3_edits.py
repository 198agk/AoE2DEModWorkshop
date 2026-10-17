# -*- coding: utf-8 -*-
"""Audit probe 3 (fixed): do the two edits do what the design claims?

  A: CT.grant(britons, 2550)         -- is the granted row renderable?
  B: BP.remove_entry(panel, brit,74) -- does ONE removal remove EVERY visible
                                        Barracks Militia row for Britons?
"""
import copy, json, os, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


trees = CT.load_trees(GAME)
brit = trees["BRITONS"]
panels = BP.load_all(GAME)
p, kb = BP.panel_path_for(GAME, "Britons")
txt = panels[kb]["text"]
obj = panels[kb]["obj"]
print("panel file  :", p)
print("civ key     :", kb)
print("civ obj keys:", sorted(obj[kb]))
blks = BP.buildings(obj, kb)
print("buildings   : %d" % len(blks))

head("B1: every place unit 74 appears for Britons, before the edit")
tot = 0
for b in blks:
    for space in (BP.UNITS_KEY, BP.TECHS_KEY):
        h = [x for x in BP.entries(obj, kb, b.get("ID"), space) if x.get("ID") == 74]
        if h:
            print("   building %-5s %-7s n=%-3d  74 -> %d  %s"
                  % (b.get("ID"), space, len(BP.entries(obj, kb, b.get("ID"), space)),
                     len(h), h))
            tot += len(h)
print("   TOTAL unit-74 entries for Britons across all buildings: %d" % tot)

head("B2: what one remove_entry actually removes")
t2, removed = BP.remove_entry(txt, kb, 74, BP.UNITS_KEY)
print("   returned removed-flag: %r" % (removed,))
o2 = json.loads(t2)
after = []
for b in BP.buildings(o2, kb):
    for space in (BP.UNITS_KEY, BP.TECHS_KEY):
        h = [x for x in BP.entries(o2, kb, b.get("ID"), space) if x.get("ID") == 74]
        if h:
            after.append((b.get("ID"), space, len(h)))
print("   74-entries remaining for Britons: %d  %s"
      % (sum(a[2] for a in after), after))

head("B3: surgical check -- did other civs lose their Militia?")
ok, info = BP.verify_surgical(txt, t2)
print("   verify_surgical ok=%r" % (ok,))
print("   info=%s" % json.dumps(info, ensure_ascii=False))


def cnt_all(o, nid):
    n = 0
    for ck in o:
        for b in BP.buildings(o, ck):
            for space in (BP.UNITS_KEY, BP.TECHS_KEY):
                n += len([x for x in BP.entries(o, ck, b.get("ID"), space)
                          if isinstance(x, dict) and x.get("ID") == nid])
    return n


print("   unit-74 entries across ALL 58 civs before: %d" % cnt_all(obj, 74))
print("   unit-74 entries across ALL 58 civs after : %d" % cnt_all(o2, 74))
print("   civs listing 74 at building 12 before: %d"
      % sum(1 for ck in obj if BP.has_entry(obj, ck, 12, 74, BP.UNITS_KEY)))
print("   civs listing 74 at building 12 after : %d"
      % sum(1 for ck in o2 if BP.has_entry(o2, ck, 12, 74, BP.UNITS_KEY)))

head("A1: the exact row CT.grant writes into BRITONS")
edited = copy.deepcopy(brit)
dc, drow = CT.donor_row(trees, 2550, CT.UNIT_USE_TYPES)
print("   donor civ: %r" % dc)
n0 = len(CT.unit_rows(edited))
CT.grant(edited, 2550, drow)
row = CT.row_for(edited, 2550, CT.UNIT_USE_TYPES)
print("   rows before/after: %d -> %d" % (n0, len(CT.unit_rows(edited))))
print("   granted row == donor row byte-for-byte? %r" % (row == drow))
print("   row: %s" % json.dumps(row, ensure_ascii=False, sort_keys=True))
print("   can_build(edited,2550)=%r  node_status=%r"
      % (CT.can_build(edited, 2550), CT.node_status(edited, 2550)))
print("   Trigger Tech ID copied = %r ; Britons has that TECH row? %r"
      % (row.get("Trigger Tech ID"),
         CT.row_for(edited, row.get("Trigger Tech ID"), CT.TECH_USE_TYPES) is not None))
# duplicates?
dups = [r for r in CT.unit_rows(edited) if r.get("Node ID") == 2550]
print("   rows with Node ID 2550 in edited tree: %d" % len(dups))

head("A2: how the 4 native civs differ from the granted Britons row")
for c in ("INCAS", "BRITONS"):
    t = edited if c == "BRITONS" else trees[c]
    r = CT.row_for(t, 2550, CT.UNIT_USE_TYPES)
    pe = BP.find_entry(obj, BP.civ_key_for(panels, c), 2550, BP.UNITS_KEY)[1]
    print("   %-8s row=%-5s panelentry=%r" % (c, r is not None, pe))

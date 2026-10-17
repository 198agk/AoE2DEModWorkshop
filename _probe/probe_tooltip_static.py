# -*- coding: utf-8 -*-
r"""Is the tooltip line '升级：升级到精锐炮舰' STATIC help text or generated?

The Poles dock screenshot shows, hovering the Cannon Galleon button:

    建造炮舰（价格：200木，150金）
    ...
    升级：升级到精锐炮舰
    (码头)；攻击力，射程，护甲，速度，费用，生产速度
    (大学)；提升抵抗僧侣的能力（修道院）。
    (热键：E)

Poles' tree marks 691 Elite Cannon Galleon `NotAvailable`.  So either that line is
DYNAMIC -- and the dock really is offering an upgrade the tree refuses, which would
mean the menu unions the layers -- or it is part of unit 420's own help string and
civ-independent.

Decide by looking up unit 420's help string in the shipped string table.  If the
literal text is there, the line proves nothing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

LANG = {}
for loc in ("zh", "en"):
    d = os.path.join(GAME, "resources", loc, "strings", "key-value")
    LANG[loc] = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        for line in open(os.path.join(d, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if v.startswith('"') and v.endswith('"'):
                LANG[loc][k.strip()] = v[1:-1]

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
recs = tk._unit_records()

print("A  unit 420 Cannon Galleon: its name/help string ids and their text")
for uid in (420, 691, 550, 588):
    r = recs[uid] if uid < len(recs) else None
    if not r:
        continue
    nm_id = r.get("language_dll_name")
    hp_id = r.get("language_dll_help")
    print("   unit %-5s language_dll_name=%-7s help=%-7s"
          % (uid, nm_id, hp_id))
    for loc in ("zh", "en"):
        print("      %s name=%r" % (loc, LANG[loc].get(str(nm_id))))
        h = LANG[loc].get(str(hp_id))
        if h:
            print("      %s help=%r" % (loc, h[:400]))

print()
print("B  the decisive question: does unit 420's help text contain the upgrade line?")
r420 = recs[420]
h420 = str(r420.get("language_dll_help"))
zh = LANG["zh"].get(h420, "")
print("   help id %s ->" % h420)
print("   %r" % zh[:600])
print()
if "精锐炮舰" in zh:
    print("   VERDICT: the string ALREADY CONTAINS 精锐炮舰")
    print("   -> the tooltip line is STATIC help text, civ-independent.")
    print("      It does NOT prove Poles may research the upgrade.")
else:
    print("   VERDICT: the help text does NOT mention the upgrade")
    print("   -> the line in the screenshot is generated DYNAMICALLY.")

print()
print("C  so what would a dynamic line look like?  Check a case where the answer")
print("   is known: Sicilians' Onager (550) -- its tree grants 588,")
print("   and the user saw '升级到重型投石车'.")
r550 = recs[550]
h550 = str(r550.get("language_dll_help"))
zh550 = LANG["zh"].get(h550, "")
print("   unit 550 help id %s ->" % h550)
print("   %r" % zh550[:600])
print("   contains 重型投石车: %s" % ("重型投石车" in zh550))

print()
print("D  and a control: a civ that CANNOT upgrade, where the tooltip still shows")
print("   the line, would prove it static.")
print("   Poles help text for 420 == the same id for every civ: %s"
      % (r420.get("language_dll_help")))
print("   (the help string id is a property of the UNIT, not of a civ,")
print("    so this text is identical for every civilization that has unit 420)")

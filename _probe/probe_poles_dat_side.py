# -*- coding: utf-8 -*-
r"""The decisive third layer: does the .dat allow Poles the Elite Cannon Galleon?

The user has now answered the one open question in the shipped game:

    2026-10-18, Poles, dock: there is NO Elite Cannon Galleon upgrade button.

That single observation is only decisive if BOTH other layers are known:

    tree   691 NotAvailable, and no row for tech 376 at all   -> refuses
    panel  691 listed in Units, 376 listed in Techs           -> allows
    .dat   ... the question this probe answers ...

If the .dat ALSO allows it, then the menu follows neither the .dat nor the
panel, and the tree is the only layer that agrees with what the user saw.  If
the .dat refuses it (tech 376 absent, or unit 691 not in the Poles' unit
table), then the menu might be reading the .dat and the tree, and the panel
would still be excluded -- a weaker but still useful conclusion.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_poles_dat_side.py
"""
import os
import sys
import io
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

raw, how = P.load_dat(DAT)
st = P.Parser(raw).parse()          # quiet: swallow the stage-by-stage chatter
if False:
    pass


def _civ_named(want):
    for c in st["civs"]:
        if (c.get("name") or "").strip().lower() == want.lower():
            return c
    return None


print("parsed %d civs, %d techs (%s)" % (len(st["civs"]), len(st["techs"]), how))

pol = _civ_named("Poles")
print()
print("A  the Poles' own unit table in the .dat")
if pol is None:
    print("     no civ literally named Poles; first civs: %s"
          % [c.get("name") for c in st["civs"][:6]])
else:
    ids = set(u["id"] for u in pol["units"])
    print("     civ name=%r  units=%d" % (pol.get("name"), len(ids)))
    for uid, label in ((420, "Cannon Galleon"), (691, "Elite Cannon Galleon"),
                       (527, "Demolition Ship"), (528, "Heavy Demolition Ship")):
        print("     unit %-5s %-24s in the Poles' table: %s"
              % (uid, label, uid in ids))

print()
print("B  the techs the .dat carries (tech ids ARE array indices -- read_tech does")
print("   not store an id field, so lookup must be by position)")
techs = st["techs"]
for tid, label in ((376, "Elite Cannon Galleon upgrade"),
                   (37, "Cannon Galleon upgrade"),
                   (244, "Heavy Demolition Ship upgrade"),
                   (205, "Cannon Galleon research"),
                   (320, "Siege Onager upgrade")):
    if tid >= len(techs):
        print("     tech %-5s %-30s OUT OF RANGE (only %d techs)"
              % (tid, label, len(techs)))
        continue
    t = techs[tid]
    print("     tech %-5s %-30s civ=%-4s name=%r"
          % (tid, label, t.get("civ"), t.get("name")))
    print("              required_techs=%s research_locations=%s"
          % (t.get("required_techs", "<not stored>"),
             t.get("research_locations")))

print()
print("C  the verdict table")
print("     layer   allows Elite Cannon Galleon for Poles?")
print("     tree    NO   (691 NotAvailable, tech 376 has no row)")
print("     panel   YES  (691 in Units, 376 in Techs)")
print("     .dat    see A and B above")
print("    The user saw NO button.  Any layer that says YES is not what fills")
print("    the menu -- unless it is overridden by one that says NO.")
sys.exit(0)

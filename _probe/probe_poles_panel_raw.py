# -*- coding: utf-8 -*-
r"""Where does the shipped panel actually file the Poles' Elite Cannon Galleon?

`test_protocol_subjects` classified POLES / building 45 / unit 691 as kind-P,
i.e. "the panel lists it while the tree refuses it".  But
`probe_poles_dock_test` looked up building 45 in the Poles panel block and found
ZERO entries at all, in both `Units` and `Techs`.

Those cannot both be true, so one of the two lookups is wrong.  This probe reads
the raw panel file directly (no helper layer) and prints, for the Poles:

  * the building ids the panel actually has, with entry counts
  * every panel entry whose ID is 420 / 691 / 376, with its building
  * what `buildpanel.building_block` returns for id 45 and whether it is None

The outcome decides whether the dock test is a real kind-P subject or a
classifier artefact.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_poles_panel_raw.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PANEL = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


with open(PANEL, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

print("A  top-level keys (civ names) mention 'Poles'?")
hits = [k for k in raw if "pole" in k.lower()]
print("     %s" % hits)

name = hits[0] if hits else "Poles"
obj = raw[name]
print("     using civ key: %r" % name)
print("     its top keys: %s" % list(obj)[:6])

blds = obj.get("Buildings") or []
print("     building blocks: %d" % len(blds))

print()
print("B  building ids present, with entry counts (only ids near the dock)")
for b in blds:
    bid = _int(b.get("ID"))
    nu = len(b.get("Units") or [])
    nt = len(b.get("Techs") or [])
    if bid in (45, 47, 49, 12, 87) or nu + nt:
        if bid in (45, 47, 49, 12, 87):
            print("     building %-5s Units=%-3d Techs=%-3d %s"
                  % (bid, nu, nt, b.get("Name")))

print()
print("C  every entry with ID 420 / 691 / 376 anywhere in the Poles block")
for b in blds:
    for space in ("Units", "Techs"):
        for e in (b.get(space) or []):
            if _int(e.get("ID")) in (420, 691, 376):
                print("     bldg %-5s %-6s id=%-5s %-24s age=%s prq=%s"
                      % (b.get("ID"), space, e.get("ID"), e.get("Name"),
                         e.get("RequiredAge"), e.get("PrereqTech")))

print()
print("D  what the helper layer returns")
panels = BP.load_all(GAME)
key = BP.civ_key_for(panels, "Poles")
print("     civ_key_for -> %r" % key)
blk = BP.building_block(panels[key], key, 45)
print("     building_block(45) is None? %s" % (blk is None))
if blk is not None:
    print("     its keys: %s" % list(blk)[:6])
    print("     Units=%d Techs=%d"
          % (len(BP.entries(blk, "Units")), len(BP.entries(blk, "Techs"))))
    print("     has_entry(691, Units) = %s"
          % BP.has_entry(blk, 691, "Units"))
print("     ids available on this civ: %s"
      % sorted(_int(b.get("ID")) for b in (panels[key].get("Buildings") or []))[:12])

print()
print("POLES PANEL RAW: compare B/C against D.  If C finds 691 but D does not, the")
print("helper is looking in the wrong block and the kind-P classification is fine.")
print("If C also finds nothing, the Poles/691 kind-P claim is an artefact.")
sys.exit(0)

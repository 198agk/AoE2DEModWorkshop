# -*- coding: utf-8 -*-
"""Why did the panel lookup return None?  (my probe's shape, or the file's?)

`probe_json_is_engine_data.py` printed
    panel Turks    Archery Range lists unit 5 : None
    panel Britons  Archery Range lists unit 5 : None
for building 87.  None means the building record was not found at all, which is
a different statement from "the building is there and omits the unit".

Find out which, and record the answer.  Never let a None stand unexamined in a
pin: it usually means the probe is looking in the wrong place.
"""
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import buildpanel as BP    # noqa: E402

GAME = A.open_toolkit().game_root
panels = BP.load_all(GAME)
print("panel files loaded : %d" % len(panels))
print("keys (first 12)    : %s" % list(panels)[:12])

for civ in ("Turks", "Britons"):
    pk = BP.civ_key_for(panels, civ)
    v = panels[pk]
    print()
    print("--- %s -> key %r  (%s)" % (civ, pk, type(v).__name__))
    obj = v["obj"] if isinstance(v, dict) and "obj" in v else (
        v[1] if isinstance(v, tuple) else v)
    print("    obj type: %s" % type(obj).__name__)
    if not isinstance(obj, dict):
        print("    not a dict, stop")
        continue
    print("    obj keys: %s" % list(obj)[:10])
    if "Buildings" in obj:
        blds = obj["Buildings"]
    elif "civs" in obj:
        print("    this is the AGGREGATE form (top-level 'civs')")
        continue
    else:
        print("    no Buildings key")
        continue
    print("    buildings in this civ: %d" % len(blds))
    ids = [b.get("ID") for b in blds]
    print("    building IDs: %s" % ids[:40])
    print("    contains 87 (Archery Range): %s" % (87 in ids))
    print("    contains 12 (Barracks)     : %s" % (12 in ids))
    for b in blds[:3]:
        print("        sample building keys: %s  units %d"
              % (list(b)[:6], len(b.get("Units") or [])))
    # find the archery range by name
    for b in blds:
        if "Archery" in str(b.get("Name", "")):
            us = [u.get("ID") for u in (b.get("Units") or [])]
            print("    named Archery Range: ID=%s units=%s" % (b.get("ID"), us))
            print("    ...lists unit 5? %s" % (5 in us))

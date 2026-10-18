# -*- coding: utf-8 -*-
"""What is that .dat in the availability mod, and why is edit_count 0?

An availability build reports changes_dat=False yet ships
resources/_common/dat/empires2_x2_p1.dat.  Measure whether it is byte-identical
to the base file (a 12 MB no-op) and whether the two JSON layers changed.
"""
import hashlib
import json
import os
import sys

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(ROOT, r"resources\_common\dat\empires2_x2_p1.dat")
MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s4b", "revoke")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


man = json.load(open(os.path.join(MOD, "info.json"), encoding="utf-8")) \
    if os.path.isfile(os.path.join(MOD, "info.json")) else {}
print("info.json keys:", sorted(man))
mdat = os.path.join(MOD, r"resources\_common\dat\empires2_x2_p1.dat")
print("base .dat size:", os.path.getsize(BASE), "sha:", sha(BASE))
print("mod  .dat size:", os.path.getsize(mdat), "sha:", sha(mdat))
print("identical to base:", sha(BASE) == sha(mdat))
for rel in (r"resources\_common\dat\CivTechTrees\BRITONS.json",
            r"resources\_common\dat\futuravailableunits.json"):
    p = os.path.join(MOD, rel)
    src = os.path.join(ROOT, rel)
    print("%-58s mod=%d base=%d identical=%s"
          % (rel, os.path.getsize(p), os.path.getsize(src) if os.path.isfile(src) else -1,
             (sha(p) == sha(src)) if os.path.isfile(src) else "n/a"))

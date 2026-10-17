# -*- coding: utf-8 -*-
"""Audit probe 13: does the built mod even LOAD, and can another mod outrank it?
Plus: is there a per-civ availability block in the .dat the parser discards?"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, glob, inspect
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT
from aoe2mod.dat import parser as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
W = _HERE_PATH()

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

head("13a: what did build_smoke5 actually emit?")
OUT = os.path.join(W, "_probe", "out_smoke5")
print("   exists:", os.path.isdir(OUT))
if os.path.isdir(OUT):
    n = 0
    for r, d, fs in os.walk(OUT):
        for f in sorted(fs):
            p = os.path.join(r, f)
            n += 1
            print("   %-70s %12d B" % (os.path.relpath(p, OUT), os.path.getsize(p)))
    print("   total files: %d" % n)

head("13b: how many panel files does the engine layering expose, and does the mod ship all of them?")
paths = BP.panel_paths(GAME)
print("   BP.panel_paths(GAME) ->")
for p in paths:
    print("      %s" % (p.replace(GAME, "<GAME>") if p else p))
print("   BP.PANEL_REL:", getattr(BP, "PANEL_REL", None))
print("   mod ships:", [rel for rel in (BP.PANEL_REL,) if os.path.isfile(os.path.join(OUT, rel or ""))] if os.path.isdir(OUT) else "-")

head("13c: the player profile -- local mods and mod-status.json")
print("   profile exists:", os.path.isdir(PROFILE))
for acc in sorted(os.listdir(PROFILE)) if os.path.isdir(PROFILE) else []:
    print("   account dir: %s" % acc)
local = None
for acc in sorted(os.listdir(PROFILE)) if os.path.isdir(PROFILE) else []:
    cand = os.path.join(PROFILE, acc, "mods", "local")
    if os.path.isdir(cand):
        local = cand
        print("   local mods dir: %s" % cand)
        for d in sorted(os.listdir(cand)):
            full = os.path.join(cand, d)
            print("      %-46s %s" % (d, "dir" if os.path.isdir(full) else "file"))
            if os.path.isdir(full):
                for r, _dd, fs in os.walk(full):
                    for f in sorted(fs):
                        print("         %s" % os.path.relpath(os.path.join(r, f), full))
    ms = os.path.join(PROFILE, acc, "mods", "mod-status.json")
    if os.path.isfile(ms):
        print("   mod-status.json: %s" % ms)
        j = json.load(open(ms, encoding="utf-8-sig"))
        print("      top keys: %s" % (list(j)[:10] if isinstance(j, dict) else type(j)))

head("13d: any OTHER mod in ANY profile enumerating a conflicting path?")
for acc in sorted(os.listdir(PROFILE)) if os.path.isdir(PROFILE) else []:
    base = os.path.join(PROFILE, acc, "mods")
    if not os.path.isdir(base):
        continue
    for r, d, fs in os.walk(base):
        for f in fs:
            if f in ("empires2_x2_p1.dat", "futuravailableunits.json", "BRITONS.json"):
                print("   %s" % os.path.join(r, f))

head("13e: does read_civ DISCARD a per-civ unit-availability block?")
print("\n".join(inspect.getsource(P.read_civ).splitlines()))

head("13f: is there a per-civ 'disabled units' count near read_civ's call site?")
src = inspect.getsource(P)
i = src.find("read_civ(")
while i != -1 and i < len(src):
    ln = src[:i].count("\n") + 1
    print("   line %d: %s" % (ln, src.splitlines()[ln - 1].strip()))
    i = src.find("read_civ(", i + 1)

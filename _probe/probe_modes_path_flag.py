# -*- coding: utf-8 -*-
r"""THE UNEXPLAINED LEAD: `use_modes_path_for_mods: true` on the DAT storage point.

Every other storage point behaves like WIDGETUI, which provably accepts a loose
override (a depth-3 emblem PNG from a mod is visible in game).  The DAT storage
point is different in exactly one measured way:

    modes/Pompeii/Pompeii.json -> storage_point_list -> the DAT entry is the ONLY
    one of 28 flagged `use_modes_path_for_mods: true`

and the single reported tree-write failure (2026-10-14) was a write into that
storage point.  So the flag is the natural suspect for "why did the tree write not
show up".

Three concrete questions:

  A  does the MODE tree carry its own `CivTechTrees/` (i.e. is the whole DAT layer
     redirected for a mode)?
  B  what does the exe do with the flag -- is it a path substitution, a search-root
     change, or a fallback ordering?
  C  if the flag redirects mod lookup to `modes/<Name>/...`, then a mod's
     `resources/_common/dat/CivTechTrees/BRITONS.json` would be looked for at
     `modes/Pompeii/resources/_common/dat/CivTechTrees/BRITONS.json` INSTEAD --
     which would explain the failure exactly, and would mean the write must be
     placed somewhere else (or that both names must be shipped).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
PJ = os.path.join(GAME, "modes", "Pompeii", "Pompeii.json")

print("A  the mode's own DAT tree")
for sub in ("resources/_common/dat/CivTechTrees",
            "resources/_common/dat",
            "resources/_common"):
    d = os.path.join(GAME, "modes", "Pompeii", sub.replace("/", os.sep))
    if os.path.isdir(d):
        ents = sorted(os.listdir(d))
        print("   %-42s %d entries" % (sub, len(ents)))
        for e in ents[:10]:
            p = os.path.join(d, e)
            if os.path.isfile(p):
                print("        %-42s %d B" % (e, os.path.getsize(p)))
        if len(ents) > 10:
            print("        ... and %d more" % (len(ents) - 10))
    else:
        print("   %-42s (absent)" % sub)

print()
print("B  the flag's neighbours in the exe")
data = open(EXE, "rb").read()
for lit in (b"use_modes_path_for_mods", b"use_modes_path",
            b"storage_point_list", b"modes_path", b"modes\\", b"CivTechTrees/%s.json"):
    offs = []
    i = data.find(lit)
    while i >= 0 and len(offs) < 8:
        offs.append(i)
        i = data.find(lit, i + 1)
    print("   %-26s %s" % (lit.decode(errors="replace"),
                           [hex(o) for o in offs] or "none"))

print()
print("C  the NUL-delimited run around the flag (string-pool neighbours)")
i = data.find(b"use_modes_path_for_mods")
if i < 0:
    print("   flag not found")
else:
    lo = data.rfind(b"\x00", 0, i - 400)
    hi = data.find(b"\x00", i + 400)
    seg = data[max(0, i - 700):i + 700]
    runs = [r for r in seg.split(b"\x00") if 1 < len(r) < 60
            and all(32 <= c < 127 for c in r)]
    print("   runs around it (order preserved):")
    for r in runs:
        print("        %s" % r.decode())

print()
print("D  every storage-point type/path pair, and which carries the flag")
obj = json.loads(open(PJ, "rb").read().decode("utf-8-sig"))
spl = obj.get("storage_point_list") or []
print("   %-22s %-46s %s" % ("type", "path", "modes-aware"))
for s in spl:
    print("   %-22s %-46s %s"
          % (s.get("type"), s.get("path"),
             "YES" if s.get("use_modes_path_for_mods") else "-"))

print()
print("E  does the MODE dir actually get populated by this install?")
md = os.path.join(GAME, "modes", "Pompeii")
n = 0
for _r, _d, fs in os.walk(md):
    n += len(fs)
print("   modes/Pompeii total files: %d" % n)

print()
print("F  the decisive question: is there a SECOND copy of the tree anywhere")
hits = []
for root, _d, fs in os.walk(GAME):
    for f in fs:
        if f.upper().endswith(".JSON") and root.lower().endswith("civtechtrees"):
            hits.append(os.path.join(root, f))
print("   CivTechTrees directories on this install: %d file(s)" % len(hits))
dirs = sorted({os.path.dirname(h) for h in hits})
for d in dirs:
    cnt = sum(1 for h in hits if os.path.dirname(h) == d)
    print("      %-70s %d file(s)" % (os.path.relpath(d, GAME), cnt))

print()
print("G  what the exe says about a per-civ file template vs a mode path")
for pat in (rb"[a-zA-Z\\/_.%]{4,60}modes[a-zA-Z\\/_.%]{0,60}",
            rb"[a-zA-Z\\/_.%]{4,60}CivTechTrees[a-zA-Z\\/_.%]{0,60}"):
    found = sorted({m.group(0) for m in re.finditer(pat, data)})
    print("   pattern %s -> %d distinct" % (pat[:40], len(found)))
    for f in found[:14]:
        print("        %s" % f.decode(errors="replace"))

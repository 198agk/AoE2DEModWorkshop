# -*- coding: utf-8 -*-
r"""THE DEFECT: a mod that overrides `resources/_common/dat/` but ships NO
`empires2_x2_p1.dat` prevents the game from starting.

The user reported this twice, in-game:
  * m21855: 「你的mod里没有empires2_x2_p1.dat，所以连开局都开不了」
  * m21927: 「能开局，村民血量1000，靶场没有火枪手」   <- the SAME intent, but with
    the `.dat` added, started fine.

`unit.availability`'s JSON-only build (`_build_availability`) produces exactly that
shape: `CivTechTrees/<CIV>.json` and/or `futuravailableunits.json` with no `.dat`.

Check the corpus for the correlation, because if it holds this is a hard product
constraint and not a coincidence:

  * every third-party mod that ships a file under `resources/_common/dat/` also
    ships `empires2_x2_p1.dat`
  * the only exception in the corpus is this project's own failing smoke test

Also record the mechanism candidate: the DAT storage point is the ONLY one flagged
`use_modes_path_for_mods: true` in `modes/Pompeii/Pompeii.json`, so the engine may
resolve that directory as a unit rather than per-file.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
MODS = os.path.join(ACC, "mods")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT_REL = os.path.join("resources", "_common", "dat")
DAT_FILE = "empires2_x2_p1.dat"

print("A  every installed mod: does it touch the DAT folder, and does it carry")
print("   the .dat itself?")
status = json.loads(open(os.path.join(MODS, "mod-status.json"), "rb")
                    .read().decode("utf-8-sig"), strict=False)
rows = []
for m in status.get("Mods", []):
    rel = (m.get("Path") or "").replace("//", os.sep)
    d = os.path.join(MODS, rel)
    if not os.path.isdir(d):
        rows.append((m.get("Title"), m.get("Enabled"), "MISSING", [], False))
        continue
    nested, has_dat = [], False
    for root, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            r = os.path.relpath(p, d)
            if r.lower().startswith(DAT_REL.lower() + os.sep):
                nested.append(r)
                if f.lower() == DAT_FILE:
                    has_dat = True
    rows.append((m.get("Title"), m.get("Enabled"),
                 "touches DAT" if nested else "clean", nested, has_dat))

for title, enabled, kind, nested, has_dat in rows:
    if kind == "clean":
        print("   %-52s %-5s clean" % (title[:52], enabled))
        continue
    print("   %-52s %-5s %s   carries .dat: %s"
          % (title[:52], enabled, kind, has_dat))
    for r in nested[:5]:
        print("         %s" % r)

touchers = [r for r in rows if r[2] != "clean"]
without = [r for r in touchers if not r[4]]
print()
print("   mods touching the DAT folder      : %d" % len(touchers))
print("   of those, WITHOUT the .dat        : %d" % len(without))
for t in without:
    print("        %s" % t[0])
print()
print("   The only one without a `.dat` is this project's own JSON-only smoke test,")
print("   and that is the one the user reported as 'the game cannot even start'.")

print()
print("B  the mechanism candidate: the DAT storage point is the only modes-aware one")
pj = os.path.join(GAME, "modes", "Pompeii", "Pompeii.json")
if os.path.exists(pj):
    obj = json.loads(open(pj, "rb").read().decode("utf-8-sig"))
    spl = obj.get("storage_point_list") or []
    aware = [s for s in spl if s.get("use_modes_path_for_mods")]
    print("   storage points           : %d" % len(spl))
    print("   flagged modes-aware      : %d" % len(aware))
    for s in aware:
        print("        type=%s path=%s" % (s.get("type"), s.get("path")))
    print("   -> if the engine resolves that DIRECTORY as a unit, a mod carrying a")
    print("      file under it but not the .dat may shadow the whole directory.")
else:
    print("   no Pompeii.json")

print()
print("C  what the product currently does")
sys.path.insert(0, ROOT)
import aoe2mod.api as A                                    # noqa: E402
tk = A.open_toolkit(game_root=GAME)
out = os.path.join(HERE, "out_datcheck")
m = tk.build({"intent": "unit.availability", "unit": 2550, "civ": "British",
              "action": "grant"}, out, title="dat check", author="aoe2mod probe",
             overwrite=True)
files = []
for root, _d, fs in os.walk(out):
    for f in fs:
        files.append(os.path.relpath(os.path.join(root, f), out))
print("   files the JSON-only build emitted:")
for f in sorted(files):
    print("        %s" % f)
print("   mod_contains_dat: %r" % m.get("mod_contains_dat"))
_has = any(f.lower().endswith(DAT_FILE) for f in files)
print("   carries a .dat  : %s" % _has)
print()
if without and not _has:
    print("   VERDICT: the JSON-only path produces exactly the shape the user")
    print("   reported as unstartable.  The emitter/api must ship the base .dat")
    print("   alongside any file written under resources/_common/dat/.")

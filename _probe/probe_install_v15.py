# -*- coding: utf-8 -*-
r"""Install `dsh test v15` and verify what the engine will actually see.

Installing is a WRITE into the user's game profile, so this probe verifies the
result instead of trusting `install()`'s return value:

  * the folder sits under `<account>/mods/local/` with `info.json` at its root
  * `mod-status.json` lists it ENABLED and first (priority wins)
  * the two tree files and the `.dat` are byte-identical to what was built
  * the PROFILE copy -- not the build output -- is what gets re-parsed

Why v15 exists: v14 asked the right question (does the game read a mod's
`CivTechTrees/<CIV>.json`?) and the user's reading was "nothing changed".  But
v14 shipped only a byte-identical `.dat` plus two tree files, so "the mod never
loaded" and "the tree half was ignored" look identical on screen -- the same
confounder that made smoke5 AMBIGUOUS.  v15 adds the one control group that has
been proven in-game (villager family -> 1000 hp, `dsh test v7`, 2026-10-16), so
one launch answers both questions.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v15")
VILLAGER = 83
HP = 1000
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name[:70], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


print("A  build output is present and complete")
info = os.path.join(OUT, "info.json")
check("info.json exists", os.path.isfile(info))
title = json.load(open(info, encoding="utf-8-sig")).get("Title")
print("   Title: %s" % title)
check("the Title fits the engine's 100 UTF-8 bytes",
      len((title or "").encode("utf-8")) <= 100,
      "%d bytes" % len((title or "").encode("utf-8")))

print()
print("B  install it into the profile")
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
man = tk.install(OUT, kind="local", enabled=True, position=0, overwrite=True)
for k in ("name", "path", "enabled", "position", "requires_game_restart"):
    print("   %-22s %r" % (k, man.get(k)))
check("install reported success", bool(man) and not man.get("error"), man.get("error"))

prof = G.find_profile_root()
# Mods live under a PER-ACCOUNT folder; ask `read_status_doc` which one.
_doc0, _acc0, _raw0 = G.read_status_doc(prof)
dest = os.path.join(G.account_mods_dir(_acc0, "local"), man.get("name") or "")
print("   profile: %s" % prof)
print("   account: %s" % _acc0)
print("   dest:    %s" % dest)
check("the folder the engine will read exists", os.path.isdir(dest))
check("info.json is at the mod ROOT (no resources/ wrapper)",
      os.path.isfile(os.path.join(dest, "info.json")))

print()
print("C  the status file lists it ENABLED, at the top")
doc, path, _raw = G.read_status_doc(prof)
print("   status file: %s" % path)
ents = doc.get("Mods") or []
mine = [i for i, e in enumerate(ents)
        if os.path.basename(str(e.get("Path") or "")) == man.get("name")]
check("exactly one entry for this mod", len(mine) == 1, mine)
if mine:
    e = ents[mine[0]]
    check("it is Enabled", bool(e.get("Enabled")), e.get("Enabled"))
    check("it is first (priority wins)", mine[0] == 0, mine[0])
    print("   path in status: %s" % e.get("Path"))

print()
print("D  the installed files match the built files byte for byte")
for rel in ("resources/_common/dat/CivTechTrees/INCAS.json",
            "resources/_common/dat/CivTechTrees/BRITONS.json",
            "resources/_common/dat/empires2_x2_p1.dat"):
    a = os.path.join(OUT, rel.replace("/", os.sep))
    b = os.path.join(dest, rel.replace("/", os.sep))
    check("installed %s matches" % rel.split("/")[-1],
          os.path.isfile(b) and sha(a) == sha(b),
          "" if os.path.isfile(b) else "missing")

print()
print("E  re-read the PROFILE copies and assert BOTH halves' premises")
for key, want, label in (("INCAS", False, "Incas refuses 2550"),
                         ("BRITONS", True, "British allows 2550")):
    p = os.path.join(dest, "resources", "_common", "dat", "CivTechTrees",
                     "%s.json" % key)
    if not os.path.isfile(p):
        check(label, False, "missing file")
        continue
    t = json.load(open(p, encoding="utf-8"))
    check(label, CT.can_build(t, 2550) is want, CT.can_build(t, 2550))
    check("%s tree is chain-closed" % key, CT.dangling_links(t) == [],
          CT.dangling_links(t))

# The control half, read out of the INSTALLED .dat with the shipped bytes as
# the baseline: they must differ, and the only difference we authored is the
# villager family's hit points.
print()
print("F  the CONTROL half, read back from the installed .dat")
from aoe2mod.dat import parser as P                         # noqa: E402
import contextlib                                           # noqa: E402
import io                                                   # noqa: E402


def hp_of(path):
    raw, _how = P.load_dat(path)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return sorted({u.get("hit_points") for c in p.stats["civs"]
                   for u in (c.get("units") or []) if u.get("id") == VILLAGER})


check("the shipped villager is 25 hp (the baseline is not already 1000)",
      hp_of(G.dat_path(GAME)) == [25], hp_of(G.dat_path(GAME)))
check("the INSTALLED villager is %d hp (the control will be visible)" % HP,
      hp_of(os.path.join(dest, "resources", "_common", "dat",
                         "empires2_x2_p1.dat")) == [HP],
      hp_of(os.path.join(dest, "resources", "_common", "dat",
                         "empires2_x2_p1.dat")))
check("the installed .dat is NOT the shipped one",
      sha(os.path.join(dest, "resources", "_common", "dat",
                       "empires2_x2_p1.dat")) != sha(G.dat_path(GAME)))

print()
if fails:
    print("INSTALL v15: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("INSTALL v15: ALL CHECKS PASSED")
print("   installed at: %s" % dest)
print("   开局看三处：村民血量 1000 / 印加兵营没有蔷琵侦察兵 / 不列颠黑暗时代兵营有蔷琵侦察兵")

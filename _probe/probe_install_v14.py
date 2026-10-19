# -*- coding: utf-8 -*-
r"""Install (or re-install) `dsh test v14` and verify what the engine will see.

Installing is a WRITE into the user's game profile, so the probe verifies the
result rather than trusting `install()`'s return value:

  * the folder sits under `<profile>/mods/local/` with `info.json` at its root
  * `mod-status.json` lists it ENABLED and at the top (priority wins)
  * the two tree files are byte-identical to what was built
  * the profile copy -- not the build output -- is what gets re-parsed

Why v14 matters (see the builder's docstring): it is the first mod in this
project that changes ONLY the `CivTechTrees` layer.  Every earlier attempt
either edited the `.dat` at the same time, or deleted a node and left a dangling
`Link ID` (a shape no shipped file has), or also edited the panel.  So a reading
from this mod is the first one that can be attributed to the tree layer alone.
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v14")
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
# The mods live under a PER-ACCOUNT folder: `<profile>/<account>/mods/local/<name>`.
# `read_status_doc` already resolves which account the tool installs into, so ask
# it rather than guessing `<profile>/mods/...` (that path does not exist, and a
# probe that checks it fails while the install is perfectly fine).
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
          os.path.isfile(b) and sha(a) == sha(b), b if not os.path.isfile(b) else "")

print()
print("E  re-read the PROFILE copies and assert the experiment's premise")
from aoe2mod.game import civtechtrees as CT                 # noqa: E402
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

print()
if fails:
    print("INSTALL v14: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("INSTALL v14: ALL CHECKS PASSED")
print("   installed at: %s" % dest)

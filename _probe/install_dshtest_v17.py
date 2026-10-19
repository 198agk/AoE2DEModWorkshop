# -*- coding: utf-8 -*-
r"""Install dsh test v17 through the product's own installer and verify it.

Using ``locations.install_mod`` rather than a raw copy is deliberate: it is the
path the product ships, so a bad install here is a product defect and not a
probe bug.  The 2026-10-19 ``move`` fix (a local folder the game registered by
itself used to stay pinned at the end of the list) is exercised here: v17 is a
brand-new folder, but it asks for position 0 anyway.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from aoe2mod.game import civtechtrees as CT                 # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SRC = os.path.join(HERE, "out_dshtest_v17")
NAME = "dsh test v17 印加不能再造蔷琵侦察兵"
UNIT = 2550
TREE_KEY = "INCAS"

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (("  :: " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


prof = G.find_profile_root()
acc = G.pick_account(prof)
print("profile: " + prof)
print("account: " + acc)

doc0, _, _ = G.read_status_doc(prof)
n0 = len(doc0.get("Mods") or [])
print("mods before: %d" % n0)

man = G.install_mod(SRC, prof, name=NAME, title=NAME, kind="local",
                    enabled=True, position=0, account=acc, overwrite=True)
print("install manifest: " + repr(json.dumps(man, ensure_ascii=False, default=str)[:400]))

dst = os.path.join(G.account_mods_dir(acc, "local"), NAME)
check("folder landed under the account's local/", os.path.isdir(dst), dst)
check("info.json at the mod root", os.path.isfile(os.path.join(dst, "info.json")))
for rel in ("resources/_common/dat/empires2_x2_p1.dat",
            "resources/_common/dat/CivTechTrees/%s.json" % TREE_KEY):
    check("installed: " + rel, os.path.isfile(os.path.join(dst, *rel.split("/"))), rel)
    check("byte-identical to the build output: " + rel,
          open(os.path.join(dst, *rel.split("/")), "rb").read()
          == open(os.path.join(SRC, *rel.split("/")), "rb").read(), rel)

doc, _, _ = G.read_status_doc(prof)
mods = doc.get("Mods") or []
entries = [m for m in mods
           if str(m.get("Path", "")).replace("\\", "/").rstrip("/").endswith(NAME)]
print("status entries: %d" % len(entries))
for e in entries:
    print("   %r" % e)
check("exactly one status entry", len(entries) == 1, len(entries))
check("the list either gained this mod or already had it",
      len(mods) in (n0, n0 + 1), "%d -> %d" % (n0, len(mods)))
if entries:
    check("it is enabled", entries[0].get("Enabled") is True, entries[0].get("Enabled"))
    check("it sits at priority 1 (the move fix)", entries[0].get("Priority") == 1,
          entries[0].get("Priority"))

# Read the installed copy back: bytes on disk, not merely a same-sized file.
import aoe2mod.dat.parser as P                             # noqa: E402

dat_installed = os.path.join(dst, "resources", "_common", "dat", "empires2_x2_p1.dat")
raw, how = P.load_dat(dat_installed)
_base_how = P.load_dat(G.dat_path(GAME))[1]
# The container matters as much as the contents: the game answers "Decode
# failed" at map start for a raw stream, and `load_dat` accepts both shapes.
check("installed .dat is compressed like the shipped one", how == _base_how,
      "%r (shipped %r)" % (how, _base_how))


def parse_raw(blob):
    p = P.Parser(blob)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p


p = parse_raw(raw)
check("the installed .dat re-parses to a clean EOF", p.r.pos == len(raw),
      "%d of %d" % (p.r.pos, len(raw)))
for ti, when in ((495, "0:00"), (508, "Castle")):
    t = p.stats["techs"][ti]
    eff = p.stats["effects"][t["effect_id"]]
    cmds = [(c["type"], c["a"], c["b"]) if isinstance(c, dict) else tuple(c)[:3]
            for c in (eff.get("commands") or [])]
    check("installed: tech %d (%s) carries the 2550 disable" % (ti, when),
          (2, UNIT, 0) in cmds, cmds[-2:])
    check("installed: tech %d still keeps its original command" % ti,
          len(cmds) >= 2, len(cmds))
check("installed: every villager is 1000 hp",
      sorted({u.get("hit_points") for c in p.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == 83}) == [1000])

tree_installed = os.path.join(dst, "resources", "_common", "dat", "CivTechTrees",
                              "%s.json" % TREE_KEY)
with open(tree_installed, encoding="utf-8") as fh:
    tback = json.load(fh)
check("installed: the Incas tree no longer offers 2550",
      not CT.has(tback, UNIT, CT.UNIT_USE_TYPES),
      CT.node_status(tback, UNIT, CT.UNIT_USE_TYPES))
check("installed: the tree is chain-closed", CT.dangling_links(tback) == [],
      CT.dangling_links(tback))

# The experiment is only meaningful if no other ENABLED mod ships one of the
# three engine paths -- otherwise a screen reading cannot be attributed.
enabled = [m for m in mods if m.get("Enabled")]
print()
print("enabled mods after the install: %d" % len(enabled))
for m in enabled:
    print("   %-60r %s" % ((m.get("Title") or "")[:60], m.get("Path")))

print()
if fails:
    print("V17 INSTALL FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("V17 INSTALL: ALL CHECKS PASSED")

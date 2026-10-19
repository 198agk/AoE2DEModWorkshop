# -*- coding: utf-8 -*-
r"""Install dsh test v16 through the product's own installer and verify it.

Using ``locations.install_mod`` rather than a raw copy is deliberate: it is the
path the product ships, so a bad install here is a product defect and not a
probe bug.
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

from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SRC = os.path.join(HERE, "out_dshtest_v16")
NAME = "dsh test v16 不列颠多出蔷琵侦察兵、印加没有"

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
check("the patched .dat is there",
      os.path.isfile(os.path.join(dst, "resources", "_common", "dat", "empires2_x2_p1.dat")))
check("byte-identical to the build output",
      open(os.path.join(dst, "resources", "_common", "dat", "empires2_x2_p1.dat"), "rb").read()
      == open(os.path.join(SRC, "resources", "_common", "dat", "empires2_x2_p1.dat"), "rb").read())

doc, _, _ = G.read_status_doc(prof)
mods = doc.get("Mods") or []
entries = [m for m in mods if str(m.get("Path", "")).replace("\\", "/").endswith(NAME)
           or str(m.get("Path", "")).replace("\\", "/").endswith("local//" + NAME)]
print("status entries: %d" % len(entries))
for e in entries:
    print("   %r" % e)
check("exactly one status entry", len(entries) == 1, len(entries))
check("the list either gained this mod or already had it",
      len(mods) in (n0, n0 + 1), "%d -> %d" % (n0, len(mods)))
if entries:
    check("it is enabled", entries[0].get("Enabled") is True, entries[0].get("Enabled"))
    check("it sits at priority 1", entries[0].get("Priority") == 1, entries[0].get("Priority"))

# Read the installed copy back through the parser: proof the bytes on disk are
# the two edits, not merely a same-sized file.
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.locate as L                            # noqa: E402

raw, how = P.load_dat(os.path.join(dst, "resources", "_common", "dat",
                                   "empires2_x2_p1.dat"))
# The container matters as much as the contents: the game answers "Decode
# failed" at map start for a raw stream, and `load_dat` accepts both shapes, so
# without this the probe passes on a file that cannot boot.
_base_how = P.load_dat(G.dat_path(GAME))[1]
check("installed .dat is compressed like the shipped one",
      how == _base_how, "%r (shipped %r)" % (how, _base_how))
pr = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
civs, _, _, _ = L.locate(raw, parser=pr)
b = next(x for x in next(c for c in civs if c["name"] == "British")["units"] if x["id"] == 2550)
i = next(x for x in next(c for c in civs if c["name"] == "Incas")["units"] if x["id"] == 2550)
print("installed copy: British button=%d  Incas disabled=%d"
      % (b["train_locations"][0]["button_id"], raw[i["_creatable_start"] + 57]))
check("British reads button 4 back", b["train_locations"][0]["button_id"] == 4)
check("Incas reads disabled 1 back", raw[i["_creatable_start"] + 57] == 1)

print()
if fails:
    print("V16 INSTALL FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("V16 INSTALL: ALL CHECKS PASSED")

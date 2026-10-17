# -*- coding: utf-8 -*-
"""Build the loose-.sld in-game test mod.

Two independent subjects in ONE mod, so a single look at a normal game start
settles both a unit and a building:

  * villager (unit 83)  <- archer (unit 4)   -- villagers look like archers
  * barracks (unit 12)  <- mill   (unit 68)   -- the dark-age barracks looks like a mill

No .dat at all.  If loose .sld files override the shipped art, both change.  If
neither changes, this path does not work (or needs something else), and NOTHING
else in this mod could explain a change.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.intent import reskin as R

TITLE = "dsh test sld v1 村民换步弓手造型 + 黑暗兵营换磨坊造型"
AUTHOR = "aoe2mod"
DESC = "dsh test sld v1｜改动：村民(83)造型←步弓手(4)；黑暗时代兵营(12)造型←磨坊(68)｜无 .dat"

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "out_sld_test_v1")

BUNDLE = [
    {"intent": "unit.sprite", "unit": 83, "donor": 4},
    {"intent": "unit.sprite", "unit": 12, "donor": 68},
]

tk = A.open_toolkit()
tk._ensure()

print("== preview ==")
p = tk.plan_bundle(BUNDLE)
print("  editable       %s" % p.get("editable"))
print("  edit_count     %s" % p.get("edit_count"))
print("  sprite_files   %s" % p.get("sprite_file_count"))
print("  changes_dat    %s" % p.get("changes_dat"))
print("  mod_contains_dat %s" % p.get("mod_contains_dat"))
for nm, val in p.items():
    print("  [%s] %r" % (nm, val))

print()
if os.path.isdir(OUT):
    shutil.rmtree(OUT, ignore_errors=True)

print("== build ==")
man = tk.build_bundle(BUNDLE, OUT, title=TITLE, author=AUTHOR,
                      description=DESC, overwrite=True)
print("  mod_dir        %s" % man.get("mod_dir"))
print("  files          %s" % len(man.get("files") or ()))
print("  edits          %s" % man.get("edits"))
print("  changes_dat    %s" % man.get("changes_dat"))
print("  mod_contains_dat %s" % man.get("mod_contains_dat"))
print("  dat            %s" % man.get("dat"))
print("  sprite_files   %s" % man.get("sprite_files"))
sv = man.get("sprite_verification") or {}
print("  sprite ok      %s" % sv.get("ok"))
print("  checked        %s" % sv.get("checked"))
for k in ("missing_on_disk", "wrong_bytes", "identical_to_target"):
    if sv.get(k):
        print("  !! %s %s" % (k, sv[k]))
print("  proven:")
for s in sv.get("proven") or ():
    print("     - %s" % s)
print("  not_proven:")
for s in sv.get("not_proven") or ():
    print("     - %s" % s)
print()

print("== on disk ==")
tot = 0
n = 0
for dirpath, _dn, fns in os.walk(OUT):
    for fn in fns:
        fp = os.path.join(dirpath, fn)
        rel = os.path.relpath(fp, OUT)
        sz = os.path.getsize(fp)
        tot += sz
        n += 1
        if n <= 30:
            print("  %-70s %10d" % (rel.replace("\\", "/"), sz))
print("  TOTAL %d files  %.2f MB" % (n, tot / 1048576.0))

print()
print("== info.json ==")
with open(os.path.join(OUT, "info.json"), "rb") as fh:
    raw = fh.read()
print("  %s" % raw.decode("utf-8"))
print("  Title bytes: %d / 100" % len(TITLE.encode("utf-8")))

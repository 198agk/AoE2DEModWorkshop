# -*- coding: utf-8 -*-
r"""Install smoke9, replacing every earlier smoke mod.

Per the user's correction (m24660/m24720), a data mod needs neither `mod-status.json`
edits nor a priority: it just has to be in `mods/local/` and be selected before the
match.  So this script only copies the folder, verifies it by sha256, and removes the
previous one.

Safety: refuses to run while the game is running (the game rewrites
`mod-status.json` on exit), and checks the realpath of anything it deletes.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out_smoke9")
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")
DEST = os.path.join(LOCAL, "aoe2mod Smoke9 Dat Grant")

REMOVE = ["aoe2mod Smoke8 Inplace Avail", "aoe2mod Smoke7 Dat Grant",
          "aoe2mod Smoke6 Champi Scout",
          "aoe2mod Bundle VillagerHP plus Britons HandCannon",
          "aoe2mod Smoke2 BuildPanel", "aoe2mod Smoke HP+Units",
          "aoe2mod Smoke5 TreeVsPanel", "aoe2mod Smoke4 Britons Champi Scout",
          "aoe2mod Panel Smoke - Britons Hand Cannoneer",
          "Smoke Test Villager HP", "aoe2mod restart-note check"]


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None
    return "AoE2DE_s.exe" in out


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if game_running():
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")
assert os.path.isdir(SRC), "build it first: _probe/build_smoke9.py"

print()
print("A  remove earlier smoke mods")
for name in REMOVE:
    d = os.path.join(LOCAL, name)
    if not os.path.isdir(d):
        continue
    real = os.path.realpath(d)
    if os.sep + "mods" + os.sep + "local" + os.sep not in real + os.sep:
        print("   SKIP (not under mods/local): %s" % real)
        continue
    shutil.rmtree(real)
    print("   removed %s" % name)

print()
print("B  copy smoke9 in")
if os.path.isdir(DEST):
    real = os.path.realpath(DEST)
    assert os.sep + "mods" + os.sep + "local" + os.sep in real + os.sep, real
    shutil.rmtree(real)
shutil.copytree(SRC, DEST)
print("   -> %s" % DEST)

print()
print("C  verify by sha256")
n = ok = 0
bad = []
for root, _d, fs in os.walk(SRC):
    for f in fs:
        sp = os.path.join(root, f)
        rel = os.path.relpath(sp, SRC)
        dp = os.path.join(DEST, rel)
        n += 1
        if os.path.exists(dp) and sha(sp) == sha(dp):
            ok += 1
        else:
            bad.append(rel)
print("   files verified: %d/%d   problems: %s" % (ok, n, bad or "none"))
assert not bad

print()
print("D  contents")
for root, _d, fs in os.walk(DEST):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("   %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, DEST)))

print()
print("E  local\\ holds")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if os.path.isdir(p):
        cnt = sum(len(f) for _r, _dd, f in os.walk(p))
        print("   %-40s %d file(s)" % (d, cnt))

print()
print("INSTALLED: aoe2mod Smoke9 Dat Grant")
print("  Select it before starting the match, then:")
print("    CONTROL A : give a villager a task -- it must STAY at 1000 hit points")
print("    CONTROL B : CASTLE AGE, British CASTLE -> 长弓兵 still offered")
print("    TEST      : DARK AGE, British BARRACKS -> 蔷琵侦察兵?")

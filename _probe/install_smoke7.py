# -*- coding: utf-8 -*-
r"""Install smoke7 (the `.dat`-only grant) and REMOVE smoke6.

smoke6 was a JSON-layer test; the user's clean run showed that layer does not reach
the build menu, so carrying both would only add a confound.  smoke7 ships ONE `.dat`
containing:

    CONTROL  villager hit points -> 1000                (proven to render)
    TEST     new civ-owned (British) tech with a type-2 command a=2550 b=1
             -> "make the Champi Scout available to the Britons"

Per the user's correction (m24660) about how data mods actually load, this script:
  * does NOT touch `mod-status.json` or priorities -- the user selects the mod before
    starting a match, which is what loads it;
  * only ensures the FOLDER is in `mods/local/`, with every file sha256-verified;
  * refuses to run while the game is running.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out_smoke7")
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")
DEST = os.path.join(LOCAL, "aoe2mod Smoke7 Dat Grant")

REMOVE = ["aoe2mod Smoke6 Champi Scout",
          "aoe2mod Bundle VillagerHP plus Britons HandCannon",
          "aoe2mod Smoke2 BuildPanel",
          "aoe2mod Smoke HP+Units",
          "aoe2mod Smoke5 TreeVsPanel",
          "aoe2mod Smoke4 Britons Champi Scout",
          "aoe2mod Panel Smoke - Britons Hand Cannoneer",
          "Smoke Test Villager HP",
          "aoe2mod restart-note check"]


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
    print("REFUSING: close the game first (it rewrites mod-status.json on exit).")
    sys.exit(1)
print("game running: False")

assert os.path.isdir(SRC), "build it first: _probe/build_smoke7.py"

print()
print("A  remove every earlier smoke mod of ours")
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
print("B  copy smoke7 in")
if os.path.isdir(DEST):
    real = os.path.realpath(DEST)
    assert os.sep + "mods" + os.sep + "local" + os.sep in real + os.sep, real
    shutil.rmtree(real)
shutil.copytree(SRC, DEST)
print("   -> %s" % DEST)

print()
print("C  verify by sha256")
bad = []
n = 0
for root, _d, fs in os.walk(SRC):
    for f in fs:
        sp = os.path.join(root, f)
        rel = os.path.relpath(sp, SRC)
        dp = os.path.join(DEST, rel)
        if not os.path.exists(dp):
            bad.append((rel, "MISSING"))
            continue
        n += 1
        if sha(sp) != sha(dp):
            bad.append((rel, "sha mismatch"))
print("   files verified: %d   problems: %d" % (n, len(bad)))
for rel, why in bad:
    print("      %s: %s" % (rel, why))
assert not bad

print()
print("D  contents")
for root, _d, fs in os.walk(DEST):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("   %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, DEST)))

print()
print("E  local\\ now holds")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if os.path.isdir(p):
        cnt = sum(len(f) for _r, _dd, f in os.walk(p))
        print("   %-40s %d file(s)" % (d, cnt))

print()
print("INSTALLED: aoe2mod Smoke7 Dat Grant")
print("  Select it before starting a match (that is what loads a data mod), then:")
print("    CONTROL  a villager's hit points should read 1000")
print("    TEST     Britons, DARK AGE, Barracks -> is there a 蔷琵侦察兵?")

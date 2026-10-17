# -*- coding: utf-8 -*-
r"""Install smoke6 into the player's local mods folder, WITHOUT touching
`mod-status.json`.

Per the user's instruction (m22351):
    「你不需要调整模组启用问题，你只需要放入对应文件夹就可以了，游戏能自动识别，
      我可以查看是否启用，我已经关闭游戏了」
so this script only copies the folder.  The user enables it in game.

Safety:
  * refuses to run while the game is running (the game rewrites `mod-status.json`
    on exit and may switch the mod off),
  * verifies every copied file by sha256 against the source,
  * removes any earlier smoke mod of ours so only ONE of ours can be active,
  * never writes `mod-status.json`.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out_smoke6")
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")
DEST = os.path.join(LOCAL, "aoe2mod Smoke6 Champi Scout")

# our own earlier smoke mods -- remove them so a stale copy cannot compete
OURS = ["aoe2mod Bundle VillagerHP plus Britons HandCannon",
        "aoe2mod Smoke2 BuildPanel",
        "aoe2mod Smoke HP+Units",
        "aoe2mod Smoke5 TreeVsPanel",
        "Smoke Test Villager HP",
        "aoe2mod Panel Smoke - Britons Hand Cannoneer",
        "aoe2mod Smoke4 Britons Champi Scout",
        "aoe2mod Smoke6 Champi Scout"]


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


running = game_running()
print("game running: %r" % running)
if running:
    print("REFUSING: close the game first.  The game rewrites mod-status.json on "
          "exit and may switch this mod off, which would make the next test "
          "meaningless.")
    sys.exit(1)

assert os.path.isdir(SRC), "build the artifact first: _probe/build_smoke6.py"
assert os.path.isdir(LOCAL), LOCAL

print()
print("A  remove our earlier smoke mods (so only one of ours can be active)")
for name in OURS:
    d = os.path.join(LOCAL, name)
    if not os.path.isdir(d):
        continue
    real = os.path.realpath(d)
    if os.sep + "mods" + os.sep + "local" + os.sep not in real + os.sep:
        print("   SKIP (not under mods/local): %s" % real)
        continue
    if name == "aoe2mod Smoke6 Champi Scout":
        continue
    shutil.rmtree(real)
    print("   removed %s" % name)

print()
print("B  copy the artifact in")
if os.path.isdir(DEST):
    real = os.path.realpath(DEST)
    assert os.sep + "mods" + os.sep + "local" + os.sep in real + os.sep, real
    shutil.rmtree(real)
shutil.copytree(SRC, DEST)
print("   -> %s" % DEST)

print()
print("C  verify every copied file by sha256")
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
        a, b = sha(sp), sha(dp)
        n += 1
        if a != b:
            bad.append((rel, "%s != %s" % (a[:16], b[:16])))
for root, _d, fs in os.walk(DEST):
    for f in fs:
        dp = os.path.join(root, f)
        rel = os.path.relpath(dp, DEST)
        if not os.path.exists(os.path.join(SRC, rel)):
            bad.append((rel, "EXTRA in destination"))
print("   files verified: %d   problems: %d" % (n, len(bad)))
for rel, why in bad:
    print("      %s: %s" % (rel, why))
assert not bad, "copy verification failed"

print()
print("D  listing what is now in local\\")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if os.path.isdir(p):
        cnt = sum(len(f) for _r, _dd, f in os.walk(p))
        print("   %-46s %d file(s)" % (d, cnt))

print()
print("INSTALLED.  Enable 'aoe2mod Smoke6 Champi Scout' in game (优先级 1),")
print("then start a game as BRITONS and check the Barracks in the DARK AGE.")

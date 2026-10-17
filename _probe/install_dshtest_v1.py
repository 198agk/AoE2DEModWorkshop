# -*- coding: utf-8 -*-
r"""smoke9 -> `dsh test v1`, using the naming scheme the user asked for.

The artifact already exists and was verified (`_probe/out_smoke9`): the only change is
the NAME, so the folder becomes

    dsh test v1 - villager HP (27-id family) + Champi Scout for Britons

and the Description records the version, the changes and the in-game reading.  The
`.dat` bytes are reused unchanged (sha256 asserted against the built artifact), so this
is a rename, not a new experiment.

Scheme defined in `_probe/testmod_name.py`.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import testmod_name as TN                                   # noqa: E402

SRC = os.path.join(HERE, "out_smoke9")
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")

CHANGED = "villager HP 1000 (all 27 family ids) + Champi Scout for Britons"
TESTED = "Britons' Barracks, Dark Age"
# Keep the FOLDER short: the game shows the folder name in its mod list, and a long
# one is unreadable there.  The Description carries the full version/change/test
# record, which is where the detail belongs.
TITLE = "%s v1 - villager HP + Britons Champi Scout" % TN.PREFIX
DESC = TN.description_for(
    1, CHANGED, TESTED,
    extra_lines=[
        "CONTROL A: give a villager a task, it must STAY at 1000 hp",
        "CONTROL B: Castle Age, British Castle -> Longbowman still offered",
    ])
DEST = os.path.join(LOCAL, TITLE)


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None
    return "AoE2DE_s.exe" in out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if game_running():
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")
print("title: %s" % TITLE)

src_dat = os.path.join(SRC, "resources", "_common", "dat", "empires2_x2_p1.dat")
assert os.path.exists(src_dat), "build smoke9 first"
src_sha = sha(src_dat)
print("source .dat sha256: %s" % src_sha[:32])

print()
print("A  remove the old-named folder(s)")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if not os.path.isdir(p):
        continue
    if d == TITLE:
        continue
    real = os.path.realpath(p)
    if os.sep + "mods" + os.sep + "local" + os.sep not in real + os.sep:
        print("   SKIP (not under mods/local): %s" % real)
        continue
    if d.startswith("aoe2mod ") or d.startswith("dsh test ") or d == "Smoke Test Villager HP":
        shutil.rmtree(real)
        print("   removed %s" % d)

print()
print("B  write the renamed mod (same .dat bytes)")
os.makedirs(DEST, exist_ok=True)
info = {"Author": "dsh", "CacheStatus": 0, "Description": DESC, "Title": TITLE}
with open(os.path.join(DEST, "info.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
dst_dat_dir = os.path.join(DEST, "resources", "_common", "dat")
os.makedirs(dst_dat_dir, exist_ok=True)
shutil.copy2(src_dat, os.path.join(dst_dat_dir, "empires2_x2_p1.dat"))

print()
print("C  verify")
dst = os.path.join(dst_dat_dir, "empires2_x2_p1.dat")
print("   .dat sha256: %s" % sha(dst)[:32])
print("   IDENTICAL to the verified artifact: %s" % (sha(dst) == src_sha))
assert sha(dst) == src_sha
print("   info.json:")
print(json.dumps(info, ensure_ascii=False, indent=2))

print()
print("D  local\\ now holds")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if os.path.isdir(p):
        cnt = sum(len(f) for _r, _dd, f in os.walk(p))
        print("   %-58s %d file(s)" % (d, cnt))

print()
print("INSTALLED as: %s" % TITLE)
print("  CONTROL A : give a villager a task -- it must STAY at 1000 hp")
print("  CONTROL B : CASTLE AGE, British CASTLE -> 长弓兵 still offered")
print("  TEST      : DARK AGE, British BARRACKS -> 蔷琵侦察兵?")

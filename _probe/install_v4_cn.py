# -*- coding: utf-8 -*-
r"""Rename `dsh test v4` to the Chinese scheme and install it.

The user asked for Chinese (m25601) and the scheme now lives in
`_probe/testmod_name.py`.  The `.dat` and the JSON overrides are already built and
verified (`_probe/out_dshtest_v4`, checked by `_probe/verify_dshtest_v4.py`), so this
only rewrites `info.json` and copies the folder -- the bytes under test are
sha256-checked to be the same ones that were verified.

Per the user's correction (m24660/m24720) a data mod needs neither `mod-status.json`
edits nor a priority; it just has to be in `mods/local/` and be selected before the
match.
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

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")
SRC = os.path.join(HERE, "out_dshtest_v4")

TITLE = TN.name_for(4, "村民血量1000 + 不列颠可造蔷琵侦察兵")
DESC = TN.description_for(
    4,
    "不列颠的 .dat 科技263效果加一条“让蔷琵侦察兵可用”；单位2550的"
    "EnablingResearch指向263；CivTechTrees/BRITONS.json 加该单位行；"
    "建造面板给兵营加该条目。另：村民全族27个id血量改1000（对照A）；"
    "长弓兵的单位侧链接清空（负对照B）",
    "黑暗时代·不列颠兵营里有没有蔷琵侦察兵",
    extra_lines=[
        "对照A：给村民派活后血量应仍为1000",
        "对照B：城堡时代·不列颠城堡 → 长弓兵是否还在（这是机制探针）",
        "v1只给了效果那一半，v4把两半都给了",
    ])
DEST = os.path.join(LOCAL, TITLE)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if "AoE2DE_s.exe" in subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
        capture_output=True, text=True).stdout:
    print("REFUSING: game still running.")
    sys.exit(1)
print("game running: False")
print("title:", TITLE)
print()

src_dat = os.path.join(SRC, "resources", "_common", "dat", "empires2_x2_p1.dat")
before = sha(src_dat)
print("source .dat sha256:", before[:32])

print()
print("A  remove every earlier test mod")
for d in sorted(os.listdir(LOCAL)):
    p = os.path.join(LOCAL, d)
    if not os.path.isdir(p) or d == TITLE:
        continue
    real = os.path.realpath(p)
    if os.sep + "mods" + os.sep + "local" + os.sep not in real + os.sep:
        print("   SKIP (not under mods/local):", real)
        continue
    if d.startswith(TN.PREFIX + " ") or d.startswith("aoe2mod ") or \
            d == "Smoke Test Villager HP":
        shutil.rmtree(real)
        print("   removed", d)

print()
print("B  write the renamed mod (same bytes)")
if os.path.isdir(DEST):
    shutil.rmtree(os.path.realpath(DEST))
shutil.copytree(SRC, DEST)
info = {"Author": "dsh", "CacheStatus": 0, "Description": DESC, "Title": TITLE}
with open(os.path.join(DEST, "info.json"), "w", encoding="utf-8",
          newline="\n") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

print()
print("C  verify every payload file by sha256 against the verified artifact")
n = ok = 0
bad = []
for root, _d, fs in os.walk(SRC):
    for f in fs:
        if f == "info.json":
            continue
        sp = os.path.join(root, f)
        rel = os.path.relpath(sp, SRC)
        dp = os.path.join(DEST, rel)
        n += 1
        if os.path.exists(dp) and sha(sp) == sha(dp):
            ok += 1
        else:
            bad.append(rel)
print("   payload files verified: %d/%d   problems: %s" % (ok, n, bad or "none"))
assert not bad, bad

print()
print("D  contents")
for root, _d, fs in os.walk(DEST):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("   %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, DEST)))
print()
print("   备注：", DESC)

print()
print("INSTALLED:", TITLE)
print("  在开局前选中它，然后用【不列颠】开一局：")
print("    对照A  给村民派活 → 血量是否仍为 1000")
print("    对照B  升到城堡时代 → 【城堡】里长弓兵是否还在")
print("    主测试 黑暗时代 → 【兵营】里有没有【蔷琵侦察兵】")

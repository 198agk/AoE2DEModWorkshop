# -*- coding: utf-8 -*-
"""Scan EVERY scenario-like file on the machine with the structural locator and
report an honest success/failure denominator.

Read-only.  Never writes to the game directories.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_header import locate_deflate  # noqa: E402

ROOTS = [
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\campaign",
]
EXTS = (".aoe2scenario", ".scx")

files = []
for root in ROOTS:
    if not os.path.isdir(root):
        print(f"!! missing root: {root}")
        continue
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(dirpath, n))

print(f"scenario-like files found: {len(files)}")
print("=" * 100)

ok = fail = 0
layout_hist = {}
version_hist = {}
failures = []
for p in sorted(files):
    with open(p, "rb") as f:
        b = f.read()
    h, data, diag = locate_deflate(b)
    ver = diag.get("version")
    version_hist[ver] = version_hist.get(ver, 0) + 1
    if h is not None:
        ok += 1
        layout_hist[h["layout"]] = layout_hist.get(h["layout"], 0) + 1
        print(f"OK   {ver}  off={h['deflate_offset']:>7}  out={len(data):>9}  "
              f"size={len(b):>9}  {h['layout'][:5]}  {os.path.basename(p)}")
    else:
        fail += 1
        failures.append((p, ver, diag))
        print(f"FAIL {ver}  size={len(b):>9}  {os.path.basename(p)}")
        print(f"       reason={diag.get('reason')} attempts={diag.get('attempts')}")

print("=" * 100)
print(f"TOTAL={len(files)}  OK={ok}  FAIL={fail}")
print(f"layout histogram = {layout_hist}")
print(f"version histogram = {dict(sorted((str(k), v) for k, v in version_hist.items()))}")
print(f"failures = {len(failures)}")
for p, ver, diag in failures:
    print(f"   {p}  ver={ver}  {diag.get('reason')}")

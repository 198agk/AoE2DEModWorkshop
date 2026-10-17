# -*- coding: utf-8 -*-
"""Verify the structural locator against the ground-truth brute-force scan.

Ground truth (established earlier by scan_groundtruth.py, brute force over EVERY
offset, kept only streams reaching end-of-stream, then took the longest):
    The Siege.aoe2scenario      1.53   real deflate offset = 83    out = 1453615 B
    default0.aoe2scenario       1.59   real deflate offset = 1183  out = 2525710 B
    0_E3_Scenario.aoe2scenario  1.35   real deflate offset = 85    out =  316584 B
    7V1...aoe2scenario          1.54   (ground truth computed here)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenario_header import locate_deflate  # noqa: E402

CASES = [
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario", 83),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\default0.aoe2scenario", 1183),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario", None),
    (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario", 85),
    (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\*.aoe2scenario", None),
]

ok = 0
bad = 0
for path, expect in CASES:
    if "*" in path:
        continue
    if not os.path.isfile(path):
        print(f"!! missing: {path}")
        continue
    with open(path, "rb") as f:
        b = f.read()
    h, data, diag = locate_deflate(b)
    got = h["deflate_offset"] if h else None
    verdict = "OK " if (got == expect or expect is None) else "MISMATCH"
    if got == expect:
        ok += 1
    else:
        bad += 1
    print(f"{verdict} {os.path.basename(path)}")
    print(f"      version={diag['version']} expect={expect} got={got} "
          f"out={len(data) if data else 0} layout={h['layout'] if h else None}")
    print(f"      header_length_field={h['header_length'] if h else None} "
          f"savable={h['savable'] if h else None} "
          f"player_count={h['player_count'] if h else None} "
          f"creator={h['creator_name'] if h else None!r} "
          f"trigger_count={h['trigger_count'] if h else None}")
    for a in diag["attempts"]:
        print(f"      attempt {a.get('layout')}: {a}")

print(f"\nverified={ok} mismatched={bad}")

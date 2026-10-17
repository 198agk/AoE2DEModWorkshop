# -*- coding: utf-8 -*-
"""Dump the first N bytes of a scenario file, 16 bytes per line, with offsets.
Also show a u32-LE interpretation starting at a given base offset so fields can be
lined up against the AoE2ScenarioParser FileHeader retriever order.
Pure stdlib. Read-only.
"""
import sys

PATHS = [
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\default0.aoe2scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\acam1.aoe2campaign",
]

N = int(sys.argv[1]) if len(sys.argv) > 1 else 192


def hexdump(b, n):
    out = []
    for i in range(0, min(len(b), n), 16):
        chunk = b[i:i + 16]
        hx = " ".join(f"{c:02x}" for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append(f"  {i:6d}  {hx:<47}  {asc}")
    return "\n".join(out)


for p in PATHS:
    try:
        with open(p, "rb") as f:
            b = f.read()
    except OSError as e:
        print(f"!! {p}: {e}")
        continue
    print("=" * 100)
    print(f"FILE {p}")
    print(f"  size={len(b)}  version_tag={b[:4]!r}")
    print(hexdump(b, N))

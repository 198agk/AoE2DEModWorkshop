"""Brute-force disp32 scan: every position in .text whose 4-byte disp32 resolves to target VA.
Also wider region dumps and more literal searches. Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, json, struct, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = _HERE_PATH("_probe", "modes_overlay")
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
text = next(s for s in secs if s["name"] == ".text")
TD = buf[text["rawptr"]:text["rawptr"]+text["rawsize"]]
TV, TR = text["vaddr"], text["rawptr"]

def brute(target_va, label):
    hits = []
    for p in range(len(TD) - 4):
        disp = struct.unpack_from("<i", TD, p)[0]
        if (TV + p + 4 + disp) == target_va:
            hits.append(p)
    print(f"\n### brute disp32 -> {label} VA={target_va:#x}: {len(hits)} raw hits")
    out = []
    for p in hits[:40]:
        s = max(0, p-16); e = min(len(TD), p+12)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in TD[s:e])
        ctx_off = TR + s
        print(f"   textFile={TR+p:#x} VA={TV+p:#x}  bytes[{s}:{e}]={TD[s:e].hex()} |{asc}|")
        out.append(dict(text_file=TR+p, va=TV+p, ctx_hex=TD[s:e].hex()))
    return out

targets = {
    "storage_point_list":      0x325c588,
    "use_modes_path_for_mods": 0x325c5a8,
    "replace":                 0x325c5a0,
    "modes\\Pompeii\\":        0x31f8420,
    "pompeii-strings":         0x31fe1d8,
    "pompeii-strings-utf8":    0x334f510,
    "mod-status.json":         0x329e8d8,
    "info.json":               0x329eef0,
    "subscribed":              0x31f6457,   # approx
}
res = {}
for k, va in targets.items():
    res[k] = brute(va, k)
json.dump(res, open(os.path.join(OUT, "exe_brute_disp.json"), "w"), indent=1)

# --- wider region around filesystem.cpp ---
def wide(lo, hi, step=48, label=""):
    print(f"\n===== WIDE {label} {lo:#x}..{hi:#x} =====")
    for i in range(lo, hi, step):
        chunk = buf[i:i+step]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print(f"  {i:#010x}  {asc}")
wide(0x31f62a0, 0x31f64c0, label="filesystem.cpp full")
wide(0x31f63f0, 0x31f65a0, step=16, label="modes literal hex-narrow")

# --- code ref context at text+0xbcb9e ---
print("\n===== CODE CONTEXT around text+0xbcb40 ===== (LEA 'modes\\Pompeii\\')")
lo = 0xbcb40; hi = 0xbcbe0
for i in range(lo, hi, 16):
    chunk = TD[i:i+16]
    asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
    print(f"  VA {TV+i:#010x}  {chunk.hex()}  |{asc}|")
# disassemble-ish: print the string pointer setup
print("\n=== other literals near 0x31f6420 referenced? scanning 0x31f6400-0x31f64b0 for C-strings ===")
region = buf[0x31f63f0:0x31f64c0]
parts = region.split(b"\x00")
cur = 0x31f63f0
for p in parts:
    if p:
        print(f"  {cur:#x} ({len(p)}B): {p.decode('latin1')!r}")
    cur += len(p) + 1

print("\n=== more literal searches ===")
for n in [b"ContentMode", b"SelectedContentMode", b"gameMode", b"GameMode", b"game_mode",
          b"modeList", b"ModeList", b"datasets", b"Dataset", b"dataset", b".json",
          b"empires2_x2_p1.dat", b"morematerials", b"AOE2DE_Temp", b"UNIQUE_TEMP_FOLDER",
          b"preview", b"subscribed", b"restart", b"RESTART", b"-mode", b"--mode", b"Mode"]:
    print(f"  {n!r}: {buf.count(n)}")

"""Dump string context around every needle hit in AoE2DE_s.exe. Read-only."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, re, json, struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = _HERE_PATH("_probe", "modes_overlay")
EXE  = os.path.join(GAME, "AoE2DE_s.exe")
buf = open(EXE, "rb").read()

secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
def vaname(va):
    for s in secs:
        if s["vaddr"] <= va < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["name"]
    return None

def cstr_at(off):
    """back up to previous NUL, read to next NUL"""
    a = off
    while a > 0 and buf[a-1] != 0:
        a -= 1
    b = off
    while b < len(buf) and buf[b] != 0:
        b += 1
    return a, buf[a:b].decode("latin1", "replace")

def dump(off, before=96, after=320, label=""):
    lo = max(0, off - before); hi = min(len(buf), off + after)
    seg = buf[lo:hi]
    print(f"--- {label} fileOff={off:#x} VA={hex(off+0x2000)} sec={vaname(off+0x2000)} ---")
    s0, cs = cstr_at(off)
    print(f"  enclosing C-string @{s0:#x}: {cs!r}")
    # print as lines of 64 with ascii gutter
    for i in range(lo, hi, 32):
        chunk = buf[i:i+32]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print(f"  {i:#010x}  {asc}")
    print()

targets = [
    (0x325a588, "storage_point_list"),
    (0x325a5a8, "use_modes_path_for_mods"),
    (0x31f6420, "modes\\ (A)"),
    (0x31f6426, "Pompeii (A)"),
    (0x31fc1d8, "pompeii (B)"),
    (0x32c3d16, "pompeii (C)"),
    (0x334d51a, "pompeii (D)"),
    (0x334d54d, "modes\\ (D)"),
    (0x334d553, "Pompeii (D)"),
    (0x334d57d, "modes\\ (D2)"),
    (0x334d583, "Pompeii (D2)"),
    (0x334d5b1, "Pompeii (D3)"),
    (0x35e081f, "modes\\ (E)"),
    (0x35a7edb, "modes (F)"),
    (0x35a85ff, "modes (G)"),
    (0x329c8d8, "mod-status.json"),
    (0x329cef0, "info.json"),
    (0x3320a6e, "ReturnOfRome"),
    (0x33212e0, "Return of Rome"),
    (0x321d580, "Pompeii (H)"),
    (0x321d750, "Pompeii (H2)"),
]
for off, lbl in targets:
    dump(off, label=lbl)

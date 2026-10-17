"""Deeper exe analysis:
 - PDB/compiler/version info from .rsrc / Rich header
 - full dump of the mod-system literal cluster around 0x329c800
 - search for JSON field names likely tied to mode selection
 - scan .rdata for the .data pointer-table region (RVA-based tables)
Read-only.
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

def wide(lo, hi, step=64, label=""):
    print(f"\n===== {label} {lo:#x}..{hi:#x} =====")
    for i in range(lo, hi, step):
        chunk = buf[i:i+step]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print(f"  {i:#010x}  {asc}")

wide(0x329c800, 0x329cd00, label="mod manager literals")
wide(0x329ce80, 0x329d080, label="info.json literals")

# --- all C-strings in .rdata that contain '.json' and their neighbours ---
print("\n===== distinct NUL-terminated strings containing '.json' =====")
seen = set()
cur = 0
for m in re.finditer(rb"[\x20-\x7e]{3,200}", buf):
    s = m.group()
    if b".json" in s:
        if s not in seen:
            seen.add(s)
            print(f"  {m.start():#x}  {s.decode('latin1')}")
print("count:", len(seen))

# --- search Windows version resource for build/version ---
print("\n===== version-ish strings =====")
for pat in [rb"FileVersion", rb"ProductVersion", rb"CompanyName", rb"OriginalFilename",
            rb"FileDescription", rb"ProductName"]:
    for m in re.finditer(re.escape(pat), buf):
        lo = m.start(); hi = lo + 90
        seg = buf[lo:hi]
        # strings in rsrc are UTF-16
        try:
            u = seg.decode("utf-16-le", "replace")
        except Exception:
            u = ""
        print(f"  {pat.decode()} @{lo:#x}: {seg[:60]!r}")
        break
# raw utf-16 scan of rsrc
rsrc = next(s for s in secs if s["name"] == ".rsrc")
seg = buf[rsrc["rawptr"]:rsrc["rawptr"]+rsrc["rawsize"]]
u = seg.decode("utf-16-le", "replace")
vs = re.findall(r"[\x20-\x7e]{6,120}", u)
print("rsrc utf16 strings (first 60):")
for s in vs[:60]:
    print("   ", s)

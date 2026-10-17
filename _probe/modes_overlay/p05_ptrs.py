"""1) Scan .data/.rdata/.text for 64-bit (and 32-bit RVA) pointers equal to target VAs.
   2) Wide hexdump of key regions.
   3) PDB path / RTTI / mode-related searches.
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
EXE  = os.path.join(GAME, "AoE2DE_s.exe")
buf = open(EXE, "rb").read()
secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
IMG = 0x140000000

def file_to_va(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["name"], s["vaddr"] + (off - s["rawptr"])
    return None, None
def secrange(name):
    s = next(x for x in secs if x["name"] == name)
    return s["rawptr"], s["rawptr"] + s["rawsize"], s

# ---- 1) pointer scan ----
targets = {
    "storage_point_list":      0x325c588,
    "use_modes_path_for_mods": 0x325c5a8,
    "modes\\Pompeii\\":        0x31f8420,
    "pompeii-strings":         0x31fe1d8,
    "mod-status.json":         0x329e8d8,
    "info.json":               0x329eef0,
    "replace":                 0x325a598,   # 8 bytes after storage_point_list (approx)
}
# find 'replace' exact
i = buf.find(b"replace\x00", 0x325a588)
print("'replace' literal at fileoff", hex(i), "VA", hex(IMG + i + 0x2000) if i>0 else None)
IMGREF = None

print("\n=== 64-bit absolute pointer scan (.data,.rdata,.text,.pdata) ===")
regions = [("Data",) , ("Rdata",), ("Text",), ("Pdata",)]
name_map = {"Data": ".data", "Rdata": ".rdata", "Text": ".text", "Pdata": ".pdata"}
for lbl, in regions:
    sec = next(x for x in secs if x["name"] == name_map[lbl])
    lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
    print(f"-- section {sec['name']} raw {lo:#x}..{hi:#x} size={hi-lo:#x}")
    for k, va in targets.items():
        pat = struct.pack("<Q", IMG + va)
        hits = []
        st = lo
        while True:
            j = buf.find(pat, st, hi)
            if j < 0: break
            hits.append(j); st = j + 1
        if hits:
            print(f"   {k:26s} abs-ptr hits={len(hits)}: {[hex(h) for h in hits[:10]]}")
    # 32-bit RVA scan (image-relative) for .data
    for k, va in targets.items():
        pat = struct.pack("<I", va)
        hits = []
        st = lo
        while True:
            j = buf.find(pat, st, hi)
            if j < 0: break
            hits.append(j); st = j + 1
        if hits:
            print(f"   {k:26s} rva32   hits={len(hits)}: {[hex(h) for h in hits[:10]]}")

# ---- 2) wide dumps ----
def wide(lo, hi, step=32, label=""):
    print(f"\n===== WIDE {label} {lo:#x}..{hi:#x} =====")
    for i in range(lo, hi, step):
        chunk = buf[i:i+step]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print(f"  {i:#010x}  {asc}")

wide(0x31f6380, 0x31f6620, label="filesystem.cpp region")
wide(0x325a500, 0x325a640, label="storage_point_list region")
wide(0x327de60, 0x327df20, label="modes @327de9f")

# ---- 3) PDB / RTTI / misc ----
print("\n=== PDB / NDEBUG / RTTI ===")
for n in [b".pdb", b"AoE2DE_s.pdb", b".?AV", b".?AU", b"MSVC", b"Return of Rome", b"AOE2DE"]:
    c = buf.count(n)
    print(f"{n!r}: {c}")
pdbs = sorted(set(re.findall(rb"[A-Za-z0-9_\\:\.\-]{4,120}\.pdb", buf)))
print("distinct .pdb strings:", len(pdbs))
for p in pdbs[:40]:
    print("   ", p.decode("latin1"))

# RTTI names containing 'Mode' / 'Storage' / 'Mod' / 'StoragePoint'
rt = re.findall(rb"\.\?A[VU][A-Za-z0-9_@\?\$]{0,80}", buf)
rt = sorted(set(rt))
print("RTTI name count:", len(rt))
keep = [x for x in rt if re.search(rb"[Mm]ode|Storage|[Ss]torage|Mod|FileSystem|Dataset", x)]
print("filtered RTTI:", len(keep))
for x in keep[:200]:
    print("   ", x.decode("latin1"))
json.dump([x.decode("latin1") for x in rt], open(os.path.join(OUT, "exe_rtti.json"), "w"), indent=1)

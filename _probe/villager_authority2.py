"""Two independent tests of the villager task-variant authority.

TEST 1 -- is the exe table referenced?
  No RIP-relative reference was found, but an absolute pointer stored in .data
  would carry a BASE RELOCATION.  The .reloc section names every relocated
  address, so a hit there proves the loader rewrites a pointer to this table.

TEST 2 -- does the dat's own internal naming already enumerate the family?
  The variants found empirically are named VMBAS/VMBLD/VMFOR/... and
  VFBAS/VFBLD/...  A `VM`/`VF` prefix is self-describing and, unlike a stat
  signature, cannot sweep up unrelated units.  If the naming is deliberate the
  product can use it as the rule.
"""
import os
import re
import struct
import sys

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()

pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
opt = pe + 24
sections = []
for i in range(nsec):
    e = opt + optsz + i * 40
    name = data[e:e + 8].rstrip(b"\0").decode("ascii", "replace")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, e + 8)
    sections.append((name, vaddr, vsize, rawptr, rawsize))

sec = {n: (va, vs, rp, rs) for n, va, vs, rp, rs in sections}


def foff_to_rva(fo):
    for name, va, vs, rp, rs in sections:
        if rp <= fo < rp + rs:
            return va + (fo - rp)
    return None


TABLES = [0x032B1DD0, 0x03232E30]
print("=== TEST 1: base relocations that point at the tables ===")
if ".reloc" in sec:
    va, vs, rp, rs = sec[".reloc"]
    print("   .reloc raw 0x%X size 0x%X" % (rp, rs))
    relocs = {}
    o = rp
    while o < rp + rs:
        page_rva, blk = struct.unpack_from("<II", data, o)
        if blk == 0:
            break
        n = (blk - 8) // 2
        for k in range(n):
            (w,) = struct.unpack_from("<H", data, o + 8 + k * 2)
            typ, ofs = w >> 12, w & 0xFFF
            if typ in (3, 10):                       # HIGHLOW / DIR64
                relocs[page_rva + ofs] = typ
        o += blk
    print("   relocation entries: %d" % len(relocs))
    for t in TABLES:
        rva = foff_to_rva(t)
        print("   table rva 0x%08X relocated directly: %s" % (rva, rva in relocs))
        # a pointer to it would live in .data; check if the rva value appears
        pat = struct.pack("<I", rva)
        print("      4-byte rva value occurrences in file: %d" % data.count(pat))

print()
print("=== TEST 2: dat units named VM* / VF* (villager male / female) ===")
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
by = {}
for c in tk._civs:
    for u in c["units"]:
        by.setdefault(u["id"], u)

pat = re.compile(r"^V[MF]")
hits = sorted((i, u) for i, u in by.items() if pat.match(u.get("name") or ""))
print("   units whose internal name starts with VM/VF: %d" % len(hits))
print("   %-6s %-16s %-5s %-6s %-6s %-6s %-7s" % ("id", "name", "type", "class", "hp", "range", "dll"))
for i, u in hits:
    t = u.get("type50") or {}
    print("   %-6d %-16s %-5s %-6s %-6s %-6s %-7s"
          % (i, u.get("name"), u.get("type"), u.get("class"),
             u.get("hit_points"), t.get("max_range"), u.get("_dll_name")))

exe_ids = {56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220,
           222, 259, 293, 354, 579, 581, 590, 592, 1891, 1892, 2333, 2334}
dat_ids = {i for i, _ in hits}
print()
print("   exe table ids : %d" % len(exe_ids))
print("   dat VM/VF ids : %d" % len(dat_ids))
print("   in BOTH       : %s" % sorted(exe_ids & dat_ids))
print("   exe-only      : %s" % sorted(exe_ids - dat_ids))
print("   dat-only      : %s" % sorted(dat_ids - exe_ids))

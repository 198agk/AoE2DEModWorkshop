# -*- coding: utf-8 -*-
"""Is the tree row-field block reached from its HEAD rather than the template?

The .rdata run around 0x3261a18 looks like:

    ... Picture Node Type | civ_id | civ_techs_buildings | civ_techs_units |
    CivTechTrees/%s.json | UnitTech | Age | Unit | ...

A rip-relative scan for the template itself found nothing, and neither did a
QWORD/DWORD pointer scan.  A JSON reader that is handed the block head and
walks it would produce exactly that pattern.  So: find code references to the
HEAD literals as well, and dump the neighbourhood of every hit so the call
site can be judged rather than counted.
"""
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
with open(EXE, "rb") as fh:
    exe = fh.read()

e_lfanew = struct.unpack_from("<I", exe, 0x3C)[0]
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", exe, coff + 2)
optsz, = struct.unpack_from("<H", exe, coff + 16)
opt = coff + 20
imgbase, = struct.unpack_from("<Q", exe, opt + 24)
secoff = opt + optsz
sections = []
for i in range(nsec):
    o = secoff + i * 40
    name = exe[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
    vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", exe, o + 8)
    sections.append((name, vaddr, vsize, raddr, rsize))

tn, tva, tvsz, tra, trs = [s for s in sections if s[0] == ".text"][0]
text = exe[tra:tra + trs]


def off_to_rva(off):
    for name, va, vsz, ra, rs in sections:
        if ra <= off < ra + rs:
            return va + (off - ra)
    return None


def refs_to(rva, limit=40):
    out = []
    for i in range(len(text) - 4):
        disp, = struct.unpack_from("<i", text, i)
        if tva + i + 4 + disp == rva:
            out.append(i)
            if len(out) >= limit:
                break
    return out


NAMES = [
    b"Picture Node Type",
    b"civ_id",
    b"civ_techs_units",
    b"CivTechTrees/%s.json",
    b"Node Status",
    b"ResearchedCompleted",
    b"UnitUpgrade",
    b"storage_point_list",
    b"use_modes_path_for_mods",
    b"futuravailableunits.json",
]

for nm in NAMES:
    offs, start = [], 0
    while True:
        j = exe.find(nm, start)
        if j < 0:
            break
        offs.append(j)
        start = j + 1
    print()
    print("%-28s file hits %d  at %s" % (nm.decode(), len(offs),
                                         [hex(o) for o in offs[:5]]))
    for off in offs:
        rva = off_to_rva(off)
        if rva is None:
            print("      @0x%08x outside sections" % off)
            continue
        hits = refs_to(rva)
        print("      @0x%08x rva 0x%08x  disp32 refs %d %s"
              % (off, rva, len(hits), [hex(tva + h) for h in hits[:6]]))

print()
print("--- neighbourhood of each .text site that references anything above ---")
seen = set()
for nm in NAMES:
    offs, start = [], 0
    while True:
        j = exe.find(nm, start)
        if j < 0:
            break
        offs.append(j)
        start = j + 1
    for off in offs:
        rva = off_to_rva(off)
        if rva is None:
            continue
        for h in refs_to(rva, limit=3):
            if h in seen:
                continue
            seen.add(h)
            lo = max(0, h - 24)
            print()
            print("  site .text+0x%08x  (%s)" % (h, nm.decode()))
            print("      %s" % text[lo:h + 24].hex(" "))

print()
print("counted sites: %d" % len(seen))

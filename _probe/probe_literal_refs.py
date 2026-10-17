# -*- coding: utf-8 -*-
"""Which code references each data-file literal?  Storage point, or direct read?

Motivation
----------
The tree JSON is parsed by the engine (its whole row-field table sits right at
the template string), the path is exactly right, and nested mod files DO
override -- WIDGETUI proves that.  Yet the in-game rewrite had no effect.

The one static signal that separates the remaining hypotheses is WHO references
the literal:

  * if `CivTechTrees/%s.json` is referenced from the same code that references
    `storage_point_list` / `replace` / `use_modes_path_for_mods`, then the tree
    goes through the mod overlay and "scheduling" (read before mods mount) is
    the explanation;
  * if it is referenced only from a bare file-open path with no storage-point
    vocabulary nearby, the tree may be read from the BASE install directly.

So: map each literal to its VA, then find every RIP-relative code reference.
This measures the reference SITES, not the semantics -- no claim beyond that.
"""
import os
import struct
import sys

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"

with open(EXE, "rb") as fh:
    exe = fh.read()

# ---- PE headers ------------------------------------------------------------
e_lfanew = struct.unpack_from("<I", exe, 0x3C)[0]
assert exe[e_lfanew:e_lfanew + 4] == b"PE\0\0", "not a PE"
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", exe, coff + 2)
optsz, = struct.unpack_from("<H", exe, coff + 16)
opt = coff + 20
magic, = struct.unpack_from("<H", exe, opt)
imgbase, = struct.unpack_from("<Q", exe, opt + 24) if magic == 0x20b else \
    struct.unpack_from("<I", exe, opt + 28)[0] + (0,)
secoff = opt + optsz

sections = []
for i in range(nsec):
    o = secoff + i * 40
    name = exe[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
    vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", exe, o + 8)
    chars, = struct.unpack_from("<I", exe, o + 36)
    sections.append((name, vaddr, vsize, raddr, rsize, chars))

print("image base : 0x%x" % imgbase)
print("sections   : %d" % len(sections))
for s in sections:
    print("    %-8s VA 0x%08x  vsize 0x%07x  raw 0x%08x  rsize 0x%07x  ch 0x%08x"
          % (s[0], s[1], s[2], s[3], s[4], s[5]))


def off_to_rva(off):
    for name, va, vsz, ra, rs, ch in sections:
        if ra <= off < ra + rs:
            return va + (off - ra)
    return None


def rva_to_off(rva):
    for name, va, vsz, ra, rs, ch in sections:
        if va <= rva < va + max(vsz, rs):
            return ra + (rva - va)
    return None


TEXT = [s for s in sections if s[0] == ".text"]
if not TEXT:
    sys.exit("no .text")
_tn, _tva, _tvsz, _tra, _trs, _tch = TEXT[0]
text = exe[_tra:_tra + _trs]
print()
print(".text      : VA 0x%08x  raw 0x%08x  size 0x%x" % (_tva, _tra, _trs))


LITERALS = [
    b"CivTechTrees/%s.json",
    b"civTechTrees.json",
    b"futuravailableunits.json",
    b"paphosfutureavailableunits.json",
    b"linkedTechs.json",
    b"linkedUnits.json",
    b"storage_point_list",
    b"use_modes_path_for_mods",
    b"objreplacement.json",
    b"morematerials",
]

# ---- find code references by decoding rip-relative operands ----------------
# Any 4-byte operand at position i in the instruction stream could be a
# disp32.  Rather than a full disassembler, accept every offset where
#   (VA_of_next_field) + signed_disp == target
# and record it.  False positives are possible; REQUIRE the instruction's
# opcode byte(s) to look like a rip-relative form (REX.lea/mov with modrm
# mod=00 r/m=101) so the count stays meaningful.
def find_refs(target_va):
    # NOTE: the operand is relative to the VA of the NEXT instruction, and the
    # VA of a .text byte is imgbase + section VA + offset.  Comparing a raw
    # section RVA here silently yields ZERO references for every literal --
    # which is exactly what the first run printed.
    hits = []
    for i in range(len(text) - 4):
        disp, = struct.unpack_from("<i", text, i)
        va_of_next = imgbase + _tva + i + 4
        if (va_of_next + disp) & 0xFFFFFFFFFFFFFFFF != target_va:
            continue
        # look back for a plausible opcode: optional REX, then 0x8D (lea) or
        # 0x8B (mov), with ModRM r/m == 101 (rip-relative)
        for back in (2, 3):
            j = i - back
            if j < 0:
                continue
            b = text[j]
            if b in (0x8D, 0x8B) and back == 2:
                hits.append((i, "lea/mov rip"))
                break
            if 0x40 <= b <= 0x4F and back == 3 and text[j + 1] in (0x8D, 0x8B):
                hits.append((i, "REX lea/mov rip"))
                break
    return hits


print()
print("=" * 78)
print("code references per literal (rip-relative lea/mov only)")
print("=" * 78)
for lit in LITERALS:
    offs, start = [], 0
    while True:
        i = exe.find(lit, start)
        if i < 0:
            break
        offs.append(i)
        start = i + 1
    print()
    print("%-32s file hits %d" % (lit.decode(), len(offs)))
    for off in offs:
        rva = off_to_rva(off)
        va = None if rva is None else imgbase + rva
        refs = [] if va is None else find_refs(va)
        print("    @0x%08x  rva 0x%08x  va 0x%016x  code refs %d"
              % (off, rva or 0, va or 0, len(refs)))
        for i, kind in refs[:12]:
            print("        ref at .text+0x%08x  (rva 0x%08x)  %s"
                  % (i, _tva + i, kind))
        if len(refs) > 12:
            print("        ... +%d more" % (len(refs) - 12))

print()
print("LITERAL REFERENCE MAP: counts above only say which code touches a")
print("string.  Compare the clusters -- they are the evidence.")

# -*- coding: utf-8 -*-
"""Diagnose why the rip-relative scan found nothing.

Two candidate reasons, and they mean different things:
  A. my decoder is wrong (no raw disp32 lands on the target either);
  B. the engine does not use rip-relative loads for these strings -- it uses
     an absolute pointer table (8-byte VA) or a pointer stored in .data.
Separating them matters: B would be a finding, A is just my bug.
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
magic, = struct.unpack_from("<H", exe, opt)
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
print("imgbase 0x%x  .text va 0x%x raw 0x%x size 0x%x" % (imgbase, tva, tra, trs))

TARGETS = {
    "CivTechTrees/%s.json": 0x03261a18,
    "futuravailableunits.json": 0x0325a5d8,
    "storage_point_list": 0x0325a588,
    "linkedTechs.json": 0x032986b0,
}
# convert file offset of the string to RVA via section table
def off_to_rva(off):
    for name, va, vsz, ra, rs in sections:
        if ra <= off < ra + rs:
            return va + (off - ra)
    return None

for lit, off in TARGETS.items():
    rva = off_to_rva(off)
    va = imgbase + rva
    print()
    print("%-28s fileoff 0x%x  rva 0x%x  va 0x%016x" % (lit, off, rva, va))

    # --- A. raw disp32 anywhere in .text resolving to this RVA ---------------
    raw = 0
    samples = []
    for i in range(len(text) - 4):
        disp, = struct.unpack_from("<i", text, i)
        if tva + i + 4 + disp == rva:
            raw += 1
            if len(samples) < 6:
                samples.append((i, text[max(0, i - 4):i + 4].hex()))
    print("    A) raw disp32 hits (no opcode filter) : %d" % raw)
    for i, h in samples:
        print("        .text+0x%08x  bytes %s" % (i, h))

    # --- B. absolute 8-byte VA pointers anywhere in the image ----------------
    pat = struct.pack("<Q", va)
    hits, start = [], 0
    while True:
        j = exe.find(pat, start)
        if j < 0:
            break
        hits.append(j)
        start = j + 1
    print("    B) absolute QWORD pointers to it     : %d" % len(hits))
    for j in hits[:8]:
        print("        @0x%08x  rva 0x%x" % (j, off_to_rva(j) or 0))

    # --- C. 4-byte RVA (32-bit) pointers ------------------------------------
    pat4 = struct.pack("<I", rva)
    hits4, start = [], 0
    while True:
        j = exe.find(pat4, start)
        if j < 0:
            break
        hits4.append(j)
        start = j + 1
    print("    C) absolute DWORD rva pointers        : %d" % len(hits4))

print()
print("If A is 0 but B/C are large, these strings are reached through a")
print("pointer table, not by a rip-relative load -- which is a different")
print("kind of evidence and must not be reported as 'unreferenced'.")

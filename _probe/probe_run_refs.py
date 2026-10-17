# -*- coding: utf-8 -*-
"""Does ANY code load an address inside the tree row-field string block?

Why this shape of test
----------------------
Scanning for a reference to each literal individually came back empty, but the
scan did find one clean `48 8d 05` (lea rip) for `ResearchedCompleted`.  So the
decoder works and the negative is real FOR THOSE EXACT ADDRESSES.  The 18 row
field names sit in one contiguous run; a table-driven reader would load the
run's head once and index into it, which would explain the negative.

So: find every disp32 in .text that resolves anywhere inside the block, then
report the block bounds and the sites.  This distinguishes

    "nothing points at these strings"   (a finding, if true)
from
    "the decoder only catches exact-hit loads"  (my bug)

and it does not require a full disassembler.
"""
import re
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


# --- locate the contiguous printable run that holds the row field names -----
anchor = exe.find(b"Picture Node Type")
print("anchor 'Picture Node Type' at 0x%x" % anchor)
lo = anchor
while lo > 0 and 0x20 <= exe[lo - 1] < 0x7f:
    lo -= 1
hi = anchor
while hi < len(exe) and (0x20 <= exe[hi] < 0x7f):
    hi += 1
run = exe[lo:hi]
print("printable run   0x%x .. 0x%x  (%d bytes)" % (lo, hi, len(run)))
print("run text: %r" % run[:400])

run_rva_lo = off_to_rva(lo)
run_rva_hi = off_to_rva(hi - 1)
run_va_lo = imgbase + run_rva_lo
run_va_hi = imgbase + run_rva_hi
print("run VA          0x%016x .. 0x%016x" % (run_va_lo, run_va_hi))

# --- every disp32 in .text resolving into that range ------------------------
print()
print("=" * 78)
print("disp32 operands in .text that land INSIDE the row-field run")
print("=" * 78)
hits = []
for i in range(len(text) - 4):
    disp, = struct.unpack_from("<i", text, i)
    # operand is relative to the next instruction
    target = tva + i + 4 + disp
    if run_rva_lo <= target <= run_rva_hi:
        hits.append((i, target))

print("sites: %d" % len(hits))
for i, target in hits[:40]:
    back = text[max(0, i - 8):i + 6]
    print("    .text+0x%08x -> rva 0x%08x  off-in-run 0x%x  bytes %s"
          % (i, target, target - run_rva_lo, back.hex(" ")))

# also: absolute QWORD pointers into the run
print()
pat_lo = struct.pack("<Q", run_va_lo)
cnt = 0
start = 0
while True:
    j = exe.find(pat_lo, start)
    if j < 0:
        break
    cnt += 1
    start = j + 1
print("absolute QWORD pointers to the run head: %d" % cnt)

# widen: any QWORD in .data/.rdata pointing into the run
for secname in (".rdata", ".data"):
    sn, sva, svsz, sra, srs = [s for s in sections if s[0] == secname][0]
    blob = exe[sra:sra + srs]
    found = []
    for i in range(0, len(blob) - 8, 8):
        v, = struct.unpack_from("<Q", blob, i)
        if run_va_lo <= v <= run_va_hi:
            found.append((i, v))
    print("%s QWORDs pointing into the run: %d %s"
          % (secname, len(found),
             [(hex(sra + i), hex(v - run_va_lo)) for i, v in found[:8]]))

print()
print("A positive result identifies the loader; a clean negative across exact")
print("addresses AND the enclosing range means the accessor is not a direct")
print("address load, and 'unreferenced' still must not be claimed.")

# -*- coding: utf-8 -*-
"""Are the row-field strings reached through an ARRAY OF POINTERS?

The disp32 scan found no code reference to the tree row-field names, the
template, or most other literals -- while `ResearchedCompleted` had exactly
one plausible `48 8d 05` lea.  A parser that walks a name table would produce
exactly that pattern: the field names are only ever compared against keys
obtained from a table, so no single string is loaded by address.

Test: look for runs of consecutive QWORD (and DWORD) pointers inside .rdata /
.data that point at these strings.  If a contiguous pointer array exists, the
"no references" result is an artifact of my decoder and must NOT be reported
as evidence that the file is unreferenced.
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

BYSEC = {s[0]: s for s in sections}


def off_to_rva(off):
    for name, va, vsz, ra, rs in sections:
        if ra <= off < ra + rs:
            return va + (off - ra)
    return None


ROW_FIELDS = [
    b"Picture Node Type", b"Link ID", b"Link Node Type", b"Name String ID",
    b"Node ID", b"Node Status", b"Node Type", b"Picture Index",
    b"Prerequisite IDs", b"Prerequisite Types", b"Trigger Tech ID",
    b"Use Type", b"Draw Node Type", b"Age ID", b"Building ID",
    b"Help String ID", b"Building in new column", b"Building upgraded from ID",
]

addrs = {}
for nm in ROW_FIELDS:
    j = exe.find(nm)
    if j < 0:
        print("MISSING literal: %s" % nm.decode())
        continue
    rva = off_to_rva(j)
    addrs[nm] = (imgbase + rva, rva)

print("resolved %d of %d row-field literals" % (len(addrs), len(ROW_FIELDS)))
print()
print("each literal's VA:")
for nm, (va, rva) in addrs.items():
    print("    %-28s va 0x%016x" % (nm.decode(), va))

print()
print("=" * 78)
print("contiguous pointer runs containing at least 3 of these literals")
print("=" * 78)
va_set = {va for va, _ in addrs.values()}

for secname in (".rdata", ".data", "_RDATA"):
    if secname not in BYSEC:
        continue
    sn, sva, svsz, sra, srs = BYSEC[secname]
    blob = exe[sra:sra + srs]
    sec_base_va = imgbase + sva
    found = []
    for width, fmt, size in ((8, "<Q", 8), (4, "<I", 4)):
        step = width
        i = 0
        run = []
        while i <= len(blob) - width:
            v, = struct.unpack_from(fmt, blob, i)
            if v in va_set:
                run.append((i, v))
                i += step
                continue
            if len(run) >= 3:
                found.append((width, run))
            run = []
            i += 1
        if len(run) >= 3:
            found.append((width, run))
    print()
    print("%s: %d run(s) of >=3 consecutive pointers" % (secname, len(found)))
    for width, run in found[:6]:
        names = []
        for off, v in run:
            nm = [k for k, (a, r) in addrs.items() if a == v]
            names.append(nm[0].decode() if nm else "?")
        print("    width %d  at %s+0x%x  count %d"
              % (width, secname, run[0][0], len(run)))
        for k, nm in enumerate(names[:20]):
            print("        [%2d] %s" % (k, nm))

print()
print("If no run exists, these strings are hashed or the accessor is indirect")
print("in a way this scan cannot see -- do NOT read '0 references' as")
print("'the engine ignores this file'.")

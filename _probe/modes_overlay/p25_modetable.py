"""p25: the pointer TABLE that references the 'Pompeii' content-mode string, plus the .data
targets of the modes-path function. Final structural evidence.
Read-only -> p25_out.txt
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p25_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf); IB = 0x140000000
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
sects = []
so = e + 24 + optsz
for i in range(nsec):
    o = so + i*40
    nm = buf[o:o+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, o+8)
    sects.append((nm, va, vs, ra, rs))
def r2o(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va); return o if 0 <= o < N else None
    return None
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"
def cstr(rva, ml=200):
    o = r2o(rva)
    if o is None: return None
    q = buf.find(b"\0", o, o+ml)
    return buf[o:q].decode("latin-1") if q > 0 else None

P("#"*100)
P("# A) the table at rva 0x321efe0 (contains an abs VA of the 'Pompeii' string)")
P("   strings near rva 0x321ee80..0x321ef40:")
o = r2o(0x321ee80); seg = buf[o:o+0xc0]
p = 0
while p < len(seg):
    q = seg.find(b"\0", p)
    if q < 0: break
    if q > p:
        s = seg[p:q]
        if len(s) >= 2 and all(32 <= b < 127 or b == 9 for b in s):
            P(f"     {0x321ee80+p:#010x} {s.decode('latin-1')!r}")
    p = q + 1
P("")
P("   the table itself, rva 0x321ef60..0x321f080 as 8-byte values:")
o = r2o(0x321ef60); seg = buf[o:0x321f080-0x321ef60+o]
p = 0
while p <= len(seg) - 8:
    v = struct.unpack_from("<Q", seg, p)[0]
    rva = 0x321ef60 + p
    tag = ""
    if IB <= v < IB + 0x6000000:
        t = v - IB
        s = cstr(t, 48)
        tag = f" -> rva {t:#x} [{sec(t)}]" + (f" {s!r}" if s else "")
    P(f"     {rva:#010x}  {v:#018x}{tag}")
    p += 8

P("")
P("#"*100)
P("# B) .data targets of func 0xBDB50, as strings/structs")
for a in (0x428bb30, 0x427fdf0, 0x427fdf8, 0x427fe00):
    o = r2o(a)
    P(f"   rva {a:#x} [{sec(a)}] 96 bytes: {buf[o:o+96].hex()}")
    P(f"        as ascii: {buf[o:o+96]!r}")
    for k in range(0, 64, 8):
        v = struct.unpack_from("<Q", buf, o+k)[0]
        P(f"        +{k:2d} {v:#018x}")
    P("")

P("")
P("#"*100)
P("# C) enumerate ALL absolute-VA pointers to any of the 5 content-mode name strings")
names = {"Pompeii": 0x31f7480, "Philadelphia": 0x31f7488, "Paphos": 0x31f7498,
         "Paris": 0x31f74a0, "Providence": 0x31f74a8}
for nm, rva in names.items():
    pat = struct.pack("<Q", IB + rva)
    hs = []
    s = 0
    while True:
        i = buf.find(pat, s)
        if i < 0: break
        hs.append(i); s = i + 1
    P(f"   {nm!r} rva {rva:#x}: {len(hs)} abs-VA ptr(s) at fileoff {[hex(x) for x in hs]}")
    for fo in hs:
        P(f"       table rva {o2r(fo):#x} [{sec(o2r(fo))}]")

P("")
P("#"*100)
P("# D) the content-mode name block in full, as strings AND as the 0x321efe0-style table")
P("   strings rva 0x31f7420..0x31f7560:")
o = r2o(0x31f7420); seg = buf[o:0x31f7560-0x31f7420+o]
p = 0
while p < len(seg):
    q = seg.find(b"\0", p)
    if q < 0: break
    if q > p:
        s = seg[p:q]
        if len(s) >= 2 and all(32 <= b < 127 or b == 9 for b in s):
            P(f"     {0x31f7420+p:#010x} {s.decode('latin-1')!r}")
    p = q + 1
P("")
P("   as 8-byte values:")
p = 0
while p <= len(seg) - 8:
    v = struct.unpack_from("<Q", seg, p)[0]
    rva = 0x31f7420 + p
    tag = ""
    if IB <= v < IB + 0x6000000:
        t = v - IB
        s = cstr(t, 40)
        tag = f" -> rva {t:#x} [{sec(t)}]" + (f" {s!r}" if s else "")
    P(f"     {rva:#010x}  {v:#018x}{tag}")
    p += 8
F.close()
print("wrote p25_out.txt")

"""p21: (a) locate '%s.json' and its code refs; (b) print full neighbourhoods of every
`modes`-bearing literal; (c) look for any '%s' string adjacent to a mode name; (d) check the
data object 0x428bb30 / 0x427fe00 referenced by func 0xBDB50; (e) list the PathSpec cluster fully.
Read-only -> p21_out.txt
"""
import os, struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p21_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf)
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
def cstr(rva, ml=400):
    o = r2o(rva)
    if o is None: return None
    q = buf.find(b"\0", o, o+ml)
    return buf[o:q if q > 0 else o+ml].decode("latin-1")
def rd(rva, n):
    o = r2o(rva); return buf[o:o+n] if o is not None else b""

P("#"*100)
P("# A) locate every ')s.json' style candidate: literal '%s.json' + context + code refs")
def allocc(pat):
    out=[]; s=0
    while True:
        i=buf.find(pat,s)
        if i<0: break
        out.append(i); s=i+1
    return out
for pat in [b"%s.json", b"modes", b"Pompeii.json"]:
    occ = allocc(pat)
    P(f"  {pat!r}: {len(occ)} occurrence(s) at fileoffs {[hex(x) for x in occ]}")
    for i in occ:
        rv = o2r(i)
        P(f"     fo {i:#x} rva {rv if rv else 0:#x} [{sec(rv) if rv else '?'}] ctx {buf[max(0,i-60):i+60]!r}")

P("")
P("#"*100)
P("# B) code refs (disp32 whose target == rva of each 'modes'/'%s.json' literal)")
targets = {}
for pat in [b"%s.json", b"modes\\Pompeii\\"]:
    s=0
    while True:
        i=buf.find(pat,s)
        if i<0: break
        targets[o2r(i)] = pat.decode()
        s=i+1
tsec = next(x for x in sects if x[0]==".text")
traw, trs = tsec[3], tsec[4]
hits = {k: [] for k in targets}
for p in range(traw, traw+trs-4):
    disp = struct.unpack_from("<i", buf, p)[0]
    rv = o2r(p)
    if rv is None: continue
    tgt = rv+4+disp
    if tgt in targets:
        hits[tgt].append((rv, buf[p-3:p].hex()))
for tgt, name in targets.items():
    P(f"  {name!r} rva {tgt:#x}: {len(hits[tgt])} rip ref(s)")
    for rv, prev in hits[tgt][:20]:
        P(f"      site rva {rv:#x} prev3 {prev}")
    # pdata function owning it
    pdo = next(x for x in sects if x[0]==".pdata")
    pd_raw, pd_rs = pdo[3], pdo[4]
    for rv, prev in hits[tgt][:6]:
        owner=None
        for i in range(pd_rs//12):
            st,en,ui = struct.unpack_from("<III", buf, pd_raw+i*12)
            if st <= rv < en: owner=(st,en); break
        P(f"          owner func {owner[0]:#x}-{owner[1]:#x}" if owner else "          owner func <none>")

P("")
P("#"*100)
P("# C) full neighbourhood of the LIVE modes\\Pompeii\\ literal (0x31f8420): ±0x140 printable strings")
o = r2o(0x31f8420) - 0x140
seg = buf[o:o+0x320]
p=0
while p < len(seg):
    q = seg.find(b"\0", p)
    if q<0: break
    if q>p:
        s = seg[p:q]
        if len(s)>=2 and all(32<=b<127 or b==9 for b in s):
            P(f"   {0x31f8420-0x140+p:#010x} {s.decode('latin-1')!r}")
    p=q+1

P("")
P("#"*100)
P("# D) func 0xBDB50 data targets 0x428bb30 (was 'EZt') and 0x427fe00, 0x427fdf0/8")
for a in (0x428bb30, 0x427fdf0, 0x427fdf8, 0x427fe00):
    P(f"  rva {a:#x} [{sec(a)}] bytes {rd(a,48).hex()}")
    # interpret as possible pointer / struct
    for k in range(0, 32, 8):
        v = struct.unpack_from("<Q", buf, r2o(a)+k)[0]
        P(f"      +{k:2d} u64 {v:#018x}")
P("")
P("  global at 0x428bb30 - 0x3676dc8 (the empty std::string) check:")
for a in (0x3676dc8, 0x3059a30, 0x800fb0):
    P(f"  rva {a:#x} [{sec(a)}] bytes {rd(a,32).hex()}  str {cstr(a,40)!r}")

P("")
P("#"*100)
P("# E) PathSpec / storagepoint cluster full dump 0x31faf00-0x31fb400")
o = r2o(0x31faf00); seg = buf[o:o+0x500]
p=0
while p < len(seg):
    q = seg.find(b"\0", p)
    if q<0: break
    if q>p:
        s = seg[p:q]
        if len(s)>=2 and all(32<=b<127 for b in s):
            P(f"   {0x31faf00+p:#010x} {s.decode('latin-1')!r}")
    p=q+1
F.close()
print("wrote p21_out.txt")

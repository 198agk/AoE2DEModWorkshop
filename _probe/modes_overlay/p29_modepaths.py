"""p29: decode the function(s) that reference ALL FIVE content-mode names at a regular stride
(sites 0x27e89d, 0x27e9bf, 0x27ea3c, 0x27eb39, 0x27ebb5). If the engine ever forms
"modes\\<Name>\\" or "<Name>.json" at runtime, it happens here.
For each site: owning .pdata function, full string-ref list, call targets, and the disasm window.
Also dump the `%s%s` / `.json` template clusters and test a `%s%s` + `.json` name build.
Read-only -> p29_out.txt
"""
import os, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p29_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read(); N = len(buf); IB = 0x140000000
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
so = e + 24 + optsz
sects = []
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
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"
_, tva, tvs, tra, trs = [s for s in sects if s[0] == ".text"][0]
text = buf[tra:tra+trs]

# .pdata function map
pdr = [s for s in sects if s[0] == ".pdata"][0]
_, pva, pvs, pra, prs = pdr
funcs = []
n = pvs // 12
for i in range(n):
    st, en = struct.unpack_from("<II", buf, pra + i*12)
    funcs.append((st, en))
funcs.sort()
def owner(site):
    lo, hi = 0, len(funcs)
    while lo < hi:
        mid = (lo + hi)//2
        if funcs[mid][0] <= site: lo = mid + 1
        else: hi = mid
    if lo == 0: return None
    st, en = funcs[lo-1]
    return (st, en) if st <= site < en else None

def strict_refs(target):
    out = []
    for p in range(1, len(text) - 4):
        d = struct.unpack_from("<i", text, p)[0]
        if (tva + p + 4) + d == target and (text[p-1] & 0xC7) == 0x05:
            out.append(tva + p)
    return out
def cstr(rva, ml=120):
    o = r2o(rva)
    if o is None: return None
    q = buf.find(b"\0", o, o+ml)
    return buf[o:q].decode("latin-1") if q > 0 else None
def strrefs_in(lo, hi):
    """all RIP-relative refs from inside [lo,hi) to a printable string in .rdata"""
    res = []
    for p in range(max(1, lo - tva), min(len(text)-4, hi - tva)):
        d = struct.unpack_from("<i", text, p)[0]
        t = (tva + p + 4) + d
        if sec(t) in (".rdata", ".rodata", ".data") and (text[p-1] & 0xC7) == 0x05:
            s = cstr(t, 90)
            if s and len(s) >= 3 and all(32 <= ord(c) < 127 for c in s):
                res.append((tva + p, t, s))
    return res
def calls_in(lo, hi):
    res = []
    for p in range(1, min(len(text)-4, hi - tva)):
        if text[p-1] == 0xE8 and p - 1 >= lo - tva:
            d = struct.unpack_from("<i", text, p)[0]
            res.append((tva + p - 1, (tva + p + 4) + d))
    return res

P("#"*100)
P("# A) the five content-mode-name reference sites and their owning functions")
sites = {"Pompeii": 0x27e89d, "Philadelphia": 0x27e9bf, "Paphos": 0x27ea3c,
         "Paris": 0x27eb39, "Providence": 0x27ebb5}
owners = {}
for nm, site in sites.items():
    ow = owner(site)
    P(f"   {nm!r:14s} site rva {site:#x} owner func {ow[0]:#x}-{ow[1]:#x} ({ow[1]-ow[0]} B)")
    owners.setdefault(ow, []).append(nm)
P("")
for ow, nms in sorted(owners.items()):
    lo, hi = ow
    P(f"   === FUNCTION {lo:#x}-{hi:#x} ({hi-lo} B) references {nms}")
    P(f"       strings referenced:")
    for s, t, txt in strrefs_in(lo, hi):
        P(f"         site {s:#x} -> {t:#x} {txt!r}")
    P(f"       calls:")
    for s, t in calls_in(lo, hi):
        P(f"         site {s:#x} -> {t:#x} [{sec(t)}]")
    P("")

P("#"*100)
P("# B) is there a per-mode PATH construction? test every template-ish literal near the")
P("   content-mode names and their strict refs")
for pat in (b"%s%s", b"%s%s%s", b"%s\\%s", b"%s.json", b".json", b"*.json",
            b"modes\\%s", b"%s\\modes", b"%s.json\\0"):
    c = buf.count(pat)
    P(f"   {pat!r}: {c} byte occurrence(s)")

P("")
P("   `%s%s` string starts and their strict refs (looking for name+suffix concatenation):")
p = 0; rows = []
while True:
    i = buf.find(b"%s%s\0", p)
    if i < 0: break
    # find string start
    a = i
    while a > 0 and buf[a-1] != 0: a -= 1
    rows.append(a); p = i + 1
for a in rows[:40]:
    rva = None
    for nm, va, vs, ra, rs in sects:
        if ra <= a < ra + rs: rva = va + (a - ra); break
    if rva is None: continue
    rr = strict_refs(rva)
    s = cstr(rva, 80)
    P(f"     rva {rva:#x} {s!r} strict_refs={len(rr)} {[hex(x) for x in rr[:5]]}")

P("")
P("#"*100)
P("# C) the `.json` literal at rva 0x3202418 and `*.json` at 0x321c498 neighbourhoods")
for rva, label in ((0x3202418, "'.json'"), (0x321c498, "'*.json'")):
    o = r2o(rva)
    P(f"   {label} rva {rva:#x}:")
    a = o - 0x80; b2 = o + 0x80
    seg = buf[a:b2]
    q = 0
    while q < len(seg):
        z = seg.find(b"\0", q)
        if z < 0: break
        if z > q:
            s = seg[q:z]
            if len(s) >= 3 and all(32 <= x < 127 for x in s):
                P(f"       {rva-0x80+q:#x} {s.decode('latin-1')!r}")
        q = z + 1
    P("")

P("#"*100)
P("# D) the modes\\Pompeii\\ initializer function 0xbdb50 - who calls the callee 0x2d6bffc?")
P("   (0x2d6bffc appeared as a callee in every per-DLC content-mode function too)")
for tgt in (0x2d6bffc, 0x2d6ba78, 0x2d6bd04):
    o = r2o(tgt)
    P(f"   func {tgt:#x}: {buf[o:o+40].hex()}")
    # find callers
    callers = []
    for p in range(1, len(text)-4):
        if text[p-1] == 0xE8:
            d = struct.unpack_from("<i", text, p)[0]
            if (tva+p+4)+d == tgt: callers.append(tva+p-1)
    P(f"       direct E8 callers: {len(callers)}; sample: {[hex(x) for x in callers[:12]]}")
F.close()
print("wrote p29_out.txt")

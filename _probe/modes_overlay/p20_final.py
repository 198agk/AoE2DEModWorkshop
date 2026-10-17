"""p20: close the remaining gaps.
 (a) exact verbatim Pompeii.json (for the report)
 (b) RTTI names mentioning Storage / GameVariant / ContentMode / Mod (from exe_rtti.json + fresh scan)
 (c) does any literal like '%s.json' / '%s\\\\%s.json' exist?  -> how is Pompeii.json found?
 (d) the mode-name -> path mapping functions (0xbc330-0xbe480): decode LEAs & short strings
 (e) storagepoint.cpp neighbours: the storage point TYPE enum strings in order
Read-only. Writes p20_out.txt.
"""
import os, struct, json, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p20_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf)
e_lfanew = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e_lfanew+6)[0]
optsz = struct.unpack_from("<H", buf, e_lfanew+20)[0]
sects = []
so = e_lfanew + 24 + optsz
for i in range(nsec):
    off = so + i*40
    name = buf[off:off+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, off+8)
    sects.append((name, va, vs, ra, rs))
def rva2off(rva):
    for name, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va)
            return o if 0 <= o < N else None
    return None
def off2rva(off):
    for name, va, vs, ra, rs in sects:
        if ra <= off < ra + rs: return va + (off - ra)
    return None
def sec_of(rva):
    for name, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return name
    return "?"
def cstr(rva, maxlen=300):
    o = rva2off(rva)
    if o is None: return None
    e = buf.find(b"\0", o, o+maxlen)
    if e < 0: return None
    return buf[o:e].decode("latin-1")
def rd(rva, n):
    o = rva2off(rva)
    return buf[o:o+n] if o is not None else b""

P("#"*100)
P("# A) verbatim modes/Pompeii/Pompeii.json")
raw = open(os.path.join(GAME, "modes", "Pompeii", "Pompeii.json"), "rb").read()
txt = raw.decode("utf-8-sig")
P(txt)
obj = json.loads(txt)
P("")
P("entries: idx | type | has_replace | replace | path | extra keys")
for i, e in enumerate(obj["storage_point_list"]):
    extra = [k for k in e if k not in ("type", "path", "replace")]
    P(f"  [{i:2d}] {e.get('type','?'):22s} replace={str(e.get('replace')):5s} path={e.get('path','')!r:42s} extra={extra}")

P("")
P("#"*100)
P("# B) RTTI .?AV/.?AU names filtered")
pat = re.compile(rb"\.\?A[VU][A-Za-z0-9_@?$<>,`'\-\.]{2,200}")
names = set()
for m in pat.finditer(buf):
    try:
        names.add(m.group().decode("ascii"))
    except UnicodeDecodeError:
        pass
P(f"  {len(names)} distinct RTTI names; filtered:")
for n in sorted(names):
    low = n.lower()
    if any(k in low for k in ["storagepoint", "storage", "gamevariant", "contentmode",
                              "modpackage", "modstatus", "modmanager", "moddisplay",
                              "filesystem", "vfs", "mount", "dataset", "extensionmanager"]):
        P(f"    {n}")

P("")
P("#"*100)
P("# C) format-string literals that could build '<name>.json'")
cands = [b"%s.json", b"%s\\%s.json", b"%s/%s.json", b"%s%s.json", b".json",
         b"%s.json\\0", b"%s_%s.json", b"modes", b"modes\\", b"\\modes", b"modes/"]
for c in cands:
    tot = buf.count(c)
    P(f"  {c!r}: {tot} raw byte-occurrence(s)")
# list every NUL-terminated string ENDING in '.json' that contains a % or \
P("")
P("  --- NUL-terminated strings containing '.json' AND ('%' or '\\\\') ---")
o = 0
seen = set()
while True:
    i = buf.find(b".json", o)
    if i < 0: break
    o = i + 1
    s = i
    while s > 0 and buf[s-1] >= 32 and buf[s-1] < 127: s -= 1
    e = i + 5
    while e < N and buf[e] >= 32 and buf[e] < 127: e += 1
    if buf[e:e+1] == b"\0":
        st = buf[s:e].decode("latin-1")
        if ("%" in st or "\\" in st) and st not in seen:
            seen.add(st)
            rv = off2rva(s)
            P(f"    {rv:#010x} {st!r}")

P("")
P("#"*100)
P("# D) function family 0xbc330-0xbe480: LEAs to short strings + call graph")
TEXT = next(s for s in sects if s[0] == ".text")
pdo = next(s for s in sects if s[0] == ".pdata")
pd_rs, pd_raw = pdo[4], pdo[3]
funcs = []
for i in range(pd_rs // 12):
    st, en, ui = struct.unpack_from("<III", buf, pd_raw + i*12)
    if 0xbc300 <= st <= 0xbe500:
        funcs.append((st, en))
funcs.sort()
for st, en in funcs:
    o0, o1 = rva2off(st), rva2off(en-1)
    if o0 is None or o1 is None: continue
    body = buf[o0:o1+1]
    strs = []
    calls = []
    p = 0
    while p < len(body) - 7:
        b0, b1, b2 = body[p], body[p+1], body[p+2]
        if b0 == 0xE8 and p+5 <= len(body):
            rel = struct.unpack_from("<i", body, p+1)[0]
            calls.append(st + p + 5 + rel); p += 5; continue
        if b0 in (0x48, 0x4c, 0x44, 0x49) and b1 in (0x8d, 0x8b, 0x89, 0x03) and b2 in (0x05, 0x0d, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d):
            rel = struct.unpack_from("<i", body, p+3)[0]
            t = st + p + 7 + rel
            s = cstr(t, 100)
            if s and len(s) >= 3 and all(32 <= ord(ch) < 127 for ch in s):
                strs.append((t, s))
            p += 7; continue
        if b0 == 0x8d and b1 in (0x05, 0x0d, 0x15, 0x1d):
            rel = struct.unpack_from("<i", body, p+2)[0]
            t = st + p + 6 + rel
            s = cstr(t, 100)
            if s and len(s) >= 3 and all(32 <= ord(ch) < 127 for ch in s):
                strs.append((t, s))
            p += 6; continue
        if b0 == 0xE9 and p+5 <= len(body):
            rel = struct.unpack_from("<i", body, p+1)[0]
            calls.append(st + p + 5 + rel); p += 5; continue
        p += 1
    us, seen2 = [], set()
    for t, s in strs:
        if s not in seen2:
            seen2.add(s); us.append((t, s))
    uc = sorted(set(calls))
    P(f"  func {st:#08x}-{en:#08x} ({en-st:5d} B) strs={len(us)} calls={len(uc)}")
    for t, s in us[:20]:
        P(f"      str {t:#010x} {s!r}")
    if uc:
        P(f"      calls {[hex(c) for c in uc[:16]]}")

P("")
P("#"*100)
P("# E) storagepoint.cpp cluster: strings immediately around 0x31fb140-0x31fb260")
o = rva2off(0x31fb000)
seg = buf[o:o+0x400]
P(f"  raw {seg[:0].hex()}")
p = 0
while p < len(seg):
    e = seg.find(b"\0", p)
    if e < 0: break
    if e > p:
        s = seg[p:e]
        ok = all(32 <= b < 127 or b in (9,) for b in s)
        if ok and len(s) >= 3:
            P(f"    {0x31fb000+p:#010x} {s.decode('latin-1')!r}")
    p = e + 1

F.close()
print("wrote p20_out.txt")

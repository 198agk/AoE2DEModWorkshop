"""p18: (a) how are the registry keys reached at all? 32-bit RVA immediates, window refs,
(b) hand-decode the 323-byte function at 0xBDB50 that owns the `modes\\Pompeii\\` literal,
(c) whether the region around 0x1ee15ba really is code.
Read-only. Writes p18_out.txt.
"""
import os, struct, json, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p18_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf)
P(f"exe {N} B")

# --- PE parse ---
e_lfanew = struct.unpack_from("<I", buf, 0x3c)[0]
assert buf[e_lfanew:e_lfanew+4] == b"PE\0\0"
nsec = struct.unpack_from("<H", buf, e_lfanew+6)[0]
optsz = struct.unpack_from("<H", buf, e_lfanew+20)[0]
imagebase = struct.unpack_from("<Q", buf, e_lfanew+24+24)[0]
sects = []
so = e_lfanew + 24 + optsz
for i in range(nsec):
    off = so + i*40
    name = buf[off:off+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, off+8)
    sects.append((name, va, vs, ra, rs))
for s in sects:
    P(f"  {s[0]:8s} rva {s[1]:#010x} vsize {s[2]:#010x} raw {s[3]:#010x} rsize {s[4]:#010x}")
def rva2off(rva):
    for name, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va)
            return o if 0 <= o < N else None
    return None
def off2rva(off):
    for name, va, vs, ra, rs in sects:
        if ra <= off < ra + rs:
            return va + (off - ra)
    return None
def sec_of(rva):
    for name, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return name
    return "?"
def rd(rva, n):
    o = rva2off(rva)
    return buf[o:o+n] if o is not None else b""
def cstr(rva, maxlen=200):
    o = rva2off(rva)
    if o is None: return None
    e = buf.find(b"\0", o, o+maxlen)
    if e < 0: return None
    try: return buf[o:e].decode("ascii")
    except UnicodeDecodeError: return buf[o:e].decode("latin-1")

TEXT = next(s for s in sects if s[0] == ".text")
t_rva, t_rs = TEXT[1], TEXT[4]
t_raw = TEXT[3]

TARGETS = {
    "storage_point_list": 0x325c588,
    "replace": 0x325c5a0,
    "use_modes_path_for_mods": 0x325c5a8,
    "pompeii(mode table)": 0x31f7480,
    "modes\\Pompeii\\": 0x31f8420,
    "mod-status.json": 0x329e8d8,
    "info.json": 0x329eef0,
    "morematerials": 0x325c618,
}

P("")
P("#" * 100)
P("# A) 32-bit IMMEDIATE search: the RVA itself as a little-endian dword anywhere")
for label, tva in TARGETS.items():
    pat = struct.pack("<I", tva)
    hits = []
    start = 0
    while True:
        i = buf.find(pat, start)
        if i < 0: break
        r = off2rva(i)
        hits.append((i, r, sec_of(r) if r else "?"))
        start = i + 1
    P(f"  {label:26s} rva {tva:#010x}: {len(hits)} raw dword hit(s)")
    for i, r, s in hits[:12]:
        P(f"        fileoff {i:#010x} rva {r if r else 0:#010x} {s}")
    if not hits:
        P("        -- none --")
    # also try the fileoff value as dword (in case of file-based tables)
    fo = rva2off(tva)
    if fo:
        pat2 = struct.pack("<I", fo)
        h2 = [i for i in range(0) ]
        cnt = buf.count(pat2)
        P(f"        (fileoff {fo:#010x} as dword appears {cnt} time(s) in whole file)")

P("")
P("#" * 100)
P("# B) every RIP-relative disp32 site whose TARGET lands in a window around the registry cluster")
def scan_disp32_into(lo, hi, maxout=60):
    out = []
    for p in range(t_raw, t_raw + t_rs - 4):
        disp = struct.unpack_from("<i", buf, p)[0]
        rva_p = off2rva(p)
        if rva_p is None: continue
        tgt = rva_p + 4 + disp
        if lo <= tgt < hi:
            prev = buf[p-3:p].hex()
            out.append((rva_p, tgt, prev))
    return out
for name, lo, hi in [("registry 0x325c400-0x325c700", 0x325c400, 0x325c700),
                     ("mode-name table 0x31f7400-0x31f7560", 0x31f7400, 0x31f7560),
                     ("filesystem path cl 0x31f8200-0x31f8500", 0x31f8200, 0x31f8500)]:
    res = scan_disp32_into(lo, hi)
    P(f"  {name}: {len(res)} disp32 site(s)")
    for rva_p, tgt, prev in res[:40]:
        P(f"      site rva {rva_p:#010x} prev3 {prev}  ->  {tgt:#010x}  '{cstr(tgt,60)}'")

P("")
P("#" * 100)
P("# C) full decode of function rva 0xBDB50 .. 0xBDC93 (323 B): LEAs, calls, string targets")
lo, hi = 0xBDB50, 0xBDC93
body = rd(lo, hi - lo)
P(f"  raw: {body.hex()}")
o = rva2off(lo)
p = 0
while p < len(body):
    b = body[p]
    va = lo + p
    note = ""
    if b == 0xE8 and p + 5 <= len(body):
        rel = struct.unpack_from("<i", body, p+1)[0]
        note = f"CALL rel32 -> {va+5+rel:#x}"
        p += 5
    elif b == 0xE9 and p + 5 <= len(body):
        rel = struct.unpack_from("<i", body, p+1)[0]
        note = f"JMP rel32 -> {va+5+rel:#x}"
        p += 5
    elif b in (0x48, 0x4c, 0x49, 0x44, 0x0f, 0xff) and p + 7 <= len(body) and body[p+2] in (0x05, 0x0d, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d) and body[p+1] in (0x8d, 0x8b, 0x89, 0x03, 0x2b):
        rel = struct.unpack_from("<i", body, p+3)[0]
        tgt = va + 7 + rel
        note = f"LEA/MOV rip -> {tgt:#x} '{cstr(tgt,80)}'  [{sec_of(tgt)}]"
        p += 7
    elif b == 0x8d and p + 6 <= len(body) and body[p+1] in (0x05, 0x0d, 0x15, 0x1d):
        rel = struct.unpack_from("<i", body, p+2)[0]
        tgt = va + 6 + rel
        note = f"LEA rip -> {tgt:#x} '{cstr(tgt,80)}'  [{sec_of(tgt)}]"
        p += 6
    else:
        note = f"db {b:02x}"
        p += 1
    if "CALL" in note or "JMP" in note or "->" in note or "rip" in note:
        P(f"    {va:#010x}: {note}")

P("")
P("#" * 100)
P("# D) is 0x1ee1580-0x1ee1620 code?  print bytes + try decode")
for base in (0x1ee1540, 0x1ee1580, 0x1ee15a0, 0x1ee15c0, 0x1ee1600):
    P(f"  rva {base:#010x}: {rd(base,48).hex()}")
P("  .pdata functions covering 0x1ee1540-0x1ee1620:")
pdo = next(s for s in sects if s[0] == ".pdata")
pd_rva, pd_rs, pd_raw = pdo[1], pdo[4], pdo[3]
pdn = pd_rs // 12
for i in range(pdn):
    st, en, ui = struct.unpack_from("<III", buf, pd_raw + i*12)
    if not (st <= 0x1ee1540 < en or st < 0x1ee1620 <= en or (st >= 0x1ee1540 and en <= 0x1ee1620)):
        continue
    P(f"    runtimestruct {st:#x}-{en:#x} ({en-st} B) unwind {ui:#x}")

F.close()
print("wrote p18_out.txt")

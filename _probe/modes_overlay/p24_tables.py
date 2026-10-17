"""p24: (1) whole-tree scan for any file that NAMES 'Pompeii.json' / 'modes\\Pompeii';
 (2) exe literals for wildcard/json-suffix path building;
 (3) the static tables: 0x321cfe0 (pointers to content-mode name strings) and 0x319c348 (fn ptrs);
 (4) decode 0xBDB50 properly, listing every immediate/LEA/CALL in order.
Read-only -> p24_out.txt
"""
import os, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POM = os.path.join(GAME, "modes", "Pompeii")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p24_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf); IMGBASE = 0x140000000
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
P("# 1) whole-tree scan: which FILES contain which markers (byte scan, every file)")
ALL = GAME
markers = [b"Pompeii.json", b"modes\\Pompeii", b"modes/Pompeii", b"modes\\\\Pompeii",
           b"storage_point_list", b"use_modes_path_for_mods", b"use_modes_path"]
hits = {m: [] for m in markers}
nfiles = 0; nbytes = 0; errs = []
for dp, dn, fn in os.walk(ALL):
    for f in fn:
        fp = os.path.join(dp, f)
        try:
            b = open(fp, "rb").read()
        except OSError as ex:
            errs.append((fp, str(ex))); continue
        nfiles += 1; nbytes += len(b)
        for m in markers:
            if m in b:
                hits[m].append((os.path.relpath(fp, ALL), len(b), b.count(m)))
P(f"  scanned {nfiles} files / {nbytes} bytes; {len(errs)} unreadable")
for m in markers:
    P(f"  {m!r}: {len(hits[m])} file(s)")
    for rel, sz, c in hits[m][:25]:
        P(f"      {rel}  ({sz} B, {c} occurrence(s))")
    if len(hits[m]) > 25:
        P(f"      ... and {len(hits[m])-25} more (see p24_markers.json)")

P("")
P("#"*100)
P("# 2) exe literals for wildcard / json-suffix path building")
for pat in [b"*.json", b"*.*", b"\\*.json", b".%s", b"%s.%s", b"%s%s", b".dat", b".pck",
            b"%s\\%s", b"%s/%s", b"\\\\?\\", b"\\\\%s", b"modes.%s", b"modes%s"]:
    P(f"  {pat!r}: {buf.count(pat)}")

P("")
P("#"*100)
P("# 3a) static table feeding off the content-mode name strings: 0x321cfa0 - 0x321d060")
o0 = r2o(0x321cfa0); o1 = r2o(0x321d060)
seg = buf[o0:o1]
p = 0
while p <= len(seg) - 8:
    v = struct.unpack_from("<Q", seg, p)[0]
    rva = 0x321cfa0 + p
    tag = ""
    if IMGBASE <= v < IMGBASE + 0x6000000:
        t = v - IMGBASE
        s = cstr(t, 40)
        tag = f" -> rva {t:#x} [{sec(t)}]" + (f" {s!r}" if s else "")
    P(f"   {rva:#010x}  {v:#018x}{tag}")
    p += 8

P("")
P("#"*100)
P("# 3b) function-pointer array bounds around 0x319c348")
# walk backwards/forwards while entries are valid .text pointers
text = next(x for x in sects if x[0] == ".text")
tv, tvs = text[1], text[2]
def is_text_ptr(v):
    return IMGBASE + tv <= v < IMGBASE + tv + tvs
start = None
p = 0x319c348
while p > 0x319c000:
    v = struct.unpack_from("<Q", buf, r2o(p))[0]
    if not is_text_ptr(v): break
    start = p; p -= 8
end = None
p = 0x319c348
while p < 0x319d400:
    v = struct.unpack_from("<Q", buf, r2o(p))[0]
    if not is_text_ptr(v): break
    end = p; p += 8
P(f"  contiguous .text-pointer run: rva {start:#x} .. {end:#x}  entries={(end-start)//8+1}")
idx = (0x319c3b0 - start)//8
P(f"  modes\\Pompeii\\ fn 0xbdb50 at index {idx} of {(end-start)//8+1}")
P(f"  entries:")
for i in range((end-start)//8+1):
    rva = start + i*8
    v = struct.unpack_from("<Q", buf, r2o(rva))[0] - IMGBASE
    P(f"    [{i:3d}] {rva:#010x} -> {v:#x}")

P("")
P("#"*100)
P("# 4) ordered decode of func 0xBDB50-0xBDC93")
st, en = 0xbdb50, 0xbdc93
body = buf[r2o(st):r2o(en)]
p = 0
while p < len(body):
    q = p
    b = body[p:p+16]
    line = None
    # RIP-relative with 7-byte forms (48/4C 8D/8B/89/03 modrm 05/0d/15/1d)
    if len(b) >= 7 and b[0] in (0x48, 0x4c) and b[1] in (0x8d, 0x8b, 0x89, 0x03, 0x8d) and (b[2] & 0xc7) == 0x05:
        rel = struct.unpack_from("<i", body, p+3)[0]
        t = st+p+7+rel
        s = cstr(t, 60)
        line = f"  {st+p:#08x}: RIP {b[1]:02x} modrm{b[2]:02x} -> rva {t:#x} [{sec(t)}]" + (f" str {s!r}" if s else "")
        p += 7
    elif len(b) >= 6 and b[0] == 0x8d and (b[1] & 0xc7) == 0x05:
        rel = struct.unpack_from("<i", body, p+2)[0]
        t = st+p+6+rel
        s = cstr(t, 60)
        line = f"  {st+p:#08x}: RIP 8d modrm{b[1]:02x} -> rva {t:#x} [{sec(t)}]" + (f" str {s!r}" if s else "")
        p += 6
    elif b[0] == 0xE8 and len(b) >= 5:
        rel = struct.unpack_from("<i", body, p+1)[0]
        line = f"  {st+p:#08x}: CALL rel32 -> {st+p+5+rel:#x}"
        p += 5
    elif b[0] == 0xE9 and len(b) >= 5:
        rel = struct.unpack_from("<i", body, p+1)[0]
        line = f"  {st+p:#08x}: JMP rel32 -> {st+p+5+rel:#x}"
        p += 5
    elif b[0] in (0xB8, 0xB9, 0xBA, 0xBB) and len(b) >= 5:
        v = struct.unpack_from("<I", body, p+1)[0]
        line = f"  {st+p:#08x}: MOV r32, {v:#x} ({v})"
        p += 5
    elif b[0] == 0xC7 and len(b) >= 7 and (b[1] & 0xc7) == 0x05:
        v = struct.unpack_from("<I", body, p+3)[0]
        rel = struct.unpack_from("<i", body, p+3)[0]
        line = f"  {st+p:#08x}: MOV dword [rip+{rel}], {v:#x} ({v}) -> rva {st+p+7+rel:#x}"
        p += 7
    elif b[0] == 0x48 and b[1] == 0x8d and len(b) >= 8 and (b[2] & 0xc7) == 0x05:
        p += 1
    else:
        p += 1
    if line:
        P(line)
F.close()
print("want p24_markers.json too")

# save marker hits
with open(os.path.join(OUT, "p24_markers.json"), "w", encoding="utf-8") as g:
    json.dump({m.decode(): v for m, v in hits.items()}, g, ensure_ascii=False, indent=1)
print("wrote p24_out.txt + p24_markers.json")

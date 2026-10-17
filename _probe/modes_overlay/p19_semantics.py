"""p19: semantics hunt.
 (a) all printable strings in .rdata mentioning storage/mount/override/virtual/variant/mode,
 (b) the .pdata function family 0xbd900-0xbe200 and every string each function references
     -> reveals the "user path / mod root / modes path" setup family,
 (c) do Philadelphia/Paphos/Paris/Providence exist as directories anywhere on disk?
 (d) which DLC codenames appear as files in the BASE tree (they do not use modes/)
Read-only. Writes p19_out.txt.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, json, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p19_out.txt"), "w", encoding="utf-8")
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

P("#" * 100)
P("# A) .rdata printable strings matching semantic keywords (min len 6)")
pat = re.compile(rb"[\x20-\x7e]{6,200}")
rdata = next(s for s in sects if s[0] == ".rdata")
ro, rrva = rdata[3], rdata[1]
blob = buf[ro:ro+rdata[4]]
KEYS = ["storage", "mount", "override", "virtual", "variant", "modes", "content mode",
        "ContentMode", "mode path", "ModesPath", "mod path", "ModPath", "layered", "priority"]
seen = set()
for m in pat.finditer(blob):
    s = m.group().decode("latin-1")
    low = s.lower()
    for k in KEYS:
        if k.lower() in low:
            rva = rrva + ro - ro + m.start()  # careful: rva = rrva + m.start()
            rva = rrva + m.start()
            key = (rva, s)
            if key in seen: continue
            seen.add(key)
            P(f"   {rva:#010x} [{sec_of(rva)}]  {s!r}")
            break
P(f"   ({len(seen)} matching strings)")

P("")
P("#" * 100)
P("# B) .pdata function family near the modes\\Pompeii\\ literal; per-function string refs")
pdo = next(s for s in sects if s[0] == ".pdata")
pd_rva, pd_rs, pd_raw = pdo[1], pdo[4], pdo[3]
funcs = []
for i in range(pd_rs // 12):
    st, en, ui = struct.unpack_from("<III", buf, pd_raw + i*12)
    if 0xb8000 <= st <= 0xc2000:
        funcs.append((st, en))
funcs.sort()
P(f"   {len(funcs)} functions in 0xb8000-0xc2000")
text_sec = next(s for s in sects if s[0] == ".text")
t_raw, t_rs, t_rva = text_sec[3], text_sec[4], text_sec[1]
for st, en in funcs:
    # collect rip-relative targets inside this function
    o0 = rva2off(st); o1 = rva2off(en - 1)
    if o0 is None or o1 is None: continue
    body = buf[o0:o1+1]
    tgts = []
    for p in range(0, len(body) - 6):
        b0 = body[p]
        if b0 in (0x48, 0x4c, 0x44, 0x49) and body[p+1] in (0x8d, 0x8b, 0x89, 0x03, 0x2b) and body[p+2] in (0x05, 0x0d, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d):
            rel = struct.unpack_from("<i", body, p+3)[0]
            tgts.append(st + p + 7 + rel); p += 7
        elif b0 == 0x8d and body[p+1] in (0x05, 0x0d, 0x15, 0x1d):
            rel = struct.unpack_from("<i", body, p+2)[0]
            tgts.append(st + p + 6 + rel); p += 6
        elif b0 in (0x0f, 0x10, 0x28) :
            pass
    strs = []
    for t in tgts:
        s = cstr(t, 120)
        if s is not None and len(s) >= 2 and all(32 <= ord(c) < 127 for c in s):
            strs.append((t, s))
    # unique, keep first 14
    u = []
    for t, s in strs:
        if s not in [x[1] for x in u]: u.append((t, s))
    mark = "  <== owns modes\\Pompeii\\" if any(0xbdb50 <= st <= 0xbdc93 for _ in [0]) else ""
    P(f"   func {st:#08x}-{en:#08x} ({en-st:5d} B) {len(u)} static str refs{mark}")
    if 0xbdb00 <= st <= 0xbe000:
        for t, s in u[:18]:
            P(f"        -> {t:#010x} {s!r}")

P("")
P("#" * 100)
P("# C) do the other content-mode names exist as directories anywhere?")
names = ["Pompeii", "Philadelphia", "Paphos", "Paris", "Providence", "Palermo", "Prague",
         "Porto", "Plymouth", "Peru", "Portland"]
hits = {n: [] for n in names}
for root_label, root in [("game", GAME)]:
    for dp, dn, fn in os.walk(root):
        base = os.path.basename(dp)
        if base in names:
            hits[base].append(os.path.relpath(dp, root))
        for d in dn:
            if d in names and d != base:
                hits[d].append(os.path.relpath(os.path.join(dp, d), root))
for n in names:
    P(f"   dir named {n!r}: {len(hits[n])} -> {hits[n][:8]}")

P("")
P("#" * 100)
P("# D) which codenames appear as FILES in the base tree (content delivered inline)?")
cnt = {}
for dp, dn, fn in os.walk(GAME):
    if "modes" in dp.split(os.sep)[len(GAME.split(os.sep)):len(GAME.split(os.sep))+1]:
        continue
    for f in fn:
        low = f.lower()
        for n in ["paphos", "philadelphia", "paris", "providence", "pompeii", "palermo",
                  "prague", "porto", "plymouth", "peru", "portland"]:
            if n in low:
                cnt.setdefault(n, []).append(os.path.relpath(os.path.join(dp, f), GAME))
for n in sorted(cnt):
    P(f"   base-tree files containing {n!r}: {len(cnt[n])}")
    for x in cnt[n][:12]:
        P(f"       {x}")

F.close()
print("wrote p19_out.txt")

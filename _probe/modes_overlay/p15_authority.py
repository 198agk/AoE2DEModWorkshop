"""p15: authoritative code analysis.
 - entropy map of .text (detect non-code regions so I can judge whether a
   disp32 'hit' is real code or coincidental data)
 - full dump + LEA-string resolution of .pdata func 0xBDB50..0xBDC93
 - indirect references to 0xBDB50
 - content-mode name table + per-mode WWISE bank table
 - second (non-<locale>) storage-point path table
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, json, re, math

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = _HERE_PATH("_probe", "modes_overlay")
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()

e_lfanew = struct.unpack_from("<I", buf, 0x3C)[0]
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", buf, coff + 2)
optsz, = struct.unpack_from("<H", buf, coff + 16)
opt = coff + 20
imgbase, = struct.unpack_from("<Q", buf, opt + 24)
sectab = opt + optsz
secs = []
for i in range(nsec):
    o = sectab + 40 * i
    name = buf[o:o+8].rstrip(b"\0").decode()
    vsize, rva, rsize, rptr = struct.unpack_from("<IIII", buf, o + 8)
    secs.append(dict(name=name, vsize=vsize, rva=rva, rsize=rsize, rawptr=rptr))

def rva2off(rva):
    for s in secs:
        if s["rva"] <= rva < s["rva"] + max(s["vsize"], s["rsize"]):
            o = s["rawptr"] + (rva - s["rva"])
            return o if 0 <= o < len(buf) else None
    return None
def off2rva(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rsize"]:
            return s["rva"] + (off - s["rawptr"])
    return None
def off2sec(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rsize"]:
            return s["name"]
    return None

T = next(s for s in secs if s["name"] == ".text")
TRVA = T["rva"]
TD = buf[T["rawptr"]:T["rawptr"] + T["rsize"]]
F = open(os.path.join(OUT, "p15_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

def cstr_at(rva, back=160, fwd=240):
    o = rva2off(rva)
    if o is None: return None
    a = o
    while a > 0 and buf[a-1] != 0 and (o - a) < back: a -= 1
    b = o
    while b < len(buf) and buf[b] != 0 and (b - o) < fwd: b += 1
    try: return buf[a:b].decode("utf-8")
    except Exception: return buf[a:b].decode("latin1")

P("=" * 100)
P("### 0) .text entropy map (4096-byte windows).  >7.5 bits/byte => data/encrypted, not code")
tot_h = 0.0
cnt = 0
worst = []
for w in range(0, len(TD) - 4096, 4096):
    ch = TD[w:w+4096]
    f = [0]*256
    for b in ch: f[b] += 1
    H = -sum((c/4096)*math.log2(c/4096) for c in f if c)
    tot_h += H; cnt += 1
    if H > 7.5: worst.append((TRVA + w, H))
P(f"  windows: {cnt}  mean entropy {tot_h/cnt:.4f} bits/byte")
P(f"  windows > 7.5 bits/byte: {len(worst)}")
for rva, H in worst[:40]:
    P(f"    rva {rva:#010x} H={H:.4f} sec-span .text")
P("  --- entropy of the specific region .pdata claims is a func at 0x1EE1540 ---")
for rva, n in [(0x1EE1500, 0x100), (0x1EE1400, 0x300)]:
    o = rva2off(rva); ch = buf[o:o+n]
    f = [0]*256
    for b in ch: f[b] += 1
    H = -sum((c/n)*math.log2(c/n) for c in f if c)
    P(f"    rva {rva:#x} len {n} H={H:.4f}  first32={ch[:32].hex(' ')}")

P("")
P("=" * 100)
P("### 1) .pdata func 0xBDB50..0xBDC93 : full dump + resolved LEA targets")
LO, HI = 0xBDB50, 0xBDC93
i = LO
while i < HI:
    c = TD[i-TRVA:i-TRVA+16]
    P(f"  {i:#010x}  {c.hex(' '):<47} |" + "".join(chr(x) if 32 <= x < 127 else "." for x in c) + "|")
    i += 16
P("")
P("  --- every RIP-relative target found in this function (any 4-byte disp whose sum lands in a section) ---")
seen = set()
for p in range(LO - TRVA, HI - TRVA - 4):
    disp, = struct.unpack_from("<i", TD, p)
    t = TRVA + p + 4 + disp
    for back in (3, 4, 7):
        st = TRVA + p - back
        if st < LO: continue
        nxt = st + back + 4
        if nxt + disp != t: continue
        s = cstr_at(t)
        if s is None: continue
        key = (st, t)
        if key in seen: continue
        seen.add(key)
        printable = sum(1 for ch in s if 32 <= ord(ch) < 127) / max(1, len(s))
        P(f"    instr@{st:#x} (disp@{TRVA+p:#x}) -> rva {t:#x} sec {off2sec(rva2off(t))} printable={printable:.2f} {s[:110]!r}")

P("")
P("=" * 100)
P("### 2) indirect references to the function 0xBDB50")
for val, lbl, fmt in [(0xBDB50, "RVA32", "<I"), (imgbase + 0xBDB50, "VA64", "<Q")]:
    pat = struct.pack(fmt, val)
    hits = [m.start() for m in re.finditer(re.escape(pat), buf)]
    P(f"  {lbl} {val:#x}: {len(hits)} hit(s)")
    for h in hits[:30]:
        P(f"      fileoff {h:#x} rva {off2rva(h)} sec {off2sec(h)}")
P("  --- any 8-byte-aligned pointer in .rdata/.data equal to imgbase+0xBDB50 ---")
va = struct.pack("<Q", imgbase + 0xBDB50)
for s in secs:
    if s["name"] not in (".rdata", ".data", "_RDATA"): continue
    blob = buf[s["rawptr"]:s["rawptr"]+s["rsize"]]
    for m in re.finditer(re.escape(va), blob):
        P(f"      {s['name']} fileoff {s['rawptr']+m.start():#x} rva {s['rva']+m.start():#x}")

P("")
P("=" * 100)
P("### 3) content-mode code-name table @0x31f7420 region, full")
for a, s in [(0x31f7480, "Pompeii"), (0x31f7488, "Philadelphia"), (0x31f7498, "Paphos"),
             (0x31f74a0, "Paris"), (0x31f74a8, "Providence"), (0x31f74b8, "WlC?")]:
    P(f"  {a:#010x}: {s!r}")
P("  --- raw region 0x31f7400..0x31f7600 as NUL strings ---")
o = rva2off(0x31f7400)
blob = buf[o:o+0x200]
cur = bytearray(); st = 0
for k, b in enumerate(blob):
    if b == 0:
        if cur: P(f"    {0x31f7400+st:#010x} {bytes(cur).decode('latin1')!r}")
        cur = bytearray(); st = k+1
    else:
        if not cur: st = k
        cur.append(b)
P("  --- all code refs (disp32) to each content-mode name ---")
for name in ["Pompeii", "Philadelphia", "Paphos", "Paris", "Providence", "Plymouth", "Palermo",
             "Prague", "Porto", "Peru", "Portland", "Phoenix"]:
    for m in re.finditer(re.escape(name.encode()), buf):
        fo = m.start(); rva = off2rva(fo)
        if off2sec(fo) != ".rdata": continue
        # only exact NUL-terminated string of that name
        if buf[fo+len(name)] != 0: continue
        if fo > 0 and buf[fo-1] == 0:
            sites = []
            for p in range(len(TD)-4):
                disp, = struct.unpack_from("<i", TD, p)
                if TRVA + p + 4 + disp == rva: sites.append(TRVA+p)
            P(f"    {name!r} @rva {rva:#x}: {len(sites)} disp32 site(s) {[hex(s) for s in sites[:8]]}")

P("")
P("=" * 100)
P("### 4) all strings containing 'modes' (case-sensitive) with exact offsets")
for m in re.finditer(rb"modes", buf):
    fo = m.start(); rva = off2rva(fo)
    s = cstr_at(rva, 40, 120) if rva else None
    P(f"  fileoff {fo:#x} rva {rva} sec {off2sec(fo)}  ctx={s[:90]!r}" if s else f"  fileoff {fo:#x} rva {rva} sec {off2sec(fo)}")

P("")
P("=" * 100)
P("### 5) second storage-point path table: search for other default path literals")
for pat in [b"resources\\_common\\dat", b"resources\\_common\\drs\\graphics", b"resources\\_common\\palettes",
            b"resources\\_common\\campaign", b"resources\\_common\\ai", b"resources\\_common\\scenario",
            b"savegame", b"resources\\_common\\drs", b"resources\\_common\\wpfg", b"resources\\_common\\terrain",
            b"resources\\_common\\particles", b"resources\\_common\\achievements", b"resources\\_common\\strings"]:
    hits = [(m.start(), off2rva(m.start()), off2sec(m.start())) for m in re.finditer(re.escape(pat), buf)]
    P(f"  {pat.decode()!r}: {len(hits)} hit(s)")
    for fo, rva, sec in hits[:8]:
        P(f"      fileoff {fo:#x} rva {rva} sec {sec}  {cstr_at(rva,20,120)!r}")

P("")
P("=" * 100)
P("### 6) search for path-prepend / mode-prefix format strings")
for pat in [rb"modes\\", rb"\\modes", rb"modes%s", rb"%s\\modes", rb"modes\\%s", rb"use_modes",
            rb"modes_path", rb"ModsPath", rb"ModesPath", rb"content_mode", rb"ContentMode"]:
    hits = [m.start() for m in re.finditer(re.escape(pat), buf)]
    P(f"  {pat!r}: {len(hits)} hit(s) {[hex(h) for h in hits[:10]]}")
    for h in hits[:10]:
        rva = off2rva(h)
        P(f"      fo {h:#x} rva {rva} sec {off2sec(h)}  {cstr_at(rva,40,90)!r}")

F.close()
print("wrote p15_out.txt")

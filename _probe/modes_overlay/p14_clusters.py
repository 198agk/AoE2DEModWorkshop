"""p14: correct-RVA string-cluster dumps + focused reference analysis.
Writes report to p14_out.txt (utf-8) to avoid console truncation.
Canonical: RVA = VA - ImageBase; fileoff = rawptr + (RVA - sec.rva).
"""
import os, struct, json, re, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
F = open(os.path.join(OUT, "p14_out.txt"), "w", encoding="utf-8")
def P(*a):
    print(*a, file=F)

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

T = next(s for s in secs if s["name"] == ".text")
TD = buf[T["rawptr"]:T["rawptr"] + T["rsize"]]
TRVA = T["rva"]

def strings_in(rva, n):
    o = rva2off(rva)
    if o is None: return []
    blob = buf[o:o+n]; res = []; cur = bytearray(); start = 0
    for i, b in enumerate(blob):
        if b == 0:
            if cur: res.append((rva + start, bytes(cur).decode("latin1")))
            cur = bytearray(); start = i + 1
        else:
            if not cur: start = i
            cur.append(b)
    if cur: res.append((rva + start, bytes(cur).decode("latin1")))
    return res

def cluster(title, rva, n):
    P("\n" + "=" * 96)
    P(f"### {title}   rva {rva:#x} (fileoff {rva2off(rva):#x}) len {n}")
    for a, s in strings_in(rva, n):
        P(f"  {a:#010x} (fo {rva2off(a):#08x})  {s!r}")
    P("")

# ---- 1. the filesystem.cpp path cluster (contains modes\Pompeii\) ----
cluster("path cluster A (filesystem.cpp, contains modes\\Pompeii\\)", 0x31f8250, 0x2B0)
# ---- 2. the <locale> template table (6 hits) ----
cluster("path template table (<locale> x6)", 0x31fa6e0, 0x340)
# ---- 3. 'Pompeii' at 0x31f7480 (referenced by MOV rax,[rip]) ----
cluster("'Pompeii' cluster @0x31f7480 (5 code refs)", 0x31f7420, 0x180)
# ---- 4. the 6 'Pompeii' strings @0x321f580..0x321f780 (LEA refs) ----
cluster("'Pompeii' constants @0x321f540 (6 LEA refs)", 0x321f520, 0x2A0)
# ---- 5. 'Pompeii' @0x31ccfca (no code refs) ----
cluster("'Pompeii' @0x31ccfca (no code refs)", 0x31ccf80, 0xC0)
# ---- 6. registry blob ----
cluster("storage-point registry blob", 0x325c560, 0xE0)
# ---- 7. mod manager cluster ----
cluster("ModManager / mod-status.json cluster", 0x329e880, 0x260)
cluster("info.json cluster", 0x329eea0, 0x140)
# ---- 8. localization cluster with pompeii-strings ----
cluster("LocalizationManager cluster (pompeii-strings)", 0x31fe140, 0x140)
# ---- 9. regression harness ----
cluster("Regression tool cluster", 0x334f4f0, 0x100)

# ---- 10. disassemble around the modes\Pompeii\ reference precisely ----
P("\n" + "=" * 96)
P("### raw bytes around the code that loads 'modes\\Pompeii\\' (rva 0x31f8420)")
for rva in range(0xbdb70, 0xbdbc0, 16):
    c = TD[rva - TRVA:rva - TRVA + 16]
    asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
    P(f"  {rva:#010x}  {c.hex(' '):<47} |{asc}|")

P("\n### raw bytes around the code that loads storage_point_list (rva 0x325c588)")
for rva in range(0x1ee1580, 0x1ee1620, 16):
    c = TD[rva - TRVA:rva - TRVA + 16]
    asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
    P(f"  {rva:#010x}  {c.hex(' '):<47} |{asc}|")
P("\n### all .rdata strings referenced from func 0x1EE1540..0x1EE167C")
for p in range(0x1EE1540 - TRVA, 0x1EE167C - TRVA):
    disp, = struct.unpack_from("<i", TD, p)
    t = TRVA + p + 4 + disp
    o = rva2off(t)
    if o is None: continue
    a = o
    while a > 0 and buf[a-1] != 0 and (o - a) < 120: a -= 1
    b = o
    while b < len(buf) and buf[b] != 0 and (b - o) < 200: b += 1
    s = buf[a:b].decode("latin1")
    if len(s) >= 3 and sum(1 for ch in s if 32 <= ord(ch) < 127) / len(s) > 0.85:
        P(f"   {s!r}  (target rva {t:#x}) via disp32 @rva {TRVA+p:#x}")

# ---- 11. the 323-byte function at 0xbdb50: what does it call? ----
P("\n### calls (E8 rel32) inside func rva 0xbdb50..0xbdc93")
for p in range(0xbdb50 - TRVA, 0xbdc93 - TRVA - 5):
    if TD[p] == 0xE8:
        rel, = struct.unpack_from("<i", TD, p + 1)
        tgt = TRVA + p + 5 + rel
        P(f"   rva {TRVA+p:#x} -> call {tgt:#x}")
    elif TD[p] == 0xE9:
        rel, = struct.unpack_from("<i", TD, p + 1)
        P(f"   rva {TRVA+p:#x} -> jmp {TRVA+p+5+rel:#x}")

# ---- 12. RTTI for the 6 LEA'd Pompeii constants ----
P("\n### version resource check")
P("   (see earlier block)")

F.close()
print("wrote", os.path.join(OUT, "p14_out.txt"))

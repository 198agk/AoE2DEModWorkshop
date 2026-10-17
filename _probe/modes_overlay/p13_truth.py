"""p13: ground-truth PE mapping + unambiguous string/code reference scan.
Fixes the RVA-vs-fileoff confusion in my earlier blocks.
Canonical: RVA = VA - ImageBase.  off = rawptr + (RVA - sec.rva).
"""
import os, struct, json, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
print("exe size", len(buf))

e_lfanew = struct.unpack_from("<I", buf, 0x3C)[0]
print("e_lfanew", hex(e_lfanew))
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", buf, coff + 2)
optsz, = struct.unpack_from("<H", buf, coff + 16)
opt = coff + 20
magic, = struct.unpack_from("<H", buf, opt)
imgbase, = struct.unpack_from("<Q", buf, opt + 24)
sectab = opt + optsz
secs = []
for i in range(nsec):
    o = sectab + 40 * i
    name = buf[o:o+8].rstrip(b"\0").decode()
    vsize, rva, rsize, rptr = struct.unpack_from("<IIII", buf, o + 8)
    secs.append(dict(name=name, vsize=vsize, rva=rva, rsize=rsize, rawptr=rptr))
print("ImageBase", hex(imgbase), "nsec", nsec)
for s in secs:
    print(f"  {s['name']:8s} rva {s['rva']:#010x} vsize {s['vsize']:#x} raw {s['rawptr']:#010x} rsize {s['rsize']:#x}")

def rva2off(rva):
    for s in secs:
        if s["rva"] <= rva < s["rva"] + max(s["vsize"], s["rsize"]):
            return s["rawptr"] + (rva - s["rva"])
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
TD = buf[T["rawptr"]:T["rawptr"] + T["rsize"]]
TRVA = T["rva"]

def dump_bytes(rva, n, label=""):
    off = rva2off(rva)
    if off is None:
        print(f"  [{label}] rva {rva:#x} -> no section"); return
    print(f"\n--- {label} rva {rva:#x} fileoff {off:#x} sec {off2sec(off)} ---")
    for i in range(0, n, 16):
        c = buf[off+i:off+i+16]
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
        print(f"  {rva+i:#010x} (+{off+i:#08x})  {c.hex(' '):<47} |{asc}|")

def dump_strings(rva, n, label=""):
    off = rva2off(rva)
    blob = buf[off:off+n]
    cur = bytearray(); start = 0
    print(f"\n--- strings in {label} rva {rva:#x}..{rva+n:#x} ({n} B) ---")
    for i, b in enumerate(blob):
        if b == 0:
            if cur:
                s = bytes(cur).decode("latin1")
                print(f"  {rva+start:#010x} (len {len(cur):3d}) {s!r}")
            cur = bytearray(); start = i + 1
        else:
            if not cur: start = i
            cur.append(b)
    if cur:
        print(f"  {rva+start:#010x} (len {len(cur):3d}) {bytes(cur).decode('latin1')!r}")

print("\n" + "=" * 100)
print("A) STRING LOCATIONS (searched by content over whole file; fileoff, then rva, then section)")
TARGETS = [b"modes\\Pompeii\\", b"storage_point_list", b"replace\0", b"use_modes_path_for_mods",
           b"mod-status.json", b"info.json", b"pompeii-strings", b"Pompeii.json",
           b"Age of Empires II: Definitive Edition", b"Age of Empires 2 DE", b"workshop\\content",
           b"<userrelicid>", b"<locale>", b"ReturnOfRome", b"Return of Rome", b"morematerials",
           b"&size_pompeii", b"Pompeii"]
strrvas = {}
for t in TARGETS:
    hits = [m.start() for m in re.finditer(re.escape(t), buf)]
    print(f"\n  {t!r}: {len(hits)} hit(s)")
    for h in hits:
        r = off2rva(h)
        print(f"      fileoff {h:#010x}  rva {r if r is None else hex(r)}  sec {off2sec(h)}")
        if r is not None:
            strrvas.setdefault(t, []).append(r)

print("\n" + "=" * 100)
print("B) BRUTE disp32 SCAN over .text: does ANY instruction compute the address of these strings?")
for t in sorted(strrvas, key=lambda x: strrvas[x][0]):
    for rva in strrvas[t]:
        found = []
        for p in range(len(TD) - 4):
            disp, = struct.unpack_from("<i", TD, p)
            if TRVA + p + 4 + disp == rva:
                found.append(p)
        lbl = t.decode("latin1", "replace")
        print(f"\n  target {lbl!r} rva {rva:#x} -> {len(found)} disp32 site(s)")
        for p in found:
            site = TRVA + p
            pre = TD[p-4:p]
            print(f"      disp32 at rva {site:#x} (fileoff {rva2off(site):#x})")
            print(f"        bytes[{site-8:#x}..{site+8:#x}] = {TD[p-8:p+8].hex(' ')}")
            # candidate RIP-relative instr starts in the 7 bytes before disp32
            for back in (3, 4, 7):
                q = p - back
                if q >= 0:
                    print(f"        if instr starts {back}B before disp: rva {TRVA+q:#x} bytes {TD[q:q+back].hex(' ')}")

print("\n" + "=" * 100)
print("C) REGISTRY BLOB raw bytes")
dump_bytes(0x325c570, 0x60, "storage_point_list / replace / use_modes_path_for_mods blob")

print("\n" + "=" * 100)
print("D) PATH-TEMPLATE CLUSTER around modes\\Pompeii\\")
dump_bytes(0x31f6280, 0x240, "filesystem.cpp path cluster start")
dump_strings(0x31f6280, 0x240, "filesystem.cpp path cluster")
print()
dump_strings(0x31f8700, 0x400, "post-cluster <locale> template area")

print("\n" + "=" * 100)
print("E) FUNCTION that references storage_point_list (rva 0x1EE1540..0x1EE167C)")
LO, HI = 0x1EE1540, 0x1EE167C
for i in range(LO, HI, 16):
    c = TD[i-TRVA:i-TRVA+16]
    asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
    print(f"  {i:#010x}  {c.hex(' '):<47} |{asc}|")
print("\n  strings referenced by that function:")
for p in range(LO - TRVA, min(len(TD) - 4, HI - TRVA)):
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
        print(f"     {s!r} (rva {t:#x}) via disp32 at rva {TRVA+p:#x}")

print("\n  direct callers of 0x1EE1540 (E8 rel32):")
callers = []
for i in range(len(TD) - 5):
    if TD[i] == 0xE8:
        rel, = struct.unpack_from("<i", TD, i + 1)
        if TRVA + i + 5 + rel == LO:
            callers.append(TRVA + i)
print("   ", len(callers), [hex(c) for c in callers[:20]])

print("\n" + "=" * 100)
print("F) who references the modes\\Pompeii\\ function? data pointers to 0xBDB50 / 0x1400BDB50")
for val, lbl in [(0xBDB50, "RVA 32-bit"), (imgbase + 0xBDB50, "VA 64-bit")]:
    if lbl.endswith("32-bit"):
        pat = struct.pack("<I", val)
    else:
        pat = struct.pack("<Q", val)
    hits = [m.start() for m in re.finditer(re.escape(pat), buf)]
    print(f"\n  {lbl} {val:#x}: {len(hits)} raw hit(s)")
    for h in hits[:20]:
        print(f"      fileoff {h:#x} rva {off2rva(h)} sec {off2sec(h)}")

print("\n" + "=" * 100)
print("G) .pdata function containing the modes\\Pompeii\\ LEA (if any) + neighbours")
funcs = sorted(tuple(x) for x in json.load(open(os.path.join(OUT, "exe_funcmap.json"))))
def func_of(rva):
    lo, hi = 0, len(funcs) - 1
    while lo <= hi:
        m = (lo + hi) // 2
        b, e, u = funcs[m]
        if b <= rva < e: return funcs[m]
        if rva < b: hi = m - 1
        else: lo = m + 1
    return None
for rva in [0xBDB50, 0xBDB9E, 0x1EE1540, 0x1EE15BA]:
    print(f"  rva {rva:#x} -> {func_of(rva)}")

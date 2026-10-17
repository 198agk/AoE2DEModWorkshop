"""p26: two decisive checks.
(1) BLOCK-REFERENCE TEST: does any .text disp32 point INTO the registry blob (0x325c480-0x325c800),
    the content-mode table (0x321ef60-0x321f080), or the storagepoint.cpp cluster (0x31faf00-0x31fb400)?
    If the code takes the blob base and slices by offset, individual key names show 0 refs but the
    block start would be referenced.
(2) MOD TOP-LEVEL SHAPE: list top-level entries of every installed mod, looking for a `modes` dir
    or a `resources\\_common\\dat` mirror (empirical test of Q2 / Q4).
Read-only -> p26_out.txt
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p26_out.txt"), "w", encoding="utf-8")
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
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"
TEXT = [s for s in sects if s[0] == ".text"][0]
_, tva, tvs, tra, trs = TEXT
text = buf[tra:tra+trs]
P("#"*100)
P("# 1) BLOCK-REFERENCE TEST: every .text disp32 (RIP-relative or rel32) landing in a range")
RANGES = {
    "registry blob (storage_point_list/replace/use_modes_path_for_mods)": (0x325c480, 0x325c800),
    "content-mode DLC table 0x321efe0":                                   (0x321ef60, 0x321f080),
    "storagepoint.cpp string cluster":                                    (0x31faf00, 0x31fb400),
    "path-template table #0 (storage-point defaults)":                    (0x31f8500, 0x31f8700),
    "path-template table #1 (<locale>)":                                  (0x31fa6e0, 0x31faa00),
    "content-mode name block 0x31f7460":                                  (0x31f7460, 0x31f7520),
}
for label, (lo, hi) in RANGES.items():
    rip_hits = []; rel_hits = []
    for p in range(0, len(text) - 4):
        d = struct.unpack_from("<i", text, p)[0]
        # RIP-relative: next instruction at rva tva+p+4 ; any instruction length, so approximate
        tgt = (tva + p + 4) + d
        if lo <= tgt < hi:
            modrm = text[p-1] if p >= 1 else 0
            # keep only if the disp is plausibly the last 4 bytes of an instruction with RIP modrm
            rip_hits.append((tva + p, tgt, text[max(0,p-4):p+4].hex()))
        # rel32 call/jmp target (E8/E9 opcode right before)
        if p >= 1 and text[p-1] in (0xE8, 0xE9):
            t2 = (tva + p + 4) + d
            if lo <= t2 < hi:
                rel_hits.append((tva + p - 1, t2))
    P(f"   {label}")
    P(f"       range [{lo:#x},{hi:#x})  rip-like disp32 hits: {len(rip_hits)}  E8/E9 rel32 hits: {len(rel_hits)}")
    for site, tgt, bb in rip_hits[:12]:
        P(f"         disp32 @rva {site:#x} -> {tgt:#x} [{sec(tgt)}]  prev4={bb}")
    for site, tgt in rel_hits[:12]:
        P(f"         E8/E9  @rva {site:#x} -> {tgt:#x}")

P("")
P("   control: the SAME scan for the exact 3 key strings (must be 0/0 if truly unreferenced)")
for label, rva in (("storage_point_list", 0x325c588), ("replace", 0x325c5a0),
                   ("use_modes_path_for_mods", 0x325c5a8), ("modes\\Pompeii\\", 0x31f8420),
                   ("Pompeii", 0x31f7480)):
    n_rip = 0; n_rel = 0
    for p in range(0, len(text) - 4):
        d = struct.unpack_from("<i", text, p)[0]
        if (tva + p + 4) + d == rva: n_rip += 1
        if p >= 1 and text[p-1] in (0xE8, 0xE9) and (tva + p + 4) + d == rva: n_rel += 1
    P(f"     {label!r:28s} rva {rva:#x}: rip-ish={n_rip}  E8/E9={n_rel}")
    if rva == 0x31f7480:
        P(f"       (control: 'Pompeii' HAS refs -> method is not blind)")

P("")
P("#"*100)
P("# 2) MOD TOP-LEVEL SHAPE (empirical: do installed mods mirror the game root, or a modes/ tree?)")
USERROOT = r"C:\Users\26913\Games\Age of Empires 2 DE"
cands = []
for prof in os.listdir(USERROOT):
    mp = os.path.join(USERROOT, prof, "mods")
    if os.path.isdir(mp):
        for kind in ("local", "subscribed"):
            kp = os.path.join(mp, kind)
            if os.path.isdir(kp):
                for m in sorted(os.listdir(kp)):
                    cands.append((prof, kind, m, os.path.join(kp, m)))
P(f"   mod folders found: {len(cands)}")
for prof, kind, m, p in cands:
    try:
        tops = sorted(os.listdir(p))
    except Exception as ex:
        P(f"   - {prof}/{kind}/{m}: ERROR {ex}"); continue
    has_modes = [t for t in tops if t.lower() == "modes"]
    P(f"   - {prof}/{kind}/{m}")
    P(f"       top-level ({len(tops)}): {tops[:40]}")
    P(f"       contains 'modes' dir: {has_modes if has_modes else 'NO'}")
    # does it carry a dat mirror?
    dp = os.path.join(p, "resources", "_common", "dat")
    if os.path.isdir(dp):
        try:
            P(f"       resources\\_common\\dat mirror: {sorted(os.listdir(dp))[:20]}")
        except Exception as ex:
            P(f"       resources\\_common\\dat: {ex}")
    ip = os.path.join(p, "info.json")
    if os.path.isfile(ip):
        try:
            j = json.loads(open(ip, "r", encoding="utf-8-sig", errors="replace").read())
            P(f"       info.json keys: {sorted(j.keys())}")
        except Exception as ex:
            P(f"       info.json unreadable: {ex}")

P("")
P("# 2b) the 639-entry static-init pointer table at rva 0x319c008: what band does it cover?")
o = None
for nm, va, vs, ra, rs in sects:
    if va <= 0x319c008 < va + max(vs, rs): o = ra + (0x319c008 - va)
vals = []
for i in range(639):
    v = struct.unpack_from("<Q", buf, o + i*8)[0]
    vals.append(v - IB if IB <= v < IB + 0x6000000 else None)
idx = vals.index(0xbdb50) if 0xbdb50 in vals else -1
P(f"   'modes\\Pompeii\\' initializer fn 0xbdb50 at index {idx}; neighbours' rvas:")
for j in range(max(0, idx-3), min(639, idx+4)):
    P(f"     [{j:3d}] {vals[j]:#x}" if vals[j] is not None else f"     [{j:3d}] (non-text)")
lo = [v for v in vals if v is not None]
P(f"   table spans .text rvas {min(lo):#x}..{max(lo):#x}; {len(lo)} entries resolve into .text")
F.close()
print("wrote p26_out.txt")

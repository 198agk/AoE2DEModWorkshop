"""p27: RIGOROUS reference test. A disp32 counts as a real RIP-relative reference only if the
byte at p-1 (the ModRM) has mod=00 and rm=101 (RIP-relative addressing), which is a NECESSARY
condition for any x64 RIP-relative operand. This kills the coincidental hits that land mid-string.

Also: is any target a real STRING START (preceded by a NUL byte)? Mid-string targets are impossible
for a genuine reference.
Read-only -> p27_out.txt
"""
import os, struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p27_out.txt"), "w", encoding="utf-8")
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
TEND = tva + len(text)

def is_rip_modrm(b):
    return (b & 0xC7) == 0x05          # mod=00 (no disp8/disp32 beyond RIP), rm=101

def refs_to(target_rva, label):
    """Real refs: disp32 at p, ModRM at p-1 is RIP-relative, and VA(p+4)+disp == target."""
    strict = []
    loose_mid = 0
    for p in range(1, len(text) - 4):
        d = struct.unpack_from("<i", text, p)[0]
        if (tva + p + 4) + d != target_rva: continue
        if is_rip_modrm(text[p-1]):
            strict.append(tva + p)
        else:
            loose_mid += 1
    # is the target a genuine string start in the image?
    o = r2o(target_rva)
    start_ok = o is not None and o > 0 and buf[o-1] == 0
    P(f"   {label!r}")
    P(f"       rva {target_rva:#x} [{sec(target_rva)}]  string-start={start_ok}  "
      f"STRICT refs={len(strict)}  rejected(non-RIP ModRM)={loose_mid}")
    for s in strict:
        P(f"         site rva {s:#x}  prev5={text[s-4:s+4].hex()}")
    return strict

P("#"*100)
P("# A) STRICT (ModRM-validated) RIP-relative refs to the registry key names")
for lab, rva in (("storage_point_list", 0x325c588), ("replace", 0x325c5a0),
                 ("use_modes_path_for_mods", 0x325c5a8),
                 ("morematerials", 0x325c618), ("materials", 0x325c610),
                 ("linkedUnits.json", 0x325c5c0),
                 ("futuravailableunits.json", 0x325c5e0),
                 ("paphosfutureavailableunits.json", 0x325c5f8)):
    refs_to(rva, lab)

P("")
P("#"*100)
P("# B) STRICT refs to the two path literals + the content-mode names (positive controls)")
for lab, rva in (("modes\\Pompeii\\", 0x31f8420), ("pompeii-strings", 0x31fe1d8),
                 ("Pompeii", 0x31f7480), ("Philadelphia", 0x31f7488), ("Paphos", 0x31f7498),
                 ("Paris", 0x31f74a0), ("Providence", 0x31f74a8),
                 ("mod-status.json", 0x329e8d8), ("info.json", 0x329eef0),
                 ("UNIQUE_TEMP_FOLDER", 0x31f8408)):
    refs_to(rva, lab)

P("")
P("#"*100)
P("# C) MID-STRING FALSIFICATION: for the content-mode block, show how many 'loose' hits land")
P("   MID-string (impossible for a real reference) vs exactly at a string start (possible).")
lo, hi = 0x31f7460, 0x31f7520
o = r2o(lo)
seg = buf[o:o + (hi-lo)]
# collect string starts inside the block
starts = [lo + i for i in range(len(seg))
          if (i == 0 or seg[i-1] == 0) and seg[i] != 0]
P(f"   string starts in block: {[hex(x) for x in starts]}")
loose_all = 0; loose_mid = 0; loose_start = 0
for p in range(1, len(text) - 4):
    d = struct.unpack_from("<i", text, p)[0]
    t = (tva + p + 4) + d
    if lo <= t < hi:
        loose_all += 1
        if t in starts: loose_start += 1
        else: loose_mid += 1
P(f"   TOTAL raw disp32 hits into block: {loose_all}")
P(f"     landing EXACTLY on a string start (0x31f7480/88/98/74a0/74a8): {loose_start}")
P(f"     landing MID-string or on padding        (coincidental)         : {loose_mid}")
P(f"   -> {loose_mid/loose_all*100:.1f}% of raw hits are coincidental; only the ModRM-validated")
P(f"      ones on string starts are real references.")

P("")
P("#"*100)
P("# D) SAME test on the registry blob: where do the REAL refs land vs where the keys live?")
lo, hi = 0x325c480, 0x325c800
o = r2o(lo); seg = buf[o:o+(hi-lo)]
starts = [lo + i for i in range(len(seg)) if (i == 0 or seg[i-1] == 0) and seg[i] != 0]
P(f"   string starts in blob:")
for s in starts:
    q = buf.find(b"\0", r2o(s))
    if q > 0:
        t = buf[r2o(s):q].decode("latin-1")
        if all(32 <= ord(c) < 127 for c in t):
            P(f"     {s:#010x} {t!r}")
real = {}
for p in range(1, len(text) - 4):
    d = struct.unpack_from("<i", text, p)[0]
    t = (tva + p + 4) + d
    if lo <= t < hi and is_rip_modrm(text[p-1]):
        real.setdefault(t, []).append(tva + p)
P(f"   ModRM-validated refs into the blob: {len(real)} distinct target(s)")
for t in sorted(real):
    onstart = "STRING START" if t in starts else "mid-string/padding"
    P(f"     target {t:#x} [{onstart}]  sites={[hex(x) for x in real[t]]}")

P("")
P("#"*100)
P("# E) FULL-TREE re-verification of the one decisive negative: '.json' name construction")
for pat in (b"%s.json", b"%s.JSON", b"%s.json\\0"):
    cnt = buf.count(pat)
    P(f"   {pat!r}: {cnt} occurrence(s)")
    s = 0
    while True:
        i = buf.find(pat, s)
        if i < 0: break
        a = max(0, i-40); b2 = min(N, i+len(pat)+10)
        ctx = buf[a:b2]
        P(f"       fo {i:#x} ctx {ctx!r}")
        s = i + 1
F.close()
print("wrote p27_out.txt")

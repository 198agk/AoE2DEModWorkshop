"""p31: dump raw bytes around the LOGS storage-point enum and decide the true separator/count.
Read-only -> p31_out.txt
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p31_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read(); N = len(buf)
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
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None
def sec(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return nm
    return "?"

i = buf.find(b"\0LOGS\0")
P(f"fo 0x{i:x} = the 'LOGS' occurrence. RAW BYTES fo 0x{i-16:x} .. fo 0x{i+0x180:x}:")
seg = buf[i-16:i+0x180]
for k in range(0, len(seg), 16):
    chunk = seg[k:k+16]
    hexs = " ".join(f"{b:02x}" for b in chunk)
    txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    P(f"   {i-16+k:#08x}  {hexs:<48}  {txt}")

P("")
P("# ALL byte occurrences of 'LOGS' and their immediate following bytes:")
p = 0
while True:
    j = buf.find(b"LOGS", p)
    if j < 0: break
    P(f"   fo 0x{j:x} [{sec(j)}] next 80 bytes: {buf[j:j+80]!r}")
    p = j + 1

P("")
P("# Search for the exact tail string of the root/source enum, to bound the real enum:")
for tail in (b"SUBSCRIBEDMODS", b"NOTFOUND", b"APPATA", b"MODSROOT"):
    p = 0; hits = []
    while True:
        j = buf.find(tail, p)
        if j < 0: break
        hits.append(j); p = j + 1
    P(f"   {tail!r}: {len(hits)} hit(s) {[hex(x) for x in hits[:8]]}")
    if hits:
        j = hits[0]
        P(f"       ctx fo 0x{j-0x80:x}: {buf[j-0x80:j+0x60]!r}")

P("")
P("# If the whole enum is ONE space/other-separated blob, print printable runs containing 'LOGS':")
j = i + 1
a = j
while a > 0 and 32 <= buf[a-1] < 127: a -= 1
b2 = j
while b2 < N and (32 <= buf[b2] < 127): b2 += 1
P(f"   printable run containing LOGS: fo 0x{a:x}..0x{b2:x} ({b2-a} B)")
blob = buf[a:b2].decode("latin-1")
P(f"   {blob!r}")
# try comma / space / newline splits
import re
for sep in (",", " ", "\n", ";", "\t"):
    if sep in blob:
        parts = [x.strip() for x in blob.split(sep) if x.strip()]
        P(f"   split on {sep!r}: {len(parts)} -> {parts}")
F.close()
print("wrote p31_out.txt")

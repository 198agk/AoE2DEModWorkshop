"""p32: exact enumeration of the storage-point enum from raw bytes.
The enum is NUL-terminated strings separated by varying 0-7 bytes of NUL padding, so the correct
parse is: scan for maximal printable runs, not strict single-NUL separators.
Read-only -> p32_out.txt
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p32_out.txt"), "w", encoding="utf-8")
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

START = 0x31f8cc4          # 'LOGS'
# end = just before 'COUNT' which begins the root/source enum
ci = buf.find(b"\0COUNT\0", START)
P(f"enum start fo {START:#x} ('LOGS'); '\\0COUNT\\0' at fo {ci:#x}")
seg = buf[START:ci]
P(f"segment length {len(seg)} B")
P("")
P("full raw segment:")
for k in range(0, len(seg), 16):
    chunk = seg[k:k+16]
    hexs = " ".join(f"{b:02x}" for b in chunk)
    txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    P(f"   {START+k:#08x}  {hexs:<48}  {txt}")

P("")
P("# maximal printable runs (the true enum members, in order):")
names = []
for m in re.finditer(rb"[\x20-\x7e]{1,40}", seg):
    names.append((START + m.start(), m.group().decode("ascii")))
for k, (o, t) in enumerate(names, 1):
    P(f"   [{k:2d}] rva {o2r(o):#010x}  {t}")
P("")
P(f"# MEASURED storage-point count = {len(names)}")
P(f"# Brief claimed 46        -> {'MATCH' if len(names)==46 else '*** MISMATCH: actual %d ***' % len(names)}")

P("")
P("# root/source enum (COUNT onward, same padding rule):")
seg2 = buf[ci+1:ci+1+240]
run2 = []
for m in re.finditer(rb"[\x20-\x7e]{1,40}", seg2):
    run2.append((ci+1 + m.start(), m.group().decode("ascii")))
    if len(run2) >= 14: break
for o, t in run2:
    P(f"   rva {o2r(o):#010x}  {t}")

P("")
P("# CROSS-CHECK against Pompeii.json's 28 declared types")
import json
j = json.loads(open(r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\Pompeii.json","rb").read().decode("utf-8-sig"))
used = [x["type"] for x in j["storage_point_list"]]
enum = [t for _, t in names]
P(f"   enum={len(enum)}  used={len(used)}")
P(f"   used-but-not-in-enum: {[x for x in used if x not in enum]}")
unused = [x for x in enum if x not in used]
P(f"   enum-but-unused: {len(unused)}")
for x in unused: P(f"      - {x}")
P("")
P(f"   arithmetic: {len(enum)} - {len(used)} = {len(enum)-len(used)}  vs unused {len(unused)}  "
  f"{'CONSISTENT' if len(enum)-len(used)==len(unused) else '*** INCONSISTENT ***'}")
F.close()
print("wrote p32_out.txt")

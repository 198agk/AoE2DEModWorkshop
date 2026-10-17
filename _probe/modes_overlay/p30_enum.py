"""p30: verify the storage-point enum COUNT and the unused set directly from the exe,
rather than trusting the 46/47 discrepancy in the task brief.
Locates the enum, splits it exactly, and diffs against Pompeii.json's 28 types.
Read-only -> p30_out.txt
"""
import os, struct, json, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p30_out.txt"), "w", encoding="utf-8")
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

# The enum starts at the 'LOGS' NUL-terminated string. Find it as a whole string.
i = buf.find(b"\0LOGS\0")
P(f"found '\\0LOGS\\0' at fo {i:#x}" if i > 0 else "NOT FOUND '\\0LOGS\\0'")
start = i + 1
# walk NUL-terminated strings until we hit the root/source enum tail
seq = []
p = start
while True:
    q = buf.find(b"\0", p)
    if q < 0: break
    s = buf[p:q]
    try: t = s.decode("ascii")
    except Exception: break
    if not (1 <= len(t) <= 40 and all(32 <= ord(c) < 127 for c in t)):
        break
    seq.append((p, t))
    p = q + 1
    if len(seq) > 120: break

P("")
P(f"# raw NUL-terminated sequence starting at LOGS ({len(seq)} strings before a break)")
for o, t in seq:
    P(f"   rva {o2r(o):#010x}  {t}")

# The storage-point enum ends where the root/source enum begins.
ROOT_ENUM = ["COUNT", "NONE", "NOTFOUND", "TEMP", "BASE", "APPATA", "USER",
             "MODSROOT", "LOCALMODS", "SUBSCRIBEDMODS", "DLC", "CLOUD"]
names = [t for _, t in seq]
ri = next((k for k, t in enumerate(names) if t == "COUNT"), None)
P("")
if ri is not None:
    sp = names[:ri]
    root = names[ri:ri+len(ROOT_ENUM)]
    P(f"# SPLIT: storage-point enum = {len(sp)} names; root/source enum = {len(root)} names")
    P(f"   storage points ({len(sp)}): {sp}")
    P(f"   root/source   ({len(root)}): {root}")
    P(f"   BRIEF CLAIMED 46 storage points -> MEASURED {len(sp)}  "
      f"{'MATCH' if len(sp)==46 else '*** MISMATCH ***'}")
else:
    sp = names
    P("# could not find 'COUNT' separator")

# Pompeii.json used types
PJ = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\Pompeii.json"
j = json.loads(open(PJ, "rb").read().decode("utf-8-sig"))
used = [x["type"] for x in j["storage_point_list"]]
P("")
P(f"# Pompeii.json declares {len(used)} storage points")
P(f"   {used}")
unused = [x for x in sp if x not in used]
P("")
P(f"# enum names NOT used by Pompeii.json: {len(unused)}")
P(f"   {unused}")
P(f"   check: len(enum)={len(sp)} - len(used)={len(used)} = {len(sp)-len(used)}"
  f"  (unused computed = {len(unused)}) "
  f"{'CONSISTENT' if len(sp)-len(used)==len(unused) else '*** INCONSISTENT (duplicates?) ***'}")
# duplicates in used?
dup = [x for x in set(used) if used.count(x) > 1]
P(f"   duplicate types in Pompeii.json: {dup if dup else 'none'}")
# names in used but not in enum?
P(f"   used-but-not-in-enum: {[x for x in used if x not in sp]}")
F.close()
print("wrote p30_out.txt")

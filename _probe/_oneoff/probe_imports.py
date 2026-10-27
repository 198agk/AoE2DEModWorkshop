# -*- coding: utf-8 -*-
"""Print the exe's full import table, including delay-load, with resolved names."""
import struct
import sys

P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Software\AI\帝国项目\_build\native2\app_entry.dist\aoe2mod-engine.exe"
d = open(P, "rb").read()

pe = struct.unpack_from("<I", d, 0x3C)[0]
assert d[pe:pe + 4] == b"PE\x00\x00", "not a PE"
nsec = struct.unpack_from("<H", d, pe + 6)[0]
optsz = struct.unpack_from("<H", d, pe + 20)[0]
opt = pe + 24
magic = struct.unpack_from("<H", d, opt)[0]
ddoff = opt + (112 if magic == 0x20B else 96)

secs = []
for i in range(nsec):
    o = pe + 24 + optsz + i * 40
    name = d[o:o + 8].rstrip(b"\x00").decode("latin1")
    vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
    secs.append((name, va, vs, rp, rs))


def off(rva):
    for name, va, vs, rp, rs in secs:
        if va <= rva < va + max(vs, rs):
            return rp + (rva - va)
    return None


def cstr(rva):
    o = off(rva)
    if o is None:
        return None
    end = d.index(b"\x00", o)
    return d[o:end].decode("latin1", "replace")


def dump_table(label, rva):
    print("\n== %s (rva 0x%X) ==" % (label, rva))
    if not rva:
        print("   (empty)")
        return
    o = off(rva)
    while True:
        ent = d[o:o + 20]
        if len(ent) < 20 or ent == b"\x00" * 20:
            break
        oft, ts, fc, name_rva, ft = struct.unpack("<IIIII", ent)
        nm = cstr(name_rva)
        print("   %s" % nm)
        o += 20


imp_rva = struct.unpack_from("<I", d, ddoff + 8)[0]
delay_rva = struct.unpack_from("<I", d, ddoff + 104)[0]
dump_table("static imports", imp_rva)

# delay load descriptors are 8 dwords each
print("\n== delay-load imports (rva 0x%X) ==" % delay_rva)
if delay_rva:
    o = off(delay_rva)
    while True:
        ent = d[o:o + 32]
        if len(ent) < 32 or ent == b"\x00" * 32:
            break
        attrs, name_rva = struct.unpack_from("<II", ent, 0)
        nm = cstr(name_rva)
        # bit 0 of attrs == 1 means RVA-based
        print("   %s   (attrs=0x%X, %s)" % (nm, attrs, "RVA" if attrs & 1 else "VA"))
        o += 32
else:
    print("   (none)")

print("\nsections:", [s[0] for s in secs])

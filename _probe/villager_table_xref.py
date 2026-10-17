"""Is the exe's villager variant table actually REFERENCED by code, or is it
coincidental data that merely looks like a table?

A table nothing reads is not an authority.  This resolves the file offsets to
RVAs via the PE section headers and then hunts for RIP-relative references
(`lea reg, [rip+disp32]` / `mov reg, [rip+disp32]`) whose target is the table.

Output answers one question: does the engine know this table exists?
"""
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()

# --- PE sections -----------------------------------------------------------
pe = struct.unpack_from("<I", data, 0x3C)[0]
assert data[pe:pe + 4] == b"PE\0\0", "not a PE"
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
image_base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
opt = pe + 24
sections = []
off = opt + optsz
for i in range(nsec):
    e = off + i * 40
    name = data[e:e + 8].rstrip(b"\0").decode("ascii", "replace")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, e + 8)
    sections.append((name, vaddr, vsize, rawptr, rawsize))
    print("%-10s VA 0x%08X vsize 0x%08X  raw 0x%08X size 0x%08X"
          % (name, vaddr, vsize, rawptr, rawsize))
print("image_base 0x%X  entry 0x%X" % (image_base, struct.unpack_from("<I", data, opt + 16)[0]))


def foff_to_rva(fo):
    for name, va, vs, rp, rs in sections:
        if rp <= fo < rp + rs:
            return va + (fo - rp)
    return None


TABLES = [0x032B1DD0, 0x03232E30]
for t in TABLES:
    rva = foff_to_rva(t)
    print()
    print("=== table at file 0x%08X -> RVA 0x%08X -> VA 0x%X ===" % (t, rva, image_base + rva))
    # hunt RIP-relative refs: disp32 where next_insn + disp == rva
    refs = []
    for fo in range(0, len(data) - 7):
        disp = struct.unpack_from("<i", data, fo + 3)[0]
        if (fo + 7) + disp == rva:
            # sanity: preceding bytes look like an instruction with a modrm
            b1 = data[fo + 2]
            if 0x05 <= b1 <= 0x3D:            # modrm with mod=00, rm=101 (rip-rel)
                refs.append(fo)
    print("   RIP-relative references found: %d" % len(refs))
    for fo in refs[:20]:
        r = foff_to_rva(fo)
        print("     file 0x%08X (rva 0x%08X): %s" % (fo, r, data[fo - 3:fo + 7].hex(" ", 1)))
    if not refs:
        # try absolute immediate (some tables are referenced by full 64-bit imm)
        tgt = image_base + rva
        b = struct.pack("<Q", tgt)
        print("   absolute 8-byte references: %d" % data.count(b))
        b2 = struct.pack("<I", rva)
        print("   32-bit rva immediate occurrences: %d" % data.count(b2))

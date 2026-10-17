"""Index AoE2DE_s.exe: locate PE sections, then find candidate literals.
Read-only. Prints offsets + hexdump context. No game launch.
"""
import os, re, struct, sys, json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
EXE  = os.path.join(GAME, "AoE2DE_s.exe")

buf = open(EXE, "rb").read()
print("exe size:", len(buf))
assert buf[:2] == b"MZ"

peoff = struct.unpack_from("<I", buf, 0x3C)[0]
print("e_lfanew:", hex(peoff), buf[peoff:peoff+4])
nsec = struct.unpack_from("<H", buf, peoff + 6)[0]
optsz = struct.unpack_from("<H", buf, peoff + 20)[0]
print("num sections:", nsec, "opt hdr size:", optsz)
magic = struct.unpack_from("<H", buf, peoff + 24)[0]
print("opt magic:", hex(magic), "(0x20b = PE32+)")
imgbase = struct.unpack_from("<Q", buf, peoff + 24 + 24)[0] if magic == 0x20b else struct.unpack_from("<I", buf, peoff + 24 + 28)[0]
print("ImageBase:", hex(imgbase))

secoff = peoff + 24 + optsz
secs = []
for i in range(nsec):
    o = secoff + i * 40
    name = buf[o:o+8].rstrip(b"\0").decode("latin1")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", buf, o + 8)
    secs.append(dict(name=name, vsize=vsize, vaddr=vaddr, rawsize=rawsize, rawptr=rawptr))
    print(f"  {name:10s} VA={vaddr:#010x} VSize={vsize:#x} Raw={rawptr:#010x} RawSize={rawsize:#x}")

json.dump(secs, open(os.path.join(OUT, "exe_sections.json"), "w"), indent=1)

def va_of(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["name"], s["vaddr"] + (off - s["rawptr"])
    return None, None

def off_of_va(va):
    for s in secs:
        if s["vaddr"] <= va < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["name"], s["rawptr"] + (va - s["vaddr"])
    return None, None

# candidate needles
needles = [b"Pompeii", b"pompeii", b"POMPEII", b"modes", b"modes\\", b"/modes",
           b"use_modes_path_for_mods", b"storage_point_list", b"Pompeii.json",
           b"mod-status.json", b"info.json", b"return_of_rome", b"ReturnOfRome",
           b"Return of Rome", b"RoR", b"ModesPath"]

report = {}
print("\n=== NEEDLE SCAN (all sections) ===")
for n in needles:
    hits = []
    start = 0
    while True:
        i = buf.find(n, start)
        if i < 0: break
        sec, va = va_of(i)
        hits.append((i, sec, va))
        start = i + 1
    report[n.decode("latin1")] = hits
    print(f"{n!r}: {len(hits)} hits")
    for (i, sec, va) in hits[:80]:
        print(f"    fileOff={i:#x} sec={sec} VA={hex(va) if va else None}")

json.dump({k: v for k, v in report.items()}, open(os.path.join(OUT, "exe_needle_hits.json"), "w"), indent=1)
print("\nwrote exe_needle_hits.json")

# -*- coding: utf-8 -*-
"""Is the failing exe actually a complete PE, or was it truncated on write?

0xC0000135 (`STATUS_DLL_NOT_FOUND`) is what Windows reports when it cannot
resolve an import, but a file whose section table points past EOF produces the
same symptom for a different reason.  Compare the two side by side: the exe that
fails (`aoe2mod-engine.exe`) and one that runs (`t7.exe`).
"""
import os
import struct

CASES = [
    ("FAILS", r"D:\Software\AI\帝国项目\_build\native2\app_entry.dist\aoe2mod-engine.exe"),
    ("WORKS", r"D:\Software\AI\_nktest2\out\t7.dist\t7.exe"),
    ("WORKS", r"D:\Software\AI\_nktest\out\hello.dist\hello.exe"),
]

for label, path in CASES:
    print("=" * 70)
    print(label, path)
    if not os.path.isfile(path):
        print("  missing")
        continue
    size = os.path.getsize(path)
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\x00\x00":
        print("  NOT A PE (sig %r at 0x%X)" % (d[pe:pe + 4], pe))
        continue
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    print("  size %d, PE at 0x%X, %d sections, magic 0x%X" % (size, pe, nsec, magic))

    worst = 0
    for i in range(nsec):
        o = pe + 24 + optsz + i * 40
        name = d[o:o + 8].rstrip(b"\x00").decode("latin1", "replace")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        end = rp + rs
        worst = max(worst, end)
        flag = ""
        if end > size:
            flag = "  <-- PAST EOF by %d bytes" % (end - size)
        print("    %-10s va=0x%08X vsize=%-9d rawptr=0x%08X rawsize=%-9d end=%d%s"
              % (name, va, vs, rp, rs, end, flag))
    print("  furthest section end: %d   file size: %d   %s"
          % (worst, size, "OK" if worst <= size else "TRUNCATED"))
    # also: does the file end where a finished build should?
    print("  trailing 16 bytes: %r" % d[-16:])

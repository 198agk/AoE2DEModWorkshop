# -*- coding: utf-8 -*-
"""Dump the .rsrc manifest of a failing vs a working Nuitka exe.

`fail - works` in the PE layout was only 6,656 bytes of code and 4 bytes of
.eh_fram, so the executables are near-identical.  The one thing that differs in
kind is `.rsrc`: subsystem / manifest / icon live there, and a manifest naming an
assembly the machine cannot resolve produces STATUS_DLL_NOT_FOUND at process
start without ever running WinMain.
"""
import struct
import sys

CASES = [
    ("FAILS", r"D:\Software\AI\帝国项目\_build\native2\app_entry.dist\aoe2mod-engine.exe"),
    ("WORKS", r"D:\Software\AI\_nktest2\out\t7.dist\t7.exe"),
]


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    out = []
    for i in range(nsec):
        o = pe + 24 + optsz + i * 40
        name = d[o:o + 8].rstrip(b"\x00").decode("latin1", "replace")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        out.append((name, va, vs, rp, rs))
    return out


for label, path in CASES:
    print("=" * 74)
    print(label, path)
    d = open(path, "rb").read()
    for name, va, vs, rp, rs in sections(d):
        if name != ".rsrc":
            continue
        blob = d[rp:rp + rs]
        print("  .rsrc %d bytes; printable strings:" % len(blob))
        # pull every printable run out of the resource blob
        cur = bytearray()

        def flush():
            if len(cur) >= 8:
                try:
                    s = cur.decode("utf-8")
                except UnicodeDecodeError:
                    s = cur.decode("latin1")
                print("    %r" % s[:300])
            cur.clear()

        for b in blob:
            if 32 <= b < 127:
                cur.append(b)
            else:
                flush()
        flush()

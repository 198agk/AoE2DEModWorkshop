# -*- coding: utf-8 -*-
"""Scan AoE2DE_s.exe for font-table strings (ASCII + UTF-16LE)."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, re, sys, io, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "hud_render")

data = open(EXE, "rb").read()
print("exe size", len(data))

NEEDLES = [
    b"basic_bold_16", b"combined_sansserif", b"combined.box", b"georgia_european",
    b"centrg_", b"centbd_", b"combined.txt", b"combined_", b"lblack",
    b"FontIndex", b"PointSize", b"TextOutlineWidth", b"TextOutlineColor",
    b"Font File Atlas Summary", b"Source Font Pixel Size",
    b".fnt", b"font_vs", b"font_ps", b"mdsf_font",
    b"papyrus", b"vineritc", b"poorich", b"lcallig", b"lbrite", b"georgia",
    b"comic", b"Jost",
]

rep = io.StringIO()
rep.write("EXE: %s  (%d bytes)\n" % (EXE, len(data)))

found_single = {}
for n in NEEDLES:
    hits = []
    start = 0
    while True:
        i = data.find(n, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
        if len(hits) > 60:
            break
    found_single[n.decode()] = hits
    rep.write("\n=== ASCII %-26s hits=%d\n" % (n.decode(), len(hits)))
    for h in hits[:12]:
        lo = max(0, h - 70); hi = min(len(data), h + 90)
        ctx = data[lo:hi]
        ctx = bytes(c if 32 <= c < 127 else 46 for c in ctx)
        rep.write("  @0x%08X  %s\n" % (h, ctx.decode("ascii")))

# UTF-16LE scan
rep.write("\n\n########## UTF-16LE ##########\n")
found_u16 = {}
for n in NEEDLES:
    nn = n.decode().encode("utf-16-le")
    hits = []
    start = 0
    while True:
        i = data.find(nn, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
        if len(hits) > 60:
            break
    found_u16[n.decode()] = hits
    rep.write("\n=== UTF16 %-26s hits=%d\n" % (n.decode(), len(hits)))
    for h in hits[:12]:
        lo = max(0, h - 90); hi = min(len(data), h + 130)
        ctx = data[lo:hi]
        try:
            s = ctx.decode("utf-16-le", errors="replace")
        except Exception:
            s = "?"
        rep.write("  @0x%08X  %s\n" % (h, "".join(ch if ch.isprintable() else "." for ch in s)))

open(os.path.join(OUT, "exe_font_scan.txt"), "w", encoding="utf-8").write(rep.getvalue())
json.dump({"ascii": found_single, "utf16": found_u16},
          open(os.path.join(OUT, "exe_font_scan.json"), "w"), indent=1)
print(rep.getvalue()[:9000])

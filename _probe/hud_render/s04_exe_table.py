# -*- coding: utf-8 -*-
"""Dump exe region around the font-name table; validate combined.box record layout."""
import os, io, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
FD = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
data = open(EXE, "rb").read()
rep = io.StringIO()

def hexdump(off, n, base=None):
    base = base if base is not None else off
    for i in range(off, off + n, 16):
        chunk = data[i:i+16]
        hx = " ".join("%02X" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        rep.write("  %08X  %-47s  %s\n" % (i, hx, asc))

# region around the font table found at 0x032E6DA0
rep.write("=== hexdump 0x032E6D40 .. 0x032E6E60 ===\n")
hexdump(0x032E6D40, 0x120)

# Render the region as a NUL-separated string list to see the table
rep.write("\n=== NUL-separated UTF-8 strings in 0x032E6C00..0x032E6F00 ===\n")
seg = data[0x032E6C00:0x032E6F00]
for s in seg.split(b"\x00"):
    if s:
        rep.write("   [%s]\n" % s.decode("utf-8", "replace"))

# Look for the specific font filenames the exe might reference with directories
for needle in [b"fonts/", b"fonts\\", b"combined", b"_sansserif", b"basic_bold",
               b"georgia_euro", b".box", b".fnt"]:
    hits = []
    st = 0
    while len(hits) < 40:
        i = data.find(needle, st)
        if i < 0: break
        hits.append(i); st = i + 1
    rep.write("\n=== needle %r : %d hits (cap40)\n" % (needle, len(hits)))
    for h in hits:
        lo = max(0, h-48); hi = min(len(data), h+64)
        ctx = bytes(c if 32 <= c < 127 else 46 for c in data[lo:hi])
        rep.write("  @0x%08X %s\n" % (h, ctx.decode("ascii")))

# ---- combined.box layout validation ----
bb = open(os.path.join(FD, "combined.box"), "rb").read()
ver, nglyph, npages = struct.unpack_from("<III", bb, 0)
ppem, = struct.unpack_from("<f", bb, 12)
rep.write("\n\n=== combined.box header: version=%d glyphs=%d pages=%d ppem=%.3f size=%d ===\n"
          % (ver, nglyph, npages, ppem, len(bb)))
REC = 40
HDR = 16
expect = HDR + nglyph * REC
rep.write("HDR=%d REC=%d -> 16+n*40 = %d ; file=%d ; trailing=%d (=n*4? %d)\n"
          % (HDR, REC, expect, len(bb), len(bb) - expect, nglyph * 4))

# glyph records, in glyph-index order
recs = []
for i in range(nglyph):
    o = HDR + i * REC
    W, H, u0, u1, v0, v1 = struct.unpack_from("<6f", bb, o)
    atlas, = struct.unpack_from("<I", bb, o + 24)
    XO, YO, adv = struct.unpack_from("<3f", bb, o + 28)
    recs.append(dict(gi=i, W=W, H=H, u0=u0, u1=u1, v0=v0, v1=v1,
                     atlas=atlas, XO=XO, YO=YO, adv=adv))

# trailing block = cmap: array of (codepoint u16, glyph_index u16)
tail = bb[expect:]
ncmap = len(tail) // 4
cmap = []
for i in range(ncmap):
    cp, gi = struct.unpack_from("<HH", tail, i * 4)
    cmap.append((cp, gi))
rep.write("cmap entries=%d ; first 12=%s\n" % (len(cmap), cmap[:12]))
rep.write("cmap cp min=%d max=%d ; gi min=%d max=%d\n"
          % (min(c[0] for c in cmap), max(c[0] for c in cmap),
             min(c[1] for c in cmap), max(c[1] for c in cmap)))
code_of = {gi: cp for cp, gi in cmap}
for r in recs:
    r["code"] = code_of.get(r["gi"], -1)
codes = [r["code"] for r in recs]
rep.write("resolved codes: %d ; -1 (unmapped)=%d ; min=%d max=%d unique=%d\n"
          % (len(codes), codes.count(-1), min(codes), max(codes), len(set(codes))))
rep.write("rec[0]=%s\nrec[1]=%s\nrec[2]=%s\n" % (recs[0], recs[1], recs[2]))
for ch in "Aa0 .,!":
    r = next((x for x in recs if x["code"] == ord(ch)), None)
    rep.write("  glyph %-4r %s\n" % (ch, r))

# cross-check against combined.txt order
import re as _re
txt = open(os.path.join(FD, "combined.txt"), "r", encoding="utf-8", errors="replace").read()
lines = [l for l in txt.splitlines() if l.startswith("Glyph -")]
rep.write("combined.txt glyph lines=%d (header says %d) ; box cmap=%d\n"
          % (len(lines), nglyph, len(cmap)))
json.dump(recs, open(os.path.join(OUT, "combined_box_records.json"), "w"), indent=1)
json.dump(cmap, open(os.path.join(OUT, "combined_box_cmap.json"), "w"), indent=1)

# dims of combined_0000.png
from PIL import Image
for nm in ["combined_0000.png", "combined_0005.png", "combined_sansserif_0000.png",
           "georgia_european_0000.png"]:
    p = os.path.join(FD, nm)
    if os.path.exists(p):
        im = Image.open(p)
        rep.write("PNG %-28s %s %s\n" % (nm, im.size, im.mode))
# dims of the DDS files
for nm in ["combined_0000.DDS", "basic_bold_16.dds", "georgia_european_0000.DDS"]:
    p = os.path.join(FD, nm)
    if os.path.exists(p):
        try:
            im = Image.open(p)
            rep.write("DDS %-28s %s %s\n" % (nm, im.size, im.mode))
        except Exception as e:
            rep.write("DDS %-28s UNREADABLE by Pillow: %s\n" % (nm, e))
        with open(p, "rb") as fh:
            rep.write("     header: %s\n" % fh.read(4))
            fh.seek(4)
            rep.write("     size=%d\n" % os.path.getsize(p))

open(os.path.join(OUT, "exe_font_table.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

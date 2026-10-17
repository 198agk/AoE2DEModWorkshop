# -*- coding: utf-8 -*-
"""Parse resources\_common\fonts\basic_bold_16.fnt and combined.box; cross-check with combined.txt."""
import os, struct, io, json, collections, re

FD = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
rep = io.StringIO()

# ---------- basic_bold_16.fnt ----------
p = os.path.join(FD, "basic_bold_16.fnt")
b = open(p, "rb").read()
rep.write("=== basic_bold_16.fnt  size=%d ===\n" % len(b))
rep.write("first 64 bytes hex:\n")
for i in range(0, 64, 16):
    rep.write("  %04X  %s\n" % (i, " ".join("%02X" % c for c in b[i:i+16])))
rep.write("magic: %r\n" % b[:4])

# try common multi-byte bitmap font header parse
# offset 4..: appears to be a version then counts
u32 = lambda o: struct.unpack_from("<I", b, o)[0]
u16 = lambda o: struct.unpack_from("<H", b, o)[0]
rep.write("u32 @4 =%d @8 =%d @12=%d @16=%d @20=%d\n" % (u32(4), u32(8), u32(12), u32(16), u32(20)))
rep.write("u16 @4 =%d @6=%d @8=%d @10=%d @12=%d @14=%d\n" % (u16(4), u16(6), u16(8), u16(10), u16(12), u16(14)))

# Heuristic: find total glyph count candidates by scanning first 64 bytes as u16/u32
rep.write("\nfirst 32 u32 values:\n")
for i in range(0, 128, 4):
    if i + 4 <= len(b):
        rep.write("  off %3d (0x%02X): %d\n" % (i, i, u32(i)))

# ---------- combined.txt ----------
ptxt = os.path.join(FD, "combined.txt")
txt = open(ptxt, "r", encoding="utf-8", errors="replace").read()
lines = txt.splitlines()
rep.write("\n\n=== combined.txt size=%d lines=%d ===\n" % (len(txt), len(lines)))
for l in lines[:12]:
    rep.write("  | " + l + "\n")

gr = re.compile(r"Glyph\s*-\s*(\d+)\s+W\(([-\d.]+)\),\s*H\(([-\d.]+)\),\s*UV\(([-\d.]+),\s*([-\d.]+)\),\s*ST\(([-\d.]+),\s*([-\d.]+)\),\s*Atlas\((\d+)\),\s*XO\(([-\d.]+)\),\s*YO\(([-\d.]+)\),\s*HAdvance\(([-\d.]+)\)")
glyphs = []
for l in lines:
    m = gr.search(l)
    if m:
        g = m.groups()
        glyphs.append(dict(code=int(g[0]), W=float(g[1]), H=float(g[2]),
                           u0=float(g[3]), v0=float(g[4]), u1=float(g[5]), v1=float(g[6]),
                           atlas=int(g[7]), XO=float(g[8]), YO=float(g[9]), adv=float(g[10])))
rep.write("\nparsed glyphs from combined.txt: %d\n" % len(glyphs))
rep.write("codes range: %d .. %d\n" % (min(g["code"] for g in glyphs), max(g["code"] for g in glyphs)))
rep.write("atlas pages used: %s\n" % sorted(set(g["atlas"] for g in glyphs)))
rep.write("sample: %s\n" % json.dumps(glyphs[:3], ensure_ascii=False))
# lines that are not glyph lines
non = [l for l in lines if l.strip() and not gr.search(l)]
rep.write("\nnon-glyph lines (%d):\n" % len(non))
for l in non[:40]:
    rep.write("  | " + l + "\n")

# ---------- combined.box ----------
pb = os.path.join(FD, "combined.box")
bb = open(pb, "rb").read()
rep.write("\n\n=== combined.box size=%d ===\n" % len(bb))
rep.write("bytes/record if %d glyphs: %.3f\n" % (len(glyphs), len(bb) / max(1, len(glyphs))))
rep.write("first 128 bytes hex:\n")
for i in range(0, 128, 16):
    rep.write("  %04X  %s\n" % (i, " ".join("%02X" % c for c in bb[i:i+16])))

open(os.path.join(OUT, "font_parse.txt"), "w", encoding="utf-8").write(rep.getvalue())
json.dump(glyphs[:50], open(os.path.join(OUT, "combined_txt_sample.json"), "w"), indent=1)
print(rep.getvalue()[:9000])

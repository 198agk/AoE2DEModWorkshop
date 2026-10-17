# -*- coding: utf-8 -*-
"""Settle: how does the DE engine apply PLAYER COLOUR to unit sprites?

Competing stories:
  S_palette (graphics survey): DE sprites store palette indices; recolouring a
      unit = editing playercolor_*.pal (JASC text).  "Player colour is a
      palette swap, not a shader."
  S_mask : DE unit sprites carry a single-channel player-colour MASK; the
      engine multiplies it by the team colour declared in spritecolors.json,
      gated by the material blend mode AlphaPlayerColor.  The .pal files are
      legacy.

Evidence gathered so far AGAINST S_palette:
  * palettes.conf "New Unit player colors" ids 64..71 ALL map to
    playercolor_black.pal -- if new units resolved colour through the palette
    table they would all render black.
  * no installed mod ships any .pal/.palx/palettes.conf.
  * exe references `spritecolors`, `TeamColors`, `OutlineColors`, `FloatRGBA`,
    `HexColor` -- and 1205 materials declare Blend AlphaPlayerColor.

This script closes the case with two independent measurements:
  E1  render main + playercolor layers of real units and check whether the
      player-colour layer is a spatially-coherent MASK over the art
      (mask hypothesis) -- and that it is single-channel BC4.
  E2  for each player colour in spritecolors.json, ask what the mask would
      produce if multiplied; and confirm the colour set matches the .pal
      palettes only for the LEGACY ids.
  E3  count Blend modes across materials.json to size AlphaPlayerColor usage.
Read-only.
"""
import json
import os
import struct
from collections import Counter
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
PAL = os.path.join(GAME, "resources", "_common", "palettes")
WID = os.path.join(GAME, "widgetui")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\playerclr"
os.makedirs(OUT, exist_ok=True)

u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
i16 = lambda b, o: struct.unpack_from("<h", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]

BITS = [(0, "main", False), (1, "shadow", True), (2, "unknown2", False),
        (3, "damage", False), (4, "playercolor", True)]


def bc1(blk):
    c0, c1 = struct.unpack_from("<HH", blk, 0)
    idx = struct.unpack_from("<I", blk, 4)[0]
    ch = lambda c: ((c >> 11 & 31) * 255 // 31, (c >> 5 & 63) * 255 // 63,
                    (c & 31) * 255 // 31, 255)
    a, b2 = ch(c0), ch(c1)
    c0_, c1_ = c0, c1
    if c0_ > c1_:
        c2 = tuple((2 * a[i] + b2[i]) // 3 for i in range(3)) + (255,)
        c3 = tuple((a[i] + 2 * b2[i]) // 3 for i in range(3)) + (255,)
    else:
        c2 = tuple((a[i] + b2[i]) // 2 for i in range(3)) + (255,)
        c3 = (0, 0, 0, 0)
    lut = [a, b2, c2, c3]
    return [lut[idx >> (2 * k) & 3] for k in range(16)]


def bc4(blk):
    c0, c1 = blk[0], blk[1]
    if c0 > c1:
        lut = [c0, c1] + [((7 - i) * c0 + i * c1) // 7 for i in range(1, 7)]
    else:
        lut = [c0, c1] + [((5 - i) * c0 + i * c1) // 5 for i in range(1, 5)] + [0, 255]
    v = int.from_bytes(blk[2:8], "little")
    return [lut[v >> (3 * k) & 7] for k in range(16)]


def decode_layer(b, L, x, y, w, h, isbc4):
    """Decode a layer's blocks into an (w x h) RGBA / mask array."""
    bw, bh = (w + 3) // 4, (h + 3) // 4
    o = L["pixel_off"]
    clen = u16(b, o)
    o += 2
    cmds = [(u8(b, o + 2 * i), u8(b, o + 2 * i + 1)) for i in range(clen)]
    o += 2 * clen
    total = sum(c[1] for c in cmds)
    im = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
    px = im.load()
    bx = by = 0
    for skip, draw in cmds:
        for _ in range(skip):
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
        for _ in range(draw):
            blk = b[o:o + 8]
            o += 8
            vals = bc4(blk) if isbc4 else [c for c in bc1(blk)]
            for j in range(4):
                yy = by * 4 + j
                if yy >= bh * 4:
                    continue
                for i in range(4):
                    xx = bx * 4 + i
                    if xx >= bw * 4:
                        continue
                    if isbc4:
                        v = vals[j * 4 + i]
                        px[xx, yy] = (v, v, v, 255)
                    else:
                        px[xx, yy] = vals[j * 4 + i]
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
    return im.crop((0, 0, w, h)), isbc4


def frame0(path):
    b = open(path, "rb").read()
    nf = u16(b, 6)
    off = 16
    cw, ch = u16(b, off), u16(b, off + 2)
    ft = u8(b, off + 8)
    off += 12
    layers = []
    for bit, name, isbc4 in BITS:
        if not (ft & (1 << bit)):
            continue
        clen = u32(b, off)
        body = off + 4
        L = dict(name=name, clen=clen, isbc4=isbc4, pixel_off=body + 10)
        if name in ("main", "shadow"):
            x1, y1, x2, y2 = (u16(b, body), u16(b, body + 2),
                              u16(b, body + 4), u16(b, body + 6))
            L.update(x=x1, y=y1, w=x2 - x1, h=y2 - y1)
        else:
            L.update(x=0, y=0, w=cw, h=ch)
        off += clen + ((4 - clen % 4) % 4)
        layers.append(L)
    return b, cw, ch, ft, layers


print("=" * 72)
print("E1  render main + playercolor layers, check mask coherence")
print("=" * 72)
tiles = []
for name in ("u_arc_archer_idlea_x1.sld", "u_cav_knight_idlea_x1.sld",
             "u_inf_militia_idlea_x1.sld"):
    p = os.path.join(GP, name)
    b, cw, ch, ft, layers = frame0(p)
    main = next((l for l in layers if l["name"] == "main"), None)
    pc = next((l for l in layers if l["name"] == "playercolor"), None)
    print("%s ft=0x%02x canvas=%dx%d layers=%s"
          % (name, ft, cw, ch, [l["name"] for l in layers]))
    if main:
        try:
            im, _ = decode_layer(b, main, main["x"], main["y"], main["w"], main["h"], False)
            print("   main   %dx%d  opaque(alpha>0)=%d/%d"
                  % (im.size[0], im.size[1],
                     sum(1 for q in im.getdata() if q[3] > 0), im.size[0] * im.size[1]))
            tiles.append(("main:" + name[:22], im))
        except Exception as e:
            print("   main decode err", e)
    if pc:
        try:
            im, isbc4 = decode_layer(b, pc, pc["x"], pc["y"], pc["w"], pc["h"], pc["isbc4"])
            d = list(im.getdata())
            nz = [q[0] for q in d if q[0] > 0]
            print("   pc(mask?) %dx%d comp=%s nonzero=%d/%d  min=%s max=%s distinct=%d"
                  % (im.size[0], im.size[1], "BC4" if isbc4 else "BC1",
                     len(nz), len(d), min(nz) if nz else None,
                     max(nz) if nz else None, len(set(nz))))
            tiles.append(("pc:" + name[:22], im))
        except Exception as e:
            print("   pc decode err", e)

# contact sheet: main | pc | main tinted by pc * red / blue
print()
sheet_w = sum(t[1].size[0] for t in tiles) + 10 * len(tiles)
sheet_h = max(t[1].size[1] for t in tiles)
sheet = Image.new("RGBA", (sheet_w, sheet_h), (40, 40, 40, 255))
xx = 0
for nm, im in tiles:
    sheet.alpha_composite(im, (xx, 0))
    xx += im.size[0] + 10
sheet.save(os.path.join(OUT, "playerclr_layers.png"))

print()
print("=" * 72)
print("E2  spritecolors.json colour set vs the .pal palettes")
print("=" * 72)
sc = json.load(open(os.path.join(PAL, "spritecolors.json"), encoding="utf-8-sig"))
tcols = {}
for k, v in sc["TeamColors"].items():
    f = v["FloatRGBA"]
    tcols[k] = (round(f["r"] * 255), round(f["g"] * 255), round(f["b"] * 255))
print("  spritecolors TeamColors (RGB 0-255):")
for k, v in tcols.items():
    print("     %-10s %s" % (k, v))
print()
conf = open(os.path.join(PAL, "palettes.conf"), encoding="latin1").read()
ids_new, ids_legacy = [], []
for line in conf.split("\n"):
    line = line.split("//")[0].strip()
    if not line or "," not in line:
        continue
    a, f = [x.strip() for x in line.split(",", 1)]
    if not a.isdigit():
        continue
    if 64 <= int(a) <= 71:
        ids_new.append((int(a), f))
    if 55 <= int(a) <= 62:
        ids_legacy.append((int(a), f))
print("  NEW-unit player colour ids 64..71 ->", sorted(set(f for _, f in ids_new)))
print("  LEGACY player colour ids 55..62 ->")
for i, f in ids_legacy:
    p = os.path.join(PAL, f)
    first = open(p, "rb").read().split(b"\r\n")[3] if os.path.exists(p) else b"?"
    print("     id %d  %-24s first colour = %r" % (i, f, first))

print()
print("=" * 72)
print("E3  materials.json Blend usage")
print("=" * 72)
mat = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8-sig"))
bl = Counter()
for m in mat["Materials"]:
    bl[m.get("Blend", "?")] += 1
print("  Blend histogram:", dict(bl))
apc = [m for m in mat["Materials"] if m.get("Blend") == "AlphaPlayerColor"]
print("  AlphaPlayerColor materials:", len(apc))
print("  sample names:", [m["Name"] for m in apc[:12]])

# do AlphaPlayerColor materials point at unit sprites?
atlas = {}
for a in mat["AtlasTextures"]:
    for t in a.get("Textures", []):
        atlas.setdefault(a["Name"], {})[t.get("RefName")] = t.get("FileName")
hit_unit = 0
for m in apc:
    fn = atlas.get(m.get("AtlasRef"), {}).get(m.get("TextureRef") or m.get("Name"))
    if fn and ("ingame/units" in fn or "ingame/buildings" in fn):
        hit_unit += 1
print("  AlphaPlayerColor materials resolving to ingame units/buildings art:", hit_unit)

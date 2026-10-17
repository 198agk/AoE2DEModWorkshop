#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a42_render_shipped.py -- DECISIVE VISUAL CHECK of the shipped index.

Every earlier visual check (a26/a27) rendered the LOOSE texture file.  This one renders
the atlas slice that the SHIPPED index_units.json actually names, reading the atlas and
the UV rect OUT OF THE DELIVERABLE -- so it verifies the deliverable, not the rule.

Rows (top to bottom), each entry = .dat unit id, taken from the deliverable itself:
   Archer 4 | Villager 83 | Knight 38 | Militia 74 | Spearman 93
   Monk 125 | Trebuchet 42 | Town Center 71 | Barracks 12 | Castle 82
   House 70 | Farm 50 | Watch Tower 79 | Longbowman 8 | Mangonel 280

If a row shows the WRONG thing, the deliverable is wrong.  Uses the SD atlas
(DefaultSource, BC3/DXT5) because the HD tier is BC7, which this decoder cannot read.
"""
import json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}

ROWS = [(4, "Archer"), (83, "Villager"), (38, "Knight"), (74, "Militia"),
        (93, "Spearman"), (125, "Monk"), (42, "Trebuchet"), (71, "Town Center"),
        (12, "Barracks"), (82, "Castle"), (70, "House"), (50, "Farm"),
        (79, "Watch Tower"), (8, "Longbowman"), (280, "Mangonel")]


def hdr(p):
    b = open(p, "rb").read(160)
    return {"w": struct.unpack_from("<I", b, 16)[0], "h": struct.unpack_from("<I", b, 12)[0],
            "fourcc": b[84:88].decode("latin1").strip("\x00"),
            "off": 148 if b[84:88] == b"DX10" else 128}


def _c565(c0, c1, d1):
    def ex(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; bl = c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2))
    a, b2 = ex(c0), ex(c1)
    if not d1 or c0 > c1:
        return [a, b2, tuple((2 * a[k] + b2[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b2[k]) // 3 for k in range(3))]
    return [a, b2, tuple((a[k] + b2[k]) // 2 for k in range(3)), (0, 0, 0)]


def _a5(blk, i):
    a0, a1 = blk[0], blk[1]
    if a0 > a1:
        tab = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    else:
        tab = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
    return tab[(int.from_bytes(blk[2:8], "little") >> (3 * i)) & 7]


_CACHE = {}


def dec(p, lx, ly, w, h):
    if p not in _CACHE:
        d = hdr(p)
        _CACHE[p] = (d, open(p, "rb").read()[d["off"]:])
    d, raw = _CACHE[p]
    mode = d["fourcc"]
    W = d["w"]
    bs = 8 if mode == "DXT1" else 16
    bw = (W + 3) // 4
    out = bytearray(w * h * 4)
    for by in range(max(0, ly) // 4, (ly + h - 1) // 4 + 1):
        for bx in range(max(0, lx) // 4, (lx + w - 1) // 4 + 1):
            o = (by * bw + bx) * bs
            blk = raw[o:o + bs]
            if len(blk) < bs:
                continue
            if mode == "DXT1":
                c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                cols = _c565(c0, c1, True)
            else:
                c0, c1 = struct.unpack_from("<HH", blk, 8)
                bits = struct.unpack_from("<I", blk, 12)[0]
                cols = _c565(c0, c1, False)
            for py in range(4):
                y = by * 4 + py
                if y < ly or y >= ly + h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x < lx or x >= lx + w:
                        continue
                    i = py * 4 + px
                    idx = (bits >> (2 * i)) & 3
                    r, g, bl = cols[idx]
                    a = 0 if (mode == "DXT1" and idx == 3 and c0 <= c1) else (
                        255 if mode == "DXT1" else (_a5(blk, i) if mode == "DXT5" else
                                                   (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17))
                    o2 = ((y - ly) * w + x - lx) * 4
                    out[o2:o2 + 4] = bytes((r, g, bl, a))
    return w, h, bytes(out)


def png(path, W, H, rows):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    data = b"".join(b"\x00" + r for r in rows)
    out = [b"\x89PNG\r\n\x1a\n"]
    for tag, payload in ((b"IHDR", ihdr), (b"IDAT", __import__("zlib").compress(data)),
                         (b"IEND", b"")):
        out.append(struct.pack(">I", len(payload)) + tag + payload +
                   struct.pack(">I", __import__("zlib").crc32(tag + payload) & 0xFFFFFFFF))
    open(path, "wb").write(b"".join(out))


TILE = 128
CANVAS = bytearray(TILE * len(ROWS) * TILE * 4)
print("%-6s %-14s %-16s %-34s %s" % ("id", "expected", "atlas", "RefName", "uv(px in SD atlas)"))
for ri, (uid, want) in enumerate(ROWS):
    r = U.get(str(uid))
    if r is None:
        print("  id %-5d %-14s ABSENT FROM DELIVERABLE" % (uid, want))
        continue
    ic = r["icon"] or {}
    if not ic.get("resolved"):
        print("  id %-5d %-14s NO RESOLVED ICON (why=%s)" % (uid, want, ic.get("why")))
        continue
    atlas = ic["atlas"]
    at = ATLS[atlas]
    src = os.path.join(WID, at["DefaultSource"].replace("/", os.sep))
    d = hdr(src)
    uv = ic["uv"]
    lx = int(round(uv["x1"] * d["w"] + 0.5)); ly = int(round(uv["y1"] * d["h"] + 0.5))
    hx = int(round(uv["x2"] * d["w"] - 0.5)); hy = int(round(uv["y2"] * d["h"] - 0.5))
    w, h = hx - lx + 1, hy - ly + 1
    print("%-6d %-14s %-16s %-34s (%d,%d)-(%d,%d) %dx%d  fourcc=%s %dx%d"
          % (uid, want, atlas, ic.get("RefName"), lx, ly, hx, hy, w, h, d["fourcc"], d["w"], d["h"]))
    if fourcc_w := d["fourcc"]:
        pass
    if d["fourcc"] not in ("DXT1", "DXT5", "DXT3"):
        print("      -> fourcc %s not decodable by this script" % d["fourcc"])
        continue
    _, _, pix = dec(src, lx, ly, w, h)
    # blit scaled into a TILE x TILE cell on a checkerboard so alpha is visible
    for y in range(TILE):
        sy = min(h - 1, y * h // TILE)
        for x in range(TILE):
            sx = min(w - 1, x * w // TILE)
            o = (sy * w + sx) * 4
            r_, g_, b_, a_ = pix[o], pix[o + 1], pix[o + 2], pix[o + 3]
            chk = 200 if ((x // 16 + y // 16) % 2) else 120
            if a_ < 8:
                r_, g_, b_ = chk, chk, chk
            elif a_ < 255:
                f = a_ / 255.0
                r_ = int(r_ * f + chk * (1 - f)); g_ = int(g_ * f + chk * (1 - f))
                b_ = int(b_ * f + chk * (1 - f))
            o2 = ((ri * TILE + y) * TILE + x) * 4
            CANVAS[o2:o2 + 4] = bytes((r_, g_, b_, 255))

out = os.path.join(HERE, "png", "shipped_icon_check.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
png(out, TILE, TILE * len(ROWS), [bytes(CANVAS[y * TILE * 4:(y + 1) * TILE * 4])
                                  for y in range(TILE * len(ROWS))])
print("\nrendered %s  (%dx%d, rows top->bottom: %s)"
      % (out, TILE, TILE * len(ROWS), ", ".join(w for _, w in ROWS)))

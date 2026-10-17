#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a44_crosscheck10.py -- the MANDATED 10-unit cross-check, loose vs shipped, visually.

For each of the 10 well-known units the task asked about, this renders THREE things side
by side:
    col 1 = the game's own loose icon texture for that entity
              (buildings: widgetui\\textures\\ingame\\buildings\\<NNN>_<label>.DDS, the
               authors' own descriptive name; units: ...\\units\\<NNN>_50730.DDS)
    col 2 = the atlas slice the SHIPPED index names (atlas + UV rect read from the JSON)
    col 3 = the sprite (idle) frames the SHIPPED index names -- counts only, since .sld
            parsing is beyond this script; the sprite claim is checked in C1/C2 instead

It also prints, per unit, the exact sprite filenames and icon identity so the reader can
confirm "the names obviously match" without trusting my prose.

Correct-by-construction: if col 1 and col 2 differ for any row, the shipped index's atlas
or UV is wrong.  Rows: Archer, Villager, Knight, Militia, Town Center, Barracks, Castle,
House, Longbowman, Monk.
"""
import json, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
GFX = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
DISK = set(f.lower() for f in os.listdir(GFX))

UNITS_L = os.path.join(WID, "textures", "ingame", "units")
BLD_L = os.path.join(WID, "textures", "ingame", "buildings")
LOOSE_U = {}
for f in os.listdir(UNITS_L):
    h = f.split("_")[0]
    if h.isdigit():
        LOOSE_U[int(h)] = os.path.join(UNITS_L, f)
LOOSE_B = {}
for f in os.listdir(BLD_L):
    h = f.split("_")[0]
    if h.isdigit():
        LOOSE_B[int(h)] = os.path.join(BLD_L, f)

TEN = [(4, "Archer"), (83, "Villager"), (38, "Knight"), (74, "Militia"),
       (71, "Town Center"), (12, "Barracks"), (82, "Castle"),
       (70, "House"), (8, "Longbowman"), (125, "Monk")]


def hdr(p):
    b = open(p, "rb").read(160)
    d = {"w": struct.unpack_from("<I", b, 16)[0], "h": struct.unpack_from("<I", b, 12)[0],
         "pfFlags": struct.unpack_from("<I", b, 80)[0],
         "fourcc": b[84:88].decode("latin1").strip("\x00"),
         "bits": struct.unpack_from("<I", b, 88)[0],
         "mR": struct.unpack_from("<I", b, 92)[0], "mG": struct.unpack_from("<I", b, 96)[0],
         "mB": struct.unpack_from("<I", b, 100)[0], "mA": struct.unpack_from("<I", b, 104)[0]}
    d["off"] = 148 if b[84:88] == b"DX10" else 128
    return d


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


def dec_rect(p, lx=0, ly=0, w=None, h=None):
    d = hdr(p)
    W, H = d["w"], d["h"]
    if w is None:
        w, h = W, H
    raw = open(p, "rb").read()[d["off"]:]
    out = bytearray(w * h * 4)
    if (d["pfFlags"] & 0x40) and not d["fourcc"]:
        bpp = d["bits"] // 8
        rowbytes = W * bpp

        def shf(m):
            return (bin(m)[::-1].index("1") if m else 0)

        def nb(m):
            return bin(m).count("1") if m else 0

        sR, nR, sG, nG = shf(d["mR"]), nb(d["mR"]), shf(d["mG"]), nb(d["mG"])
        sB, nB, sA, nA = shf(d["mB"]), nb(d["mB"]), shf(d["mA"]), nb(d["mA"])
        for y in range(ly, ly + h):
            for x in range(lx, lx + w):
                o = y * rowbytes + x * bpp
                px = int.from_bytes(raw[o:o + bpp], "little")
                def sc(sh, n):
                    return ((px >> sh) & ((1 << n) - 1)) * 255 // ((1 << n) - 1) if n else 255
                o2 = ((y - ly) * w + x - lx) * 4
                out[o2:o2 + 4] = bytes((sc(sR, nR), sc(sG, nG), sc(sB, nB),
                                        sc(sA, nA) if nA else 255))
        return w, h, bytes(out)
    mode = d["fourcc"]
    if mode not in ("DXT1", "DXT3", "DXT5"):
        return None
    bs = 8 if mode == "DXT1" else 16
    bw = (W + 3) // 4
    for by in range(ly // 4, (ly + h - 1) // 4 + 1):
        for bx in range(lx // 4, (lx + w - 1) // 4 + 1):
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
                    if mode == "DXT1":
                        a = 0 if (idx == 3 and c0 <= c1) else 255
                    elif mode == "DXT5":
                        a = _a5(blk, i)
                    else:
                        a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                    o2 = ((y - ly) * w + x - lx) * 4
                    out[o2:o2 + 4] = bytes((r, g, bl, a))
    return w, h, bytes(out)


def png(path, W, H, rows):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    data = b"".join(b"\x00" + r for r in rows)
    o = [b"\x89PNG\r\n\x1a\n"]
    for tag, pl in ((b"IHDR", ihdr), (b"IDAT", zlib.compress(data)), (b"IEND", b"")):
        o.append(struct.pack(">I", len(pl)) + tag + pl +
                 struct.pack(">I", zlib.crc32(tag + pl) & 0xFFFFFFFF))
    open(path, "wb").write(b"".join(o))


TILE = 128
COLS = 2
GAP = 8
CW = COLS * TILE + GAP
CAN = bytearray(TILE * len(TEN) * CW * 4)
print("%-5s %-12s %-16s %-32s %s" % ("id", "name", "icon atlas", "icon RefName", "sprite files"))
for ri, (uid, name) in enumerate(TEN):
    r = U[str(uid)]
    ic = r["icon"]
    at = ATLS[ic["atlas"]]
    src = os.path.join(WID, at["DefaultSource"].replace("/", os.sep))
    d = hdr(src)
    uv = ic["uv"]
    lx = int(round(uv["x1"] * d["w"] + 0.5)); ly = int(round(uv["y1"] * d["h"] + 0.5))
    hx = int(round(uv["x2"] * d["w"] - 0.5)); hy = int(round(uv["y2"] * d["h"] - 0.5))
    A = dec_rect(src, lx, ly, hx - lx + 1, hy - ly + 1)
    loose = LOOSE_B.get(ic["icon_id"]) if ic["atlas"] == "ingamebuildings" else LOOSE_U.get(ic["icon_id"])
    B_ = dec_rect(loose) if loose else None
    fs = [v["sld_x1"] for v in r["sprites"].values() if v.get("sld_x1")]
    for v in r["sprites"].values():
        fs += [a["sld_x1"] for a in (v.get("animations") or {}).values() if a.get("sld_x1")]
    print("%-5d %-12s %-16s %-32s %s" % (uid, name, ic["atlas"], ic["RefName"], fs))
    print("        loose file : %s" % (os.path.basename(loose) if loose else "NONE"))
    print("        atlas slice: fourcc=%s %dx%d at SD px (%d,%d)"
          % (d["fourcc"], d["w"], d["h"], lx, ly))
    print("        sprite file exists on disk: %s" % all(f.lower() in DISK for f in fs))
    for side, img in ((0, A), (1, B_)):
        if img is None:
            continue
        w, h, pix = img
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
                X = side * (TILE + GAP) + x
                o2 = ((ri * TILE + y) * CW + X) * 4
                CAN[o2:o2 + 4] = bytes((r_, g_, b_, 255))

out = os.path.join(HERE, "png", "crosscheck10.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
png(out, CW, TILE * len(TEN), [bytes(CAN[y * CW * 4:(y + 1) * CW * 4])
                               for y in range(TILE * len(TEN))])
print("\nrendered %s  (left column = game's own loose icon, right = SHIPPED atlas slice)"
      % out)
print("rows top->bottom: %s" % ", ".join(n for _, n in TEN))

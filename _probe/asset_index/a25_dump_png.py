#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a25_dump_png.py -- visual arbitration of the loose-texture vs atlas-slice
question raised by a24 (some tiles matched to MAD<13, others sat at MAD~90).

Writes a contact sheet PNG per atlas:
    row per icon:  [ loose 256x256 ] [ atlas rect in the HD/UHD atlas ]
so the two can be compared by eye rather than by a distance metric.

Also reports whether the loose texture is a downscale of the HD atlas tile
(proper 2x box) or genuinely different artwork.
"""
import json, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}


def hdr(p):
    with open(p, "rb") as f:
        b = f.read(148)
    return {"h": struct.unpack_from("<I", b, 12)[0], "w": struct.unpack_from("<I", b, 16)[0],
            "fourcc": struct.unpack_from("<4s", b, 84)[0].decode("latin1").strip("\x00"),
            "off": 148 if b[84:88] == b"DX10" else 128,
            "dx10": struct.unpack_from("<I", b, 128)[0] if b[84:88] == b"DX10" else None}


DXGI = {70: "BC1", 71: "BC1", 72: "BC2", 73: "BC2", 74: "BC3", 75: "BC3",
        76: "BC1", 77: "BC2", 78: "BC3", 79: "BC4", 80: "BC4",
        81: "BC5", 82: "BC5", 83: "BC5", 94: "BC5"}


def _c565(c0, c1, dxt1):
    def ex(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; bl = c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2))
    a, b = ex(c0), ex(c1)
    if not dxt1 or c0 > c1:
        return [a, b, tuple((2 * a[k] + b[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b[k]) // 3 for k in range(3))]
    return [a, b, tuple((a[k] + b[k]) // 2 for k in range(3)), (0, 0, 0)]


def _a5(blk, i):
    a0, a1 = blk[0], blk[1]
    if a0 > a1:
        tab = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    else:
        tab = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
    c = int.from_bytes(blk[2:8], "little")
    return tab[(c >> (3 * i)) & 7]


def decode(p, lx, ly, w, h):
    hd = hdr(p)
    mode = hd["fourcc"]
    if mode == "DX10":
        mode = DXGI.get(hd["dx10"], "?")
        if mode not in ("BC1", "BC2", "BC3", "BC5"):
            return None, hd
    bs = 8 if mode in ("DXT1", "BC1") else 16
    W = hd["w"]
    bw = (W + 3) // 4
    off = hd["off"]
    out = bytearray(w * h * 4)
    with open(p, "rb") as f:
        for by in range(ly // 4, (ly + h - 1) // 4 + 1):
            n = ((lx + w - 1) // 4 - lx // 4 + 1)
            f.seek(off + (by * bw + lx // 4) * bs)
            ch = f.read(n * bs)
            for j in range(n):
                blk = ch[j * bs:(j + 1) * bs]
                bx = lx // 4 + j
                if mode in ("DXT1", "BC1"):
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
                        if mode in ("DXT1", "BC1"):
                            a = 0 if (idx == 3 and c0 <= c1) else 255
                        elif mode == "DXT3" or mode == "BC2":
                            a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                        else:
                            a = _a5(blk, i)
                        o = ((y - ly) * w + (x - lx)) * 4
                        out[o:o + 4] = bytes((r, g, bl, a))
    return bytes(out), hd


def png(path, w, h, rgba, scale=1):
    W, H = w * scale, h * scale
    rows = bytearray()
    for y in range(H):
        rows.append(0)
        sy = y // scale
        for x in range(W):
            s = (sy * w + x // scale) * 4
            r, g, b, a = rgba[s], rgba[s + 1], rgba[s + 2], rgba[s + 3]
            # composite over a checker so alpha 0 is visible
            c = 200 if (((x // 8) + (y // 8)) % 2 == 0) else 120
            rows += bytes(((r * a + c * (255 - a)) // 255,
                           (g * a + c * (255 - a)) // 255,
                           (b * a + c * (255 - a)) // 255))
    def ch(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(ch(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)))
        f.write(ch(b"IDAT", zlib.compress(bytes(rows), 6)))
        f.write(ch(b"IEND", b""))


def emb(a):
    out = {}
    for t in ATLS[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        hh = stem.split("_")[0]
        if hh.isdigit():
            out[int(hh)] = t
    return out


def loose(a, t):
    fp = os.path.join(WID, t["FileName"].replace("/", os.sep))
    if os.path.exists(fp):
        return fp
    d = os.path.dirname(fp)
    for f in os.listdir(d):
        if f.lower() == os.path.basename(fp).lower():
            return os.path.join(d, f)
    return None


OUT = os.path.join(HERE, "png")
os.makedirs(OUT, exist_ok=True)

for a, picks in (("ingameunits", [4, 41, 17, 900]), ("ingamebuildings", [2, 28]),
                 ("ingametechs", [1, 105])):
    E = emb(a)
    src = os.path.join(WID, ATLS[a]["HDSource"].replace("/", os.sep))
    hd = hdr(src)
    DW = int(ATLS[a]["MaxWidth"])
    sheet_w = 256 + 8 + 128
    sheet_h = len(picks) * (132 + 4)
    canvas = bytearray(sheet_w * sheet_h * 4)
    for row, n in enumerate(picks):
        t = E.get(n)
        if not t:
            continue
        lp = loose(a, t)
        lpx, lh = decode(lp, 0, 0, hdr(lp)["w"], hdr(lp)["h"])
        # atlas tile in TRUE HD space (256x256)
        hx = int(round(float(t["imageTLX"]) * DW + 0.5))
        hy = int(round(float(t["imageTLY"]) * DW + 0.5))
        apx, _ = decode(src, hx, hy, 256, 256)
        if apx is None:
            print("   %s icon %d: HD atlas is %s (%s) - cannot decode"
                  % (a, n, hd["fourcc"], hd["dx10"]))
            continue
        # place loose at x=0 scaled 1 (it is 256), atlas at x=264 scaled 0.5 -> 128
        for y in range(256):
            for x in range(256):
                o = ((row * 136 + y) * sheet_w + x) * 4
                s = (y * 256 + x) * 4
                canvas[o:o + 4] = lpx[s:s + 4]
        for y in range(128):
            for x in range(128):
                o = ((row * 136 + y) * sheet_w + 264 + x) * 4
                s = ((y * 2) * 256 + x * 2) * 4
                canvas[o:o + 4] = apx[s:s + 4]
        d = sum(abs(lpx[((y) * 256 + x) * 4] - apx[((y) * 2) * 256 + x * 2 * 4])
                for y in range(0, 256, 4) for x in range(256)) / float(256 * 64)
        print("   %-16s icon %-4d %-26s loose %dx%d | HD tile @(%d,%d)  MAD=%.2f"
              % (a, n, os.path.basename(lp), lh["w"], lh["h"], hx, hy, d))
    p = os.path.join(OUT, "sheet_%s.png" % a)
    png(p, sheet_w, sheet_h, bytes(canvas))
    print("   wrote %s (%dx%d)" % (p, sheet_w, sheet_h))

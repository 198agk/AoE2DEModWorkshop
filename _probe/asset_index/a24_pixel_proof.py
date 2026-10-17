#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a24_pixel_proof.py -- name-independent, pixel-level proof of the icon chain.

a23 failed 0/24 because the UVs are normalised against the DECLARED MaxWidth /
MaxHeight -- which equal the HD/UHD source size (units 7168x7424, buildings
2816x2816, techs 4800x4800) -- while the DefaultSource is the SD atlas at exactly
half those dimensions.  So in SD space a tile is 128x128, not 127, and the basis
was wrong.

This script:
  1. shows the UV grid is exactly a 256-texel grid in HD space (structural proof
     that the atlas entry describes a 256x256 tile);
  2. compares the loose 256x256 source texture, box-downsampled 2x, against the
     SD atlas rect (128x128) with a best-offset search -> per-pixel MAD;
  3. prints a NEGATIVE CONTROL (the same icon against a different atlas tile) so
     the reader can see the matched MAD is small and the mismatched MAD is not.
"""
import json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}


def dds_header(path):
    with open(path, "rb") as f:
        b = f.read(128)
    # DDS: dwMagic@0 dwSize@4 dwFlags@8 dwHeight@12 dwWidth@16 dwPitch@20
    #      dwDepth@24 dwMipMapCount@28  (dwSize@0 of this struct is @4)
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    fourcc = struct.unpack_from("<4s", b, 84)[0].decode("latin1").strip("\x00")
    dx10 = struct.unpack_from("<I", b, 128)[0] if fourcc == "DX10" else None
    return {"h": h, "w": w, "mips": mips, "fourcc": fourcc, "dx10": dx10}


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


def decode_rect(path, hd, lx, ly, w, h):
    fourcc = hd["fourcc"]
    if fourcc == "DX10":
        return None
    bs = 8 if fourcc == "DXT1" else 16
    W = hd["w"]
    bw = (W + 3) // 4
    bx0, bx1 = lx // 4, (lx + w - 1) // 4
    by0, by1 = ly // 4, (ly + h - 1) // 4
    out = bytearray(w * h * 4)
    nbx = bx1 - bx0 + 1
    with open(path, "rb") as f:
        for by in range(by0, by1 + 1):
            f.seek(128 + (by * bw + bx0) * bs)
            chunk = f.read(nbx * bs)
            for j in range(nbx):
                blk = chunk[j * bs:(j + 1) * bs]
                bx = bx0 + j
                if fourcc == "DXT1":
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
                        if fourcc == "DXT1":
                            a = 0 if (idx == 3 and c0 <= c1) else 255
                        elif fourcc == "DXT3":
                            a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                        else:
                            a = _a5(blk, i)
                        o = ((y - ly) * w + (x - lx)) * 4
                        out[o:o + 4] = bytes((r, g, bl, a))
    return bytes(out)


def downsample2(px, w, h):
    W, H = w // 2, h // 2
    out = bytearray(W * H * 4)
    for y in range(H):
        for x in range(W):
            acc = [0, 0, 0, 0]
            for dy in (0, 1):
                for dx in (0, 1):
                    s = (((y * 2 + dy) * w) + (x * 2 + dx)) * 4
                    for k in range(4):
                        acc[k] += px[s + k]
            o = (y * W + x) * 4
            for k in range(4):
                out[o + k] = acc[k] // 4
    return bytes(out), W, H


def mad(a, b, n=None):
    n = n or len(a)
    return sum(abs(a[i] - b[i]) for i in range(n)) / float(n)


def emb_map(a):
    out = {}
    for t in ATLS[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
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


print("=== 1. UV grid alignment (structural) ===")
for a in ("ingameunits", "ingamebuildings", "ingametechs"):
    hd = dds_header(os.path.join(WID, ATLS[a]["DefaultSource"].replace("/", os.sep)))
    DW = int(ATLS[a]["MaxWidth"]); DH = int(ATLS[a]["MaxHeight"])
    print("   %-16s SD %dx%d  declared Max %dx%d (=HD/UHD source)  SD=half: %s"
          % (a, hd["w"], hd["h"], DW, DH, (hd["w"] * 2, hd["h"] * 2) == (DW, DH)))
    # UV * MaxWidth should land on a half-texel offset: <int> + 0.5
    offgrid = 0
    tot = 0
    for t in ATLS[a]["Textures"]:
        for k in ("imageTLX", "imageTLY", "imageBRX", "imageBRY"):
            v = float(t[k]) * DW
            tot += 1
            if abs((v - 0.5) - round(v - 0.5)) > 0.02:
                offgrid += 1
    print("      UV*MaxWidth NOT of the form N+0.5 (half-texel inset): %d of %d"
          % (offgrid, tot))
    spans = {}
    for t in ATLS[a]["Textures"]:
        spans[round((float(t["imageBRX"]) - float(t["imageTLX"])) * DW)] = \
            spans.get(round((float(t["imageBRX"]) - float(t["imageTLX"])) * DW), 0) + 1
    print("      spans in HD texels: %s" % sorted(spans.items(), key=lambda kv: -kv[1])[:4])

print("\n=== 2/3. PIXEL MATCH: loose 256x256 (box->128) vs SD atlas rect 128x128 ===")
for a in ("ingameunits", "ingamebuildings", "ingametechs"):
    E = emb_map(a)
    hd = dds_header(os.path.join(WID, ATLS[a]["DefaultSource"].replace("/", os.sep)))
    apath = os.path.join(WID, ATLS[a]["DefaultSource"].replace("/", os.sep))
    DW = int(ATLS[a]["MaxWidth"])
    if a == "ingameunits":
        picks = [n for n in (1, 4, 7, 17, 28, 40, 41, 71, 139, 264, 900, 936) if n in E]
    elif a == "ingamebuildings":
        picks = [n for n in (2, 7, 28, 34, 35, 116) if n in E]
    else:
        picks = [n for n in (1, 33, 69, 105, 147) if n in E]
    print("\n   --- %s (SD %dx%d) ---" % (a, hd["w"], hd["h"]))
    for n in picks:
        t = E[n]
        lp = loose(a, t)
        if not lp:
            print("      %-4d loose MISSING" % n)
            continue
        lh = dds_header(lp)
        lp256 = decode_rect(lp, lh, 0, 0, lh["w"], lh["h"])
        small, sw, sh = downsample2(lp256, lh["w"], lh["h"])
        ux, uy = float(t["imageTLX"]), float(t["imageTLY"])
        bx, by = ux * hd["w"], uy * hd["h"]          # SD texel origin
        best = (1e9, None)
        for oy in range(-3, 4):
            for ox in range(-3, 4):
                lx, ly = int(round(bx)) + ox, int(round(by)) + oy
                if lx < 0 or ly < 0 or lx + sw > hd["w"] or ly + sh > hd["h"]:
                    continue
                tile = decode_rect(apath, hd, lx, ly, sw, sh)
                m = mad(tile, small)
                if m < best[0]:
                    best = (m, (lx, ly))
        ctrl = int(round(bx)) + 256, int(round(by)) + 256
        cm = None
        if ctrl[0] + sw <= hd["w"] and ctrl[1] + sh <= hd["h"]:
            cm = mad(decode_rect(apath, hd, ctrl[0], ctrl[1], sw, sh), small)
        print("      %-4d %-26s uv(%.6f,%.6f)*SD=(%.1f,%.1f) best@%s MAD=%6.2f | control MAD=%s"
              % (n, os.path.basename(lp), ux, uy, bx, by,
                 best[1], best[0], ("%6.2f" % cm) if cm is not None else "n/a"))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a26_icon_sheet.py -- VISUAL proof of the unit icon rule.

a24's pixel comparison was invalid because it assumed every loose .dds is DXT1 or
DXT5, while a23 showed most of them report a blank fourcc -- they are either
DX10/BC7 or plain uncompressed.  This script parses the DDS pixel format
properly (dwFlags@8, pfFlags@80, fourCC@84, RGBBitCount@88, masks@92..104),
decodes what it can, and renders a contact sheet of the LOOSE icons for ten
well-known units.  Seeing "Archer" is an archer is the decisive check that
IconID -> ingameunits entry -> FileName is the right chain.

Prints the grid order so the sheet can be read without drawn labels.
"""
import json, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))


def parse(p):
    with open(p, "rb") as f:
        b = f.read(160)
    d = {"magic": b[:4], "h": struct.unpack_from("<I", b, 12)[0],
         "w": struct.unpack_from("<I", b, 16)[0], "mips": struct.unpack_from("<I", b, 28)[0],
         "pfFlags": struct.unpack_from("<I", b, 80)[0],
         "fourcc": b[84:88].decode("latin1").strip("\x00"),
         "bits": struct.unpack_from("<I", b, 88)[0],
         "maskR": struct.unpack_from("<I", b, 92)[0], "maskG": struct.unpack_from("<I", b, 96)[0],
         "maskB": struct.unpack_from("<I", b, 100)[0], "maskA": struct.unpack_from("<I", b, 104)[0]}
    d["off"] = 148 if b[84:88] == b"DX10" else 128
    if b[84:88] == b"DX10":
        d["dxgi"] = struct.unpack_from("<I", b, 128)[0]
    return d


DXGI = {70: "BC1", 71: "BC1", 72: "BC2", 73: "BC2", 74: "BC3", 75: "BC3", 76: "BC1",
        77: "BC2", 78: "BC3", 79: "BC4", 80: "BC4", 81: "BC5", 82: "BC5", 83: "BC5",
        94: "BC5", 95: "BC6H", 96: "BC6H", 97: "BC7", 98: "BC7",
        28: "R8G8B8A8_UNORM", 29: "R8G8B8A8_UNORM_SRGB", 87: "B8G8R8A8_UNORM",
        88: "B8G8R8X8_UNORM"}


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


def decode_full(p):
    """Return (w, h, rgba bytes, describe str) or (w,h,None,why)."""
    d = parse(p)
    w, h, off = d["w"], d["h"], d["off"]
    mode = d["fourcc"]
    if mode == "DX10":
        mode = DXGI.get(d.get("dxgi"), "DXGI%s" % d.get("dxgi"))
    with open(p, "rb") as f:
        f.seek(off)
        raw = f.read()
    if mode in ("BC1", "DXT1", "BC2", "DXT3", "BC3", "DXT5"):
        m = {"BC1": "DXT1", "BC2": "DXT3", "BC3": "DXT5"}.get(mode, mode)
        bs = 8 if m == "DXT1" else 16
        bw = (w + 3) // 4
        out = bytearray(w * h * 4)
        for by in range((h + 3) // 4):
            for bx in range(bw):
                o = (by * bw + bx) * bs
                blk = raw[o:o + bs]
                if len(blk) < bs:
                    continue
                if m == "DXT1":
                    c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                    cols = _c565(c0, c1, True)
                else:
                    c0, c1 = struct.unpack_from("<HH", blk, 8)
                    bits = struct.unpack_from("<I", blk, 12)[0]
                    cols = _c565(c0, c1, False)
                for py in range(4):
                    y = by * 4 + py
                    if y >= h:
                        continue
                    for px in range(4):
                        x = bx * 4 + px
                        if x >= w:
                            continue
                        i = py * 4 + px
                        idx = (bits >> (2 * i)) & 3
                        r, g, bl = cols[idx]
                        if m == "DXT1":
                            a = 0 if (idx == 3 and c0 <= c1) else 255
                        elif m == "DXT3":
                            a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                        else:
                            a = _a5(blk, i)
                        o2 = (y * w + x) * 4
                        out[o2:o2 + 4] = bytes((r, g, bl, a))
        return w, h, bytes(out), "%s %dx%d" % (m, w, h)
    if d["pfFlags"] & 0x40:  # DDPF_RGB, uncompressed
        bits = d["bits"]
        step = bits // 8
        out = bytearray(w * h * 4)
        for i in range(w * h):
            o = i * step
            if o + step > len(raw):
                break
            px = int.from_bytes(raw[o:o + step], "little")
            def get(mask):
                if not mask:
                    return 255
                sh = (mask & -mask).bit_length() - 1
                mx = mask >> sh
                return ((px & mask) >> sh) * 255 // mx
            o2 = i * 4
            out[o2:o2 + 4] = bytes((get(d["maskR"]), get(d["maskG"]),
                                    get(d["maskB"]), get(d["maskA"])))
        return w, h, bytes(out), "RGB%d %dx%d" % (bits, w, h)
    return w, h, None, "UNSUPPORTED fourcc=%r dxgi=%s pfFlags=0x%x bits=%d" % (
        d["fourcc"], d.get("dxgi"), d["pfFlags"], d["bits"])


def png(path, W, H, rgba):
    rows = bytearray()
    for y in range(H):
        rows.append(0)
        for x in range(W):
            s = (y * W + x) * 4
            r, g, b, a = rgba[s], rgba[s + 1], rgba[s + 2], rgba[s + 3]
            c = 210 if (((x // 8) + (y // 8)) % 2 == 0) else 130
            rows += bytes(((r * a + c * (255 - a)) // 255,
                           (g * a + c * (255 - a)) // 255,
                           (b * a + c * (255 - a)) // 255))

    def ch(t, dd):
        c = t + dd
        return struct.pack(">I", len(dd)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
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


byid = {}
for civ in C:
    for u in civ["units"]:
        byid.setdefault(u["id"], u)

E = emb("ingameunits")
targets = [4, 83, 38, 74, 71, 12, 82, 70, 8, 125, 93, 280]
print("FORMAT SURVEY of the 794 loose unit icons:")
fmt = {}
for t in ATLS["ingameunits"]["Textures"]:
    lp = loose("ingameunits", t)
    if not lp:
        continue
    w, h, px, why = decode_full(lp)
    fmt[why.split()[0] if px is None else why.split()[0]] = \
        fmt.get(why.split()[0] if px is None else why.split()[0], 0) + 1
for k, v in sorted(fmt.items(), key=lambda kv: -kv[1]):
    print("   %-14s %d" % (k, v))

print("\nGRID (3 columns x 4 rows, reading order left-to-right, top-to-bottom):")
cols, scale = 3, 1
tw = 128
rows = (len(targets) + cols - 1) // cols
W, H = cols * (tw + 4), rows * (tw + 4)
canvas = bytearray(W * H * 4)
for i, uid in enumerate(targets):
    u = byid.get(uid)
    if not u:
        continue
    ic = u.get("icon_id", -1)
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name")
    t = E.get(ic)
    cx, cy = (i % cols) * (tw + 4), (i // cols) * (tw + 4)
    print("   r%dc%d  unit %-4d icon=%-4d %-22s -> %s"
          % (i // cols + 1, i % cols + 1, uid, ic, (en or "")[:22],
             os.path.basename(loose("ingameunits", t)) if t else "NO ENTRY"))
    if not t:
        continue
    lp = loose("ingameunits", t)
    w, h, px, why = decode_full(lp)
    if px is None:
        print("        could not decode: %s" % why)
        continue
    for y in range(tw):
        for x in range(tw):
            sx, sy = x * w // tw, y * h // tw
            s = (sy * w + sx) * 4
            o = ((cy + y) * W + cx + x) * 4
            canvas[o:o + 4] = px[s:s + 4]
OUT = os.path.join(HERE, "png")
os.makedirs(OUT, exist_ok=True)
p = os.path.join(OUT, "units_named.png")
png(p, W, H, bytes(canvas))
print("\nwrote %s (%dx%d)" % (p, W, H))

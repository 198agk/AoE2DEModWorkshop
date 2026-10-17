#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a27_loose_vs_atlas.py -- arbitrate loose icon file vs packed atlas slice.

a24 found that SOME loose icons equal their SD atlas slice (MAD<13) and some do
not (MAD~90).  This renders both side by side so the difference is visible, and
measures the agreement rate over ALL 794 entries.

  left  column = loose widgetui/textures/ingame/units/<NNN>_50730.dds
  right column = the atlas slice that RefName UnitIcons<NNN>50730 points at

If the loose file is the true icon and the atlas slice is stale, the LEFT column
is the authoritative image; either way the atlas entry (RefName + UV + FileName)
stays the same, only the pixels differ.
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
    return {"h": struct.unpack_from("<I", b, 12)[0], "w": struct.unpack_from("<I", b, 16)[0],
            "pfFlags": struct.unpack_from("<I", b, 80)[0],
            "fourcc": b[84:88].decode("latin1").strip("\x00"),
            "bits": struct.unpack_from("<I", b, 88)[0],
            "maskR": struct.unpack_from("<I", b, 92)[0], "maskG": struct.unpack_from("<I", b, 96)[0],
            "maskB": struct.unpack_from("<I", b, 100)[0], "maskA": struct.unpack_from("<I", b, 104)[0],
            "off": 148 if b[84:88] == b"DX10" else 128}


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
    d = parse(p)
    mode = d["fourcc"]
    with open(p, "rb") as f:
        f.seek(d["off"])
        raw = f.read()
    W = d["w"]
    out = bytearray(w * h * 4)
    if mode in ("DXT1", "DXT3", "DXT5"):
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
                        elif mode == "DXT3":
                            a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                        else:
                            a = _a5(blk, i)
                        o2 = ((y - ly) * w + x - lx) * 4
                        out[o2:o2 + 4] = bytes((r, g, bl, a))
        return w, h, bytes(out)
    if d["pfFlags"] & 0x40:
        step = d["bits"] // 8
        for y in range(ly, ly + h):
            for x in range(lx, lx + w):
                o = (y * W + x) * step
                if o + step > len(raw):
                    continue
                pxv = int.from_bytes(raw[o:o + step], "little")
                def g(mask):
                    if not mask:
                        return 255
                    sh = (mask & -mask).bit_length() - 1
                    return ((pxv & mask) >> sh) * 255 // (mask >> sh)
                o2 = ((y - ly) * w + x - lx) * 4
                out[o2:o2 + 4] = bytes((g(d["maskR"]), g(d["maskG"]), g(d["maskB"]), g(d["maskA"])))
        return w, h, bytes(out)
    return w, h, None


def png(path, W, H, rgba):
    rows = bytearray()
    for y in range(H):
        rows.append(0)
        for x in range(W):
            s = (y * W + x) * 4
            r, g, b, a = rgba[s], rgba[s + 1], rgba[s + 2], rgba[s + 3]
            c = 205 if (((x // 8) + (y // 8)) % 2 == 0) else 125
            rows += bytes(((r * a + c * (255 - a)) // 255, (g * a + c * (255 - a)) // 255,
                           (b * a + c * (255 - a)) // 255))

    def ch(t, dd):
        cc = t + dd
        return struct.pack(">I", len(dd)) + cc + struct.pack(">I", zlib.crc32(cc) & 0xFFFFFFFF)
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


def emb_uv(t, W, H):
    lx = int(round(float(t["imageTLX"]) * W + 0.5))
    ly = int(round(float(t["imageTLY"]) * H + 0.5))
    hx = int(round(float(t["imageBRX"]) * W - 0.5))
    hy = int(round(float(t["imageBRY"]) * H - 0.5))
    return lx, ly, hx - lx + 1, hy - ly + 1


def down2(px, w, h):
    W, Hh = w // 2, h // 2
    out = bytearray(W * Hh * 4)
    for y in range(Hh):
        for x in range(W):
            for k in range(4):
                out[(y * W + x) * 4 + k] = (px[((y * 2) * w + x * 2) * 4 + k] +
                                            px[((y * 2) * w + x * 2 + 1) * 4 + k] +
                                            px[((y * 2 + 1) * w + x * 2) * 4 + k] +
                                            px[((y * 2 + 1) * w + x * 2 + 1) * 4 + k]) // 4
    return bytes(out)


SRC = os.path.join(WID, ATLS["ingameunits"]["DefaultSource"].replace("/", os.sep))
hdr_src = parse(SRC)
SW, SH = hdr_src["w"], hdr_src["h"]
E = emb("ingameunits")

print("SD atlas %dx%d ; %d entries ; loose files 256x256" % (SW, SH, len(E)))
res = []
for n in sorted(E):
    t = E[n]
    lp = loose("ingameunits", t)
    if not lp:
        res.append((n, None, None))
        continue
    lw, lh, lpx = decode(lp, 0, 0, parse(lp)["w"], parse(lp)["h"])
    if lpx is None:
        res.append((n, None, "undecodable"))
        continue
    small = down2(lpx, lw, lh)
    lx, ly, w, h = emb_uv(t, SW, SH)
    aw, ah, apx = decode(SRC, lx, ly, w, h)
    if apx is None:
        res.append((n, None, "atlas-undecodable"))
        continue
    if (aw, ah) != (lw // 2, lh // 2):
        res.append((n, None, "size %dx%d vs %dx%d" % (aw, ah, lw // 2, lh // 2)))
        continue
    mad = sum(abs(apx[i] - small[i]) for i in range(len(apx))) / float(len(apx))
    res.append((n, mad, (lx, ly, lw, lh)))

ok = [r for r in res if isinstance(r[1], float) and r[1] < 20]
bad = [r for r in res if isinstance(r[1], float) and r[1] >= 20]
print("compared: %d ; MAD<20 (identical): %d ; MAD>=20 (differ): %d ; other: %d"
      % (len([r for r in res if isinstance(r[1], float)]), len(ok), len(bad),
         len([r for r in res if r[1] is None])))
if bad:
    ms = sorted(r[1] for r in bad)
    print("   differing MAD: min %.1f median %.1f max %.1f" % (ms[0], ms[len(ms) // 2], ms[-1]))
if ok:
    ms = sorted(r[1] for r in ok)
    print("   identical MAD: min %.2f median %.2f max %.2f" % (ms[0], ms[len(ms) // 2], ms[-1]))
print("   first 24 differing numbers: %s" % [r[0] for r in bad[:24]])
print("   numbers with no comparison: %s" % [(r[0], r[2]) for r in res if r[1] is None][:10])

byid = {}
for civ in C:
    for u in civ["units"]:
        byid.setdefault(u["id"], u)
targets = [4, 83, 38, 74, 71, 12, 82, 70, 8, 125, 93, 280]
TW = 128
W, H = 2 * (TW + 4), len(targets) * (TW + 4)
canvas = bytearray(W * H * 4)
print("\nSHEET: left = loose file, right = atlas slice   (2 cols x %d rows)" % len(targets))
for i, uid in enumerate(targets):
    u = byid[uid]
    ic = u["icon_id"]
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name")
    t = E[ic]
    lp = loose("ingameunits", t)
    cy = i * (TW + 4)
    lw, lh, lpx = decode(lp, 0, 0, parse(lp)["w"], parse(lp)["h"])
    small = down2(lpx, lw, lh)
    lx, ly, w, h = emb_uv(t, SW, SH)
    aw, ah, apx = decode(SRC, lx, ly, w, h)
    for y in range(TW):
        for x in range(TW):
            s = ((y * (lw // 2) // TW) * (lw // 2) + (x * (lw // 2) // TW)) * 4
            o = ((cy + y) * W + x) * 4
            canvas[o:o + 4] = small[s:s + 4]
            s2 = ((y * ah // TW) * aw + (x * aw // TW)) * 4
            o2 = ((cy + y) * W + TW + 4 + x) * 4
            canvas[o2:o2 + 4] = apx[s2:s2 + 4]
    m = sum(abs(apx[k] - small[k]) for k in range(len(apx))) / float(len(apx))
    print("   r%-2d unit %-4d %-20s icon=%-4d MAD=%6.2f %s"
          % (i + 1, uid, (en or "")[:20], ic, m, "SAME" if m < 20 else "DIFFER"))
OUT = os.path.join(HERE, "png")
os.makedirs(OUT, exist_ok=True)
p = os.path.join(OUT, "loose_vs_atlas.png")
png(p, W, H, bytes(canvas))
print("\nwrote %s (%dx%d)" % (p, W, H))

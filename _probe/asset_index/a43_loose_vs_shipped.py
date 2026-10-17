#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a43_loose_vs_shipped.py -- verify the SHIPPED index's atlas+UV against the game's own
author-named loose icon files, for the 300 building-routed entities.

Why this is the right instrument:
  * the loose file widgetui\\textures\\ingame\\buildings\\<NNN>_<label>.DDS carries a NAME
    the game's authors wrote (028_town_center.DDS, 002_barracks_1.DDS).  It is therefore
    independent, non-circular evidence for what icon <NNN> is supposed to depict.
  * the shipped index names, for the SAME entity, an atlas + a UV rect.  If that atlas
    slice renders identical to the loose file, then both the atlas choice AND the UV rect
    are verified against author intent -- not against my own rule.

Renders a side-by-side contact sheet (left = loose file, right = shipped atlas slice) and
prints a MAD table.  a27 established that a raw MAD number is a misleading instrument when
two images differ by one texel in size, so the CONTACT SHEET is the primary evidence and
MAD is only reported alongside a box-resampled comparison.
"""
import json, os, re, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
LOOSE_B = os.path.join(WID, "textures", "ingame", "buildings")

# loose numeric stem -> actual filename on disk (case-insensitive match)
LST = {}
for f in os.listdir(LOOSE_B):
    h = f.split("_")[0]
    if h.isdigit():
        LST[int(h)] = os.path.join(LOOSE_B, f)


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
    """decode a rectangle of a DDS: DXT1/2/3/5 or uncompressed RGB(A) via bit masks."""
    d = hdr(p)
    W, H = d["w"], d["h"]
    if w is None:
        w, h = W, H
    raw = open(p, "rb").read()[d["off"]:]
    out = bytearray(w * h * 4)
    if d["pfFlags"] & 0x40 and not d["fourcc"]:
        # uncompressed, bit masks
        bpp = d["bits"] // 8
        rowbytes = W * bpp

        def shf(m):
            return bin(m)[::-1].index("1") if m else 0

        def bits_of(m):
            return bin(m).count("1") if m else 0

        sR, nR, sG, nG = shf(d["mR"]), bits_of(d["mR"]), shf(d["mG"]), bits_of(d["mG"])
        sB, nB, sA, nA = shf(d["mB"]), bits_of(d["mB"]), shf(d["mA"]), bits_of(d["mA"])
        for y in range(ly, ly + h):
            base = y * rowbytes
            for x in range(lx, lx + w):
                o = base + x * bpp
                px = int.from_bytes(raw[o:o + bpp], "little")
                def sc(sh, n):
                    return ((px >> sh) & ((1 << n) - 1)) * 255 // ((1 << n) - 1) if n else 255
                o2 = ((y - ly) * w + x - lx) * 4
                out[o2:o2 + 4] = bytes((sc(sR, nR), sc(sG, nG), sc(sB, nB), sc(sA, nA) if nA else 255))
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


def resize(pix, w, h, W2, H2):
    o2 = bytearray(W2 * H2 * 4)
    for y in range(H2):
        sy = min(h - 1, y * h // H2)
        for x in range(W2):
            sx = min(w - 1, x * w // W2)
            s = (sy * w + sx) * 4
            d = (y * W2 + x) * 4
            o2[d:d + 4] = pix[s:s + 4]
    return bytes(o2)


def mad(a, b):
    n = len(a) // 4
    t = 0
    for i in range(0, len(a), 4):
        t += abs(a[i] - b[i]) + abs(a[i + 1] - b[i + 1]) + abs(a[i + 2] - b[i + 2])
    return t / (3.0 * n)


def png(path, W, H, rows):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    data = b"".join(b"\x00" + r for r in rows)
    o = [b"\x89PNG\r\n\x1a\n"]
    for tag, pl in ((b"IHDR", ihdr), (b"IDAT", zlib.compress(data)), (b"IEND", b"")):
        o.append(struct.pack(">I", len(pl)) + tag + pl +
                 struct.pack(">I", zlib.crc32(tag + pl) & 0xFFFFFFFF))
    open(path, "wb").write(b"".join(o))


TILE = 128
rows_shown = []
mad_rows = []
targets = []
for k, r in sorted(U.items(), key=lambda x: int(x[0])):
    ic = r.get("icon") or {}
    if not ic.get("resolved") or ic.get("atlas") != "ingamebuildings":
        continue
    n = ic.get("icon_id")
    if n not in LST:
        continue
    targets.append((int(k), r["en"], ic, n))

print("building-routed entities with a loose author-named file: %d" % len(targets))
for uid, en, ic, n in targets:
    at = ATLS[ic["atlas"]]
    src = os.path.join(WID, at["DefaultSource"].replace("/", os.sep))
    d = hdr(src)
    uv = ic["uv"]
    lx = int(round(uv["x1"] * d["w"] + 0.5)); ly = int(round(uv["y1"] * d["h"] + 0.5))
    hx = int(round(uv["x2"] * d["w"] - 0.5)); hy = int(round(uv["y2"] * d["h"] - 0.5))
    w, h = hx - lx + 1, hy - ly + 1
    A = dec_rect(src, lx, ly, w, h)
    B_ = dec_rect(LST[n])
    if A is None or B_ is None:
        mad_rows.append((uid, en, n, os.path.basename(LST[n]), None, "undecodable"))
        continue
    aa = resize(A[2], w, h, 64, 64)
    bb = resize(B_[2], B_[0], B_[1], 64, 64)
    m = mad(aa, bb)
    mad_rows.append((uid, en, n, os.path.basename(LST[n]), m, ""))

vals = [m for *_x, m, st in mad_rows if m is not None]
vals.sort()
print("\nMAD distribution over %d comparable pairs:" % len(vals))
if vals:
    print("  min=%.1f  median=%.1f  max=%.1f" % (vals[0], vals[len(vals) // 2], vals[-1]))
    for thr in (2, 5, 10, 20, 40):
        print("  MAD <= %-3d : %d / %d" % (thr, sum(1 for v in vals if v <= thr), len(vals)))

print("\nfirst 25 rows (uid, name, icon, loose label, MAD):")
for row in mad_rows[:25]:
    print("  %-7s %-26s %-5s %-30s %s %s"
          % (row[0], (row[1] or "")[:26], row[2], row[3], row[4], row[5]))

# ---- side-by-side contact sheet for the 12 lowest-MAD and 12 highest-MAD ----
ranked = [r for r in mad_rows if r[4] is not None]
ranked.sort(key=lambda r: r[4])
show = ranked[:12] + ranked[-12:]
print("\ncontact sheet rows (%d), left=loose right=shipped-atlas:" % len(show))
for r in show:
    print("   %-7s %-26s %-30s MAD=%s" % (r[0], (r[1] or "")[:26], r[3], r[4]))

CAN = bytearray(TILE * len(show) * (TILE * 2 + 8) * 4)
CW = TILE * 2 + 8
for ri, (uid, en, n, lbl, m, st) in enumerate(show):
    at = ATLS[U[str(uid)]["icon"]["atlas"]]
    src = os.path.join(WID, at["DefaultSource"].replace("/", os.sep))
    d = hdr(src)
    uv = U[str(uid)]["icon"]["uv"]
    lx = int(round(uv["x1"] * d["w"] + 0.5)); ly = int(round(uv["y1"] * d["h"] + 0.5))
    hx = int(round(uv["x2"] * d["w"] - 0.5)); hy = int(round(uv["y2"] * d["h"] - 0.5))
    A = dec_rect(src, lx, ly, hx - lx + 1, hy - ly + 1)
    B_ = dec_rect(LST[n])
    for side, (w, h, pix) in ((0, A), (1, B_)):
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
                X = side * (TILE + 8) + x
                o2 = ((ri * TILE + y) * CW + X) * 4
                CAN[o2:o2 + 4] = bytes((r_, g_, b_, 255))
out = os.path.join(HERE, "png", "loose_vs_shipped_buildings.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
png(out, CW, TILE * len(show), [bytes(CAN[y * CW * 4:(y + 1) * CW * 4])
                                for y in range(TILE * len(show))])
print("\nrendered %s (%dx%d)" % (out, CW, TILE * len(show)))

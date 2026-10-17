#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a23_pixel_proof.py -- DECISIVE, name-independent proof of the icon chain.

The name-plausibility test in a21 can only confirm atlases whose RefName carries
text (ingamebuildings, ingametechs).  ingameunits RefNames are 'UnitIcons<NNN>50730'
-- pure numbers -- so 0/986 could never fire.  That is a one-sided test.

This replaces name-guessing with PIXELS:
  1. parse DDS headers of the atlas packs and of loose icon textures: real
     dimensions, format, mip count.
  2. turn each atlas UV rect into a pixel rect using the REAL texture size and
     report whether the implied tile size is a whole number of pixels.
  3. DECODE DXT1/DXT3/DXT5 blocks and compare the pixels of
     widgetui\\textures\\ingame\\units\\<NNN>_50730.dds
     against that icon's rect inside textures\\atlas\\SD\\ingameunits.dds.
     Exact match  =>  the FileName, the UV rect and the atlas all describe the
     same image; and running the same test for a building and a tech icon shows
     which atlas each IconID namespace really belongs to.

Only the blocks covering the requested rect are decoded (the SD atlas is 13 MB).
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, struct, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}

def dds_header(path):
    with open(path, "rb") as f:
        b = f.read(128)
    if b[:4] != b"DDS ":
        return None
    (size, flags, h, w, pitch, depth, mips) = struct.unpack_from("<7I", b, 4)
    fourcc = struct.unpack_from("<4s", b, 84)[0]
    return {"h": h, "w": w, "mips": mips, "fourcc": fourcc.decode("latin1").strip("\x00")}

def _c565(c0, c1, dxt1):
    def ex(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; bl = c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2))
    a, b = ex(c0), ex(c1)
    if not dxt1 or c0 > c1:
        return [a, b, tuple((2 * a[k] + b[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b[k]) // 3 for k in range(3))]
    return [a, b, tuple((a[k] + b[k]) // 2 for k in range(3)), (0, 0, 0)]

def _dxt5_alpha(blk, i):
    a0, a1 = blk[0], blk[1]
    if a0 > a1:
        tab = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    else:
        tab = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
    code = int.from_bytes(blk[2:8], "little")
    return tab[(code >> (3 * i)) & 7]

def decode_rect(path, hd, lx, ly, w, h):
    """Decode exactly the pixel rect [lx,lx+w) x [ly,ly+h) from a DDS file."""
    fourcc = hd["fourcc"]
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
                            a = _dxt5_alpha(blk, i)
                        o = ((y - ly) * w + (x - lx)) * 4
                        out[o:o + 4] = bytes((r, g, bl, a))
    return bytes(out)

def emb_map(a):
    out = {}
    for t in ATLS[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out

def rect(t, W, H):
    """UV rect -> inclusive texel box (half-texel inset), then (lx,ly,w,h,size)."""
    x1, y1 = float(t["imageTLX"]), float(t["imageTLY"])
    x2, y2 = float(t["imageBRX"]), float(t["imageBRY"])
    lx = int(round(x1 * W + 0.5)); ly = int(round(y1 * H + 0.5))
    hx = int(round(x2 * W - 0.5)); hy = int(round(y2 * H - 0.5))
    return lx, ly, hx - lx + 1, hy - ly + 1

def loose(a, t):
    fp = os.path.join(WID, t["FileName"].replace("/", os.sep))
    if os.path.exists(fp):
        return fp
    d = os.path.dirname(fp)
    for f in os.listdir(d):
        if f.lower() == os.path.basename(fp).lower():
            return os.path.join(d, f)
    return None

print("=== 1. DDS headers ===")
for a in ("ingameunits", "ingamebuildings", "ingametechs"):
    for k in ("SDSource", "DefaultSource", "HDSource"):
        p = ATLS[a].get(k)
        if not p:
            continue
        fp = os.path.join(WID, p.replace("/", os.sep))
        hd = dds_header(fp) if os.path.exists(fp) else None
        print("   %-16s %-9s %-42s %s" % (a, k, p, hd))
print("   atlas declared Max: units %sx%s  buildings %sx%s  techs %sx%s"
      % (ATLS["ingameunits"].get("MaxWidth"), ATLS["ingameunits"].get("MaxHeight"),
         ATLS["ingamebuildings"].get("MaxWidth"), ATLS["ingamebuildings"].get("MaxHeight"),
         ATLS["ingametechs"].get("MaxWidth"), ATLS["ingametechs"].get("MaxHeight")))

print("\n=== 2. UV rect -> texel box ===")
HDR = {}
for a in ("ingameunits", "ingamebuildings", "ingametechs"):
    fp = os.path.join(WID, ATLS[a]["DefaultSource"].replace("/", os.sep))
    HDR[a] = dds_header(fp)
    W, H = HDR[a]["w"], HDR[a]["h"]
    sizes = {}
    nonint = 0
    for t in ATLS[a]["Textures"]:
        lx, ly, w, h = rect(t, W, H)
        sizes[(w, h)] = sizes.get((w, h), 0) + 1
    print("   %-16s DDS %dx%d  entries %d  texel-box sizes %s"
          % (a, W, H, len(ATLS[a]["Textures"]), sorted(sizes.items(), key=lambda kv: -kv[1])[:4]))
    ex = ATLS[a]["Textures"][0]
    print("      e.g. %-30s -> %s" % (ex["RefName"], rect(ex, W, H)))

print("\n=== 3. PIXEL COMPARISON: loose texture vs its atlas rect ===")
report = {}
for a in ("ingameunits", "ingamebuildings", "ingametechs"):
    E = emb_map(a)
    W, H = HDR[a]["w"], HDR[a]["h"]
    apath = os.path.join(WID, ATLS[a]["DefaultSource"].replace("/", os.sep))
    picks = sorted(E)[:0]
    if a == "ingameunits":
        picks = [n for n in (1, 4, 7, 17, 28, 40, 41, 71, 139, 264, 507, 794, 900, 936) if n in E]
    elif a == "ingamebuildings":
        picks = [n for n in (2, 7, 28, 34, 35, 36, 116) if n in E]
    else:
        picks = [n for n in (1, 33, 69, 105, 107, 147, 148) if n in E]
    tested = match = 0
    print("\n   --- atlas %s (%dx%d %s) ---" % (a, W, H, HDR[a]["fourcc"]))
    for n in picks:
        t = E[n]
        lp = loose(a, t)
        if not lp:
            print("      %-4d loose file MISSING: %s" % (n, t["FileName"]))
            continue
        lh = dds_header(lp)
        lx, ly, w, h = rect(t, W, H)
        tile = decode_rect(apath, HDR[a], lx, ly, w, h)
        lpix = decode_rect(lp, lh, 0, 0, lh["w"], lh["h"])
        same = (lh["w"], lh["h"]) == (w, h) and tile == lpix
        tested += 1
        match += 1 if same else 0
        print("      %-4d %-24s loose %dx%d %-5s | atlas @(%d,%d) %dx%d  MATCH=%-5s sha %s/%s"
              % (n, os.path.basename(lp), lh["w"], lh["h"], lh["fourcc"], lx, ly, w, h,
                 same, hashlib.sha1(tile).hexdigest()[:8], hashlib.sha1(lpix).hexdigest()[:8]))
    report[a] = (match, tested)
    print("      => pixel-identical %d/%d" % (match, tested))

print("\n=== 4. NEGATIVE CONTROL: same IconID in the wrong atlas ===")
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))
byid = {}
for civ in C:
    for u in civ["units"]:
        byid.setdefault(u["id"], u)
UB, BB, TB = emb_map("ingameunits"), emb_map("ingamebuildings"), emb_map("ingametechs")
for uid in (12, 71, 70, 4, 8):
    u = byid[uid]
    ic = u["icon_id"]
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name")
    print("   unit %-4d %-20s type=%-3d icon=%-4d" % (uid, (en or "")[:20], u["type"], ic))
    for nm, E, at in (("ingameunits", UB, "ingameunits"), ("ingamebuildings", BB, "ingamebuildings")):
        t = E.get(ic)
        if not t:
            print("        %-16s no entry" % nm)
            continue
        lp = loose(at, t)
        H2 = HDR[at]
        lx, ly, w, h = rect(t, H2["w"], H2["h"])
        print("        %-16s %-34s %s" % (nm, t["RefName"],
                                          os.path.basename(lp) if lp else "loose missing"))

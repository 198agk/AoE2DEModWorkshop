# -*- coding: utf-8 -*-
"""probe_icon_look.py -- LOOK at the tiles before writing the resolver.

`probe_icon_section_rule.py` decides by name overlap (81.3% of real buildings vs
0.2% of everything else).  A name test cannot settle the leftovers, and the whole
question is "which picture does a player expect" -- so dump the actual pixels and
look at them.

Two things a25_dump_png.decode() cannot do here, both measured by
probe_icon_render_route.py:

  * the loose file IS the whole 256x256 icon (its size equals uv*atlas for
    1,211/1,211 icon-atlas entries), so the UV rect must NOT be used to crop it;
  * 539/794 unit icons are UNCOMPRESSED BGRA (`fourcc` empty, pitch = w*4), which
    a25's block decoder has no path for.

So this probe decodes both DXT5 and raw BGRA itself and writes PNGs to
_shots/icons/ for a human to look at.
"""
from __future__ import print_function

import codecs
import io
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
OUT = os.path.join(ROOT, "_shots", "icons")


# ---------------------------------------------------------------- DDS decode
def head(path):
    with open(path, "rb") as fh:
        b = fh.read(148)
    fourcc = struct.unpack_from("<4s", b, 84)[0].decode("latin1").strip("\x00")
    return {"h": struct.unpack_from("<I", b, 12)[0],
            "w": struct.unpack_from("<I", b, 16)[0],
            "pitch": struct.unpack_from("<I", b, 20)[0],
            "fourcc": fourcc,
            "dx10": struct.unpack_from("<I", b, 128)[0] if fourcc == "DX10" else None,
            "off": 148 if fourcc == "DX10" else 128}


def _c565(c0, c1):
    def ex(c):
        r = (c >> 11) & 31
        g = (c >> 5) & 63
        b = c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))
    a, b = ex(c0), ex(c1)
    if c0 > c1:
        return [a, b, tuple((2 * a[k] + b[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b[k]) // 3 for k in range(3))], True
    return [a, b, tuple((a[k] + b[k]) // 2 for k in range(3)), (0, 0, 0)], False


def decode(path):
    """-> (w, h, RGBA bytes) or raise with the reason."""
    hd = head(path)
    w, h = hd["w"], hd["h"]
    with open(path, "rb") as fh:
        fh.seek(hd["off"])
        body = fh.read()
    fourcc = hd["fourcc"]
    if not fourcc:                                  # uncompressed, BGRA 8:8:8:8
        need = w * h * 4
        if len(body) < need:
            raise ValueError("raw BGRA short: %d < %d" % (len(body), need))
        out = bytearray(need)
        for i in range(0, need, 4):
            out[i:i + 4] = bytes((body[i + 2], body[i + 1], body[i],
                                  body[i + 3]))     # BGRA -> RGBA
        return w, h, bytes(out)
    if fourcc in ("DXT5", "DXT4", "BC3"):
        bs = 16
    elif fourcc in ("DXT1", "BC1"):
        bs = 8
    else:
        raise ValueError("unsupported fourcc %r (DXGI %s)" % (fourcc, hd["dx10"]))
    bw = (w + 3) // 4
    bh = (h + 3) // 4
    if len(body) < bw * bh * bs:
        raise ValueError("block data short: %d < %d" % (len(body), bw * bh * bs))
    out = bytearray(w * h * 4)
    pos = 0
    for by in range(bh):
        for bx in range(bw):
            blk = body[pos:pos + bs]
            pos += bs
            if bs == 8:
                c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                cols, _ = _c565(c0, c1)
            else:
                c0, c1 = struct.unpack_from("<HH", blk, 8)
                cols, _ = _c565(c0, c1)
                bits = struct.unpack_from("<I", blk, 12)[0]
            for py in range(4):
                y = by * 4 + py
                if y >= h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= w:
                        continue
                    i = py * 4 + px
                    r, g, b = cols[(bits >> (2 * i)) & 3]
                    if bs == 16:
                        a = (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17
                    elif (bits >> (2 * i)) & 3 == 3 and c0 <= c1:
                        a = 0
                    else:
                        a = 255
                    o = (y * w + x) * 4
                    out[o:o + 4] = bytes((r, g, b, a))
    return w, h, bytes(out)


# ---------------------------------------------------------------- PNG writer
def png(path, w, h, rgba, scale=1, checker=True):
    W, H = w * scale, h * scale
    rows = bytearray()
    for y in range(H):
        rows.append(0)
        sy = y // scale
        for x in range(W):
            s = (sy * w + x // scale) * 4
            r, g, b, a = rgba[s], rgba[s + 1], rgba[s + 2], rgba[s + 3]
            if checker:
                c = 200 if (((x // 8) + (y // 8)) % 2 == 0) else 120
                rows += bytes(((r * a + c * (255 - a)) // 255,
                               (g * a + c * (255 - a)) // 255,
                               (b * a + c * (255 - a)) // 255))
            else:
                rows += bytes((r, g, b))
    def ch(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(ch(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)))
        fh.write(ch(b"IDAT", zlib.compress(bytes(rows), 6)))
        fh.write(ch(b"IEND", b""))


# ---------------------------------------------------------------- the chain
def load():
    with io.open(os.path.join(WID, "materials.json"), encoding="utf-8-sig") as fh:
        M = json.load(fh)
    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        I = json.load(fh)
    atls = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in M["AtlasTextures"]}
    mats = {}
    for m in M["Materials"]:
        md = m.get("MaterialDef")
        if md and md.get("Name"):
            mats.setdefault(md["Name"], md)
    return I, atls, mats


def resolve(icons, atls, mats, section, icon_id):
    mname = (icons.get(section) or {}).get("%03d" % icon_id)
    if not mname:
        return None, "no %s[%03d]" % (section, icon_id)
    md = mats.get(mname)
    if not md:
        return None, "no MaterialDef %r" % mname
    at = atls.get(md.get("AtlasRef"))
    if at is None:
        return None, "AtlasRef %r missing" % md.get("AtlasRef")
    tex = None
    for t in at["Textures"]:
        if t.get("RefName") in (mname, md.get("Name")):
            tex = t
            break
    if tex is None:
        return None, "no texture in %s for %r" % (at["Name"], mname)
    fp = os.path.join(WID, tex["FileName"].replace("/", os.sep))
    if not os.path.exists(fp):
        return None, "missing file %s" % tex["FileName"]
    return (mname, at["Name"], tex["FileName"], fp), None


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    icons, atls, mats = load()

    # icon_id comes from the entity record (probe_icon_cases.py), NOT from its id:
    # the Barracks is unit 12 but icon_id 2, the TC is unit 71 but icon_id 28.
    cases = [("2", "Barracks 兵营 (unit 12)"), ("28", "Town Center 城镇中心 (unit 71/42/109)"),
             ("34", "House 房屋 (unit 70)"), ("35", "Farm 农田 (unit 50)"),
             ("7", "Castle 城堡 (unit 82)"), ("37", "Wonder 奇观 (unit 182)"),
             ("40", "Lumber Camp 伐木场 (unit 889)"), ("58", "Colosseum (unit 263)"),
             ("94", "action icon (unit 682)"),
             ("15", "Villager 村民 (unit 83)"), ("8", "Militia 民兵 (unit 74)"),
             ("17", "Archer 步弓手 (unit 4)")]
    for icon_id, label in cases:
        print("\n=== icon_id %s  %s ===" % (icon_id, label))
        for section in ("Units", "Buildings"):
            got, why = resolve(icons, atls, mats, section, int(icon_id))
            if not got:
                print("  %-10s %s" % (section, why))
                continue
            mname, atlas, rel, fp = got
            try:
                w, h, rgba = decode(fp)
            except Exception as exc:
                print("  %-10s %s -> %s" % (section, mname, exc))
                continue
            out = os.path.join(OUT, "%s_%s.png" % (section, icon_id))
            png(out, w, h, rgba)
            print("  %-10s %-28s %-22s %dx%d -> %s"
                  % (section, mname, os.path.basename(rel), w, h, os.path.basename(out)))

    # a tech, to prove the same chain serves them
    for icon_id in (6, 105):
        got, why = resolve(icons, atls, mats, "Techs", icon_id)
        print("\n=== tech icon_id %s ===" % icon_id)
        if not got:
            print("  %s" % why)
            continue
        mname, atlas, rel, fp = got
        w, h, rgba = decode(fp)
        out = os.path.join(OUT, "Techs_%s.png" % icon_id)
        png(out, w, h, rgba)
        print("  %-28s %-22s %dx%d -> %s" % (mname, os.path.basename(rel), w, h,
                                             os.path.basename(out)))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

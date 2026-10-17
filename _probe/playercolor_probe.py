# -*- coding: utf-8 -*-
"""Decode the PLAYER-COLOUR layer of real DE sprites to settle how player
colour is applied.

Uses the corrected SLD layout established earlier in this project:
  * 16-byte file header : <4s 2H 2H I   (sig, ver, num_frames, u1, u2, u3)
  * 12-byte frame header: canvas_w, canvas_h (u16), centre_x, centre_y (i16),
                          frame_type (u8), unknown (u8), frame_index (u16)
  * layer presence follows frame_type bits with the REAL bit order 0..4
    (main, shadow, unknown2, damage, playercolor) -- the openage doc's
    7/6/5/4/3 numbering is reversed and was empirically refuted here.
  * each layer: u32 content_len, then body, then pad to 4 bytes
      - main/shadow: x1,y1,x2,y2 (u16), flag, unk, then BC1/BC4 blocks
      - other layers (damage, playercolor): flag, unk, then pixel data

Question: does the player-colour layer contain palette INDICES (implying a
palette lookup via palettes.conf) or a grayscale intensity MASK (implying a
multiply by the team colour in spritecolors.json)?

Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import struct
from collections import Counter
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "sld")

u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
i16 = lambda b, o: struct.unpack_from("<h", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]

LAYER_BITS = [(0, "main", False), (1, "shadow", True), (2, "unknown2", False),
              (3, "damage", False), (4, "playercolor", True)]

def walk(path, max_frames=1):
    b = open(path, "rb").read()
    if b[:4] != b"SLDX":
        return None
    ver, nf = u16(b, 4), u16(b, 6)
    u1, u2, u3 = u16(b, 8), u16(b, 10), u32(b, 12)
    off = 16
    frames = []
    for fi in range(min(nf, max_frames)):
        cw, ch, cx, cy = u16(b, off), u16(b, off + 2), i16(b, off + 4), i16(b, off + 6)
        ft, unk, fidx = u8(b, off + 8), u8(b, off + 9), u16(b, off + 10)
        off += 12
        fr = dict(idx=fi, cw=cw, ch=ch, cx=cx, cy=cy, ft=ft, layers=[])
        for bit, name, isbc4 in LAYER_BITS:
            if not (ft & (1 << bit)):
                continue
            clen = u32(b, off)
            body = off + 4
            L = dict(name=name, clen=clen, bit=bit, body=body,
                     comp="BC4" if isbc4 else "BC1")
            if name in ("main", "shadow"):
                x1, y1, x2, y2 = (u16(b, body), u16(b, body + 2),
                                  u16(b, body + 4), u16(b, body + 6))
                L.update(x1=x1, y1=y1, x2=x2, y2=y2, w=x2 - x1, h=y2 - y1,
                         pixel_off=body + 10)
            else:
                L.update(flag1=u8(b, body), unk=u8(b, body + 1),
                         pixel_off=body + 2)
            off += clen
            off += (4 - (clen % 4)) % 4
            fr["layers"].append(L)
        frames.append(fr)
        break
    return dict(ver=ver, nf=nf, u1=u1, u2=u2, u3=u3, frames=frames,
                consumed=off, size=len(b))

def bc1_block(blk):
    c0, c1 = struct.unpack_from("<HH", blk, 0)
    idx = struct.unpack_from("<I", blk, 4)[0]
    def ch(c):
        return ((c >> 11 & 31) * 255 // 31, (c >> 5 & 63) * 255 // 63,
                (c & 31) * 255 // 31)
    a, b2 = ch(c0), ch(c1)
    if c0 > c1:
        c2 = tuple((2 * a[i] + b2[i]) // 3 for i in range(3))
        c3 = tuple((a[i] + 2 * b2[i]) // 3 for i in range(3))
        lut = [a, b2, c2, c3]
    else:
        lut = [a, b2, tuple((a[i] + b2[i]) // 2 for i in range(3)), (0, 0, 0)]
    return [lut[idx >> (2 * k) & 3] for k in range(16)]

def bc4_block(blk):
    c0, c1 = blk[0], blk[1]
    if c0 > c1:
        lut = [c0, c1] + [((7 - i) * c0 + i * c1) // 7 for i in range(1, 7)]
    else:
        lut = [c0, c1] + [((5 - i) * c0 + i * c1) // 5 for i in range(1, 5)] + [0, 255]
    v = int.from_bytes(blk[2:8], "little")
    return [lut[v >> (3 * k) & 7] for k in range(16)]

os.makedirs(OUT, exist_ok=True)
for name in ("u_arc_archer_idlea_x1.sld", "u_cav_knight_idlea_x1.sld",
             "u_inf_militia_idlea_x1.sld", "u_monk_west_idlea_x1.sld"):
    p = os.path.join(GP, name)
    if not os.path.exists(p):
        print("missing", name)
        continue
    r = walk(p)
    print("=" * 72)
    print("%s  size=%d ver=%s nf=%d u2=0x%04x u3=0x%08x consumed=%d/%d"
          % (name, r["size"], r["ver"], r["nf"], r["u2"], r["u3"],
             r["consumed"], r["size"]))
    f = r["frames"][0]
    print("   frame0 ft=0x%02x (bits %s) canvas %dx%d layers=%s"
          % (f["ft"], [n for bit, n, _ in LAYER_BITS if f["ft"] & (1 << bit)],
             f["cw"], f["ch"], [(l["name"], l["clen"]) for l in f["layers"]]))
    for L in f["layers"]:
        if L["name"] != "playercolor":
            continue
        px = L["pixel_off"]
        # try to decode as BC4 (8 bytes per 4x4 block) and report value spread
        # first: how many distinct bytes in the raw payload?
        raw = open(p, "rb").read()[px:px + min(4096, L["clen"] - 2)]
        c = Counter(raw)
        print("      playercolor payload: clen=%d  distinct bytes in first 4KB=%d"
              % (L["clen"], len(c)))
        print("      byte histogram (top 12): %s" % c.most_common(12))
        # decode a few BC4 blocks
        vals = []
        for k in range(0, min(len(raw) // 8, 64)):
            vals.extend(bc4_block(raw[k * 8:k * 8 + 8]))
        vc = Counter(vals)
        print("      BC4-decoded values (first 64 blocks, 1024 px): distinct=%d"
              % len(vc))
        print("      value histogram (top 12): %s" % vc.most_common(12))
        print("      min=%s max=%s" % (min(vals), max(vals)))

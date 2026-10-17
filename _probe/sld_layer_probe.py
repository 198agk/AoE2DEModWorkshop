# -*- coding: utf-8 -*-
"""Decisive test: for DE (modern) sprites, how is player colour applied?

The graphics survey asserted "making a unit red is editing a 2-16 KB text
palette; player colour is a palette swap, not a shader."  Two facts already
argue against that for DE sprites:
  * palettes.conf ids 64-71 ("New Unit player colors") are ALL
    playercolor_black.pal placeholders.
  * no installed mod ships any palette.

This script tests the competing hypothesis directly:
  H_palette : the SLD stores palette INDICES; the engine looks them up in the
              palette named by palettes.conf, so editing playercolor_red.pal
              recolours units.
  H_channel : the SLD stores a player-colour CHANNEL (an intensity mask); the
              engine multiplies it by the team colour from spritecolors.json,
              so the .pal files are legacy and editing them does nothing for
              modern sprites.

Discriminator: decode the playercolor-flagged layer of a real DE unit sprite
and look at its pixel content.
  * palette indices across a 256/1024-entry palette would look like scattered
    indices reusing the whole range
  * a player-colour mask looks like a smooth grayscale ramp / near-constant
    small set of intensity values

Read-only. Uses Pillow only to decode BC textures.
"""
import os
import struct
import zlib
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def parse_sld(path):
    b = open(path, "rb").read()
    assert b[0:4] == b"SLDX", b[0:4]
    version = u16(b, 4)
    num_frames = u16(b, 6)
    # 16-byte file header: <4s 4H I  -> sig, v, num_frames, ?, ?, trailer
    o = 16
    frames = []
    for fi in range(num_frames):
        # 12-byte frame header: <4H 2B H
        ft, u1, findex, layer_count, unk_a, unk_b, odd = struct.unpack_from(
            "<HHHHBBH", b, o)
        o += 12
        layers = []
        for li in range(layer_count):
            # layer: u16 flags/order + u16 shape_count, then shapes
            lf, sc = struct.unpack_from("<HH", b, o)
            o += 4
            shapes = []
            for si in range(sc):
                if li == 0:
                    w, h, cx, cy = struct.unpack_from("<4H", b, o)
                    o += 8
                    # hotspot + drawblock count
                    hx, hy = struct.unpack_from("<2h", b, o)
                    o += 4
                    nblk = u16(b, o)
                    o += 2
                    # command array length then commands then pixel data
                    clen = u16(b, o)
                    o += 2 + clen
                    shapes.append(dict(w=w, h=h, nblk=nblk))
                    # pixel data
                    for _ in range(nblk):
                        # draw block: u16 cmd, i16 x, y, w, h
                        o += 10
                        # compressed size then data
                        sz = struct.unpack_from("<I", b, o)[0]
                        o += 4 + sz
                else:
                    # shadow / player colour layers use a different shape rec
                    w, h = struct.unpack_from("<2H", b, o)
                    o += 4
                    hx, hy = struct.unpack_from("<2h", b, o)
                    o += 4
                    nblk = u16(b, o)
                    o += 2
                    clen = u16(b, o)
                    o += 2 + clen
                    shapes.append(dict(w=w, h=h, nblk=nblk))
                    for _ in range(nblk):
                        o += 10
                        sz = struct.unpack_from("<I", b, o)[0]
                        o += 4 + sz
            layers.append(dict(lf=lf, sc=sc, shapes=shapes))
        frames.append(dict(ft=ft, layer_count=layer_count, layers=layers))
        if fi >= 0:
            break
    return dict(version=version, num_frames=num_frames, frame0=frames[0],
                consumed=o, size=len(b), head=b[:32])


for name in ("u_arc_archer_idlea_x1.sld", "u_cav_knight_idlea_x1.sld",
             "b_west_town_center_age2_back_x1.sld"):
    p = os.path.join(GP, name)
    print("=" * 72)
    print(name, os.path.getsize(p))
    try:
        r = parse_sld(p)
    except Exception as e:
        print("   parse error:", type(e).__name__, e)
        continue
    print("   version", r["version"], "num_frames", r["num_frames"])
    print("   head 32B:", r["head"].hex())
    f = r["frame0"]
    print("   frame0 frame_type=0x%02x layer_count=%d" % (f["ft"], f["layer_count"]))
    for i, l in enumerate(f["layers"]):
        print("     layer %d flags=0x%04x shapes=%d %s"
              % (i, l["lf"], l["sc"], l["shapes"][:2]))

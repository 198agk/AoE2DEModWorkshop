# -*- coding: utf-8 -*-
"""Determine the true SLD frame-layer walk.

Facts: frame0 header @16 (12 B) -> layers @28.  main size=412 OK (28->440),
shadow size=574 OK (440->1014).  Frame1 header is at 1304 (canvas 200x200,
idx==1), so frame0 occupies 16..1303 and trailing layers = 290 bytes.

u32 @1014 = 0x00B20000 (absurd) but u32 @1016 = 178 (plausible).  Hypothesis:
layers after the first are padded to 4-byte alignment, OR the walk uses a
different convention.

Method: for every candidate start s in [1014,1304) test whether a layer at s
with declared u32 size lands exactly on 1304 (= last layer).  Then chain
backwards.  Also verify the walk on frames 1..4 by requiring the next frame
header's frame_index to increment.  Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]


def layer_at(b, s):
    """Try to read a layer with the rect+cmdarray shape at s. Returns dict/None."""
    if s + 16 > len(b):
        return None
    size = u32(b, s)
    if size < 16 or s + size > len(b):
        return None
    x1, y1, x2, y2 = struct.unpack_from("<4H", b, s + 4)
    f8, ncmd = struct.unpack_from("<2H", b, s + 12)
    if s + 16 + 2 * ncmd + 8 > len(b):
        return None
    cmds = [(u8(b, s + 16 + 2 * i), u8(b, s + 17 + 2 * i)) for i in range(ncmd)]
    draws = sum(c[1] for c in cmds)
    comp = 16 + 2 * ncmd + 8 * draws
    return dict(start=s, size=size, rect=(x1, y1, x2, y2), w=x2 - x1, h=y2 - y1,
                f8=f8, ncmd=ncmd, draws=draws, comp=comp, exact=(comp == size))


name = "u_arc_archer_idlea_x1.sld"
b = open(os.path.join(GP, name), "rb").read()
print("=" * 78)
print("H1  exhaustive boundary search: which start makes a layer END at frame1 (1304)?")
FRAME1 = 1304
for s in range(1012, FRAME1):
    L = layer_at(b, s)
    if L and s + L["size"] == FRAME1:
        print("   start=%-5d size=%-6d rect=(%d,%d)-(%d,%d) %dx%d ncmd=%-3d draws=%-4d comp=%-5d exact=%s"
              % (s, L["size"], L["rect"][0], L["rect"][1], L["rect"][2], L["rect"][3],
                 L["w"], L["h"], L["ncmd"], L["draws"], L["comp"], L["exact"]))

print()
print("H2  test the 4-byte-alignment walk on frames 0..5")
def walk(off, verbose=False):
    cw, ch, cx, cy, ft, unk, fi = struct.unpack_from("<2H 2h 2B H", b, off)
    p = off + 12
    got = []
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        # try unaligned then 4-byte aligned
        for cand in (p, p + ((4 - p % 4) % 4)):
            L = layer_at(b, cand)
            if L and L["exact"]:
                p = cand + L["size"]
                got.append((nm, L))
                break
        else:
            # fall back to declared size
            L = layer_at(b, p)
            if not L:
                return None, got, p
            p = p + L["size"]
            got.append((nm + "*", L))
    return (cw, ch, ft, fi), got, p

off = 16
ok = True
for k in range(6):
    hdr, got, p = walk(off)
    if hdr is None:
        print("   frame %d: parse failed at %d" % (k, p))
        ok = False
        break
    cw, ch, ft, fi = hdr
    print("   frame %-2d idx=%-4d ft=0x%02x canvas=%dx%d  layers: %s"
          % (k, fi, ft, cw, ch,
             "  ".join("%s@%d(sz=%d,%s)" % (nm, L["start"], L["size"],
                                            "exact" if L["exact"] else "approx") for nm, L in got)))
    if fi != k:
        print("      *** idx != k -> walk is WRONG ***")
        ok = False
        break
    off = p
print("   walk consistent for 6 frames:", ok)

print()
print("H3  if alignment is right, dump the trailing layers of frame 0")
hdr, got, p = walk(16)
for nm, L in got:
    print("   %-11s @%-6d size=%-6d rect=(%d,%d)-(%d,%d) %dx%d ncmd=%-3d draws=%-4d comp=%-5d exact=%s"
          % (nm, L["start"], L["size"], L["rect"][0], L["rect"][1], L["rect"][2], L["rect"][3],
             L["w"], L["h"], L["ncmd"], L["draws"], L["comp"], L["exact"]))
print("   frame0 end =", p, "(frame1 predicted at %d)" % p)

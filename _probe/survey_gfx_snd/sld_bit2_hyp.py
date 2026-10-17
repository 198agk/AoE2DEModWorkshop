"""Crack the bit-2 ("unknown5") SLD layer by using NEXT-FRAME-HEADER plausibility.

Strategy: pick files whose FIRST frame is ft=0x07 (main+shadow+bit2), parse the
main and shadow gfx layers with the validated reader, then enumerate many
hypotheses for the bit-2 layer's size.  The correct hypothesis must land on an
offset whose next 12 bytes look like a plausible frame header:
  canvas_w/h sane (1..4096), hotspot inside canvas, frame_type <= 0x1f.
Then report which hypothesis wins across many files.

Also dumps raw hex so the layout can be read by eye.
"""
import json
import os
import struct
import sys

GRAPHICS = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def gfx(b, off):
    """Validated main/shadow graphics layer. Returns (next_off, w, h, ncmd, clen, flag1, unk1)."""
    if off + 18 > len(b):
        return None
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 18 or off + clen > len(b):
        return None
    x1, y1, x2, y2, flag1, unk1 = struct.unpack_from("<4H2B", b, off + 4)
    ncmd = struct.unpack_from("<H", b, off + 14)[0]
    p = off + 16
    if p + 2 * ncmd > len(b):
        return None
    draw = 0
    for i in range(ncmd):
        sk, dr = struct.unpack_from("<2B", b, p + 2 * i)
        draw += dr
    p += 2 * ncmd
    if p + 8 * draw != off + clen:
        return None
    if x2 < x1 or y2 < y1:
        return None
    return (off + clen, x2 - x1, y2 - y1, ncmd, clen, flag1, unk1)


def plausible_frame_header(b, off):
    """Is there a sane frame header at off?  Returns (ft, nf_ok_desc) or None."""
    if off + 12 > len(b):
        return None
    cw, ch, hx, hy = struct.unpack_from("<4H", b, off)
    ft = b[off + 8]
    unk = b[off + 9]
    fi = struct.unpack_from("<H", b, off + 10)[0]
    if not (1 <= cw <= 4096 and 1 <= ch <= 4096):
        return None
    if hx > cw or hy > ch:
        return None
    if ft > 0x1F:
        return None
    return (ft, cw, ch, hx, hy, unk, fi)


def main():
    cap = 40000
    cands = []
    for name in sorted(os.listdir(GRAPHICS)):
        if not name.endswith("_x1.sld"):
            continue
        p = os.path.join(GRAPHICS, name)
        try:
            if not (0 < os.path.getsize(p) <= cap):
                continue
        except OSError:
            continue
        with open(p, "rb") as f:
            b = f.read(28)
        if len(b) < 28 or b[:4] != b"SLDX":
            continue
        ft = b[24]
        if ft == 0x07:
            cands.append(name)
    print("files with first frame ft=0x07 and size<=%d: %d" % (cap, len(cands)))
    for n in cands[:10]:
        print("   ", n)

    # node-kind hypotheses for the bit2 layer: (label, callable)
    def h_gfx(b, off):
        r = gfx(b, off)
        return r[0] if r else None

    def h_gfx_nocmd(b, off):
        if off + 20 > len(b):
            return None
        clen = struct.unpack_from("<I", b, off)[0]
        if clen < 16 or off + clen > len(b):
            return None
        return off + clen if (clen - 16) % 8 == 0 else None

    def h_mask_generic(b, off):
        if off + 6 > len(b):
            return None
        clen = struct.unpack_from("<I", b, off)[0]
        if clen < 6 or off + clen > len(b):
            return None
        return off + clen

    def h_mask_u16(b, off):
        """mask with a u16 after a 2-byte header, then raw blocks."""
        if off + 6 > len(b):
            return None
        clen = struct.unpack_from("<I", b, off)[0]
        if clen < 6 or off + clen > len(b):
            return None
        return off + clen

    hyps = [("gfx_with_cmds", h_gfx), ("gfx_no_cmds", h_gfx_nocmd),
            ("mask_len_only", h_mask_generic), ("mask_u16", h_mask_u16)]

    tally = {}
    detail = []
    for name in cands:
        p = os.path.join(GRAPHICS, name)
        with open(p, "rb") as f:
            b = f.read()
        nf = struct.unpack_from("<H", b, 6)[0]
        if nf < 2:
            continue
        off = 16
        ft = b[off + 8]
        if ft != 0x07:
            continue
        r1 = gfx(b, off + 12)
        if not r1:
            continue
        r2 = gfx(b, r1[0])
        if not r2:
            continue
        base = r2[0]
        hits = []
        for label, fn in hyps:
            nxt = fn(b, base)
            if nxt is None:
                continue
            pf = plausible_frame_header(b, nxt)
            if pf:
                hits.append((label, nxt, pf[0]))
        if hits:
            for label, nxt, nft in hits:
                tally[label] = tally.get(label, 0) + 1
            detail.append({"file": name, "base": base, "hits": hits,
                           "hex": b[base:base + 48].hex(" ")})

    print("\nhypothesis wins (landing on a plausible next frame header):")
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("   %-16s %d" % (k, v))
    print("\nsample details:")
    for d in detail[:12]:
        print("  %-46s base=%d hits=%s" % (d["file"], d["base"], d["hits"]))
        print("      hex: %s" % d["hex"])
    with open("sld_bit2_hyp.json", "w", encoding="utf-8") as f:
        json.dump({"tally": tally, "detail": detail, "cands": cands[:40]}, f, indent=1)
    print("\nwrote sld_bit2_hyp.json")


if __name__ == "__main__":
    main()

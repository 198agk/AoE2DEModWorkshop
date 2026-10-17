"""Test competing global interpretations of bit 2 of SLD frame_type.

Earlier result: reversed bit mapping is correct (bit0=main, bit1=shadow,
bit3=damage, bit4=playercolor) but rich frame types do not walk to EOF.
bit 2 ("unknown5") is the suspect.  This script tries, for the SAME file set,
a handful of global interpretations of bit 2 and reports how many files reach
exact EOF under each.  Nothing is written to the game tree.

Interpretations tested
  A  bit2 -> gfx layer, 16-byte offsets header + cmd array + blocks   (current)
  B  bit2 -> no layer at all (ignored)
  C  bit2 -> mask layer (2-byte header, optional cmd array)
  D  bit2 -> mask layer (2-byte header, exactly 6 bytes)
  E  bit2 -> gfx layer but with NO command array (blocks only)
  F  bit2 -> gfx layer, 16-byte header, cmd array, but blocks NOT 8/block
"""
import json
import os
import struct
import sys

GRAPHICS = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
MAIN, SHADOW, UNK, DAMAGE, PC = 0x01, 0x02, 0x04, 0x08, 0x10


def read_gfx_layer(b, off):
    """16-byte offsets header + u16 ncmd + cmds + BC1 blocks. Validated."""
    if off + 22 > len(b):
        return None
    (x1, y1, x2, y2) = struct.unpack_from("<4H", b, off)
    flag1, unk1 = struct.unpack_from("<2B", b, off + 8)
    clen = struct.unpack_from("<I", b, off + 12 - 12)[0] if False else None
    return (x1, y1, x2, y2, flag1, unk1, off + 10)


def gfx(b, off):
    """Returns (next_off, w, h, ncmd) or None. off points at layer start (clen field)."""
    if off + 22 > len(b):
        return None
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 18 or off + clen > len(b):
        return None
    # layout: clen u32 @0, 4H offsets @4, flag1/unk1 2B @12, ncmd u16 @14, cmds @16
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
    w, h = x2 - x1, y2 - y1
    return (off + clen, w, h, ncmd)


def gfx_nocmd(b, off):
    """bit2 as gfx with no command array: content_length == 16 + 8*blocks."""
    if off + 20 > len(b):
        return None
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 20 or off + clen > len(b):
        return None
    if (clen - 16) % 8:
        return None
    x1, y1, x2, y2, flag1, unk1 = struct.unpack_from("<4H2B", b, off + 4)
    return (off + clen, x2 - x1, y2 - y1, 0)


def mask(b, off, with_cmds, exact6):
    if off + 6 > len(b):
        return None
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 6 or off + clen > len(b):
        return None
    if exact6 and clen != 6:
        return None
    if not with_cmds:
        return (off + clen, 0, 0, 0)
    # 2-byte header then u16 ncmd then cmds then BC4 blocks
    if off + 8 > len(b):
        return None
    ncmd = struct.unpack_from("<H", b, off + 6)[0]
    p = off + 8
    if p + 2 * ncmd > len(b):
        return None
    draw = 0
    for i in range(ncmd):
        sk, dr = struct.unpack_from("<2B", b, p + 2 * i)
        draw += dr
    p += 2 * ncmd
    if p + 8 * draw != off + clen:
        return None
    return (off + clen, 0, 0, ncmd)


def walk(path, mode):
    with open(path, "rb") as f:
        b = f.read()
    if len(b) < 16 or b[:4] != b"SLDX":
        return ("badsig", -1)
    nf = struct.unpack_from("<H", b, 6)[0]
    off = 16
    for fi in range(nf):
        if off + 12 > len(b):
            return ("eof@header %d/%d" % (fi, nf), off)
        ft = b[off + 8]
        off += 12
        if ft & ~0x1F:
            return ("highbits ft=%02x" % ft, off)
        layers = []
        if ft & MAIN:
            layers.append("main")
        if ft & SHADOW:
            layers.append("shadow")
        if ft & UNK:
            layers.append("unk2")
        if ft & DAMAGE:
            layers.append("damage")
        if ft & PC:
            layers.append("pc")
        for lay in layers:
            if lay == "main" or lay == "shadow":
                r = gfx(b, off)
            elif lay == "unk2":
                if mode == "A" or mode == "F":
                    r = gfx(b, off)
                elif mode == "B":
                    continue
                elif mode == "C":
                    r = mask(b, off, True, False)
                elif mode == "D":
                    r = mask(b, off, False, True)
                elif mode == "E":
                    r = gfx_nocmd(b, off)
                else:
                    r = None
            else:
                r = mask(b, off, False, True)
            if r is None:
                return ("fail@ft=%02x@%d" % (ft, off), off)
            off = r[0]
    return ("ok" if off == len(b) else "end=%d filelen=%d" % (off, len(b)), off)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 200 * 1024
    cands = []
    for name in sorted(os.listdir(GRAPHICS)):
        if not name.endswith("_x1.sld"):
            continue
        p = os.path.join(GRAPHICS, name)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if 0 < sz <= cap:
            cands.append((name, sz))
    cands.sort(key=lambda t: t[0])
    step = max(1, len(cands) // n)
    sample = cands[::step][:n]
    print("pool=%d sampled=%d cap=%d" % (len(cands), len(sample), cap))

    modes = ["A", "B", "C", "D", "E", "F"]
    results = {m: {"ok": 0, "reasons": {}} for m in modes}
    solved = {m: [] for m in modes}
    for name, sz in sample:
        p = os.path.join(GRAPHICS, name)
        for m in modes:
            try:
                why, off = walk(p, m)
            except Exception as e:
                why = "exc %s" % e
            if why == "ok":
                results[m]["ok"] += 1
                solved[m].append(name)
            else:
                key = why.split("@")[0] if why.startswith(("fail@", "eof@")) else why
                results[m]["reasons"][key] = results[m]["reasons"].get(key, 0) + 1
        print("  %-52s %s" % (name, {m: walk(p, m)[0] for m in ("A", "B", "C")}))

    print()
    for m in modes:
        r = results[m]
        top = sorted(r["reasons"].items(), key=lambda kv: -kv[1])[:8]
        print("mode %s exact-EOF %d/%d  %s" % (m, r["ok"], len(sample), top))
        if r["ok"] and r["ok"] <= 12:
            print("     solved:", solved[m][:12])

    with open("sld_bit2.json", "w", encoding="utf-8") as f:
        json.dump({"modes": {m: results[m] for m in modes},
                   "solved": solved,
                   "sample": [s[0] for s in sample]}, f, indent=1)
    print("\nwrote sld_bit2.json")


if __name__ == "__main__":
    main()

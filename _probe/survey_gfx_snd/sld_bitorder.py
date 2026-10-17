"""SLD mapping test v4 -- hypothesis 'bit N = Nth layer present, ascending'.

Under this hypothesis the layer ORDER is fixed (main, shadow, unknown5, damage,
playercolor) and frame_type bit N set means slot N is present.  We walk each
file requiring the walk to land exactly on EOF after num_frames frames.

We also vary how strictly a mask layer's content_length is validated, because
the openage doc's "2-byte mask header, content_length == 6" claim may only hold
for EMPTY masks.
"""
import struct, os, glob, json, collections, random, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(GAME, "resources", "_common", "drs", "graphics")

u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
pad = lambda n: (4 - (n % 4)) % 4

SLOTS = ["main", "shadow", "unknown5", "damage", "playercolor"]
GFX_SLOTS = {"main", "shadow", "unknown5"}


def as_gfx(b, off, target):
    if off + 16 > len(b):
        return None
    clen = u32(b, off)
    if clen < 16:
        return None
    o1, o2, o3, o4 = u16(b, off + 4), u16(b, off + 6), u16(b, off + 8), u16(b, off + 10)
    if o3 < o1 or o4 < o2 or o3 > 8192 or o4 > 8192:
        return None
    ncmd = u16(b, off + 14)
    cmd = off + 16
    if cmd + ncmd * 2 > len(b):
        return None
    draw = 0
    for i in range(ncmd):
        draw += u8(b, cmd + i * 2 + 1)
    if (cmd + ncmd * 2 + draw * 8) - off != clen:
        return None
    return off + clen + pad(clen), dict(kind="gfx", clen=clen, w=o3 - o1, h=o4 - o2,
                                        flag1=u8(b, off + 12), unk=u8(b, off + 13),
                                        ncmd=ncmd, draw=draw)


def as_mask_strict(b, off, target):
    if off + 6 > len(b):
        return None
    clen = u32(b, off)
    if clen != 6:
        return None
    return off + 6 + pad(6), dict(kind="mask6", clen=6, flag1=u8(b, off + 4), unk=u8(b, off + 5))


def as_mask_loose(b, off, target):
    """Any content_length >= 6 whose padded end stays in the file."""
    if off + 6 > len(b):
        return None
    clen = u32(b, off)
    if clen < 6:
        return None
    end = off + clen + pad(clen)
    if end > target:
        return None
    return end, dict(kind="maskN", clen=clen, flag1=u8(b, off + 4), unk=u8(b, off + 5))


def walk(b, mask_fn):
    nf = u16(b, 6)
    target = len(b)
    off = 16
    frames = []
    for fi in range(nf):
        if off + 12 > target:
            return False, frames, off, "frame-header-EOF"
        ft = u8(b, off + 8)
        o = off + 12
        subs, kinds = [], []
        for i, slot in enumerate(SLOTS):
            if not (ft >> i) & 1:
                continue
            r = as_gfx(b, o, target) if slot in GFX_SLOTS else mask_fn(b, o, target)
            if r is None:
                return False, frames, o, "fail@ft=%02x@%d" % (ft, o)
            o, info = r
            subs.append(slot)
            kinds.append(info["kind"])
        frames.append((fi, ft, off, tuple(subs), tuple(kinds), o))
        off = o
    return (off == target), frames, off, ("eof" if off == target else "extra=%d" % (off - target))


def run(sample, mask_fn, label):
    exact = 0
    walked = 0
    ft_subsets = collections.defaultdict(collections.Counter)
    fails = []
    for p in sample:
        b = open(p, "rb").read()
        if len(b) < 16 or b[0:4] != b"SLDX":
            continue
        try:
            ok, frames, off, why = walk(b, mask_fn)
        except Exception as e:
            fails.append((os.path.basename(p), repr(e)))
            continue
        if ok:
            exact += 1
            walked += 1
            for (fi, ft, o, subs, kinds, endo) in frames:
                ft_subsets[ft]["+".join(subs) or "(none)"] += 1
        else:
            fails.append((os.path.basename(p), why))
    print("== %-14s exact-EOF %3d / %d   fails[:3]=%s" % (label, exact, len(sample), fails[:3]))
    return exact, ft_subsets


def main():
    random.seed(31)
    allsld = sorted(p for p in glob.glob(os.path.join(G, "*.sld")) if 0 < os.path.getsize(p) < 120000)
    print("pool:", len(allsld))
    sample = random.sample(allsld, min(300, len(allsld)))
    e1, ft1 = run(sample, as_mask_strict, "mask clen==6")
    e2, ft2 = run(sample, as_mask_loose, "mask any clen>=6")
    best = ft1 if e1 >= e2 else ft2
    print("\n=== frame_type -> slots (best variant) ===")
    for ft in sorted(best):
        tot = sum(best[ft].values())
        print("  ft=0x%02x (%3d) n=%-6d  %s" % (ft, ft, tot, best[ft].most_common(3)))
    json.dump(dict(n=len(sample), exact_strict=e1, exact_loose=e2,
                   ft_strict={("%02x" % k): dict(v) for k, v in ft1.items()},
                   ft_loose={("%02x" % k): dict(v) for k, v in ft2.items()}),
              open(os.path.join(OUT, "sld_solve4.json"), "w"), indent=1, ensure_ascii=False)
    print("\nwrote sld_solve4.json")


if __name__ == "__main__":
    main()

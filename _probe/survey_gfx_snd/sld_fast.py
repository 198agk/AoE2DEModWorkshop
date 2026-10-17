"""Fast sequential SLD hypothesis validator.

Instead of DFS over 2^5 subsets per frame (too slow), we test a small set of
candidate frame_type -> layer-presence mappings, walk each file frame by frame
with strict content_length validation, and require the walk to land EXACTLY on
EOF after exactly num_frames frames.  The mapping that solves the most files
wins; no trust in the openage doc's bit table.
"""
import struct, os, glob, json, collections, random, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(GAME, "resources", "_common", "drs", "graphics")

u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
pad = lambda n: (4 - (n % 4)) % 4


def parse_gfx(b, off, prev=None):
    if off + 16 > len(b):
        return None
    clen = u32(b, off)
    if clen < 16:
        return None
    o1, o2, o3, o4 = u16(b, off + 4), u16(b, off + 6), u16(b, off + 8), u16(b, off + 10)
    flag1 = u8(b, off + 12)
    unk = u8(b, off + 13)
    ncmd = u16(b, off + 14)
    if o3 < o1 or o4 < o2:
        return None
    if o3 > 8192 or o4 > 8192:
        return None
    cmd = off + 16
    if cmd + ncmd * 2 > len(b):
        return None
    draw = sum(u8(b, cmd + i * 2 + 1) for i in range(ncmd))
    if (cmd + ncmd * 2 + draw * 8) - off != clen:
        return None
    end = off + clen + pad(clen)
    return end, dict(kind="gfx", clen=clen, w=o3 - o1, h=o4 - o2,
                     flag1=flag1, unk=unk, ncmd=ncmd, draw=draw)


def parse_mask(b, off, prev=None):
    if off + 6 > len(b):
        return None
    clen = u32(b, off)
    if clen != 6:
        return None
    end = off + clen + pad(clen)
    return end, dict(kind="mask", clen=clen, flag1=u8(b, off + 4), unk=u8(b, off + 5))


# --- candidate mappings -------------------------------------------------
# Each maps a layer slot name to the bit tested in frame_type.
SLOTS = ["main", "shadow", "unknown5", "damage", "playercolor"]

CANDIDATES = {}
# doc table: bit7 main, bit6 shadow, bit5 unknown5, bit4 damage, bit3 playercolor
CANDIDATES["doc_msb"] = {"main": 7, "shadow": 6, "unknown5": 5, "damage": 4, "playercolor": 3}
# LSB-first mirror of the doc table
CANDIDATES["lsb"] = {"main": 0, "shadow": 1, "unknown5": 2, "damage": 3, "playercolor": 4}
# LSB-first but with only 4 slots (no "unknown5")
CANDIDATES["lsb4"] = {"main": 0, "shadow": 1, "damage": 2, "playercolor": 3}
# MSB-mirror of lsb4: bit7 main, bit6 shadow, bit5 damage, bit4 playercolor
CANDIDATES["msb4"] = {"main": 7, "shadow": 6, "damage": 5, "playercolor": 4}


def walk(b, order):
    """order: list of slot names in file order. Returns (ok, frames, end, why)."""
    nf = u16(b, 6)
    off = 16
    frames = []
    for fi in range(nf):
        if off + 12 > len(b):
            return False, frames, off, "frame-header-EOF"
        cw, ch, hx, hy = u16(b, off), u16(b, off + 2), u16(b, off + 4), u16(b, off + 6)
        ft = u8(b, off + 8)
        unk = u8(b, off + 9)
        o = off + 12
        present = []
        for slot in order:
            bit = ORDER_BIT[slot]
            if not (ft >> bit) & 1:
                continue
            r = (parse_gfx if slot in ("main", "shadow", "unknown5") else parse_mask)(b, o)
            if r is None:
                return False, frames, o, "layer-parse-fail@ft=%02x@%d" % (ft, o)
            o, info = r
            info["slot"] = slot
            present.append(info)
        frames.append(dict(fi=fi, off=off, ft=ft, unk=unk, cw=cw, ch=ch,
                           hx=hx, hy=hy, layers=[p["slot"] for p in present],
                           infos=present, end=o))
        off = o
    return True, frames, off, "done"


def try_file(path, order, ORDER_BIT):
    with open(path, "rb") as f:
        b = f.read()
    if len(b) < 16 or b[0:4] != b"SLDX":
        return None
    ok, frames, off, why = walk(b, order)
    return dict(ok=ok, why=why, end=off, size=len(b), nf=u16(b, 6),
                frames=frames, exact=(ok and off == len(b)))


def main():
    random.seed(7)
    allsld = sorted(p for p in glob.glob(os.path.join(G, "*.sld")) if os.path.getsize(p) > 0)
    sample = random.sample(allsld, 200)
    results = {}
    for cname, bits in CANDIDATES.items():
        global ORDER_BIT
        ORDER_BIT = bits
        order = [s for s in SLOTS if s in bits] if cname != "lsb4" else ["main", "shadow", "damage", "playercolor"]
        if cname == "msb4":
            order = ["main", "shadow", "damage", "playercolor"]
        n_exact = 0
        n_walked = 0
        bad = []
        ft_map = collections.defaultdict(collections.Counter)
        for p in sample:
            try:
                r = try_file(p, order, bits)
            except Exception as e:
                bad.append((os.path.basename(p), repr(e)))
                continue
            if r is None:
                continue
            if r["ok"]:
                n_walked += 1
                if r["exact"]:
                    n_exact += 1
                    for fr in r["frames"]:
                        ft_map[fr["ft"]][" ".join(fr["layers"]) or "(none)"] += 1
            else:
                bad.append((os.path.basename(p), r["why"]))
        results[cname] = dict(walked=n_walked, exact=n_exact, n=len(sample),
                              bad=bad[:8],
                              ft_map={("%02x" % k): dict(v) for k, v in ft_map.items()})
        print("== %-8s walked=%d exact-EOF=%d / %d  (first failures: %s)" %
              (cname, n_walked, n_exact, len(sample), bad[:3]))

    best = max(results, key=lambda k: results[k]["exact"])
    print("\nBEST MAPPING:", best, "->", CANDIDATES[best])
    print("\n=== frame_type -> layers under", best, "===")
    for ft in sorted(results[best]["ft_map"]):
        d = results[best]["ft_map"][ft]
        tot = sum(d.values())
        print("  ft=0x%s n=%-6d %s" % (ft, tot, sorted(d.items(), key=lambda x: -x[1])[:3]))

    json.dump(dict(best=best, candidates=results), open(os.path.join(OUT, "sld_fast.json"), "w"),
              indent=1, ensure_ascii=False)
    print("\nwrote sld_fast.json")


if __name__ == "__main__":
    main()

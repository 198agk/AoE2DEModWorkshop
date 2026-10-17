"""SLD layer mapping solver v2 -- iterative frontier DP.

At each frame we keep the SET of offsets reachable so far (normally size 1-3).
For every subset S of the 5 documented slots (in fixed order main, shadow,
unknown5, damage, playercolor) we compute the resulting end offset using strict
content_length validation.  A frame sequence is accepted when after num_frames
frames the frontier contains exactly filesize.

For each solved frame we record the observed frame_type byte together with the
slot subset that produced the accepted path, which yields the true bit->slot
mapping empirically (no trust in the openage doc).
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


def parse_gfx(b, off):
    if off + 16 > len(b):
        return None
    clen = u32(b, off)
    if clen < 16:
        return None
    o1, o2, o3, o4 = u16(b, off + 4), u16(b, off + 6), u16(b, off + 8), u16(b, off + 10)
    if o3 < o1 or o4 < o2 or o3 > 8192 or o4 > 8192:
        return None
    flag1, unk, ncmd = u8(b, off + 12), u8(b, off + 13), u16(b, off + 14)
    cmd = off + 16
    if cmd + ncmd * 2 > len(b):
        return None
    draw = 0
    for i in range(ncmd):
        draw += u8(b, cmd + i * 2 + 1)
    if (cmd + ncmd * 2 + draw * 8) - off != clen:
        return None
    return off + clen + pad(clen), dict(kind="gfx", clen=clen, w=o3 - o1, h=o4 - o2,
                                        flag1=flag1, unk=unk, ncmd=ncmd, draw=draw)


def parse_mask(b, off):
    if off + 6 > len(b):
        return None
    clen = u32(b, off)
    if clen != 6:
        return None
    return off + 6 + pad(6), dict(kind="mask", clen=6, flag1=u8(b, off + 4), unk=u8(b, off + 5))


def layer_at(b, off, slot):
    return parse_gfx(b, off) if slot in GFX_SLOTS else parse_mask(b, off)


def solve(path, verbose=False):
    b = open(path, "rb").read()
    if len(b) < 16 or b[0:4] != b"SLDX":
        return None
    nf = u16(b, 6)
    target = len(b)
    # frontier: off -> list of (subsets) reaching it; we keep one representative
    frontier = {16: ((), 0)}          # off -> (list of per-frame subsets, frames_done)
    for fi in range(nf):
        nxt = {}
        for off, (sub_path, _) in frontier.items():
            if off + 12 > len(b):
                continue
            ft = u8(b, off + 8)
            if u16(b, off + 10) != fi:      # frame_index must equal frame ordinal
                continue
            o0 = off + 12
            for mask in range(32):
                o = o0
                subs = []
                ok = True
                for i, slot in enumerate(SLOTS):
                    if not (mask >> i) & 1:
                        continue
                    r = layer_at(b, o, slot)
                    if r is None:
                        ok = False
                        break
                    o, info = r
                    subs.append(slot)
                    if o > target:
                        ok = False
                        break
                if not ok:
                    continue
                # the next frame must start with its own sequential index, or be EOF
                if fi + 1 < nf:
                    if o + 12 > target or u16(b, o + 10) != fi + 1:
                        continue
                ns = sub_path + (tuple(subs),)
                if o not in nxt:
                    nxt[o] = (ns, fi + 1)
        if not nxt:
            return dict(ok=False, why="dead-end at frame %d" % fi, nf=nf,
                        frames_done=fi, size=len(b))
        if len(nxt) > 4000:
            return dict(ok=False, why="frontier explosion at frame %d (%d)" % (fi, len(nxt)),
                        nf=nf, frames_done=fi, size=len(b))
        frontier = nxt
    if target in frontier:
        sub_path, _ = frontier[target]
        return dict(ok=True, exact=True, nf=nf, size=len(b), subsets=sub_path)
    return dict(ok=False, why="not EOF (offsets %s)" % sorted(frontier)[:5], nf=nf,
                frames_done=nf, size=len(b), offs=sorted(frontier)[:5])


def main():
    random.seed(11)
    allsld = sorted(p for p in glob.glob(os.path.join(G, "*.sld")) if os.path.getsize(p) > 0)
    # prefer small files first so the solver is fast
    small = sorted(allsld, key=os.path.getsize)[:400]
    sample = random.sample(small, 60) + random.sample(allsld, 20)
    ok_n = 0
    ft_subsets = collections.defaultdict(collections.Counter)
    fails = []
    for i, p in enumerate(sample):
        try:
            r = solve(p)
        except Exception as e:
            fails.append((os.path.basename(p), repr(e)))
            continue
        if r and r["ok"]:
            ok_n += 1
            b = open(p, "rb").read()
            off = 16
            for fi, subs in enumerate(r["subsets"]):
                ft = u8(b, off + 8)
                ft_subsets[ft][tuple(subs)] += 1
                o = off + 12
                for slot in subs:
                    o = layer_at(b, o, slot)[0]
                off = o
        else:
            fails.append((os.path.basename(p), (r or {}).get("why", "n/a")))
        if (i + 1) % 10 == 0:
            print("  ...%d/%d  solved=%d" % (i + 1, len(sample), ok_n), flush=True)
            sys.stdout.flush()

    print("\nSOLVED %d / %d" % (ok_n, len(sample)))
    print("first failures:", fails[:6])
    print("\n=== frame_type -> slot subset (from solved paths) ===")
    for ft in sorted(ft_subsets):
        tot = sum(ft_subsets[ft].values())
        top = ft_subsets[ft].most_common(4)
        print("  ft=0x%02x (%3d) n=%-6d  %s" % (ft, ft, tot,
              "  |  ".join("%s:%d" % ("+".join(s) or "(none)", c) for s, c in top)))

    json.dump(dict(n=len(sample), solved=ok_n, fails=fails[:40],
                   ft={("%02x" % k): {"+".join(s) or "(none)": c for s, c in v.items()}
                       for k, v in ft_subsets.items()}),
              open(os.path.join(OUT, "sld_solve2.json"), "w"), indent=1, ensure_ascii=False)
    print("\nwrote sld_solve2.json")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    main()

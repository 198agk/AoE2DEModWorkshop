"""SLD layer mapping solver v3 -- full DFS with memo, per-slot kind agnostic.

Each of the 5 documented layer slots may parse as a graphics layer (content
length validated as 16 + 2*ncmd + 8*sum(draw)) or as a mask layer (content
length == 6).  We DFS from (frame 0, offset 16) to (num_frames frames,
offset == filesize) and record, for every frame type observed on a successful
path, which slots were present and whether each slot parsed as gfx or mask.
No frame_index assumption.  Only small files so the search is tractable.
"""
import struct, os, glob, json, collections, random, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(GAME, "resources", "_common", "drs", "graphics")

u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
pad = lambda n: (4 - (n % 4)) % 4

SLOTS = ["s0", "s1", "s2", "s3", "s4"]


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
    end = off + clen + pad(clen)
    if end > target:
        return None
    return end, dict(kind="gfx", clen=clen, w=o3 - o1, h=o4 - o2,
                     flag1=u8(b, off + 12), unk=u8(b, off + 13), ncmd=ncmd, draw=draw)


def as_mask(b, off, target):
    if off + 6 > len(b):
        return None
    clen = u32(b, off)
    if clen != 6:
        return None
    end = off + 6 + pad(6)
    if end > target:
        return None
    return end, dict(kind="mask", clen=6, flag1=u8(b, off + 4), unk=u8(b, off + 5))


def solve(path, node_cap=200000):
    b = open(path, "rb").read()
    if len(b) < 16 or b[0:4] != b"SLDX":
        return None
    nf = u16(b, 6)
    target = len(b)
    seen = {}
    nodes = [0]

    def dfs(fi, off):
        nodes[0] += 1
        if nodes[0] > node_cap:
            raise RuntimeError("node cap")
        if fi == nf:
            return [] if off == target else None
        key = (fi, off)
        if key in seen:
            return seen[key]
        seen[key] = None
        if off + 12 > target:
            return None
        ft = u8(b, off + 8)
        o0 = off + 12
        for mask in range(32):
            o = o0
            subs = []
            kinds = []
            ok = True
            for i, slot in enumerate(SLOTS):
                if not (mask >> i) & 1:
                    continue
                r = as_gfx(b, o, target)
                if r is not None:
                    o, info = r
                else:
                    r = as_mask(b, o, target)
                    if r is None:
                        ok = False
                        break
                    o, info = r
                subs.append(slot)
                kinds.append(info["kind"])
            if not ok or o <= off:
                continue
            rest = dfs(fi + 1, o)
            if rest is not None:
                res = [(fi, ft, off, tuple(subs), tuple(kinds), o)] + rest
                seen[key] = res
                return res
        return None

    try:
        r = dfs(0, 16)
    except RuntimeError as e:
        return dict(ok=False, why=repr(e), nf=nf, size=len(b), nodes=nodes[0])
    if r is None:
        return dict(ok=False, why="no exact-EOF path", nf=nf, size=len(b), nodes=nodes[0])
    return dict(ok=True, nf=nf, size=len(b), nodes=nodes[0], frames=r)


def main():
    random.seed(23)
    allsld = sorted(p for p in glob.glob(os.path.join(G, "*.sld")) if 0 < os.path.getsize(p) < 250000)
    print("small .sld pool:", len(allsld))
    sample = random.sample(allsld, min(80, len(allsld)))
    ok_n = 0
    ft_subsets = collections.defaultdict(collections.Counter)
    kind_by_slot = collections.defaultdict(collections.Counter)
    fails = []
    for i, p in enumerate(sample):
        try:
            r = solve(p)
        except Exception as e:
            fails.append((os.path.basename(p), repr(e)))
            continue
        if r and r["ok"]:
            ok_n += 1
            for (fi, ft, off, subs, kinds, endo) in r["frames"]:
                ft_subsets[ft]["+".join(subs) or "(none)"] += 1
                for s, k in zip(subs, kinds):
                    kind_by_slot[s][k] += 1
        else:
            fails.append((os.path.basename(p), (r or {}).get("why", "n/a")))
        if (i + 1) % 10 == 0:
            print("  ...%d/%d solved=%d" % (i + 1, len(sample), ok_n), flush=True)

    print("\nSOLVED %d / %d" % (ok_n, len(sample)))
    print("first failures:", fails[:8])
    print("\n=== frame_type -> slot subset ===")
    for ft in sorted(ft_subsets):
        tot = sum(ft_subsets[ft].values())
        print("  ft=0x%02x (%3d) n=%-6d  %s" % (ft, ft, tot, ft_subsets[ft].most_common(4)))
    print("\n=== slot -> parsed kind ===")
    for s in sorted(kind_by_slot):
        print("  ", s, dict(kind_by_slot[s]))

    json.dump(dict(n=len(sample), solved=ok_n, fails=fails[:40],
                   ft={("%02x" % k): dict(v) for k, v in ft_subsets.items()},
                   kinds={k: dict(v) for k, v in kind_by_slot.items()}),
              open(os.path.join(OUT, "sld_solve3.json"), "w"), indent=1, ensure_ascii=False)
    print("\nwrote sld_solve3.json")


if __name__ == "__main__":
    sys.setrecursionlimit(200000)
    main()

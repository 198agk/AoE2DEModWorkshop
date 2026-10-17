"""Solve the SLD frame_type -> layer-presence mapping EMPIRICALLY.

Method: for each frame we consider all 2^5 subsets of {main, shadow, unknown5,
damage, playercolor} in the fixed doc order. Each subset gives a deterministic
end offset (or a structural failure). We then DFS from (frame 0, offset 16) to
(frame num_frames, filesize) requiring an EXACT landing on EOF. Any frame_type
value's mapping is then read off the successful path. This needs no trust in
the openage doc's bit table.
"""
import struct, os, glob, json, collections, random, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(GAME, "resources", "_common", "drs", "graphics")

def u8(b,o): return b[o]
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def i16(b,o): return struct.unpack_from("<h",b,o)[0]
def u32(b,o): return struct.unpack_from("<I",b,o)[0]

ORDER = ["main", "shadow", "unknown5", "damage", "playercolor"]
GFX = {"main", "shadow", "unknown5"}

def parse_gfx(b, off):
    """Return (end_offset, info) or None."""
    if off + 16 > len(b): return None
    clen = u32(b, off)
    if clen < 16: return None
    o1=u16(b,off+4); o2=u16(b,off+6); o3=u16(b,off+8); o4=u16(b,off+10)
    flag1=u8(b,off+12); unk=u8(b,off+13); ncmd=u16(b,off+14)
    if o3 < o1 or o4 < o2: return None
    if o4 > 4096 or o3 > 4096: return None
    cmdarr = off + 16
    end_cmd = cmdarr + ncmd*2
    if end_cmd > len(b): return None
    draw = 0
    for ci in range(ncmd):
        draw += u8(b, cmdarr + ci*2 + 1)
    px_end = end_cmd + draw*8
    if px_end - off != clen: return None       # content_length must match exactly
    end = off + clen
    end += (4 - (clen % 4)) % 4
    return end, dict(name="gfx", content_len=clen, w=o3-o1, h=o4-o2,
                     flag1=flag1, unk=unk, ncmd=ncmd, draw=draw)

def parse_mask(b, off):
    if off + 6 > len(b): return None
    clen = u32(b, off)
    if clen != 6: return None                  # mask layer: 4 len + 2 header
    end = off + clen
    end += (4 - (clen % 4)) % 4
    return end, dict(name="mask", content_len=clen, flag1=u8(b,off+4), unk=u8(b,off+5))

def layer_end(b, off, name):
    return parse_gfx(b, off) if name in GFX else parse_mask(b, off)

def frame_subsets(b, off):
    """For a frame at off, yield (ft, subset_tuple, new_off, layer_infos)."""
    if off + 12 > len(b): return
    ft = u8(b, off+8)
    out = []
    for mask in range(32):
        sub = tuple(ORDER[i] for i in range(5) if mask & (1 << i))
        o = off + 12
        infos = []
        ok = True
        for nm in sub:
            r = layer_end(b, o, nm)
            if r is None: ok = False; break
            o, info = r
            infos.append((nm, info))
        if ok and o <= len(b):
            out.append((ft, sub, o, infos))
    return ft, out

def solve(path, max_frames=None):
    with open(path,"rb") as f: b = f.read()
    if len(b) < 16 or b[0:4] != b"SLDX": return None
    nf = u16(b,6)
    limit = nf if max_frames is None else min(nf, max_frames)
    target = len(b) if max_frames is None else None
    # DFS with memo
    from functools import lru_cache
    seen = {}
    def dfs(fi, off):
        if fi == limit:
            return [] if (target is None or off == target) else None
        key = (fi, off)
        if key in seen: return seen[key]
        seen[key] = None
        r = frame_subsets(b, off)
        if r is None:
            return None
        ft, subs = r
        for ft2, sub, noff, infos in subs:
            if noff <= off: continue
            if target is not None and noff > target: continue
            rest = dfs(fi+1, noff)
            if rest is not None:
                res = [(fi, ft2, sub, off, noff, infos)] + rest
                seen[key] = res
                return res
        return None
    path_res = dfs(0, 16)
    return dict(path=os.path.relpath(path,GAME), size=len(b), nf=nf, limit=limit,
                solved=path_res is not None, frames=path_res)

# --- run over a sample -------------------------------------------------
random.seed(3)
allsld = [p for p in glob.glob(os.path.join(G,"*.sld")) if os.path.getsize(p) > 0]
random.shuffle(allsld)
sample = allsld[:120]
solved = []; failed = []
ft_to_subsets = collections.defaultdict(collections.Counter)
for p in sample:
    try:
        r = solve(p, max_frames=60)      # first 60 frames only; target-free
        r2 = solve(p, max_frames=None)   # full file, exact EOF required
    except Exception as e:
        failed.append((os.path.basename(p), repr(e))); continue
    if r2 and r2["solved"]:
        solved.append(r2)
        for (fi, ft, sub, a, bb, infos) in r2["frames"]:
            ft_to_subsets[ft][sub] += 1
    elif r and r["solved"]:
        failed.append((os.path.basename(p), "partial-only"))
    else:
        failed.append((os.path.basename(p), "unsolved"))

print("solve with exact-EOF: %d/%d solved, %d failed" % (len(solved), len(sample), len(failed)))
for f in failed[:10]: print("   FAIL", f)
print("\n=== frame_type -> layer subset (from exact-EOF solutions) ===")
for ft in sorted(ft_to_subsets):
    tot = sum(ft_to_subsets[ft].values())
    top = ft_to_subsets[ft].most_common(3)
    print("ft=0x%02x (%3d) n=%-6d %s" % (ft, ft, tot,
          "  ".join("%s:%d" % (str(s), c) for s, c in top)))

# layer kind sanity: which subset position is gfx vs mask
kinds = collections.Counter()
for r in solved:
    for (fi, ft, sub, a, bb, infos) in r["frames"]:
        for nm, info in infos:
            kinds[(nm, info["name"])] += 1
print("\n=== layer name -> parsed kind ===")
for k in sorted(kinds, key=str): print("   ", k, kinds[k])

with open(os.path.join(OUT,"sld_solve.json"),"w",encoding="utf-8") as f:
    json.dump(dict(
        n_sample=len(sample), n_solved=len(solved), failed=failed[:40],
        ft_to_subsets={("%02x"%k): {" ".join(v) if v else "(none)": c
                                     for v,c in cnt.items()}
                       for k,cnt in ft_to_subsets.items()},
        kinds={str(k):v for k,v in kinds.items()},
        example=[dict(path=r["path"], size=r["size"], nf=r["nf"],
                      frames=[dict(fi=fi, ft=ft, layers=" ".join(sub))
                              for (fi,ft,sub,a,b,inf) in r["frames"][:12]])
                 for r in solved[:6]],
    ), f, indent=1, ensure_ascii=False)

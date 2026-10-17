"""Definitive SLD structure probe.

Goal: determine the TRUE meaning of the SLD frame_type bitfield and the layer
header layouts, by walking every frame of real files and checking that the
content_length chain lands EXACTLY on the next frame / end of file.

Hypotheses for frame_type bit -> layer:
  H_doc : bit7 main, bit6 shadow, bit5 ???, bit4 damage, bit3 playercolor
  H_rev : bit0 main, bit1 shadow, bit2 ???, bit3 damage, bit4 playercolor
Layer kinds:
  "G" graphics layer: u32 len | 4 x u16 offsets | u8 flag1 | u8 unk | u16 ncmds | ncmds*2 | blocks
  "M" mask layer:      u32 len | u8 flag1 | u8 unk
"""
import struct, os, glob, json, collections, random

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(GAME, "resources", "_common", "drs", "graphics")

def u8(b,o): return b[o]
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def i16(b,o): return struct.unpack_from("<h",b,o)[0]
def u32(b,o): return struct.unpack_from("<I",b,o)[0]

HYPS = {
    "H_doc": {7:"main", 6:"shadow", 5:"unknown5", 4:"damage", 3:"playercolor"},
    "H_rev": {0:"main", 1:"shadow", 2:"unknown5", 3:"damage", 4:"playercolor"},
}
# which layer names are graphics layers (have offsets+blocks) vs mask layers
GFX  = {"main", "shadow", "unknown5"}
MASK = {"damage", "playercolor"}

def try_walk(path, hyp, max_frames=None):
    """Walk all frames under hypothesis hyp. Return (n_frames_ok, info, first_err)."""
    with open(path,"rb") as f: b = f.read()
    if len(b) < 16 or b[0:4] != b"SLDX":
        return None
    ver = u16(b,4); nf = u16(b,6)
    off = 16
    info = dict(path=os.path.relpath(path,GAME), size=len(b), ver=ver, num_frames=nf,
                u1=u16(b,8), u2=u16(b,10), u3=u32(b,12), frames=[])
    limit = nf if max_frames is None else min(nf, max_frames)
    names = HYPS[hyp]
    for fi in range(limit):
        if off + 12 > len(b):
            return (fi, info, "frame header past EOF at off=%d" % off)
        cw = u16(b,off); ch = u16(b,off+2); cx = i16(b,off+4); cy = i16(b,off+6)
        ft = u8(b,off+8); unk = u8(b,off+9); fidx = u16(b,off+10)
        off += 12
        fr = dict(idx=fi, canvas_w=cw, canvas_h=ch, cx=cx, cy=cy, frame_type=ft,
                  unk=unk, frame_index=fidx, layers=[])
        for bit in sorted(names, reverse=True):
            if not (ft & (1 << bit)): continue
            nm = names[bit]
            if nm in GFX:
                if off + 12 > len(b): return (fi, info, "gfx layer hdr past EOF")
                clen = u32(b,off)
                o1 = u16(b,off+4); o2 = u16(b,off+6); o3 = u16(b,off+8); o4 = u16(b,off+10)
                flag1 = u8(b,off+12); lunk = u8(b,off+13)
                ncmd = u16(b,off+14)
                body_end = off + 16 + ncmd*2
                if body_end > len(b): return (fi, info, "cmd array past EOF")
                drawsum = 0; skipsum = 0
                for ci in range(ncmd):
                    sk = u8(b, body_end - ncmd*2 + ci*2)
                    dr = u8(b, body_end - ncmd*2 + ci*2 + 1)
                    skipsum += sk; drawsum += dr
                px_end = body_end + drawsum*8
                fr["layers"].append(dict(name=nm, bit=bit, content_len=clen,
                    x1=o1,y1=o2,x2=o3,y2=o4,w=o3-o1,h=o4-o2, flag1=flag1,unk=lunk,
                    ncmd=ncmd, drawsum=drawsum, skipsum=skipsum,
                    interior=clen-4 - (16+ncmd*2+drawsum*8)))
            else:
                if off + 6 > len(b): return (fi, info, "mask layer hdr past EOF")
                clen = u32(b,off)
                flag1 = u8(b,off+4); lunk = u8(b,off+5)
                fr["layers"].append(dict(name=nm, bit=bit, content_len=clen,
                    flag1=flag1, unk=lunk, interior=clen-4-2))
            if clen == 0:
                return (fi, info, "zero content_len")
            off = off + clen
            pad = (4 - (clen % 4)) % 4
            off += pad
        info["frames"].append(fr)
    info["end_off"] = off
    info["file_size"] = len(b)
    info["exact"] = (off == len(b))
    info["remainder"] = len(b) - off
    return (limit, info, None)

def score(path, hyp):
    r = try_walk(path, hyp, max_frames=None)
    if r is None: return None
    n, info, err = r
    return dict(err=err, n=n, exact=info.get("exact"), rem=info.get("remainder"),
                expected_frames=info["num_frames"], end=info.get("end_off"), size=info["size"])

random.seed(11)
allsld = glob.glob(os.path.join(G,"*.sld"))
# exclude 0-byte files
nz = [p for p in allsld if os.path.getsize(p) > 0]
tiny = [p for p in nz if os.path.getsize(p) <= 4096]
random.shuffle(nz)
sample = tiny + nz[:60]
sample = list(dict.fromkeys(sample))
# limit each to first 40 frames for speed on huge files
results = {"H_doc": [], "H_rev": []}
for hyp in HYPS:
    for p in sample:
        try:
            r = try_walk(p, hyp, max_frames=40)
        except Exception as e:
            r = None
            results[hyp].append(dict(path=os.path.basename(p), exc=repr(e)))
            continue
        if r is None: continue
        n, info, err = r
        results[hyp].append(dict(path=os.path.basename(p), size=info["size"],
                                 nf=info["num_frames"], walked=n, err=err,
                                 exact=(info.get("exact") if n>=info["num_frames"] else None),
                                 remainder=info.get("remainder")))
    ok = sum(1 for r in results[hyp] if r.get("err") is None)
    ex = sum(1 for r in results[hyp] if r.get("exact"))
    print("%s : walked_clean=%d/%d  exact_to_EOF=%d" % (hyp, ok, len(results[hyp]), ex))

# frame_type histogram + layer presence for winning hypothesis
ft_hist = collections.Counter()
layer_presence = collections.Counter()
combo = collections.Counter()
for p in sample[:200]:
    try:
        r = try_walk(p, "H_rev", max_frames=6)
        r2 = try_walk(p, "H_doc", max_frames=6)
    except Exception:
        continue
    if not r: continue
    for fr in r[1]["frames"]:
        ft_hist[fr["frame_type"]] += 1
        combo[fr["frame_type"]] += 0
        for l in fr["layers"]:
            layer_presence[l["name"]] += 1
summary = dict(
    sample_size=len(sample),
    clean_H_doc=sum(1 for r in results["H_doc"] if r.get("err") is None),
    clean_H_rev=sum(1 for r in results["H_rev"] if r.get("err") is None),
    exact_H_doc=sum(1 for r in results["H_doc"] if r.get("exact")),
    exact_H_rev=sum(1 for r in results["H_rev"] if r.get("exact")),
    frame_type_hist=dict(ft_hist.most_common(40)),
    layer_presence_rev=dict(layer_presence),
)
print(json.dumps(summary, indent=1))

# Dump full detail for a handful of files under H_rev
detail = []
for nm in ["b_archaic_dock_age1_rubble_x1.sld","u_arc_bowman_death_x1.sld",
           "n_tree_oak_x1.sld","u_misc_relic_x1.sld"]:
    p = os.path.join(G,nm)
    if not os.path.exists(p): continue
    for hyp in ("H_doc","H_rev"):
        r = try_walk(p, hyp, max_frames=2)
        if r: detail.append(dict(hyp=hyp, err=r[2], info=r[1]))
with open(os.path.join(OUT,"sld_walk.json"),"w",encoding="utf-8") as f:
    json.dump(dict(summary=summary, results=results, detail=detail), f, indent=1, ensure_ascii=False)
print("\n=== detail (frame 0/1) ===")
for d in detail:
    i = d["info"]
    print("\n--", os.path.basename(i["path"]), d["hyp"], "err=", d["err"],
          "u2=0x%04x u3=0x%08x"%(i["u2"],i["u3"]), "exact=", i.get("exact"), "rem=", i.get("remainder"))
    for fr in i["frames"]:
        print("   frame", fr["idx"], "ft=0x%02x"%fr["frame_type"], "canvas", fr["canvas_w"], fr["canvas_h"], "hot", fr["cx"], fr["cy"])
        for l in fr["layers"]:
            print("      ", {k:v for k,v in l.items() if k!='name'}, l.get("name"))

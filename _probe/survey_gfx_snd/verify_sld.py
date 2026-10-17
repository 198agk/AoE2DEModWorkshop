"""Verify openage SLD spec against real AoE2DE .sld files by FULLY decoding frames."""
import struct, os, glob, json, collections, sys
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.dirname(os.path.abspath(__file__))

def u8(b,o): return b[o]
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def i16(b,o): return struct.unpack_from("<h",b,o)[0]
def u32(b,o): return struct.unpack_from("<I",b,o)[0]

def bc1_lut(c0, c1):
    def ch(c):
        r = (c & 0xF800) >> 11; g = (c & 0x07E0) >> 5; bl = c & 0x001F
        return (r*255//31, g*255//63, bl*255//31, 255)
    a, b = ch(c0), ch(c1)
    if c0 > c1:
        c2 = tuple((2*a[i] + b[i])//3 for i in range(3)) + (255,)
        c3 = tuple((a[i] + 2*b[i])//3 for i in range(3)) + (255,)
    else:
        c2 = tuple((a[i] + b[i])//2 for i in range(3)) + (255,)
        c3 = (0,0,0,0)
    return [a,b,c2,c3]

def bc4_lut(c0, c1):
    if c0 > c1:
        return [c0, c1] + [(( (7-i)*c0 + i*c1 )//7) for i in range(1,7)]
    else:
        return [c0, c1] + [(((5-i)*c0 + i*c1)//5) for i in range(1,5)] + [0, 255]

def decode_bc1_block(blk):
    c0, c1 = struct.unpack_from("<HH", blk, 0)
    idx = struct.unpack_from("<I", blk, 4)[0]
    lut = bc1_lut(c0, c1)
    px = []
    for _ in range(16):
        px.append(lut[idx & 3]); idx >>= 2
    return px

def decode_bc4_block(blk):
    c0, c1 = blk[0], blk[1]
    lut = bc4_lut(c0, c1)
    # 6 bytes of 3-bit indices = 48 bits, little-endian
    v = int.from_bytes(blk[2:8], "little")
    px = []
    for _ in range(16):
        px.append(lut[v & 7]); v >>= 3
    return px

def decode_layer(data, off, w, h, bc4=False, prev=None):
    """Decode a graphics layer at off in data. Returns RGBA image bytes or None."""
    bw = (w + 3)//4; bh = (h + 3)//4
    cmdlen = u16(data, off); off += 2
    cmds = []
    for i in range(cmdlen):
        cmds.append((u8(data,off), u8(data,off+1))); off += 2
    blocks = []
    # collect compressed blocks
    total_draw = sum(c[1] for c in cmds)
    for i in range(total_draw):
        blocks.append(data[off:off+8]); off += 8
    blkbytes = 8 if not bc4 else 8
    out = [[(0,0,0,0)]*(bw*4) for _ in range(bh*4)]
    bx = by = 0; bi = 0
    for (skip, draw) in cmds:
        for _ in range(skip):
            bx += 1
            if bx >= bw: bx = 0; by += 1
        for _ in range(draw):
            if bi >= len(blocks): break
            px = decode_bc4_block(blocks[bi]) if bc4 else decode_bc1_block(blocks[bi])
            bi += 1
            # place block
            for j in range(4):
                yy = by*4 + j
                if yy >= bh*4: continue
                for i in range(4):
                    xx = bx*4 + i
                    if xx >= bw*4: continue
                    if bc4:
                        a = 255 - px[j*4+i]   # shadow: invert
                        out[yy][xx] = (0,0,0,a)
                    else:
                        out[yy][xx] = px[j*4+i]
            bx += 1
            if bx >= bw: bx = 0; by += 1
    img = Image.new("RGBA", (bw*4, bh*4))
    px_out = img.load()
    for y in range(bh*4):
        row = out[y]
        for x in range(bw*4):
            px_out[x,y] = row[x]
    return img.crop((0,0,w,h)), off

def parse_sld(path, max_frames=3, render=None):
    with open(path,"rb") as f: b = f.read()
    sig = b[0:4].decode("latin1"); ver = u16(b,4); nf = u16(b,6)
    u1 = u16(b,8); u2 = u16(b,10); u3 = u32(b,12)
    res = dict(path=os.path.relpath(path,GAME), size=len(b), sig=sig, ver=ver,
               num_frames=nf, u1=u1, u2=u2, u3=u3, frames=[])
    off = 16
    for fi in range(min(nf, max_frames)):
        cw = u16(b,off); ch = u16(b,off+2); cx = i16(b,off+4); cy = i16(b,off+6)
        ft = u8(b,off+8); unk = u8(b,off+9); fidx = u16(b,off+10)
        off += 12
        fr = dict(idx=fi, canvas_w=cw, canvas_h=ch, center_x=cx, center_y=cy,
                  frame_type=ft, unk=unk, frame_index=fidx, layers=[])
        # layer order: main(bit7), shadow(bit6), ???(bit5), damage(bit4), playercolor(bit3)
        layer_defs = [(7,"main",False),(6,"shadow",True),(5,"unknown5",False),
                      (4,"damage",False),(3,"playercolor",True)]
        for bit, name, is_bc4 in layer_defs:
            if not (ft & (1<<bit)): continue
            clen = u32(b, off)
            lstart = off
            body = off + 4
            if name in ("main","shadow"):
                o1 = u16(b,body); o2 = u16(b,body+2); o3 = u16(b,body+4); o4 = u16(b,body+6)
                flag1 = u8(b,body+8); lunk = u8(b,body+9)
                w = o3-o1; h = o4-o2
                fr["layers"].append(dict(name=name, content_len=clen, x1=o1,y1=o2,x2=o3,y2=o4,
                                         w=w,h=h, flag1=flag1, unk=lunk, pixel_off=body+10,
                                         comp="BC4" if is_bc4 else "BC1"))
            else:
                flag1 = u8(b,body); lunk = u8(b,body+1)
                fr["layers"].append(dict(name=name, content_len=clen, flag1=flag1, unk=lunk,
                                         pixel_off=body+2,
                                         comp="BC4" if is_bc4 else "BC1"))
            off = lstart + clen
            pad = (4 - (clen % 4)) % 4
            off += pad
        res["frames"].append(fr)
    # render first frame main layer
    if render and res["frames"]:
        fr = res["frames"][0]
        main = next((l for l in fr["layers"] if l["name"]=="main"), None)
        if main and main["w"]>0 and main["h"]>0:
            try:
                img,_ = decode_layer(b, main["pixel_off"], main["w"], main["h"], bc4=False)
                img.save(render)
                res["rendered"] = os.path.basename(render)
                res["rendered_size"] = img.size
            except Exception as e:
                res["render_error"] = repr(e)
    return res

# pick a few interesting files
cands = [
    os.path.join(GAME,"resources","_common","drs","graphics","u_arc_archer_x1.sld"),
    os.path.join(GAME,"resources","_common","drs","graphics","u_vil_villager_x1.sld"),
    os.path.join(GAME,"resources","_common","drs","graphics","b_archaic_dock_age1_rubble_x1.sld"),
]
# find by glob if names differ
all_sld = glob.glob(os.path.join(GAME,"resources","_common","drs","graphics","*.sld"))
byname = {os.path.basename(p).lower(): p for p in all_sld}
print("graphics dir sld count:", len(all_sld))

results = []
# 1) tiny stub
for nm in ["b_archaic_dock_age1_rubble_x1.sld"]:
    p = byname.get(nm)
    if p: results.append(parse_sld(p, max_frames=2))

# 2) several real units/buildings - pick mid-size
import random
random.seed(7)
mid = sorted(all_sld, key=lambda p: os.path.getsize(p))
sample = mid[len(mid)//2 : len(mid)//2+40]
random.shuffle(sample)
n_ok = 0
frame_type_hist = collections.Counter()
layer_hist = collections.Counter()
for p in sample[:25]:
    try:
        r = parse_sld(p, max_frames=2)
    except Exception as e:
        r = dict(path=os.path.basename(p), error=repr(e))
    results.append(r)
    for fr in r.get("frames",[]):
        frame_type_hist[fr["frame_type"]] += 1
        for l in fr["layers"]: layer_hist[l["name"]] += 1

# 3) render a known unit
for nm in ["u_arc_archer_x1.sld","u_vil_male_villager_x1.sld","u_vil_villager_x1.sld"]:
    p = byname.get(nm)
    if p:
        results.append(parse_sld(p, max_frames=2,
            render=os.path.join(OUT, nm.replace(".sld","_frame0_main.png"))))
        break
else:
    # fall back: any u_ unit
    us = [p for p in all_sld if os.path.basename(p).startswith("u_")]
    if us:
        us.sort(key=lambda p: os.path.getsize(p))
        p = us[len(us)//2]
        results.append(parse_sld(p, max_frames=2,
            render=os.path.join(OUT, "render_sample_frame0.png")))

summary = dict(
    frame_type_hist=dict(frame_type_hist),
    layer_hist=dict(layer_hist),
    n_parsed=len(results),
    errors=[r for r in results if "error" in r or "render_error" in r],
)
print(json.dumps(summary, indent=1)[:3000])
with open(os.path.join(OUT,"sld_verify.json"),"w",encoding="utf-8") as f:
    json.dump(dict(summary=summary, results=results), f, indent=1, ensure_ascii=False)
print("\n--- sample parsed ---")
for r in results[:6]:
    if "error" in r: print(r); continue
    print(os.path.basename(r["path"]), "size",r["size"],"nf",r["num_frames"],"u2=0x%04x"%r["u2"],"u3=0x%08x"%r["u3"])
    for l in r["frames"][0]["layers"]:
        print("   ", l)

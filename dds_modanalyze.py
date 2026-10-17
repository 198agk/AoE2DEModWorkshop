import os, struct, sys

def fourcc_str(v):
    b = struct.pack("<I", v)
    return b.decode("ascii") if all(32 <= c < 127 for c in b) else f"0x{v:08X}"

def hdr(path):
    with open(path,"rb") as f: d = f.read(148)
    if len(d) < 128: return None
    magic, = struct.unpack("<I", d[:4])
    if magic != 0x20534444: return None
    hsz, flags, h, w, pitch, depth, mips = struct.unpack("<7I", d[4:32])
    pfsize, pfflags, fourcc, bitcount = struct.unpack("<4I", d[76:92])
    masks = struct.unpack("<4I", d[92:108])
    caps, caps2, caps3, caps4, r2 = struct.unpack("<5I", d[108:128])
    r = dict(w=w,h=h,mips=mips,flags=flags,pitch=pitch,depth=depth,pfflags=pfflags,
             fourcc=fourcc_str(fourcc),bitcount=bitcount,masks=masks,caps=caps,size=os.path.getsize(path))
    if fourcc_str(fourcc)=="DX10" and len(d)>=148:
        r["dx10"]=struct.unpack("<5I", d[128:148])
    return r

roots = [
 r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed",
 r"C:\Users\26913\Games\Age of Empires 2 DE\0\mods\local",
]
for root in roots:
    print("="*110); print("ROOT:", root); print("="*110)
    for dp, dn, fn in os.walk(root):
        for n in fn:
            if not n.lower().endswith(".dds"): continue
            p = os.path.join(dp,n)
            r = hdr(p)
            rel = os.path.relpath(p, root)
            if r is None:
                print(f"  {rel}  -> NOT A VALID DDS / unreadable"); continue
            print(f"  {rel}")
            print(f"      {r['w']}x{r['h']} mips={r['mips']} depth={r['depth']} flags=0x{r['flags']:06X} "
                  f"linear/pitch={r['pitch']} pf=0x{r['pfflags']:X} fourcc={r['fourcc']} bits={r['bitcount']} "
                  f"caps=0x{r['caps']:X} size={r['size']}")
            if r['pfflags'] & 4 == 0:
                print(f"      masks=[{', '.join(hex(m) for m in r['masks'])}]")
            if "dx10" in r:
                print(f"      dx10={r['dx10']}")
    # PNGs replacing widgetui paths
    print("  --- PNG files present under a mod (these replace textures too?) ---")
    for dp, dn, fn in os.walk(root):
        for n in fn:
            if n.lower().endswith(".png") and ("widgetui" in dp.lower() or "wpfg" in dp.lower()):
                print("   ", os.path.relpath(os.path.join(dp,n), root))

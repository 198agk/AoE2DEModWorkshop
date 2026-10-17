import os, struct, collections

G = r"D:\Games\Steam\steamapps\common\AoE2DE"

def hdr(p):
    with open(p,"rb") as f: d=f.read(148)
    if len(d)<128: return None
    if struct.unpack("<I",d[:4])[0]!=0x20534444: return None
    _,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
    pfp,fourcc,bc = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
    fc = struct.pack("<I",fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else ""
    dxgi = None
    if fc=="DX10" and len(d)>=148: dxgi = struct.unpack("<I", d[128:132])[0]
    return dict(w=w,h=h,mips=mips,flags=flags,pitch=pitch,depth=depth,pfp=pfp,fourcc=fc,dxgi=dxgi,bits=bc,
                masks=struct.unpack("<4I",d[92:108]), size=os.path.getsize(p))

DXGI = {2:"BC1_TYPELESS",3:"BC1_UNORM",4:"BC1_UNORM_SRGB",5:"BC2_TYPELESS",6:"BC2_UNORM",7:"BC2_UNORM_SRGB",
        8:"BC3_TYPELESS",9:"BC3_UNORM",10:"BC3_UNORM_SRGB",73:"BC2_TYPELESS",76:"BC3_TYPELESS",82:"BC5_TYPELESS",
        95:"BC6H_UF16",96:"BC6H_SF16",97:"BC7_TYPELESS",98:"BC7_UNORM",99:"BC7_UNORM_SRGB",28:"R8G8B8A8_UNORM",29:"R8G8B8A8_UNORM_SRGB"}

def label(r):
    if r["pfp"]==0x4:
        if r["fourcc"]=="DX10": return f"DX10/{DXGI.get(r['dxgi'], r['dxgi'])}"
        return r["fourcc"]
    return "UNCOMPRESSED_RGBA8" if r["masks"][3] else "UNCOMPRESSED_RGB8"

def scan(root, name):
    print("="*100); print(name, "->", root); print("="*100)
    bydir = collections.defaultdict(list)
    for dp,dn,fn in os.walk(root):
        for n in fn:
            if not n.lower().endswith(".dds"): continue
            r = hdr(os.path.join(dp,n))
            if r: bydir[os.path.relpath(dp,root)].append(r)
    for d in sorted(bydir, key=lambda k: -len(bydir[k]))[:22]:
        rs = bydir[d]
        c = collections.Counter(label(r) for r in rs)
        mips = collections.Counter(r["mips"] for r in rs)
        pot = sum(1 for r in rs if (r["w"]&(r["w"]-1))==0 and (r["h"]&(r["h"]-1))==0)
        sq  = sum(1 for r in rs if r["w"]==r["h"])
        print(f"  {len(rs):5d}  {d}")
        print(f"         formats: {dict(c)}")
        print(f"         mipcounts: {dict(mips)}   POT: {pot}/{len(rs)}   SQUARE: {sq}/{len(rs)}")
    return bydir

scan(os.path.join(G,"widgetui"), "widgetui")
scan(os.path.join(G,"modes","Pompeii","widgetui"), "modes/Pompeii/widgetui")

print("\n"+"="*100)
print("SPECIFIC HUD CLASSES: format + mips + dims + linear-size correctness")
print("="*100)
checks = [
 r"widgetui\textures\ingame\units\000_50730.DDS",
 r"widgetui\textures\ingame\tech\001_50730.dds",
 r"widgetui\textures\ingame\buildings\001_50730.dds",
 r"widgetui\textures\menu\mapicons\icon_arabia.dds",
 r"widgetui\textures\atlas\SD\ingameicons.dds",
 r"widgetui\textures\atlas\HD\ingameicons.dds",
 r"widgetui\textures\atlas\UHD\ingameicons.dds",
 r"widgetui\textures\atlas\SD\chatatlas.dds",
 r"widgetui\textures\backgrounds\mainmenu_bg.dds",
 r"widgetui\textures\backgrounds\techtree_left.dds",
]
for rel in checks:
    p=os.path.join(G,rel)
    if not os.path.exists(p): print(f"  {rel} -> MISSING"); continue
    r=hdr(p); 
    blk = 8 if "DXT1" in label(r) or label(r)=="UNCOMPRESSED_RGBA8" else 16
    exp = max(1,(r['w']+3)//4)*max(1,(r['h']+3)//4)*blk
    body = r['size']-128
    print(f"  {rel}")
    print(f"      {r['w']}x{r['h']} {label(r)} mips={r['mips']} depth={r['depth']} flags=0x{r['flags']:06X} "
          f"caps=0x{struct.unpack('<I',open(p,'rb').read(112)[108:112])[0]:X} linear={r['pitch']} expTopMipLinear={exp} "
          f"bodybytes={body} bodyIsOneMip={body==exp} isPOT={(r['w']&(r['w']-1))==0 and (r['h']&(r['h']-1))==0}")

print("\n"+"="*100)
print("mip distribution inside widgetui ONLY")
print("="*100)
c=collections.Counter()
for dp,dn,fn in os.walk(os.path.join(G,"widgetui")):
    for n in fn:
        if n.lower().endswith(".dds"):
            r=hdr(os.path.join(dp,n))
            if r: c[r["mips"]]+=1
print("  ", dict(c), " (any >1?)", any(k>1 for k in c))

print("\n"+"="*100)
print("total install format histogram + mip histogram by compressed/uncompressed")
print("="*100)
fmt=collections.Counter(); mm=collections.Counter()
for dp,dn,fn in os.walk(G):
    for n in fn:
        if not n.lower().endswith(".dds"): continue
        r=hdr(os.path.join(dp,n))
        if not r: continue
        fmt[label(r)]+=1
        mm[(("compressed" if r["pfp"]==0x4 else "uncompressed"), r["mips"])]+=1
for k,v in fmt.most_common(): print(f"  {v:6d}  {k}")
print("  --- mips ---")
for k in sorted(mm, key=lambda x:(x[0],x[1])): print(f"  {mm[k]:6d}  {k}")

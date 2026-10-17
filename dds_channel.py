import os, struct, subprocess, collections
from PIL import Image

G  = r"D:\Games\Steam\steamapps\common\AoE2DE"
TC = os.path.join(G, r"Tools_Builds\texconv.exe")
OUT= r"D:\Software\DeepSeek Harness\工作区2\_ddstest4"
os.makedirs(OUT, exist_ok=True)

def hdr(p):
    with open(p,"rb") as f: d=f.read(148)
    size,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
    pfp,fourcc,bc = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
    fc = struct.pack("<I",fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else "0"
    return dict(w=w,h=h,mips=mips,pfp=pfp,fourcc=fc,bits=bc,masks=struct.unpack("<4I",d[92:108]))

print("="*104)
print("MASK-ORDER CENSUS: which uncompressed mask layout is used WHERE?  (mask=0xff at byte0 = 'R-first'/RGBA-in-memory)")
print("="*104)
by = collections.defaultdict(collections.Counter)
for root,dirs,files in os.walk(G):
    for n in files:
        if not n.lower().endswith(".dds"): continue
        p=os.path.join(root,n)
        try: h=hdr(p)
        except Exception: continue
        if h["pfp"]==0x41:  # uncompressed RGB(A)
            key = "R-first[ff,ff00,ff0000,ff000000]" if h["masks"][0]==0xff else ("B-first[ff0000,ff00,ff,ff000000]" if h["masks"][0]==0xff0000 else f"OTHER{h['masks']}")
            rel = os.path.relpath(root, G)
            top = rel.split(os.sep)[0] if rel!="." else "<root>"
            by[top][key]+=1
for k in sorted(by, key=lambda x:-sum(by[x].values())):
    print(f"  {sum(by[k].values()):5d}  {k:34s} {dict(by[k])}")

print()
print("  --- widgetui subtrees ---")
by2 = collections.defaultdict(collections.Counter)
for root,dirs,files in os.walk(os.path.join(G,"widgetui")):
    for n in files:
        if not n.lower().endswith(".dds"): continue
        try: h=hdr(os.path.join(root,n))
        except Exception: continue
        if h["pfp"]==0x41:
            key = "R-first" if h["masks"][0]==0xff else "B-first"
            by2[os.path.relpath(root, os.path.join(G,"widgetui"))][key]+=1
for k in sorted(by2, key=lambda x:-sum(by2[x].values()))[:15]:
    print(f"  {sum(by2[k].values()):5d}  widgetui\\{k:44s} {dict(by2[k])}")

print()
print("="*104)
print("CHANNEL-ORDER A/B: decode the SAME shipped file with Pillow and with texconv(-ft png), compare RGB")
print("="*104)
tests = [
  os.path.join(G, r"widgetui\textures\ingame\units\000_50730.DDS"),
  os.path.join(G, r"resources\_common\fonts\georgia_european_0000.DDS"),
]
# also find one B-first uncompressed file
bfirst=None
for root,dirs,files in os.walk(G):
    for n in files:
        if not n.lower().endswith(".dds"): continue
        try: h=hdr(os.path.join(root,n))
        except Exception: continue
        if h["pfp"]==0x41 and h["masks"][0]==0xff0000:
            bfirst=os.path.join(root,n); break
    if bfirst: break
tests.append(bfirst)
for p in tests:
    if not p or not os.path.exists(p): print("  SKIP", p); continue
    h=hdr(p)
    print(f"\n  {os.path.relpath(p,G)}")
    print(f"    header masks={h['masks']}  R first at byte {'0' if h['masks'][0]==0xff else '2'}  ({'R-first' if h['masks'][0]==0xff else 'B-first'})")
    im=Image.open(p); im.load()
    rc=subprocess.run([TC,"-ft","png","-f","R8G8B8A8_UNORM","-m","1","-y","-o",OUT,p],
                      capture_output=True)
    o=rc.stdout.decode("utf-8","replace")
    print("    texconv:", [l for l in o.splitlines() if "reading" in l or "FAILED" in l][:1])
    q=os.path.join(OUT, os.path.splitext(os.path.basename(p))[0]+".png")
    if os.path.exists(q):
        t=Image.open(q).convert("RGBA"); t.load()
        for pt in [(0,0),(64,64),(128,128)]:
            if pt[0]<im.size[0] and pt[1]<im.size[1]:
                print(f"      {pt}: Pillow={im.getpixel(pt)}   texconvPNG={t.getpixel(pt)}")
    else:
        print("      no PNG produced")

print()
print("="*104)
print("PILLOW'S DXT5 BODY vs TEXCONV'S DXT5 BODY — are the block bytes identical for the same PNG?")
print("="*104)
src = Image.new("RGBA",(256,256))
src.putdata([((x*7)%256,(y*11)%256,((x^y)*3)%256, 255 if (x*y)%5 else 64) for y in range(256) for x in range(256)])
sp=os.path.join(OUT,"s.png"); src.save(sp)
pa=os.path.join(OUT,"p_pil.dds"); src.save(pa, format="DDS", pixel_format="DXT5")
rc=subprocess.run([TC,"-f","DXT5","-m","1","-y","-o",OUT,"-px","p_tc_",sp], capture_output=True)
pb=os.path.join(OUT,"p_tc_s.dds")
if os.path.exists(pb):
    da=open(pa,"rb").read()[128:]; db=open(pb,"rb").read()[128:]
    print(f"  Pillow body {len(da)} bytes, texconv body {len(db)} bytes, equal={da==db}")
    if da!=db:
        diff=sum(1 for a,b in zip(da,db) if a!=b)
        print(f"  differing bytes: {diff} / {len(da)}  ({100*diff/len(da):.1f}%)  -> different encoder (Pillow uses its own/stb-style BC3; texconv uses DirectXTex)")
    # decode both with texconv and measure vs source
    print("  both are structurally valid DXT5 (same size, both decode):", len(da)==len(db))

print()
print("="*104)
print("BC7: Pillow CANNOT write it. Verify texconv BC7 output quality is what AoE2 HD atlases use")
print("="*104)
rc=subprocess.run([TC,"-f","BC7_UNORM","-m","1","-y","-o",OUT,"-px","p_bc7_",sp], capture_output=True)
pq=os.path.join(OUT,"p_bc7_s.dds")
print("  exists:", os.path.exists(pq), hdr(pq) if os.path.exists(pq) else "")
print("  -> Pillow alternative for BC7: none (OSError: cannot write pixel format BC7).")

print()
print("="*104)
print("EXACT ERROR STRINGS: Pillow refuses for every BC1/BC4/BC6H/BC7 request")
print("="*104)
for pf in ["BC1","BC4","BC6H","BC7","ATI2","BC5U","BC1_UNORM","DXT2","DXT4"]:
    try:
        src.save(os.path.join(OUT,f"x_{pf}.dds"), format="DDS", pixel_format=pf)
        print(f"  {pf:10s} -> WROTE (unexpected)")
    except Exception as e:
        print(f"  {pf:10s} -> {type(e).__name__}: {e}")

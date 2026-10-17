import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, subprocess, shutil
from PIL import Image

OUT = _ROOT_PATH("_ddstest3")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
TC  = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texconv.exe"
G   = r"D:\Games\Steam\steamapps\common\AoE2DE"

def run(args):
    p = subprocess.run(args, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8","replace") + p.stderr.decode("utf-8","replace")

def hdr(p):
    with open(p,"rb") as f: d=f.read(148)
    size,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
    pfp,fourcc,bc = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
    fc = struct.pack("<I",fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else str(fourcc)
    caps = struct.unpack("<I", d[108:112])[0]
    r=dict(dwSize=size,w=w,h=h,mips=mips,flags=flags,pitch=pitch,depth=depth,pfp=pfp,fourcc=fc,bits=bc,caps=caps,
           masks=struct.unpack("<4I",d[92:108]), size=os.path.getsize(p))
    if fc=="DX10" and len(d)>=148: r["dx10"]=struct.unpack("<5I",d[128:148])
    return r

def game_exact_patch(path, w, h, blockbytes):
    lin = max(1,(w+3)//4)*max(1,(h+3)//4)*blockbytes
    d = bytearray(open(path,"rb").read())
    struct.pack_into("<I", d, 8,  0x000A1007)   # dwFlags CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAPCOUNT|LINEARSIZE
    struct.pack_into("<I", d, 20, lin)          # dwPitchOrLinearSize = exact top-mip size
    struct.pack_into("<I", d, 24, 1)            # dwDepth
    struct.pack_into("<I", d, 28, 1)            # dwMipMapCount
    struct.pack_into("<I", d, 88, 0)            # dwRGBBitCount = 0 for FOURCC
    struct.pack_into("<I", d, 108, 0x1000)      # dwCaps = DDSCAPS_TEXTURE
    open(path,"wb").write(bytes(d)); return lin

# ---- source image ----
src = Image.new("RGBA",(300,200))
src.putdata([ ( (x*3)%256, (y*5)%256, ((x+y)*7)%256, 255 if (x+y)%7 else 128 ) for y in range(200) for x in range(300) ])
sp = os.path.join(OUT,"src.png"); src.save(sp)

print("="*104)
print("TEST 1: MS parser acceptance of Pillow DXT5 with a GAME-EXACT header on a fresh copy")
print("="*104)
a = os.path.join(OUT,"A_pil_raw.dds");   src.save(a, format="DDS", pixel_format="DXT5")
print("  A raw Pillow header   :", hdr(a))
b = os.path.join(OUT,"B_pil_patched.dds"); shutil.copyfile(a,b)
lin = game_exact_patch(b, 300, 200, 16)
print(f"  B patched (lin={lin})  :", hdr(b))
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",os.path.join(OUT,"decA"),a])
print(f"  texconv reads RAW Pillow DXT5      rc={rc}  ->", [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l])
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",os.path.join(OUT,"decB"),b])
print(f"  texconv reads PATCHED Pillow DXT5  rc={rc}  ->", [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l])

print()
print("="*104)
print("TEST 2: DX10 arraySize=0 (Pillow) vs arraySize=1 (correct) — exact HRESULT")
print("="*104)
c = os.path.join(OUT,"C_pil_bc3.dds"); src.save(c, format="DDS", pixel_format="BC3")
print("  C Pillow BC3 header:", hdr(c))
d = os.path.join(OUT,"D_pil_bc3_fixed.dds"); shutil.copyfile(c,d)
dd = bytearray(open(d,"rb").read()); struct.pack_into("<I", dd, 140, 1)   # arraySize at DXT10 +12 => 128+12=140
open(d,"wb").write(bytes(dd))
print("  D arraySize=1       :", hdr(d))
for tag,f in [("C arraySize=0",c),("D arraySize=1",d)]:
    rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",os.path.join(OUT,"dec"+tag[0]),f])
    lines = [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l]
    print(f"  texconv {tag}: rc={rc} ->", lines)
print("  HRESULT 0x8007000d = ERROR_INVALID_DATA ; 0x80070032 = ERROR_NOT_SUPPORTED")

print()
print("="*104)
print("TEST 3: does Pillow itself notice anything? read back each variant")
print("="*104)
for tag,f in [("A raw",a),("B patched",b),("C bc3 dx10 array0",c),("D bc3 dx10 array1",d)]:
    try:
        im=Image.open(f); im.load()
        print(f"  {tag:20s} -> OK {im.size} {im.mode} pf={im.info.get('pixel_format')}  bytes={os.path.getsize(f)}")
    except Exception as e:
        print(f"  {tag:20s} -> FAIL {type(e).__name__}: {e}")

print()
print("="*104)
print("TEST 4: CHANNEL ORDER — decode a real shipped uncompressed RGBA8 texture with BOTH readers")
print("="*104)
real = os.path.join(G, r"widgetui\textures\ingame\units\000_50730.DDS")
print("  shipped header:", hdr(real))
im = Image.open(real); im.load()
print(f"  Pillow: {im.size} {im.mode}  corner px(0,0)={im.getpixel((0,0))} px(128,128)={im.getpixel((128,128))}")
# ask texconv to decode the SAME file to PNG, then compare pixels
rc,out = run([TC,"-f","R8G8B8A8_UNORM","-m","1","-y","-o",OUT,real])
print(f"  texconv decode rc={rc}:", [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l])
tcp = os.path.join(OUT,"000_50730.png")
if os.path.exists(tcp):
    tim = Image.open(tcp); tim.load()
    print(f"  texconv->PNG: {tim.size} {tim.mode}")
    diffs=[]
    for pt in [(0,0),(100,50),(128,128),(200,200),(255,255)]:
        p1=im.getpixel(pt); p2=tim.convert("RGBA").getpixel(pt)
        same = (p1[0]>=p2[0]-2 and p1[0]<=p2[0]+2) if tim.mode!="RGBA" else p1==p2
        diffs.append((pt,p1,p2))
    for pt,p1,p2 in diffs: print(f"    {pt}: Pillow={p1}  texconv={p2}")
else:
    print("  texconv produced no PNG (check -ft / output naming)")

print()
print("="*104)
print("TEST 5: same channel-order check on the OTHER shipped mask order [0xff,0xff00,0xff0000,0xff000000]")
print("="*104)
import glob
cands=[]
for root,dirs,files in os.walk(os.path.join(G,"resources","_common")):
    for n in files:
        if n.lower().endswith(".dds"):
            p=os.path.join(root,n)
            try:
                h=hdr(p)
                if h['pfp']==0x41 and h['bits']==32 and h['masks'][0]==0xff and h['masks'][1]==0xff00:
                    cands.append(p)
                    if len(cands)>=1: break
            except Exception: pass
    if len(cands)>=1: break
print("  sample:", cands[:1])
if cands:
    p=cands[0]; print("  header:", hdr(p))
    im=Image.open(p); im.load(); print(f"  Pillow: {im.size} {im.mode} px(0,0)={im.getpixel((0,0))} px(64,64)={im.getpixel((64,64))}")
    rc,out=run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,p])
    print(f"  texconv rc={rc}:", [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l])
    q=os.path.join(OUT,os.path.splitext(os.path.basename(p))[0]+".png")
    if os.path.exists(q):
        t=Image.open(q).convert("RGBA"); t.load()
        for pt in [(0,0),(64,64)]: print(f"    {pt}: Pillow={im.getpixel(pt)}  texconv={t.getpixel(pt)}")

print()
print("="*104)
print("TEST 6: full HUD-atlas round trip — SD chatatlas DXT5 -> Pillow decode -> Pillow DXT5 -> patch -> texconv")
print("="*104)
atlas = os.path.join(G, r"widgetui\textures\atlas\SD\chatatlas.dds")
ishdr = hdr(atlas)
im = Image.open(atlas); im.load()
rt = os.path.join(OUT,"chat_rt.dds"); im.save(rt, format="DDS", pixel_format="DXT5")
game_exact_patch(rt, ishdr['w'], ishdr['h'], 16)
print("  source atlas header:", ishdr)
print("  my re-encode header:", hdr(rt))
print("  same file size?", os.path.getsize(rt)==os.path.getsize(atlas), os.path.getsize(rt), os.path.getsize(atlas))
rc,out=run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,rt])
print(f"  texconv reads the round-tripped atlas rc={rc}:", [l for l in out.splitlines() if 'reading' in l or 'FAILED' in l])
src_im = Image.open(atlas).convert("RGBA")
re_im  = Image.open(os.path.join(OUT,"chat_rt.png")).convert("RGBA") if os.path.exists(os.path.join(OUT,"chat_rt.png")) else None
if re_im:
    import statistics
    d=[abs(a-b) for pa,pb in zip(src_im.getdata(), re_im.getdata()) for a,b in zip(pa,pb)]
    print(f"  Pillow-DXT5 re-encode vs source, mean |diff| = {sum(d)/len(d):.3f} / 255  max={max(d)}")

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, subprocess, shutil, sys
from PIL import Image

OUT = _ROOT_PATH("_ddstest2")
os.makedirs(OUT, exist_ok=True)
TC  = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texconv.exe"
G   = r"D:\Games\Steam\steamapps\common\AoE2DE"

def run(args):
    p = subprocess.run(args, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8","replace") + p.stderr.decode("utf-8","replace")

def hdr(p):
    with open(p,"rb") as f: d=f.read(148)
    _,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
    pfp,fourcc,bc = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
    fc = struct.pack("<I",fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else str(fourcc)
    r=dict(w=w,h=h,mips=mips,flags=flags,pitch=pitch,depth=depth,pfp=pfp,fourcc=fc,bits=bc,size=os.path.getsize(p))
    if fc=="DX10" and len(d)>=148: r["dx10"]=struct.unpack("<5I",d[128:148])
    return r

print("="*100)
print("TEST A: can Microsoft DirectXTex (texconv) LOAD Pillow's DXT5 output?")
print("="*100)
src = Image.new("RGBA",(300,200))
for y in range(200):
    for x in range(300):
        src.putpixel((x,y),(x%256, y%256, (x+y)%256, 255 if x>10 else 0))
sp = os.path.join(OUT,"src.png"); src.save(sp)

pil_dxt5 = os.path.join(OUT,"pil_dxt5.dds")
src.save(pil_dxt5, format="DDS", pixel_format="DXT5")
print("  Pillow DXT5 header:", hdr(pil_dxt5))
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,pil_dxt5])
print(f"  texconv decode rc={rc}")
print("  stdout:", out.strip()[:600])
dec = os.path.join(OUT,"pil_dxt5.png")
print("  texconv wrote decodable PNG:", os.path.exists(dec))

print()
print("="*100)
print("TEST B: does texconv accept Pillow's DX10 BC3 output (arraySize=0)?")
print("="*100)
pil_bc3 = os.path.join(OUT,"pil_bc3.dds")
src.save(pil_bc3, format="DDS", pixel_format="BC3")
print("  Pillow BC3 header:", hdr(pil_bc3))
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,pil_bc3])
print(f"  texconv decode rc={rc}")
print("  stdout:", out.strip()[:600])

print()
print("="*100)
print("TEST C: reference — texconv's own DXT5 with -dx10 (arraySize=1)")
print("="*100)
rc,out = run([TC,"-f","DXT5","-m","1","-dx10","-y","-o",OUT,"-px","tc_",sp])
print(f"  rc={rc} :", out.strip()[:400])
print("  header:", hdr(os.path.join(OUT,"tc_src.dds")))

print()
print("="*100)
print("TEST D: PILLOW UNCOMPRESSED RGBA — is the channel order correct? (mask claims R=0xff at byte 0)")
print("="*100)
probe = Image.new("RGBA",(4,1))
probe.putpixel((0,0),(255,0,0,255))   # red
probe.putpixel((1,0),(0,255,0,255))   # green
probe.putpixel((2,0),(0,0,255,255))   # blue
probe.putpixel((3,0),(0,0,0,128))     # half alpha black
pp = os.path.join(OUT,"pil_uncompressed.dds")
probe.save(pp, format="DDS")
with open(pp,"rb") as f: d=f.read()
body = d[128:128+16]
print("  Pillow header:", hdr(pp))
print("  raw first-4-pixel bytes (B,G,R,A order expected for D3DFMT_A8R8G8B8):", body.hex(" "))
print("  expected if masks are TRUE 32-bit ARGB (byte0=B): ff0000ff 00ff00ff 0000ffff 00000080")
print("  expected if masks are FALSE/byte-reversed (byte0=R): ff0000ff 00ff00ff 0000ffff 00000080 (same!)")
# distinguish: use a color where channel order differs in a way that matters vs texconv
tc_un = os.path.join(OUT,"tc_uncompressed.png")
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,"-px","tcu_",pp])
print(f"  texconv view of Pillow uncompressed rc={rc}:", out.strip()[:300])
print("  header:", hdr(os.path.join(OUT,"tcu_pil_uncompressed.dds")))

print()
print("="*100)
print("TEST E: ROUND-TRIP a REAL SHIPPED HUD ATLAS through Pillow (does re-encode stay byte-plausible?)")
print("="*100)
real = os.path.join(G,r"widgetui\textures\atlas\SD\chatatlas.dds")
im = Image.open(real)
print(f"  {real}")
print(f"  source: {im.size} {im.mode}")
out_pil = os.path.join(OUT,"chatatlas_pil_dxt5.dds")
im.save(out_pil, format="DDS", pixel_format="DXT5")
print("  Pillow re-encode header:", hdr(out_pil))
print("  source    header        :", hdr(real))
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,out_pil])
print(f"  texconv re-reads Pillow re-encode rc={rc}")

print()
print("="*100)
print("TEST F: What does texconv do with a Pillow file whose header we PATCH to game-exact?")
print("="*100)
import shutil as _sh
patched = os.path.join(OUT,"pil_dxt5_patched.dds")
_sh.copyfile(pil_dxt5, patched)
data = bytearray(open(patched,"rb").read())
w,h = 300,200
lin = max(1,(w+3)//4)*max(1,(h+3)//4)*16
struct.pack_into("<I", data, 8, 0x000A1007)   # dwFlags
struct.pack_into("<I", data, 20, lin)          # dwPitchOrLinearSize
struct.pack_into("<I", data, 24, 1)            # dwDepth
struct.pack_into("<I", data, 28, 1)            # dwMipMapCount
struct.pack_into("<I", data, 88, 0)            # dwRGBBitCount -> 0 (as game does)
struct.pack_into("<I", data, 108, 0x1000)      # dwCaps
open(patched,"wb").write(data)
print("  patched header:", hdr(patched))
rc,out = run([TC,"-f","B8G8R8A8_UNORM","-m","1","-y","-o",OUT,patched])
print(f"  texconv rc={rc}:", out.strip()[:400])
rc,out = run([TC,"-nologo","-f","DXT5","-m","1","-y","-o",OUT,"-px","patched_",patched])
print(f"  texconv re-encode rc={rc}:", out.strip()[:400])

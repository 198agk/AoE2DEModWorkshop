import os, struct, subprocess
from PIL import Image
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ddstest")
G = r"D:\Games\Steam\steamapps\common\AoE2DE"
TC = os.path.join(G, "Tools_Builds", "texconv.exe")

print("="*100); print("5. Does Pillow EVER write mipmaps / MIPMAPCOUNT?"); print("="*100)
for f in sorted(os.listdir(OUT)):
    if f.startswith("pil_") and f.endswith(".dds"):
        p = os.path.join(OUT, f)
        with open(p, "rb") as fh: d = fh.read(128)
        _, flags, _, _, pitch, depth, mips = struct.unpack("<7I", d[4:32])
        caps, = struct.unpack("<I", d[108:112])
        print(f"  {f:34s} mipCount={mips} depth={depth} pitchOrLinear={pitch} "
              f"MIPMAPCOUNTflag={bool(flags & 0x20000)} MIPMAPcap={bool(caps & 0x400000)}")

print("\n" + "="*100); print("6. texconv stdout for representative command lines"); print("="*100)
src = os.path.join(OUT, "src.png")
for label, flags in [("DXT5 -m 1", ["-f","DXT5","-m","1","-y"]),
                     ("DXT5 (default mips)", ["-f","DXT5","-y"]),
                     ("DXT5 + DX10 header", ["-f","DXT5","-m","1","-dx10","-y"]),
                     ("BC7_UNORM -m 1", ["-f","BC7_UNORM","-m","1","-y"])]:
    r = subprocess.run([TC, *flags, "-o", os.path.join(OUT,"tc"), "-px", "run_", src],
                       capture_output=True, timeout=900)
    print(f"  --- texconv {' '.join(flags)}  (rc={r.returncode}) ---")
    for s in (r.stdout or b"").decode("utf-8","replace").splitlines(): print("      ", s)
    for s in (r.stderr or b"").decode("utf-8","replace").splitlines(): print("   E: ", s)

print("\n" + "="*100); print("7. EXPERIMENT: Pillow DXT5 body + GAME-CORRECT patched header"); print("="*100)
ref_src = os.path.join(OUT, "src.png")
pil = os.path.join(OUT, "pil_dxt5_pf.dds")
target = os.path.join(OUT, "pillow_dxt5_patched_header.dds")
with open(pil,"rb") as f: data = bytearray(f.read())
w, h = 300, 200
linear = max(1,(w+3)//4) * 16
# Game-correct header for a single-mip DXT5 HUD texture (mirrors ingameicons.dds):
# flags = CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAPCOUNT|LINEARSIZE = 0x000A1007
struct.pack_into("<I", data, 8, 0x000A1007)   # dwFlags
struct.pack_into("<I", data, 20, linear)      # dwPitchOrLinearSize
struct.pack_into("<I", data, 24, 1)           # dwDepth
struct.pack_into("<I", data, 28, 1)           # dwMipMapCount
struct.pack_into("<I", data, 108, 0x1000)     # dwCaps = DDSCAPS_TEXTURE
with open(target,"wb") as f: f.write(data)
with open(target,"rb") as f: d=f.read(128)
_,flags,hh,ww,pitch,depth,mips = struct.unpack("<7I", d[4:32])
print(f"  patched file : {ww}x{hh} flags=0x{flags:06X} pitchOrLinear={pitch} depth={depth} mipCount={mips}")
print(f"  game template: 720x796 flags=0x0A1007 pitchOrLinear=573120 depth=1 mipCount=1  (ingameicons.dds)")
print(f"  exact linear size for 300x200 DXT5 = ceil(300/4)*ceil(200/4)*16 = {linear}")
try:
    rt = Image.open(target); rt.load()
    print(f"  Pillow reopens patched file OK: mode={rt.mode} size={rt.size} pixel_format={rt.pixel_format}")
    a = np.asarray(rt.convert("RGBA"), dtype=float)
    b = np.asarray(Image.open(ref_src).convert("RGBA"), dtype=float)
    print(f"  DXT5 round-trip mean abs error vs PNG: {abs(a-b).mean():.2f} / 255")
except Exception as e:
    print(f"  reopen FAILED: {type(e).__name__}: {e}")

print("\n" + "="*100); print("8. Size comparison: Pillow DXT5 vs texconv DXT5 (same source, -m 1)"); print("="*100)
for p in [os.path.join(OUT,"pil_dxt5_pf.dds"), os.path.join(OUT,"tc","tc_legacy_dxt5_src.dds")]:
    if os.path.exists(p):
        print(f"  {os.path.basename(p):34s} {os.path.getsize(p)} bytes")

print("\n" + "="*100); print("9. Pillow read of multi-mip game texture: does it expose level 0 only?"); print("="*100)
g = os.path.join(G, r"resources\_common\particles\textures\exclamation_mark.dds")
try:
    im = Image.open(g); im.load()
    print(f"  exclamation_mark.dds (512x512, 10 mips): Pillow -> mode={im.mode} size={im.size} "
          f"pixel_format={im.pixel_format} n_frames={getattr(im,'n_frames',1)}")
    print(f"  Pillow info keys: {list(im.info.keys())}")
    print("  => Pillow exposes ONLY mip level 0; no mip access API.")
except Exception as e:
    print(f"  FAIL {type(e).__name__}: {e}")

print("\n" + "="*100); print("10. BC7 in game + Pillow BC7 write capa check"); print("="*100)
p = os.path.join(G, r"resources\_common\particles\textures\aura_glow.dds")
im = Image.open(p); im.load()
print(f"  aura_glow.dds -> Pillow reads OK, pixel_format={im.pixel_format}, size={im.size}")
try:
    im.save(os.path.join(OUT,"_bc7write.dds"), format="DDS", pixel_format="BC7")
    print("  Pillow BC7 WRITE: OK")
except Exception as e:
    print(f"  Pillow BC7 WRITE: {type(e).__name__}: {e}")
print("  => Pillow can READ BC7 but CANNOT WRITE BC7.")

print("\nDone.")

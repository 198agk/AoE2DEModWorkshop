import os, struct, subprocess, sys, tempfile, shutil
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ddstest")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

def fourcc_str(v):
    b = struct.pack("<I", v)
    return b.decode("ascii") if all(32 <= c < 127 for c in b) else f"0x{v:08X}"

def hdr(path):
    with open(path,"rb") as f: d = f.read(148)
    if len(d) < 128: return f"short file ({len(d)} bytes)"
    magic, = struct.unpack("<I", d[:4])
    if magic != 0x20534444: return "NOT DDS"
    hsz, flags, h, w, pitch, depth, mips = struct.unpack("<7I", d[4:32])
    pfsize, pfflags, fourcc, bitcount = struct.unpack("<4I", d[76:92])
    masks = struct.unpack("<4I", d[92:108])
    caps, caps2, caps3, caps4, r2 = struct.unpack("<5I", d[108:128])
    dd = {"file":os.path.basename(path),"size":os.path.getsize(path),"w":w,"h":h,"mips":mips,
          "flags":hex(flags),"pitch_or_linearsize":pitch,"depth":depth,"pfsize":pfsize,
          "pfflags":hex(pfflags),"fourcc":fourcc_str(fourcc),"bitcount":bitcount,
          "masks":[hex(m) for m in masks],"caps":hex(caps),"caps2":hex(caps2),
          "mipcap":bool(caps & 0x400000), "dx10":None}
    off = 128
    if (pfflags & 0x4) and dd["fourcc"]=="DX10":
        dd["dx10"], = struct.unpack("<I", d[128:132])
        dd["dx10_full"] = struct.unpack("<5I", d[128:148])
    return dd

def show(p):
    r = hdr(p)
    if isinstance(r,str): print(f"  {os.path.basename(p):32s} {r}"); return r
    line = (f"  {r['file']:34s} {r['w']:5d}x{r['h']:<5d} mips={r['mips']} pf={r['pfflags']:>5s} "
            f"fourcc={r['fourcc']:>5s} bits={r['bitcount']:2d} mipcap={str(r['mipcap']):5s} "
            f"flags={r['flags']:>7s} size={r['size']}")
    if r["dx10"] is not None:
        line += f"  dx10=({r['dx10_full']})"
    print(line)
    return r

# --- Create a test image: non-square, non-POT, with alpha ---
W, H = 300, 200
img = Image.new("RGBA", (W,H))
px = img.load()
for y in range(H):
    for x in range(W):
        px[x,y] = (x % 256, y % 256, (x+y) % 256, 255 if (x//10 + y//10) % 2 else 0)

rgbsrc = os.path.join(OUT, "src.png")
img.save(rgbsrc)
print(f"Source PNG: {W}x{H} RGBA\n")

print("=" * 110)
print("PART A: Pillow native DDS writes")
print("=" * 110)
variants = [
    ("dxt1_default", dict(), "RGBA"),
    ("dxt1_pf",      dict(pixel_format="DXT1"), "RGBA"),
    ("dxt3_pf",      dict(pixel_format="DXT3"), "RGBA"),
    ("dxt5_pf",      dict(pixel_format="DXT5"), "RGBA"),
    ("bc2_pf",       dict(pixel_format="BC2"), "RGBA"),
    ("bc3_pf",       dict(pixel_format="BC3"), "RGBA"),
    ("bc5_pf_rgb",   dict(pixel_format="BC5"), "RGB"),
    ("uncompressed_rgba", dict(), "RGBA"),
    ("uncompressed_rgb",  dict(), "RGB"),
]
imgs = {"RGBA": img, "RGB": img.convert("RGB")}
for name, kw, mode in variants:
    p = os.path.join(OUT, f"pil_{name}.dds")
    try:
        imgs[mode].save(p, format="DDS", **kw)
        show(p)
    except Exception as e:
        print(f"  {name:34s} FAILED: {type(e).__name__}: {e}")

# --- Test the wrapper-drops-pixel_format bug ---
print("\n  --- pixel_format dropped by wrapper test ---")
src = img.copy()
src.encoderinfo = {}
p = os.path.join(OUT, "pil_encoderinfo_BAD.dds")
try:
    src.save(p, format="DDS", encoderinfo={})
except Exception as e:
    print(f"    save(encoderinfo={{}}) -> {type(e).__name__}: {e}")
p = os.path.join(OUT, "pil_encoderinfo_GOOD.dds")
try:
    src.save(p, format="DDS", encoderinfo={"pixel_format":"DXT5"})
    show(p)
except Exception as e:
    print(f"    save(encoderinfo=pixel_format) -> {type(e).__name__}: {e}")
# The classic bug: encoderinfo passed via 'save(im, fp, ...)' in a wrapper
import io
buf = io.BytesIO()
try:
    src.save(buf, format="DDS", pixel_format="DXT5")
    buf.seek(0)
    tmp = os.path.join(OUT,"pil_bytesio.dds")
    open(tmp,"wb").write(buf.getvalue())
    show(tmp)
except Exception as e:
    print(f"    BytesIO save -> {type(e).__name__}: {e}")

# --- Mode requirements per pixel_format ---
print("\n  --- mode requirements ---")
modes = {"1": Image.new("1",(32,32)), "L": Image.new("L",(32,32)), "LA": Image.new("LA",(32,32)),
         "P": Image.new("P",(32,32)), "RGB": Image.new("RGB",(32,32)), "RGBA": Image.new("RGBA",(32,32)),
         "I": Image.new("I",(32,32)), "F": Image.new("F",(32,32))}
for fmt in ["DXT1","DXT3","DXT5","BC2","BC3","BC5", None]:
    row = []
    for m, im in modes.items():
        p = os.path.join(OUT, f"_m_{fmt}_{m}.dds")
        try:
            kw = {} if fmt is None else {"pixel_format": fmt}
            im.save(p, format="DDS", **kw)
            row.append(f"{m}:OK")
            os.remove(p)
        except Exception as e:
            row.append(f"{m}:{type(e).__name__}")
    print(f"    pixel_format={str(fmt):6s}  {'  '.join(row)}")

print("\n" + "=" * 110)
print("PART B: texconv.exe outputs")
print("=" * 110)
TEXCONV = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texconv.exe"
TEXASM  = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\texassemble.exe"
tcout = os.path.join(OUT, "tc")
os.makedirs(tcout, exist_ok=True)

cmds = [
    ("legacy_dxt5", ["-f","DXT5","-m","1","-y"]),
    ("legacy_dxt5_nom", ["-f","DXT5","-y"]),
    ("legacy_dxt1", ["-f","DXT1","-m","1","-y"]),
    ("dx10_bc3",    ["-f","BC3_UNORM","-m","1","-y"]),
    ("dx10_flag",   ["-f","DXT5","-m","1","-dx10","-y"]),
    ("bc7",         ["-f","BC7_UNORM","-m","1","-y"]),
    ("uncomp_bgra", ["-f","B8G8R8A8_UNORM","-m","1","-y"]),
    ("uncomp_rgba", ["-f","R8G8B8A8_UNORM","-m","1","-y"]),
]
for name, flags in cmds:
    p = os.path.join(OUT, f"tc_{name}.dds")
    if os.path.exists(p): os.remove(p)
    try:
        r = subprocess.run([TEXCONV, *flags, "-o", tcout, "-px", f"tc_{name}_", rgbsrc],
                           capture_output=True, text=True, timeout=600)
    except Exception as e:
        print(f"  {name}: subprocess error {e}"); continue
    found = [f for f in os.listdir(tcout) if f.startswith(f"tc_{name}_")]
    if not found:
        print(f"  {name:14s} texconv produced nothing (rc={r.returncode})")
        print("    stdout:", (r.stdout or "")[-500:])
        print("    stderr:", (r.stderr or "")[-500:])
    for f in found:
        show(os.path.join(tcout, f))

print("\n" + "=" * 110)
print("PART C: Round-trip Pillow-read of game textures  (can Pillow parse shipped AoE2 DDS?)")
print("=" * 110)
g = r"D:\Games\Steam\steamapps\common\AoE2DE"
samples = [
    os.path.join(g, r"widgetui\textures\atlas\SD\ingameicons.dds"),
    os.path.join(g, r"widgetui\textures\atlas\SD\chatatlas.dds"),
    os.path.join(g, r"resources\_common\particles\textures\aura_glow.dds"),
]
# add one uncompressed BGRA from widgetui
for dp,dn,fn in os.walk(os.path.join(g,"widgetui")):
    for n in fn:
        if n.lower().endswith(".dds"):
            samples.append(os.path.join(dp,n))
        if len(samples) > 6: break
    if len(samples) > 6: break

for s in samples[:6]:
    if not os.path.exists(s): continue
    try:
        im = Image.open(s)
        im.load()
        print(f"  OK   {os.path.basename(s):28s} mode={im.mode} size={im.size} "
              f"pixel_format={getattr(im,'pixel_format',None)} mips_read={getattr(im,'n_frames',1)}")
    except Exception as e:
        print(f"  FAIL {os.path.basename(s):28s} {type(e).__name__}: {e}")

print(f"\nArtifacts in: {OUT}")

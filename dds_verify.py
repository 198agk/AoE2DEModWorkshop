import os, struct, subprocess, sys
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ddstest")
G = r"D:\Games\Steam\steamapps\common\AoE2DE"
TC = os.path.join(G, "Tools_Builds", "texconv.exe")

def fourcc_str(v):
    b = struct.pack("<I", v)
    return b.decode("ascii") if all(32 <= c < 127 for c in b) else f"0x{v:08X}"

def full(path, label=""):
    with open(path,"rb") as f: d = f.read(148)
    magic, = struct.unpack("<I", d[:4])
    if magic != 0x20534444:
        print(f"  {label or os.path.basename(path)}: NOT DDS"); return
    hsz, flags, h, w, pitch, depth, mips = struct.unpack("<7I", d[4:32])
    pfsize, pfflags, fourcc, bitcount = struct.unpack("<4I", d[76:92])
    masks = struct.unpack("<4I", d[92:108])
    caps, caps2, caps3, caps4, r2 = struct.unpack("<5I", d[108:128])
    px = "[R=%s G=%s B=%s A=%s]" % tuple(hex(m) for m in masks)
    print(f"  {label or os.path.basename(path)}")
    print(f"      {w}x{h}  hdrflags=0x{flags:06X}  pitch/linearSize={pitch}  depth={depth}  mipCount={mips}")
    print(f"      pfSize={pfsize} pfFlags=0x{pfflags:X}({'FOURCC' if pfflags&4 else ('RGBA' if pfflags&1 else 'RGB') if pfflags&0x40 else '?'}) "
          f"fourCC='{fourcc_str(fourcc)}' bitCount={bitcount}")
    print(f"      masks {px}   caps=0x{caps:X} (MIPMAPcap={bool(caps & 0x400000)})  caps2=0x{caps2:X}")
    print(f"      fileSize={os.path.getsize(path)}")
    # compute expected linear size for the top mip
    if fourcc_str(fourcc) in ("DXT1","DXT5","DXT3"):
        bs = 8 if fourcc_str(fourcc)=="DXT1" else 16
        print(f"      expected linearSize (top mip) = {max(1,(w+3)//4) * bs}")
    if fourcc_str(fourcc) == "DX10":
        v = struct.unpack("<5I", d[128:148])
        print(f"      DDS_HEADER_DXT10 = (dxgiFormat={v[0]}, resourceDimension={v[1]}, miscFlag={v[2]}, "
              f"arraySize={v[3]}, miscFlags2={v[4]})   [arraySize must be >=1 per MS spec]")

print("="*100); print("1. PITCH / LINEARSIZE: Pillow vs texconv vs SHIPPED GAME"); print("="*100)
for f in ["pil_dxt5_pf.dds","pil_dxt3_pf.dds","pil_dxt1_pf.dds",
          os.path.join("tc","tc_legacy_dxt5_src.dds"), os.path.join("tc","tc_legacy_dxt1_src.dds")]:
    p = os.path.join(OUT,f)
    if os.path.exists(p): full(p)
for f in [r"widgetui\textures\atlas\SD\ingameicons.dds", r"widgetui\textures\atlas\SD\chatatlas.dds",
          r"widgetui\textures\atlas\SD\ingamecursor.dds", r"resources\_common\particles\textures\aura_glow.dds"]:
    p = os.path.join(G,f)
    if os.path.exists(p): full(p, "GAME: "+os.path.basename(p))

print("\n" + "="*100); print("2. UNCOMPRESSED RGBA: Pillow byte-order masks vs SHIPPED GAME"); print("="*100)
for f in ["pil_uncompressed_rgba.dds", os.path.join("tc","tc_uncomp_rgba_src.dds"), os.path.join("tc","tc_uncomp_bgra_src.dds")]:
    p = os.path.join(OUT,f)
    if os.path.exists(p): full(p)
# find a shipped uncompressed RGBA and a shipped BGRA
seen = {}
for dp,dn,fn in os.walk(G):
    for n in fn:
        if not n.lower().endswith(".dds"): continue
        p = os.path.join(dp,n)
        try:
            with open(p,"rb") as f: d=f.read(108)
        except Exception: continue
        if len(d)<108: continue
        pfsize,pfflags,fourcc,bitcount = struct.unpack("<4I", d[76:92])
        masks = struct.unpack("<4I", d[92:108])
        if pfflags & 4: continue
        if bitcount != 32 or not (pfflags & 0x1): continue
        if masks[0]==0xff and "RGBAorder" not in seen:
            seen["RGBAorder"]=p; full(p, "GAME (mask 0xff|0xff00|0xff0000): "+os.path.basename(p))
        if masks[0]==0xff0000 and "BGRAorder" not in seen:
            seen["BGRAorder"]=p; full(p, "GAME (mask 0xff0000|0xff00|0xff): "+os.path.basename(p))
        if len(seen)>=2: break
    if len(seen)>=2: break

print("\n" + "="*100); print("3. FONT / 8-bit format examples in game"); print("="*100)
for f in [r"resources\_common\fonts\basic_bold_16.dds"]:
    p=os.path.join(G,f)
    if os.path.exists(p): full(p, "GAME: "+os.path.basename(p))

print("\n" + "="*100); print("4. PILLOW pixel_format support matrix (incl BC1/BC7/DX10 aliases)"); print("="*100)
im = Image.new("RGBA",(64,64),(255,0,0,128))
imrgb = im.convert("RGB")
for pf in ["DXT1","DXT3","DXT5","BC1","BC2","BC3","BC4","BC5","BC6H","BC7","ATI2","BC5U",""]:
    for tag, src in (("RGBA",im),("RGB",imrgb)):
        p=os.path.join(OUT,"_x.dds")
        try:
            kw={} if pf=="" else {"pixel_format":pf}
            src.save(p, format="DDS", **kw)
            with open(p,"rb") as f: d=f.read(148)
            _,_,_,_,_,_,_ = struct.unpack("<7I", d[4:32])
            pfsize,pfflags,fourcc,bitcount = struct.unpack("<4I", d[76:92])
            extra = ""
            if fourcc_str(fourcc)=="DX10":
                v=struct.unpack("<5I", d[128:148]); extra=f" dx10={v}"
            print(f"  pixel_format={pf!r:8s} mode={tag:4s} -> OK  fourCC='{fourcc_str(fourcc)}' bitCount={bitcount}{extra}")
            os.remove(p)
        except Exception as e:
            print(f"  pixel_format={pf!r:8s} mode={tag:4s} -> {type(e).__name__}: {e}")

print("\n" + "="*100); print("5. Does Pillow EVER write mipmaps / MIPMAPCOUNT? (scan all Pillow outputs)"); print("="*100)
for f in sorted(os.listdir(OUT)):
    if f.startswith("pil_") and f.endswith(".dds"):
        p=os.path.join(OUT,f)
        with open(p,"rb") as fh: d=fh.read(32)
        _,flags,_,_,_,_,mips = struct.unpack("<7I", d[4:32])
        caps, = struct.unpack("<I", d[108:112])
        print(f"  {f:34s} mipCount={mips} MIPMAPCOUNTflag={bool(flags & 0x20000)} MIPMAPcap={bool(caps&0x400000)}")

print("\n" + "="*100); print("6. texconv stdout (encoding-safe) for key commands"); print("="*100)
src = os.path.join(OUT,"src.png")
for label, flags in [("DXT5 -m 1", ["-f","DXT5","-m","1","-y"]),
                     ("DXT5 default mips", ["-f","DXT5","-y"]),
                     ("DXT1 -m 1", ["-f","DXT1","-m","1","-y"])]:
    r = subprocess.run([TC, *flags, "-o", os.path.join(OUT,"tc"), "-px", "run_", src],
                       capture_output=True, timeout=600)
    print(f"  --- texconv {' '.join(flags)} ---")
    for s in (r.stdout or b"").decode("utf-8","replace").splitlines(): print("      ", s)
    for s in (r.stderr or b"").decode("utf-8","replace").splitlines(): print("   E: ", s)
    print(f"      rc={r.returncode}")

print("\n" + "="*100); print("7. Pillow round-trip read of its own DXT5 output (quality sanity)"); print("="*100)
p=os.path.join(OUT,"pil_dxt5_pf.dds")
try:
    rt=Image.open(p); rt.load()
    print(f"  reopen OK mode={rt.mode} size={rt.size} pixel_format={getattr(rt,'pixel_format',None)}")
    ref=Image.open(src).convert("RGBA")
    import numpy as np
    a=np.asarray(rt.convert("RGBA"),dtype=float); b=np.asarray(ref.convert("RGBA"),dtype=float)
    print(f"  mean abs err vs source PNG: {abs(a-b).mean():.2f} (DXT5 is lossy; expected small)")
except Exception as e:
    print(f"  FAIL {type(e).__name__}: {e}")

print("\nDone.")

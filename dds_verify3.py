import os, struct
from PIL import Image
import numpy as np

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ddstest")

def find(name):
    for dp, dn, fn in os.walk(G):
        for n in fn:
            if n.lower() == name.lower(): return os.path.join(dp, n)
    return None

print("="*100); print("9. Pillow on a multi-mip game texture"); print("="*100)
p = find("exclamation_mark.dds")
print(f"  path: {p}")
im = Image.open(p); im.load()
print(f"  mode={im.mode} size={im.size} pixel_format={im.pixel_format} n_frames={getattr(im,'n_frames',1)}")
print(f"  info keys={list(im.info.keys())}")
print("  => Pillow exposes ONLY mip level 0; no mip-chain API on read or write.")

print("\n" + "="*100); print("10. BC7: game ships it, Pillow reads but cannot write"); print("="*100)
p = find("aura_glow.dds")
im = Image.open(p); im.load()
print(f"  {os.path.basename(p)} -> Pillow OK, pixel_format={im.pixel_format}, size={im.size}")
try:
    im.save(os.path.join(OUT,"_bc7write.dds"), format="DDS", pixel_format="BC7")
    print("  Pillow BC7 WRITE: OK")
except Exception as e:
    print(f"  Pillow BC7 WRITE: {type(e).__name__}: {e}")

print("\n" + "="*100); print("11. Where does the game use DX10/BC7 vs legacy fourCC?"); print("="*100)
import collections
use = collections.defaultdict(list)
for dp, dn, fn in os.walk(G):
    for n in fn:
        if not n.lower().endswith(".dds"): continue
        fp = os.path.join(dp, n)
        try:
            with open(fp,"rb") as f: d = f.read(148)
        except Exception: continue
        if len(d) < 128: continue
        pfp, fourcc = struct.unpack("<I", d[80:84])[0], struct.unpack("<I", d[84:88])[0]
        fc = struct.pack("<I", fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else ""
        if fc == "DX10":
            v = struct.unpack("<I", d[128:132])[0]
            rel = os.path.relpath(fp, G)
            top = rel.split(os.sep)[0] + "/" + (rel.split(os.sep)[1] if len(rel.split(os.sep))>1 else "")
            use[f"DX10 dxgi={v} in {top}"].append(rel)
        elif fc in ("DXT1","DXT3","DXT5"):
            rel = os.path.relpath(fp, G)
            top = rel.split(os.sep)[0] + "/" + (rel.split(os.sep)[1] if len(rel.split(os.sep))>1 else "")
            use[f"{fc} in {top}"].append(rel)
for k in sorted(use, key=lambda k: -len(use[k])):
    print(f"  {len(use[k]):5d}  {k}")
print("\n  --- BC7/DX10 sample paths ---")
for k in use:
    if k.startswith("DX10"):
        for pth in use[k][:6]: print("     ", pth)

print("\n" + "="*100); print("12. Are mips ever combined with DXT1/3/5 in HUD (widgetui)?"); print("="*100)
for dp, dn, fn in os.walk(os.path.join(G,"widgetui")):
    for n in fn:
        if not n.lower().endswith(".dds"): continue
        fp = os.path.join(dp,n)
        with open(fp,"rb") as f: d=f.read(32)
        _,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
        if mips > 1:
            print(f"  {os.path.relpath(fp,G)}  {w}x{h} mips={mips}")

print("\n" + "="*100); print("13. .smx/.slp/.sld presence and DESpriteTool modes"); print("="*100)
import subprocess
for ext in (".smx",".smp",".slp",".sld"):
    c = 0; samples=[]
    for dp,dn,fn in os.walk(G):
        for n in fn:
            if n.lower().endswith(ext):
                c += 1
                if len(samples)<3: samples.append(os.path.relpath(os.path.join(dp,n),G))
    print(f"  {ext:6s} count={c:6d}  e.g. {samples}")
r = subprocess.run([os.path.join(G,"Tools_Builds","Sprites","DESpriteTool.exe")], capture_output=True, timeout=120)
print("  DESpriteTool.exe no-arg stdout:")
for s in (r.stdout or b"").decode("utf-8","replace").splitlines()[:40]: print("     ", s)
for s in (r.stderr or b"").decode("utf-8","replace").splitlines()[:20]: print("   E: ", s)
print(f"  rc={r.returncode}")

print("\n" + "="*100); print("14. SoftwareLicenses for texconv/DirectXTex"); print("="*100)
sl = os.path.join(G, "SoftwareLicenses")
if os.path.isdir(sl):
    for n in os.listdir(sl):
        if any(k in n.lower() for k in ("directx","tex","microsoft","mit")):
            print("  ", n)
    print("  --- all entries ---")
    for n in sorted(os.listdir(sl))[:60]: print("     ", n)

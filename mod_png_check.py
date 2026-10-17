import os

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
M = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"

print("="*100)
print("A. Does the BASE INSTALL ship .dds or .png at the same widgetui paths the mods override?")
print("="*100)
samples = [
 r"widgetui\textures\ingame\emblems\achaemenids",
 r"widgetui\textures\ingame\panels\menu-panel_full",
 r"widgetui\textures\ingame\panels\AFRI\topbar",
 r"widgetui\textures\ingame\icons\minimap_flare_normal",
 r"widgetui\textures\menu\buttons\button_big_normal",
 r"widgetui\textures\menu\tabs\tab1_normal",
 r"widgetui\textures\ingame\chat\chatbar_bg",
 r"widgetui\textures\menu\mixer\loading",
 r"widgetui\textures\backgrounds\mainmenu_bg",
 r"widgetui\textures\backgrounds\wide_default_background",
 r"widgetui\textures\listboxes\table\tablestyle1_inlay",
 r"widgetui\textures\table\tablestyle1_inlay",
 r"widgetui\textures\ingame\recordedgames\text-dropdown",
 r"resources\_common\wpfg\resources\aoe_logo",
 r"resources\_common\wpfg\resources\scroll\knot",
]
for s in samples:
    base = os.path.join(G, s)
    found = []
    for ext in (".dds",".png",".jpg",".bmp",".tga"):
        if os.path.exists(base+ext): found.append(ext+" "+str(os.path.getsize(base+ext)))
    print(f"  {s:70s} -> {'MISSING' if not found else ', '.join(found)}")

print("\n" + "="*100)
print("B. Counts: base install widgetui texture file extensions")
print("="*100)
import collections
c = collections.Counter()
for dp,dn,fn in os.walk(os.path.join(G,"widgetui")):
    for n in fn: c[os.path.splitext(n)[1].lower()] += 1
print("  widgetui:", dict(c))
c2 = collections.Counter()
for dp,dn,fn in os.walk(os.path.join(G,"resources","_common","wpfg")):
    for n in fn: c2[os.path.splitext(n)[1].lower()] += 1
print("  resources/_common/wpfg:", dict(c2))

print("\n" + "="*100)
print("C. Mod file-extension inventory (does any mod ship .dds at all?)")
print("="*100)
for dp,dn,fn in os.walk(M):
    exts = collections.Counter(os.path.splitext(n)[1].lower() for n in fn)
    if os.path.basename(dp) in ("mods","subscribed") or True:
        pass
sub = [os.path.join(M,d) for d in os.listdir(M) if os.path.isdir(os.path.join(M,d))]
for p in sub:
    c = collections.Counter()
    for dp,dn,fn in os.walk(p):
        for n in fn: c[os.path.splitext(n)[1].lower()] += 1
    print(f"  {os.path.basename(p)[:52]:54s} {dict(c)}")

print("\n" + "="*100)
print("D. info.json / mod-status.json structure")
print("="*100)
M0 = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
for f in ["mod-status.json"]:
    p = os.path.join(M0,f)
    if os.path.exists(p):
        print(f"  --- {f} (first 1200 chars) ---")
        print("   ", open(p,encoding="utf-8",errors="replace").read()[:1200])
for d in os.listdir(M):
    ip = os.path.join(M,d,"info.json")
    if os.path.isfile(ip):
        print(f"  --- {d}/info.json ---")
        print("   ", open(ip,encoding="utf-8",errors="replace").read()[:600])

print("\n" + "="*100)
print("E. Does a mod .dds exist anywhere that is NOT DXT1/DXT5? (modder format survey)")
print("="*100)
import struct
for dp,dn,fn in os.walk(M):
    for n in fn:
        if not n.lower().endswith(".dds"): continue
        p=os.path.join(dp,n)
        with open(p,"rb") as f: d=f.read(148)
        pfp,fourcc,bitcount = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
        _,_,_,_,pitch,depth,mips = struct.unpack("<7I", d[4:32])
        masks = struct.unpack("<4I", d[92:108])
        print(f"  {os.path.relpath(p,M)}  pfFlags=0x{pfp:X} fourCC={fourcc!r} bits={bitcount} mips={mips} depth={depth} masks={[hex(m) for m in masks]}")

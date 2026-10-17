import os, collections, struct
from PIL import Image

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(G, "widgetui")
M = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"

print("="*100)
print("1. Names present as BOTH .dds and .png inside widgetui/")
print("="*100)
names = collections.defaultdict(set)
for dp,dn,fn in os.walk(W):
    for n in fn:
        stem, ext = os.path.splitext(n)
        names[os.path.join(dp,stem).lower()].add(ext.lower())
both = [k for k,v in names.items() if ".dds" in v and ".png" in v]
dds_only = [k for k,v in names.items() if v=={".dds"}]
png_only = [k for k,v in names.items() if v=={".png"}]
print(f"  total stems={len(names)}  both={len(both)}  dds_only={len(dds_only)}  png_only={len(png_only)}")
print("\n  --- sample BOTH ---")
for k in sorted(both)[:15]: print("   ", os.path.relpath(k, G))
print("\n  --- sample DDS_ONLY ---")
for k in sorted(dds_only)[:15]: print("   ", os.path.relpath(k, G))
print("\n  --- sample PNG_ONLY ---")
for k in sorted(png_only)[:15]: print("   ", os.path.relpath(k, G))

print("\n" + "="*100)
print("2. Where are the .dds files in widgetui? (directory histogram)")
print("="*100)
c = collections.Counter()
for dp,dn,fn in os.walk(W):
    d = sum(1 for n in fn if n.lower().endswith(".dds"))
    if d: c[os.path.relpath(dp,W)] = d
for k,v in sorted(c.items(), key=lambda kv:-kv[1])[:25]: print(f"  {v:5d}  {k}")

print("\n" + "="*100)
print("3. Where are the .png files in widgetui? (directory histogram)")
print("="*100)
c = collections.Counter()
for dp,dn,fn in os.walk(W):
    d = sum(1 for n in fn if n.lower().endswith(".png"))
    if d: c[os.path.relpath(dp,W)] = d
for k,v in sorted(c.items(), key=lambda kv:-kv[1])[:25]: print(f"  {v:5d}  {k}")

print("\n" + "="*100)
print("4. Mod PNG vs base PNG dimensions (does the modder keep identical size?)")
print("="*100)
pairs = [
 (r"widgetui\textures\ingame\emblems\achaemenids.png", "182654_Age of Anime (Chibi Edition)"),
 (r"widgetui\textures\ingame\emblems\britons.png", "182654_Age of Anime (Chibi Edition)"),
 (r"widgetui\textures\ingame\panels\menu-panel_full.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\ingame\panels\AFRI\topbar.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\menu\buttons\button_big_normal.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\menu\tabs\tab1_normal.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\ingame\chat\chatbar_bg.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\ingame\icons\minimap_flare_normal.png", "550412_透明主题整合自用"),
 (r"resources\_common\wpfg\resources\scroll\knot.png", "550412_透明主题整合自用"),
 (r"resources\_common\wpfg\resources\aoe_logo.png", "550412_透明主题整合自用"),
 (r"widgetui\textures\ingame\recordedgames\text-dropdown.png", "550412_透明主题整合自用"),
]
for rel, mod in pairs:
    bp = os.path.join(G, rel)
    mp = os.path.join(M, mod, rel)
    def info(p):
        if not os.path.exists(p): return "MISSING"
        im = Image.open(p)
        return f"{im.size} {im.mode} fmt={im.format}"
    print(f"  {rel}")
    print(f"      BASE: {info(bp)}")
    print(f"      MOD : {info(mp)}   {'SAME SIZE' if os.path.exists(bp) and os.path.exists(mp) and Image.open(bp).size==Image.open(mp).size else 'DIFFERENT'}")

print("\n" + "="*100)
print("5. Are mod DDS backgrounds exactly the base size? (5120x2160 vs base)")
print("="*100)
for rel in [r"widgetui\textures\backgrounds\mainmenu_bg.dds", r"widgetui\textures\backgrounds\wide_default_background.dds"]:
    for label, root in (("BASE", G), ("MOD", os.path.join(M, "550412_透明主题整合自用"))):
        p = os.path.join(root, rel)
        with open(p,"rb") as f: d=f.read(148)
        _,flags,h,w,pitch,depth,mips = struct.unpack("<7I", d[4:32])
        pfp,fourcc,bc = struct.unpack("<I",d[80:84])[0], struct.unpack("<I",d[84:88])[0], struct.unpack("<I",d[88:92])[0]
        fc = struct.pack("<I",fourcc).decode("ascii","replace") if all(32<=c<127 for c in struct.pack("<I",fourcc)) else hex(fourcc)
        exp = max(1,(w+3)//4) * (8 if fc=="DXT1" else 16)
        print(f"  {label:5s} {rel.split(chr(92))[-1]:28s} {w}x{h} mips={mips} depth={depth} fourCC={fc} linear={pitch} expectedLinear={exp} flags=0x{flags:06X} size={os.path.getsize(p)}")

print("\n" + "="*100)
print("6. Base vs mod .dds backgrounds: same relative path AND same dims → proves path-replacement model")
print("="*100)
print("  base mainmenu_bg dims:", Image.open(os.path.join(G, r'widgetui\textures\backgrounds\mainmenu_bg.dds')).size)
print("  mod  mainmenu_bg dims:", Image.open(os.path.join(M, '550412_透明主题整合自用', r'widgetui\textures\backgrounds\mainmenu_bg.dds')).size)

print("\n" + "="*100)
print("7. Any .ps1 / .json under widgetui that maps texture names?")
print("="*100)
for dp,dn,fn in os.walk(W):
    for n in fn:
        if n.lower().endswith((".ps1",".json")):
            print("   ", os.path.relpath(os.path.join(dp,n), W))

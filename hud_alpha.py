import re, os, glob
from PIL import Image

# --- 1. alpha presence in shipped HUD textures ---
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
samples = [
    r"widgetui\textures\ingame\units\000_50730.DDS",
    r"widgetui\textures\ingame\units\000_50706.dds",
    r"widgetui\textures\ingame\buildings\108_ant_tower_guard.dds",
    r"widgetui\textures\atlas\SD\ingameicons.dds",
    r"widgetui\textures\atlas\SD\chatatlas.dds",
    r"widgetui\textures\atlas\SD\defaultwidgets.dds",
    r"widgetui\textures\backgrounds\mainmenu_bg.dds",
]
print("=== ALPHA STATS OF SHIPPED HUD DDS ===")
for rel in samples:
    p = os.path.join(GAME, rel)
    if not os.path.exists(p):
        print(f"  MISSING {rel}")
        continue
    im = Image.open(p).convert("RGBA")
    a = im.getchannel("A")
    h = a.histogram()
    mn, mx = a.getextrema()
    zero = h[0]
    full = h[255]
    tot = im.width * im.height
    print(f"  {rel}")
    print(f"     {im.width}x{im.height} alpha min={mn} max={mx} #alpha==0 {zero} ({100*zero/tot:.1f}%) #alpha==255 {full} ({100*full/tot:.1f}%)")

print()
print("=== ALPHA STATS OF SHIPPED HUD PNG (base + anime mod emblems) ===")
pngs = [
    os.path.join(GAME, r"widgetui\textures\ingame\emblems\britons.png"),
    os.path.join(GAME, r"widgetui\textures\ingame\panels\menu-panel_full.png"),
    os.path.join(GAME, r"widgetui\textures\menu\buttons\button_big_normal.png"),
    os.path.join(GAME, r"widgetui\textures\ingame\chat\chatbar_bg.png"),
    os.path.join(GAME, r"resources\_common\wpfg\resources\scroll\knot.png"),
    os.path.join(r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)", r"widgetui\textures\ingame\emblems\britons.png"),
]
for p in pngs:
    if not os.path.exists(p):
        print(f"  MISSING {p}")
        continue
    im = Image.open(p)
    mode = im.mode
    a = im.convert("RGBA").getchannel("A")
    h = a.histogram()
    tot = im.width*im.height
    print(f"  {os.path.relpath(p)}")
    print(f"     mode={mode} {im.width}x{im.height} alpha min/max={a.getextrema()} #0 {h[0]} ({100*h[0]/tot:.1f}%) #255 {h[255]} ({100*h[255]/tot:.1f}%)")

# --- 2. blend / alpha related strings in the exe ---
print()
print("=== exe strings: blend/alpha ===")
data = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{3,}", data)]
keys = ["inversealpha", "player color", "playercolor", "premultipl", "alphatest", "alpha test",
        "alpha blend", "opacity", "transparen", "blendmode", "blend mode", "mask"]
seen = set()
n = 0
for off, s in strs:
    low = s.lower()
    if any(k in low for k in keys) and 4 <= len(s) <= 90 and s not in seen:
        seen.add(s)
        print(f"  0x{off:08X}  {s!r}")
        n += 1
        if n >= 45:
            print("  ...(truncated)")
            break

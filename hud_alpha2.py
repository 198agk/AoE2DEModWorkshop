import re, os
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
p = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems\britons.png"
print("=== MOD (anime) emblem alpha ===")
if os.path.exists(p):
    im = Image.open(p)
    a = im.convert("RGBA").getchannel("A"); h = a.histogram(); tot = im.width*im.height
    print(f"  mode={im.mode} {im.width}x{im.height} alpha {a.getextrema()} #0={h[0]} ({100*h[0]/tot:.1f}%) #255={h[255]} ({100*h[255]/tot:.1f}%)")
else:
    print("  MISSING")

print()
print("=== exe strings: blend / alpha / premultiply ===")
data = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{3,}", data)]
keys = ["inversealpha", "alphablend", "alphatest", "alpha test", "premultipl", "straight alpha",
        "blendmode", "blend mode", "blendstate", "alphamode", "alpha mode", "srcblend", "srcalpha",
        "playercolor", "player color", "colormask", "opacity", "transparen", "chroma"]
seen, n = set(), 0
for off, s in strs:
    low = s.lower()
    if any(k in low for k in keys) and 4 <= len(s) <= 100 and s not in seen:
        seen.add(s); print(f"  0x{off:08X}  {s!r}"); n += 1
        if n >= 60:
            print("  ...(truncated)"); break

print()
print("=== exe strings: texture format / bc / fourcc / mip ===")
keys2 = ["bc1", "bc2", "bc3", "bc4", "bc5", "bc6", "bc7", "dxt", "fourcc", "mip", "blockcomp", "block compressed", "texel"]
seen, n = set(), 0
for off, s in strs:
    low = s.lower()
    if any(k in low for k in keys2) and 3 <= len(s) <= 100 and s not in seen:
        seen.add(s); print(f"  0x{off:08X}  {s!r}"); n += 1
        if n >= 70:
            print("  ...(truncated)"); break

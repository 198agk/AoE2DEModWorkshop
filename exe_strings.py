import re, sys
p = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(p, "rb").read()
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{4,}", data)]

def show(title, keys, limit=70):
    print()
    print("=== " + title + " ===")
    n = 0
    for off, s in strs:
        low = s.lower()
        if any(k in low for k in keys):
            print(f"  0x{off:08X}  {s}")
            n += 1
            if n >= limit:
                print("  ...(truncated)")
                break

show("LOADER / CODEC CLASS NAMES", ["stbimage","stb_image","loadfrommemory","imageloader","textureloader",
     "loaddds","ddsloader","squish","directxtex","d3dx","loadtexture","loadfromfile","stbi_","stb__"])
show("MOD / ASSET ERROR STRINGS", ["mod texture","supported format","out of space","feature level",
     "low fidelity","format support","atlas \""])
show("atlas diagnostics", ["atlas"], 60)
show("format / page tokens", ["_page", "enable_atlas", "mod_bc3", "mod_sld", "hdn_sld", "dmg_sld", "enable_"])
show("SLD / sprite asset errors", ["sld", "smx", "smp asset"], 60)

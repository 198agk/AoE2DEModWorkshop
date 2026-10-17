import re
p = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(p, "rb").read()
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{3,}", data)]

def show(title, keys, limit=80, mode="any"):
    print()
    print("=== " + title + " ===")
    n = 0
    for off, s in strs:
        low = s.lower()
        hit = any(k in low for k in keys) if mode == "any" else all(k in low for k in keys)
        if hit:
            print(f"  0x{off:08X}  {s!r}")
            n += 1
            if n >= limit:
                print("  ...(truncated)")
                break

# any string containing the literal token 'dds' AND looking like an error/format
print("=== strings containing 'dds' (case-sensitive-ish) that are >=6 chars ===")
n = 0
for off, s in strs:
    if "dds" in s and len(s) >= 8 and re.search(r"[A-Za-z]", s):
        low = s.lower()
        if any(k in low for k in ["texture","asset","load","unsupported","format","mip","error","fail","header","invalid"]):
            print(f"  0x{off:08X}  {s!r}")
            n += 1
            if n >= 60:
                print("  ...(truncated)")
                break

show("DDS-ish format errors", ["dds","dxt"], 80)
show("compressed texture / block formats", ["block compressed","block-compressed","uncompressed","compressed texture",
     "unsupported format","invalid format"])
show("'supported format' family", ["supported format","supported texture","format is not","not supported"])
show("source file paths leaked (Engine/Resource/Texture)", ["engine\\resource","engine\\graphics","engine\\texture",
     "texture.cpp","texture.h","dds.cpp","image.cpp","resourcemanager"], 60)

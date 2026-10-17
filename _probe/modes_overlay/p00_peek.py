import os, json, sys
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"

def walk_inv(root):
    inv = {}   # relpath(lower, / sep) -> size
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                sz = -1
            rel = os.path.relpath(p, root).replace("\\", "/")
            inv[rel] = sz
    return inv

def summarize(name, inv):
    tot = sum(v for v in inv.values() if v > 0)
    print(f"[{name}] files={len(inv)} bytes={tot}")
    return tot

print("=== GAME ROOT LISTING ===")
for e in sorted(os.listdir(GAME)):
    p = os.path.join(GAME, e)
    print(("DIR  " if os.path.isdir(p) else "FILE "), e, ("" if os.path.isdir(p) else os.path.getsize(p)))

print()
print("=== modes/ listing ===")
m = os.path.join(GAME, "modes")
for e in sorted(os.listdir(m)):
    p = os.path.join(m, e)
    print(("DIR  " if os.path.isdir(p) else "FILE "), e, ("" if os.path.isdir(p) else os.path.getsize(p)))

print()
print("=== Pompeii.json ===")
pj = os.path.join(m, "Pompeii", "Pompeii.json")
print("size:", os.path.getsize(pj))
data = open(pj, "rb").read()
print(data.decode("utf-8", "replace"))

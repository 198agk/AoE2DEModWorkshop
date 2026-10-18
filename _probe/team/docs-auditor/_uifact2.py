# -*- coding: utf-8 -*-
import sys, io, os, json, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"

def walk(root):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            yield os.path.join(dp, f)

print("== palettes RECURSIVE ==")
pal_dir = os.path.join(G, "resources", "_common", "palettes")
ext = collections.Counter()
magic = collections.Counter()
for p in walk(pal_dir):
    ext[os.path.splitext(p)[1].lower()] += 1
    try:
        head = open(p, "rb").read(12)
        magic[head.rstrip(b"\x00\r\n ")[:9].decode("ascii", "replace")] += 1
    except Exception as e:
        magic["ERR:" + type(e).__name__] += 1
print(" ext:", dict(ext))
print(" magic:", dict(magic))
print(" pal+palx:", ext[".pal"] + ext[".palx"])

print("\n== widgetui (game root) ==")
wu = os.path.join(G, "widgetui")
files = [f for f in os.listdir(wu) if os.path.isfile(os.path.join(wu, f))]
print(" files:", len(files), " .json:", sum(1 for f in files if f.endswith(".json")))

withwidgets = 0
tot = 0
types = set()
for f in files:
    if not f.endswith(".json"):
        continue
    d = json.load(open(os.path.join(wu, f), encoding="utf-8-sig"))
    if not isinstance(d, dict):
        continue
    w = d.get("widgets") or {}
    if w:
        withwidgets += 1
        tot += len(w)
        for v in w.values():
            if isinstance(v, dict) and v.get("type") is not None:
                types.add(v["type"])
print(" with widgets:", withwidgets, " total widgets:", tot, " distinct types:", len(types))

print("\n== widgetui/textures ==")
wt = os.path.join(G, "widgetui", "textures")
if os.path.isdir(wt):
    c = collections.Counter(os.path.splitext(p)[1].lower() for p in walk(wt))
    print(" ", dict(c), " total:", sum(c.values()))

print("\n== wpfg ==")
wp = os.path.join(G, "resources", "_common", "wpfg")
c = collections.Counter(os.path.splitext(p)[1].lower() for p in walk(wp))
print(" ", dict(c), " total:", sum(c.values()))

print("\n== graphics ==")
gd = os.path.join(G, "resources", "_common", "drs", "graphics")
c = collections.Counter(os.path.splitext(p)[1].lower() for p in os.listdir(gd))
print(" ", dict(c), " total:", sum(c.values()))

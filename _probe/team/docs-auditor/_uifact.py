# -*- coding: utf-8 -*-
"""Re-measure the ui-textures and sprites numeric claims against the shipped game."""
import sys, io, os, json, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"

def walk(root):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            yield os.path.join(dp, f)

print("== palettes ==")
pal_dir = os.path.join(G, "resources", "_common", "palettes")
ext = collections.Counter()
magic = collections.Counter()
sizes = {}
for p in sorted(os.listdir(pal_dir)):
    fp = os.path.join(pal_dir, p)
    if os.path.isdir(fp):
        print("  [subdir]", p, len(os.listdir(fp)))
        continue
    ext[os.path.splitext(p)[1].lower()] += 1
    with open(fp, "rb") as fh:
        head = fh.read(12)
    magic[head.rstrip(b"\x00\r\n ")[:9].decode("ascii", "replace")] += 1
    sizes[p] = os.path.getsize(fp)
print(" ext:", dict(ext))
print(" magic:", dict(magic))
print(" total files:", sum(ext.values()))

print("\n== widgetui (game root) ==")
wu = os.path.join(G, "widgetui")
files = [f for f in os.listdir(wu) if os.path.isfile(os.path.join(wu, f))]
print(" files:", len(files), " .json:", sum(1 for f in files if f.endswith(".json")))
print(" non-json:", [f for f in files if not f.endswith(".json")][:10])

withwidgets = 0
tot_widgets = 0
types = set()
for f in files:
    if not f.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(wu, f), encoding="utf-8-sig"))
    except Exception as e:
        print("  parse fail", f, e)
        continue
    w = d.get("widgets") or {}
    if w:
        withwidgets += 1
        tot_widgets += len(w)
        for v in w.values():
            if isinstance(v, dict):
                t = v.get("type")
                if t is not None:
                    types.add(t)
print(" with widgets:", withwidgets, " total widgets:", tot_widgets, " distinct types:", len(types))

print("\n== widgetui/textures ==")
wt = os.path.join(G, "widgetui", "textures")
if os.path.isdir(wt):
    c = collections.Counter(os.path.splitext(p)[1].lower() for p in walk(wt))
    print(" ", dict(c), " total:", sum(c.values()))

print("\n== wpfg ==")
wp = os.path.join(G, "resources", "_common", "wpfg")
c = collections.Counter(os.path.splitext(p)[1].lower() for p in walk(wp))
print(" ", dict(c), " total:", sum(c.values()))

print("\n== graphics dir ==")
gd = os.path.join(G, "resources", "_common", "drs", "graphics")
c = collections.Counter(os.path.splitext(p)[1].lower() for p in os.listdir(gd))
print(" ", dict(c), " total:", sum(c.values()))

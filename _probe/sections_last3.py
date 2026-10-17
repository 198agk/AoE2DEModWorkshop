"""Resolve the last three icons.json sections: Notification, MenuIcons, StatIcons.

sections_rest.py proved MapIcons -> wpfg/resources/mapicons/<stem>.png (197/197).
These three stayed unresolved:
  Notification  2  ('wonder_icon', 'relic_icon')          -> nowhere yet
  MenuIcons     9  (submenu_button_base, ...)             -> nowhere yet
  StatIcons    24  -> 6 in materials.json, 0 as filename  -> partial

Method: search the whole game tree for a file whose stem equals the value, in
any extension; also search widgetui/**/*.json for the value as a material or
widget reference; also check materials.json Textures[] RefName.  Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")
ICONS = os.path.join(WIDGETUI, "icons.json")

sys.stdout.reconfigure(encoding="utf-8")


def load_json(p):
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return json.load(f)


print("=" * 90)
print("last three icons.json sections")
print("=" * 90)

doc = load_json(ICONS)
for name in ("Notification", "MenuIcons", "StatIcons", "MapIcons", "CivHero"):
    sec = doc.get(name)
    if isinstance(sec, dict):
        print("  %-14s %3d entries" % (name, len(sec)))
    else:
        print("  %-14s %r" % (name, type(sec).__name__))

# ---- build the on-disk stem index once --------------------------------------
print()
print("indexing game tree stems ...")
stem_index = {}          # lowercased stem -> [relpath, ...]
scanned = 0
SKIP = ("campaign", "drs", "movies", "sound")
for root, dirs, files in os.walk(GAME):
    low = root.lower()
    dirs[:] = [d for d in dirs if not any(s in d.lower() for s in SKIP)]
    for fn in files:
        scanned += 1
        stem, ext = os.path.splitext(fn)
        stem_index.setdefault(stem.lower(), []).append(
            os.path.relpath(os.path.join(root, fn), GAME))
print("  files scanned: %d   distinct stems: %d" % (scanned, len(stem_index)))

# ---- materials.json: collect material names, TextureRefs, and FileName stems -
mat = load_json(os.path.join(WIDGETUI, "materials.json"))
mat_names = set()
tex_refs = set()
file_stems = set()
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        mat_names.add(md["Name"])
    if md.get("TextureRef"):
        tex_refs.add(md["TextureRef"])
for at in mat.get("AtlasTextures", []):
    for t in at.get("Textures", []):
        fn = t.get("FileName")
        if fn:
            file_stems.add(os.path.splitext(os.path.basename(fn))[0].lower())
print("  materials.json: %d names, %d texturerefs, %d file stems"
      % (len(mat_names), len(tex_refs), len(file_stems)))

# ---- widgetui layouts: which values appear as a Material/TextureRef ---------
print()
print("scanning widgetui layouts for material references ...")
layout_text = {}
for root, dirs, files in os.walk(WIDGETUI):
    for fn in files:
        if fn.lower().endswith(".json"):
            p = os.path.join(root, fn)
            try:
                with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
                    layout_text[fn.lower()] = f.read()
            except Exception:
                pass
print("  layouts read: %d" % len(layout_text))


def resolve(value):
    """Return (kind, detail)."""
    v = value.lower()
    hits = []
    if value in mat_names or v in {n.lower() for n in mat_names}:
        hits.append("materials:Name")
    if value in tex_refs or v in {n.lower() for n in tex_refs}:
        hits.append("materials:TextureRef")
    if v in file_stems:
        hits.append("materials:FileName-stem")
    if v in stem_index:
        hits.append("disk-stem(%d)" % len(stem_index[v]))
    # widget layouts
    refs = [fn for fn, txt in layout_text.items() if value in txt]
    if refs:
        hits.append("layout_ref(%d)" % len(refs))
    return hits


for sec_name in ("Notification", "MenuIcons", "StatIcons"):
    sec = doc.get(sec_name) or {}
    print()
    print("=" * 90)
    print("%s  (%d entries)" % (sec_name, len(sec)))
    print("=" * 90)
    for k in sorted(sec.keys()):
        v = sec[k]
        if v in (None, "", []):
            continue
        vs = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        hits = resolve(vs)
        mark = "OK  " if hits else "????"
        print("  %-8s %-34s %s" % (mark, vs[:34], "; ".join(hits) if hits else "<unresolved>"))
        if hits and hits[0].startswith("disk-stem"):
            for rel in stem_index[vs.lower()][:3]:
                print("               -> %s" % rel)

print()
print("=" * 90)
print("done")

# -*- coding: utf-8 -*-
"""Resolve every material referenced by scorepanel.json + resourcepanel.json to a real image file.
Also: fix combined.box codepoint array parse; census materials.json."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, struct, collections
from PIL import Image

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
FD = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = _HERE_PATH("_probe", "hud_render")
rep = io.StringIO()

# ---------- combined.box codepoint tail ----------
bb = open(os.path.join(FD, "combined.box"), "rb").read()
ver, nglyph, npages = struct.unpack_from("<III", bb, 0)
HDR, REC = 16, 40
expect = HDR + nglyph * REC
tailbytes = bb[expect:]
rep.write("=== combined.box tail: %d bytes for %d glyphs = %.3f B/glyph ===\n"
          % (len(tailbytes), nglyph, len(tailbytes) / nglyph))
codes = list(struct.unpack_from("<%dH" % nglyph, tailbytes, 0))
rep.write("as u16[%d]: first 16 = %s\n" % (nglyph, codes[:16]))
rep.write("min=%d max=%d unique=%d\n" % (min(codes), max(codes), len(set(codes))))
for want, lbl in [(9, "TAB"), (10, "LF"), (32, "space"), (33, "!"), (48, "0"), (65, "A"), (97, "a")]:
    rep.write("  code %3d (%s) present=%s\n" % (want, lbl, want in codes))

# ---------- materials.json ----------
mp = os.path.join(W, "materials.json")
mj = json.load(open(mp, "r", encoding="utf-8-sig"))
rep.write("\n\n=== materials.json top keys: %s ===\n" % list(mj.keys()))
mats, atlases, globals_ = mj["Materials"], mj["AtlasTextures"], mj["GlobalTextures"]
rep.write("Materials=%d AtlasTextures=%d GlobalTextures=%d\n" % (len(mats), len(atlases), len(globals_)))

MAT = {}
for e in mats:
    d = e["MaterialDef"]
    MAT[d["Name"]] = d
ATL = {}
for e in atlases:
    d = e["AtlasDef"]
    ATL[d["Name"]] = d
GLB = {}
for e in globals_:
    d = e["TextureDef"]
    GLB[d["Name"]] = d

rep.write("distinct material names: %d\n" % len(MAT))
rep.write("distinct atlas names: %s\n" % sorted(ATL.keys()))
tc = collections.Counter(d.get("Type") for d in MAT.values())
rep.write("MaterialDef.Type: %s\n" % dict(tc))
bc = collections.Counter(d.get("Blend") for d in MAT.values())
rep.write("MaterialDef.Blend: %s\n" % dict(bc))
ark = collections.Counter(tuple(sorted(d.keys())) for d in MAT.values())
rep.write("MaterialDef key-sets: %s\n" % dict(ark))
adk = collections.Counter(tuple(sorted(d.keys())) for d in ATL.values())
rep.write("AtlasDef key-sets: %s\n" % {str(k): v for k, v in adk.items()})
gdk = collections.Counter(tuple(sorted(d.keys())) for d in GLB.values())
rep.write("TextureDef key-sets: %s\n" % {str(k): v for k, v in gdk.items()})

# exact key names
rep.write("\n--- sample AtlasDef (ingamepanels) ---\n")
for k, v in ATL.items():
    d = v
    rep.write("Atlas %s: MaxW=%s MaxH=%s UHDSource=%s HDSource=%s DefaultSource=%s nTextures=%d\n"
              % (k, d.get("MaxWidth"), d.get("MaxHeight"), d.get("UHDSource"),
                 d.get("HDSource"), d.get("DefaultSource"), len(d.get("Textures", []))))
    if d.get("Textures"):
        rep.write("   tex[0]=%s\n" % json.dumps(d["Textures"][0]))
    break
rep.write("\n--- all atlas source fields ---\n")
for k, d in sorted(ATL.items()):
    rep.write("%-28s UHD=%-40s HD=%-40s DEF=%s  n=%d\n"
              % (k, d.get("UHDSource"), d.get("HDSource"), d.get("DefaultSource"),
                 len(d.get("Textures", []))))

# ---------- resolve materials used by the two panels ----------
def collect_material_refs(path):
    d = json.load(open(path, "r", encoding="utf-8-sig"))
    found = []
    def rec(o, wname):
        if isinstance(o, dict):
            if "Material" in o and isinstance(o["Material"], str):
                found.append((wname, o["Material"]))
            for k, v in o.items():
                rec(v, wname)
        elif isinstance(o, list):
            for v in o:
                rec(v, wname)
    for cname, coll in d.items():
        if isinstance(coll, dict):
            rec(coll.get("Widgets"), cname)
    return found

WIDGETUI = W

def resolve(matname):
    """Return ('ok', kind, path, uvrect) or ('fail', reason)."""
    d = MAT.get(matname)
    if d is None:
        return ("fail", "material-not-found")
    t = d.get("Type")
    if t == "Atlas":
        a = ATL.get(d.get("AtlasRef"))
        if a is None:
            return ("fail", "atlas-not-found:%s" % d.get("AtlasRef"))
        texref = d.get("TextureRef")
        hit = None
        for tx in a.get("Textures", []):
            if tx.get("RefName") == texref:
                hit = tx; break
        if hit is None:
            return ("fail", "atlas-entry-not-found:%s/%s" % (d.get("AtlasRef"), texref))
        fn = hit.get("FileName")
        p = os.path.join(WIDGETUI, fn) if fn else None
        if not p or not os.path.exists(p):
            return ("fail", "atlas-file-missing:%s" % fn)
        uv = (hit.get("imageTLX"), hit.get("imageTLY"), hit.get("imageBRX"), hit.get("imageBRY"))
        return ("ok", "atlas", p, uv)
    if t == "Texture":
        texref = d.get("TextureRef")
        g = GLB.get(texref)
        fn = None
        if g is not None:
            fn = g.get("FileName")
        if fn is None:
            # maybe TextureRef is itself a path
            cand = os.path.join(WIDGETUI, texref)
            if os.path.exists(cand):
                return ("ok", "texture-direct", cand, None)
            return ("fail", "global-texture-not-found:%s" % texref)
        p = os.path.join(WIDGETUI, fn)
        if not os.path.exists(p):
            return ("fail", "global-file-missing:%s" % fn)
        return ("ok", "texture", p, None)
    if t == "Color":
        return ("fail", "type-color-no-texture")
    return ("fail", "unknown-material-type:%s" % t)

allrows = []
for panel in ["scorepanel.json", "resourcepanel.json"]:
    p = os.path.join(W, panel)
    refs = collect_material_refs(p)
    rep.write("\n\n=== %s : %d Material refs ===\n" % (panel, len(refs)))
    c = collections.Counter()
    for wname, m in refs:
        r = resolve(m)
        c[(r[0], r[1] if r[0] == "fail" else r[1])] += 1
        allrows.append((panel, wname, m, r[0], r[1] if r[0] == "fail" else r[1],
                        r[2] if r[0] == "ok" else "", r[3] if r[0] == "ok" else None))
        rep.write("  %-22s %-30s -> %s\n" % (wname, m, r[0] if r[0] == "fail" else "%s %s" % (r[1], r[2])))
    rep.write("-- summary --\n")
    for k, v in c.most_common():
        rep.write("   %-40s %d\n" % (str(k), v))

# global material usage census: how many of the 4555 resolve
ok = 0; fails = collections.Counter()
for name in MAT:
    r = resolve(name)
    if r[0] == "ok":
        ok += 1
    else:
        fails[r[1].split(":")[0]] += 1
rep.write("\n\n=== ALL 4555 materials resolvability ===\n")
rep.write("resolvable: %d / %d = %.2f%%\n" % (ok, len(MAT), 100.0*ok/len(MAT)))
rep.write("failures: %s\n" % dict(fails))

json.dump(allrows, open(os.path.join(OUT, "material_resolution.json"), "w"), indent=1)
open(os.path.join(OUT, "material_census.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:8000])

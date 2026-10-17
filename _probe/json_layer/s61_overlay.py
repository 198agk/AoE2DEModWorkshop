import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
POM = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def rd(p):
    return open(p, "rb").read().decode("utf-8-sig", "ignore")

w("=== OVERRIDE MECHANISM PROBE: Pompeii stubs vs base ===")
for f in ("linkedTechs.json", "sharedbuildings.json", "unitcategories.json", "AIConsts.json", "eras.json"):
    pb, pp = os.path.join(BASE, f), os.path.join(POM, f)
    w("")
    w("--- %s  base=%s B   pompeii=%s B ---" % (f,
        os.path.getsize(pb) if os.path.exists(pb) else "-",
        os.path.getsize(pp) if os.path.exists(pp) else "-"))
    if os.path.exists(pp) and os.path.getsize(pp) < 900:
        w("  POMPEII CONTENT: %s" % rd(pp).strip())
    elif os.path.exists(pp):
        t = rd(pp)
        try:
            j = json.loads(t)
            k = list(j.keys())
            w("  pompeii top keys=%s  n_first=%s" % (k, (len(j[k[0]]) if isinstance(j[k[0]], list) else "?")))
        except Exception as e:
            w("  (unparsable: %s)" % e)
        w("  pompeii first 300 chars: %s" % t[:300].replace("\n", " "))

w("")
w("=== is there a BASE morematerials.json? ===")
for p in (os.path.join(GAME, "widgetui", "morematerials.json"),
          os.path.join(GAME, "widgetui", "materials.json"),
          os.path.join(GAME, "modes", "Pompeii", "widgetui", "morematerials.json")):
    w("  %-72s exists=%s size=%s" % (os.path.relpath(p, GAME), os.path.exists(p),
        os.path.getsize(p) if os.path.exists(p) else "-"))

w("")
w("=== which non-Pompeii mode dirs exist & do any carry dat JSONs? ===")
md = os.path.join(GAME, "modes")
w("  modes = %s" % sorted(os.listdir(md)))

w("")
w("=== base vs Pompeii for EVERY in-scope json: is the pompeii file an increment (subset) or a full copy? ===")
for f in sorted(os.listdir(BASE)):
    if not f.endswith(".json") or f == "civTechTrees.json":
        continue
    pb, pp = os.path.join(BASE, f), os.path.join(POM, f)
    if not os.path.exists(pp):
        w("  %-42s base=%-9s pompeii=ABSENT" % (f, os.path.getsize(pb)))
        continue
    tb, tp = rd(pb), rd(pp)
    try:
        jb, jp = json.loads(tb), json.loads(tp)
        same_keys = (set(jb) == set(jp))
        if same_keys and len(jb) == 1:
            k = list(jb)[0]
            if isinstance(jb[k], list) and isinstance(jp[k], list):
                w("  %-42s base=%-9d pompeii=%-9d  %s: base_n=%-5d pom_n=%-5d  SUBSET=%s" % (
                    f, len(tb), len(tp), k, len(jb[k]), len(jp[k]),
                    {json.dumps(x, sort_keys=True) for x in jp[k]} <= {json.dumps(x, sort_keys=True) for x in jb[k]}))
                continue
        w("  %-42s base=%-9d pompeii=%-9d topkeys_same=%s" % (f, len(tb), len(tp), same_keys))
    except Exception as e:
        w("  %-42s base=%-9d pompeii=%-9d (diff parse: %s)" % (f, len(tb), len(tp), e))
open(os.path.join(OUT, "s61_overlay.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

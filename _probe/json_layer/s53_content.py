import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json
OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def load(n):
    return json.loads(open(os.path.join(BASE, n), "rb").read().decode("utf-8-sig"))

w("=" * 90); w("JJ. UNITLINES.json — does it encode what the .dat cannot?")
w("=" * 90)
u = load("unitlines.json")
w("  top keys = %s" % list(u.keys()))
w("  Hint = %r" % u.get("Hint"))
ul = u["UnitLines"]
w("  UnitLines n=%d" % len(ul))
w("  entry keys (union) = %s" % sorted({k for e in ul for k in e}))
for e in ul[:6]:
    w("    %s" % json.dumps(e, ensure_ascii=False))
w("  LineID range: min=%s max=%s" % (min(e.get("LineID") for e in ul), max(e.get("LineID") for e in ul)))
w("  IDChains total=%d, lengths=%s" % (sum(len(e.get("IDChain", [])) for e in ul),
    sorted({len(e.get("IDChain", [])) for e in ul})))

w(""); w("=" * 90); w("KK. DROPSITES.json")
w("=" * 90)
d = load("dropsites.json")
w("  top keys = %s n=%d" % (list(d.keys()), len(d["drop_site_list"])))
w("  entry keys (union) = %s" % sorted({k for e in d["drop_site_list"] for k in e}))
for e in d["drop_site_list"][:4]:
    w("    %s" % json.dumps(e, ensure_ascii=False))

w(""); w("=" * 90); w("LL. AIConsts.json + airesourcetypes.json")
w("=" * 90)
a = load("AIConsts.json")
w("  AIConsts top = %s" % list(a.keys()))
w("  DefConsts n=%d keys=%s" % (len(a["DefConsts"]), sorted({k for e in a["DefConsts"] for k in e})))
for e in a["DefConsts"][:5]: w("    %s" % json.dumps(e, ensure_ascii=False))
w("  Defines n=%d" % len(a["Defines"]))
for e in a["Defines"][:5]: w("    %s" % json.dumps(e, ensure_ascii=False))
r = load("airesourcetypes.json")
w("  airesourcetypes top = %s n=%d" % (list(r.keys()), len(r["ResourceTypes"])))
for e in r["ResourceTypes"]:
    w("    Resource=%-10s nTypes=%-3d first=%s" % (e["Resource"], len(e["Types"]), json.dumps(e["Types"][:3], ensure_ascii=False)))
w("  all types flat n=%d" % sum(len(e["Types"]) for e in r["ResourceTypes"]))
w("  type keys union = %s" % sorted({k for e in r["ResourceTypes"] for t in e["Types"] for k in t}))

w(""); w("=" * 90); w("MM. objreplacement / linkedUnits / sharedbuildings FULL")
w("=" * 90)
for n in ("objreplacement.json", "linkedUnits.json", "sharedbuildings.json", "unitcategories.json"):
    j = load(n)
    w("  --- %s ---" % n)
    w("  %s" % json.dumps(j, ensure_ascii=False, indent=1)[:2600])

w(""); w("=" * 90); w("NN. sounds.json FULL")
w("=" * 90)
s = load("sounds.json")
w("  top = %s n=%d keys-union=%s" % (list(s.keys()), len(s["sound_list"]),
    sorted({k for e in s["sound_list"] for k in e})))
for e in s["sound_list"]:
    w("    %s" % json.dumps(e, ensure_ascii=False))

open(os.path.join(OUT, "s53_content.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:6000])

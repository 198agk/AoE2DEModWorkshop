import json, os, io, collections

P = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\resources\_common\dat\civTechTrees.json"
out = io.StringIO()
def w(s=""):
    out.write(str(s) + "\n")

w("size=%d" % os.path.getsize(P))
raw = open(P, "rb").read()
w("first 300: %r" % raw[:300])
j = json.loads(raw.decode("utf-8-sig"))
w("top type=%s" % type(j).__name__)
if isinstance(j, dict):
    ks = list(j.keys())
    w("top keys n=%d: %s" % (len(ks), ks))
    k0 = ks[0]
    w("\nfirst key=%r value type=%s" % (k0, type(j[k0]).__name__))
    v = j[k0]
    if isinstance(v, dict):
        for kk, vv in v.items():
            w("   %-30s type=%s len=%s" % (kk, type(vv).__name__, len(vv) if hasattr(vv, '__len__') else '-'))
        # schema of first node
        for kk, vv in v.items():
            if isinstance(vv, list) and vv:
                w("\n   verbatim %s[0]:" % kk)
                w("   " + json.dumps(vv[0], ensure_ascii=False)[:600])
elif isinstance(j, list):
    w("list len=%d elem0 type=%s" % (len(j), type(j[0]).__name__))
    w(json.dumps(j[0], ensure_ascii=False)[:800])

# schema comparison with per-civ file
P2 = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\CivTechTrees\BRITONS.json"
j2 = json.loads(open(P2, "rb").read().decode("utf-8-sig"))
w("\n### per-civ BRITONS top keys: %s" % list(j2.keys()))

def keypaths(o, prefix="", acc=None, depth=0):
    if acc is None:
        acc = set()
    if depth > 4:
        return acc
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(prefix + "." + str(k))
            keypaths(v, prefix + "." + str(k), acc, depth + 1)
    elif isinstance(o, list) and o:
        keypaths(o[0], prefix + "[]", acc, depth + 1)
    return acc

k_mono = keypaths(j)
k_civ = keypaths(j2)
w("\n### monolithic distinct keypaths n=%d" % len(k_mono))
for k in sorted(k_mono):
    w("   %s" % k)
w("\n### per-civ distinct keypaths n=%d" % len(k_civ))
for k in sorted(k_civ):
    w("   %s" % k)
w("\n### mono-only: %s" % sorted(k_mono - k_civ))
w("### civ-only: %s" % sorted(k_civ - k_mono))

# does Pompeii monolithic have a BRITONS section identical to base per-civ file?
for cand in ["BRITONS", "Britons", "britons"]:
    if isinstance(j, dict) and cand in j:
        w("\n### found section %r in monolithic" % cand)
        a = j[cand]
        w("   type=%s keys=%s" % (type(a).__name__, list(a.keys()) if isinstance(a, dict) else None))
        if isinstance(a, dict) and "civ_techs_units" in a:
            w("   n buildings=%d n units=%d" % (len(a.get("civ_techs_buildings", [])), len(a.get("civ_techs_units", []))))
            w("   buildings identical to base per-civ? %s" % ([x.get("Building ID") for x in a.get("civ_techs_buildings", [])] == [x.get("Building ID") for x in j2.get("civ_techs_buildings", [])]))
            w("   units identical to base per-civ? %s" % ([x.get("Node ID") for x in a.get("civ_techs_units", [])] == [x.get("Node ID") for x in j2.get("civ_techs_units", [])]))
            w("   verbatim mono units[0]: %s" % json.dumps(a["civ_techs_units"][0], ensure_ascii=False))
            w("   verbatim civ units[0]:  %s" % json.dumps(j2["civ_techs_units"][0], ensure_ascii=False))

# Pompeii per-civ dir listing
PD = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\resources\_common\dat\CivTechTrees"
w("\n### Pompeii CivTechTrees dir:")
for f in sorted(os.listdir(PD)):
    w("   %-30s %8d" % (f, os.path.getsize(os.path.join(PD, f))))

open(r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer\s12_mono.txt", "w", encoding="utf-8").write(out.getvalue())
print(out.getvalue()[:9000])

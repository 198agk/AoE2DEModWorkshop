import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, sys
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
DAT = os.path.join(BASE, "empires2_x2_p1.dat")
import parse_dat as P
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(DAT)
p = P.Parser(data); st = p.parse()

w("=== .dat top-level stat keys ===")
w("  %s" % sorted(st.keys()))
for k in sorted(st.keys()):
    v = st[k]
    if isinstance(v, list):
        w("  %-28s list len=%d" % (k, len(v)))
    elif isinstance(v, dict):
        w("  %-28s dict keys=%s" % (k, list(v.keys())[:12]))
    else:
        w("  %-28s %r" % (k, v))

w("")
w("=== do the 7 unitcategories.json names exist as .dat unit classes? ===")
cats = ["Infantry", "Cavalry", "Archers", "CavalryArchers", "Monks", "Warboats", "SiegeWeapons"]
uc = st.get("unit_classes")
if isinstance(uc, list):
    names = [c.get("name") if isinstance(c, dict) else str(c) for c in uc]
    w("  unit_classes n=%d first 40 = %s" % (len(uc), names[:40]))
    for c in cats:
        w("    %-16s in .dat unit_classes: %s" % (c, c in names))
else:
    w("  no unit_classes list exposed; st['unit_classes']=%r" % (uc,))

w("")
w("=== does .dat express a per-unit -> class membership? (first unit records) ===")
civs = getattr(p, "first_units", None)
w("  p.first_units len=%s" % (len(civs) if civs else civs))
if civs:
    for u in civs[:5]:
        w("    %s" % json.dumps({k: u[k] for k in list(u)[:14]}, ensure_ascii=False)[:400])

w("")
w("=== dropsites object_group / attribute_type vs .dat resource ids ===")
ds = json.loads(open(os.path.join(BASE, "dropsites.json"), "rb").read().decode("utf-8-sig"))
ogroups, attrs, rt = set(), set(), set()
for e in ds["drop_site_list"]:
    for t in e.get("target_list", []):
        if "object_group" in t: ogroups.add(t["object_group"])
        if "attribute_type" in t: attrs.add(t["attribute_type"])
    for t in e.get("update_ai_resource_types", []):
        rt.add(t["resource_type"])
w("  object_group values = %s" % sorted(ogroups))
w("  attribute_type values = %s" % sorted(attrs))
w("  resource_type values = %s" % sorted(rt))
res = st.get("resources")
w("  .dat st['resources'] = " + repr((type(res), (len(res) if isinstance(res, list) else res))))

w("")
w("=== airesourcetypes: are its 47 IDs .dat TERRAIN/unit/tree ids? ===")
ars = json.loads(open(os.path.join(BASE, "airesourcetypes.json"), "rb").read().decode("utf-8-sig"))
ids = [(e["Resource"], t["Name"], t["ID"]) for e in ars["ResourceTypes"] for t in e["Types"]]
w("  n=%d  sample=%s" % (len(ids), ids[:10]))
allids = set(st.get("terrain_restriction") or [])
w("  st keys with 'terrain': %s" % [k for k in st if "terrain" in k])
open(os.path.join(OUT, "s57_datclasses.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

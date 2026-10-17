import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, io, json
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

src = open(_HERE_PATH("_probe", "datparse", "parse_dat.py"), encoding="utf-8").read()
i = src.find("def read_civ("); j = src.find("\ndef ", i + 5)
w("=" * 70); w(src[i:j]); w("=" * 70)

w("BASE DIR LISTING (json)")
for fn in sorted(os.listdir(BASE)):
    if fn.lower().endswith(".json") or fn.lower().endswith(".pbin"):
        st = os.stat(os.path.join(BASE, fn))
        import datetime
        w("  %-42s %10d  %s" % (fn, st.st_size, datetime.datetime.fromtimestamp(st.st_mtime)))
w("  subdirs: %s" % [d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))])
w("  civTechTrees.json exists in base? %s" % os.path.exists(os.path.join(BASE, "civTechTrees.json")))

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data)
st = p.parse()
civs = st["civs"]
# map civ name -> units
w("\nread_civ result keys: %s" % list(civs[0].keys()))
brit = [c for c in civs if c["name"] == "British"][0]
azt = [c for c in civs if c["name"] == "Aztecs"][0]
w("British units len=%d, first record keys=%s" % (len(brit["units"]), list(brit["units"][0].keys())))
w("sample unit records:")
for u in brit["units"][:3]:
    w("   %s" % json.dumps(u, ensure_ascii=False)[:400])

def idset(c):
    return set(u["id"] for u in c["units"] if u.get("id"))
w("\nBritish ids=%d unique, Aztecs ids=%d unique" % (len(idset(brit)), len(idset(azt))))

# unit header table
w("\nunit_header_count=%d; sample headers:" % len(st["unit_headers"]))
from collections import Counter
wc = Counter(len(h.get("tasks", [])) for h in st["unit_headers"])
w("  header task-count distribution: %s" % dict(list(wc.items())[:12]))

# enabled flags
en_b = [u for u in brit["units"] if u.get("id")]
w("\nBritish: units with id>0: %d" % len(en_b))

open(os.path.join(OUT, "s24_civunits.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:6000])

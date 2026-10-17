"""TIE-BREAKER.  Three questions:

1. Does the British per-civ .dat unit list actually CONTAIN 2550?  (If not, no
   tree edit can ever add the button, and the A half is dead on arrival.)
   Compare against Incas.
2. The 6 unconditional tree rows absent from the cache -- are those units
   listed by the cache at some OTHER building (staleness), or nowhere?
3. Is building 1806 / 2172 a real train building in the .dat?
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
from aoe2mod.dat import parser as P, locate

data, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(data)
p.parse()
civs = locate.locate(data, parser=p)[0]
by_name = {c["name"]: c for c in civs}
print("civs:", len(by_name))
print("names sample:", sorted(by_name)[:12])

print("\n=== Q1. per-civ .dat unit LIST ownership ===")
for civname in ("British", "Incas", "Goths", "Byzantine", "Aztecs"):
    c = by_name.get(civname)
    if not c:
        cand = [k for k in by_name if civname.lower() in k.lower()]
        print("   %-10s NOT FOUND; candidates=%s" % (civname, cand))
        continue
    ids = {u["id"] for u in c.get("units", [])}
    print("   %-10s unit_pointers_total=%-6s len(units)=%-6d has2550=%-6s has74=%-6s has759=%-6s has8(Longbow)=%s"
          % (civname, c.get("unit_pointers_total"), len(c.get("units", [])),
             2550 in ids, 74 in ids, 759 in ids, 8 in ids))

print("\n=== Q2. the 6 unconditional cache omissions, cross-checked ===")
caches = {}
for nm in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    caches[nm] = json.load(open(os.path.join(DAT, nm), encoding="utf-8-sig"))
CASES = [("Armenians", 1806, 125, "Monk"), ("Armenians", 1806, 1811, "Warrior Priest"),
         ("Georgians", 49, 588, "Siege Onager"), ("Georgians", 1806, 125, "Monk"),
         ("Sicilians", 49, 588, "Siege Onager"), ("Spartans", 2172, 13, "Fishing Ship")]
for civ, bid, uid, nm in CASES:
    where = []
    for cname, obj in caches.items():
        for k, v in obj.items():
            if k != civ:
                continue
            for b in v.get("Buildings", []):
                for e in b.get("Units", []):
                    if e["ID"] == uid:
                        where.append((cname, b["ID"], b.get("Name"), e.get("RequiredAge")))
    # .dat train hosts for that unit, for that civ
    c = by_name.get(civ) or by_name.get({"Spartans": "Spartans"}.get(civ))
    hosts = "?"
    if c:
        cands = [u for u in c["units"] if u["id"] == uid]
        if cands:
            hosts = sorted({tl["unit_id"] for tl in cands[0].get("train_locations", [])})
    print("   %-10s bldg=%-5s uid=%-5s %-16s cache-says=%-42s .dat-hosts=%s"
          % (civ, bid, uid, nm, where if where else "NOWHERE in that civ's cache", hosts))

print("\n=== Q3. is 1806 / 2172 a train building in the .dat? ===")
for bid in (1806, 2172, 49, 12):
    hits = locate.find_units(civs, bid)
    nm = hits[0][2].get("name") if hits else "?"
    hosts = sorted({tl["unit_id"] for tl in hits[0][2].get("train_locations", [])}) if hits else None
    print("   building %-5s datname=%-18s records=%-3s its own train hosts=%s"
          % (bid, nm, len(hits), hosts))
print("\nDONE")

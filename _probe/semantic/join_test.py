# -*- coding: utf-8 -*-
"""Test whether the JSON semantic sources join cleanly to dat unit/tech ids."""
import json
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
import os
import sys
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = GP.DAT_DIR

units = json.load(open(os.path.join(HERE, "unit_names.json"), encoding="utf-8"))
techs = json.load(open(os.path.join(HERE, "tech_names.json"), encoding="utf-8"))
dat_unit_ids = {int(k) for k in units}
print("dat distinct unit ids: %d" % len(dat_unit_ids))

def load(n):
    return json.load(open(os.path.join(BASE, n), encoding="utf-8"))

# ---- futuravailableunits.json -----------------------------------------
fau = load("futuravailableunits.json")
civs = list(fau.keys())
print()
print("futuravailableunits.json civs: %d -> %s" % (len(civs), civs[:8]))
b = fau.get("Britons", {}).get("Buildings", [])
print("  Britons buildings: %d ; first: %s" % (len(b), b[0] if b else None))
ids = set()
for civ, v in fau.items():
    for bl in v.get("Buildings", []):
        ids.add(bl.get("ID"))
        for un in bl.get("Units", []):
            ids.add(un.get("ID"))
ids.discard(None)
print("  distinct IDs referenced: %d" % len(ids))
print("  of which present in dat unit ids: %d (%.1f%%)"
      % (len(ids & dat_unit_ids), 100.0 * len(ids & dat_unit_ids) / max(1, len(ids))))
print("  referenced but NOT a dat unit id (sample): %s"
      % sorted(ids - dat_unit_ids)[:15])

# ---- CivTechTrees ------------------------------------------------------
CT = os.path.join(BASE, "CivTechTrees")
files = sorted(os.listdir(CT))
namematch = 0
total = 0
node_ids = set()
for fn in files:
    d = load(os.path.join(CT, fn))
    for key in ("civ_techs_buildings", "civ_techs_units"):
        for node in d.get(key, []):
            total += 1
            nid = node.get("Node ID")
            if isinstance(nid, int):
                node_ids.add(nid)
            nsid = node.get("Name String ID")
            name = node.get("Name")
            if isinstance(nid, int) and str(nid) in units:
                total and None
                if units[str(nid)]["en"] == name:
                    namematch += 1
print()
print("CivTechTrees: %d files, %d nodes" % (len(files), total))
print("  distinct Node ID: %d ; present in dat unit ids: %d"
      % (len(node_ids), len(node_ids & dat_unit_ids)))
print("  nodes whose json Name == our resolved env name: %d" % namematch)

# ---- civilizations.json ------------------------------------------------
civ = load("civilizations.json")["civilization_list"]
print()
print("civilizations.json entries: %d" % len(civ))
print("  keys: %s" % list(civ[0].keys()))
sys.path.insert(0, HERE)
from strings_db import load_language  # noqa: E402
en, _ = load_language("en")
ok = 0
for c in civ:
    sid = c.get("name_string_id")
    if sid in en:
        ok += 1
print("  name_string_id resolvable in en strings: %d / %d" % (ok, len(civ)))
print("  civ order in file: %s" % [c["internal_name"] for c in civ][:10])
dat_civs = ["Gaia", "British", "French", "Goths", "Teutons", "Japanese", "Chinese"]
print("  dat civ order:     %s" % dat_civs)
print("  NOTE dat uses 'British'/'French' but civilizations.json uses %r/%r"
      % (civ[1]["internal_name"], civ[2]["internal_name"]))

# ---- other tables ------------------------------------------------------
for name, key in (("linkedTechs.json", "LinkedTechs"),
                  ("linkedUnits.json", "Data"),
                  ("dropsites.json", "drop_site_list"),
                  ("sharedbuildings.json", "Data"),
                  ("objreplacement.json", "objects"),
                  ("buttons.json", "command_button_list"),
                  ("sounds.json", "sound_list")):
    d = load(name)
    v = d.get(key)
    n = len(v) if isinstance(v, list) else len(d)
    sk = list(v[0].keys()) if isinstance(v, list) and v else list(d.keys())[:6]
    print()
    print("%-26s %-22s entries=%-5s keys=%s" % (name, key, n, sk))

# unitlines / unitcategories / eras
ul = load("unitlines.json")
print()
print("unitlines.json keys: %s" % list(ul.keys()))
print("  UnitLines: %s" % json.dumps(ul.get("UnitLines"), ensure_ascii=False)[:500])
uc = load("unitcategories.json")
print()
print("unitcategories.json: %s" % {k: len(v) for k, v in uc.items()})
er = load("eras.json")
print()
print("eras.json: %s" % json.dumps(er, ensure_ascii=False)[:600])

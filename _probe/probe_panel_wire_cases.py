"""Panel-half behaviour in the cases that exercise it.

Two shapes matter:
  * the shipped disagreement -- the tree says NotAvailable while the panel
    already lists it (11 such pairs), which is the honest no-op path;
  * a revoke, where the entry must actually come out;
  * the tech space, where the panel has its own `Techs` arrays.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
OUT = os.path.join(HERE, "out_panelwire2")
trees = tk._trees()


def show(tag, path):
    rels = sorted(os.path.relpath(os.path.join(r, n), path).replace(os.sep, "/")
                  for r, _d, ns in os.walk(path) for n in ns)
    print("%s files: %s" % (tag, rels))


# --- 1. the shipped disagreement: tree says no, panel already lists it ------
print("=== tree NotAvailable + panel lists it (ARMENIANS 569 Paladin) ===")
_row = CT.row_for(trees["ARMENIANS"], 569, CT.UNIT_USE_TYPES)
print("tree row:", {k: _row.get(k) for k in ("Node ID", "Node Status",
                                             "Building ID", "Age ID")})
_p = os.path.join(OUT, "disagree")
man = tk.build({"intent": "unit.availability", "unit": 569,
                "civ": "Armenians", "action": "grant"},
               _p, title="t", author="aoe2mod", overwrite=True)
print("panel:", {k: man["panel"].get(k) for k in
                 ("ok", "mode", "panel_name", "reason")})
show("", _p)

# --- 2. revoke something the panel really lists -----------------------------
print()
print("=== revoke: Vikings Berserk (692) ===")
_r2 = CT.row_for(trees["VIKINGS"], 692, CT.UNIT_USE_TYPES)
print("tree row:", {k: _r2.get(k) for k in ("Node ID", "Node Status",
                                            "Building ID", "Age ID")})
_p2 = os.path.join(OUT, "revoke")
man2 = tk.build({"intent": "unit.availability", "unit": 692,
                 "civ": "Vikings", "action": "revoke"},
                _p2, title="t", author="aoe2mod", overwrite=True)
print("panel:", {k: man2["panel"].get(k) for k in
                 ("ok", "mode", "panel_name", "removed", "before_entries",
                  "after_entries")})
show("", _p2)

# --- 3. the tech space ------------------------------------------------------
print()
print("=== tech space: does a tech ROW carry a Building ID? ===")
for _civ, _tid in (("GOTHS", 3), ("BRITONS", 22), ("VIKINGS", 2)):
    _r = CT.row_for(trees[_civ], _tid, CT.TECH_USE_TYPES)
    print("  %-8s tech %-4s row=%s" % (_civ, _tid,
          None if _r is None else {k: _r.get(k) for k in
                                   ("Node ID", "Building ID", "Age ID")}))

print()
print("=== what does the panel's Techs array hold? ===")
_panels = BP.load_all(tk.game_root)
_txt, _obj = BP.load_panel(BP.panel_paths(tk.game_root)[0])
_civ = BP.civ_key_for(_panels, "Britons")
for _b in BP.buildings(_obj, _civ)[:6]:
    _bid = _b.get("ID")
    _t = BP.entries(_obj, _civ, _bid, BP.TECHS_KEY)
    if _t:
        print("  building %-4s Techs: %s" % (_bid, [e.get("ID") for e in _t]))

# --- 4. tech space where the receiver has NO row -> donor fallback ----------
print()
print("=== tech grant to a civ with no row: Goths gets Yeomen (3) ===")
_p4 = os.path.join(OUT, "tech")
man4 = tk.build({"intent": "tech.availability", "tech": 3, "civ": "Goths",
                 "action": "grant"},
                _p4, title="t", author="aoe2mod", overwrite=True)
print("panel:", {k: man4["panel"].get(k) for k in
                 ("ok", "mode", "panel_name", "donor", "entry",
                  "building_from", "reason")})
show("", _p4)

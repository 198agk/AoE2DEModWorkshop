"""Does a build write BOTH halves of an availability edit?

This is the API-level contract, asserted from emitted files rather than from the
report, because the report and the disk have disagreed before in this project.

The tree file alone is not an availability edit: 2026-10-14 showed a tree rewrite
loading in a mod and changing nothing in the menu.  The menu is fed by a
*pre-baked* panel file, so the product must ship both.  Four shapes are pinned,
and each one is a way the product could look like it worked while shipping the
wrong thing:

  1. the panel ALREADY lists the node -> no panel file at all (the honest no-op);
  2. the panel lacks it -> a synthesised entry, under the receiver's own
     `Building ID`, with a donor recorded;
  3. a revoke -> one entry out;
  4. a tech whose receiver has NO tree row -> the building comes from the donor
     row, and the report says which civ it came from.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
trees = tk._trees()
ROOT_OUT = tempfile.mkdtemp(prefix="aoe2mod panel wire ")
checks = 0


def _check(cond, msg):
    global checks
    assert cond, msg
    checks += 1


def _files(path):
    return sorted(os.path.relpath(os.path.join(r, n), path).replace(os.sep, "/")
                  for r, _d, ns in os.walk(path) for n in ns)


def _panel_of(path, which="futuravailableunits.json"):
    return BP.load_panel(os.path.join(path, "resources", "_common", "dat",
                                      which))


try:
    # --- 1. the shipped disagreement: the tree says no and the panel says yes --
    # Measured, not chosen: `_probe/probe_shipped_disagreement.py` finds 11 such
    # pairs, and this is one of them.
    row = CT.row_for(trees["ARMENIANS"], 569, CT.UNIT_USE_TYPES)
    _check(row is not None and row["Node Status"] == "NotAvailable",
           "the subject is not the shipped disagreement: %r" % (row,))
    p1 = os.path.join(ROOT_OUT, "noop")
    m1 = tk.build({"intent": "unit.availability", "unit": 569,
                   "civ": "Armenians", "action": "grant"},
                  p1, title="t", author="aoe2mod test")
    _check(m1["panel"]["ok"] is True, m1["panel"])
    _check(m1["panel"]["mode"] == "none", m1["panel"])
    f1 = _files(p1)
    _check(not any("futuravailableunits" in f for f in f1),
           "the no-op shipped the panel file anyway: %s" % f1)
    _check(any("CivTechTrees" in f for f in f1), f1)
    # The report must not claim it wrote a file it did not write.
    _check(not any("build-panel entry was written" in s
                   for s in m1["verification"]["proven"]),
           m1["verification"]["proven"])

    # --- 2. the panel lacks it: synthesise from a measured donor ------------
    p2 = os.path.join(ROOT_OUT, "add")
    m2 = tk.build({"intent": "unit.availability", "unit": 5,
                   "civ": "British", "action": "grant"},
                  p2, title="t", author="aoe2mod test")
    _check(m2["panel"]["mode"] == "add_entry", m2["panel"])
    _check((m2["panel"]["before_entries"], m2["panel"]["after_entries"])
           == (0, 1), m2["panel"])
    _check(m2["panel"]["donor"], "no donor recorded: %s" % m2["panel"])
    bldg = CT.row_for(trees["BRITONS"], 5, CT.UNIT_USE_TYPES)["Building ID"]
    txt2, obj2 = _panel_of(p2)
    _check(BP.has_entry(obj2, "Britons", bldg, 5, BP.UNITS_KEY),
           "the emitted panel does not list the unit under building %r" % bldg)
    # The age must come from the RECEIVER's row, or the menu gates it wrongly.
    _check(m2["panel"]["entry"]["RequiredAge"]
           == CT.row_for(trees["BRITONS"], 5, CT.UNIT_USE_TYPES)["Age ID"],
           m2["panel"]["entry"])
    # Surgical: every civilization other than Britons keeps the shipped bytes.
    shipped_txt, _ = BP.load_panel(os.path.join(tk.game_root, BP.PANEL_REL))
    ok_s, info = BP.verify_surgical(shipped_txt, txt2)
    _check(ok_s is True, info)
    _check(info["kind"] == "insert" and info["outside_is_untouched"] is True,
           info)

    # --- 3. a revoke actually removes one -----------------------------------
    p3 = os.path.join(ROOT_OUT, "revoke")
    m3 = tk.build({"intent": "unit.availability", "unit": 692,
                   "civ": "Vikings", "action": "revoke"},
                  p3, title="t", author="aoe2mod test")
    _check(m3["panel"]["mode"] == "remove_entry", m3["panel"])
    _check(m3["panel"]["removed"] == 1, m3["panel"])
    _check((m3["panel"]["before_entries"], m3["panel"]["after_entries"])
           == (1, 0), m3["panel"])
    _txt3, obj3 = _panel_of(p3)
    _check(not BP.has_entry(obj3, "Vikings", 82, 692, BP.UNITS_KEY),
           "the revoked unit is still in the emitted panel")

    # --- 4. the tech space, receiver has no row ------------------------------
    _check(CT.row_for(trees["GOTHS"], 3, CT.TECH_USE_TYPES) is None,
           "Goths unexpectedly has a Yeomen row; pick another subject")
    p4 = os.path.join(ROOT_OUT, "tech")
    m4 = tk.build({"intent": "tech.availability", "tech": 3, "civ": "Goths",
                   "action": "grant"},
                  p4, title="t", author="aoe2mod test")
    _check(m4["space"] == "Tech", m4)
    _check(m4["panel"]["mode"] == "add_entry", m4["panel"])
    donor_civ, donor_row = CT.donor_row(trees, 3, CT.TECH_USE_TYPES)
    _check(m4["panel"]["building_from"] == donor_civ, m4["panel"])
    _check(m4["panel"]["donor"] == donor_civ.strip().capitalize()
           or m4["panel"]["donor"] == donor_civ, m4["panel"])
    _txt4, obj4 = _panel_of(p4)
    _check(BP.has_entry(obj4, "Goths", donor_row["Building ID"], 3,
                        BP.TECHS_KEY),
           "the granted technology is not in the panel's Techs array")
    _check(BP.count_entries(obj4, "Goths", 3, BP.TECHS_KEY) == 1,
           "the technology entry is duplicated in the emitted panel")

    # --- the tree half must be there in every case above --------------------
    for _path, _key in ((p1, "ARMENIANS"), (p2, "BRITONS"),
                        (p3, "VIKINGS"), (p4, "GOTHS")):
        _check(any(f.endswith("CivTechTrees/%s.json" % _key) for f in
                   _files(_path)),
               "%s shipped no tree file" % _path)
finally:
    shutil.rmtree(ROOT_OUT, ignore_errors=True)

print("%d checks passed" % checks)
print("PANEL WIRE PIN: an availability build writes the tree AND the pre-baked "
      "panel, and a panel no-op is reported rather than shipped.")
print("ANSWERED SINCE (2026-10-19): the running game reads the panel file for")
print("SOME screen -- but not for the build menu, which is excluded in both")
print("directions (Sicilians panel-silent-but-offered / Poles")
print("panel-listed-but-not-offered).  It most likely feeds the greyed-out")
print("future-items view.  What this file pins -- that the build WRITES both")
print("files and reports a panel no-op instead of shipping one -- is unaffected.")

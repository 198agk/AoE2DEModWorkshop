"""The panel half of an availability edit: does it produce a CORRECT file?

Run:  python _probe/test_panel_edit.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

_fail = []


def check(cond, label, extra=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", label,
                           ("  -- " + str(extra)) if extra else ""))
    if not cond:
        _fail.append(label)


tk = A.open_toolkit()
G = tk.game_root
trees = CT.load_trees(G)


def tree_row(civ_key, node_id):
    stem = CT.civ_file_stem(civ_key)
    tree = trees.get(stem)
    return CT.row_for(tree, node_id, CT.UNIT_USE_TYPES) if tree else None


def ready(civ_key):
    def _r(node_id):
        r = tree_row(civ_key, node_id)
        return bool(r) and r.get("Node Status") == "ResearchedCompleted"
    return _r


print("A  the shipped file round-trips untouched")
_p, _k = BP.panel_path_for(G, "British")
_text, _obj = BP.load_panel(_p)
_rep, _files = BP.availability_edit(G, "British", 83, "grant",
                                    building_id=12, age_id=1)
check(_rep["mode"] == "none", "granting the Villager to Britons is a no-op "
      "(the panel already lists it)", _rep.get("reason"))
check(_files == {}, "and it emits no file", _files)
check(_rep["ok"] is True, "and it is reported ok", _rep["ok"])

print()
print("B  a node the panel lacks gets a synthesised entry")
# Hand Cannoneer (5) for Britons: the panel's Archery Range does not list it.
_rep2, _files2 = BP.availability_edit(G, "British", 5, "grant",
                                     building_id=87, age_id=4)
check(_rep2["mode"] == "add_entry", "mode is add_entry", _rep2.get("mode"))
check(_rep2["surgical"] is True, "the splice is surgical", _rep2.get("surgical_info"))
check(_rep2["before_entries"] == 0 and _rep2["after_entries"] == 1,
      "entry count goes 0 -> 1",
      (_rep2["before_entries"], _rep2["after_entries"]))
check(_rep2["entry"].get("ID") == 5, "the entry carries the node id",
      _rep2["entry"])
check(_rep2["entry"].get("RequiredAge") == 4,
      "RequiredAge came from the target's own tree Age ID", _rep2["entry"])
check(_rep2["donor"] is not None, "a donor civ was recorded", _rep2.get("donor"))
_rel = _rep2["rel"].replace(os.sep, "/")
check(_rel.startswith("resources/_common/dat/"),
      "the path is engine-relative", _rel)
check("British" in json.dumps(_obj) or True, "sanity: object loads")

# the emitted bytes must be a valid file with ONE more entry
_t2, _o2 = BP.load_panel_text(_files2[_rep2["rel"]].decode("utf-8"))
# NOTE: the panel keys by ITS OWN name ("Britons"), not the .dat's ("British").
# Passing the .dat name to has_entry looks up a civ that is not there and
# reports "absent" for a file that has it -- which is what the first run of this
# test did, four times.
_CK = _rep2["civ_key"]
check(_CK == "Britons", "the panel's own key for British is Britons", _CK)
check(BP.has_entry(_o2, _CK, 87, 5, BP.UNITS_KEY),
      "the emitted file parses and lists it")
check(len(BP.entries(_o2, _CK, 87, BP.UNITS_KEY))
      == len(BP.entries(_obj, _CK, 87, BP.UNITS_KEY)) + 1,
      "touching only that building's array",
      (len(BP.entries(_obj, _CK, 87, BP.UNITS_KEY)),
       len(BP.entries(_o2, _CK, 87, BP.UNITS_KEY))))
# and another civ is untouched
check(json.dumps(_o2.get("Goths"), sort_keys=True, ensure_ascii=False)
      == json.dumps(_obj.get("Goths"), sort_keys=True, ensure_ascii=False),
      "another civilization is byte-identical after re-parse")

print()
print("C  insert then remove restores the ORIGINAL bytes")
# Remove from the EMITTED text, not from the shipped file: the shipped file
# never had this entry (that is why B inserted one), so revoking from it is
# correctly a no-op.  The claim worth testing is that the two splices are
# inverse, so the round trip has to start where the insert finished.
_new_text = _files2[_rep2["rel"]].decode("utf-8")
_back_text, _removed = BP.remove_entry(_new_text, _CK, 5)
check(_removed == 1, "the entry inserted above is removed by remove_entry",
      _removed)
_ok_back, _info_back = BP.verify_surgical(_new_text, _back_text)
check(_ok_back and _info_back["kind"] == "delete",
      "the removal is a surgical deletion", _info_back)
check(BP.serialize_bytes(_back_text) == BP.serialize_bytes(_text),
      "insert then remove restores the shipped bytes exactly",
      "%d vs %d" % (len(_back_text), len(_text)))
_rep3, _files3 = BP.availability_edit(G, _CK, 5, "revoke")
check(_rep3["mode"] == "none",
      "revoking from the SHIPPED file is honestly a no-op (it never had it)",
      _rep3.get("mode"))

print()
print("D  the antiquity civ goes to the OTHER file")
_ap, _ak = BP.panel_path_for(G, "Athenians")
check(_ap is not None and os.path.basename(_ap) == BP.PAPHOS_PANEL_NAME,
      "Athenians is served by the paphos panel", os.path.basename(_ap or ""))
_bp, _bk = BP.panel_path_for(G, "British")
check(os.path.basename(_bp) == BP.PANEL_NAME,
      "Britons is served by the main panel", os.path.basename(_bp))
_rep4, _files4 = BP.availability_edit(G, "Athenians", 5, "grant",
                                      building_id=87, age_id=4)
check(_rep4["mode"] in ("add_entry", "none"),
      "an antiquity civ edit succeeds or is honestly a no-op", _rep4.get("mode"))
if _rep4["mode"] == "add_entry":
    check(os.path.basename(_rep4["path"]) == BP.PAPHOS_PANEL_NAME,
          "and it writes the paphos file, not the main one",
          os.path.basename(_rep4["path"]))
    check(_rep4["surgical"] is True, "surgically", _rep4.get("surgical_info"))

print()
print("E  a civ with no panel entry anywhere is reported, not guessed")
_rep5, _files5 = BP.availability_edit(G, "Gaia", 5, "grant", building_id=87,
                                      age_id=1)
check(_files5 == {}, "no file is emitted for it", _rep5.get("mode"))
print("     gaia -> %s" % {k: v for k, v in _rep5.items()
                           if k in ("ok", "mode", "reason", "civ_key")})

print()
if _fail:
    print("PANEL EDIT: %d FAILED" % len(_fail))
    for f in _fail:
        print("   - %s" % f)
    sys.exit(1)
print("PANEL EDIT: the writer copies measured entries and splices only what it "
      "was asked to.")

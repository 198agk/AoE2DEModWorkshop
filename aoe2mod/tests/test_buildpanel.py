"""The build-panel cache writer: `aoe2mod/game/buildpanel.py`.

Three things have to hold before anything else may write this file:

  1. a no-op edit returns the file BYTE-FOR-BYTE (the file is not canonical
     JSON, so any re-serialise would rewrite ~983 KB nobody asked about);
  2. a real insertion changes ONLY the inserted characters and leaves a file the
     game can still parse;
  3. a removal does the same, and removing something absent is a no-op rather
     than an error.

Plus the shape facts the module's docstring asserts, kept as assertions here so
a data update cannot quietly invalidate the layer.

Run:  python aoe2mod/tests/test_buildpanel.py
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def main():
    tk = A.open_toolkit()
    text, obj = BP.load_panel(os.path.join(tk.game_root, BP.PANEL_REL))
    raw = open(os.path.join(tk.game_root, BP.PANEL_REL), "rb").read()

    print("panel cache: %d chars, %d civs, parses: %s"
          % (len(text), len(obj), isinstance(obj, dict)))
    print()

    print("A  it round-trips untouched")
    check(BP.serialize_bytes(text) == raw,
          "load + serialize returns the original bytes exactly")

    print()
    print("B  a no-op insertion check is byte-exact (the invariant)")
    ok, info = BP.verify_surgical(text, text)
    check(ok and info["inserted"] == 0,
          "verify_surgical accepts an unchanged text", json.dumps(info))

    print()
    print("C  insertion: only the inserted characters move")
    key = "Britons"
    node = 5
    bldg = 87
    check(not BP.has_entry(obj, key, bldg, node, BP.UNITS_KEY),
          "%s Archery Range does not already list Hand Cannoneer" % key)
    entry = {"ID": node, "Name": "Hand Cannoneer", "RequiredAge": 3}
    after = BP.insert_entry(text, key, bldg, entry)
    obj2 = json.loads(after)
    check(BP.has_entry(obj2, key, bldg, node, BP.UNITS_KEY),
          "the unit is in the new text")
    ok, info = BP.verify_surgical(text, after)
    check(ok and info["inserted"] > 0,
          "everything outside one contiguous insertion is unchanged",
          "inserted %d chars" % info["inserted"])
    # and the count is exactly one entry's worth
    n0 = len(BP.entries(obj, key, bldg, BP.UNITS_KEY))
    n1 = len(BP.entries(obj2, key, bldg, BP.UNITS_KEY))
    check(n1 == n0 + 1, "exactly one entry was added", "%d -> %d" % (n0, n1))
    # unrelated bytes: the previous civ and the next civ must be untouched
    added = after[info["common_prefix"]:len(after) - info["common_suffix"]]
    check(after.count("\r\n") - text.count("\r\n") == added.count("\r\n"),
          "every added line break lies inside the inserted region",
          "+%d lines, %d inside" % (after.count("\r\n") - text.count("\r\n"),
                                    added.count("\r\n")))
    check(BP.has_entry(obj2, "Bulgarians", bldg, 74, BP.UNITS_KEY)
          == BP.has_entry(obj, "Bulgarians", bldg, 74, BP.UNITS_KEY),
          "another civ's content is unaffected")

    print()
    print("D  inserting a duplicate is refused, not silently doubled")
    raised = False
    try:
        BP.insert_entry(after, key, bldg, entry)
    except BP.PanelError as e:
        raised = True
        print("     refused: %s" % str(e)[:70])
    check(raised, "a second identical insert raises PanelError")

    print()
    print("E  removal is surgical, and removing nothing is a no-op")
    back, removed = BP.remove_entry(after, key, node, BP.UNITS_KEY)
    check(removed == 1, "one entry removed", "%d" % removed)
    check(json.loads(back) == obj,
          "and the result parses equal to the original object")
    ok, info = BP.verify_surgical(after, back)
    check(ok and info["kind"] == "delete",
          "removal also moved only a contiguous region", json.dumps(info))
    cut = info["common_suffix"]
    gone = after[info["common_prefix"]:len(after) - cut] if cut else \
        after[info["common_prefix"]:]
    check('"ID": %d' % node in gone and len(gone) < 200,
          "the deleted region is exactly the entry that was removed",
          "%d chars: %r" % (len(gone), gone))
    check(len(after) - len(back) == -info["inserted"],
          "the net change accounts for every character that moved",
          "%d -> %d" % (len(after), len(back)))
    again, removed2 = BP.remove_entry(back, key, node, BP.UNITS_KEY)
    check(removed2 == 0 and again == back,
          "removing something absent changes nothing")

    print()
    print("E2 insert then remove is the identity (this is what found the bug)")
    again2 = BP.insert_entry(text, key, bldg, entry)
    back2, _n2 = BP.remove_entry(again2, key, node, BP.UNITS_KEY)
    check(again2 == after,
          "inserting the same entry twice gives the same text")
    check(back2 == text,
          "insert followed by remove restores the ORIGINAL bytes",
          "%d -> %d -> %d" % (len(text), len(again2), len(back2)))

    print()
    print("F  the shape facts the docstring asserts")
    tree = CT.load_trees(tk.game_root)
    panels = BP.load_all(tk.game_root)
    check(BP.civ_key_for(panels, "Magyars") == "Magyars"
          or BP.civ_key_for(panels, "Magyars") == "MAGYAR",
          "the civ bridge resolves Magyars",
          "%s" % BP.civ_key_for(panels, "Magyars"))
    check(BP.civ_key_for(panels, "Hindustanis") is not None,
          "and it resolves Hindustanis (IND.INDIANS in the tree)",
          "%s" % BP.civ_key_for(panels, "Hindustanis"))
    techs_any = False
    for k in list(obj)[:5]:
        for blk in BP.buildings(obj, k):
            if blk.get(BP.TECHS_KEY):
                techs_any = True
                break
    check(techs_any, "the file carries Techs lists (it is misnamed)")
    n_techs = sum(len(b.get(BP.TECHS_KEY) or [])
                  for k in obj for b in BP.buildings(obj, k))
    check(n_techs > 3000, "thousands of tech entries", "%d" % n_techs)

    print()
    print("G  the sibling covers the civs the main file omits")
    main_keys = {CT.civ_file_stem(k) for k in obj}
    all_keys = {CT.civ_file_stem(k) for k in panels}
    check(len(all_keys) > len(main_keys),
          "the union is larger than the main file alone",
          "%d -> %d" % (len(main_keys), len(all_keys)))
    check(all(k in all_keys for k in tree),
          "every tree file has a cache entry across the two files",
          "missing: %s" % sorted(k for k in tree if k not in all_keys))

    print()
    print("H  which file actually ships a civ (asked, not inferred)")
    # The two files share keys and are NOT copies: FullTechCiv differs.  A dict
    # merge would silently lose one of them, so the write path must ask which
    # file holds the key rather than trusting load order.
    amb = sorted(k for k, v in panels.items() if v.get("ambiguous"))
    check(amb, "some keys are defined by BOTH files (so a merge is lossy)",
          "%s" % amb)

    def _pairs(o, k):
        out = set()
        for b in BP.buildings(o, k):
            for u in (b.get(BP.UNITS_KEY) or []):
                out.add((b.get("ID"), u.get("ID")))
        return out

    shared_differ = 0
    for k in amb:
        sets = []
        for p in panels[k]["sources"]:
            _t, o = BP.load_panel(p)
            sets.append(_pairs(o, k))
        if len(set(map(frozenset, sets))) > 1:
            shared_differ += 1
    check(shared_differ > 0,
          "and at least one of those keys really differs between the files",
          "%d of %d" % (shared_differ, len(amb)))

    # the accessor the write path is supposed to use
    for _civ, _expect in (("Britons", "futuravailableunits.json"),
                          ("Achaemenids", "paphosfutureavailableunits.json"),
                          ("Spartans", "paphosfutureavailableunits.json"),
                          ("Magyars", "futuravailableunits.json")):
        _p, _k = BP.panel_path_for(tk.game_root, _civ)
        check(_p is not None and os.path.basename(_p) == _expect,
              "panel_path_for(%s) names the file that ships it" % _civ,
              "%s / %s" % (os.path.basename(_p) if _p else None, _k))

    # Cross-check the era prediction against what is actually on disk -- the
    # prediction is corroboration, the lookup is the fact.
    _ant = ("Achaemenids", "Athenians", "Macedonians", "Puru", "Spartans",
            "Thracians")
    _base = ("Britons", "Goths", "Turks", "Magyars", "Danes")
    check(all(os.path.basename(BP.panel_path_for(tk.game_root, c)[0])
              == "paphosfutureavailableunits.json" for c in _ant),
          "all six antiquity civs live in the paphos file", "")
    check(all(os.path.basename(BP.panel_path_for(tk.game_root, c)[0])
              == "futuravailableunits.json" for c in _base),
          "and base-era civs live in the main file", "")

    print()
    if fails:
        print("BUILD-PANEL CACHE: %d FAILED -> %s" % (len(fails), fails))
        return 1
    print("BUILD-PANEL CACHE: the writer is surgical -- an edit moves only the "
          "characters it was asked to move.")
    print("ANSWERED 2026-10-19: the running game does NOT read this file for the")
    print("build menu.  It is excluded in BOTH directions by plain-game runs --")
    print("Sicilians (panel silent, the game still offered the unit) and Poles")
    print("(panel listed the unit AND its upgrade tech, the game offered neither).")
    print("What moves the menu is a `.dat` `type 2` Enable/Disable Unit command on")
    print("a tech the civ owns, last one to fire wins (v7 grant / v17 revoke).")
    print("The write is still correct and still made -- some other screen consumes")
    print("this file, most likely the greyed-out future-items view.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

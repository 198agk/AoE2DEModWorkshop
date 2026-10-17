"""Build the SECOND smoke mod: the decisive test of the build-panel gate.

The first in-game test (2026-10-14) shipped ONE mod with TWO halves and split
the verdict cleanly: the `.dat` edit took effect, the `CivTechTrees/<CIV>.json`
edit did not.  This mod removes the tree half entirely and edits the one
remaining candidate instead:

    resources/_common/dat/futuravailableunits.json

which lists, PER BUILDING, the units that building offers:

    {"Britons": {"Buildings": [{"ID": 12, "Name": "Barracks",
        "Units": [{"ID": 74, "Name": "Militia", "RequiredAge": 1}, ...]}]}}

It agrees with the tree layer on 99.45% of (civ, unit) pairs over the 55 civs
it covers (`_probe/probe_build_panel_gate.py`) -- and since the tree rewrite
changed nothing, this file is the best remaining explanation.

SINGLE VARIABLE: this mod carries NO `.dat` and NO `CivTechTrees` file.  The
only difference from the install is one inserted unit entry, so whatever the
user sees is attributable to this file alone.

WHY A SURGICAL BYTE EDIT RATHER THAN json.dump: the shipped file is NOT
reproducible by `json.dumps`.  It uses `indent=2` and CRLF, but 127 hunks differ
because the generator wrote run-together separators like `},      {` (15 of
them) and a few trailing spaces.  A `json.dump` round-trip therefore rewrites
thousands of bytes nobody asked to change -- exactly the "near-match is the most
dangerous" failure this project already paid for in `CivTechTrees`.  Instead we
insert the new entry's text between the last existing entry and the closing
bracket, leaving every other byte identical, then assert the file still parses
AND that the untouched regions are byte-identical.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.mod import emitter as E         # noqa: E402

FU_REL = "resources/_common/dat/futuravailableunits.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_smoke2")

# The one thing we change: put the Champi Scout (2550, an Incas/Mapuche/Muisca/
# Tupi Barracks unit) into the BRITONS Barracks (12).
CIV_KEY = "Britons"
BLDG_ID = 12
NEW_UNIT = 2550
NEW_NAME = "Champi Scout"
NEW_AGE = 1

# A second, independent change in the same file: the Hand Cannoneer (5) into the
# Britons Archery Range (87).  Two different target buildings makes it much
# harder to explain a positive result as "one lucky row".
CIV_KEY2 = "Britons"
BLDG_ID2 = 87
NEW_UNIT2 = 5
NEW_NAME2 = "Hand Cannoneer"
NEW_AGE2 = 3


def _units_span(txt, civ_key, bldg_id):
    """Return (open_idx, close_idx) of that building's Units array.

    NOTE the indent anchor.  A building id appears TWICE in this file: once as a
    top-level entry in a civ's `Buildings` list (indent 8, the entry that owns a
    `Units` array) and once INSIDE another building's `Units` list (indent 12,
    e.g. the Archery Range shows up as a producible item under `Builder`, with
    no `Units` key of its own).  A plain `txt.index('"ID": 87,')` finds the
    NESTED one first and then walks forward to some other building's array --
    which silently inserts the entry in the wrong place.  Anchoring on the
    8-space indent picks the entry that actually has the array.
    """
    cs = txt.index('"%s"' % civ_key)
    anchor = '\n        "ID": %d,' % bldg_id
    bi = txt.index(anchor, cs)
    ui = txt.index('"Units": [', bi)
    k = txt.index("[", ui)
    depth = 0
    j = k
    while True:
        if txt[j] == "[":
            depth += 1
        elif txt[j] == "]":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return k, j


def insert_unit(txt, civ_key, bldg_id, uid, name, age):
    """Insert one unit entry, touching nothing else.  Returns (text, note)."""
    k, j = _units_span(txt, civ_key, bldg_id)
    arr = txt[k:j + 1]
    inner = arr.rstrip()
    assert inner.endswith("]"), inner[-40:]
    inner = inner[:-1].rstrip()
    if inner.endswith("["):
        # empty array: no leading comma
        entry = ('\r\n          {\r\n            "ID": %d,\r\n'
                 '            "Name": "%s",\r\n'
                 '            "RequiredAge": %d\r\n          }\r\n        ]'
                 % (uid, name, age))
    else:
        entry = (',\r\n          {\r\n            "ID": %d,\r\n'
                 '            "Name": "%s",\r\n'
                 '            "RequiredAge": %d\r\n          }\r\n        ]'
                 % (uid, name, age))
    new = txt[:k] + inner + entry + txt[j + 1:]
    return new, "%s/%d += unit %d" % (civ_key, bldg_id, uid)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    src = os.path.join(tk.game_root, FU_REL.replace("/", os.sep))
    if not os.path.isfile(src):
        print("MISSING %s" % src)
        return 2
    raw = open(src, "rb").read()
    txt = raw.decode("utf-8")

    notes = []
    txt, n1 = insert_unit(txt, CIV_KEY, BLDG_ID, NEW_UNIT, NEW_NAME, NEW_AGE)
    notes.append(n1)
    txt, n2 = insert_unit(txt, CIV_KEY2, BLDG_ID2, NEW_UNIT2, NEW_NAME2, NEW_AGE2)
    notes.append(n2)

    # --- assertions before anything touches disk --------------------------
    obj = json.loads(txt)                       # still valid JSON
    u1 = [u for b in obj[CIV_KEY]["Buildings"] if b["ID"] == BLDG_ID
          for u in b["Units"]]
    u2 = [u for b in obj[CIV_KEY2]["Buildings"] if b["ID"] == BLDG_ID2
          for u in b["Units"]]
    assert any(u["ID"] == NEW_UNIT for u in u1), "insert 1 did not land"
    assert any(u["ID"] == NEW_UNIT2 for u in u2), "insert 2 did not land"

    # --- emit -------------------------------------------------------------
    # Everything we did NOT touch must be byte-identical.  Prune exactly the two
    # entries we added out of the EDITED parse; what is left must equal the
    # original parse key for key.
    # (First version of this check pruned the ORIGINAL instead, which never had
    #  the entries, so it compared "original" against "original + 2" and failed
    #  for the wrong reason.  Prune the edited side, compare against original.)
    pruned = json.loads(txt)
    for _civ, _bld, _uid in ((CIV_KEY, BLDG_ID, NEW_UNIT),
                             (CIV_KEY2, BLDG_ID2, NEW_UNIT2)):
        for _b in pruned[_civ]["Buildings"]:
            if _b["ID"] == _bld:
                _b["Units"] = [u for u in _b["Units"] if u["ID"] != _uid]
    original = json.loads(raw.decode("utf-8"))
    assert pruned == original, "the edit changed something beyond the two entries"
    print("surgical edit: +%d bytes; parses; nothing else changed"
          % (len(txt.encode("utf-8")) - len(raw)))
    blob = txt.encode("utf-8")
    info = E.make_info("aoe2mod smoke2 build panel gate",
                       author="aoe2mod probe",
                       description="Only futuravailableunits.json differs.")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    man = E.emit_json_mod(OUT, {FU_REL: blob}, info,
                          base_dir=tk.game_root, overwrite=True)
    print()
    print("wrote %s" % OUT)
    for root, _d, files in os.walk(OUT):
        for f in files:
            p = os.path.join(root, f)
            print("   %-46s %d B" % (os.path.relpath(p, OUT).replace("\\", "/"),
                                     os.path.getsize(p)))
    print("changes_dat: %s   json_overrides: %s"
          % (man.get("changes_dat"), man.get("json_overrides")))

    # read it back off disk and re-assert
    back = open(os.path.join(OUT, FU_REL.replace("/", os.sep)), "rb").read()
    assert back == blob, "emitted bytes differ from what we intended"
    bobj = json.loads(back.decode("utf-8"))
    ok1 = any(u["ID"] == NEW_UNIT
              for b in bobj[CIV_KEY]["Buildings"] if b["ID"] == BLDG_ID
              for u in b["Units"])
    ok2 = any(u["ID"] == NEW_UNIT2
              for b in bobj[CIV_KEY2]["Buildings"] if b["ID"] == BLDG_ID2
              for u in b["Units"])
    print()
    print("read back from disk: Britons Barracks has Champi Scout: %s" % ok1)
    print("                     Britons Archery Range has Hand Cannoneer: %s" % ok2)

    print()
    print("WHAT THIS MOD TESTS, AND WHAT IT DOES NOT")
    print("  PROVEN: the shipped file parses, exactly two entries were added,")
    print("          every other byte is untouched, and the mod contains no")
    print("          .dat and no CivTechTrees file -- one variable only.")
    print("  IT DOES NOT PROVE that the build panel reads this file.  Only")
    print("          the user's next in-game look can do that.")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())

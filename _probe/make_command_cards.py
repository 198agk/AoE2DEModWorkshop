# -*- coding: utf-8 -*-
"""The command card is indexed BY THE BUILDING, and each unit says which one.

The first version walked each record's own `train_locations` and treated that as
"what this building trains". Backwards: for a unit record, `train_locations` says
WHICH BUILDING trains IT (`unit_id` is the building, `button_id` is the box). So
Barracks(12) appeared to train exactly one thing -- the one record that happens to
point at 12 -- instead of the 49 the docs measure.

Correct shape: iterate every unit, group by its `unit_id`.

Two measured facts this must respect (both already in `项目状态.md`):

  * `button_id` is a CHAIN number, not a slot. Barracks box 1 holds the whole
    militia upgrade line (16 units). Reporting one unit per box is wrong.
  * `.dat` is a SUPERSET: Barracks trains 49 units here while a given civ's tree
    lists 8. The narrowing happens in the tree/panel layer; this table reports
    the `.dat` truth and the caller narrows.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "command_cards.json")


def main():
    raw, _ = P.load_dat(DAT)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _start, _gv, _o = L.locate(raw, parser=p)

    gaia = civs[0]
    cards = {}
    entries = 0
    for u in gaia["units"]:
        for t in u.get("train_locations") or []:
            building = t.get("unit_id", -1)
            if building is None or building < 0:
                continue
            cards.setdefault(str(building), []).append({
                "unit": u["id"],
                "button": t.get("button_id", 0),
                "seconds": t.get("train_time", 0),
                # Where the box number lives. `locate` records
                # `_off_train_time` (ABSOLUTE) and the box byte sits
                # TRAIN_BUTTON_OFF=4 bytes after it -- see
                # aoe2mod/dat/newunit.py. `_off_button` does not exist on the
                # record, so exporting that produced all-null and a drag would
                # have had nowhere to write.
                "_off_train_time": t.get("_off_train_time"),
            })
            entries += 1

    out = {"source": "Gaia", "civ_count": len(civs), "cards": cards}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, separators=(",", ":"))

    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("buildings: %d | entries: %d" % (len(cards), entries))
    bar = cards.get("12") or []
    boxes = {}
    for r in bar:
        boxes.setdefault(r["button"], []).append(r["unit"])
    print("Barracks(12): %d units in %d boxes" % (len(bar), len(boxes)))
    for b in sorted(boxes)[:5]:
        print("   box %-2s -> %2d units %s" % (b, len(boxes[b]), boxes[b][:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

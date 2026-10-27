# -*- coding: utf-8 -*-
"""Export `{id: [names]}` for units and techs, out of the shipped index.

`nl.py` matches names by LONGEST SPAN over the whole sentence, which needs the
full name table.  The table lives in `aoe2mod/semantic/data/*_names.json` and is
loaded into `SemanticIndex`, whose entities carry four name fields: `zh`, `en`,
`tw`, `internal`.  All four are exported, because a player types any of them
("村民", "Villager", "Villager Male").

Output: `_golden/entity_names.json`
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "_golden", "entity_names.json")


def names_of(e):
    out = []
    for attr in ("zh", "en", "tw", "internal", "display"):
        v = getattr(e, attr, None)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return list(dict.fromkeys(out))


def main():
    from aoe2mod.semantic import index as IX

    ix = IX.index()
    result = {"units": {}, "techs": {}}
    for kind, table, key in (("unit", ix.units, "units"),
                             ("tech", ix.techs, "techs")):
        for eid, e in table.items():
            # `is_visible` is what the screen offers; a hidden record is an
            # internal variant a player cannot name, and including them would
            # make "剑士" match two id ranges that look identical.
            if not getattr(e, "is_visible", True):
                continue
            names = names_of(e)
            if names:
                result[key][str(eid)] = names
        print("%-8s %d entities" % (key, len(result[key])))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    for probe in ("83", "74", "93", "101"):
        if probe in result["units"]:
            print("  unit %-5s %s" % (probe, result["units"][probe][:4]))
    for probe in ("22", "67"):
        if probe in result["techs"]:
            print("  tech %-5s %s" % (probe, result["techs"][probe][:4]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

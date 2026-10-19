# -*- coding: utf-8 -*-
"""probe_icon_build_list.py -- the villager's OWN list is the build menu.

probe_icon_where_trained.py read the producer off the product and treated
"producer == 118" as "the villager builds it".  probe_icon_rule_crosscheck.py then
showed 184 rows where the Buildings material plainly names the entity (Town Center,
gates, walls, pavilions) yet the product-side record says producer -1 -- because a
Town Center's `train_locations` entry is the untrainable placeholder
`{unit_id: -1, button_id: 255}`, not a statement about who builds it.

The unambiguous source is the PRODUCER's own list: unit 118 (the Builder/Villager)
carries one TrainLocation per thing on its build menu, each with the button id that
menu uses (button 1 Barracks, 6 Farm, 13 Castle, ...).  So:

    in the villager's list -> the BUILD MENU -> icons.json "Buildings"
    not in it              -> the train list / portrait -> icons.json "Units"

This probe measures that, and cross-checks it against the material-name witness.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")
BUILDER = 118

_STOP = {"icon", "icons", "building", "buildings", "unit", "units", "the", "of",
         "and", "a", "b", "full", "empty", "no", "new", "old"}


def words(text):
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return {w.lower() for w in s.split()
            if len(w) >= 3 and w.lower() not in _STOP}


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        icons = json.load(fh)
    units_sec = icons.get("Units") or {}
    bld_sec = icons.get("Buildings") or {}

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    en = {}
    base = os.path.join(GAME, "resources", "en", "strings", "key-value")
    for name in S.KV_FILES:
        fp = os.path.join(base, name)
        if os.path.exists(fp):
            en.update(S.parse_kv_file(fp)[0])

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    builder = by_id.get(BUILDER) or {}
    menu = {}
    for e in builder.get("train_locations") or []:
        menu[e.get("unit_id")] = e.get("button_id")
    print("the Builder's (unit %d) build menu has %d entries: %s"
          % (BUILDER, len(menu), sorted(menu)[:20]))

    def rule(u):
        return "Buildings" if u.get("id") in menu else "Units"

    def witness(u):
        key = "%03d" % u["icon_id"]
        m = bld_sec.get(key)
        if not m:
            return "no-buildings-entry"
        name = en.get(u.get("_dll_name")) or ""
        if not words(name):
            return "unnamed"
        return "names-it" if (words(m) & words(name)) else "other-thing"

    def served(u):
        key = "%03d" % u["icon_id"]
        w = rule(u)
        return w if (key in (bld_sec if w == "Buildings" else units_sec)) else (
            "Units" if w == "Buildings" else "Buildings")

    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    both = [u for u in rows if ("%03d" % u["icon_id"]) in bld_sec
            and ("%03d" % u["icon_id"]) in units_sec]
    fell = [u for u in rows if served(u) != rule(u)]
    print("icon rows %d, ids in BOTH sections %d" % (len(rows), len(both)))
    print("rule served without fallback: %d / %d" % (len(rows) - len(fell), len(rows)))

    table = {}
    for u in both:
        table[(rule(u), witness(u))] = table.get((rule(u), witness(u)), 0) + 1
    print("\n(rule, material-name witness) where both sections exist:")
    for k in sorted(table, key=lambda k: (k[0], k[1])):
        print("  rule=%-9s witness=%-18s %4d" % (k[0], k[1], table[k]))

    bad = [u for u in both if rule(u) == "Buildings" and witness(u) == "other-thing"]
    print("\n=== rule=Buildings but the Buildings name is another thing: %d ===" % len(bad))
    for u in sorted(bad, key=lambda u: u.get("id") or 0):
        print("  unit %-5s icon=%-4s %-26r buildings=%s  btn=%s"
              % (u.get("id"), u.get("icon_id"),
                 (en.get(u.get("_dll_name")) or "")[:26],
                 bld_sec.get("%03d" % u["icon_id"]), menu.get(u.get("id"))))

    wrong = [u for u in both if rule(u) == "Units" and witness(u) == "names-it"]
    print("\n=== rule=Units while the Buildings name names it: %d ===" % len(wrong))
    for u in sorted(wrong, key=lambda u: u.get("id") or 0)[:25]:
        print("  unit %-5s icon=%-4s %-26r buildings=%s"
              % (u.get("id"), u.get("icon_id"),
                 (en.get(u.get("_dll_name")) or "")[:26],
                 bld_sec.get("%03d" % u["icon_id"])))

    print("\n=== fell back %d ===" % len(fell))
    for u in sorted(fell, key=lambda u: u.get("id") or 0)[:20]:
        print("  unit %-5s icon=%-4s rule=%-9s %r"
              % (u.get("id"), u.get("icon_id"), rule(u),
                 (en.get(u.get("_dll_name")) or "")[:26]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

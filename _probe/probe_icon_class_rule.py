# -*- coding: utf-8 -*-
"""probe_icon_class_rule.py -- is the section chosen by unit CLASS, not by type?

probe_icon_look.py settled what the two sections hold by looking at pixels:

  icon  2  Units -> knight portrait      Buildings -> crossed swords  (Barracks
                                                                      button)
  icon 15  Units -> villager portrait    Buildings -> a dock          (unit 446
                                                                      "PORT")
  icon 34  Units -> ?                    Buildings -> a house         (unit 70)
  icon  7  Units -> ?                    Buildings -> a castle        (unit 82)
  icon 28  Units -> a trebuchet          Buildings -> ?                (unit 71
                                                                      Town Center
                                                                      and unit 42
                                                                      Trebuchet
                                                                      BOTH say 28)

Unit 42 is a trebuchet with type 80 (the unpacked trebuchet is stored as a
building), so a "type == 80 -> Buildings" rule would hand the trebuchet the Town
Center icon.  The `.dat` also carries a unit CLASS, and the game's own class 3 is
"Building".  This probe measures: for every entity with an icon, what class does
it have, and does "class == 3 -> Buildings, else Units" disagree with anything
we can see?

It prints the whole class distribution and the class of the flagged cases, so the
rule is chosen from data rather than from the word "building".
"""
from __future__ import print_function

import codecs
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")

FLAGGED = {42: "Trebuchet (unpacked)", 71: "Town Center", 110: "Trade Workshop",
           263: "Colosseum", 331: "Trebuchet packed", 446: "Port",
           682: "Bad Neighbor", 826: "Monument", 1193: "FARMDROP",
           1690: "Warwolf Trebuchet", 2412: "Supply Cart A",
           2678: "Fort Wall", 444: "TC packed", 12: "Barracks",
           83: "Villager", 4: "Archer", 70: "House", 82: "Castle"}


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
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]

    # class x type cross-tab, and how many of each can be served where
    cross = {}
    for u in rows:
        k = (u.get("class"), u.get("type"))
        cross[k] = cross.get(k, 0) + 1
    print("class x type among entities with an icon (%d rows):" % len(rows))
    for k in sorted(cross, key=lambda k: (-cross[k], str(k))):
        print("  class=%-4s type=%-4s %4d" % (k[0], k[1], cross[k]))

    print("\n=== flagged cases ===")
    print("  %-5s %-8s %-8s %-10s %-6s %-6s %-26s" %
          ("id", "class", "type", "icon", "inU", "inB", "english"))
    for i in sorted(FLAGGED):
        u = by_id.get(i) or {}
        key = "%03d" % (u.get("icon_id") or 0)
        print("  %-5d %-8s %-8s %-10s %-6s %-6s %-26r"
              % (i, u.get("class"), u.get("type"), u.get("icon_id"),
                 key in units_sec, key in bld_sec,
                 (en.get(u.get("_dll_name")) or FLAGGED[i])[:26]))

    # the two candidate rules, compared
    def rule_class(u):
        return "Buildings" if u.get("class") == 3 else "Units"

    def rule_type(u):
        return "Buildings" if u.get("type") == 80 else "Units"

    diff = [u for u in rows if rule_class(u) != rule_type(u)]
    print("\nclass rule vs type rule: %d entities differ" % len(diff))
    for u in sorted(diff, key=lambda u: u.get("id") or 0)[:30]:
        key = "%03d" % u["icon_id"]
        print("  unit %-5s class=%-4s type=%-4s icon=%-4s class->%-10s type->%-10s en=%r"
              % (u.get("id"), u.get("class"), u.get("type"), u.get("icon_id"),
                 rule_class(u), rule_type(u),
                 (en.get(u.get("_dll_name")) or "")[:22]))

    # class-3 entities whose icon only exists in the Units section
    only_units = [u for u in rows if rule_class(u) == "Buildings"
                  and ("%03d" % u["icon_id"]) not in bld_sec]
    print("\nclass-3 entities with NO Buildings entry: %d" % len(only_units))
    for u in sorted(only_units, key=lambda u: u.get("id") or 0)[:20]:
        print("  unit %-5s icon=%-4s en=%r" % (u.get("id"), u.get("icon_id"),
                                               (en.get(u.get("_dll_name")) or "")[:26]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

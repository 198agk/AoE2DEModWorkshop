# -*- coding: utf-8 -*-
"""probe_icon_produced_rule.py -- can "is this thing produced by a building"
choose the icon section?

Looking at the rendered sheets settled what each section IS:

  Buildings[2]  = crossed swords        <- the Barracks BUILD BUTTON
  Buildings[7]  = castle                <- castle build button
  Buildings[17] = scales/market         <- market build button
  Buildings[28] = two villagers         <- the Town Center BUILD BUTTON
  Buildings[34] = house                 <- house build button
  Buildings[35] = farm rows             <- farm build button
  Buildings[40] = axe over logs         <- lumber camp build button
  Buildings[58] = the Colosseum         <- amphitheatre button
  Units[28]     = a trebuchet           <- the trebuchet TRAIN icon
  Units[15]     = the villager portrait

So the two sections are two different UI lookup tables: `Buildings` is the build
menu, `Units` is the portrait/train list.  Neither type (the trebuchet is type 80
like a barracks) nor class (a farm is class 49, a trebuchet 54) separates them.

The behavioural separator would be production: a thing that some building trains
is shown from `Units`, a thing a villager builds is shown from `Buildings`.  This
probe measures that rule and prints every entity where it disagrees with
"Buildings if present".
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

# entities whose icon we can eyeball, with what the game shows in the build menu
CHECK = {2: "Barracks build button", 7: "Castle build button",
         17: "Archer portrait / Market button", 28: "TC button / Trebuchet icon",
         34: "House button", 35: "Farm button", 40: "Lumber Camp button",
         58: "Colosseum button", 94: "action icon", 15: "villager / dock"}


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

    # who trains whom: train_locations live on the producer
    produced = set()
    for u in by_id.values():
        for loc in u.get("train_locations") or ():
            uid = loc.get("unit") if isinstance(loc, dict) else None
            if uid is None and isinstance(loc, (list, tuple)) and len(loc) >= 4:
                uid = loc[3]
            if uid is not None:
                produced.add(uid)
    print("units trained by something: %d" % len(produced))

    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    agree = disagree = neither = 0
    dis = []
    for u in rows:
        key = "%03d" % u["icon_id"]
        hu, hb = key in units_sec, key in bld_sec
        want = "Units" if u.get("id") in produced else "Buildings"
        have = want if (key in (units_sec if want == "Units" else bld_sec)) else (
            "Buildings" if want == "Units" else "Units")
        if not (hu or hb):
            neither += 1
        elif have == want:
            agree += 1
        else:
            disagree += 1
        if have != want or (want == "Buildings" and not hb):
            dis.append((u, want, have))

    print("icon rows: %d   rule served: %d   fell back: %d   no entry at all: %d"
          % (len(rows), agree, disagree, neither))

    print("\n=== fell back / suspicious (%d), first 40 ===" % len(dis))
    for u, want, have in sorted(dis, key=lambda r: r[0].get("id") or 0)[:40]:
        print("  unit %-5s type=%-3s class=%-3s icon=%-4s want=%-9s got=%-9s produced=%-5s en=%r"
              % (u.get("id"), u.get("type"), u.get("class"), u.get("icon_id"),
                 want, have, u.get("id") in produced,
                 (en.get(u.get("_dll_name")) or "")[:22]))

    print("\n=== the eyeballed cases ===")
    for i in sorted(CHECK):
        u = by_id.get(i) or {}
        key = "%03d" % (u.get("icon_id") or 0)
        print("  unit %-5s type=%-3s class=%-3s icon=%-4s produced=%-5s inU=%-5s inB=%-5s %r"
              % (i, u.get("type"), u.get("class"), u.get("icon_id"),
                 i in produced, key in units_sec, key in bld_sec, CHECK[i]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

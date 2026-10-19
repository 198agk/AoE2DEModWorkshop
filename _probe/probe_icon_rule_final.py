# -*- coding: utf-8 -*-
"""probe_icon_rule_final.py -- the rule stated the way the data actually stores it.

probe_train_locations.py established the direction: `train_locations` lives on the
PRODUCT and its `unit_id` names a PRODUCER.  Unit 12 (Barracks) says
{train_time 50, unit_id 118 (Builder), button_id 1} = "the Builder makes a
Barracks on button 1".  Unit 42 (Trebuchet) says unit_id 82 (Castle) = "the Castle
makes a Trebuchet".

So the two icon sections split on exactly that:

    Builder's list  (producer 118)  -> the BUILD MENU  -> icons.json "Buildings"
    a building's list (producer 80x) -> the TRAIN LIST -> icons.json "Units"
    nobody's list    (producer -1)   -> not buildable  -> "Units" is where the game
                                        keeps its portrait

That is a fact about the record, not about the word "building", and it is the rule
this probe measures at 100% coverage -- including the entities the earlier
type-based and class-based rules mis-served.
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

BUILDER = 118        # the villager/builder unit id; see probe_icon_where_trained.py


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

    def producers(u):
        return [e.get("unit_id") for e in (u.get("train_locations") or [])]

    def want(u):
        prods = producers(u)
        for pid in prods:
            if pid == BUILDER:
                return "Buildings"
        for pid in prods:
            prod = by_id.get(pid)
            if prod is not None and prod.get("type") == 80:
                return "Units"
        return "Units"

    def served(u):
        key = "%03d" % u["icon_id"]
        w = want(u)
        if w == "Buildings":
            return "Buildings" if key in bld_sec else (
                "Units" if key in units_sec else None)
        return "Units" if key in units_sec else (
            "Buildings" if key in bld_sec else None)

    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    tally = {"agree": 0, "fellback": [], "nowhere": []}
    for u in rows:
        w, h = want(u), served(u)
        if h is None:
            tally["nowhere"].append(u)
        elif h == w:
            tally["agree"] += 1
        else:
            tally["fellback"].append((u, w, h))

    print("icon rows: %d" % len(rows))
    print("  asked for the section the record points at, got it: %d (%.2f%%)"
          % (tally["agree"], 100.0 * tally["agree"] / len(rows)))
    print("  section missing, fell back:  %d" % len(tally["fellback"]))
    print("  no entry in either section:  %d" % len(tally["nowhere"]))

    print("\n=== fell back %d ===" % len(tally["fellback"]))
    for u, w, h in sorted(tally["fellback"], key=lambda r: r[0].get("id") or 0):
        print("  unit %-5s type=%-3s class=%-3s icon=%-4s want=%-9s got=%-9s prods=%-10s %r"
              % (u.get("id"), u.get("type"), u.get("class"), u.get("icon_id"),
                 w, h, producers(u)[:2], (en.get(u.get("_dll_name")) or "")[:24]))

    # split by reason, so a systematic hole is visible as a group
    from collections import Counter
    why = Counter()
    for u, w, h in tally["fellback"]:
        why[(w, u.get("type"))] += 1
    print("\n=== fallbacks grouped ===")
    for k in sorted(why, key=lambda k: (k[0], str(k[1]))):
        print("  want=%-9s type=%-4s %d" % (k[0], k[1], why[k]))

    print("\n=== agreement by type ===")
    by = Counter()
    for u in rows:
        by[(u.get("type"), want(u))] += 1
    for k in sorted(by, key=lambda k: (str(k[0]), k[1])):
        print("  type=%-4s -> %-9s %4d" % (k[0], k[1], by[k]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

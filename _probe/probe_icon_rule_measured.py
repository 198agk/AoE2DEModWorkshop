# -*- coding: utf-8 -*-
"""probe_icon_rule_measured.py -- the rule, measured on all 1,344 icon rows.

WHAT THE PICTURES SAID (probe_icon_look.py / probe_icon_sheet.py)
    Buildings[2]  crossed swords     <-> unit 12 Barracks is BUILT by a villager
    Buildings[7]  a castle           <-> unit 82 Castle is BUILT by a villager
    Buildings[28] two villagers      <-> unit 71 Town Center is BUILT / placed
    Buildings[35] farm rows          <-> unit 50 Farm is BUILT by a villager
    Buildings[11] a monastery        <-> unit 655 Mosque is BUILT
    Units[28]     a trebuchet        <-> unit 42 Trebuchet is TRAINED in a Castle
    Units[17]     an archer          <-> unit 4 Archer is TRAINED in an Archery Range
    Units[15]     a villager         <-> unit 83 Villager is TRAINED in a Town Center

WHAT THE RECORD SAYS (probe_icon_where_trained.py)
    A TrainLocation lives on the unit, and its `unit_id` is the PRODUCER.
    producer 118 is the villager/builder -> that thing is CONSTRUCTED.
    producer 82 / 87 / 109 are buildings -> that thing is TRAINED.

THE RULE THIS PROBE MEASURES
    constructed (or placed, producer -1) -> `Buildings` section
    trained by a building                -> `Units` section

Neither unit TYPE nor unit CLASS can stand in for this: the Trebuchet is type 80
and class 54, exactly like a Bad Neighbor, yet one is trained in a Castle and the
other is not; the Farm is type 80 class 49 and its Buildings entry is farm rows.

Prints agreement, every disagreement, and the fallbacks for entities with no
recorded producer.
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

EYEBALLED = {2: "Barracks/Castle", 7: "Castle", 11: "Mosque", 17: "Market/Archer",
             28: "TC/Trebuchet", 35: "Farm", 58: "Colosseum", 94: "action"}


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

    produce_times = {}
    for u in by_id.values():
        for e in u.get("train_locations") or []:
            uid = e.get("unit_id")
            produce_times[uid] = produce_times.get(uid, 0) + 1

    def producers(u):
        return [e.get("unit_id") for e in (u.get("train_locations") or [])]

    def want_section(u):
        """'Units' if a BUILDING trains it, else 'Buildings'."""
        for pid in producers(u):
            prod = by_id.get(pid)
            if prod is None:
                continue
            if prod.get("type") == 80:          # a building trains it
                return "Units"
        return "Buildings"

    def have_section(u):
        key = "%03d" % u["icon_id"]
        w = want_section(u)
        if w == "Units":
            return ("Units" if key in units_sec else
                    "Buildings" if key in bld_sec else None)
        return ("Buildings" if key in bld_sec else
                "Units" if key in units_sec else None)

    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    agree, fellback, nowhere = [], [], []
    for u in rows:
        w, h = want_section(u), have_section(u)
        if h is None:
            nowhere.append(u)
        elif h == w:
            agree.append(u)
        else:
            fellback.append((u, w, h))

    print("icon rows: %d" % len(rows))
    print("  rule agreed with an existing section entry: %d (%.1f%%)"
          % (len(agree), 100.0 * len(agree) / len(rows)))
    print("  wanted section missing, fell back:          %d" % len(fellback))
    print("  no entry in either section:                 %d" % len(nowhere))

    print("\n=== fell back (want / got) %d ===" % len(fellback))
    for u, w, h in sorted(fellback, key=lambda r: r[0].get("id") or 0)[:30]:
        print("  unit %-5s type=%-3s class=%-3s icon=%-4s want=%-9s got=%-9s prods=%-12s %r"
              % (u.get("id"), u.get("type"), u.get("class"), u.get("icon_id"),
                 w, h, producers(u)[:3], (en.get(u.get("_dll_name")) or "")[:22]))

    print("\n=== no entry at all %d ===" % len(nowhere))
    for u in sorted(nowhere, key=lambda u: u.get("id") or 0)[:15]:
        print("  unit %-5s type=%-3s icon=%-4s %r"
              % (u.get("id"), u.get("type"), u.get("icon_id"),
                 (en.get(u.get("_dll_name")) or "")[:24]))

    print("\n=== built vs trained, by type ===")
    tally = {}
    for u in rows:
        k = (u.get("type"), want_section(u))
        tally[k] = tally.get(k, 0) + 1
    for k in sorted(tally, key=lambda k: (str(k[0]), k[1])):
        print("  type=%-4s -> %-9s %4d" % (k[0], k[1], tally[k]))

    print("\n=== eyeballed cases ===")
    for i in sorted(EYEBALLED):
        u = by_id.get(i) or {}
        print("  unit %-5s %-26r want=%-9s got=%-9s  %s"
              % (i, (en.get(u.get("_dll_name")) or "")[:26],
                 want_section(u), have_section(u), EYEBALLED[i]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

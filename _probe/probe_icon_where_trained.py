# -*- coding: utf-8 -*-
"""probe_icon_where_trained.py -- whose list says who makes what?

probe_train_locations.py showed unit 83 (Villager) carries train_locations
[{train_time: 25, unit_id: 109, button_id: 1}] and unit 109 IS the Town Center.
So a TrainLocation lives on the UNIT and `unit_id` names the PRODUCER, not the
product -- the opposite of what probe_icon_produced_rule.py assumed, which is why
it counted "units trained by something: 0".

The remaining question for icon section choice: is a thing CONSTRUCTED by a
villager (build menu -> `Buildings` section) or TRAINED in a building (train
list -> `Units` section)?  The producer id tells us: a mobile villager/builder
means "constructed", a building means "trained".

Prints the producer and its own name for the eyeballed cases.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

CASES = [12, 71, 42, 82, 50, 4, 83, 682, 446, 263, 110, 331, 1193, 2678, 2412,
         9, 87, 101, 199, 232]


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

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

    for i in CASES:
        u = by_id.get(i) or {}
        tl = u.get("train_locations") or []
        print("\nunit %-5s %-26r type=%-3s class=%-3s icon=%s"
              % (i, (en.get(u.get("_dll_name")) or "")[:26], u.get("type"),
                 u.get("class"), u.get("icon_id")))
        if not tl:
            print("   train_locations: EMPTY")
        for e in tl:
            pid = e.get("unit_id")
            prod = by_id.get(pid) or {}
            print("   t=%-4s producer=%-6s %-24r type=%-4s btn=%s"
                  % (e.get("train_time"), pid,
                     (en.get(prod.get("_dll_name")) or "")[:24],
                     prod.get("type"), e.get("button_id")))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

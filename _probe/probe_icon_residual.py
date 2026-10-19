# -*- coding: utf-8 -*-
"""probe_icon_residual.py -- who are the 588 rows with no witness?

probe_icon_rule_composite.py settles 756 of the 1344 icon-bearing units with an
independent witness (the Builder makes it / a building trains it / the build-menu
material names it) and leaves 588 with none, defaulted to "Units".

A default is a claim.  This probe prints what those 588 actually are -- by type,
by name, and whether the Units section even has a picture for them -- so the
default can be judged instead of assumed.
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

TYPE_ZH = {10: "building?", 20: "??", 30: "树/资源", 50: "单位(人/骑)", 60: "??",
           70: "单位(杂)", 80: "建筑/攻城", 90: "鸟/虫"}


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

    resid = []
    for u in by_id.values():
        icon = u.get("icon_id") or 0
        if icon <= 0:
            continue
        key = "%03d" % icon
        prods = [e.get("unit_id") for e in (u.get("train_locations") or [])]
        if any(pd == BUILDER for pd in prods):
            continue
        if any((by_id.get(pd) or {}).get("type") == 80 for pd in prods):
            continue
        if bld_sec.get(key) and (words(bld_sec[key]) & words(en.get(u.get("_dll_name")) or "")):
            continue
        resid.append(u)

    print("residual rows: %d" % len(resid))
    by_type = {}
    for u in resid:
        by_type[u.get("type")] = by_type.get(u.get("type"), 0) + 1
    print("\nby unit type:")
    for t in sorted(by_type, key=lambda t: -by_type[t]):
        print("  type %-4s %-14s %4d" % (t, TYPE_ZH.get(t, ""), by_type[t]))

    no_units_pic = [u for u in resid if ("%03d" % u["icon_id"]) not in units_sec]
    only_bld = [u for u in resid
                if ("%03d" % u["icon_id"]) in bld_sec
                and ("%03d" % u["icon_id"]) not in units_sec]
    print("\nno picture in the Units section at all: %d" % len(no_units_pic))
    print("only a Buildings picture (default is showing nothing): %d" % len(only_bld))
    for u in sorted(only_bld, key=lambda u: u.get("id") or 0)[:15]:
        print("  unit %-5s icon=%-4s type=%-3s %r -> %s"
              % (u.get("id"), u.get("icon_id"), u.get("type"),
                 (en.get(u.get("_dll_name")) or "")[:24],
                 bld_sec["%03d" % u["icon_id"]]))

    print("\nsample of the residual (first 25):")
    for u in sorted(resid, key=lambda u: u.get("id") or 0)[:25]:
        print("  unit %-5s type=%-3s class=%-3s icon=%-4s %r"
              % (u.get("id"), u.get("type"), u.get("class"), u.get("icon_id"),
                 (en.get(u.get("_dll_name")) or "")[:28]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

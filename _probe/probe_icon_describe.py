# -*- coding: utf-8 -*-
"""probe_icon_describe.py -- two questions the icon/description layer needs.

1. Of the 588 units whose section is a DEFAULT rather than a witness, how many
   even have a Buildings entry?  If almost none do, "default to Units" is not a
   coin flip: it is the only option that exists.
2. Do units have description / help / tech-tree text at all?  unit_names.json has
   none, and the research note says the 107xxx LanguageDLLHelp ids are absent
   from both shipped string tables -- which would mean unit prose cannot be
   shown, and the UI must not pretend otherwise.
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
    bld_sec = icons.get("Buildings") or {}
    units_sec = icons.get("Units") or {}

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    en = {}
    zh = {}
    base = os.path.join(GAME, "resources")
    for lang, table in (("en", en), ("zh", zh)):
        d = os.path.join(base, lang, "strings", "key-value")
        for name in S.KV_FILES:
            fp = os.path.join(d, name)
            if os.path.exists(fp):
                table.update(S.parse_kv_file(fp)[0])

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

    both = [u for u in resid if ("%03d" % u["icon_id"]) in bld_sec]
    print("residual %d; of those, have BOTH pictures %d, only Units %d"
          % (len(resid), len(both), len(resid) - len(both)))

    # ---- do units have prose? -------------------------------------------
    print("\n--- unit prose availability ---")
    keys = {}
    for u in by_id.values():
        for k in u:
            keys[k] = keys.get(k, 0) + 1
    dll = [k for k in keys if "dll" in k.lower() or "help" in k.lower()
           or "desc" in k.lower() or "lang" in k.lower()]
    print("unit record fields that could hold text: %s" % sorted(dll))
    sample = [83, 74, 4, 2550, 82, 12]
    for uid in sample:
        u = by_id.get(uid) or {}
        names = u.get("_dll_names")
        nameid = u.get("_dll_name")
        hit_en = en.get(nameid)
        hit_zh = zh.get(nameid)
        print("  unit %-5s nameid=%-8s en=%-18r zh=%r"
              % (uid, nameid, (hit_en or "")[:18], (hit_zh or "")[:18]))
        if isinstance(names, dict):
            for k, v in sorted(names.items()):
                print("      %-22s %s -> en=%r" % (k, v, (en.get(v) or "")[:40]))
        elif names:
            print("      _dll_names = %r" % (names,))

    # how many of the 107xxx ids exist at all?
    lo = [k for k in en if isinstance(k, int) and k >= 100000]
    print("\nstring ids >= 100000 in en table: %d (min %s max %s)"
          % (len(lo), min(lo) if lo else None, max(lo) if lo else None))
    print("any id in 107000..108000: %d"
          % len([k for k in lo if 107000 <= k < 108000]))

    # tech prose, for contrast
    print("\ntech 22 (Loom) ids: %s"
          % {k: v for k, v in (SI_TECH(22) or {}).items() if "string" in k or "id" in k})
    return 0


def SI_TECH(tid):
    try:
        from aoe2mod.semantic import index as SI
        e = SI.index().techs.get(tid)
        raw = e._extra if e else None
        return raw
    except Exception:
        return None


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

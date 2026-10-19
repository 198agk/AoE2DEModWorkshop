# -*- coding: utf-8 -*-
"""probe_icon_rule_composite.py -- the composite rule, and its residual.

Three rules have each died on measurement:

  * by unit TYPE  -- the Trebuchet is type 80 exactly like the Barracks.
  * by unit CLASS -- farms (49) and trebuchets (54) are classes, not kinds; 161
                     rows disagree with type.
  * by the villager's OWN build list -- unit 118 carries one train_location
                     (Town Center); the build menu is not stored there.

probe_icon_rule_final.py measured the rule that survived, at 1344/1344 coverage:

    a TrainLocation on the PRODUCT whose `unit_id` is the Builder (118)
        -> the thing appears in the BUILD MENU  -> icons.json "Buildings"
    a producer that is a building (type 80)
        -> the thing is TRAINED                 -> icons.json "Units"
    producer -1 / no entry (the placeholder unit 71 carries)
        -> undecided

For the undecided third it fell back to "Units", and probe_icon_rule_crosscheck.py
showed 184 of those have a Buildings material that literally names them (Town
Center, Gate, Palisade Wall, Pavilion, Fish Trap, Aqueduct).  So the third case is
resolved by the material name.

This probe measures the COMPOSITE rule and prints what is left over, so the
residual can be reviewed as a list rather than assumed to be zero.
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


def section_for(uid, train_locations, by_id, buildings_name, english_name):
    """Return (section, why).  Documented in the module docstring."""
    prods = [e.get("unit_id") for e in (train_locations or [])]
    if any(p == BUILDER for p in prods):
        return "Buildings", "the Builder makes it (build menu)"
    for p in prods:
        prod = by_id.get(p)
        if prod is not None and prod.get("type") == 80:
            return "Units", "building %d trains it" % p
    if buildings_name and (words(buildings_name) & words(english_name or "")):
        return "Buildings", "no producer; the build-menu material names it"
    return "Units", "no producer and no matching build-menu material"


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
    reasons = {}
    fell, clash = [], []
    for u in rows:
        key = "%03d" % u["icon_id"]
        sec, why = section_for(u.get("id"), u.get("train_locations"), by_id,
                              bld_sec.get(key), en.get(u.get("_dll_name")))
        reasons[why] = reasons.get(why, 0) + 1
        have = sec if (key in (bld_sec if sec == "Buildings" else units_sec)) else (
            "Units" if sec == "Buildings" else "Buildings")
        if have != sec:
            fell.append((u, sec, why))
        # residual: did the material name contradict the choice?
        other = units_sec.get(key) if sec == "Buildings" else bld_sec.get(key)
        if sec == "Units" and bld_sec.get(key) and (
                words(bld_sec[key]) & words(en.get(u.get("_dll_name")) or "")):
            clash.append((u, bld_sec[key]))

    print("icon rows: %d" % len(rows))
    print("\nwhy each row got its section:")
    for k in sorted(reasons, key=lambda k: -reasons[k]):
        print("  %-46s %4d" % (k, reasons[k]))
    print("\nchosen section missing -> fell back: %d" % len(fell))
    print("chose Units while a build-menu material names the entity: %d" % len(clash))
    for u, m in sorted(clash, key=lambda r: r[0].get("id") or 0)[:20]:
        print("  unit %-5s icon=%-4s %-24r buildings=%s"
              % (u.get("id"), u.get("icon_id"),
                 (en.get(u.get("_dll_name")) or "")[:24], m))
    for u, sec, why in sorted(fell, key=lambda r: r[0].get("id") or 0)[:10]:
        print("  FELL unit %-5s icon=%-4s wanted=%s %r"
              % (u.get("id"), u.get("icon_id"), sec,
                 (en.get(u.get("_dll_name")) or "")[:24]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

# -*- coding: utf-8 -*-
"""probe_icon_rule_typed.py -- is the section chosen by TYPE, not by name?

probe_icon_look.py showed the two sections hold different kinds of picture:

  icon_id 2   Units -> a knight portrait      Buildings -> crossed swords (the
                                                  Barracks button in game)
  icon_id 15  Units -> the villager portrait   Buildings -> a dock
  icon_id 34  Units -> ?                       Buildings -> a house
  icon_id 37  Units -> ?                       Buildings -> a mosque (Wonder)

Unit 446 "PORT" is a building with icon_id 15 and its internal name shares no
word with "Dock3", so the name test drops it -- yet Buildings[15] is a dock and
Units[15] is a villager, i.e. the NAME test was never the mechanism.  The
mechanism looks like: a building (type 80) is drawn from the Buildings section,
everything else from Units.

This probe measures that rule directly and lists the cases where the type rule
and the name rule disagree, so a human can eyeball the disagreements.
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

_MAT_RE = re.compile(r"^(Unit|Building|Icon)icons?(\d+)(.*)$", re.I)
_STOP = {"building", "icon", "icons", "unit", "the", "of", "and"}


def words(text):
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    out = set()
    for w in s.split():
        w = re.sub(r"\d+", "", w).strip().lower()
        if w and w not in _STOP:
            out.add(w)
    return out


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

    # type distribution among entities that even have an icon
    types = {}
    for u in rows:
        types[u.get("type")] = types.get(u.get("type"), 0) + 1
    print("type distribution of entities with icon_id>0:")
    for t in sorted(types):
        print("  type %-4s %d" % (t, types[t]))

    both = chosen_ok = chosen_missing = 0
    fell_back = []
    disagree = []
    for u in rows:
        key = "%03d" % u["icon_id"]
        has_u, has_b = key in units_sec, key in bld_sec
        if has_u and has_b:
            both += 1
        want = "Buildings" if u.get("type") == 80 else "Units"
        alt = "Units" if want == "Buildings" else "Buildings"
        pick = want if (key in (bld_sec if want == "Buildings" else units_sec)) else alt
        if pick != want:
            chosen_missing += 1
            fell_back.append((u, pick))
        else:
            chosen_ok += 1
            picked_name = (bld_sec if pick == "Buildings" else units_sec)[key]
            bw = words((_MAT_RE.match(picked_name) or [None, "", "", picked_name])[3]
                       if _MAT_RE.match(picked_name) else picked_name)
            ent = words(en.get(u.get("_dll_name")) or "")
            if bw and ent and not (bw & ent):
                disagree.append((u, pick, picked_name))

    print("\nentities with an icon: %d" % len(rows))
    print("icon_id present in BOTH sections: %d" % both)
    print("type rule served: %d   fell back to the other section: %d"
          % (chosen_ok, chosen_missing))
    print("of the served ones, name test disagrees with the type rule: %d"
          % len(disagree))

    print("\n=== FELL BACK (wanted section has no such icon_id) %d ===" % len(fell_back))
    for u, pick in sorted(fell_back, key=lambda r: r[0].get("id") or 0)[:40]:
        print("  unit %-5s type=%-3s icon=%-4s -> %-10s en=%r"
              % (u.get("id"), u.get("type"), u.get("icon_id"), pick,
                 (en.get(u.get("_dll_name")) or "")[:26]))

    print("\n=== NAME SAYS NO, TYPE SAYS YES %d (eyeball these) ===" % len(disagree))
    for u, pick, mname in sorted(disagree, key=lambda r: r[0].get("id") or 0)[:40]:
        print("  unit %-5s type=%-3s icon=%-4s %-32s en=%r code=%r"
              % (u.get("id"), u.get("type"), u.get("icon_id"), mname,
                 (en.get(u.get("_dll_name")) or "")[:24], (u.get("name") or "")[:20]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

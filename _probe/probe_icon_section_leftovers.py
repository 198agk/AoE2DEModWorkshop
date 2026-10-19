# -*- coding: utf-8 -*-
"""probe_icon_section_leftovers.py -- the cases the tie-break does NOT settle.

probe_icon_section_rule.py measured the proposed rule:

    if the Buildings-section material name denotes the entity, use Buildings

and it fires 70.1% of the time on real buildings (type 80) versus 0.1% on
everything else -- so the test is a discriminator, not name-shaped noise.  But
70.1% is not 100%: 102 buildings fall through to the Units section.  This probe
prints them, plus the single non-building hit, so a human can say whether the
fallback is right or whether those 102 want a third rule.

Nothing here is a claim about what the game draws; it is a list of the places
where the mechanical rule needs a human eye.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "_probe", "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")

_MAT_RE = re.compile(r"^(Unit|Building)icons(\d+)(.*)$", re.I)


def words(text):
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    out = set()
    for w in s.split():
        # trailing variant digits are glued to the word (Barracks1) and would
        # otherwise never intersect the entity name (Barracks)
        w = re.sub(r"\d+", "", w).strip().lower()
        if w:
            out.add(w)
    return out


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        icons = json.load(fh)

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    def table(loc):
        base = os.path.join(GAME, "resources", loc, "strings", "key-value")
        merged = {}
        for name in S.KV_FILES:
            fp = os.path.join(base, name)
            if os.path.exists(fp):
                merged.update(S.parse_kv_file(fp)[0])
        return merged

    en, zh = table("en"), table("zh")

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]

    def sec(section, icon_id):
        return (icons.get(section) or {}).get("%03d" % icon_id)

    left = []
    stray = []
    for u in rows:
        b = sec("Buildings", u["icon_id"])
        if not b:
            continue
        m = _MAT_RE.match(b)
        matted = words(m.group(3)) if m else words(b)
        name_en = en.get(u.get("_dll_name")) or ""
        hit = bool(matted & words(name_en))
        if hit and u.get("type") != 80:
            stray.append((u, name_en, b))
        elif (not hit) and u.get("type") == 80:
            left.append((u, name_en, b, sec("Units", u["icon_id"])))

    print("BUILDINGS THAT FALL THROUGH TO Units (%d):" % len(left))
    for u, name_en, b, un in sorted(left, key=lambda r: r[0].get("id") or 0):
        print("  unit %-5s type=%-3s en=%-28r buildings=%-38s units=%s"
              % (u.get("id"), u.get("type"), name_en, b, un))

    print("\nNON-BUILDINGS WHERE THE RULE FIRES ANYWAY (%d):" % len(stray))
    for u, name_en, b in stray:
        print("  unit %-5s type=%-3s en=%-28r buildings=%s"
              % (u.get("id"), u.get("type"), name_en, b))

    # Are the fall-throughs concentrated in a few material names?  A third rule
    # has a chance only if they cluster; if they are 102 unrelated names, the
    # honest answer is "Units is the default and Buildings only when it denotes".
    print("\nFALL-THROUGH MATERIAL NAMES (clustering test):")
    tally = {}
    for u, name_en, b, un in left:
        tally[b] = tally.get(b, 0) + 1
    for b in sorted(tally, key=lambda k: (-tally[k], k)):
        print("  %3d  %s" % (tally[b], b))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

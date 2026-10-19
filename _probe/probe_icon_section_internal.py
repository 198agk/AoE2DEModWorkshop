# -*- coding: utf-8 -*-
"""probe_icon_section_internal.py -- can the entity's INTERNAL name settle the
leftovers the display name cannot?

probe_icon_section_leftovers.py left 62 type-80 entities falling through to the
Units section.  Most of them have an EMPTY display name (unit 182, 889, 1193,
1693, 1890 ...), so the "does the building material name denote this entity"
test has nothing to compare against -- not a wrong answer, a missing one.

The .dat also carries an internal code name per unit (`UnitNames`), and for
buildings it is descriptive (`LUMBER_CAMP`, `FARM`, `HOUSE`).  This probe asks
whether matching the building material name against the INTERNAL name instead of
the display name recovers those cases, and keeps the same control: it must stay
rare on entities that are not buildings.

Output is a decision table, not a conclusion: `recovered` rows are the evidence,
`still unknown` rows are what a human would have to look at in-game.
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
# words that carry no identity once a material name is reduced to words
_STOP = {"building", "icon", "icons", "unit", "the", "of", "and", "a", "b", "x"}


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

    en = table("en")

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)
    print("unit record keys available: %s" % sorted(k for k in (by_id.get(83) or {}) if k.startswith("name")))
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]

    def sec(section, icon_id):
        return (icons.get(section) or {}).get("%03d" % icon_id)

    def mat_words(mname):
        if not mname:
            return set()
        m = _MAT_RE.match(mname)
        return words(m.group(3) if m else mname)

    tally = {}
    recovered = []
    unknown = []
    for u in rows:
        b = sec("Buildings", u["icon_id"])
        if not b:
            continue
        bw = mat_words(b)
        ent_en = words(en.get(u.get("_dll_name")) or "")
        ent_code = words(u.get("name") or u.get("internal") or "")
        if bw & ent_en:
            continue                      # already settled by the display name
        if not (u.get("type") == 80):
            continue                      # the control group, not the target
        if bw & ent_code:
            recovered.append((u, b, sorted(bw & ent_code)))
            tally["recovered by internal name"] = tally.get("recovered by internal name", 0) + 1
        else:
            unknown.append((u, b, ent_code))
            tally["still unknown"] = tally.get("still unknown", 0) + 1

    print("\n=== RECOVERED by internal name (%d) ===" % len(recovered))
    for u, b, shared in sorted(recovered, key=lambda r: r[0].get("id") or 0):
        print("  unit %-5s %-22r %-34s shared=%s"
              % (u.get("id"), (u.get("name") or ""), b, shared))

    print("\n=== STILL UNKNOWN (%d) ===" % len(unknown))
    for u, b, code in sorted(unknown, key=lambda r: r[0].get("id") or 0):
        print("  unit %-5s code=%-22r %-34s en=%r"
              % (u.get("id"), (u.get("name") or "")[:22], b,
                 (en.get(u.get("_dll_name")) or "")[:24]))

    # control: does the internal-name test misfire on non-buildings?
    hits, total = 0, 0
    for u in rows:
        if u.get("type") == 80:
            continue
        b = sec("Buildings", u["icon_id"])
        if not b:
            continue
        total += 1
        if mat_words(b) & words(u.get("name") or ""):
            hits += 1
    print("\nCONTROL, internal-name test on non-buildings: %d / %d = %.1f%%"
          % (hits, total, 100.0 * hits / max(1, total)))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

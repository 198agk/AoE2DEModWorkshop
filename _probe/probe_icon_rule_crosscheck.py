# -*- coding: utf-8 -*-
"""probe_icon_rule_crosscheck.py -- is the rule right, or merely total?

probe_icon_rule_final.py reports "1344 / 1344 got the section the record points
at" -- but that is a tautology: 652 icon_ids exist in BOTH sections, so a rule
that always asks for the section that exists always scores 100%.  Covering every
row is not the same as picking the right picture.

The independent witness is the MATERIAL NAME in the Buildings section.  It says
what the picture depicts (`BuildingIcons028TownCenter`), and it is written for the
build menu.  So:

  * if the Buildings name shares a word with the entity's English name, the
    Buildings entry plausibly depicts that entity  -> rule should say Buildings;
  * if it shares nothing, the Buildings entry belongs to some other thing
    (`BuildingIcons028TownCenter` under a Trebuchet) -> the entity cannot be
    served from Buildings.

Prints the 2x2 of (rule says / name witness says) and every clash.
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

_MAT_RE = re.compile(r"^(?:Building|Unit|Icon)icons?(\d+)(.*)$", re.I)
_STOP = {"icon", "icons", "building", "buildings", "unit", "units", "the", "of",
         "and", "a", "b", "full", "empty", "no", "new", "old"}


def words(text):
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    # Digits separate words too: "Icons002Barracks1" is three words, not one.
    # Without this, `iconsbarracks` matched nothing and 81 correct buildings were
    # reported as "the name is about something else" -- a tokenizer bug wearing
    # the costume of a finding.
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    out = set()
    for w in s.split():
        w = w.strip().lower()
        if len(w) >= 3 and w not in _STOP:
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

    def prods(u):
        return [e.get("unit_id") for e in (u.get("train_locations") or [])]

    def rule(u):
        ps = prods(u)
        if any(p == BUILDER for p in ps):
            return "Buildings"
        return "Units"

    def witness(u):
        """What the Buildings material name claims, when both sections exist."""
        key = "%03d" % u["icon_id"]
        m = bld_sec.get(key)
        if not m:
            return "no-buildings-entry"
        name = en.get(u.get("_dll_name")) or ""
        if len(words(name)) < 1:
            return "unnamed"
        return "names-it" if (words(m) & words(name)) else "other-thing"

    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    both = [u for u in rows
            if ("%03d" % u["icon_id"]) in bld_sec
            and ("%03d" % u["icon_id"]) in units_sec]
    print("icon rows %d, ids in BOTH sections %d" % (len(rows), len(both)))

    table = {}
    for u in both:
        table[(rule(u), witness(u))] = table.get((rule(u), witness(u)), 0) + 1
    print("\n(rule, name witness) over the rows where BOTH sections exist:")
    for k in sorted(table, key=lambda k: (k[0], k[1])):
        print("  rule=%-9s witness=%-18s %4d" % (k[0], k[1], table[k]))

    suspicious = [u for u in both
                  if rule(u) == "Buildings" and witness(u) in ("other-thing",)]
    print("\n=== rule says Buildings, the Buildings name is about something else: %d ==="
          % len(suspicious))
    for u in sorted(suspicious, key=lambda u: u.get("id") or 0)[:40]:
        key = "%03d" % u["icon_id"]
        print("  unit %-5s icon=%-4s %-24r buildings=%-28s prods=%s"
              % (u.get("id"), u["icon_id"],
                 (en.get(u.get("_dll_name")) or "")[:24], bld_sec.get(key), prods(u)))

    named = [u for u in both if rule(u) == "Units" and witness(u) == "names-it"]
    print("\n=== rule says Units, but the Buildings name names the entity: %d ==="
          % len(named))
    for u in sorted(named, key=lambda u: u.get("id") or 0)[:40]:
        key = "%03d" % u["icon_id"]
        print("  unit %-5s icon=%-4s %-24r buildings=%-28s prods=%s"
              % (u.get("id"), u["icon_id"],
                 (en.get(u.get("_dll_name")) or "")[:24], bld_sec.get(key), prods(u)))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

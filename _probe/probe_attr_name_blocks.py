# -*- coding: utf-8 -*-
"""Does the game name the attribute ids AGE cannot?

probe_unnamed_attributes.py found two blocks whose first entries look like
AGE's attribute table:
    12200 'Hit Points'  12201 'Line of Sight'  12202 'Garrison Capacity'
    12205 'Movement Speed'          <- base 12200 + attribute id
    42020 'Selected Object'  42021 'Hit Points'  42024 'Attacks'
    42025 'Armors'  42026 'Range'  42027 'Monk Faith'   <- base 42017?

AGE names 89 of 0..115 and the 11 gaps are 81, 118, 119, 125, 126, 127, 130,
145, 146, 147, 158.  If either block names them, those 160 refused commands
become editable with a data file only -- no logic change.
"""
import os
import sys
import io
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402

tk = A.open_toolkit()
TABLES = C.load_effect_tables()
ATTRS = {int(k): v for k, v in ((TABLES.get("attributes") or {}).get("attributes") or {}).items()}

MISSING = [81, 118, 119, 125, 126, 127, 130, 145, 146, 147, 158]
ALL_IDS = sorted(set(list(ATTRS) + MISSING))
LO, HI = min(ALL_IDS), max(ALL_IDS)

LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')


def load(locale):
    p = os.path.join(tk.game_root, "resources", locale, "strings", "key-value",
                     "key-value-strings-utf8.txt")
    out = {}
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


en = load("en")
zh = load("zh")
print("en strings %d | attribute ids AGE names %d | missing %d"
      % (len(en), len(ATTRS), len(MISSING)))

# ---- candidate bases: find every base where a KNOWN attribute lands on the
# right name.  Anchor on ids 0/1/5 which are unambiguous.
ANCHORS = {0: "hit point", 1: "line of sight", 5: "movement speed",
           2: "garrison cap"}
anchs = [i for i, v in ANCHORS.items() if i in ATTRS]
bases = []
for sid, val in en.items():
    for off, want in ANCHORS.items():
        if sid - off >= 0:
            v = en.get(sid) or ""
            pass
# cheaper: for each candidate base, check the anchors
for base in range(0, 60000):
    hit = 0
    for off, want in ANCHORS.items():
        v = en.get(base + off)
        if v and want in v.lower():
            hit += 1
    if hit >= 3:
        bases.append(base)
print("candidate bases (>=3 of 4 anchors match): %s" % bases[:20])

for base in bases:
    print("")
    print("=" * 78)
    print("BASE %d" % base)
    named = 0
    for aid in ALL_IDS:
        g = en.get(base + aid)
        age = ATTRS.get(aid)
        if aid in MISSING:
            mark = "  <<< MISSING from AGE"
        else:
            mark = ""
        same = ""
        if g and age:
            same = "  SAME" if g.strip().lower().replace(" ", "") == age.strip().lower().replace(" ", "") else "  DIFFERS"
        print("   %3d  AGE=%-34s GAME=%-34s ZH=%-24s%s%s"
              % (aid, str(age)[:34], str(g)[:34], str(zh.get(base + aid))[:24], same, mark))
        if g:
            named += 1
    print("   named by game: %d of %d ids" % (named, len(ALL_IDS)))
    got = [a for a in MISSING if en.get(base + a)]
    print("   MISSING ids the game names: %s" % got)

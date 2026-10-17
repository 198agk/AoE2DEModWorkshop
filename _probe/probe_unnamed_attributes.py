# -*- coding: utf-8 -*-
"""The 160 commands refused for a MISSING LABEL rather than a missing feature.

probe_refusal_reasons.py split the refusals into two kinds and only the first
(1,585 "type not in the operation table") was addressed.  The other 160 say
"attribute id has no name": the attribute in slot C is not in AGE's 89-entry
table.  That is a DATA gap, not a code gap -- and if the GAME names those ids
the way it names the resource ids, 160 more commands become editable with no
logic change at all.

So: what are they, and does the game name them?
"""
import os
import sys
import collections
import re
import io

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402
from aoe2mod.semantic.index import index as semantic_index  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
raw = tk._raw
tail, gv = tk._parsed[4], tk._parsed[3]
techs = L.locate_techs(raw, tail, gv)
effects, _ = L.locate_effects(raw)
ix = semantic_index()
TABLES = C.load_effect_tables()
ATTRS = (TABLES.get("attributes") or {}).get("attributes") or {}

WANT = [81, 118, 119, 125, 126, 127, 130, 145, 146, 147, 158]


def tech_name(tid):
    try:
        tid = int(tid)
    except (TypeError, ValueError):
        return "?%r" % (tid,)
    e = ix.get("tech", tid)
    internal = techs[tid].get("name") if 0 <= tid < len(techs) else None
    return "%s [%s]" % ((e.display if e is not None else "?"), (internal or "")[:34])


def fnum(x):
    return int(x) if isinstance(x, float) and float(x).is_integer() else x


seen = collections.defaultdict(list)
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for ci, c in enumerate(effects[eid].get("commands") or ()):
        cc = c.get("c")
        if cc in WANT and c.get("type") in (0, 4, 5, 10, 14, 15, 20, 24, 25,
                                            30, 34, 35, 40, 44, 45, 200, 201,
                                            202, 203, 204, 205):
            seen[cc].append((ti, ci, t, c))

print("=" * 78)
for aid in WANT:
    items = seen.get(aid) or []
    if not items:
        print("attr %-4d  (no live command)" % aid)
        continue
    types = collections.Counter(c.get("type") for _, _, _, c in items)
    vals = sorted({fnum(c.get("d")) for _, _, _, c in items},
                  key=lambda v: (v is None, v))[:12]
    print("")
    print("attr %-4d  %d commands  types %s" % (aid, len(items), dict(types)))
    print("   d values %s" % vals)
    owners = collections.Counter(ti for ti, _, _, _ in items)
    for oti, n in owners.most_common(6):
        print("      tech[%d] %-48s x%d" % (oti, tech_name(oti)[:48], n))
    # what does the target (slot A / B) look like on these rows -- that is the
    # only clue to the attribute's meaning when its name is missing
    print("   slot b: %s" % collections.Counter(c.get("b") for _, _, _, c in items).most_common(6))
    print("   slot a sample: %s" % [c.get("a") for _, _, _, c in items[:6]])

# ------------------------------------------------------------------ naming
print("")
print("=" * 78)
print("does the GAME name them?  (string id = base + attribute id)")
root = tk.game_root
for base in (15000, 16000, 17000, 18000, 19000, 20000, 15500, 22000, 23000,
             24000, 25000, 26000, 10000, 11000, 12000, 13000, 14000):
    rel = os.path.join("resources", "en", "strings", "key-value",
                       "key-value-strings-utf8.txt")
    pass

STR = os.path.join(root, "resources", "en", "strings", "key-value",
                   "key-value-strings-utf8.txt")
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')
strings = {}
with io.open(STR, encoding="utf-8", errors="replace") as fh:
    for ln in fh:
        m = LINE.match(ln)
        if m:
            strings[int(m.group(1))] = m.group(2)
print("en strings: %d" % len(strings))

# for every plausible base, ask: do the WANT ids all land in the table, and does
# a KNOWN attribute (0 Hit Points, 1 Line of Sight) land on a name that says so?
KNOWN = {0: "hit point", 1: "line of sight", 9: "search radius"}
for base in range(15000, 30001, 100):
    ok = 0
    for aid, want in KNOWN.items():
        v = strings.get(base + aid)
        if v and want in v.lower():
            ok += 1
    if ok >= 2:
        print("  candidate base %d : %d/3 known names match" % (base, ok))
        for aid in WANT:
            print("      +%d -> %d = %r" % (aid, base + aid, strings.get(base + aid)))

# direct: search the whole string file for any of the known attribute names and
# print the neighbourhood, in case the block is not at a round base
print("")
hits = [i for i, v in strings.items() if v.strip().lower() == "hit points"]
print("exact 'Hit Points' ids: %s" % hits[:10])
for h in hits[:3]:
    print("   neighbourhood of %d:" % h)
    for i in range(h - 3, h + 8):
        if i in strings:
            print("      %d = %r" % (i, strings[i]))

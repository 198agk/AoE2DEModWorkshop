# -*- coding: utf-8 -*-
"""Does linkedTechs.json carry data the `.dat` CANNOT express?

`probe_linkedtechs.py` showed the base game's own `linkedTechs.json` holds 20
records of `{NameId, Comment, Local, Type, Techs}`, and that its `Type` values
(`MutuallyExclusive`, `Toggleable`, `Cycle`) are the exact vocabulary that sits
next to `linkedTechs.json` in the exe string pool.

Two questions decide whether this file is real data or a cache:

  Q1  does `NameId` resolve in the game's string tables?  If yes, the file
      supplies a DISPLAY NAME, which is presentation data the `.dat` has no
      room for.
  Q2  do the `Techs` groups match the `.dat`'s own mutually-exclusive layer
      (effect command type 102, "Disable Tech")?  If they match, the `.dat`
      implements the MECHANIC and this file supplies the GROUPING, so neither
      is a cache of the other.

A `.dat` has one tech record per tech and no notion of "these three are one
either/or group with a shared name" -- that is exactly the shape this file has.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import re
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT_REL = os.path.join("resources", "_common", "dat")

FAILURES = []

def check(cond, label):
    print("[%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILURES.append(label)

# ---- all string tables, merged (we learned there are many) -----------------
STR_DIR = os.path.join(GAME, "resources", "en", "strings", "key-value")
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')
strings = {}
for fn in sorted(os.listdir(STR_DIR)):
    p = os.path.join(STR_DIR, fn)
    if not os.path.isfile(p):
        continue
    with open(p, "r", encoding="utf-8-sig", errors="replace") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                strings[int(m.group(1))] = m.group(2)
print("en strings merged : %d ids from %d files" %
      (len(strings), len([f for f in os.listdir(STR_DIR)
                          if os.path.isfile(os.path.join(STR_DIR, f))])))

with open(os.path.join(GAME, DAT_REL, "linkedTechs.json"), "rb") as fh:
    base = json.loads(fh.read().decode("utf-8-sig"))
recs = base["LinkedTechs"]

print()
print("=" * 76)
print("Q1 -- does NameId resolve to localized text?")
print("=" * 76)
hit = 0
for r in recs:
    nid = r["NameId"]
    s = strings.get(nid)
    if s:
        hit += 1
    print("    NameId %-9s -> %-34r  Type=%s" %
          (nid, s if s else "(NOT IN ANY STRING TABLE)", r.get("Type")))
print("    NameIds that resolve : %d / %d" % (hit, len(recs)))
check(hit > 0, "NameId resolves in the game's string tables")

print()
print("=" * 76)
print("Q2 -- do the Techs groups match the .dat's type-102 disable layer?")
print("=" * 76)
sys.path.insert(0, _HERE_PATH(".."))
import aoe2mod.api as A
from aoe2mod.dat import locate as L

tk = A.open_toolkit()
tk._ensure()
techs = tk._tech_records()
effects = tk._effect_records()

# build: carrier tech -> set of techs it disables (type 102)
#
# SLOT: verified against a real row, not guessed.  tech 1195 (Economic Satrapy)
# carries `type=102 a=-1 b=-1 c=-1 d=1196.0`, so the DISABLED TECH ID is in
# slot D, and it arrives as a FLOAT.  Reading `row["a"]` instead found nothing
# and would have "proven" the file matches nothing.
disables = {}
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if not isinstance(eid, int) or eid < 0 or eid >= len(effects):
        continue
    for row in effects[eid]["commands"]:
        if row["type"] == 102:
            tgt = row["d"]
            if isinstance(tgt, float) and tgt == int(tgt) and tgt >= 0:
                disables.setdefault(ti, set()).add(int(tgt))

# the .dat's mutual pairs
mutual = set()
for a, bs in disables.items():
    for b in bs:
        if b in disables and a in disables.get(b, ()):
            mutual.add((min(a, b), max(a, b)))
print("    carrier techs with a type-102 : %d" % len(disables))
print("    mutual pairs in the .dat      : %d" % len(mutual))

print()
by_type = {}
tot_g = tot_m = 0
for r in recs:
    techs_g = r["Techs"]
    pairs = 0
    for i in range(len(techs_g)):
        for j in range(i + 1, len(techs_g)):
            a, b = techs_g[i], techs_g[j]
            tot_g += 1
            if (min(a, b), max(a, b)) in mutual:
                pairs += 1
    tot_m += pairs
    t = r.get("Type", "?")
    acc = by_type.setdefault(t, [0, 0, 0])
    acc[0] += 1
    acc[1] += len(techs_g) * (len(techs_g) - 1) // 2
    acc[2] += pairs
    print("    %-38s %-17s n=%-2d  pairs=%-2d  in .dat mutual=%-2d" %
          (r.get("Comment", "?")[:38], t, len(techs_g),
           len(techs_g) * (len(techs_g) - 1) // 2, pairs))
print()
print("    group pairs total                  : %d" % tot_g)
print("    ...that the .dat also marks mutual : %d" % tot_m)
print()
print("    by Type:")
for t, (n, g, m) in sorted(by_type.items()):
    print("        %-18s records=%-2d pairs=%-3d mutual=%-3d %s" %
          (t, n, g, m, "ALL" if g == m else ("NONE" if m == 0 else "PARTIAL")))
check(tot_g > 0, "the file groups techs into either/or sets")

# The decisive split: MutuallyExclusive groups must be exactly the .dat's
# mutual pairs, and Cycle groups must not be mutual at all.  If this holds,
# the two files carry DIFFERENT information about the same techs -- the .dat
# encodes "these two exclude each other", the JSON encodes "these N are one
# either/or cycle with this display name".
me = by_type.get("MutuallyExclusive")
cy = by_type.get("Cycle")
check(me is not None and me[1] > 0 and me[1] == me[2],
      "every MutuallyExclusive group is mutual in the .dat (%s)" %
      ("%d/%d" % (me[1], me[2]) if me else "absent"))
check(cy is not None and cy[2] == 0,
      "no Cycle group is mutual in the .dat (%s)" %
      ("%d/%d" % (cy[2], cy[1]) if cy else "absent"))

print()
if FAILURES:
    print("FAILURES: %d" % len(FAILURES))
    for f in FAILURES:
        print("  - %s" % f)
    sys.exit(1)
print("LINKED-TECHS SEMANTICS: the file names the either/or groups and the .dat")
print("implements them -- neither is a cache of the other.")

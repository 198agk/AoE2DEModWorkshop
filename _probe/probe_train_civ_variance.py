# -*- coding: utf-8 -*-
r"""Is the .dat's train_locations really the SAME for every civ?  Then pin the model.

Section B of `probe_panel_vs_dat_train.py` compared panel entries against the
training buildings read from civ index 0 (Gaia).  That is only valid if the array
does not vary by civilization.  Earlier work checked two civs by hand
(`probe_train_location_content.py`: Goths and British identical); measure it across
all 63 before basing a conclusion on it.

Gaia is the one civ known to differ (it carries 529 extra eyecandy units), so it is
the worst choice as a representative -- verify or switch to a playable civ.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
civs = tk._parsed[1]
print("civs: %d   first = %r   last = %r"
      % (len(civs), civs[0].get("name"), civs[-1].get("name")))


def train_map(civ):
    out = {}
    for u in civ.get("units") or []:
        uid = u.get("id")
        if uid is None:
            continue
        bs = tuple(sorted(t.get("unit_id") for t in (u.get("train_locations") or [])
                          if t.get("unit_id") is not None and t.get("unit_id") >= 0))
        out[uid] = bs
    return out


maps = [train_map(c) for c in civs]
base = maps[0]
diffs = []
for i, m in enumerate(maps):
    if m == base:
        continue
    shared = set(m) & set(base)
    changed = {k for k in shared if m[k] != base[k]}
    diffs.append((i, civs[i].get("name"), len(m), len(changed),
                  sorted(changed)[:6]))
print()
print("civs whose train_locations map differs from civ[0] (Gaia): %d" % len(diffs))
for i, nm, n, nch, sample in diffs[:12]:
    print("   civ[%d] %-14s units=%-5d differing ids=%-4d %s"
          % (i, nm, n, nch, sample))

# Which civs agree with each other?  Group by the map's fingerprint.
from collections import Counter                                # noqa: E402
fp = Counter()
for m in maps:
    fp[hash(tuple(sorted((k, v) for k, v in m.items())))] += 1
print()
print("distinct train_locations maps across all 63 civs: %d" % len(fp))
print("   group sizes: %s" % sorted(fp.values(), reverse=True)[:10])

# The practical question: does choosing Gaia instead of a playable civ change the
# answer for the SUBJECTS?
g = train_map(civs[0])
b = train_map(civs[1])       # first playable civ
print()
print("civ[1] = %r" % civs[1].get("name"))
for uid in (77, 473, 567, 359, 532, 691, 588, 13, 5, 74, 2550):
    gg, bb = g.get(uid), b.get(uid)
    mark = "SAME" if gg == bb else "*** DIFFERS ***"
    print("   unit %-6s gaia=%-14s playable=%-14s %s" % (uid, gg, bb, mark))

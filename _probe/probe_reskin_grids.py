"""Before shipping a reskin, check the thing that fails SILENTLY.

Copying the donor's .sld over the target's NAME means the game reads a file whose
own frame/angle grid is the donor's.  The graphics record for the target still
says the TARGET's frame_count/angle_count, and the survey of this layer found
that a frame-count mismatch "plays the wrong frames rather than erroring".  A
garbled sprite would not cleanly answer "does a loose .sld override the packed
one", so the test subject has to be a pair whose grids line up.

Prints, per candidate pair: for every shared animation, (frames, angles) on the
donor vs the target, and whether they are equal.
"""
import os
import collections
import aoe2mod.api as A
from aoe2mod.game import sprites as S

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]
graphics = tk._stats["graphics"]
by_id = {g["id"]: g for g in graphics}

# The record for a unit's STANDING graphic, so the grid can be read per animation.
def rec_for_file(fname):
    """Every graphics record naming this .sld (there can be more than one)."""
    out = []
    for g in graphics:
        f = (g.get("file") or "").strip()
        if f == fname:
            out.append(g)
    return out


def grids(art):
    """{animation: (frame_count, angle_count)} for the files this art uses."""
    out = {}
    for anim, fname in sorted((art.get("tokens") or {}).items()):
        recs = rec_for_file(fname)
        if not recs:
            out[anim] = None
            continue
        out[anim] = sorted({(r.get("frame_count"), r.get("angle_count")) for r in recs})
    return out


def unit_of(uid):
    for c in civs:
        for u in c["units"]:
            if u["id"] == uid:
                return u
    return None


CANDIDATES = [
    (83, "Villager (male)", 594, "Sheep"),
    (83, "Villager (male)", 93, "Spearman"),
    (83, "Villager (male)", 293, "Villager (female)"),
    (83, "Villager (male)", 4, "Archer"),
    (83, "Villager (male)", 74, "Militia"),
    (4, "Archer", 83, "Villager (male)"),
    (4, "Archer", 594, "Sheep"),
    (93, "Spearman", 74, "Militia"),
]

for tid, tname, did, dname in CANDIDATES:
    ta = idx.art(unit_of(tid))
    da = idx.art(unit_of(did))
    tg = grids(ta)
    dg = grids(da)
    shared = sorted(set(tg) & set(dg))
    print("=== %s (unit %d)  <-  %s (unit %d) ===" % (tname, tid, dname, did))
    bad = []
    for anim in shared:
        same = tg[anim] == dg[anim]
        if not same:
            bad.append(anim)
        print("   %-10s target=%-22s donor=%-22s %s"
              % (anim, tg[anim], dg[anim], "OK" if same else "MISMATCH"))
    only_t = sorted(set(tg) - set(dg))
    if only_t:
        print("   target-only (keeps its own picture): %s" % only_t)
    print("   -> %d/%d animations fit%s"
          % (len(shared) - len(bad), len(shared),
             "" if not bad else "   MISMATCHED: %s" % bad))
    print()

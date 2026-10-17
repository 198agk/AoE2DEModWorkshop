# -*- coding: utf-8 -*-
"""The nine t50 / unit fields the locator reads but records no offset for.

Five are already converted into named t50 dict entries (projectile_unit_id,
accuracy, frame_delay, min_range, attack_graphic) and four more are read with
a bare r.u8()/r.f32() and never named at all (BreakOffCombat,
BlastAttackLevel, AccuracyDispersion, AttackGraphic2... -- see the walker).

The point of this probe is NOT to expose them all.  It is to answer the only
question that matters before adding an intent: does this field carry signal a
player could want to change, and is its value safe to write?  A field that is
constant, sentinel-valued, or structurally dangerous must NOT become an
intent no matter how easy it is to bind.

Read-only against BASE.
"""
import collections
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from aoe2mod.dat import parser as P      # noqa: E402
from aoe2mod.dat import locate as L      # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

T50_FIELDS = ["projectile_unit_id", "accuracy", "frame_delay",
              "min_range", "attack_graphic"]


def summarize(name, values):
    vals = [v for v in values if v is not None]
    if not vals:
        print("  %-22s NO VALUES" % name)
        return
    c = collections.Counter(vals)
    distinct = len(c)
    top = c.most_common(4)
    print("  %-22s n=%6d distinct=%4d  top=%s"
          % (name, len(vals), distinct, top))


def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)

    units = [u for cv in civs for u in cv["units"]]
    print("=== t50 fields that are read but unbound ===")
    print("(n = records that carry a type50 block; %d total unit objects)"
          % len(units))

    # Only records whose values vary can carry intent.  Count per field over
    # the units that actually have a type50 AND the key.
    buckets = {f: [] for f in T50_FIELDS}
    for u in units:
        t = u.get("type50")
        if not t:
            continue
        for f in T50_FIELDS:
            if f in t:
                buckets[f].append(t[f])
    for f in T50_FIELDS:
        summarize(f, buckets[f])

    print()
    print("=== is the value ever NON-default? ===")
    # The C++ defaults from Type50.h: ProjectileUnitID=-1, AccuracyPercent=0,
    # FrameDelay=0, MinRange=0, AttackGraphic=-1.  A field whose values are
    # ALL the default is a dead field.
    defaults = {"projectile_unit_id": -1, "accuracy": 0, "frame_delay": 0,
                "min_range": 0.0, "attack_graphic": -1}
    for f in T50_FIELDS:
        vals = buckets[f]
        d = defaults[f]
        nd = sum(1 for v in vals if v != d)
        print("  %-22s default %-6s non-default %6d / %6d  (%.1f%%)"
              % (f, d, nd, len(vals), 100.0 * nd / max(1, len(vals))))

    print()
    print("=== min_range specifically: who is non-zero? ===")
    nz = []
    for cv in civs:
        for u in cv["units"]:
            t = u.get("type50")
            if t and t.get("min_range"):
                nz.append((u.get("id"), u.get("name"), t["min_range"]))
    seen = {}
    for i, n, v in nz:
        seen.setdefault(i, (n, v))
    print("  distinct unit ids with non-zero min_range: %d" % len(seen))
    for i in sorted(seen)[:25]:
        print("    id %-6d %-24s min_range=%s" % (i, seen[i][0], seen[i][1]))

    print()
    print("=== accuracy: distribution over non-zero ===")
    nzacc = collections.Counter()
    for cv in civs:
        for u in cv["units"]:
            t = u.get("type50")
            if t and t.get("accuracy"):
                nzacc[t["accuracy"]] += 1
    print("  distinct accuracy values: %s" % sorted(nzacc)[:40])

    print()
    print("=== projectile_unit_id: most common targets ===")
    pc = collections.Counter()
    for cv in civs:
        for u in cv["units"]:
            t = u.get("type50")
            if t and t.get("projectile_unit_id", -1) != -1:
                pc[t["projectile_unit_id"]] += 1
    print("  distinct: %d  top: %s" % (len(pc), pc.most_common(10)))


if __name__ == "__main__":
    main()

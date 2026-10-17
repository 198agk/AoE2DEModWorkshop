# -*- coding: utf-8 -*-
"""Is `garrison_capacity` a field a player could want, and is it safe?

It is the motivating case for reading the schema's `signed` flag: it is the
first declared-but-unsigned field (a uint8), and every write path today packs
with `signed=True` unconditionally -- fine while all six int fields happen to be
signed, silently wrong the moment one is not.

Two questions, same as always: SIGNAL, and SAFETY.

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


def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, gv, tail = L.locate(data, parser=p)

    print("=== garrison_capacity over every record ===")
    c = collections.Counter()
    bytype = collections.defaultdict(collections.Counter)
    for cv in civs:
        for u in cv["units"]:
            if "garrison_capacity" not in u:
                continue
            v = u["garrison_capacity"]
            c[v] += 1
            bytype[u["type"]][v] += 1
    print("  distinct %d | histogram %s" % (len(c), sorted(c.items())))
    print("  max value: %d" % max(c))
    print()
    print("=== which unit types carry a non-zero capacity? ===")
    for t in sorted(bytype):
        nz = {v: n for v, n in bytype[t].items() if v}
        if nz:
            print("  type %-3d  %s" % (t, sorted(nz.items())))
    print()
    print("=== by id: distinct non-zero ids ===")
    seen = {}
    for cv in civs:
        for u in cv["units"]:
            v = u.get("garrison_capacity")
            if v:
                seen.setdefault(u.get("id"), (u.get("name"), u.get("type"), v))
    print("  distinct ids with capacity > 0: %d" % len(seen))
    for i in sorted(seen)[:30]:
        n, t, v = seen[i]
        print("    id %-6d type %-3d cap %-4d %s" % (i, t, v, n))
    print()
    print("=== is the field reachable in every civ (the 63-duplication trap)? ===")
    per_civ = collections.Counter()
    for cv in civs:
        per_civ[sum(1 for u in cv["units"] if u.get("garrison_capacity"))] += 1
    print("  records-with-the-key per civ: %s" % dict(per_civ))
    print()
    print("=== control: is ANY record's u8 in the 128..255 range? ===")
    # If any is, packing with signed=True would raise OverflowError the moment
    # it is written -- proof the flag is load-bearing rather than theoretical.
    hi = [(u.get("id"), u.get("name"), u["garrison_capacity"])
          for cv in civs for u in cv["units"]
          if u.get("garrison_capacity", 0) > 127]
    print("  records with a value > 127: %d" % len(hi))
    print("  sample: %s" % hi[:10])


if __name__ == "__main__":
    main()

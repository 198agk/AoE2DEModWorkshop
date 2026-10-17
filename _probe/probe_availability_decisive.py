# -*- coding: utf-8 -*-
"""Decisive: can a per-record byte express "Goths build Huskarl, Britons don't"?

Two candidate mechanisms for per-civ unit availability were measured and neither
fits:
  * the record's `Enabled`/`Disabled` u8 pair (probe_unit_availability.py: 2,690
    of 2,693 ids carry the SAME value in all 63 civs);
  * effect command type 2 (probe_availability_owner.py: 92 of 192 commands sit on
    a tech with `civ == -1`, i.e. they are GLOBAL toggles).

This file settles it by direct comparison: take two civs with very different
buildable sets and count (a) how many unit ids carry a different record byte,
versus (b) how many unit ids the game's own per-civ data assigns to one and not
the other.  If (b) is dozens and (a) is ~0, no per-record byte can be the
mechanism and the product must not promise "flip a flag to let civ X build Y".
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FU = os.path.join(GAME, "resources", "_common", "dat",
                  "futuravailableunits.json")
REL = {"hide_in_editor": 4, "enabled": 7, "disabled": 8}


def recursive_ids(obj, out):
    """Collect every ID under any nesting -- 'Buildings' rows nest 'Units'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "ID" and isinstance(v, int):
                out.add(v)
            else:
                recursive_ids(v, out)
    elif isinstance(obj, list):
        for x in obj:
            recursive_ids(x, out)
    return out


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    civs = tk._civs
    with open(FU, encoding="utf-8") as fh:
        fu = json.load(fh)

    # civ name in the .dat -> key in futuravailableunits (they differ: dat says
    # "British", the JSON says "Britons").
    alias = {"British": "Britons", "French": "Franks", "Byzantine": "Byzantines",
             "Mayan": "Mayans", "Hindustanis": "Indians", "Magyars": "MAGYAR"}

    def fu_ids(civ_name):
        key = alias.get(civ_name, civ_name)
        if key not in fu:
            return None
        return recursive_ids(fu[key], set())

    # byte vectors
    def bytevec(name):
        ci = [i for i, c in enumerate(civs) if c.get("name") == name][0]
        out = {}
        for u in (civs[ci].get("units") or ()):
            b = (u.get("_offs") or {}).get("sort_number")
            if b is None:
                continue
            out[u.get("id")] = tuple(raw[b + REL[k]] for k in
                                     ("enabled", "disabled", "hide_in_editor"))
        return out

    for a_name, b_name in (("British", "Goths"), ("Aztecs", "Goths"),
                           ("British", "Aztecs")):
        va, vb = bytevec(a_name), bytevec(b_name)
        shared = set(va) & set(vb)
        byte_diff = [i for i in shared if va[i] != vb[i]]
        ia, ib = fu_ids(a_name), fu_ids(b_name)
        if ia is None or ib is None:
            print("%s vs %s: futuravailableunits key missing (%s / %s)"
                  % (a_name, b_name, a_name in fu, b_name in fu))
            continue
        only_a = ia - ib
        only_b = ib - ia
        print("%-9s vs %-9s  shared ids %d" % (a_name, b_name, len(shared)))
        print("    record bytes that DIFFER            : %d   %s"
              % (len(byte_diff), byte_diff[:10]))
        print("    ids only %-9s can have (game data) : %d" % (a_name, len(only_a)))
        print("    ids only %-9s can have (game data) : %d" % (b_name, len(only_b)))
        print()
    print("VERDICT: if the 'ids only X can have' counts are far larger than the")
    print("'record bytes that DIFFER' count, no per-record byte governs")
    print("availability, and 'flip a flag to unlock a unit for a civ' is NOT a")
    print("mechanism this .dat exposes -- do not promise it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Human-reviewable table of the objreplacement merge.

`probe_objreplacement_family.py` proves the merge changes 5 families.  This
probe prints them NAME BY NAME so the change can be reviewed by a human before
any product code is touched, and cross-checks the villager claim against the
game's own `linkedUnits.json`.

The question being answered: is each proposed merge semantically "one object in
two runtime states", or is it two genuinely different objects that happen to be
swapped?  Only the first deserves to be one family.
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WK = os.path.dirname(HERE)
sys.path.insert(0, WK)

from aoe2mod import api as A                    # noqa: E402
from aoe2mod.dat import families as F           # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")


def main():
    tk = A.open_toolkit()
    tk._ensure()
    civs = tk._civs
    root = tk.game_root

    names = json.load(io.open(os.path.join(WK, "aoe2mod", "semantic", "data",
                                           "unit_names.json"),
                              encoding="utf-8"))
    techtree = json.load(io.open(os.path.join(WK, "aoe2mod", "semantic", "data",
                                              "tech_names.json"),
                                 encoding="utf-8"))

    def nm(i):
        n = names.get(str(i)) or {}
        return "%s / %s" % (n.get("en"), n.get("zh"))

    by_id = {}
    for c in civs:
        for u in c.get("units") or ():
            by_id.setdefault(u.get("id"), u)

    F.warm(tk._stats, tk.game_root)
    fam = F.build_families(civs)

    # Which civs offer each gating tech: the availability is per civ, and that
    # tells us how many players can ever see the swapped-in record.
    print("=== gating technologies (how many civs can ever see the swap) ===")
    for tech_id in (932, 940, 1353, 1142):
        civs_with = []
        for c in civs:
            for t in (c.get("techs") or ()):
                if t.get("id") == tech_id:
                    civs_with.append(c.get("name"))
                    break
        tn = techtree.get(str(tech_id)) or {}
        print("  tech %-5s %-28s civs=%d %s"
              % (tech_id, tn.get("internal"), len(civs_with),
                 civs_with[:8]))

    print("\n=== the 5 families objreplacement would change ===")
    proposals = [
        ("Villager (Male) <-> Villager (Female)", "chance 50, both directions",
         [56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220,
          222, 259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334]),
        ("Town Center <-> Town Center (Packed)", "attribute Raider=82",
         [71, 109, 141, 142, 444]),
        ("Lumber Camp / Mining Camp <-> Mule Cart", "techs 932/940",
         [562, 563, 564, 565, 584, 585, 586, 587, 1808]),
        ("Mill <-> Settlement", "tech 1353",
         [68, 129, 130, 131, 2556, 2558, 2560]),
        ("Dock <-> Port", "tech 1142",
         [45, 47, 51, 133, 2141, 2142, 2143, 2172]),
    ]
    for title, why, ids in proposals:
        print("\n  %s   [%s]" % (title, why))
        for i in ids:
            u = by_id.get(i) or {}
            print("    %-5s type=%-3s hp=%-6s tsg=%-2s %s"
                  % (i, u.get("type"), u.get("hit_points"),
                     u.get("task_swap_group"), nm(i)))

    # Cross-check: what does the GAME itself call one object?
    print("\n=== linkedUnits.json, the game's own named assemblies ===")
    lu_path = os.path.join(root, DAT_REL, "linkedUnits.json")
    with io.open(lu_path, "rb") as fh:
        lu = json.loads(fh.read().decode("utf-8-sig"))
    print("  top-level type: %s" % type(lu).__name__)
    entries = lu if isinstance(lu, list) else (lu.get("objects") or lu)
    if isinstance(entries, dict):
        entries = [dict(v, name=k) for k, v in entries.items()]
    for e in entries:
        if not isinstance(e, dict):
            continue
        label = e.get("name") or e.get("Name") or e.get("title")
        ids = e.get("ids") or e.get("IDs") or e.get("units") or []
        if not ids:
            continue
        low = sum(1 for i in ids if (by_id.get(i) or {}).get("task_swap_group"))
        print("  %-22s n=%-3d nonzero_tsg=%-3d both_sexes=%s"
              % (label, len(ids), low,
                 (83 in ids and 293 in ids)))
        if 83 in ids or 293 in ids:
            print("      ids: %s" % (sorted(ids),))

    print("\n=== villager: is the female record really used at runtime? ===")
    for i in (83, 293):
        u = by_id.get(i) or {}
        print("  %-5s %-22s graphic=%s train_locations=%s"
              % (i, nm(i), u.get("standing_graphic") or u.get("graphic"),
                 (u.get("train_locations") or [])[:1]))
    # A record that the engine swaps INTO must have art, or the swap would be
    # invisible; check the decisive ones.
    print("\n  art presence on the swapped-in records:")
    for i in (293, 444, 1808, 2172, 2556, 2560, 2558):
        u = by_id.get(i) or {}
        g = u.get("graphic")
        gs = tk._stats.get("graphics") or []
        has = isinstance(g, int) and 0 <= g < len(gs) and bool(gs[g])
        print("    %-5s graphic_id=%-7s art_present=%s  %s"
              % (i, g, has, nm(i)))


if __name__ == "__main__":
    main()

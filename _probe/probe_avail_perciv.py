# -*- coding: utf-8 -*-
"""Per-unit confirmation: does CivTechTrees' Node Status track real buildability?

The aggregate comparison left a loose end -- `CivTechTrees`' unit rows are a
SUBSET of futuravailableunits' ids (2378 agree, 2 disagree), so "agrees" alone
does not prove which field the engine reads.  This file asks the sharpest
available question instead, on units whose per-civ availability is well known:

    Huskarl (41)   Goths only
    Longbowman (8) Britons only
    Jaguar Warrior (725) Aztecs only
    Tarkan (755)   Huns only

For each unit and each civ, print what BOTH the .dat record says and what
CivTechTrees says, so the two candidate mechanisms are visible side by side.  A
mechanism is only credible if it separates the owner civ from the others.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
DELTA_ENABLED = 7          # sort_number +7, proven by probe_unit_availability

PROBES = [(41, "Huskarl 哥特", ("GOTHS",)),
          (8, "Longbowman 不列颠", ("BRITONS",)),
          (725, "Jaguar 阿兹特克", ("AZTECS",)),
          (755, "Tarkan 匈奴", ("HUNS",))]


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    civs = tk._civs

    # dat byte per (civ index, unit id)
    dat_byte = {}
    dat_present = set()
    for ci, c in enumerate(civs):
        for u in (c.get("units") or ()):
            uid = u.get("id")
            dat_present.add((ci, uid))
            b = (u.get("_offs") or {}).get("sort_number")
            if b is not None:
                dat_byte[(ci, uid)] = raw[b + DELTA_ENABLED]

    # JSON status per (CIVFILE, unit id)
    json_status = {}
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        for e in j.get("civ_techs_units") or ():
            if not isinstance(e, dict):
                continue
            nid = e.get("Node ID")
            if nid is None:
                continue
            json_status.setdefault((fn[:-5], nid), set()).add(
                (e.get("Node Status"), e.get("Use Type")))

    print("%-22s %-11s %-14s %-9s %s"
          % ("unit (真实归属)", "civ", "dat Enabled", "in dat?",
             "CivTechTrees (Node Status, Use Type)"))
    print("-" * 100)
    for uid, tag, owners in PROBES:
        for fn in sorted(os.listdir(CT)):
            civ_key = fn[:-5]
            ci = [i for i, c in enumerate(civs)
                  if (c.get("name") or "").upper() == civ_key.upper()]
            ci = ci[0] if ci else None
            byte = dat_byte.get((ci, uid)) if ci is not None else None
            present = "yes" if (ci, uid) in dat_present else "NO"
            st = json_status.get((civ_key, uid))
            mark = "  <== OWNER" if civ_key in owners else ""
            if civ_key in owners or st is not None or byte == 0:
                print("%-22s %-11s %-14s %-9s %s%s"
                      % (tag if civ_key == sorted(os.listdir(CT))[0][:-5] else "",
                         civ_key, byte, present,
                         sorted(st) if st else "-- absent --", mark))
        print()

    # The separation test, computed rather than eyeballed.
    print("separation test -- does the field distinguish owner from everyone?")
    for uid, tag, owners in PROBES:
        owner_keys = set(owners)
        # dat: owner's byte vs the most common byte among non-owners
        ci_owner = [i for i, c in enumerate(civs)
                    if (c.get("name") or "").upper() in owner_keys]
        owner_bytes = {dat_byte.get((i, uid)) for i in ci_owner}
        other_bytes = {dat_byte.get((i, uid)) for i, c in enumerate(civs)
                       if i not in ci_owner}
        # json: does the owner have a ResearchedCompleted row the others lack?
        owner_rows = set()
        for k in owner_keys:
            owner_rows |= json_status.get((k, uid), set())
        print("  %-22s dat owner=%s others=%s | json owner=%s"
              % (tag, sorted(b for b in owner_bytes if b is not None),
                 sorted(b for b in other_bytes if b is not None),
                 sorted(owner_rows) or "absent"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

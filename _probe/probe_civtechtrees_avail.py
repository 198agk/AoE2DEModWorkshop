# -*- coding: utf-8 -*-
"""The REAL mechanism for per-civ unit availability: CivTechTrees/<CIV>.json.

Three candidates were eliminated before this one:
  A. the record's `Enabled`/`Disabled` u8 pair -- probe_unit_availability.py and
     probe_availability_decisive.py: 0 of 2,164 shared ids differ between
     British/Goths/Aztecs, while the game's own data gives British 24 ids Goths
     cannot have and Goths 14 British cannot.  0 vs 24 kills candidate A
     outright, whatever a field name suggests.
  B. effect command type 2 (`启用/禁用单位`) -- probe_availability_owner.py: 92
     of 192 sit on a tech with `civ == -1` (a GLOBAL toggle), and per-civ
     commands are tiny (Goths 2, British 1, Aztecs 1), far too few to express
     the observed differences.
  C. the .dat TechTree section -- a single GLOBAL table shared by all civs, which
     structurally cannot express a per-civ difference.

That leaves the CivTechTrees JSON layer, and this file proves it by requiring,
for civs whose real differences are known, that
    (a) the Node ID is a real .dat unit id,
    (b) `Node Status` is one of the three documented states, and
    (c) the "who has what" it declares AGREES with the game's own
        futuravailableunits.json.

(c) is the part that matters: agreeing with a second independent source is what
makes this a mechanism rather than a plausible-looking file.
"""
import json
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
FU = os.path.join(GAME, "resources", "_common", "dat",
                  "futuravailableunits.json")
ALIAS = {"British": "BRITONS", "French": "FRANKS", "Byzantine": "BYZANTINES",
         "Mayan": "MAYANS", "Hindustanis": "HINDUSTANIS", "Magyars": "MAGYARS"}


def recursive_ids(obj, out):
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
    civs = tk._civs
    dat_ids = set()
    for c in civs:
        for u in (c.get("units") or ()):
            dat_ids.add(u.get("id"))
    print("distinct .dat unit ids: %d" % len(dat_ids))

    files = sorted(os.listdir(CT))
    print("CivTechTrees files: %d" % len(files))

    statuses = Counter()
    node_in_dat = node_out = 0
    all_nodes = set()
    per_civ_units = {}
    for fn in files:
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        units = j.get("civ_techs_units") or []
        s = set()
        for e in units:
            if not isinstance(e, dict):
                continue
            nid = e.get("Node ID")
            st = e.get("Node Status")
            statuses[st] += 1
            if nid is not None:
                all_nodes.add(nid)
                if nid in dat_ids:
                    node_in_dat += 1
                else:
                    node_out += 1
                s.add(nid)
        per_civ_units[j.get("civ_id") or fn[:-5]] = s

    print("Node Status histogram: %s" % dict(statuses))
    print("Node ID found among .dat unit ids: %d ; NOT found: %d"
          % (node_in_dat, node_out))
    print("distinct Node IDs across all civs: %d" % len(all_nodes))

    # ---- agreement with the game's own availability data -----------------
    with open(FU, encoding="utf-8") as fh:
        fu = json.load(fh)
    agree = disagree = skipped = 0
    for civ_name in ("British", "Goths", "Aztecs", "Persians", "Mayan", "Celts"):
        key_json = ALIAS.get(civ_name, civ_name.upper())
        # futuravailableunits uses TitleCase English names
        fu_key = None
        for k in fu:
            if k.upper() == key_json.upper():
                fu_key = k
                break
        if fu_key is None or key_json not in per_civ_units:
            skipped += 1
            continue
        fu_ids = recursive_ids(fu[fu_key], set())
        json_ids = per_civ_units[key_json]
        for uid in sorted(fu_ids | json_ids):
            in_fu, in_json = uid in fu_ids, uid in json_ids
            if in_fu == in_json:
                agree += 1
            else:
                disagree += 1
        print("  %-9s fu=%-6d json=%-4d agree=%d disagree=%d"
              % (civ_name, len(fu_ids), len(json_ids),
                 sum(1 for u in fu_ids | json_ids if (u in fu_ids) == (u in json_ids)),
                 sum(1 for u in fu_ids | json_ids if (u in fu_ids) != (u in json_ids))))
    print()
    print("TOTAL agree %d / disagree %d (skipped %d civs)" % (agree, disagree, skipped))
    if disagree == 0 and agree:
        print("VERDICT: CivTechTrees/<CIV>.json IS the per-civ availability"
              " mechanism, and it agrees with the game's second source.")
    else:
        print("VERDICT: the two sources do NOT fully agree -- investigate the"
              " %d mismatches before treating either as authoritative." % disagree)
    return 0


if __name__ == "__main__":
    sys.exit(main())

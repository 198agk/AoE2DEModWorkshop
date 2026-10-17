# -*- coding: utf-8 -*-
"""Two questions the tech-row work must answer honestly.

1. Is the '+10000' name-id offset TECH-SPECIFIC, or do unit rows show it too?
   A unit row's `Name String ID` was always assumed to be the .dat record's
   LanguageDLLName.  If units are 1:1 and techs are +10000, that asymmetry is a
   fact worth writing down; if units are also offset, the semantic layer's whole
   mapping needs re-checking.  Measure both against the .dat.

2. Demonstrate the trap: `CT.node_status(tree, <tech id>)` returns None for every
   civ, which reads as "no civilization has Loom".  Show it, and show what the
   tech rows actually say.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import locate as L                              # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def tech_rows(tree):
    out = []
    for v in tree.values():
        if isinstance(v, list):
            for e in v:
                if isinstance(e, dict) and e.get("Use Type") == "Tech":
                    out.append(e)
    return out


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(GAME)

    # ---- 1a. unit rows: does Name String ID == the .dat unit's LanguageDLLName?
    civs = tk._civs
    agree = differ = 0
    samples = []
    for ci, civ in enumerate(civs):
        units = civ.get("units") or []
        for u in units:
            dll = u.get("_dll_name")
            if dll is None:
                continue
            stem = CT.civ_file_stem(civ.get("name"))
            tree = trees.get(stem)
            if tree is None:
                continue
            row = CT.row_for(tree, u.get("id"))
            if row is None or row.get("Name String ID") is None:
                continue
            if row.get("Name String ID") == dll:
                agree += 1
            else:
                differ += 1
                if len(samples) < 10:
                    samples.append((stem, u.get("id"), row.get("Name String ID"), dll))
    print("UNIT rows: Name String ID == .dat LanguageDLLName")
    print("  agree %d / differ %d" % (agree, differ))
    for s in samples:
        print("   %-14s unit=%-6d row=%-8s dat=%-8s delta=%s"
              % (s[0], s[1], s[2], s[3], (s[2] - s[3]) if s[2] and s[3] else "?"))

    # ---- 1b. tech rows for comparison
    trows = [(c, e) for c, t in trees.items() for e in tech_rows(t)]
    t_plus = t_same = t_other = 0
    import json
    with open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                           "tech_names.json"), encoding="utf-8") as fh:
        names = json.load(fh)
    for c, e in trows:
        rec = names.get(str(e.get("Node ID"))) or {}
        dat = rec.get("name_string_id")
        sid = e.get("Name String ID")
        if sid is None or dat is None:
            continue
        if sid == dat + 10000:
            t_plus += 1
        elif sid == dat:
            t_same += 1
        else:
            t_other += 1
    print("\nTECH rows: Name String ID vs .dat LanguageDLLName")
    print("  +10000: %d   equal: %d   neither: %d" % (t_plus, t_same, t_other))

    # ---- 2. the trap
    print("\nTHE TRAP -- CT.node_status() on a TECH id:")
    for nid, name in ((22, "Loom"), (249, "Hand Cart"), (101, "Feudal Age")):
        st = {c: CT.node_status(trees[c], nid) for c in trees}
        distinct = Counter(st.values())
        print("  id %-5d %-12s -> node_status() says %s"
              % (nid, name, dict(distinct)))
        real = Counter(e.get("Node Status") for _, e in trows if e.get("Node ID") == nid)
        print("            tech rows actually say %s" % dict(real))

    # ---- 3. how the tech rows behave once read correctly
    print("\nread as TECH rows:")
    for nid, name in ((22, "Loom"), (249, "Hand Cart"), (8, "Town Watch"),
                      (101, "Feudal Age"), (14, "Horse Collar")):
        st = Counter(e.get("Node Status") for _, e in trows if e.get("Node ID") == nid)
        print("  id %-5d %-12s %s" % (nid, name, dict(st)))

    # ---- 4. unique techs: does exactly one civ carry each?
    per_id = {}
    for c, e in trows:
        per_id.setdefault(e.get("Node ID"), []).append((c, e.get("Node Status")))
    ready_counts = Counter(sum(1 for _, s in v if s == "ResearchedCompleted")
                           for v in per_id.values())
    print("\ntech ids by how many civs read ResearchedCompleted: %s"
          % dict(sorted(ready_counts.items())))

    # ---- 5. tech ids that are absent from a civ's file entirely
    listed = {nid: {c for c, _ in v} for nid, v in per_id.items()}
    absent_backed = [nid for nid, cs in listed.items() if len(cs) < len(trees)]
    print("tech ids not listed by every civ: %d of %d"
          % (len(absent_backed), len(listed)))
    sample = sorted(absent_backed)[:6]
    for nid in sample:
        print("   id %-5d listed by %-3d civs" % (nid, len(listed[nid])))


if __name__ == "__main__":
    sys.exit(main())

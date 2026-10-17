# -*- coding: utf-8 -*-
"""The tech-side refused families, and whether they overlap shipped intents.

`type 101 Tech Cost Modifier`, `type 103 Tech Time Modifier`, `type 102 Disable
Tech` and `type 8 Modify Tech` all talk about a TECH, and this tool already has
three intents that write about techs:

    tech.cost           -> the tech record's ResearchResourceCost slots
    tech.research_time  -> the tech record's research time
    tech.availability    -> the civ's tree row for that tech

So before wiring any of these families, the same CONTRAST question as the last
two rounds: does the command change something those intents already change, or
something they cannot express?

The crucial structural difference to measure first: does a command target the
tech that CARRIES it, or a DIFFERENT tech?  If it targets itself, it is a
same-field alias of `tech.cost`/`tech.research_time`; if it targets another tech
conditionally (i.e. "researching X cheapens Y"), no shipped intent can say that.

Writes nothing.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.dat import locate as L                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.semantic import index as SI                       # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)
    sem = SI.index()

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]

    def tname(ti):
        e = sem.techs.get(ti)
        return e.en if e else "?"

    # collect rows per family
    fam = collections.defaultdict(list)
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] in (101, 102, 103, 8):
                fam[r["type"]].append((ti, t.get("civ"), r["raw"]))

    for ty in (101, 102, 103, 8):
        rs = fam[ty]
        print("=" * 74)
        print("type %-4d rows: %d" % (ty, len(rs)))
        if not rs:
            continue
        # slot A is the target tech for 101/103/8; D is the target for 102
        def target_of(ty, rw):
            _t, a, b, c, d = rw
            if ty == 102:
                return d if isinstance(d, int) else None
            return a if isinstance(a, int) and 0 <= a < len(techs) else None
        tgt = [target_of(ty, rw) for _ti, _o, rw in rs]
        self_t = sum(1 for (ti, _o, rw), tt in zip(rs, tgt) if tt == ti)
        other = sum(1 for (ti, _o, rw), tt in zip(rs, tgt) if tt is not None and tt != ti)
        none_t = sum(1 for tt in tgt if tt is None)
        print("  target == carrier tech: %d" % self_t)
        print("  target is ANOTHER tech: %d" % other)
        print("  target not identifiable: %d" % none_t)
        print("  distinct carriers: %d   distinct targets: %d"
              % (len({ti for ti, _o, _rw in rs}),
                 len({tt for tt in tgt if tt is not None})))
        owners = collections.Counter(o for _ti, o, _rw in rs)
        print("  owner: civ-owned %d / global %d"
              % (sum(n for o, n in owners.items() if o is not None and o >= 0),
                 sum(n for o, n in owners.items() if o is None or o < 0)))
        print("  sample rows:")
        for ti, o, rw in rs[:6]:
            print("    carrier tech %-5s %-24s owner=%-5s raw=%s -> target %s (%s)"
                  % (ti, tname(ti), o, rw, target_of(ty, rw),
                     tname(target_of(ty, rw)) if target_of(ty, rw) is not None else "-"))
        print()

    # --- the decisive overlap test for 101 (cost) and 103 (time) -----------
    print("=" * 74)
    print("OVERLAP TEST: does a 101/103 target ALREADY have a tech record")
    print("whose stored cost / research time could be written by tech.cost /")
    print("tech.research_time instead?")
    print("=" * 74)
    for ty, label, field in ((101, "cost", "costs"), (103, "research time", "research_time")):
        rs = fam[ty]
        if not rs:
            continue
        same, diff = 0, 0
        for ti, _o, rw in rs:
            _t, a, b, c, d = rw
            if not (isinstance(a, int) and 0 <= a < len(techs)):
                continue
            if a == ti:
                same += 1
            else:
                diff += 1
        print("type %d (%s): target==carrier %d, target!=carrier %d" % (ty, label, same, diff))
        # for a target that is a different tech, show what the target stores
        shown = 0
        for ti, _o, rw in rs:
            _t, a, b, c, d = rw
            if not (isinstance(a, int) and 0 <= a < len(techs)) or a == ti:
                continue
            stored = techs[a].get(field)
            print("    carrier %-5s %-22s -> target %-5s %-22s stored %s=%s  delta=%s"
                  % (ti, tname(ti), a, tname(a), field, stored, d))
            shown += 1
            if shown >= 6:
                break
        print()

    # --- type 102: is the disabled tech already NotAvailable in the tree? --
    print("=" * 74)
    print("type 102 OVERLAP: when a civ's tech disables Y, does that civ's TREE")
    print("already read NotAvailable for Y?  (compare with the type-2 lesson)")
    print("=" * 74)
    tab = collections.Counter()
    samples = []
    for ti, o, rw in fam[102]:
        _t, a, b, c, d = rw
        if not (isinstance(d, int) and 0 <= d < len(techs)):
            continue
        if o is None or o < 0:
            tab["owner is global"] += 1
            continue
        stem = next((s for s, i in stem2idx.items() if i == o), None)
        if stem is None:
            tab["owner has no tree file"] += 1
            continue
        st = CT.node_status(trees[stem], d, CT.TECH_USE_TYPES)
        tab[st] += 1
        if len(samples) < 8:
            samples.append((stem, ti, tname(ti), d, tname(d), st))
    for k, n in tab.most_common():
        print("  target tech row reads %-22s : %d" % (k, n))
    print()
    print("  samples (civ, carrier, disabled tech, its tree status):")
    for s in samples:
        print("    %-14s car %-5s %-22s disables %-5s %-22s tree=%s" % s)
    print()
    print("  NOTE: if the tree already reads NotAvailable, type 102 and the tree")
    print("  row are two spellings of the same fact and the tree is the one the")
    print("  engine reads for per-civ availability (see _probe/test_mechanism_gate.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

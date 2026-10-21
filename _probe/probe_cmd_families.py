# -*- coding: utf-8 -*-
"""Characterise the REFUSED effect-command families, one family at a time.

`aoe2mod/intent/compiler.py` refuses 1,222 of 8,005 shipped effect commands, and
the refusal reasons split into two kinds that must be handled oppositely:

  * "type not in the operation table"  -> a MISSING FEATURE (write code)
  * "attribute id has no name"         -> a MISSING LABEL  (leave refused)

This probe is about the first kind.  It answers, per command type: how many
commands, what do the four parameter slots look like, does the slot address
something in an id space we can name (a tech, a unit, a resource), and -- the
only number that matters for planning -- **how many technologies would become
editable for the first time if this family were implemented**.

It changes nothing; it exists so the next feature is chosen from measurements
rather than from the size of a histogram.
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
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.semantic import index as SI                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    TABLES = C.load_effect_tables()
    TYPES = TABLES["types"]["types"]

    # What the .dat knows how to name, so we can tell "addresses a real tech"
    # from "addresses a bare integer".
    #
    # NOTE: a naive `slot in range(len(techs))` test is USELESS here, because
    # unit ids and tech array indices overlap heavily (755 is both Tarkan's unit
    # id and a legal tech index).  The only trustworthy signal is a slot value
    # that lies OUTSIDE one of the two ranges.
    tech_ids = set(range(len(techs)))
    unit_ids = set()
    for civ in tk._civs:
        for u in civ.get("units") or ():
            unit_ids.add(u.get("id"))
    # Visibility must come from the SEMANTIC index, not from the parsed record:
    # `locate.walk_tech` deliberately naked-discards `LanguageDLLName`, so
    # `tech.get("LanguageDLLName")` is always None.  (I made exactly that
    # mistake while writing this probe.)
    sem = SI.index()
    named_techs = set()
    for k in (sem.techs or {}):
        try:
            named_techs.add(int(k))
        except (TypeError, ValueError):
            pass

    def tname(t):
        return (TYPES.get(str(t)) or {}).get("label") or ("Type %d" % t)

    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            rows.append((ti, r))

    total = len(rows)
    editable = sum(1 for _ti, r in rows if r["editable"])
    print("effect rows: %d total, %d editable, %d refused"
          % (total, editable, total - editable))
    print()

    # --- per-family shape -------------------------------------------------
    fam = collections.defaultdict(list)
    for ti, r in rows:
        if not r["editable"]:
            fam[r["type"]].append((ti, r))

    print("%-6s %-5s %-28s %6s %6s  %s"
          % ("type", "rows", "label", "names?", "newT", "slot shapes (top 3)"))
    for t in sorted(fam, key=lambda k: -len(fam[k])):
        items = fam[t]
        cnt = len(items)
        # Which of the four slots address an id space we can name?  Only a
        # value OUTSIDE the other range proves which space it belongs to.
        a = [r["raw"][1] for _ti, r in items]
        a_off_tech = sum(1 for v in a if v not in tech_ids)
        a_unit_only = sum(1 for v in a if v in unit_ids and v not in tech_ids)
        named = ("off-tech" if a_off_tech > cnt * 0.5 else
                 ("unit-only" if a_unit_only > cnt * 0.5 else "-"))
        # "newT": techs that have NO editable command today but WOULD have one
        # if this family alone were implemented.  This is the planning number.
        have = collections.Counter(ti for ti, r in rows if r["editable"])
        new_t = len({ti for ti, _r in items if have[ti] == 0})
        shapes = collections.Counter(r["raw"] for _ti, r in items)
        top = "; ".join("a=%s b=%s c=%s d=%s x%d"
                        % (s[1], s[2], s[3], s[4], n)
                        for s, n in shapes.most_common(3))
        print("%-6s %-5d %-28s %6s %6d  %s"
              % (t, cnt, tname(t)[:28], named, new_t, top))
    print()

    # --- the families that would unblock the most technologies ------------
    print("technologies with NO editable command today: %d"
          % len([1 for ti in range(len(techs))
                 if not any(r["editable"] for _t2, r in rows if _t2 == ti)]))
    per_type_newt = {}
    have = collections.Counter(ti for ti, r in rows if r["editable"])
    for t, items in fam.items():
        per_type_newt[t] = {ti for ti, _r in items if have[ti] == 0}
    # Greedy: which family, then which two families together, unlock the most?
    ranked = sorted(per_type_newt, key=lambda t: -len(per_type_newt[t]))
    print("best single family by NEW technologies: %s"
          % [(t, tname(t)[:22], len(per_type_newt[t])) for t in ranked[:5]])
    best2 = []
    for i, t1 in enumerate(ranked[:8]):
        for t2 in ranked[i + 1:8]:
            best2.append((len(per_type_newt[t1] | per_type_newt[t2]), t1, t2))
    best2.sort(reverse=True)
    print("best PAIR: %s"
          % [(n, t1, t2) for n, t1, t2 in best2[:4]])
    print()

    # --- reason split: missing FEATURE vs missing LABEL -------------------
    # Match on `reason_code`, not on the sentence.  The sentence became Chinese on
    # 2026-10-21 ("这条「升级单位」命令改的不是某项属性…"), and a probe that greps
    # the old English wording then counts 0 and reads exactly like "this data has
    # no such refusals" -- the trap `probe_building_warn_count.py` already fell
    # into once.
    reasons = collections.Counter()
    for _ti, r in rows:
        if r["editable"]:
            continue
        if r.get("reason_code") == "no_attribute_slot":
            reasons["missing feature"] += 1
        else:
            reasons["missing label"] += 1
    print("refusal reasons: %s" % dict(reasons))

    # --- does any family's owned tech carry a player-visible name? --------
    print()
    print("per-family: how many of the newly-unblocked techs are VISIBLE")
    for t in ranked[:8]:
        vis = 0
        for ti in per_type_newt[t]:
            if ti in named_techs:
                vis += 1
        print("  type %-5s %-26s newT %5d  visible %5d"
              % (t, tname(t)[:26], len(per_type_newt[t]), vis))
    print()
    print("sanity: techs the semantic index names at all: %d of %d"
          % (len(named_techs & tech_ids), len(techs)))
    _zero = [ti for ti in range(0, 40)]
    print("sanity: tech slots whose semantic name exists for ids 0..39: %d"
          % len([ti for ti in _zero if ti in named_techs]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
r"""Which shipped (civ, unit) pair can settle "does the menu read the tree or the panel"?

The question has been open for many rounds because every subject proposed so far
was ambiguous in the same way: the menu could have got the answer from THREE
sources, so no observation separated them.

  tree    resources/_common/dat/CivTechTrees/<CIV>.json   `Node Status`
  panel   resources/_common/dat/futuravailableunits.json  the building's `Units`
  `.dat`  a `type 2` (Enable/Disable Unit) effect command

A subject is DECISIVE only when the two JSON layers DISAGREE and the `.dat` is
SILENT about the unit -- then whichever the game shows is the layer that decided.

This probe recomputes the disagreeing pairs from the shipped files (not from a
remembered list) and annotates each with the `.dat` side:

  A  pairs where the panel lists the unit and the tree says NotAvailable
  B  pairs where the tree says buildable and the panel omits it
  C  for each, what the `.dat` says: the effect commands that mention the unit,
     with the owning civilization, and whether that owner is THIS civ, every civ
     (civ = -1), or a different civ
  D  the decisive subset: a real disagreement with no matching `.dat` enabler

Run:  python _probe/probe_zero_mod_subject.py
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aoe2mod.api as A                                       # noqa: E402
from aoe2mod.game import buildpanel as BP                     # noqa: E402
from aoe2mod.game import civtechtrees as CT                   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def enable_commands(tk):
    """{unit_id: [(owner_civ_or_-1, b, tech_index)]} for every type-2 command.

    The command lives on the EFFECT a technology points at, not on the technology
    record itself -- reading `tech["commands"]` returns nothing and looks exactly
    like "the game never enables this unit".
    """
    techs = tk._tech_records()
    effects = tk._stats.get("effects") or []
    out = {}
    for i, t in enumerate(techs):
        eid = t.get("effect_id")
        if eid is None or eid < 0 or eid >= len(effects):
            continue
        for c in (effects[eid].get("commands") or []):
            ty, a = (c.get("type"), c.get("a")) if isinstance(c, dict) else (c[0], c[1])
            b = c.get("b") if isinstance(c, dict) else c[2]
            if ty != 2:
                continue
            out.setdefault(int(a), []).append((t.get("civ"), b, i))
    return out


def panel_units(panels, civ_name):
    """{node_id: building_id} for everything this civilization's panel lists."""
    key = BP.civ_key_for(panels, civ_name)
    if key is None:
        return None
    obj = panels[key]["obj"]
    found = {}
    for blk in BP.buildings(obj, key):
        bid = blk.get("ID")
        if bid is None:
            continue
        for sp in (BP.UNITS_KEY, BP.TECHS_KEY):
            try:
                for e in BP.entries(obj, key, bid, sp):
                    if isinstance(e, dict) and e.get("ID") is not None:
                        found.setdefault(int(e["ID"]), (bid, sp))
            except Exception:
                pass
    return found


def main():
    tk = A.open_toolkit(game_root=GAME)
    trees = tk._trees()
    panels = BP.load_all(GAME)
    enab = enable_commands(tk)

    # Which civ each `.dat` index is, so an effect's `civ` can be named.
    civ_by_index = {i: c["name"] for i, c in enumerate(tk._civs)}

    print("trees: %d   panels: %d   units with a type-2 command: %d"
          % (len(trees), len(panels), len(enab)))
    print()

    kind_p, kind_t, decisive = [], [], []
    for tree_key in sorted(trees):
        tree = trees[tree_key]
        disp = None
        for cand in (tree_key, tree_key.title()):
            if BP.civ_key_for(panels, cand) is not None:
                disp = cand
                break
        if disp is None:
            continue
        listed = panel_units(panels, disp)
        if listed is None:
            continue
        for row in CT.unit_rows(tree):
            uid = row.get("Node ID")
            if uid is None:
                continue
            uid = int(uid)
            st = row.get("Node Status")
            buildable = st != "NotAvailable"
            in_panel = uid in listed
            if in_panel and not buildable:
                kind_p.append((tree_key, disp, uid, row.get("Name"), listed[uid][0]))
            elif buildable and not in_panel:
                kind_t.append((tree_key, disp, uid, row.get("Name"), row.get("Age ID"), st))

    def dat_says(tree_key, uid):
        """What the `.dat` alone says about this civ building this unit.

        THREE mechanisms can make the `.dat` answer 'yes', and silence in only one
        of them does not mean silence:

          1. a `type 2` (Enable/Disable Unit) effect command  -> checked below
          2. the civ's own copy of the unit record carrying a `train_location` at
             the building in question                            -> checked below
          3. the unit simply not existing in that civ's array   -> checked below

        (1) alone was measured first and every disagreement looked decisive.  That
        was wrong: the unit record is the ordinary path by which a civilization
        trains something, so a pair can be listed by the panel, forbidden by the
        tree, and still have a complete `.dat` explanation.
        """
        ci = None
        for i, c in enumerate(tk._civs):
            if CT.civ_file_stem(c["name"]) == tree_key:
                ci = i
                break
        cmds = enab.get(uid) or []
        owners = [o for (o, _b, _t) in cmds]
        notes = []
        if any(o == -1 for o in owners):
            notes.append("GLOBAL enable (civ=-1)")
        elif ci is not None and ci in owners:
            notes.append("this civ owns the enable")
        elif owners:
            notes.append("enabled only by %s" % ", ".join(
                sorted({civ_by_index.get(o, str(o)) for o in owners})))
        else:
            notes.append("no type-2 command")

        # (2) and (3): the civ's own record and its training entries.
        if ci is None:
            notes.append("no .dat civilization")
            return "; ".join(notes)
        rec = None
        for u in (tk._civs[ci].get("units") or []):
            if int(u.get("id", -1)) == uid:
                rec = u
                break
        if rec is None:
            notes.append("unit absent from this civ's array")
        else:
            locs = rec.get("train_locations") or []
            if locs:
                blds = sorted({d.get("unit_id") for d in locs
                               if isinstance(d, dict)})
                notes.append("record trains at building(s) %s" % (blds,))
            else:
                notes.append("record has no train_location")
        return "; ".join(notes)

    def dat_is_silent(text):
        """True only when NO `.dat` mechanism permits this civ to train the unit."""
        return (text == "no type-2 command; record has no train_location"
                or text.endswith("no type-2 command; unit absent from this civ's array"))

    print("A  panel lists it, tree says NotAvailable   (%d pairs)" % len(kind_p))
    for tk_, disp, uid, name, bid in kind_p:
        ds = dat_says(tk_, uid)
        print("   %-12s %-5d %-26s panel@bldg %-4s | %s"
              % (tk_, uid, (name or "")[:26], bid, ds))
        if dat_is_silent(ds):
            decisive.append(("panel lists / tree forbids", tk_, disp, uid, name))
    print()
    print("B  tree says buildable, panel omits it      (%d pairs)" % len(kind_t))
    for tk_, disp, uid, name, age, st in kind_t:
        ds = dat_says(tk_, uid)
        print("   %-12s %-5d %-26s age=%-4s %-18s | %s"
              % (tk_, uid, (name or "")[:26], age, st, ds))
        if dat_is_silent(ds):
            decisive.append(("tree allows / panel omits", tk_, disp, uid, name))
    print()
    print("C  DECISIVE -- the two JSON layers disagree and the `.dat` is silent")
    if not decisive:
        print("   none.  Every disagreement has a `.dat` explanation, so a zero-mod")
        print("   observation of any of them could not separate the layers.")
    for why, tk_, disp, uid, name in decisive:
        print("   %-26s %-12s unit %-5d %s" % (why, tk_, uid, name))
    print()
    print("ZERO-MOD SUBJECT: %d decisive pair(s)." % len(decisive))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
r"""Button slots: which `button_id` a granted unit may occupy.

## Why this module exists

`dsh test v4` and `dsh test v5` differed by ONE BYTE -- the British Champi Scout's
`train_location.button_id`, 1 versus 4 -- and only v5 appeared in game.  That makes
the button slot a load-bearing input, not a cosmetic one, and the product must decide
it rather than inherit it from a donor civilization.

## The rule

`button_id` groups a building's units into button CHAINS: one slot cycles through an
upgrade line (`Militia -> Man-at-Arms -> Longswordsman -> ...`).  A unit placed in a
slot that already holds an AVAILABLE unit of a DIFFERENT chain is masked -- which is
exactly what the Incas never ran into (their militia line is `NotAvailable`, so
button 1 was free for the Champi line) and the British did.

So:

    a granted unit must take a slot with no unit the civilization can already build

"Can build" means `ResearchedCompleted` or `ResearchRequired` -- the same predicate the
rest of this package uses (`civtechtrees.node_status`).

## What is measured, not assumed

* Every (civ, building) that can build anything usually HAS a free slot, but not
  always: 77 of 678 such pairs are exhausted (single-unit buildings such as the
  Market).  `free_slots` therefore returns a possibly-empty list and
  `choose_slot` says why it failed rather than guessing.
* Shipped data never puts two unrelated chains in one available slot.  Twelve slots
  mix `unitlines.json` line ids, and all twelve are ONE line reachable at two
  buildings (`Huskarl 41@Castle` / `759@Barracks`), so they are not counter-examples.
  Verified by `_probe/probe_button_slot_collision.py` and
  `_probe/probe_slot_grouping.py`.
"""
import os
import sys
from collections import defaultdict

from ..game import civtechtrees as CT

#: The statuses that mean "this civilization can already build it here".
AVAILABLE = ("ResearchedCompleted", "ResearchRequired")


def slot_map(civ, tree, building_id):
    """``{button_id: [(unit_id, status), ...]}`` for one civ's building.

    ``civ`` is a `.dat` civ record, ``tree`` a loaded CivTechTrees dict.  A unit with
    no tree row has status ``None`` and counts as NOT available -- which is what makes
    the four American regional units invisible to the British.
    """
    out = defaultdict(list)
    for u in civ.get("units") or []:
        for t in u.get("train_locations") or []:
            if t.get("unit_id") != building_id:
                continue
            bid = t.get("button_id")
            if bid is None:
                continue
            row = CT.row_for(tree, u["id"], CT.UNIT_USE_TYPES)
            out[bid].append((u["id"], (row or {}).get("Node Status")))
    return out


def free_slots(civ, tree, building_id, exclude=()):
    """Button ids at ``building_id`` holding no AVAILABLE unit.

    ``exclude`` is a set of unit ids to treat as absent -- the donor row's own unit
    when asking "where could this go instead", since it is the thing being moved.
    """
    out = []
    for bid, entries in slot_map(civ, tree, building_id).items():
        if any(i not in exclude and st in AVAILABLE for i, st in entries):
            continue
        out.append(bid)
    return sorted(out)


def occupied_slots(civ, tree, building_id):
    """Button ids that DO hold an available unit, with what occupies them."""
    out = {}
    for bid, entries in slot_map(civ, tree, building_id).items():
        av = [i for i, st in entries if st in AVAILABLE]
        if av:
            out[bid] = sorted(av)
    return out


def choose_slot(civ, tree, building_id, node_type=None, donor_slot=None,
                exclude=()):
    """Pick a free slot, or explain why none is available.

    Returns ``(slot, reason)``.  ``reason`` is ``""`` on success; otherwise it says
    the building is exhausted, and names what occupies every slot so the caller can
    report something a player can act on rather than "no slot".

    Preference order, and every step is measured rather than invented:

      1. ``donor_slot`` when it is free -- the slot the donor civilization uses keeps
         the new unit where a player of that unit would expect it;
      2. ``slot_convention(node_type)`` when that slot is free -- the shipped game's
         own habit for that kind of unit;
      3. otherwise the lowest free slot.

    Returns ``(None, why)`` when the building is exhausted, which happens for 77 of
    the 678 (civ, building) pairs that can build anything -- single-unit buildings
    such as the Market.
    """
    free = free_slots(civ, tree, building_id, exclude=exclude)
    if donor_slot is not None and donor_slot in free:
        return donor_slot, ""
    conv = slot_convention(node_type)
    if conv is not None and conv in free:
        return conv, ""
    if free:
        return free[0], ""
    occ = occupied_slots(civ, tree, building_id)
    if not occ:
        return None, ("building %s trains nothing this civilization can build, so "
                      "there is no button to occupy" % building_id)
    detail = ", ".join("%s=%s" % (b, v) for b, v in sorted(occ.items()))
    return None, ("every button slot at building %s is already taken by a unit this "
                  "civilization can build (%s), so a new unit would be masked; "
                  "free one first" % (building_id, detail))


#: Measured from the shipped data: which `button_id` a `Node Type` usually occupies
#: among units a civilization can actually build.  Counted over every civ, with the
#: three most common values and their tallies:
#:
#:     RegionalUnit  4:61  3:56  1:26
#:     UniqueUnit    1:139 4:24  2:8
#:     Unit          1:487 2:419 3:278
#:
#: Only the REGIONAL case is useful as a tie-breaker: unique units are overwhelmingly
#: slot 1 because that is the militia chain's slot, which is exactly the slot a grant
#: must NOT reuse.  So the table deliberately covers `RegionalUnit` alone, and a
#: `None` answer means "no convention, take the lowest free slot".
_SLOT_CONVENTION = {
    "RegionalUnit": 4,
}


def slot_convention(node_type):
    """The shipped game's habitual slot for a unit kind, or ``None``.

    See ``_SLOT_CONVENTION`` for the tallies behind the one entry.  Returning
    ``None`` is the honest answer for kinds where the data shows no habit.
    """
    return _SLOT_CONVENTION.get(node_type)


def describe(civ, tree, building_id, unit_id):
    """Where ``unit_id`` sits and which slots are free -- for a preview."""
    m = slot_map(civ, tree, building_id)
    cur = None
    node_type = None
    for bid, entries in m.items():
        if any(i == unit_id for i, _st in entries):
            cur = bid
            break
    row = CT.row_for(tree, unit_id, CT.UNIT_USE_TYPES)
    node_type = (row or {}).get("Node Type")
    return {"building": building_id, "current_slot": cur,
            "node_type": node_type,
            "free_slots": free_slots(civ, tree, building_id),
            "occupied": occupied_slots(civ, tree, building_id)}

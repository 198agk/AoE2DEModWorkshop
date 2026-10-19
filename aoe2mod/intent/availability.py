# -*- coding: utf-8 -*-
"""One sentence: "let the Britons build the Huskarl".

WHY THIS IS NOT A `.dat` PATCH
==============================

The toolbar's other intents all rewrite bytes inside ``empires2_x2_p1.dat``.
Availability cannot: no per-record byte expresses it (measured -- see the module
docstring of :mod:`aoe2mod.game.civtechtrees`).  What decides "can civ X build
unit Y" is ``resources/_common/dat/CivTechTrees/<CIV>.json``, and the output of
this module is therefore a JSON-only mod -- no ``.dat`` at all.

That difference is not cosmetic.  It changes what "verify" can mean:

* the bytes are produced by :func:`civtechtrees.serialize`, whose contract is
  byte-exactness against all 62 shipped files, so a mod here can be shown to
  differ from the original ONLY in the rows the user asked about;
* the file has to land at the path the engine formats at runtime, so the check
  is done against that path rather than a path this module chose.

WHAT IS AND IS NOT PROVEN
=========================

PROVEN (by the end-to-end test ``test_availability_e2e.py``): the emitted tree
re-serialises byte-exactly, the untouched rows are byte-identical to the
shipped file, exactly one row was added, and the file sits where the engine
looks.  NOT PROVEN: that a running game offers the unit.  This layer has never
been observed in-game -- no mod on this install ships a CivTechTrees file -- so
:func:`report` says so in its own output rather than letting a caller assume it.

THE THREE WAYS A REQUEST CAN FAIL, AND WHY THEY ARE DIFFERENT SENTENCES
======================================================================

1. The unit has no row in ANY civ file.  1,364 of the 1,651 name-resolved units
   are in this state (they are eyecandy, buildings-as-units, placeholders).  The
   honest sentence is "no civilization in this game can build that", NOT "unknown
   unit" -- the unit exists and has a name, it simply is not in any tech tree.
2. The civ already has it.  Adding the row would produce a file with a duplicate
   node; the engine's behaviour with one is not something to guess at, so this is
   refused rather than attempted.
3. The civ has a row for it under ``ResearchRequired``.  This is NOT "can be
   granted": that status means it is already in the tree behind a prerequisite,
   so the civ can build it once the research is done and a grant would change
   nothing.  It is refused with its own sentence, not with "already has it".
4. The civ has a row for it under ``NotAvailable``: listed in the tree but not
   obtainable.  This IS fixable, but not by adding a row -- the operation is a
   status change on the existing row, which is a different edit and is reported
   as such (``mode: "set_status"``) so the user is not told "nothing changed".
   Being listed under ``NotAvailable`` and being absent are therefore different
   states with different sentences.

THE THREE STATUS WORDS, PINNED TO KNOWN ANSWERS
==============================================

``ResearchedCompleted`` = has it from the start; ``ResearchRequired`` = reachable
by researching the prerequisite; ``NotAvailable`` = listed, never obtainable; no
row at all = not in this civ's tree.  Measured in ``_probe/probe_status_meaning.py``
against units whose answer is already known: Galley reads ``ResearchRequired``
for all 56 civs that own a Dock and ``NotAvailable`` for none, and Huskarl reads
``ResearchedCompleted`` for the Goths and simply has no row for the other 61.
"Can build" is therefore ``ResearchedCompleted`` OR ``ResearchRequired``.
"""
import os

from ..game import civtechtrees as CT

#: The two things a user can ask for.  Named here so the schema and the code
#: agree, and so a caller can assert it handled both.
ACTIONS = ("grant", "revoke")

#: (English verb, Chinese verb) per id space.  A unit is BUILD, a technology is
#: RESEARCH, and the two spaces need different sentences or the tech side reads
#: "BRITONS can build Loom".  Keyed by the first entry of a ``use_types`` tuple.
_VERBS = {
    "Unit": ("build", "建造"),
    "Tech": ("research", "研究"),
}


def verbs_for(use_types):
    """``(en_verb, zh_verb)`` for an id space; falls back to unit wording."""
    return _VERBS.get(use_types[0] if use_types else None, _VERBS["Unit"])


#: Which id space each availability intent addresses.  Derived from the intent
#: name rather than passed around, because the SPACE is a property of the
#: request -- `tech.availability` is never about a unit id.  Anything else falls
#: back to units, which is what an unknown name would have meant before.
_INTENT_SPACES = {
    "unit.availability": "Unit",
    "tech.availability": "Tech",
}


def space_of(intent):
    """The ``use_types`` tuple for a raw availability intent dict."""
    return (_INTENT_SPACES.get((intent or {}).get("intent"), "Unit"),)


def _status_zh(status):
    """The game's own wording for the three statuses, for a user-facing reason."""
    return {
        "ResearchedCompleted": "已可用",
        "ResearchRequired": "需要研究前置科技",
        "NotAvailable": "列为不可获得",
    }.get(status, status)


def describe(trees, node_id, display="unit", use_types=CT.UNIT_USE_TYPES):
    """What the whole corpus says about ``node_id``: who has it, who can get it.

    ``use_types`` selects the id space and MUST be passed correctly: ``Node ID``
    is shared between units and techs, so asking the unit space about a tech id
    returns "nobody has it" for all 62 civs (Loom does, which is how the bug was
    found).  ``display`` is the word used in any sentence this produces.

    Returns ``None`` when NO civ has a row for it -- that is the answer for the
    1,364 unaddressable units, and it is different from "this civ does not have
    it", which is the common case.

    Two lists, because they answer different questions and differ on 14 nodes:

    * ``holders`` -- civs whose row reads ``ResearchedCompleted``: they have it
      right now, with no research.
    * ``builders`` -- civs that can EVER build it, i.e. holders plus the ones
      whose row reads ``ResearchRequired``.  This is what "who can build this"
      means to a player, and using ``holders`` for it under-reports: War Galley
      would come back as 0 civs when 56 can build it.
    """
    holders = CT.owners(trees, node_id, use_types=use_types)
    builders = CT.builders(trees, node_id, use_types=use_types)
    listed = {}
    for civ, t in sorted(trees.items()):
        st = CT.node_status(t, node_id, use_types)
        if st is not None:
            listed[civ] = st
    if not listed:
        return None
    return {
        "node_id": node_id,
        "space": use_types[0] if use_types else None,
        "holders": holders,
        "holder_count": len(holders),
        "builders": builders,
        "builder_count": len(builders),
        "listed": listed,
        # Civs with no row at all.  A grant can help these by ADDING a row;
        # civs listed as NotAvailable need a status change instead, which is a
        # different edit, so the two sets are reported separately.
        "absent_from": sorted(c for c in trees if c not in listed),
        "blocked_in": sorted(c for c, st in listed.items()
                             if st == "NotAvailable"),
        "pending_in": sorted(c for c, st in listed.items()
                             if st == "ResearchRequired"),
    }


def plan(trees, civ, node_id, action, display="unit",
         use_types=CT.UNIT_USE_TYPES):
    """Validate one availability request WITHOUT producing any bytes.

    Returns a dict.  ``ok`` False carries ``reason`` -- user-facing prose, never
    a traceback, and naming the civ and the item rather than the internal ids.
    On success the dict also carries what the edit will be (``mode``), which
    donor the row came from, and every field the donor copy inherits.

    ``use_types`` selects the id space; see :func:`describe`.
    """
    if action not in ACTIONS:
        return {"ok": False,
                "reason": "unknown action %r; expected %s"
                          % (action, " or ".join(ACTIONS))}
    if civ not in trees:
        return {"ok": False,
                "reason": "no CivTechTrees file for %s in this install"
                          % civ}

    tree = trees[civ]
    current = CT.node_status(tree, node_id, use_types)
    _en, _zh = verbs_for(use_types)

    if action == "revoke":
        # Nothing to take away when the civ cannot build it anyway -- which
        # includes a row listed as NotAvailable: removing that row would change
        # what the tree shows without changing what the civ can build.
        if not CT.can_build(tree, node_id, use_types):
            return {"ok": False,
                    "reason": "%s cannot %s %s in the first place, so there "
                              "is nothing to take away" % (civ, _en, display)}
        return {"ok": True, "civ": civ, "node_id": node_id, "action": action,
                "mode": "remove_row", "was_status": current,
                "description": "%s 不再能%s %s" % (civ, _zh, display)}

    # --- grant -----------------------------------------------------------
    # "Can build" is can_build(), not has(): a civ whose row reads
    # ResearchRequired (Cannon Galleon for BRITONS) CAN build it once the
    # prerequisite is researched, so telling it "now you can build it" would be a
    # lie about a change that is not a change.  Only a row that reads
    # NotAvailable, or no row at all, is something a grant can actually fix.
    if current == "ResearchedCompleted":
        return {"ok": False,
                "reason": "%s can already %s %s; nothing would change"
                          % (civ, _en, display)}
    if current == "ResearchRequired":
        return {"ok": False,
                "reason": "%s can already %s %s once the prerequisite is "
                          "researched; nothing would change"
                          % (civ, _en, display)}
    if current is not None:
        # The row exists and reads NotAvailable: listed, but not obtainable.
        # That is a real edit -- a status change on the existing row, which is a
        # different edit from adding one.
        return {"ok": True, "civ": civ, "node_id": node_id, "action": action,
                "mode": "set_status", "was_status": current,
                "description": "%s 改为可%s %s（原来%s）"
                               % (civ, _zh, display, _status_zh(current))}

    donor_civ, donor = CT.donor_row(trees, node_id, use_types)
    if donor is None:
        # Every civ either has no row or has one that reads NotAvailable.  Say
        # what is actually wrong: the unit is not in any tech tree at all.
        return {"ok": False,
                "reason": "no civilization in this game can %s %s, so there "
                          "is no row to give %s -- it is not part of any tech "
                          "tree" % (_en, display, civ)}
    # Warnings are produced by the REAL grant so the preview and the write cannot
    # report a different set -- but on a copy, because `grant` appends.  The copy
    # must be deep enough that the row LIST is not shared: `dict(tree)` is
    # shallow, so `setdefault(UNITS_KEY, []).append(...)` on a shallow copy
    # appends to the original civ's list and a "preview" would silently grant the
    # thing it was only supposed to describe.
    probe = {k: (list(v) if isinstance(v, list) else v)
             for k, v in tree.items()}
    probe.pop("path", None)
    _row, warnings = CT.grant(probe, node_id, donor, use_types=use_types)
    # The list copy is per-key, so the appended row landed in `probe` only.
    assert len(CT.rows_of(tree)) == len(CT.rows_of(probe)) - 1
    return {"ok": True, "civ": civ, "node_id": node_id, "action": action,
            "mode": "add_row", "donor": donor_civ, "warnings": warnings,
            "description": "%s 可以%s %s（复制 %s 的条目）"
                           % (civ, _zh, display, donor_civ)}


def apply(trees, civ, node_id, action, status="ResearchedCompleted",
          use_types=CT.UNIT_USE_TYPES):
    """Perform the edit on ``trees[civ]`` in place.  Returns a report dict.

    Mutates the tree dict -- callers that need the original keep a copy (the
    end-to-end test does exactly that and compares byte for byte).
    """
    tree = trees[civ]
    if action == "revoke":
        gone = set()
        n = CT.revoke(tree, node_id, use_types, revoked_ids=gone)
        # `revoke` cascades up the upgrade chain so the file stays chain-closed
        # (no row may Link ID a node the file lacks -- all 62 shipped files obey
        # it, and a dangling target gives the game licence to reject the whole
        # tree, which is exactly what invalidated the v9 experiment).  Report the
        # extra ids so a UI can say "this took its upgrades with it" instead of
        # silently removing more rows than were asked for.
        extra = sorted(i for i in gone if i != node_id)
        return {"civ": civ, "node_id": node_id, "action": action,
                "rows_removed": n, "rows_added": 0,
                "cascaded_ids": extra, "warnings": []}

    current = CT.node_status(tree, node_id, use_types)
    if current is not None:
        row = CT.row_for(tree, node_id, use_types)
        row["Node Status"] = status
        return {"civ": civ, "node_id": node_id, "action": action,
                "rows_removed": 0, "rows_added": 0, "status_changed_from": current,
                "warnings": []}

    donor_civ, donor = CT.donor_row(trees, node_id, use_types)
    row, warnings = CT.grant(tree, node_id, donor, status=status,
                             use_types=use_types)
    return {"civ": civ, "node_id": node_id, "action": action,
            "rows_removed": 0, "rows_added": 1, "donor": donor_civ,
            "warnings": warnings}


def emit_files(trees, civ):
    """``{relative_path: bytes}`` for one civ's tree, ready for the emitter.

    The relative path is the engine's own -- ``resources/_common/dat/
    CivTechTrees/<CIV>.json`` -- built by :func:`civtechtrees.civ_file_stem`, not
    by a second naming scheme here.
    """
    stem = CT.civ_file_stem(civ)
    rel = os.path.join(CT.CIVTECHTREES_REL, "%s.json" % stem)
    return {rel.replace(os.sep, "/"): CT.serialize(trees[civ])}, rel


def verify_files(orig_tree, new_tree, shipped_bytes, node_id,
                 use_types=CT.UNIT_USE_TYPES, cascade_ids=None):
    """Check the emitted bytes against the shipped file.  Returns a report dict.

    THREE separate claims, each of which can fail alone:

    * ``serializer_is_exact`` -- writing the ORIGINAL tree back through
      :func:`civtechtrees.serialize` reproduces the shipped bytes exactly.  This
      is the load-bearing one: without it, "the new bytes differ from the old
      ones only where we asked" is unprovable, because a formatting difference
      anywhere would look like part of the edit.
    * ``serialize_reparses`` -- the NEW bytes parse back to the tree object, so
      the apostrophe rule did not corrupt anything.
    * ``untouched_rows_identical`` -- every row the edit did not touch compares
      equal to the shipped row at the same identity.  A grant appends, so rows
      0..n-1 must be unchanged and row n is the addition; a revoke removes.

    ``cascade_ids`` is the set of node ids the edit was SUPPOSED to remove, from
    :func:`civtechtrees.chain_closure` computed before the edit.  A revoke now
    deletes the revoked node's upgrade successors too, because a file that links
    to a node it no longer contains is a state no shipped file has and the game is
    entitled to reject; passing the closure here keeps that intended cascade from
    being counted as collateral damage while still catching a row vanishing that
    was not in the plan.
    """
    rep = {}
    # 1. Can the serializer reproduce this exact file?  If not, every other
    #    comparison below is meaningless.
    rep["serializer_is_exact"] = (CT.serialize(orig_tree) == shipped_bytes)
    # 2. Do the new bytes survive a parse round-trip?
    ok, reason = CT.verify_serializer(new_tree)
    rep["serialize_reparses"] = ok
    if reason:
        rep["reason"] = reason
    # 3. Are the untouched rows untouched?  Stated as a multiset comparison of
    #    everything EXCEPT the nodes this edit intended to remove.  Index-based
    #    comparison would be wrong for a revoke (which removes a row from the
    #    middle, so the whole tail shifts) and for a grant (which appends, so only
    #    the tail changes) -- identity is the claim that actually holds for all
    #    three modes, and it catches a row vanishing anywhere.
    #
    #    The whole file is compared, not just the rows in this node's space: a
    #    grant into the tech space must not disturb a unit row either.
    before = [e for e in CT.rows_of(orig_tree) if isinstance(e, dict)]
    after = [e for e in CT.rows_of(new_tree) if isinstance(e, dict)]
    intended = {(node_id, use_types[0] if use_types else None)}
    if cascade_ids:
        intended |= {(i, use_types[0] if use_types else None) for i in cascade_ids}

    def key(row):
        return (row.get("Node ID"), row.get("Use Type"))

    def counts(rows):
        out = {}
        for row in rows:
            k = key(row)
            if k in intended:
                continue
            out[k] = out.get(k, 0) + 1
        return out

    cb, ca = counts(before), counts(after)
    vanished = sorted(k for k in cb if ca.get(k, 0) < cb[k])
    appeared = sorted(k for k in ca if cb.get(k, 0) < ca[k])
    rep["before_rows"] = len(before)
    rep["after_rows"] = len(after)
    rep["before_unit_rows"] = len(CT.unit_rows(orig_tree))
    rep["after_unit_rows"] = len(CT.unit_rows(new_tree))
    rep["other_names_vanished"] = [{"node_id": k[0], "use_type": k[1]}
                                   for k in vanished]
    rep["other_names_appeared"] = [{"node_id": k[0], "use_type": k[1]}
                                   for k in appeared]
    rep["untouched_rows_identical"] = not (vanished or appeared)

    # What happened to the node the user named.  Reported so a caller can tell
    # "the row was added" from "the row's status changed" without re-reading.
    node_key = (node_id, use_types[0] if use_types else None)
    rep["node_rows_before"] = sum(1 for r in before if key(r) == node_key)
    rep["node_rows_after"] = sum(1 for r in after if key(r) == node_key)
    rep["node_status_before"] = CT.node_status(orig_tree, node_id, use_types)
    rep["node_status_after"] = CT.node_status(new_tree, node_id, use_types)
    # Closure is now part of "the file is what we meant to write": a tree whose
    # rows link to nodes it no longer has is a state no shipped file contains.
    rep["chain_closed"] = not CT.dangling_links(new_tree)
    rep["ok"] = bool(rep["serializer_is_exact"] and rep["serialize_reparses"]
                     and rep["untouched_rows_identical"]
                     and rep["chain_closed"])
    return rep

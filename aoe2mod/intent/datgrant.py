# -*- coding: utf-8 -*-
r"""The `.dat` half of "let a civilization build a unit it cannot build".

## Why the JSON half alone was not enough

`unit.availability` originally wrote only `CivTechTrees/<CIV>.json` and
`futuravailableunits.json`.  A clean in-game test on 2026-10-15 showed the control
working (a `.dat` edit rendered) while that write produced no change in the build
menu.  `dsh test v5` then succeeded, and it carried BOTH halves.

## The three `.dat` edits, each measured

From the working recipe (`dsh test v5`, confirmed in game 2026-10-16):

1. **a new Effect** whose command is `(type 2, a=<unit id>, b=1)` -- "make this unit
   available".  `type 2` is `Enable/Disable Unit` and `b=1` means enable; shipped data
   uses exactly this for every regional unit (`tech 1350 'Champi Scout (Make avail)'`,
   `tech 1363`, `tech 1471`, ...).
   *Append an EFFECT, never a TECH*: `write_tech`'s `_new` branch hard-codes the three
   `ResearchResourceCost` slots to 0 while every shipped `make avail` tech uses `-1`,
   and a model dict cannot override it (`_probe/test_dat_edit_routes.py`).

2. **re-point a tech the target civ already owns** at that effect, *carrying the
   anchor's existing commands into the new record*.  A tech is addressed by its
   position in the array (no id field), and the array is walked by
   `locate.locate_techs`, so this is an integer write into the model.  The carry-over
   is load-bearing rather than tidy: the anchor is by construction a 0:00 technology
   the civ owns, and the civ's own bonuses live on exactly those.  Dropping them
   deletes a shipped bonus while reporting success — measured, see `apply_grant`.

3. **the button slot** — a single in-place byte in the unit record, because
   `Parser.stats["civs"][i]["units"][j]` does not model `train_locations` (an
   earlier draft read it there, got `None`, and reported `ok=False` for no visible
   reason).  The offset MUST be derived on the serialized stream: appending an
   effect shifts everything after it (measured: 93237962 -> 93238024 in the v5
   build), and reusing a base-stream offset would patch the wrong byte silently.

## `EnablingResearch` is deliberately NOT written

Earlier versions of this module also patched
`TechTree.UnitConnection.EnablingResearch` to the anchor technology.  That write has
since been **removed**, and the reasons are all measured:

  * `dsh test v7` -- the recipe the user confirmed in game (m27131) -- wrote **no
    such byte**.  Its script (`_probe/build_dshtest_v7.py`) patches only when the
    shipped value is not -1, and for unit 2550 it is -1, so the branch never ran.
    Writing it made this module differ from the confirmed recipe by 4 bytes.
  * Two in-game runs show the field does not gate: v5 wrote 263 (British, age-gated)
    and the button appeared after a Castle; v6 cleared it to -1 and behaved
    identically.  The gate was the anchor's `RequiredTechs`, not this field.
  * The field is **global, per unit id** -- there is one connection per unit, not one
    per civilization.  `tech_index` is owned by the TARGET civilization, so writing it
    points every civilization's copy of that unit at one civ's private technology.
    Unit 2550 is built by Incas/Mapuche/Muisca/Tupi and *not* by the British, so the
    write would claim "2550 is made available by a British technology" to all 63 civs
    -- and if the field ever did gate, it could hide the unit from the four civs that
    legitimately have it, while only granting it to British.
  * The shipped corpus contains **zero** precedents for that foreign pairing: every
    civ-owned `EnablingResearch` in the data belongs to a civilization that really
    builds the unit (`_probe/probe_enabling_scope.py`, section D).  Writing 383 onto
    2550 would create the first one.

The value is still read and reported, so a caller can see what the field says and
decide whether its own case needs attention; it is simply not overwritten.

## What this module does NOT do

It does not choose the civ's tech or the slot; the caller passes them, because both
are decisions with user-visible consequences and the caller has the tree data.
"""
import contextlib
import io

from ..game import buttons as BT
from ..game import civtechtrees as CT

#: The effect command for "make available": `type 2` = Enable/Disable Unit, `b = 1`
#: = enable, `a` = the unit id.  Named so no caller has to remember the tuple shape.
def enable_command(unit_id):
    """The command tuple that makes ``unit_id`` buildable: ``(2, unit, 1, -1, 0.0)``."""
    return (2, unit_id, 1, -1, 0.0)


def pick_tech(techs, civ_index, prefer_name_contains="make avail"):
    """A tech the civilization owns, to hang the effect on.

    ``techs`` is ``locate.locate_techs(...)``; ``civ_index`` is the `.dat` civ index.

    ## The anchor decides WHEN the grant takes effect, and the field that says so
    ## is ``required_techs``

    A technology is applied once every entry in its `RequiredTechs` array is
    satisfied, so the anchor's array -- not its name, not its research location --
    is what decides whether a granted unit appears at 0:00 or only after an age
    upgrade.  Measured against the British anchors, whose effects are the real
    in-game civilization bonuses, so the rule is checked against known answers:

        tech 383 'C-Bonus, +25% Shepherd'     required_techs []        shepherds faster
                                                                      FROM 0:00      ok
        tech 381 'C-Bonus, 1/2 TCs'           [102]                    half-price TCs
                                                                      from CASTLE    ok
        tech 382 'C-Bonus, +1 Archer range'   [102]                    +1 range from
                                                                      CASTLE         ok
        tech 403 'C-Bonus, archer range +1'   [103]                    +1 more at
                                                                      IMPERIAL       ok
        tech 263 'Longbow (make avail)'       [102, 266 'Castle built']  Castle       ok
        tech 1350 'Champi Scout (Make avail)' [104 'Dark Age']         works at 0:00  ok

    The earliest pick -- by name, ``"make avail"`` -- is tech 263, and `dsh test v5`
    proved what that costs: the user reported the Barracks button only AFTER building
    a Castle (m26421).  Preferring the ARRAY over the name is the whole fix.

    Ranking, strongest first:

      1. ``required_techs`` empty -- satisfied before the game starts.
      2. no research location -- a tech researched in a building is user-triggered,
         so pointing a grant at one produces nothing until someone researches it.
      3. the name preference, which only breaks ties now.
      4. array index, so the choice never depends on dictionary iteration order.

    Returns ``(index, tech, reason)``.  ``reason`` is ``""`` on success, otherwise it
    says why no tech could be used -- a civilization with no owned tech cannot receive
    a grant this way, and the caller must say so instead of writing a dead effect.
    """

    def _early(t):
        """0 when the tech fires at 0:00, 1 when it waits for an age."""
        return 0 if not t.get("required_techs") else 1

    def _untargeted(t):
        """0 when no building researches it, 1 when one does."""
        return 0 if not t.get("research_locations") else 1

    owned = []
    for i, t in enumerate(techs):
        if isinstance(t, dict) and t.get("civ") == civ_index:
            owned.append((i, t))
    if not owned:
        return None, None, ("civilization %d owns no technology, so there is no "
                            "effect list to attach a make-available command to"
                            % civ_index)
    _name = (prefer_name_contains or "").lower()
    owned.sort(key=lambda it: (_early(it[1]), _untargeted(it[1]),
                               0 if _name and _name in (it[1].get("name") or "").lower() else 1,
                               it[0]))
    i, t = owned[0]
    return i, t, ""


def connection_offset(raw, gv, unit_id):
    """Byte offset of ``unit_id``'s `EnablingResearch` i32 in ``raw``.

    Walks the `.dat` TechTree section the way the shipped layout describes: after the
    seven tail i32, `u8 ages, u8 buildings, i16 units, u8 research, i32`, then each
    connection as `i32 id, u8 status, i32 upper, common, i32 vertical, group,
    i32 location, i32 required, i32 line, i32 enabling`.

    Raises ``KeyError`` if the unit has no connection -- which is meaningful: a unit
    with no connection cannot be enabled this way, and the caller should say so
    rather than silently do nothing.
    """
    from ..dat import parser as P
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    for _ in range(n_units):
        uid = r.i32(); r.u8()
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); r.i32()
        r.i32()
        o = r.pos
        en = r.i32()
        if uid == unit_id:
            return o, en
    raise KeyError("unit %d has no TechTree connection, so EnablingResearch cannot "
                   "point at a technology for it" % unit_id)


def button_offset(raw, gv, civ_index, unit_id, building_id):
    """Byte offset of ``unit_id``'s `ButtonID` for ``building_id``, in ``raw``.

    The button slot cannot be a MODEL edit: the writer's model
    (``Parser.stats["civs"][i]["units"][j]``) keeps only
    `class/hit_points/id/name/task_swap_group/type`, so `train_locations` is not there
    at all -- an earlier draft of `apply_grant` looked for it and silently got ``None``.
    The full model, including `_off_train_time`, is ``locate``'s.

    Layout from `parser.read_train_location`: `TrainTime(i16), UnitID(i16),
    ButtonID(u8)`, so the button byte is `_off_train_time + 4`.
    """
    from ..dat import locate as L
    with contextlib.redirect_stdout(io.StringIO()):
        pr = _parser_for(raw)
        pr.parse()
    civs, _cs, _gv, _tail = L.locate(raw, parser=pr)
    if civ_index >= len(civs):
        raise KeyError("no civ record at index %d" % civ_index)
    for u in civs[civ_index].get("units") or []:
        if u.get("id") != unit_id:
            continue
        for t in u.get("train_locations") or []:
            if t.get("unit_id") == building_id:
                return t["_off_train_time"] + 4, t.get("button_id")
    raise KeyError("unit %d is not trainable at building %d for civ index %d, so "
                   "there is no button slot to move"
                   % (unit_id, building_id, civ_index))


def _parser_for(raw):
    from ..dat import parser as P
    return P.Parser(raw)


def apply_grant(stats, raw, gv, civ_index, civ_record, tree, unit_id,
                tech_index, building_id, trees=None, donor_slot=None):
    """Make the `.dat` edits and return ``(patched_bytes, report)``.

    ``stats`` is the parsed writer model (it IS mutated: the caller works on its own
    copy).  ``raw`` is the decompressed base stream.  ``trees`` is the whole
    ``{civ_key: tree}`` map, needed only to look up the donor row's `Node Type`; pass
    ``None`` and the node type is simply unknown, which only affects slot preference.

    Every byte-level offset is derived on the SERIALIZED stream, never on ``raw``:
    appending an effect moves the TechTree stage (measured: 93237962 -> 93238024 in
    the v5 build), and a stale offset would patch the wrong bytes without erroring.

    Two of the `.dat` inputs are model edits (the new effect, and the tech that points
    at it); the third is a byte patch, because the writer's model does not carry it:

      * the unit's `ButtonID` (`Parser.stats` has no `train_locations` at all -- an
        earlier draft looked for it there and silently got ``None``)

    `TechTree.UnitConnection.EnablingResearch` is READ (so the report can say what it
    holds) but NOT WRITTEN; see the module docstring for the three measurements behind
    that decision.

    Returns ``(bytes, report)``; ``report["ok"]`` is False with a ``reason`` when no
    slot is free, and then no bytes are produced.
    """
    from ..dat import writer as W
    from ..game import buttons as BT

    report = {"unit": unit_id, "civ_index": civ_index, "tech": tech_index,
              "edits": []}

    # A free slot must exist BEFORE anything is written, or the unit would be masked
    # exactly as dsh test v4 was.
    #
    # The node TYPE decides the preferred slot, and the target civ usually has no row
    # yet -- that is the whole point of a grant.  So fall back to the DONOR row's Node
    # Type: asking the target only would answer `None` and silently drop to the lowest
    # free slot, which for the British is 3 rather than the shipped convention 4
    # (measured, by comparing this module against the hand-built dsh test v5).
    _row = CT.row_for(tree, unit_id, CT.UNIT_USE_TYPES)
    node_type = (_row or {}).get("Node Type")
    if node_type is None and trees is not None:
        _donor_civ, _donor_row = CT.donor_row(trees, unit_id, CT.UNIT_USE_TYPES)
        if _donor_row is not None:
            node_type = _donor_row.get("Node Type")
    slot, why = BT.choose_slot(civ_record, tree, building_id, node_type=node_type,
                               donor_slot=donor_slot)
    if slot is None:
        return None, {"ok": False, "reason": why, **report}
    report["node_type"] = node_type
    report["button_slot"] = slot

    # --- model edits: a new effect, and the tech that points at it -------------
    #
    # ★★ The new effect must CARRY OVER the anchor effect's existing commands.
    # Re-pointing the tech at a fresh single-command effect does not add the grant,
    # it replaces whatever the anchor was doing -- and the anchor is chosen to be a
    # technology the civilization owns and that fires at 0:00, which is exactly where
    # the civilization bonuses live.  Measured on the shipped data: tech 383
    # 'C-Bonus, +25% Shepherd' owns effect 381 =
    # [(5, 592, -1, 13, 1.25), (5, 590, -1, 13, 1.25)], so a module that did not copy
    # them would silently delete the British faster-shepherd bonus while reporting
    # ok=True.  The hand-built `dsh test v5` copied the commands and that is why the
    # game accepted it (its effect 1500 held BOTH the Longbowman and the Champi
    # Scout enables); this module did not, and no test compared the two.
    #
    # The copy is a NEW record rather than an append onto the old one: `write_effect`
    # can only grow a record through its `_new` path, and mutating an existing
    # effect's command list makes the writer's model and raw cursors disagree
    # (measured: the re-parse dies in `read_bird` with `struct.error: bad char in
    # struct format`).
    old_effect = stats["techs"][tech_index].get("effect_id")
    carried = []
    if isinstance(old_effect, int) and 0 <= old_effect < len(stats["effects"]):
        for c in (stats["effects"][old_effect].get("commands") or []):
            if isinstance(c, dict):
                carried.append((c["type"], c["a"], c["b"], c["c"], c["d"]))
            else:
                carried.append(tuple(c))
    stats["effects"].append({
        "name": "make unit %d available (was effect %s)" % (unit_id, old_effect),
        "commands": carried + [enable_command(unit_id)],
        "_new": True,
    })
    stats["effect_count"] = len(stats["effects"])
    new_effect = len(stats["effects"]) - 1
    stats["techs"][tech_index]["effect_id"] = new_effect
    report["effect"] = {"index": new_effect, "was": old_effect,
                        "carried_commands": len(carried)}
    report["edits"].append({"what": "effect+tech", "effect": new_effect,
                            "tech": tech_index, "was_effect": old_effect})
    if not carried and isinstance(old_effect, int) and old_effect >= 0:
        # Not fatal, but the caller should be able to say "this anchor had nothing
        # else on it" rather than implying the copy happened.
        report["anchor_effect_was_empty"] = True

    out, rep = W.serialize_dat(stats, raw=raw, gv=gv)
    report["serialize"] = {"bytes": len(out), "delta": len(out) - len(raw),
                           "model_vs_raw_mismatches":
                           rep.get("model_vs_original_mismatches")}

    # --- byte patches on the serialized stream ---------------------------------
    #
    # ONE byte is written: the training button.  `connection_offset` is still called
    # so the report can say what `EnablingResearch` currently holds -- but the value
    # is NOT overwritten.  See the module docstring: the confirmed recipe wrote no
    # such byte, the field does not gate (v5 vs v6 in game), and it is global per
    # unit id, so pointing it at one civ's private technology would claim that all 63
    # civilizations are enabled by it.  The shipped corpus has no precedent for that.
    eoff, ebefore = connection_offset(out, gv, unit_id)
    boff, bbefore = button_offset(out, gv, civ_index, unit_id, building_id)
    patched = bytearray(out)
    patched[boff] = slot
    patched = bytes(patched)
    changed = [i for i in range(len(out)) if out[i] != patched[i]]
    report["enabling_research"] = {"offset": eoff, "was": ebefore,
                                   "now": ebefore, "written": False}
    report["button"] = {"offset": boff, "was": bbefore, "now": slot}
    report["edits"].append({"what": "button",
                            "bytes_changed": len(changed),
                            "offsets": [boff],
                            "size": len(changed)})
    report["bytes_changed"] = len(changed)
    report["ok"] = True
    return patched, report

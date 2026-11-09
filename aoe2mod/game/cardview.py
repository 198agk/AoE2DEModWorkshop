# -*- coding: utf-8 -*-
"""One building's command card, shaped for a screen.

WHY THIS MODULE EXISTS
----------------------
`aoe2mod/dat/card.py` already reads a card out of the `.dat`, but it answers in
`.dat` terms: a raw `{unit, button, train_time, icon_id, name}` row where `name`
is the record's INTERNAL name (`SPRMN`), not the name a player reads.  A screen
cannot draw that, and the Rust backend grew its own answer (`cards.rs` +
`/api/card`) while the Python backend simply had no route at all -- measured
2026-10-28: `GET /api/card?building=12` returned **404** on port 7799 while the
same request returned 200 on the native port.  A blank command panel and one
console error was the whole visible symptom.

So this module is the join: `.dat` truth + displayed names + civilisations'
trees + the game's own grid size.  Four measured facts shape the answer, and
getting any of them wrong draws a plausible card the game never shows:

1.  **`button_id` is a CHAIN number, not a slot.**  Barracks box 1 holds 16
    units (militia -> man-at-arms -> long swordsman ...); box 4 holds 28.  A card
    that printed one unit per box would be wrong about 45 of 49 entries.
2.  **The `.dat` is a SUPERSET.**  The barracks lists 49 units there; one
    civilisation's tree lists 8.  This module reports the `.dat` truth in
    `unit_count` and the narrowed slice in `shown_count`, so a caller can see how
    much was filtered instead of being handed a smaller number with no way to
    know it was ever larger.
3.  **A building with no card is not "empty".**  `has_data` says which case the
    caller is looking at.
4.  **The grid is 15 boxes, 5x3** -- read from `widgetui/commandpanel.json`,
    which is where the game places the panel.  The `.dat` reaches `button_id` 24
    on the Dock (campaign heroes, hidden units); those are listed under the grid
    with their ids intact rather than drawn as boxes, because a stored id is not
    a capacity.

`excluded` and `unlisted` are reported SEPARATELY for the same reason the Rust
side does: `excluded` is the tree saying `NotAvailable` in writing, while
`unlisted` is the tree not mentioning the node at all -- which is how regional
units (the Eagle line, in 2 of 62 trees) disappear, and ALSO how campaign and
chronicle units disappear (in no tree at all).  Collapsing them would let a
chronicle unit read as "this civ was denied it".
"""
import json
import os

from ..dat import card as CARD

#: The measured grid, used when `widgetui/commandpanel.json` is unreadable.
#: 5 columns x 3 rows; kept equal to the file this install ships (asserted against
#: the real file, not asserted into existence).  A missing layout means an
#: incomplete install, and refusing to show anything would be worse than using
#: the number that file holds today -- so the caller is TOLD which one it used.
FALLBACK_SLOTS = 15

#: The button ids the engine DRAWS, inclusive.  Measured 2026-11-07 over all 62
#: civilizations, counting only entries that civilization's own tree says it
#: can build:
#:
#:   * the buildable boxes are ``1..15`` and nothing else -- box 15 is real
#:     (Dravidians' Dock, 楼船, 40 s), which is why a grid of ``0..14`` was
#:     wrong in BOTH directions: it invented an empty first box and pushed the
#:     real last one outside the grid;
#:   * box 0 holds **27,838** stored entries (the Town Centre's villager
#:     gathering buttons, the Gate's three forms) and **zero** of them are
#:     buildable in any civilization -- each of those unit ids appears in no tech
#:     tree at all, so the engine never draws that box;
#:   * ``16..24`` hold 372 more, all campaign heroes on the Dock, also zero
#:     buildable.
#:
#: So 「第 N 格」 in the game and ``button_id`` are the same number, and the
#: number starts at 1.  A player who wrote 32 found that it did nothing because
#: there is no 32nd box: the panel is 5 columns x 3 rows, with no paging control
#: anywhere in ``widgetui/commandpanel.json``.
ENGINE_FIRST = CARD.ENGINE_FIRST
#: How many boxes ONE screen holds -- 5 columns x 3 rows, read from
#: ``widgetui/commandpanel.json`` (15 `CommandButton` widgets under
#: `BackgroundLeft/Buttons`, measured again 2026-11-08 by walking
#: `Collection -> Widgets -> ChildWidgets`, which is the only path that reaches
#: them).
PAGE_BOXES = CARD.PAGE_BOXES
#: How many screens the engine pages through when ids past the first screen are
#: present.  The player measured this on 2026-11-08 (「游戏默认是支持2页伪翻页
#: 的」): writing box 16..30 makes the engine draw its own red arrow on box 15 and
#: on box 30; 31 and up are honoured by the parser and never drawn.
PAGE_COUNT = CARD.PAGE_COUNT
#: The largest box the engine will actually show.  Kept separate from
#: `PAGE_BOXES` because they answer different questions -- how many boxes a
#: screen holds, and how many boxes exist across all screens.
ENGINE_LAST = CARD.ENGINE_LAST

COMMANDPANEL_REL = os.path.join("widgetui", "commandpanel.json")


def card_slots(game_root):
    """``(slots, from_file)`` -- how many boxes the game draws.

    `from_file` is False when the layout could not be read and
    :data:`FALLBACK_SLOTS` was used, so the caller can say so instead of
    presenting a guess as a measurement.
    """
    path = os.path.join(game_root, COMMANDPANEL_REL)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return FALLBACK_SLOTS, False
    n = _count_command_buttons(doc)
    if n and 0 < n < 256:
        return n, True
    return FALLBACK_SLOTS, False


def _count_command_buttons(doc):
    """`CommandButton` children of `BackgroundLeft` -> `Buttons`, or None.

    `BackgroundRight` also has `CommandButton` children, and those are the
    group/queue buttons -- a different grid that would inflate the count to 36 if
    mixed in.
    """
    try:
        widgets = doc["Collection"]["Widgets"]
    except (KeyError, TypeError):
        return None
    left = _named(widgets, "BackgroundLeft")
    if left is None:
        return None
    buttons = _named(left.get("ChildWidgets") or [], "Buttons")
    if buttons is None:
        return None
    n = 0
    for w in buttons.get("ChildWidgets") or []:
        o = w.get("Widget", w)
        if o.get("Type") == "CommandButton":
            n += 1
    return n


def _named(widgets, name):
    for w in widgets or []:
        o = w.get("Widget", w)
        if o.get("Name") == name:
            return o
    return None


def building_ids(cards):
    """The building ids that HAVE a card, in id order.

    `stepCard` in the page walks a list like this so its arrows never land on a
    building the game gives no card at all.  Derived from the data rather than
    hand-listed, because the 18 shipped cards are a property of the `.dat`.
    """
    return sorted(int(k) for k in cards if str(k).lstrip("-").isdigit())


def card(civs, civ_index, builder_id, slots=FALLBACK_SLOTS, icons=None,
         names=None, narrow_tree=None, narrow_status=None, builders=None,
         ages=None, techs=None, tech_icons=None, tech_names=None,
         tech_status=None, tech_ages=None, upgrades=None):
    """One building's card as ``{ok, building, name, has_data, slots, ...}``.

    ``civs`` / ``civ_index`` locate the `.dat` civ list (``Toolkit._civs`` and
    the index of the civ being asked about).  ``icons`` maps unit id -> icon id
    when the caller has a better table than the record's own field.

    ``narrow_tree`` is a parsed `CivTechTrees/<CIV>.json`; when given, entries are
    split by that civilisation's tree into kept / ``excluded`` / ``unlisted``.
    ``narrow_status(tree, node)`` is the status reader, injected so this module
    never imports the tree module and the two cannot disagree about the answer.

    ``ages`` maps unit id -> the age (1..4) that unit first appears in, from the
    build panel's `RequiredAge` (see `buildpanel.required_age_vote`).  With it,
    every row and every box carries ``age``, which is the field 「应该按时代来分」
    was asking for; without it nothing changes, so a caller that has no panel
    file (a stripped install) still gets a card.

    ``upgrades`` maps a unit id -> the list of ``{tech, tech_name, to}`` entries
    that REPLACE it: the technology you research and the unit the card then shows
    instead.  A box holding several units is a chain, and the chain is driven by
    real technologies, so without this the panel can say "5 units" but not "which
    five upgrades put them there".  ``None`` leaves every row unchanged.

    ``builders`` maps unit id -> the list of civilizations that can ever build
    it (`civtechtrees.builders`).  When given, every unit row carries
    ``civ_count`` and ``civ_sample``, which is how the panel answers 「这一格里
    16 个是什么」 -- the honest answer is "16 chains, 5 of which this civ can
    build", and a screen that only prints 16 cannot say that.
    """
    slots = int(slots or 0) or FALLBACK_SLOTS
    rows = CARD.card(civs, civ_index, builder_id)
    has_data = bool(rows)

    kept, excluded, unlisted = rows, [], []
    if narrow_tree is not None and narrow_status is not None:
        kept = []
        for r in rows:
            st = narrow_status(narrow_tree, r["unit"])
            if st == "NotAvailable":
                excluded.append(r["unit"])
            elif st is None:
                unlisted.append(r["unit"])
            else:
                kept.append(r)

    # Group by box, first-seen order: the chain order IS the upgrade line, so
    # re-sorting by unit id would silently reshuffle the card.
    order = []
    grouped = {}
    for r in kept:
        b = r.get("button")
        if b is None:
            continue
        if b not in grouped:
            order.append(b)
            grouped[b] = []
        grouped[b].append(_entry(r, icons, names, builders, ages, upgrades))
    order.sort()

    # Research buttons live in a different array from training buttons (see
    # `techs_from_records`), and they share the SAME box numbers, so they are
    # merged into the same `order` instead of being drawn as a second grid --
    # box 7 on the Barracks can hold a chain of units, a technology, or both,
    # and the panel has to say which.
    # A research button belongs to a civilization exactly like a training entry
    # does, and the first version only narrowed the units: picking 法兰克 then
    # showed 精锐希腊步兵 and 精锐瓦兰吉卫队 on the Barracks' box 9 -- buttons
    # that civilization can never press.  Reported 2026-11-09: 「文明也是，应该
    # 只显示该文明拥有的」.  The tree answers this per tech id, so the same
    # NotAvailable rule applies; what is dropped is reported in `tech_excluded`
    # so the panel can still say "this civ has 4 of the 10 on this box".
    tech_rows = list(techs or ())
    tech_excluded = []
    tech_unlisted = []
    if narrow_tree is not None and tech_status is not None:
        keep = []
        for t in tech_rows:
            st = tech_status(t["tech"])
            # Three answers, not two, and they differ: `NotAvailable` is the tree
            # saying "not for this civilization", while `None` is the tree not
            # naming the id at all -- the Barracks lists 29 research buttons for
            # 法兰克 and the Franks tree names 3 (供给/软甲/战斗操练/护卫/纵火).
            # The other 26 are other civilizations' unique upgrades that share
            # this .dat, which is why keeping them printed 精锐瓦兰吉卫队 on a
            # Franks card.  Both kinds go; they are counted apart so the panel
            # can still say how many it is hiding.
            if st == "NotAvailable":
                tech_excluded.append(t["tech"])
            elif st is None:
                tech_unlisted.append(t["tech"])
            else:
                keep.append(t)
        tech_rows = keep
    tgrouped = {}
    for t in tech_rows:
        b = t.get("button")
        if b is None:
            continue
        if b not in tgrouped:
            tgrouped[b] = []
        tgrouped[b].append(_tech_entry(t, tech_icons, tech_names, tech_status,
                                       tech_ages))
    for b in tgrouped:
        if b not in grouped:
            grouped[b] = []
            order.append(b)
    order.sort()

    # The engine shows boxes 1..30 across two screens (see ENGINE_FIRST /
    # PAGE_BOXES / PAGE_COUNT).  Everything else the `.dat` stores is reported,
    # never drawn: box 0's 27,838 entries are units that appear in no tech tree,
    # and anything past 30 is a byte the parser keeps and the panel never shows.
    # Drawing them as empty boxes -- which is what a 0..14 grid did -- invented a
    # box the player cannot use and hid the one they can.
    in_grid = [b for b in order if ENGINE_FIRST <= b <= ENGINE_LAST]
    off_grid = [b for b in order if b not in in_grid]
    # Which screens actually carry something.  The engine only grows its arrow
    # when the second screen has content, so the page's page-switch must follow
    # the data and not the constant: a card whose boxes stop at 12 has one screen
    # and must not offer a second one that would draw fifteen empty boxes.
    used_pages = sorted({CARD.page_of(b) for b in in_grid})

    boxes = [{"button": b,
              "count": len(grouped[b]),
              "tech_count": len(tgrouped.get(b) or ()),
              "techs": tgrouped.get(b) or [],
              # `count > 1` means this box is a CHAIN, not a single unit -- the
              # one fact a caller must not flatten.
              "is_chain": len(grouped[b]) > 1,
              "buildable": sum(1 for e in grouped[b] if e.get("civ_count")),
              # A box whose units span two ages is a box that cannot be filed
              # under one era honestly, so the box reports the EARLIEST and says
              # whether it spans.  The Barracks' box 1 is one age (1, the
              # militia); a mod that files a Champion next to it would span
              # 1..4, and a filter that dropped such a box would lose the whole
              # chain -- hence `age_span` rather than a single answer.
              # A research button carries its own era in the tech tree (`Age
              # ID`, present on all 5,244 tech rows), so a card that is nothing
              # but research buttons -- University, Blacksmith, Outpost -- can
              # still be filtered by era instead of vanishing whenever a filter
              # is on.  Units win when a box has both: they are what the box is
              # drawn for.
              "age": _span_age(grouped[b]) or _span_age(tgrouped.get(b) or ()),
              "age_span": _age_span(grouped[b]) or _age_span(tgrouped.get(b) or ()),
              # Which screen of the panel this box lives on. The page draws one
              # screen at a time and needs the number on every box, because the
              # box numbers on screen 2 are 16..30 and a grid built from
              # `index + 1` would label them 1..15.
              "page": CARD.page_of(b),
              "units": grouped[b]}
             for b in in_grid]
    off = [{"button": b, "count": len(grouped[b]),
            "tech_count": len(tgrouped.get(b) or ()),
            "techs": tgrouped.get(b) or [],
            "buildable": sum(1 for e in grouped[b] if e.get("civ_count")),
            "units": grouped[b]}
           for b in off_grid]

    body = {
        "ok": True,
        "building": int(builder_id),
        "name": _name_of(builder_id, names),
        "has_data": has_data,
        "slots": slots,
        "first": ENGINE_FIRST,
        "last": ENGINE_LAST,
        # One screen holds `page_boxes` boxes; `pages` lists the screens this
        # card actually uses (1..2). Both are reported rather than left for the
        # page to derive, because the page would derive them from `slots`, which
        # is the file's own count and has nothing to do with paging.
        "page_boxes": PAGE_BOXES,
        "page_count": PAGE_COUNT,
        "pages": used_pages,
        "box_count": len(boxes),
        # Stays the `.dat` total even when narrowed (see fact 2 in the module
        # docstring).
        "unit_count": len(rows),
        "tech_count": len(tech_rows) + len(tech_excluded) + len(tech_unlisted),
        "shown_count": len(kept),
        "boxes": boxes,
        "off_grid": off,
        "building_ids": building_ids_from_rows(civs, civ_index),
        # A card can hold ONLY research buttons -- Outpost, University,
        # Blacksmith, Mill, Lumber Camp, Mining Camp, Wonder.  Saying "this
        # building has no training entries" on those was true and useless: the
        # player was looking at a full card.
        "note": ("" if (has_data or tech_rows)
                 else "这个建筑在 .dat 里既没有训练条目，也没有研究按钮"),
    }
    if narrow_tree is not None:
        body["excluded"] = excluded
        body["unlisted"] = unlisted
        body["hidden"] = excluded + unlisted
        body["hidden_count"] = len(body["hidden"])
        body["tech_excluded"] = tech_excluded
        body["tech_unlisted"] = tech_unlisted
        body["tech_shown"] = len(tech_rows)
    return body


def building_ids_from_rows(civs, civ_index):
    """Every building this civ's units name as a producer, in id order.

    The page's arrows need the set of buildings that HAVE something on them, and
    the `.dat` answers that directly: a card exists iff some unit's train
    locations name that building.  Hand-listing 18 ids would be a second copy of
    a fact the data already holds.
    """
    out = set()
    for u in civs[civ_index]["units"]:
        for tl in u.get("train_locations") or ():
            bid = tl.get("unit_id")
            if bid is not None and bid >= 0:
                out.add(int(bid))
    return sorted(out)


def host_ids(civs, civ_index, trees=None, records=None, panel_ids=None):
    """Every id that can carry a command card, from all four sources.

    WHY NOT `building_ids_from_rows` ALONE (2026-11-09, 「这个列表不全，很多都没
    读出来…举个例子比如哨站里也能放的」): that function reads ONE source -- the
    training entries -- and therefore answers "which buildings train something",
    which for the British is 18.  Outpost (598), University (209), Blacksmith
    (103), Mill (68), Lumber Camp (562), Mining Camp (584), Wonder (276) and
    Settlement (2556) train nothing at all; their cards hold RESEARCH buttons,
    which live in a different array.  The full set is the union of:

    * training hosts  -- `train_locations[].unit_id` (18 for the British);
    * research hosts  -- `research_locations[].location_id` (25);
    * the build-panel file's `Buildings[].ID` (40);
    * every `Use Type == "Building"` node in this civ's tech tree (40).

    The union is 48 for the British, and the difference is exactly the cards the
    panel was calling empty.  Four sources are used on purpose: each one is the
    authority for a different question (can it train / can it research / does the
    build panel place it / does this civ's tree grant it), and any single one
    drops real cards.

    Each entry says whether the host is a BUILDING or a UNIT, because 4 real
    hosts are units -- the Trading Ship researches the three ``Trade x% wood``
    buttons, the Fishing Ship builds Fish Traps, the Villager builds everything,
    and location 0 is the moving map revealer.  An editor that only offers
    type-80 ids cannot reach them.
    """
    kinds = {}

    def _note(i, kind):
        i = int(i)
        if i >= 0 and i not in kinds:
            kinds[i] = kind

    for u in civs[civ_index]["units"]:
        for tl in u.get("train_locations") or ():
            bid = tl.get("unit_id")
            if bid is not None and bid >= 0:
                _note(bid, "building")
    for r in records or ():
        for loc in (r.get("research_locations") or ()):
            lid = loc.get("location_id")
            if lid is None or int(lid) < 0:
                continue
            _note(lid, "building")
    for i in (panel_ids or ()):
        _note(i, "building")
    if trees:
        for j in (trees.get("civ_techs_buildings") or ()):
            if j.get("Use Type") == "Building" and j.get("Node ID") is not None:
                _note(j["Node ID"], "building")
    out = []
    for i in sorted(kinds):
        out.append({"id": i, "kind": kinds[i]})
    return out


def techs_from_records(records, host_id, names=None):
    """Every TECHNOLOGY whose research button sits on ``host_id``.

    WHY THIS EXISTS (2026-11-09, 「单位里好像也能放科技」): a technology's button
    is NOT stored on the building.  It hangs on the technology record itself --
    ``research_locations[].location_id`` is the HOST -- exactly the mirror image
    of how units hang on ``train_locations``.  The panel only ever read the unit
    half, so every research button in the game was invisible to it, and the
    building list it offered was really "buildings that train something".

    ``host_id`` may be a BUILDING or a UNIT, and both are real: 417 shipped
    research locations name a building (castle 82 alone holds 211) and 3 name a
    unit (Trading Ship 17 carries ``Trade 0%/50%/100% wood``).  Anything that
    asks only for type-80 ids will silently drop those.

    A record carries NO id field -- a technology is addressed by its position in
    the array -- so the index in ``records`` IS the id, and that is what is
    returned as ``tech``.

    ``location_id`` 0 is a real host too (164 records) and it is the moving map
    revealer; -1 is the "no host" sentinel and is skipped by the caller asking
    for an id >= 0.
    """
    out = []
    for tid, r in enumerate(records or ()):
        for loc in (r.get("research_locations") or ()):
            if loc.get("location_id") is None:
                continue
            if int(loc["location_id"]) != int(host_id):
                continue
            out.append({"tech": tid,
                        "button": loc.get("button_id"),
                        "research_time": (loc.get("research_time")
                                          if loc.get("research_time") is not None
                                          else r.get("research_time")),
                        "name": r.get("name"),
                        "_record": r})
    out.sort(key=lambda r: (r["button"] if r["button"] is not None else 999,
                            r["tech"]))
    return out


def _span_age(rows):
    """The earliest age in a box's units, or None."""
    got = [r.get("age") for r in rows if r.get("age")]
    return min(got) if got else None


def _age_span(rows):
    """``[low, high]`` when a box's units come from more than one age, else None.

    Kept apart from :func:`_span_age` because they answer different questions:
    "which era do I file this box under" and "is filing it under one era a
    lie".  Collapsing them into one number is how a filter silently drops half a
    chain.
    """
    got = [r.get("age") for r in rows if r.get("age")]
    if len(got) < 2:
        return None
    lo, hi = min(got), max(got)
    return [lo, hi] if lo != hi else None


def _tech_entry(row, icons, names, status=None, ages=None):
    """One research button as the page draws it.

    ``icons`` maps tech id -> icon id (the record's own ``icon_id`` is 0 for
    974 of 1,510 technologies, so the caller's table wins when it has one).
    ``names`` maps tech id -> the player-readable name; the record's own
    ``name`` field is the ENGLISH internal string and is what the panel showed
    before, which read "Fortified Outpost" to a Chinese player.
    ``status`` is an optional ``(tech_id) -> "NotAvailable" | None`` reader used
    when a civilization is selected.
    """
    tid = row["tech"]
    icon = None
    if icons is not None:
        icon = icons.get(tid)
    if icon is None:
        icon = row.get("_record", {}).get("icon_id")
    if icon is None or icon < 0:
        icon = -1
    name = _name_of(tid, names) or row.get("name") or ("tech " + str(tid))
    out = {"tech": tid,
           "name": name,
           "internal": row.get("name"),
           "icon_id": icon,
           "seconds": row.get("research_time") or 0,
           "off_button": None}
    if status is not None:
        st = status(tid)
        out["status"] = st
        out["available"] = (st != "NotAvailable")
    if ages is not None:
        out["age"] = ages.get(tid)
    return out


def _entry(row, icons, names, builders=None, ages=None, upgrades=None):
    unit = row["unit"]
    icon = None
    if icons is not None:
        icon = icons.get(unit)
    if icon is None:
        icon = row.get("icon_id")
    if icon is None or icon < 0:
        icon = -1
    out = {"unit": unit,
           "name": _name_of(unit, names),
           "icon_id": icon,
           "seconds": row.get("train_time") or 0,
           "off_button": None}
    if builders is not None:
        who = builders.get(unit) or ()
        out["civ_count"] = len(who)
        out["civ_sample"] = list(who[:3])
    if ages is not None:
        # `None` when the panel file does not list this node at all -- 1,095 of
        # 3,984 panel rows have no tree age, and a missing answer must read as
        # missing, not as age 1.
        out["age"] = ages.get(unit)
    if upgrades is not None:
        # WHAT REPLACES THIS UNIT.  A card box is not a list of alternatives:
        # it is one button whose picture changes as you research, and the
        # technologies that change it are the reason several unit ids share the
        # same byte.  Reported 2026-11-09: 「确实是要通过研究科技才会把升级后的
        # 单位放同一个格子来覆盖前面的」.  Each entry is the tech that does the
        # swap and the unit it swaps TO, so the panel can print
        # 「民兵 —(武士)→ 封建」 instead of a bare arrow between names.
        got = upgrades.get(unit) or ()
        out["upgrades"] = [{"tech": u.get("tech"),
                            "tech_name": u.get("tech_name") or "",
                            "to": u.get("to"),
                            "to_name": _name_of(u.get("to"), names)}
                           for u in got]
    return out


def _name_of(unit_id, names):
    """The name a player reads, from whichever table the caller supplied.

    Two shapes are accepted because two do exist in this codebase: a plain
    ``{id: str}`` and the `entity_names.json` shape ``{id: [zh, en, tw, stem]}``.
    Both are joined here so a caller does not have to know which one it holds.
    """
    if not names:
        return ""
    got = names.get(unit_id)
    if got is None:
        got = names.get(str(unit_id))
    if got is None:
        return ""
    if isinstance(got, (list, tuple)):
        return str(got[0] or "") if got else ""
    return str(got)

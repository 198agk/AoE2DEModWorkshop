"""Add a unit record that the shipped file does not have.

Twenty years of editors have done this, and the structure allows it: a civ's
unit table is a list of per-id EXISTENCE FLAGS (measured on the shipped file:
2,750 slots for ids 0..2749, every non-zero value is 1), followed by the records
themselves in slot order.  So "a new unit" is two changes, neither of which
resizes anything:

  * one slot 0 -> 1 in that civ's flag array (a 4-byte in-place write)
  * one record appended to that civ's record run

The record is a BYTE IMAGE of a donor record with a few fields patched.  It is
not rebuilt field by field on purpose: a unit record's tail is type-dependent
(Type50 / Projectile / Creatable / Building, each with its own version guards),
so rebuilding from zeros is one guess per field.  A clone is right by
construction -- its animations, sounds, size, armour classes and train locations
are the donor's, which is exactly what "a new unit like that one" means.

What a clone does NOT give you: a name, an icon, and a place in a build menu.
- the name needs a string id, which ships as a loose mod file (see
  `aoe2mod/mod/strings.py`)
- the icon is an id into `widgetui/icons.json`; units 0..999 are all taken, so a
  clone shares the donor's icon unless the player overrides it
- `train_locations` are copied from the donor, which means the clone appears in
  the same building buttons as the donor.  That is the honest default: a unit
  nobody can build is not a feature.

Measured 2026-10-21 (donor 83, civ 1): a clone is +2,387 bytes, the stream
re-parses, the new id reads back with the donor's class and hit points, and
re-serialising the result is byte-stable (delta +0).
"""
import struct

from . import locate as L


class NewUnitError(Exception):
    """A clone request that cannot be honoured; the message is player-facing."""


FREE_ID_MIN = 2700          # above the highest id any shipped record uses (2749
                            # is taken by graphics-only entries; see free_ids)
HEADER_SLOTS = 1701         # unit_headers has indices 0..1700 only
# Where a NEW unit's id starts.  Past every shipped record (highest is 2,749) and
# past a wide margin, because the shipped numbers are the ones a game update will
# reuse: picking a hole in the shipped range means the next patch can put a real
# unit there and the clone becomes a second meaning for that id.  Measured: the
# pointer array can be extended to this range and the stream re-parses (ids
# 2750 / 3000 / 4000 / 5000 all round-trip, +4 bytes per added slot).
#
# The cost, stated honestly: `unit_headers` only has indices 0..1700, so an id
# here is NOT addressable by the editor or scenario triggers.  It still shows in
# game and still builds -- measured on a real shipped unit (villager 1810) whose
# id is above the header range and whose tooltip renders normally.
NEW_ID_START = 30000
# The flag array is an i16-prefixed list, so this is a hard ceiling.
NEW_ID_MAX = 32000
# A command card is a numbered grid.  Measured over every civ: the numbers
# shipped data actually uses are 0..15 plus 24, and 255 appears 1,890 times as
# the button of a placeholder entry (``unit_id == -1``) -- a sentinel for "no
# button", not a slot.  So the usable range is 0..24 and 255 must never be
# counted as taken or offered as free.
BUTTON_SLOTS = 25
BUTTON_SENTINEL = 255
# Inside one TrainLocation: i16 train_time, i16 unit_id, then the u8 button id.
TRAIN_BUTTON_OFF = 4
# ...and the i16 before it is the BUILDING that shows the button (`unit_id`).
TRAIN_BUILDER_OFF = TRAIN_BUTTON_OFF - 2
# Whole entry: i16 train_time, i16 unit_id, u8 button_id, then (C30+) i32 HotKeyID.
# MEASURED, not read off a doc: 1134 units in the shipped file carry 2+ entries
# and EVERY gap between consecutive `_off_train_time` values is exactly 9; a
# single-entry record shows `00 00 ff ff 00 | 80 3e 00 00` (train_time 0, unit -1,
# button 0, hotkey 16000).  A 5-byte guess spliced one entry and the stream
# stopped parsing inside `read_bird` -- that is what a wrong stride looks like.
TRAIN_ENTRY_BYTES = 9
# Where the record keeps its icon id.  Derived here, not copied from the parser:
# walk the fixed prefix (type u8, id i16, 2 x i32 strings, class i16, 2 x i16
# standing graphic, dying i16, undead i16, undead mode u8, hit points i16, line of
# sight f32, garrison u8, 3 x f32 collision size, 4 x i16 sounds, 2 x u8, then the
# i16) = 51.  Checked against the parsed model on 8 shipped units: 8 of 8 agree
# (83 -> 15, 12 -> 2, 109 -> 28, 2550 -> 540).
ICON_OFF = 51


def unit_spans(raw, gv, civs_start, civ_index):
    """``{unit_id: (start, end)}`` for one civ's records.

    ``civs_start`` MUST be the value ``locate()`` returns -- it already points
    past the i16 civ count.  Reading that count again offsets every later field
    by one byte and yields spans that look plausible and are wrong (that mistake
    produced a 1-byte-short clone that blew up inside ``read_task``).
    """
    rr = L.Orec(raw, civs_start, gv=gv)
    for ci in range(civ_index + 1):
        rr.u8()
        rr.debug_string()
        n = rr.i16()
        rr.i16(); rr.i16()
        rr.f32_array(n)
        rr.u8()
        m = rr.i16()
        ptrs = rr.i32_array(m)
        spans = {}
        for i in range(m):
            if not ptrs[i]:
                continue
            start = rr.o
            u = L.walk_unit(rr, ci)
            spans[u["id"]] = (start, rr.o)
        if ci == civ_index:
            return spans


def donor_image(raw, gv, civs_start, civ_index, donor_id):
    """The donor record's exact bytes."""
    spans = unit_spans(raw, gv, civs_start, civ_index)
    if donor_id not in spans:
        raise NewUnitError("这个文明里没有编号 %s 的单位，所以没有东西可以照着做"
                           % (donor_id,))
    start, end = spans[donor_id]
    return raw[start:end]


def clone_image(image, new_id, name_string_id=None, hp=None,
                creation_string_id=None, icon_id=None):
    """Patch a donor image into a new record.

    Field offsets are fixed by the record header, which every unit record shares:
    ``+0`` type (u8), ``+1`` id (i16), ``+3`` LanguageDLLName (i32),
    ``+7`` LanguageDLLCreation (i32), ``+11`` class (i16), ``+22`` hit points
    (i16).  Everything after that is type-dependent and stays the donor's.

    ``name_string_id`` writes **only** ``+3``.  It deliberately leaves ``+7``
    alone, because ``+7`` is not a second copy of the name: it is the string the
    command-card tooltip prints as its first line, and replacing it with the
    unit's own name erases the whole tooltip body.

    Measured 2026-10-21/22 on four builds that differed in exactly this field:

    ==========  ======  ========  ==============================
    build       +3      +7        tooltip on the new button
    ==========  ======  ========  ==============================
    v30 b4      5121    6121      full: 生产村民（价格：50）+ 描述
    v30 b5      30030002 30030002 empty but for (热键：Q)
    v31 b6      5606    5606      empty but for (热键：Q)
    v33 b6/b7   5606 / 30030002   6121   (this build; measured below)
    ==========  ======  ========  ==============================

    The earlier code wrote the same value to both offsets with the comment
    "creation string is cosmetic".  It is not: it is the tooltip's body, so a
    clone that renamed itself also lost its price and its description, which
    reads to a player as "the new unit is broken" rather than "the tooltip is
    missing a line".

    Pass ``creation_string_id`` only when you have a string id that carries a
    real "生产<名字>" sentence for the new unit.  Otherwise the donor's is the
    honest default: it names the donor, which is exactly what the button does.
    """
    img = bytearray(image)
    if len(img) < 56:
        raise NewUnitError("这份记录太短了（%d 字节），不像是完整的单位记录" % len(img))
    struct.pack_into("<h", img, 1, new_id)
    if name_string_id is not None:
        struct.pack_into("<i", img, 3, name_string_id)
    if creation_string_id is not None:
        struct.pack_into("<i", img, 7, creation_string_id)
    if hp is not None:
        struct.pack_into("<h", img, 22, hp)
    if icon_id is not None:
        if not 0 <= icon_id <= 32767:
            raise NewUnitError("图标号只能是 0..32767，拿到的是 %s" % (icon_id,))
        struct.pack_into("<h", img, ICON_OFF, icon_id)
    return bytes(img)


def train_slots(raw, gv, civs_start, civ_index, donor_id, civs=None):
    """Where the clone would be buildable, and where that button byte lives.

    A unit's place in a build menu is a `train_locations` entry on its OWN
    record, and each entry names the building that shows the button
    (``unit_id``), the button number (``button_id``) and the train time.  A
    clone copies that list, so by default it competes for exactly the donor's
    buttons.

    ``civs`` must be the LOCATED civ list (``Toolkit._civs``), not the parsed
    ``stats`` model: the parser drops ``train_locations`` on the way into stats
    (measured: ``stats["civs"][1]["units"]`` for unit 83 has no
    ``train_locations`` key at all, the located record has one entry).  Passing
    the wrong one silently yields "this donor trains nothing".

    Returns one dict per copied entry: ``builder`` (the building id, -1 for the
    placeholder entries shipped data uses to mean "nobody trains this"),
    ``button``, and ``rel`` -- the offset of that entry's button byte inside
    the record IMAGE, which is what `clone_image` patches.

    Measured layout of a TrainLocation (locate.py, and genieutils'
    TrainLocation.cpp): ``i16 train_time, i16 unit_id, u8 button_id``, then an
    i32 hotkey in C30+.  ``rel`` is derived from the recorded absolute
    ``_off_train_time`` minus the record start, so it is the same number the
    writer would compute rather than a second hand-counted constant.
    """
    if civs is None:
        raise NewUnitError("要传定位过的文明列表（Toolkit._civs），"
                           "解析出来的 stats 里没有训练位置")
    spans = unit_spans(raw, gv, civs_start, civ_index)
    if donor_id not in spans:
        raise NewUnitError("这个文明里没有编号 %s 的单位，所以没有东西可以照着做"
                           % (donor_id,))
    start = spans[donor_id][0]
    civ = civs[civ_index]
    rec = None
    for u in civ["units"]:
        if u["id"] == donor_id:
            rec = u
            break
    out = []
    for tl in (rec or {}).get("train_locations") or ():
        off = tl.get("_off_train_time")
        if off is None:
            continue
        out.append({"builder": tl.get("unit_id"),
                    "button": tl.get("button_id"),
                    "rel": off - start + TRAIN_BUTTON_OFF})
    return out


def used_buttons(civs, civ_index, builder_id):
    """Button numbers that building already shows, across every unit.

    The command card is a grid of numbered slots, and a unit is on it because
    some record names that building and that number -- so "which buttons are
    taken" is a scan of the whole civ, not of the donor.  Like `train_slots`
    this needs the LOCATED civs, where ``train_locations`` survives parsing.
    """
    taken = set()
    for u in civs[civ_index]["units"]:
        for tl in u.get("train_locations") or ():
            if tl.get("unit_id") == builder_id:
                b = tl.get("button_id")
                if isinstance(b, int) and 0 <= b < BUTTON_SENTINEL:
                    taken.add(b)
    return taken


def free_buttons(civs, civ_index, builder_id, limit=BUTTON_SLOTS):
    """Numbers in that building's command card nothing uses yet."""
    taken = used_buttons(civs, civ_index, builder_id)
    return [i for i in range(limit) if i not in taken]


def add_unit(stats, raw, gv, civs_start, civ_index, donor_id, new_id,
             name_string_id=None, hp=None, creation_string_id=None,
             button=None, builder=None, civs=None, civ_zh=None, icon_id=None):
    """Append one clone to ``civ_index``; returns ``(stats, record_dict)``.

    ``stats`` is mutated in place and must be a deep copy the caller owns --
    ``serialize_dat`` reads ``_ptrs`` off every civ, so this also builds that for
    the civs that needed it.

    ``civs`` (the located list) is only needed when ``button`` or ``builder`` is
    given, because the train locations are read from there; passing ``stats``
    instead makes every donor look like it trains nothing.

    ``builder`` re-points the clone's train locations at a different building.
    This is the answer to "a building that never trained the donor": the entry
    that says which building shows the button lives on the UNIT's own record, so
    changing it is a two-byte rewrite of the record the clone already has -- not
    an edit to the building, and not an append.  Measured 2026-10-23: 1134
    shipped units carry two or more entries, every consecutive pair is exactly 9
    bytes apart, and bumping a count + splicing one 9-byte entry re-parses
    cleanly with zero other records touched, so the format was never the wall.

    ``icon_id`` points the clone at an icon slot the caller has already made
    exist (``game/iconart`` writes the picture and the two tables).  It is a
    single i16 at ``ICON_OFF``, so this side of the change is one field; the
    other side -- a slot that names a real material and a texture behind it --
    is why the caller cannot just pass any number.
    """
    civ = stats["civs"][civ_index]
    have = {u["id"] for u in civ["units"]}
    if new_id in have:
        raise NewUnitError("这个文明已经有编号 %s 的单位了，换一个编号"
                           % (new_id,))
    # Free in this civ is not free.  A duplicate id anywhere puts two records
    # behind one flag, and the record count comes from the flags.
    reject_taken_id(stats, new_id, civ_zh=civ_zh)
    if new_id >= HEADER_SLOTS:
        # Not fatal, but say it: nothing indexes a header by this id, so any
        # per-unit header data (tasks, etc.) simply has none.  A clone carries
        # the donor's own sub-records, so this only matters to editor tools.
        pass
    image = donor_image(raw, gv, civs_start, civ_index, donor_id)
    img = clone_image(image, new_id, name_string_id=name_string_id, hp=hp,
                      creation_string_id=creation_string_id, icon_id=icon_id)
    moved = None
    rebuilt = None
    if button is not None or builder is not None:
        if button is None:
            # A builder change alone must not silently keep the donor's number;
            # but it also must not invent one.  Take the donor's own number so
            # the caller sees exactly one thing change per run.
            slots0 = train_slots(raw, gv, civs_start, civ_index, donor_id,
                                 civs=civs)
            button = slots0[0]["button"] if slots0 else 0
        button = int(button)
        if button == BUTTON_SENTINEL or not (0 <= button < BUTTON_SLOTS):
            raise NewUnitError("按钮号只能填 0 到 %d，%s 填不进命令卡"
                               % (BUTTON_SLOTS - 1, button))
        slots = train_slots(raw, gv, civs_start, civ_index, donor_id, civs=civs)
        if not slots:
            raise NewUnitError(
                "「%s」自己没有任何建造位置（它是那种谁都不训练的单位），"
                "所以没有按钮可以挪" % (donor_id,))
        # A placeholder entry has ``unit_id == -1``: the record carries a button
        # number but no building shows it.  Moving such an entry changes bytes
        # and puts the clone nowhere, so refuse instead of promising a button.
        # Measured: 683 British units have only placeholder entries (63 GTAA3,
        # 57 VFFIS ...), 904 have none at all, so this is the common case and
        # not an edge.
        #
        # Unless a BUILDER was named: then the placeholder is exactly what the
        # caller wants to overwrite -- "no building shows this" becomes "this
        # building shows it", which is a two-byte write on an entry that is
        # already there.  The byte positions are real either way, so the only
        # thing -1 rules out is leaving the clone where it was.
        if builder is None and all(s["builder"] in (-1, None) for s in slots):
            raise NewUnitError(
                "「%s」的建造位置没有指向任何建筑（记录里的建筑编号是 -1），"
                "挪按钮也放不到任何菜单上" % (donor_id,))
        if builder is not None:
            builder = int(builder)
            in_civ = {u["id"] for u in civs[civ_index]["units"]}
            if builder not in in_civ:
                raise NewUnitError("这个文明里没有编号 %s 的建筑，没有菜单可以放"
                                   % (builder,))
        # Move EVERY copied entry onto the chosen number and building, keeping the
        # list otherwise intact.  Moving only the first one would leave the rest
        # on the donor's buttons, which is the thing the player asked to stop.
        img = bytearray(img)
        for s in slots:
            before = s["button"]
            struct.pack_into("<B", img, s["rel"], button)
            # Read it back instead of reporting what was asked for: a manifest
            # that says "moved to 5" while the byte still says 14 is worse than
            # a refusal, because nothing downstream would ever question it.
            # Measured: dropping the pack_into above left every assertion green
            # except the one that re-read the emitted file, so this line is what
            # makes the report checkable at the place the report is made.
            if img[s["rel"]] != button:
                raise NewUnitError("按钮没写进去（第 %s 个位置还是 %s）"
                                   % (s["rel"], img[s["rel"]]))
            moved = {"from": before, "to": button, "builder": s["builder"]}
            if builder is not None:
                brel = s["rel"] - (TRAIN_BUTTON_OFF - TRAIN_BUILDER_OFF)
                was_builder = struct.unpack_from("<h", img, brel)[0]
                struct.pack_into("<h", img, brel, builder)
                if struct.unpack_from("<h", img, brel)[0] != builder:
                    raise NewUnitError(
                        "建筑没写进去（第 %s 个位置还是 %s）"
                        % (brel, struct.unpack_from("<h", img, brel)[0]))
                moved["builder_from"] = was_builder
                moved["builder"] = builder
                rebuilt = {"from": was_builder, "to": builder}
    total = civ["unit_pointers_total"]
    ptrs = civ.get("_ptrs")
    if ptrs is None:
        ptrs = [1 if i in have else 0 for i in range(total)]
    # An id past the shipped array is the NORMAL case now (NEW_ID_START), so the
    # array grows instead of refusing.  The writer emits the new slots without
    # advancing its raw cursor; without that, each added slot shifted every later
    # op() by 4 bytes (measured: 3,009,559 extra bytes, parse dies in read_unit).
    if new_id >= len(ptrs):
        ptrs.extend([0] * (new_id + 1 - len(ptrs)))
    # The flag is what makes the record reachable: without it the record is
    # written but the reader's slot walk does not expect it, and the stream
    # desyncs (measured: `struct.error: bad char in struct format` inside
    # `read_civ`, not a clean refusal).  A record nobody can address is worse
    # than no record, so this line is the whole reason the append is safe.
    ptrs[new_id] = 1
    civ["_ptrs"] = ptrs
    rec = {"type": image[0], "id": new_id, "name": "NEWUNIT%d" % new_id,
           "_img": img}
    # Insert by id so the record run stays sorted: the flag array is indexed by
    # id, and the reader walks slots in order.
    pos = len(civ["units"])
    for k, u in enumerate(civ["units"]):
        if u["id"] > new_id:
            pos = k
            break
    civ["units"].insert(pos, rec)
    return stats, {"id": new_id, "civ": civ_index, "donor": donor_id,
                   "bytes": len(img), "slot": pos,
                   "buttons": ([moved] if moved else []),
                   "builder_rebuilt": rebuilt}


def free_ids(stats, civ_index):
    """Ids this civ has no record for and that are inside its id range."""
    civ = stats["civs"][civ_index]
    have = {u["id"] for u in civ["units"]}
    return [i for i in range(civ["unit_pointers_total"]) if i not in have]


def referenced_ids(stats):
    """Ids other tables point at: effect targets, effect sources, train slots.

    Not the same question as "no unit record uses it".  Measured: ids 273, 379,
    384 and 770 have no unit record and ARE named by shipped effect commands, so
    a clone at 273 would silently become the target of whatever that effect was
    aimed at.  A new unit must avoid all of these.
    """
    out = set()
    # An effect command is a 5-tuple (type, a, b, c, amount), not a dict -- see
    # parser.read_effect_command.  Taking only the first three as ids keeps this
    # from reading the float amount as a unit id.
    for eff in stats.get("effects") or ():
        for cmd in eff.get("commands") or ():
            if isinstance(cmd, dict):
                vals = [cmd.get(k) for k in ("a", "b", "c")]
            else:
                vals = list(cmd)[1:4]
            for v in vals:
                if isinstance(v, int):
                    out.add(v)
    for civ in stats["civs"]:
        for u in civ["units"]:
            for tl in u.get("train_locations") or ():
                v = tl.get("unit_id")
                if isinstance(v, int):
                    out.add(v)
    return out


def globally_free_ids(stats, max_id=NEW_ID_MAX, avoid=(), start=NEW_ID_START):
    """Ids NO civilization uses and nothing points at, from ``start`` upward.

    Free-in-one-civ is not free.  Measured: British alone has 586 holes and the
    lowest is 43 -- but 43 is a real shipped unit in Gaia and most other civs, so
    putting a villager clone there would make one id mean two different things
    depending on who is looking.  A new unit needs an id nobody claims, and
    ``start`` defaults to ``NEW_ID_START`` so the default answer is not a hole in
    the shipped numbering that the next patch will fill.
    """
    used = set(avoid)
    for civ in stats["civs"]:
        used.update(u["id"] for u in civ["units"])
    return [i for i in range(max(1, start), max_id + 1) if i not in used]


def pick_free_id(stats, max_id=NEW_ID_MAX, avoid=(), start=NEW_ID_START):
    """The lowest id past the shipped range that nothing uses or points at.

    ``start`` defaults to ``NEW_ID_START`` rather than the lowest hole: a hole in
    the shipped numbering is a hole *this* patch, and the marker of a good id is
    that a future patch will not fill it.
    """
    ids = globally_free_ids(stats, max_id=max_id, avoid=avoid, start=start)
    if not ids:
        raise NewUnitError("这个版本里没有空着的单位编号了")
    return ids[0]


def reject_taken_id(stats, new_id, civ_zh=None):
    """Refuse an id any civilization already uses.

    An id that is in use cannot hold a second record: the number of records is
    read from the flag array, so inserting a duplicate id leaves the flags and
    the record count disagreeing, and the whole tail desynchronises.  Measured:
    the same clone at the shipped id 2,749 fails to re-parse, while 2,750 (one
    past the array) is fine.  This is checked instead of assumed because the
    failure shows up as a parse error twenty thousand records later.

    ``civ_zh`` names the civilization in the player's language; the .dat layer
    only knows the internal stem ("Gaia", "BRITONS"), and a refusal that says
    "Gaia" to a Chinese player is the same leak this project keeps fixing.
    """
    for civ in stats["civs"]:
        for u in civ["units"]:
            if u["id"] == new_id:
                who = civ_zh or "某个文明"
                raise NewUnitError(
                    "第 %d 号已经被用了（%s），换一个编号再加，否则同一号会有两条记录"
                    % (new_id, who))
    return new_id

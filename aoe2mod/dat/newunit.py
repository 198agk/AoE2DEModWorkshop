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
# A command card is a numbered grid.  Measured over every civ: the numbers
# shipped data actually uses are 0..15 plus 24, and 255 appears 1,890 times as
# the button of a placeholder entry (``unit_id == -1``) -- a sentinel for "no
# button", not a slot.  So the usable range is 0..24 and 255 must never be
# counted as taken or offered as free.
BUTTON_SLOTS = 25
BUTTON_SENTINEL = 255
# Inside one TrainLocation: i16 train_time, i16 unit_id, then the u8 button id.
TRAIN_BUTTON_OFF = 4


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


def clone_image(image, new_id, name_string_id=None, hp=None, creation_string_id=None):
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
    if len(img) < 24:
        raise NewUnitError("这份记录太短了（%d 字节），不像是完整的单位记录" % len(img))
    struct.pack_into("<h", img, 1, new_id)
    if name_string_id is not None:
        struct.pack_into("<i", img, 3, name_string_id)
    if creation_string_id is not None:
        struct.pack_into("<i", img, 7, creation_string_id)
    if hp is not None:
        struct.pack_into("<h", img, 22, hp)
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
             button=None, civs=None):
    """Append one clone to ``civ_index``; returns ``(stats, record_dict)``.

    ``stats`` is mutated in place and must be a deep copy the caller owns --
    ``serialize_dat`` reads ``_ptrs`` off every civ, so this also builds that for
    the civs that needed it.

    ``civs`` (the located list) is only needed when ``button`` is given, because
    the train locations are read from there; passing ``stats`` instead makes
    every donor look like it trains nothing.
    """
    civ = stats["civs"][civ_index]
    have = {u["id"] for u in civ["units"]}
    if new_id in have:
        raise NewUnitError("这个文明已经有编号 %s 的单位了，换一个编号"
                           % (new_id,))
    if new_id >= HEADER_SLOTS:
        # Not fatal, but say it: nothing indexes a header by this id, so any
        # per-unit header data (tasks, etc.) simply has none.  A clone carries
        # the donor's own sub-records, so this only matters to editor tooling.
        pass
    image = donor_image(raw, gv, civs_start, civ_index, donor_id)
    img = clone_image(image, new_id, name_string_id=name_string_id, hp=hp,
                      creation_string_id=creation_string_id)
    moved = None
    if button is not None:
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
        if all(s["builder"] in (-1, None) for s in slots):
            raise NewUnitError(
                "「%s」的建造位置没有指向任何建筑（记录里的建筑编号是 -1），"
                "挪按钮也放不到任何菜单上" % (donor_id,))
        # Move EVERY copied entry onto the chosen number, keeping the list
        # otherwise intact.  Moving only the first one would leave the rest on
        # the donor's buttons, which is the thing the player asked to stop.
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
    total = civ["unit_pointers_total"]
    if new_id >= total:
        raise NewUnitError(
            "编号 %s 超出了这个文明的单位编号范围（只有 0..%d），换一个小一点的"
            % (new_id, total - 1))
    ptrs = civ.get("_ptrs")
    if ptrs is None:
        ptrs = [1 if i in have else 0 for i in range(total)]
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
                   "buttons": ([moved] if moved else [])}


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


def globally_free_ids(stats, max_id=HEADER_SLOTS - 1, avoid=()):
    """Ids NO civilization uses and nothing points at.

    Free-in-one-civ is not free.  Measured: British alone has 586 holes and the
    lowest is 43 -- but 43 is a real shipped unit in Gaia and most other civs, so
    putting a villager clone there would make one id mean two different things
    depending on who is looking.  A new unit needs an id nobody claims.
    """
    used = set(avoid)
    for civ in stats["civs"]:
        used.update(u["id"] for u in civ["units"])
    return [i for i in range(1, max_id + 1) if i not in used]


def pick_free_id(stats, max_id=HEADER_SLOTS - 1, avoid=()):
    """The lowest id that NO civilization uses, nothing points at, and that has
    a header slot.

    ``max_id`` defaults to the last header index so whatever indexes headers by
    unit id (the editor, scenario triggers) can address the clone at all.
    """
    ids = globally_free_ids(stats, max_id=max_id, avoid=avoid)
    if not ids:
        raise NewUnitError("这个版本里没有空着的单位编号了")
    return ids[0]

"""Read one building's command card, and move a unit to another box on it.

This is the data half of the graphic editor the player asked for (2026-10-26:
"左下角的那个地方，工具应该做个一模一样的窗口，我可以选择这个窗口，每个按钮位置，
拖动单位/科技的按钮").  In engine terms dragging a box is one byte: the
``button_id`` inside that unit's ``train_locations`` entry.

Two things about the shape of the data surprise everyone who reads it first:

* ``train_locations`` hangs on the UNIT record, and its ``unit_id`` is the
  PRODUCER.  A card is therefore "every unit whose entry names this building",
  not a list stored on the building.  Measured: British's town centre (109) has
  42 such units, the barracks (12) has 49, the castle (82) has 171.
* A box holding nothing is simply absent.  The engine draws 25 boxes and most
  cards fill a handful, so "free" is a set difference, not a flag.

The offsets come from :mod:`aoe2mod.dat.newunit`, which is where they were
measured.  Re-deriving them here would be a second hand-counted constant, and
that mistake produced a one-byte-short clone on 2026-10-20 that only showed up
inside ``read_task``.
"""
import struct

from . import newunit as NU


class CardError(Exception):
    """A card edit that cannot be made without inventing bytes."""


def card(civs, civ_index, builder_id):
    """Every box on one building's card, in box order.

    ``civs`` is the located civ list (``Toolkit._civs``), not the parsed stats
    model: the model drops ``train_locations`` entirely.

    A row is ``{unit, button, train_time, icon_id, name, internal}``.  ``button``
    can be ``None`` when a record's entry has no box byte at all, which is how
    the shipped data marks "belongs to this building but occupies no box"
    (measured: 683 British units whose only entries say builder ``-1``).
    """
    out = []
    for u in civs[civ_index]["units"]:
        for tl in u.get("train_locations") or ():
            if tl.get("unit_id") != builder_id:
                continue
            out.append({"unit": u["id"],
                        "button": tl.get("button_id"),
                        "train_time": tl.get("train_time"),
                        "icon_id": u.get("icon_id"),
                        "name": u.get("name"),
                        "internal": u.get("name")})
    out.sort(key=lambda r: (r["button"] if r["button"] is not None else 999,
                            r["unit"]))
    return out


def boxes(civs, civ_index, builder_id, limit=NU.BUTTON_SLOTS):
    """The card as ``limit`` boxes, ``None`` where a box is empty.

    The page draws boxes, not rows: an editor that only lists the occupied ones
    cannot show a player where an empty target is.
    """
    taken = {}
    for row in card(civs, civ_index, builder_id):
        b = row["button"]
        if b is None or not (0 <= b < limit):
            continue
        taken.setdefault(b, []).append(row)
    return [taken.get(i) for i in range(limit)]


def button_of(civs, civ_index, unit_id, builder_id):
    """The box ``unit_id`` occupies on ``builder_id``'s card, or ``None``.

    The lookup is by ``(unit, builder)`` because a unit can appear on several
    buildings: the same villager is on the town centre and, through the build
    menu, on every building it can raise.
    """
    for row in card(civs, civ_index, builder_id):
        if row["unit"] == unit_id:
            return row["button"]
    return None


def _entry(raw, gv, civs_start, civ_index, unit_id, builder_id, civs):
    """Locate the byte that holds ``unit_id``'s box on ``builder_id``."""
    if civs is None:
        raise CardError("need the located civ list (Toolkit._civs)")
    spans = NU.unit_spans(raw, gv, civs_start, civ_index)
    if unit_id not in spans:
        raise CardError("第 %s 号单位在这个文明里没有记录" % unit_id)
    start = spans[unit_id][0]
    rec = None
    for u in civs[civ_index]["units"]:
        if u["id"] == unit_id:
            rec = u
            break
    if rec is None:
        raise CardError("第 %s 号单位在这个文明里没有记录" % unit_id)
    for tl in rec.get("train_locations") or ():
        if tl.get("unit_id") != builder_id:
            continue
        if tl.get("_off_train_time") is None:
            raise CardError("第 %s 号单位的建造项没有记录偏移" % unit_id)
        # `_off_train_time` is ABSOLUTE (locate.py stores the cursor position);
        # `TRAIN_BUTTON_OFF` is relative to that.  Adding the record start to a
        # relative value writes into the Sound stage: the first run of the probe
        # that became this module printed `before: 255` and the re-parse still
        # said box 1 -- a silent no-op that looked like success.
        return start + (tl["_off_train_time"] - start + NU.TRAIN_BUTTON_OFF)
    raise CardError("第 %s 号单位不在这座建筑（%s）的训练表里，所以它没有格子可挪"
                    % (unit_id, builder_id))


def set_button(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
               civs=None):
    """Write ``button`` into the entry that puts ``unit_id`` on ``builder_id``.

    Returns ``(before, after, offset)``.  Refuses when the unit has no entry for
    that building: inventing one changes the record's length, which is a
    different edit, and doing it here would make a dropped box look like a move.
    """
    if not (0 <= int(button) < NU.BUTTON_SLOTS):
        raise CardError("格子号 %r 超出 0..%d" % (button, NU.BUTTON_SLOTS - 1))
    off = _entry(raw, gv, civs_start, civ_index, unit_id, builder_id, civs)
    before = raw[off]
    raw[off:off + 1] = struct.pack("<B", int(button))
    return before, int(button), off


def move(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
         civs=None):
    """Put ``unit_id`` in ``button``, swapping with whoever is already there.

    Returns ``{"moved": [...], "swapped": [...]}`` where each item is
    ``(unit, from, to)``.  Swapping rather than overwriting is the whole point:
    two units on one box is a state the shipped data never contains, and the
    engine resolves it by drawing one of them, so an editor that lets a drop
    hide a unit is an editor that loses edits silently.

    Refuses when the target box holds more than one unit: it is not reachable
    from the shipped data, and "which one do I swap with" has no answer.
    """
    board = card(civs, civ_index, builder_id)
    here = [r for r in board if r["unit"] == unit_id]
    if not here:
        raise CardError("第 %s 号单位不在这座建筑的卡上，拖不动" % unit_id)
    src = here[0]["button"]
    if src == button:
        return {"moved": [], "swapped": []}
    there = [r for r in board if r["button"] == button]
    if len(there) > 1:
        raise CardError("第 %d 格上挤着 %d 个单位，先挪走再拖"
                        % (button, len(there)))
    moved, swapped = [], []
    if there:
        other = there[0]["unit"]
        set_button(raw, gv, civs_start, civ_index, other, builder_id, src,
                   civs=civs)
        swapped.append((other, button, src))
    set_button(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
               civs=civs)
    if src is not None:
        moved.append((unit_id, src, button))
    else:
        moved.append((unit_id, None, button))
    return {"moved": moved, "swapped": swapped}

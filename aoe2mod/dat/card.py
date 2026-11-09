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


#: The button ids the engine DRAWS, inclusive.  Measured 2026-11-07 over all 62
#: civilizations, counting only entries that civilization's own tech tree says
#: it can build:
#:
#:   * the buildable boxes are ``1..15`` and nothing else.  Box 15 is real
#:     (Dravidians' Dock, 楼船, 40 s), which is why a ``0..14`` grid was wrong in
#:     BOTH directions -- it invented an empty first box and pushed the real last
#:     one outside the grid;
#:   * box 0 holds 27,838 stored entries -- the Town Centre's villager gathering
#:     buttons, the Gate's three forms -- and ZERO of them are buildable in any
#:     civilization: those unit ids appear in no tech tree at all, so the engine
#:     never draws that box;
#:   * ``16..24`` hold 372 more, all campaign heroes on the Dock, also zero
#:     buildable.
#:
#: So 「第 N 格」 and ``button_id`` are the same number and it starts at 1.
#:
#: PAGES, measured 2026-11-08 by the player and confirmed against other mods:
#: the engine DRAWS 15 boxes at a time but ACCEPTS ids up to 30 and turns the
#: overflow into its own red arrow -- box 15 grows a "next page" arrow, and boxes
#: 16..30 are the second page behind it.  Writing 31 or more produces a byte the
#: engine reads and never shows.  The player put it as:
#:
#:   面板是只有1-15，但是游戏支持能写到30，写15以上就会默认出现这个红色
#:   箭头在第15或第30格子的，但是写31就不支持了 … 游戏默认是支持2页伪翻页的
#:
#: Other shipped mods already write past 15, which is why this is a measurement
#: and not a guess: `10 倍资源文明联盟3倍科技` reaches button 34, `15373_Multiple
#: Buffs Mod` reaches 37, `WAIFor Arcade` uses 100, and `Red Alert 2 MOD` parks
#: 1,386 entries on button 20.  Those authors were looking at the arrow.
#:
#: So there are three different numbers here and they must not be merged:
#:
#:   * :data:`PAGE_BOXES` (15) -- how many boxes one screen of the panel shows;
#:   * :data:`PAGE_COUNT` (2) -- how many screens the engine will page through;
#:   * :data:`ENGINE_LAST` (30) -- the largest ``button_id`` the engine honours.
#:
#: :data:`newunit.BUTTON_SLOTS` (25) is a fourth, unrelated thing: how much room
#: the record itself reserves.
ENGINE_FIRST = 1
PAGE_BOXES = 15
PAGE_COUNT = 2
ENGINE_LAST = PAGE_BOXES * PAGE_COUNT


def page_of(button):
    """Which screen a box is on, counting from 1.  ``None`` when out of range."""
    b = int(button)
    if not (ENGINE_FIRST <= b <= ENGINE_LAST):
        return None
    return (b - ENGINE_FIRST) // PAGE_BOXES + 1


def page_span(page):
    """``(first, last)`` box numbers on one screen, counting from 1."""
    p = int(page)
    if not (1 <= p <= PAGE_COUNT):
        raise CardError("面板只有 %d 页，没有第 %d 页" % (PAGE_COUNT, p))
    first = ENGINE_FIRST + (p - 1) * PAGE_BOXES
    return first, first + PAGE_BOXES - 1


def _check_button(button):
    """Raise unless ``button`` is a box the engine will actually draw."""
    b = int(button)
    if not (ENGINE_FIRST <= b <= ENGINE_LAST):
        raise CardError(
            "格子号 %r 不能写：命令面板每页第 %d..%d 格，共 %d 页，"
            "所以最大能写到第 %d 格；没有第 0 格（那是村民采集、城门形态用的，"
            "引擎不画），也没有第 %d 格以后（写进去引擎读得到，但永远不画）"
            % (button, ENGINE_FIRST, PAGE_BOXES, PAGE_COUNT, ENGINE_LAST,
               ENGINE_LAST))
    return b


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
    button = _check_button(button)
    off = _entry(raw, gv, civs_start, civ_index, unit_id, builder_id, civs)
    before = raw[off]
    raw[off:off + 1] = struct.pack("<B", int(button))
    return before, int(button), off


def plan_move(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
              civs=None):
    """What `move` would write: ``(writes, got)`` with equal-width writes.

    Read-only, and that is the point.  `move` mutates a bytearray, which an HTTP
    route would have to obtain by copying the file -- 93 MB per drag -- and it
    would then have to work out which bytes changed by diffing all 93 million of
    them.  `_entry` already knows the offset, so the plan is one ``{off, before,
    after}`` per moved unit and the caller applies them through the session
    buffer, which is what makes a drag undoable and visible without a save.

    Refuses in exactly the cases `move` refuses: a unit not on this card and a
    box past the grid.

    A CROWDED target box is NOT refused any more.  The engine stores one
    `button_id` per entry and draws every entry that names the same box, so two
    or three entries on one box is a state the shipped data already contains
    (box 2 of the Barracks holds 长矛兵/长枪兵/长戟兵) and the engine resolves it
    by drawing the last one it reaches.  Reported 2026-11-09: 「怎么就挪不了了
    …然后格子放的东西是可以重叠的，这个就是游戏引擎的问题了，先后顺序的话哪个
    最后弹出就会覆盖上」.  So a drop onto a crowded box just moves the unit
    there; only a box holding exactly ONE other unit still swaps, because that
    is the only case where "which one do I trade with" has an answer.
    """
    button = _check_button(button)
    board = card(civs, civ_index, builder_id)
    here = [r for r in board if r["unit"] == unit_id]
    if not here:
        raise CardError("第 %s 号单位不在这座建筑的卡上，拖不动" % unit_id)
    from_box = here[0]["button"]
    if from_box == button:
        return [], {"moved": [], "swapped": []}
    there = [r for r in board if r["button"] == button]
    writes, moved, swapped = [], [], []
    if len(there) == 1:
        other = there[0]["unit"]
        off = _entry(raw, gv, civs_start, civ_index, other, builder_id, civs)
        writes.append({"unit": other, "off": off, "before": raw[off],
                       "after": int(from_box)})
        swapped.append((other, button, from_box))
    off = _entry(raw, gv, civs_start, civ_index, unit_id, builder_id, civs)
    writes.append({"unit": unit_id, "off": off, "before": raw[off],
                   "after": int(button)})
    moved.append((unit_id, from_box, button))
    return writes, {"moved": moved, "swapped": swapped}


def move(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
         civs=None):
    """Put ``unit_id`` in ``button``, swapping with whoever is already there.

    Returns ``{"moved": [...], "swapped": [...]}`` where each item is
    ``(unit, from, to)``.  Swapping rather than overwriting is the whole point:
    two units on one box is a state the shipped data never contains, and the
    engine resolves it by drawing one of them, so an editor that lets a drop
    hide a unit is an editor that loses edits silently.

    A target box holding MORE THAN ONE unit gets the moved unit appended, not a
    refusal and not a swap: the engine draws every entry that names the box and
    the last one wins, which is exactly the overlay the player described
    (2026-11-09).  A box holding exactly one unit still swaps -- that is the
    only case where "which one do I trade with" has an answer.
    """
    board = card(civs, civ_index, builder_id)
    here = [r for r in board if r["unit"] == unit_id]
    if not here:
        raise CardError("第 %s 号单位不在这座建筑的卡上，拖不动" % unit_id)
    src = here[0]["button"]
    if src == button:
        return {"moved": [], "swapped": []}
    there = [r for r in board if r["button"] == button]
    moved, swapped = [], []
    if len(there) == 1:
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

# ---------------------------------------------------------------------------
# putting a unit ON a card, taking it OFF, and changing how long it trains
# ---------------------------------------------------------------------------
# The three edits a card editor needs beyond dragging, and the reason they were
# missing is the same for all three: `train_locations` is a LIST inside the unit
# record, and its length is a separate i16 in front of it.  Changing which
# building shows a button (what `move`/`set_button` do) is one byte because the
# entry is already there.  Adding an entry is a SPLICE -- nine bytes into the
# middle of the record, plus a count -- which is why it lives here next to the
# measured offsets rather than in the page.
#
# The offsets come from the same walk `locate.walk_unit` does, read out of the
# located record instead of re-derived: `_creatable_start` is where the three
# ResourceCosts begin, the count is the i16 right after them (18 bytes), and
# `_creatable_head_end` is where the entry list ends.  Measured on the shipped
# file: every one of British's 2,164 located units has ``count == len(
# train_locations)``, so this is the same number the parser read.
COSTS_BYTES = 18                    # 3 x (i16 Type, i16 Amount, i16 Flag)
ENTRY_COUNT_OFF = COSTS_BYTES       # relative to `_creatable_start`
HOTKEY_ID = 16000                   # what every shipped entry carries, measured


def _creatable(raw, civs, civ_index, unit_id):
    """``(start, count_off, head_end, rec)`` for one unit, or a refusal.

    A unit whose record has no Creatable block cannot carry a train location at
    all: the parser decides which blocks exist from the record's TYPE, so there
    is no count field to bump.  Saying that out loud beats writing nine bytes
    into whichever block happens to sit at the same distance.
    """
    if civs is None:
        raise CardError("要传定位过的文明列表（Toolkit._civs），"
                        "解析出来的 stats 里没有训练位置")
    rec = None
    for u in civs[civ_index]["units"]:
        if u["id"] == int(unit_id):
            rec = u
            break
    if rec is None:
        raise CardError("这个文明里没有编号 %s 的单位" % (unit_id,))
    start = rec.get("_creatable_start")
    head_end = rec.get("_creatable_head_end")
    if start is None or head_end is None:
        raise CardError(
            "第 %s 号单位（类型 %s）的记录里没有建造表这一块，"
            "所以放不到任何建筑的卡上"
            % (unit_id, rec.get("type")))
    return start, start + ENTRY_COUNT_OFF, head_end, rec


def entry_at(raw, gv, civs_start, civ_index, unit_id, builder_id, civs=None):
    """The one train-location entry that puts ``unit_id`` on ``builder_id``.

    Returns ``{start, count_off, head_end, off_train_time, index, train_time,
    builder, button}``.  Refuses when there is no such entry -- "make me one" is
    `plan_put_on_card`, a different edit that changes the record's length.
    """
    start, count_off, head_end, rec = _creatable(raw, civs, civ_index, unit_id)
    n = struct.unpack_from("<h", raw, count_off)[0]
    tls = rec.get("train_locations") or ()
    if n != len(tls):
        raise CardError(
            "第 %s 号单位的建造表写着 %d 项，走出来的记录是 %d 项，"
            "两边对不上，这份数据不能按偏移改" % (unit_id, n, len(tls)))
    for i, tl in enumerate(tls):
        if tl.get("unit_id") != builder_id:
            continue
        off = tl.get("_off_train_time")
        if off is None:
            raise CardError("第 %s 号单位的建造项没有记录偏移" % (unit_id,))
        return {"start": start, "count_off": count_off, "head_end": head_end,
                "off_train_time": off, "index": i,
                "train_time": tl.get("train_time"),
                "builder": tl.get("unit_id"),
                "button": tl.get("button_id")}
    raise CardError("第 %s 号单位不在这座建筑（%s）的建造表里"
                    % (unit_id, builder_id))


def plan_put_on_card(raw, gv, civs_start, civ_index, unit_id, builder_id,
                     button, train_time=0, civs=None):
    """Append a train location, so ``builder_id`` shows ``unit_id`` on ``button``.

    Two steps, in this order: the count goes up by one, then nine bytes of entry
    are spliced in at the END of the existing list.  The count write sits BEFORE
    the splice point, so writing it first keeps its own offset valid; doing it
    the other way round would need the count's new home before the entry exists.

    Returns ``(steps, info)`` where ``steps`` is the ``(at, cut, add)`` shape
    `records.apply_steps` takes.
    """
    start, count_off, head_end, rec = _creatable(raw, civs, civ_index, unit_id)
    n = struct.unpack_from("<h", raw, count_off)[0]
    if n < 0:
        raise CardError("第 %s 号单位的建造表项数是 %d，读不通" % (unit_id, n))
    for tl in rec.get("train_locations") or ():
        if tl.get("unit_id") == builder_id:
            raise CardError(
                "第 %s 号单位已经在这座建筑的第 %s 格上了；换格子用它自己的按钮"
                % (unit_id, tl.get("button_id")))
    button = _check_button(button)
    tt = int(train_time or 0)
    if not (-32768 <= tt <= 32767):
        raise CardError("训练时间 %r 秒写不进 i16" % (train_time,))
    if NU.TRAIN_ENTRY_BYTES == 9:
        entry = struct.pack("<hhBi", tt, int(builder_id), int(button), HOTKEY_ID)
    else:
        entry = struct.pack("<hhB", tt, int(builder_id), int(button))
    if len(entry) != NU.TRAIN_ENTRY_BYTES:
        raise CardError("建造项的宽度是 %d 字节，这里算出来 %d 字节"
                        % (NU.TRAIN_ENTRY_BYTES, len(entry)))
    steps = [(count_off, 2, struct.pack("<h", n + 1)),
             (head_end, 0, entry)]
    info = {"unit": int(unit_id), "building": int(builder_id),
            "button": int(button), "train_time": tt, "index": n,
            "at": head_end, "count": n + 1}
    return steps, info


def put_on_card(raw, gv, civs_start, civ_index, unit_id, builder_id, button,
                train_time=0, civs=None, inplace=False):
    """`plan_put_on_card` applied.  Returns ``(buffer, writes, info)``."""
    from . import records as REC
    steps, info = plan_put_on_card(raw, gv, civs_start, civ_index, unit_id,
                                   builder_id, button, train_time=train_time,
                                   civs=civs)
    work, writes = REC.apply_steps(raw, steps, inplace=inplace)
    return work, writes, info


def plan_take_off_card(raw, gv, civs_start, civ_index, unit_id, builder_id,
                       civs=None):
    """Cut the train location that puts ``unit_id`` on ``builder_id``'s card.

    Refuses on the LAST entry.  A record with zero entries parses fine (the
    shipped data has 904 of them per civ), but a unit that trains nowhere is not
    what "take it off the card" means -- so the refusal names the door that does
    mean it instead of quietly emptying the list.
    """
    got = entry_at(raw, gv, civs_start, civ_index, unit_id, builder_id, civs)
    n = struct.unpack_from("<h", raw, got["count_off"])[0]
    if n <= 1:
        raise CardError(
            "第 %s 号单位只有这一条建造项，删掉它这个单位就谁都不训练了；"
            "要删记录请用「删除这一条」" % (unit_id,))
    at = got["off_train_time"]
    steps = [(got["count_off"], 2, struct.pack("<h", n - 1)),
             (at, NU.TRAIN_ENTRY_BYTES, b"")]
    info = {"unit": int(unit_id), "building": int(builder_id),
            "button": got.get("button"), "at": at, "count": n - 1}
    return steps, info


def take_off_card(raw, gv, civs_start, civ_index, unit_id, builder_id,
                  civs=None, inplace=False):
    """`plan_take_off_card` applied.  Returns ``(buffer, writes, info)``."""
    from . import records as REC
    steps, info = plan_take_off_card(raw, gv, civs_start, civ_index, unit_id,
                                     builder_id, civs=civs)
    work, writes = REC.apply_steps(raw, steps, inplace=inplace)
    return work, writes, info


def set_train_time(raw, gv, civs_start, civ_index, unit_id, builder_id,
                   seconds, civs=None):
    """How long this unit takes to train, in seconds.  EQUAL WIDTH, one i16.

    Returns ``(before, after, offset)``.  `train_time` is the first i16 of the
    entry and it is the number the game counts down, not a multiplier: measured
    on the shipped file, villager 83 says 25 and the Barracks' militia 74 says
    21, which is what the game shows on the button.
    """
    secs = int(seconds)
    if not (-32768 <= secs <= 32767):
        raise CardError("训练时间 %r 秒写不进 i16" % (seconds,))
    got = entry_at(raw, gv, civs_start, civ_index, unit_id, builder_id, civs)
    off = got["off_train_time"]
    before = struct.unpack_from("<h", raw, off)[0]
    raw[off:off + 2] = struct.pack("<h", secs)
    return before, secs, off

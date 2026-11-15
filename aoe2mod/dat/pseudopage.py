# -*- coding: utf-8 -*-
"""pseudopage.py -- one box on a building card that turns into a page turner.

A PAGE-TURNING BOX, AND WHAT IT ACTUALLY IS
------------------------------------------
A command panel box is a ``button_id`` 1..30 (15 per screen, two screens).  The
engine draws, in that box, every technology whose ``ResearchLocations`` names
that ``(building, button)`` pair.  Normally there is exactly one, so the box
shows one research button.

What makes several technologies behave like PAGES is not the technology data at
all -- it is ``resources/_common/dat/linkedTechs.json``.  A group of type
``"Cycle"`` tells the engine: these N technologies are one button; show
``StartingTech`` first, and when it is pressed show the next one in ``Techs``,
and wrap around.  Every member shares the same ``(location_id, button_id)``,
which is what identifies the group; measured on a real mod, the five pages
4666..4670 of building 5066 box 15 all sit on ``(5066, 15)`` with hotkey
19352, differ only in which units they switch on, and are listed as one Cycle
group with ``StartingTech: 4666``.

So: ONE PAGE IS ONE TECHNOLOGY.  N pages = N technologies on one box + one
Cycle record naming them.  The technologies are cheap (about 81 bytes each);
the record is four lines of JSON.

WHAT A PAGE SAYS
----------------
Each page is free (all three resource costs zero) and takes 0 seconds, so the
press resolves on the tick it happens and no research progress can be lost.
Its effect record then decides WHICH UNITS THAT PAGE SHOWS, through effect
command type 0 (``Attribute Modifier (Set)``) writing attribute **42** -- the
unit attribute this project's vocabulary calls 「训练地点」:

* ``d = -1.0``  takes the unit off every card (it cannot be trained at all);
* ``d = <building id>`` puts it back on that building, in the box the unit's
  own ``train_locations[].button_id`` already names.

A page therefore writes ``-1`` for the union of what every OTHER page shows,
then ``<building>`` for its own units.  The union matters: all pages of a box
are present at once and nothing disables them, so hiding only the previous
page would let a player who presses page 3 while page 1 is active train both
batches.  :func:`sync_off` computes that union for the whole group, and
:func:`plan_rewrite_pages` applies it to every page in one splice.

A page shows at most 14 units: the box itself is the pager, so the other 14
boxes of the screen are its content (:func:`content_boxes`).  Page 1 uses the
first screen's 14 boxes, page 2 and later use the second screen's 14 -- which
is not a limitation, because two pages are never active at the same time and
therefore may reuse the same box numbers.

WHAT IT COSTS THE PLAYER
------------------------
A page turn REWRITES WHERE ITS UNITS ARE TRAINABLE, and anything already in
flight that depended on the old answer goes with it:

* a unit part-way through production at that building loses its train location
  and the queue entry disappears with it.  The data has no 「接着做」 flag, so
  no amount of care on our side can keep the queue; the panel says so in the
  warning under the page list.
* a technology part-way through research at that building loses its research
  location and the research is dropped.

THE PRICE IS UNCHANGED BY THIS MODULE'S SHAPE.  It is the same attribute the
engine consults, changed under a running game.

WHAT THIS FILE DOES AND DOES NOT DO
-----------------------------------
Reading: :func:`fast_effects` / :func:`effect_spans` walk the effect block in
one pass, :func:`read_page` turns one technology into ``{on, off, building}``,
:func:`read_group` collects the pages of one box and :func:`read_cycles` maps
every box in the file.

Writing: :func:`plan_add_page` appends one page (effect + technology + pointer)
as two splices; :func:`sync_off` + :func:`plan_rewrite_pages` rewrite the whole
group's command lists in one splice; :func:`plan_drop_page` removes one
technology.  The linkedTechs.json side lives in `aoe2mod/game/linkedtechs.py`
(:func:`cycle_boxes` / :func:`sync_cycles` / :func:`emit_cycles`), because the
same file also carries MutuallyExclusive and Toggleable groups that have
nothing to do with pages.
"""

import struct

from . import locate as L
from . import parser as P
from . import records as REC
from .techfields import read_tech_fields
from .unitfields import Rec

__all__ = [
    "PAGE_ATTR", "CMD_BYTES", "PageError", "page_commands", "read_page",
    "read_group", "read_cycles", "default_hide", "plan_add_page", "add_page",
    "plan_rewrite_pages", "plan_drop_page", "sync_off",
    "CONTENT_SLOTS", "content_boxes",
    "_free_to_press",
    "effect_bytes", "fast_effects", "effect_spans",
]


#: The unit attribute a page writes: 「训练地点」.  Effect command type 0 sets an
#: attribute; ``-1`` is "not trainable anywhere", a building id is "trainable
#: here".  See `aoe2mod/game/fieldbook.py` for the label this project shows.
PAGE_ATTR = 42

#: Effect command type 0 = ``Attribute Modifier (Set)``
#: (``aoe2mod/schema/effect_command_types.json``).
CMD_ATTRIBUTE_SET = 0

#: Boxes the engine draws on ONE screen of the command panel, and how many
#: screens it draws.  Same numbers as aoe2mod/dat/card.py (ENGINE_FIRST /
#: ENGINE_LAST / PAGE_BOXES / PAGE_COUNT); repeated here so this module does
#: not import the card writer just to count to 15.
SCREEN_BOXES = 15
SCREEN_COUNT = 2

#: How many boxes a page can use: one screen, minus the pager's own box.
CONTENT_SLOTS = SCREEN_BOXES - 1


def page_of(box):
    """The 1-based screen number that box (1..30) is drawn on."""
    b = int(box)
    if b < 1 or b > SCREEN_BOXES * SCREEN_COUNT:
        raise PageError(
            "格子号 %d 不在 1..%d 之间，命令面板一共 %d 屏、每屏 %d 格"
            % (b, SCREEN_BOXES * SCREEN_COUNT, SCREEN_COUNT, SCREEN_BOXES))
    return (b - 1) // SCREEN_BOXES + 1


def screen_boxes(box):
    """Every box on the screen box is drawn on, in panel order."""
    page = page_of(box)
    first = (page - 1) * SCREEN_BOXES + 1
    return list(range(first, first + SCREEN_BOXES))


def content_boxes(box):
    """The boxes a page on the pager in box may fill: its screen minus itself.

    A page turn swaps what the OTHER boxes of the same screen show, so this is
    the set a page's units have to sit in.  Two pages are never on screen at
    the same time, which is why page 2 may reuse the very same box numbers
    page 1 uses -- measured on a five-page cycle, the pager sat at box 15 and
    every page put its units on 1..14 of its own screen.
    """
    return [b for b in screen_boxes(box) if b != int(box)]


def slot_index(box, slot):
    """Where slot sits in content_boxes (0-based), or None."""
    try:
        return content_boxes(box).index(int(slot))
    except (TypeError, ValueError):
        return None


def _span_text(boxes):
    if not boxes:
        return "没有"
    return "%d..%d 这 %d 格" % (boxes[0], boxes[-1], len(boxes))


def check_slot(box, slot):
    """Return slot as an int, or raise a sentence naming the usable boxes."""
    s = int(slot)
    if s in content_boxes(box):
        return s
    if s == int(box):
        raise PageError(
            "第 %d 格是翻页按钮自己站的那一格，放不了单位；这一页能用的是 %s"
            % (s, _span_text(content_boxes(box))))
    raise PageError(
        "第 %d 格不在这一屏。翻页按钮在第 %d 格，这一页能放单位的是 %s"
        % (s, int(box), _span_text(content_boxes(box))))


class PageError(Exception):
    """A page edit that cannot be done.  The sentence is for the player."""


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
def page_commands(on=(), off=(), building=0):
    """The command list of one page: turn ``off`` off, turn ``on`` on.

    Returns ``[(type, a, b, c, d), ...]`` ready for `effect_bytes`.  ``off`` is
    written first on purpose: within one effect record the commands run in
    order, so a unit that appears in both lists ends up ON, which is the
    forgiving direction if a caller hands over overlapping sets by mistake.
    """
    cmds = []
    for u in off:
        cmds.append((CMD_ATTRIBUTE_SET, int(u), -1, PAGE_ATTR, -1.0))
    for u in on:
        cmds.append((CMD_ATTRIBUTE_SET, int(u), -1, PAGE_ATTR, float(building)))
    return cmds


def effect_bytes(name, commands):
    """One effect record, exactly the bytes `locate.walk_effect` walks.

    ``u16 marker, u16 length, text`` then ``i16 count`` and ``count`` fixed
    15-byte commands.  The marker is ``parser.DEBUG_STRING_MARKER`` and the
    length is the EXACT byte count -- there is no NUL terminator in this format
    (`writer.debug_string` documents the same rule from the writing side), and
    using the marker as the length advances a reader by 2,656 bytes.
    """
    body = (name or "").encode("latin-1", "replace")
    if len(body) > 200:
        raise PageError("这个名字太长（%d 字节），页面名最多 200 字节" % len(body))
    out = struct.pack("<HH", P.DEBUG_STRING_MARKER, len(body)) + body
    out += struct.pack("<h", len(commands))
    for ty, a, b, c, d in commands:
        out += struct.pack("<Bhhhf", int(ty), int(a), int(b), int(c), float(d))
    return out


def read_page(effects, tech):
    """``{on, off, other}`` for one technology, or ``None`` when it is not a page.

    A page is a technology whose effect turns units ON in a box: at least one
    attribute-42 write with a positive value (a building id).  Anything else in
    the record is counted in ``other`` and left alone -- the community example
    that motivated this module carries one ``type 103`` command alongside its 28
    attribute writes, and a reader that demanded "attribute writes only"
    reported zero pages for a box the game draws five on.  A technology with no
    attribute-42 writes at all is a normal research and is deliberately not
    reported here: calling it a page would make the interface offer to add a
    page next to a button that does not cycle.

    OFF commands are optional, and that is the bug this docstring used to
    describe the opposite of.  The FIRST page of a box has nothing to turn off
    -- `default_hide` over an empty group returns nothing -- so the record the
    writer produces holds ON commands only, and a reader that insisted on both
    reported zero pages for the page it had just written (measured 2026-11-09:
    `add ok=True grew=116` then `pages 0`, and a player who adds a page and
    watches the badge stay empty adds it again).

    Accepting a page with no OFF commands needs one qualifier, or every unique
    technology that unlocks a unit becomes a pager: when there are no OFF
    commands, every cost slot that is actually paid must cost nothing
    (``amount <= 0``).  Measured on the mod this was written for, that rule
    keeps 「Cycle 1」/「Cycle 5」 in (0 and -6 gold) and keeps 「Gothic Anarchy」
    (450) and 「Huns UT」 (300) out.  A negative amount pays the player back,
    which the community example does; positive is an ordinary unlock.
    """
    eid = tech.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        return None
    cmds = effects[eid].get("commands") or ()
    if not cmds:
        # A BRAND NEW PAGE, before the player has put anything in it: the
        # interface creates the button first and fills it by clicking the grid,
        # so the record it writes at that moment has nothing to turn on and
        # nothing to turn off.  A reader that refused it would report zero pages
        # for the page the player had just made -- the button would be missing
        # from the strip that is supposed to be filling it.
        #
        # Accepted only when the press is free AND takes no time, because those
        # two fields are what the writer sets and they are what keeps an ordinary
        # empty effect record (this file has 344 of them) from being read as a
        # page: measured on the retail data, no technology that has a research
        # location in box 1..30 points at an empty effect record.
        if not _free_to_press(tech):
            return None
        if int(tech.get("research_time") or 0) != 0:
            return None
        return {"on": [], "off": [], "building": 0, "commands": 0,
                "other": 0, "first": True, "empty": True, "effect": eid}
    on, off, other = [], [], 0
    for c in cmds:
        if c.get("type") != CMD_ATTRIBUTE_SET or c.get("c") != PAGE_ATTR:
            other += 1
            continue
        a = c.get("a")
        if a is None or a < 0:
            continue
        d = c.get("d")
        if d is None:
            return None
        if d < 0:
            off.append(int(a))
        else:
            on.append(int(a))
    if not on:
        # An EMPTY page: nothing turned on yet, but the record already turns
        # something off and is free to press.  The interface creates a page
        # before the player has picked its units (create a page, then click
        # the grid), so a reader that only reported pages with an ON list
        # would report zero pages for the page it had just made -- the same
        # failure the docstring above records for OFF-less pages, one step
        # further in.  It stays safe because a record with no attribute-42
        # writes puts nothing in `on` and `off` and is refused below.
        if not off:
            return None
        if not _free_to_press(tech):
            return None
        return {"on": [], "off": sorted(set(off)),
                "building": _building_of(cmds), "commands": len(cmds),
                "other": other, "first": not off, "empty": True,
                "effect": eid}
    if not off and not _free_to_press(tech):
        return None
    return {"on": sorted(set(on)), "off": sorted(set(off)),
            "building": _building_of(cmds), "commands": len(cmds),
            "other": other, "first": not off, "effect": eid}


def _free_to_press(tech):
    """True when no cost slot charges a positive amount.

    ``costs`` entries are ``{type, amount, flag}``; ``flag == 1`` is "this slot
    is paid", ``0`` is "listed but not charged" and ``2`` is "seen" (see
    `locate.walk_tech`).  An absent or empty cost list is free.
    """
    for c in (tech.get("costs") or ()):
        if not isinstance(c, dict):
            continue
        if int(c.get("flag") or 0) != 1:
            continue
        if int(c.get("amount") or 0) > 0:
            return False
    return True


def _building_of(cmds):
    """The building id every ON command names, or 0 when they disagree."""
    ids = {int(c["d"]) for c in cmds if c.get("d") is not None and c["d"] > 0}
    return ids.pop() if len(ids) == 1 else 0


def read_group(effects, techs, building, button):
    """Every page on ONE box, in the order the technologies appear.

    ``button`` is the box number (1..30) and ``building`` the unit id of the
    building whose card it is.  A technology belongs to the box when one of its
    ``research_locations`` names that pair -- that is the same field the engine
    reads to decide which box to draw it in, so the box the interface lists and
    the box the game draws cannot disagree.
    """
    pages = []
    for ti, t in enumerate(techs):
        locs = t.get("research_locations") or ()
        here = None
        for loc in locs:
            if (loc.get("location_id") == building
                    and loc.get("button_id") == button):
                here = loc
                break
        if here is None:
            continue
        page = read_page(effects, t)
        if page is None:
            continue
        page.update({"tech": ti, "tech_name": t.get("name"),
                     "seconds": here.get("research_time"),
                     "button": button, "building": building,
                     "required_techs": list(t.get("required_techs") or ()),
                     "costs": [(c.get("type"), c.get("amount"))
                               for c in (t.get("costs") or ())]})
        pages.append(page)
    return pages


def read_cycles(effects, techs):
    """Every page group in the file, keyed by ``(building, button)``.

    Walked over the whole technology list once so the interface can say "this
    box is a pager" without the player having to tell it.  Measured on the
    5,874-technology mod this was written for: 0.35 s including the effect walk,
    which is why the caller caches it per generation instead of per request.
    """
    out = {}
    for ti, t in enumerate(techs):
        page = read_page(effects, t)
        if page is None:
            continue
        for loc in (t.get("research_locations") or ()):
            key = (loc.get("location_id"), loc.get("button_id"))
            # A box needs a REAL building and a real box number.  `-1, 0` is how
            # this file writes "this technology is not in any box", and an entry
            # for it made the interface offer to add a page to building -1.
            if not isinstance(key[0], int) or not isinstance(key[1], int):
                continue
            if key[0] <= 0 or key[1] <= 0:
                continue
            out.setdefault(key, []).append(ti)
    return out


def default_hide(pages):
    """What a new page should turn OFF: what every other page turns ON.

    Not "what the last page turned on".  All the pages of one box are on screen
    at the same time -- nothing disables them -- so a player who presses page 3
    while page 1 is active turns two batches on at once unless page 3 also hides
    page 1's batch.  The union makes the order of presses irrelevant, which is
    the only version of this that survives a player clicking quickly.
    """
    hide = set()
    for p in pages:
        hide.update(p.get("on") or ())
    return sorted(hide)


# ---------------------------------------------------------------------------
# the whole effect block, fast
# ---------------------------------------------------------------------------
#: Bytes of one effect command: ``u8 type`` + three ``i16`` + ``f32``.
CMD_BYTES = 11

#: The per-record header: ``u16 marker`` + ``u16 name length``.
HEAD_BYTES = 4


def fast_effects(raw, start, end=None):
    """Walk the Effects section with ``struct``.  Returns ``(effects, end)``.

    Same shape as `locate.locate_effects`, which is what every caller of this
    module already consumes, but measured at 0.010 s against its 7.83 s on the
    125 MB mod.  The cost is entirely in `Orec`: it bounds-checks every read and
    records the offset of every field, and the effect walk needs the six values
    of a command and where they sit -- which one ``unpack_from`` answers.

    ``end`` is optional and only used to refuse a wrong answer: when the caller
    already knows where the block ends (``tablefields.stage_offsets`` reports the
    stage boundary), a walk that does not land exactly there is a bug in this
    function, and returning the records anyway would hand out ids that point
    into the wrong bytes.  A mismatch raises `PageError` rather than guessing.

    Offsets are kept because the interface edits single commands: the player
    rewrites one attribute of one page and nothing else.
    """
    n = struct.unpack_from("<i", raw, start)[0]
    if n < 0:
        raise PageError("效果段说它有 %d 条记录，这个数是负的" % n)
    pos = start + 4
    cmd_fmt = struct.Struct("<Bhhhf")
    head_fmt = struct.Struct("<HH")
    out = []
    for ei in range(n):
        if pos + HEAD_BYTES > len(raw):
            raise PageError("效果段读到第 %d 条就没有字节了" % ei)
        marker, ln = head_fmt.unpack_from(raw, pos)
        if marker != P.DEBUG_STRING_MARKER:
            raise PageError("第 %d 条效果的字符串标记是 %#06x，不是 %#06x"
                            % (ei, marker, P.DEBUG_STRING_MARKER))
        pos += HEAD_BYTES
        name = bytes(raw[pos:pos + ln]).split(b"\x00", 1)[0].decode("latin-1")
        pos += ln
        if pos + 2 > len(raw):
            raise PageError("第 %d 条效果的命令数不在文件里" % ei)
        cn = struct.unpack_from("<h", raw, pos)[0]
        pos += 2
        cmds = []
        for _ci in range(max(0, cn)):
            ty, a, b, c, d = cmd_fmt.unpack_from(raw, pos)
            cmds.append({"type": ty, "a": a, "b": b, "c": c, "d": d,
                         "_off_type": pos, "_off_a": pos + 1,
                         "_off_b": pos + 3, "_off_c": pos + 5,
                         "_off_d": pos + 7})
            pos += CMD_BYTES
        out.append({"index": ei, "name": name, "commands": cmds})
    if end is not None and pos != end:
        raise PageError("效果段走到第 %d 字节，段尾却在第 %d 字节，"
                        "这个快扫法不能用来改这份文件" % (pos, end))
    return out, pos


def effect_spans(raw, start, end=None):
    """Where each effect record begins and ends, and where its count sits.

    ``fast_effects`` answers "what does each record say"; this answers "which
    bytes are that record", which is what a REWRITE needs: replacing one
    record's command list changes its length, and a length change means every
    later record moves.  Rewriting in place with a fixed width is impossible
    (11 bytes per command), so the whole span from the first changed record to
    the last one is rebuilt and spliced as one piece.

    Returns ``([{index, name, start, name_len, count_off, cmd_start, count,
    end}], pos)``.  ``count_off`` is the two-byte command count,
    ``cmd_start`` the first command (equal to ``end`` when the record has
    none) and ``end`` the first byte AFTER the record -- so records are
    back to back and ``spans[i]["end"] == spans[i + 1]["start"]``.
    """
    n = struct.unpack_from("<i", raw, start)[0]
    if n < 0:
        raise PageError("效果段说它有 %d 条记录，这个数是负的" % n)
    pos = start + 4
    head_fmt = struct.Struct("<HH")
    out = []
    for ei in range(n):
        rec_start = pos
        if pos + HEAD_BYTES > len(raw):
            raise PageError("第 %d 条效果读到这里就没有字节了" % ei)
        marker, ln = head_fmt.unpack_from(raw, pos)
        if marker != P.DEBUG_STRING_MARKER:
            raise PageError("第 %d 条效果的字符串标记是 %#06x，不是 %#06x"
                            % (ei, marker, P.DEBUG_STRING_MARKER))
        pos += HEAD_BYTES
        name = bytes(raw[pos:pos + ln]).split(b"\x00", 1)[0].decode("latin-1")
        pos += ln
        count_off = pos
        if pos + 2 > len(raw):
            raise PageError("第 %d 条效果的条数读到了文件结尾" % ei)
        cn = struct.unpack_from("<h", raw, pos)[0]
        pos += 2
        cmd_start = pos
        count = max(0, cn)
        pos += count * CMD_BYTES
        out.append({"index": ei, "name": name, "start": rec_start,
                    "name_len": ln, "count_off": count_off,
                    "cmd_start": cmd_start, "count": count, "end": pos})
    if end is not None and pos != end:
        raise PageError("效果段走到第 %d 字节，段尾却在第 %d 字节，"
                        "这个快扫法不能用来改这份文件" % (pos, end))
    return out, pos


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def _patch_image(image, where, values):
    """Rewrite the named fields of ONE record image, in place conceptually.

    ``where`` is ``{field name: (offset, kind)}`` as `read_tech_fields` reports
    it, ``values`` is ``{field name: new value}``.  A name that is not in the
    record is skipped rather than raising: field sets differ by format version
    (`Repeatable` only exists from the Conquerors, `ResearchLocations.*` only in
    the modern layout), and a page built for one version must still work on the
    other.  Widths come from the reader's own ``kind`` column, so this cannot
    disagree with the walk that produced the offsets.
    """
    out = bytearray(image)
    fmt = {"i16": "<h", "u16": "<H", "i32": "<i", "u32": "<I", "u8": "<B"}
    for name, value in values.items():
        spot = where.get(name)
        if spot is None:
            continue
        off, kind = spot
        packer = fmt.get(kind)
        if packer is None:
            continue
        struct.pack_into(packer, out, off, int(value))
    return bytes(out)


def plan_rewrite_pages(buf, effects_start, effects_end, changes):
    """Rewrite the COMMANDS of pages that already exist, as one splice.

    ``changes`` is `{effect index: {"on": [...], "off": [...], "building":
    id}}`.  Every other byte in the touched range is copied through unchanged,
    so the effect block keeps every record it had and only the command lists of
    the named ones change -- which is what "add this unit to page 2" needs, and
    is not expressible as a fixed-width patch because a command is 11 bytes and
    the list length moves.

    Returns ``(steps, info)`` in the shape `records.apply_steps` takes, with
    ``info["delta"]`` as the net byte change (what `App._card_splice` expects
    for ``expect``).

    THE NAME IS CARRIED AS RAW BYTES, not re-encoded: a page name written by
    another tool may not survive a latin-1 round trip, and a rewrite that
    silently re-spells it would be an edit nobody asked for.
    """
    if not changes:
        raise PageError("没有要改的页")
    spans, _pos = effect_spans(buf, effects_start, effects_end)
    by_index = {s["index"]: s for s in spans}
    for ei in changes:
        if int(ei) not in by_index:
            raise PageError("效果段里没有第 %s 条记录，改不了这一页" % (ei,))
    lo = min(by_index[int(ei)]["start"] for ei in changes)
    hi = max(by_index[int(ei)]["end"] for ei in changes)
    grown = bytearray()
    touched = []
    for span in spans:
        if span["start"] < lo or span["start"] >= hi:
            continue
        want = changes.get(span["index"])
        if want is None:
            grown += buf[span["start"]:span["end"]]
            continue
        on = sorted(set(int(u) for u in (want.get("on") or ())))
        off = sorted(set(int(u) for u in (want.get("off") or ())))
        bld = int(want.get("building") or 0)
        cmds = page_commands(on=on, off=off, building=bld)
        raw_name = bytes(buf[span["start"] + HEAD_BYTES:
                             span["start"] + HEAD_BYTES + span["name_len"]])
        head = struct.pack("<HH", P.DEBUG_STRING_MARKER, len(raw_name)) + raw_name
        body = b"".join(struct.pack("<Bhhhf", int(ty), int(a), int(b), int(c),
                                    float(d)) for ty, a, b, c, d in cmds)
        grown += head + struct.pack("<h", len(cmds)) + body
        touched.append(span["index"])
    before = hi - lo
    after = len(grown)
    steps = [(lo, before, bytes(grown))]
    info = {"from": lo, "to": hi, "before": before, "after": after,
            "delta": after - before, "effects": sorted(touched)}
    return steps, info


def plan_add_page(buf, gv, tail, effects_start, effects_end, effect_count,
                  donor_tech, name, on_units, hide_units=None, building=None,
                  seconds=0, button=None):
    """Plan one more page on the box ``donor_tech`` already lives on.

    ``(steps, info)`` in the shape `records.apply_steps` takes, with one
    difference from every other plan in this package: it is built in TWO passes,
    because the second append's address only exists after the first one lands.

    1. Append the effect record at ``effects_end`` and bump the ``i32`` count at
       ``effects_start``.  The effect block sits BEFORE the civilisation block,
       so this splice moves the unit headers, every civ and the whole technology
       section -- and nothing else in the file.
    2. Re-derive the technology section on the buffer that exists after step 1
       and append a clone of the donor there.
    3. Point the clone's ``EffectID`` at the new record.  Without this the clone
       is a second copy of the donor page: the byte recipe produces a valid
       technology that does nothing new, and the interface would report a page
       the player cannot see.

    ``info`` carries ``effect`` (the new record's index), ``tech`` (its id, which
    is its position), ``effect_bytes`` / ``tech_bytes`` so a test can assert the
    size of the gesture, and ``hide`` / ``on`` as planned.
    """
    # AN EMPTY PAGE IS A REAL PAGE.  The screen builds the button first and the
    # player then drops unit icons into it one at a time, so the record that
    # gets written at that moment turns nothing on yet.  Refusing it here would
    # leave the interface with no way to start a cycle except by typing IDs
    # into a text box, which is exactly what was asked to go away.
    hide = sorted(set(int(u) for u in (hide_units or ())))
    on = sorted(set(int(u) for u in on_units or ()))
    if on and set(on) == set(hide):
        raise PageError("这一页显示的正好是它自己藏起来的那些单位，"
                        "翻过去什么也不剩")
    bld = int(building if building is not None else 0)
    if not bld:
        raise PageError("这一页属于哪座建筑？建筑编号不能是 0")
    btn = int(button if button is not None else 0)
    cmds = page_commands(on=on, off=hide, building=bld)
    img = effect_bytes(name or ("Page%d" % (effect_count + 1)), cmds)

    steps = []
    # (1) the effect record, then its count.  The count is at `effects_start`,
    # which is BEFORE the splice point, so its own address does not move.
    steps.append((effects_end, 0, img))
    steps.append((effects_start, 4, struct.pack("<i", effect_count + 1)))
    new_effect = effect_count

    # (2) the technology, planned on the buffer step 1 produces.  Planning it on
    # the ORIGINAL buffer at `tail + grown` walks the technology section from an
    # address that does not exist yet: the first version of this line raised
    # `IndexError: index out of range` inside `walk_tech`, reading the last
    # technology's name bytes as a record.  The returned offsets are therefore
    # already in post-step-1 coordinates, which is what `apply_steps` wants --
    # each write's `off` is an address in the buffer state it is applied to, and
    # `relocate.splice_rules` subtracts the earlier deltas back out.
    work = bytearray(buf)
    work, _w1 = REC.apply_steps(work, steps, inplace=True)
    grown = len(work) - len(buf)
    tsteps, tinfo = REC.plan_add_tech(work, gv, tail + grown, donor_tech,
                                      internal_name=(name or "").strip() or None)
    tech_bytes = len(tsteps[0][2])

    # (3) the pointer and the terms.  The offsets are measured, never assumed:
    # `EffectID` sits after a version-dependent run of string ids and cost
    # slots, and a clone whose copy of it is not rewritten is a duplicate page
    # (valid data, nothing new on screen).  `read_tech_fields` is the one reader
    # that walks exactly the bytes the engine walks, so its field list is what
    # this uses for every patch below.
    spot = Rec(tsteps[0][2], gv)
    read_tech_fields(spot)
    where = {f[0]: (f[1], f[2]) for f in spot.fields}
    if "EffectID" not in where:
        raise PageError("这条科技记录里找不到效果编号那两字节，不能把新页接上去")
    patched = _patch_image(
        tsteps[0][2], where,
        {"EffectID": new_effect,
         # WHICH BOX this page is drawn in.  A clone keeps the donor's
         # research location, so without these two lines "add a page to box 9"
         # on a building whose pager lives in box 15 would put the new page in
         # box 15 -- the button would appear, one box away from where it was
         # asked for.  Both names are skipped when the record layout is older
         # than `ResearchLocations[]`, in which case the box also does not exist
         # and there is nothing to write.
         "ResearchLocations.0.LocationID": bld,
         "ResearchLocations.0.ButtonID": btn,
         # A page turn must not be something to sit through.  Zero seconds means
         # the tick it is pressed is the tick it takes effect, so there is no
         # research window for a later press to cancel -- the engine has nothing
         # in flight to lose.  This is the whole mitigation for the one hazard
         # this mechanism cannot remove (see the module docstring).
         "ResearchLocations.0.ResearchTime": int(seconds),
         # Free, and free without handing resources out: the community example
         # uses negative amounts (六 gold back per press), which works but pays
         # the player for clicking.  Amount 0 with the flag cleared is the same
         # price with nothing moving.
         "ResourceCosts.0.Amount": 0,
         "ResourceCosts.0.Flag": 0,
         "ResourceCosts.1.Type": -1,
         "ResourceCosts.1.Amount": 0,
         "ResourceCosts.1.Flag": 0,
         "ResourceCosts.2.Type": -1,
         "ResourceCosts.2.Amount": 0,
         "ResourceCosts.2.Flag": 0,
         # Pressable again and again: without this the page vanishes after one
         # press and the box is stuck on whatever it showed.
         "Repeatable": 1})
    steps.extend([(tsteps[0][0], tsteps[0][1], patched), tsteps[1]])

    info = {"effect": new_effect, "tech": tinfo["id"], "donor": donor_tech,
            "effect_bytes": len(img), "tech_bytes": tech_bytes,
            "total_bytes": len(img) + tech_bytes,
            "commands": len(cmds), "on": on, "hide": hide, "building": bld,
            "button": btn, "name": name or "", "seconds": int(seconds),
            # The technology section's count lives at the OLD tail, and the old
            # tail only moves by what the effect append added -- the technology
            # append happens after that count, so it does not move it.  Reading
            # it back at `tail + total_bytes` finds the last record's name bytes
            # and `walk_tech` raises IndexError, which is why this number is
            # returned rather than left for the caller to guess.
            "tail": tail + len(img)}
    return steps, info


def sync_off(pages, building):
    """Recompute every page's "hide" list from the units the others show.

    WHY THIS EXISTS: a box's pages all sit on ONE button, so pressing page N has
    to also turn OFF what page M turned on -- otherwise the units of both pages
    stay trainable and the box shows a mixture nobody asked for.  The rule that
    keeps the box consistent is therefore

        page N's off  ==  (union of every page's on)  -  page N's on

    which is exactly the default `plan_add_page` computes for a page being
    appended.  Once the player starts editing pages AFTER they exist (dropping
    an icon into page 2, taking one out of page 1), that invariant has to be
    restored for the whole box in one go, and this is that one go:
    ``pages`` is `[{"effect": index, "on": [ids]}, ...]`, the result is the
    ``changes`` argument `plan_rewrite_pages` takes.

    ``building`` is written into every page, including the ones whose on/off did
    not change: a page whose commands were written by another tool may point its
    "on" at a different building, and rewriting it to the box's building is what
    makes the whole box pressable from the same button.
    """
    all_on = set()
    for page in pages or ():
        all_on.update(int(u) for u in (page.get("on") or ()))
    bld = int(building or 0)
    out = {}
    for page in pages or ():
        on = sorted(set(int(u) for u in (page.get("on") or ())))
        # A unit that no page turns on but this page turns OFF is kept: that is
        # a deliberate "hide this one everywhere in this box", and dropping it
        # on the next edit would silently make it trainable again.
        kept = set(int(u) for u in (page.get("off") or ())) - all_on
        off = sorted((all_on - set(on)) | kept)
        out[int(page["effect"])] = {"on": on, "off": off, "building": bld}
    return out


def plan_drop_page(buf, gv, tail, tech_id):
    """Plan the removal of ONE page: its technology record, nothing else.

    A page IS a technology record (`read_group` finds pages by walking the
    technology section), so dropping a page is `records.plan_remove_tech` and
    the records after it simply move down.  Two things are deliberately NOT
    cleaned up:

    * the page's EFFECT record stays behind as an orphan.  Nothing points at it
      any more, so the engine never reads it, and the alternative -- shrinking
      the effect block and renumbering every `EffectID` in the file -- is a
      rewrite of the whole technology section for a record that costs 30 bytes;
    * every other page keeps its own `EffectID`, because those pointers are
      indexes into a block that did not move.

    ``info["delta"]`` is negative: the file gets shorter by the record's width,
    which is what `App._card_splice` expects for ``expect``.
    """
    steps, info = REC.plan_remove_tech(buf, gv, tail, tech_id)
    info["delta"] = -int(info.get("bytes") or 0)
    return steps, info


def add_page(buf, gv, tail, effects_start, effects_end, effect_count,
             donor_tech, name, on_units, hide_units=None, building=None,
             seconds=0, button=None):
    """``plan_add_page`` applied to a copy of ``buf``."""
    steps, info = plan_add_page(
        buf, gv, tail, effects_start, effects_end, effect_count, donor_tech,
        name, on_units, hide_units=hide_units, building=building,
        seconds=seconds, button=button)
    out, info["writes"] = REC.apply_steps(buf, steps)
    info["steps"] = steps
    return out, info

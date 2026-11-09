# -*- coding: utf-8 -*-
"""pseudopage.py -- more command-panel pages than the panel has boxes.

WHAT THE PANEL REALLY HAS
-------------------------
`widgetui/commandpanel.json` gives the left panel exactly 15 `CommandButton`
widgets (5 columns x 3 rows, named ``Button11``..``Button53``), and the engine
draws a second screen of 15 for the same building.  There is no third screen and
no widget to add one: measured on the retail client, the panel JSON carries 170
widgets and not one of them is a pager (the red arrow that flips the two screens
is drawn by the engine, not described by data).  So 30 boxes per building is a
hard ceiling and writing box 31 or later produces bytes the engine reads and
never draws.

WHAT THIS MODULE ADDS
---------------------
A BOX IS NOT A BUTTON.  Every box is a ``button_id`` 1..30, and a button id may
carry ANY NUMBER of technologies: the game draws them in one box, one at a time,
and each of them is a real researchable item.  So a box can be a page-turner.

The trick needs three things from the data, all of them ordinary fields:

1. **A unit's train location can be turned off and on** with effect command
   type 0 (``Attribute Modifier (Set)``) writing attribute **42** -- the unit
   attribute this project's vocabulary calls 「训练地点」.  A value of ``-1``
   takes the unit off the building entirely; the value being the BUILDING ID
   puts it back on that building's card, in the box the unit's own
   ``Creatable.TrainLocations[0].ButtonID`` already says.

2. **A technology can be researched any number of times** with
   ``Repeatable = 1``, which is what lets one button be pressed again and again
   instead of disappearing after the first press.

3. **Technology type 0 with a zero-or-negative cost** makes the press free, so
   the page turn costs the player nothing.

One page is therefore one technology whose effect turns a batch of units OFF and
another batch ON.  N pages on one button = one box that cycles through N batches
of units forever, and the file grows by one technology (about 81 bytes) plus one
effect record (18 + 11 per command) per page -- which is why there is no
practical upper limit on the number of pages even though there is a hard limit
on boxes.

THE PRICE OF THE TRICK, STATED PLAINLY
--------------------------------------
A page turn REWRITES WHERE ITS UNITS ARE TRAINABLE.  Anything already in flight
that depended on the old answer is affected:

* a unit part-way through production at that building loses its train location
  and the queue entry disappears with it;
* a technology part-way through research at that building loses its research
  location and the research is dropped.

This is not a bug in this module and there is no flag that turns it off: it is
the same data the engine consults, changed under a running game.  Two honest
mitigations exist and both are applied by :func:`plan_add_page`:

* the generated page costs nothing and takes **0 seconds** to research, so there
  is no research window to cancel -- the press resolves on the tick it happens;
* each page hides the union of what every other page shows, not just the batch
  of the page before it, so pressing pages out of order cannot leave two batches
  trainable at once (the community example chains page N's OFF to page N-1's ON,
  which is correct only if the player always presses the next page).

The remaining risk -- a production queue at that building -- cannot be fixed
from the data.  The player has to finish the queue first, and the interface says
so where the button is.

WHAT THIS PROJECT COULD ALREADY DO, AND WHAT IT COULD NOT
--------------------------------------------------------
``/api/effect-set`` can rewrite one attribute command (so a page's OFF/ON sets
were editable one command at a time), ``/api/field-set`` can move a page to
another button, and ``/api/record-add`` can clone a technology.  What was
missing is the whole gesture: append an effect record, append a technology, and
point the technology's ``EffectID`` at the new record.  The last step is why
this module exists at all -- the cloned technology carries the donor's
``EffectID``, so a clone with no patch is a second copy of page N, and the patch
offset is only knowable by walking the record (the field is not at a fixed
position: it sits after a version-dependent run of string ids and costs, and
``read_tech_fields`` is the one reader that agrees with the engine byte for
byte).
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
    "_free_to_press",
    "effect_bytes", "fast_effects",
]


#: The unit attribute a page writes: 「训练地点」.  Effect command type 0 sets an
#: attribute; ``-1`` is "not trainable anywhere", a building id is "trainable
#: here".  See `aoe2mod/game/fieldbook.py` for the label this project shows.
PAGE_ATTR = 42

#: Effect command type 0 = ``Attribute Modifier (Set)``
#: (``aoe2mod/schema/effect_command_types.json``).
CMD_ATTRIBUTE_SET = 0


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
        return None
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
        return None
    if not off and not _free_to_press(tech):
        return None
    return {"on": sorted(set(on)), "off": sorted(set(off)),
            "building": _building_of(cmds), "commands": len(cmds),
            "other": other, "first": not off}


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
    if not on_units:
        raise PageError("这一页要显示哪些单位？一个都没选就不会有新东西出现")
    hide = sorted(set(int(u) for u in (hide_units or ())))
    on = sorted(set(int(u) for u in on_units))
    if set(on) == set(hide):
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

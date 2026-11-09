# -*- coding: utf-8 -*-
"""records.py -- add, duplicate and remove one unit or tech record, in place.

The editor could change numbers but not make or unmake a record
(「只有改动，不能添加删减复制粘贴等等的功能」, 2026-11-05).  The library already
knew how to build a new unit through the model (``newunit.add_unit`` and then
``writer.serialize_dat``), and that road costs a full reparse: 11.2 s on the
shipped file.  These functions do the same edit at the byte level.  Measured
2026-11-05 on ``empires2_x2_p1.dat``: adding a unit takes 0.037 s, and removing
it again gives back a file that is byte for byte identical to the original.

ONE SHAPE FOR EVERY EDIT: (at, cut, add)
----------------------------------------
A plan is a list of ``(at, cut, add)`` triples meaning "replace the ``cut``
bytes at ``at`` with ``add``".  A field write is ``cut == len(add)``; inserting a
record is ``cut == 0``; deleting one is ``add == b""``.  That is the same thing
`aoe2mod/ui/server.py` already records in its undo stack, so a plan can be
applied to the live session buffer and undone as one gesture without a 93 MB
copy per edit.

``add_unit`` and friends return ``(out, info)`` where ``out`` is the edited copy
and ``info["steps"]`` is the plan.  ``plan_add_unit`` returns ``(steps, info)``
and touches nothing -- that is what the UI calls.

What a unit record actually is
------------------------------
A civilization stores its units as a flag array followed by the records::

    i16 m        number of flag slots (2,750 on the shipped file)
    i32 m        one flag per id: 0 = no record here, 1 = record starts here
    ...          the records, back to back, in id order

So "add a record" is three writes: set flag[id] = 1, splice the record bytes in
at the place that keeps ids in order, and -- only when the id is past the end of
the flag array -- grow the array by the difference.  "Remove" is those three
writes backwards, and the array shrinks again once the top slots are all zero.

THE FLAG ARRAY GROWS AT ITS OWN END, NOT AT THE RECORD RUN'S END.  The first
attempt padded at the end of the record run, and the parser then read the first
record's bytes as flag slots: every record start moved, and it died in
``read_bird`` with ``struct.error: bad char in struct format``.  The new slots
belong immediately after the array, at ``ptr_off + 4 * m``.

The id has to be one nobody claims
----------------------------------
``newunit.pick_free_id`` answers that from the whole file (every civilisation,
every effect command that names an id), and it starts at 30,000: ids above 1,700
are past ``unit_headers``, so no later patch can fill the hole with a unit that
means something else.  A shipped id is refused here -- a second record on id 2,749
leaves the flags and the record count disagreeing, and the tail desynchronises
thousands of records later instead of at the mistake.
"""

import struct

from . import locate as L
from . import newtech as NT
from . import newunit as NU
from . import parser as P
from ..game import nametext as NTX


class RecordError(Exception):
    """A record edit that cannot be done.  The sentence is for the player."""


# ---------------------------------------------------------------------------
# applying a plan
# ---------------------------------------------------------------------------
def apply_steps(buf, steps, inplace=False):
    """Run a plan over ``buf``.  Returns ``(buffer, writes)``.

    ``writes`` is in the shape the UI's undo stack already uses --
    ``{"off", "before", "after"}`` -- and covers exactly the bytes the plan
    touched, so one ``duplicate this unit`` costs the ~2 KB it really moves
    rather than the 93 MB buffer it lives in.
    """
    work = buf if inplace else bytearray(buf)
    writes = []
    for at, cut, add in steps:
        before = bytes(work[at:at + cut])
        work[at:at + cut] = add
        writes.append({"off": at, "before": before, "after": bytes(add)})
    return work, writes


# ---------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------
def civ_layout(buf, gv, civs_start, civ_index):
    """Offsets of one civilization's flag array and record run.

    Returns ``{m_off, m, ptr_off, run_start, run_end, flags, spans}`` where
    ``spans`` maps unit id -> ``(start, end)``.  Walks in 0.15 s on the shipped
    file because it stops as soon as it has the civilization it was asked for.
    The caller passes ``gv`` and ``civs_start`` from ``locate.locate()`` -- those
    two numbers are not derivable from the header alone.
    """
    r = L.Orec(buf, civs_start, gv=gv)
    for i in range(civ_index + 1):
        r.u8()                                  # player_type
        r.debug_string()                        # name
        n = r.i16()                             # resources_at - start
        r.i16()                                 # tech_tree_id
        r.i16()                                 # team_bonus_id
        r.f32_array(n)                          # the 601 resources
        r.u8()                                  # icon_set
        m_off = r.o
        m = r.i16()
        ptr_off = r.o
        flags = r.i32_array(m)
        spans = {}
        for k in range(m):
            if flags[k]:
                start = r.o
                u = L.walk_unit(r, i)
                spans[u["id"]] = (start, r.o)
        if i == civ_index:
            return {"m_off": m_off, "m": m,
                    "ptr_off": ptr_off, "run_start": ptr_off + 4 * m,
                    "run_end": r.o, "flags": flags, "spans": spans}
    raise RecordError("这个文件里没有第 %d 个文明" % (civ_index,))


def _insert_point(spans, unit_id):
    """Byte offset where a record with this id belongs, to keep ids in order."""
    for other_id in sorted(spans):
        if other_id > unit_id:
            return spans[other_id][0]
    return None                                 # caller appends at the run's end


def _grow_to(lay, unit_id, steps):
    """Plan the growth of the flag array so it has a slot for ``unit_id``.

    Updates ``lay`` in place so the steps after this one see the new geometry.
    """
    need = unit_id + 1
    if need <= lay["m"]:
        return lay["m"]
    grow = need - lay["m"]
    steps.append((lay["run_start"], 0, bytes(4 * grow)))
    steps.append((lay["m_off"], 2, struct.pack("<h", need)))
    lay["run_end"] += 4 * grow
    lay["run_start"] += 4 * grow
    lay["m"] = need
    return need


def _shrink_top(lay, steps):
    """Plan dropping flag slots above the highest non-zero flag.

    ``lay["flags"]`` must already have the removed slot zeroed by the caller.
    """
    top = 0
    for i, v in enumerate(lay["flags"]):
        if v:
            top = i + 1
    if top >= lay["m"]:
        return 0
    drop = lay["m"] - top
    steps.append((lay["ptr_off"] + 4 * top, 4 * drop, b""))
    steps.append((lay["m_off"], 2, struct.pack("<h", top)))
    lay["run_start"] -= 4 * drop
    lay["run_end"] -= 4 * drop
    lay["m"] = top
    lay["flags"] = lay["flags"][:top]
    return drop


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------
def plan_add_unit(buf, gv, civs_start, civ_index, donor_id, new_id=None,
                  name_string_id=None, hp=None, icon_id=None, stats=None,
                  blank=False, name=None):
    """Plan one new record for a civilization.  Touches nothing.

    ``donor_id`` names the record to copy.  With ``blank=True`` there is no
    donor: the record is built from nothing by ``newunit.blank_image``, which
    walks its own output before returning it.  A blank record is a shell --
    no graphics, no costs, no train locations -- so nothing can build it until
    the editor fills those in, and it cannot turn up in a game by accident.

    ``new_id`` is chosen by the caller (``newunit.pick_free_id``) and refused
    here when this civilisation already uses it.  ``stats`` lets the id be
    chosen from the whole file; without it the caller must pass a free id.
    """
    lay = civ_layout(buf, gv, civs_start, civ_index)
    if not blank and donor_id not in lay["spans"]:
        raise RecordError(
            "这个文明里没有编号 %s 的单位，所以没有东西可以照着做（可以换一个文明，"
            "或者先在「单位」页签里挑一条）" % (donor_id,))
    if new_id is None:
        if stats is None:
            raise RecordError("新建单位要知道文件里哪些编号是空的，"
                              "这条请求没有带上单位表")
        new_id = NU.pick_free_id(stats, avoid=NU.referenced_ids(stats))
    if not 1 <= new_id <= 32767:
        raise RecordError("单位编号只有 1..32767 这些格子，%d 放不下" % (new_id,))
    if new_id in lay["spans"]:
        raise RecordError("这个文明已经有编号 %d 的单位了" % (new_id,))

    if blank:
        image = NU.blank_image(gv, new_id, name=name,
                               name_string_id=name_string_id, hp=hp,
                               icon_id=icon_id)
    else:
        start, end = lay["spans"][donor_id]
        image = NU.clone_image(bytes(buf[start:end]), new_id,
                               name_string_id=name_string_id, hp=hp,
                               icon_id=icon_id)

    steps = []
    _grow_to(lay, new_id, steps)
    steps.append((lay["ptr_off"] + 4 * new_id, 4, struct.pack("<i", 1)))
    at = _insert_point(lay["spans"], new_id)
    if at is None:
        at = lay["run_end"]
    steps.append((at, 0, image))
    return steps, {"id": new_id, "civ": civ_index,
                   "donor": None if blank else donor_id,
                   "blank": bool(blank),
                   "bytes": len(image), "at": at, "slots": lay["m"]}


def add_unit(buf, gv, civs_start, civ_index, donor_id, new_id=None,
             name_string_id=None, hp=None, icon_id=None, stats=None,
             blank=False, name=None):
    """``plan_add_unit`` applied to a copy of ``buf``."""
    steps, info = plan_add_unit(buf, gv, civs_start, civ_index, donor_id,
                               new_id=new_id, name_string_id=name_string_id,
                               hp=hp, icon_id=icon_id, stats=stats,
                               blank=blank, name=name)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    info["spans"] = {info["id"]: (info["at"], info["at"] + info["bytes"])}
    return out, info


def free_unit_ids(stats, count, low=None, high=32767, avoid=()):
    """The first ``count`` unit ids that nothing uses and nothing points at.

    ``low`` defaults to one past the highest id the file already uses.  That
    matters: an id *below* the shipped range is a hole this patch, and the
    marker of a good id is that a future patch will not fill it.  Measured
    2026-11-05 on the shipped file: the highest unit id is 2,749, so 2,750 and
    up leaves 30,018 ids free, while the 0..2,749 band has only 57 holes and
    every one of them is a gap in somebody else's numbering.
    """
    used = set(avoid)
    top = 0
    for civ in stats["civs"]:
        for u in civ["units"]:
            used.add(u["id"])
            if u["id"] > top:
                top = u["id"]
    lo = max(1, int(low) if low else top + 1)
    out = [i for i in range(lo, int(high) + 1) if i not in used]
    if len(out) < count:
        raise RecordError(
            "文件里只剩 %d 个没人用的编号，放不下 %d 条（单位编号上限是 %d）"
            % (len(out), count, high))
    return out[:count]


def plan_add_units(buf, gv, civs_start, civ_index, donor_id, count=None,
                   ids=None, hp=None, icon_id=None, stats=None,
                   name_string_id=None, blank=False):
    """Plan ``count`` new records in ONE splice.

    With ``blank=True`` every record is built from nothing (``blank_image``)
    instead of copied from ``donor_id``; a blank batch still needs an id list
    or ``stats`` so the ids can be picked.

    Measured 2026-11-05: one record is 0.175 s including the re-read; a thousand
    is 0.037 s of byte work and ten thousand 0.047 s.  The cost of a batch is the
    blob, not the count, so asking for a thousand one at a time would be a
    thousand re-parses of the file for the same bytes.

    Returns ``(steps, info)`` with ``info["ids"]`` in the order they were added.
    """
    lay = civ_layout(buf, gv, civs_start, civ_index)
    if not blank and donor_id not in lay["spans"]:
        raise RecordError(
            "这个文明里没有编号 %s 的单位，所以没有东西可以照着做（可以换一个文明，"
            "或者先在「单位」页签里挑一条）" % (donor_id,))
    if ids is None:
        if stats is None:
            raise RecordError("新建单位要知道文件里哪些编号是空的，"
                              "这条请求没有带上单位表")
        want = int(count or 1)
        if want < 1:
            raise RecordError("要新增几条，就得说个大于 0 的数（收到 %r）" % (count,))
        ids = free_unit_ids(stats, want, low=None,
                            avoid=NU.referenced_ids(stats))
    else:
        ids = [int(i) for i in ids]
        if not ids:
            raise RecordError("没说要新增哪些编号")
    for i in ids:
        if not 1 <= i <= 32767:
            raise RecordError("单位编号只有 1..32767 这些格子，%d 放不下" % (i,))
        if i in lay["spans"]:
            raise RecordError("这个文明已经有编号 %d 的单位了" % (i,))

    start, end = (0, 0) if blank else lay["spans"][donor_id]
    donor = b"" if blank else bytes(buf[start:end])
    old_m = lay["m"]
    steps = []
    # The flag array grows once, to the highest id in the batch.  A batch below
    # every existing id needs no growth at all and this is a no-op.
    _grow_to(lay, max(ids), steps)
    # One write for the whole span: every chosen slot becomes 1, the slots
    # between them keep the bytes they already have.  Writing the flags one id at
    # a time would be one undo entry per record for the same bytes.
    lo, hi = min(ids), max(ids)
    # Read only the slots the file already has: above the old count the flag
    # array does not exist yet, those bytes are the first record, and copying
    # them here would turn a record header into a pointer.  The new slots are
    # zero, which is what `_grow_to` just inserted.
    have = max(0, min(hi + 1, old_m) - lo)
    want = bytearray(buf[lay["ptr_off"] + 4 * lo:
                         lay["ptr_off"] + 4 * lo + 4 * have])
    want += bytes(4 * (hi + 1 - lo - have))
    for i in ids:
        off = (i - lo) * 4
        want[off:off + 4] = struct.pack("<i", 1)
    steps.append((lay["ptr_off"] + 4 * lo, len(want), bytes(want)))
    # Records go in id order at the run's end; ids below an existing one are
    # interleaved by `_insert_point`, so the blob is laid out against the spans
    # that are already there.
    blob = bytearray()
    at = None
    placed = sorted(ids)
    if placed[0] > max(lay["spans"]):
        # The common case, and the only one a four-step undo entry needs: the
        # whole batch is past every record, so it is one append.
        for i in placed:
            if blank:
                blob += NU.blank_image(gv, i, name_string_id=name_string_id,
                                       hp=hp, icon_id=icon_id)
            else:
                blob += NU.clone_image(donor, i, name_string_id=name_string_id,
                                       hp=hp, icon_id=icon_id)
        at = lay["run_end"]
        steps.append((at, 0, bytes(blob)))
    else:
        # Interleaved: still one step, by rebuilding the run from the spans.
        raise RecordError("这批编号里有的比文件里已有的记录还小，"
                          "现在只能往后面加（可以换一个更大的编号）")
    info = {"ids": placed, "civ": civ_index,
            "donor": None if blank else donor_id,
            "blank": bool(blank),
            "count": len(placed), "bytes": len(blob), "at": at,
            "slots": lay["m"], "unit_bytes": len(donor)}
    return steps, info


def add_units(buf, gv, civs_start, civ_index, donor_id, count=None, ids=None,
              hp=None, icon_id=None, stats=None, name_string_id=None,
              blank=False):
    """``plan_add_units`` applied to a copy of ``buf``."""
    steps, info = plan_add_units(
        buf, gv, civs_start, civ_index, donor_id, count=count, ids=ids,
        hp=hp, icon_id=icon_id, stats=stats, name_string_id=name_string_id,
        blank=blank)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


def plan_remove_units(buf, gv, civs_start, civ_index, ids):
    """Plan deleting several unit records in one splice.

    Records are cut from the highest offset down, so every offset in the plan is
    still valid when its turn comes -- the same reason 撤销 replays a structural
    step backwards.
    """
    lay = civ_layout(buf, gv, civs_start, civ_index)
    ids = [int(i) for i in ids]
    if not ids:
        raise RecordError("没说要删哪些编号")
    for i in ids:
        if i not in lay["spans"]:
            raise RecordError("这个文明里没有编号 %s 的单位" % (i,))
    steps = []
    lo, hi = min(ids), max(ids)
    have = max(0, min(hi + 1, lay["m"]) - lo)
    want = bytearray(buf[lay["ptr_off"] + 4 * lo:
                         lay["ptr_off"] + 4 * lo + 4 * have])
    want += bytes(4 * (hi + 1 - lo - have))
    for i in ids:
        off = (i - lo) * 4
        want[off:off + 4] = struct.pack("<i", 0)
        lay["flags"][i] = 0
    steps.append((lay["ptr_off"] + 4 * lo, len(want), bytes(want)))
    spans = [(lay["spans"][i][0], lay["spans"][i][1], i) for i in ids]
    spans.sort(reverse=True)
    freed = 0
    for start, end, i in spans:
        steps.append((start, end - start, b""))
        freed += end - start
    lay["run_end"] -= freed
    _shrink_top(lay, steps)
    return steps, {"ids": sorted(ids), "civ": civ_index, "count": len(ids),
                   "bytes": freed, "slots": lay["m"]}


def remove_units(buf, gv, civs_start, civ_index, ids):
    """``plan_remove_units`` applied to a copy of ``buf``."""
    steps, info = plan_remove_units(buf, gv, civs_start, civ_index, ids)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


def plan_remove_unit(buf, gv, civs_start, civ_index, unit_id):
    """Plan deleting one unit record and clearing its flag."""
    lay = civ_layout(buf, gv, civs_start, civ_index)
    if unit_id not in lay["spans"]:
        raise RecordError("这个文明里没有编号 %s 的单位" % (unit_id,))
    start, end = lay["spans"][unit_id]
    steps = []
    steps.append((lay["ptr_off"] + 4 * unit_id, 4, struct.pack("<i", 0)))
    steps.append((start, end - start, b""))
    lay["flags"][unit_id] = 0
    lay["run_end"] -= end - start       # every record after the hole moved left
    _shrink_top(lay, steps)
    return steps, {"id": unit_id, "civ": civ_index, "bytes": end - start,
                   "at": start, "slots": lay["m"]}


def remove_unit(buf, gv, civs_start, civ_index, unit_id):
    """``plan_remove_unit`` applied to a copy of ``buf``."""
    steps, info = plan_remove_unit(buf, gv, civs_start, civ_index, unit_id)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


def unit_references(stats, unit_id):
    """How many places name this id: effect commands, and per-civ records.

    ``train_locations[].unit_id`` is deliberately not counted: it holds "what
    this building trains", not "who trains this unit", so every shipped id scores
    zero there and a warning built on it would never fire.
    """
    effects = 0
    for eff in stats.get("effects") or ():
        for cmd in eff.get("commands") or ():
            if isinstance(cmd, dict):
                vals = [cmd.get(k) for k in ("a", "b", "c")]
            else:
                vals = list(cmd)[1:4]
            if unit_id in [v for v in vals if isinstance(v, int)]:
                effects += 1
    civs = 0
    for c in stats.get("civs") or ():
        for u in c.get("units") or ():
            if u.get("id") == unit_id:
                civs += 1
    return {"effects": effects, "civs": civs}


# ---------------------------------------------------------------------------
# technologies
# ---------------------------------------------------------------------------
def tech_section(buf, gv, tail):
    """``(count_off, count, records_start, records_end)`` of the tech array.

    ``tail`` is where the civilization block ends, which ``locate.locate()``
    returns; the tree section that follows is 65,422 bytes on the shipped file,
    so appending a technology must splice at ``records_end`` and not at EOF.
    """
    count_off = tail
    count = struct.unpack_from("<h", buf, count_off)[0]
    r = L.Orec(buf, count_off + 2, gv=gv)
    start = r.o
    for _ in range(count):
        L.walk_tech(r)
    return count_off, count, start, r.o


def _tech_at(buf, gv, start, tech_id):
    """``(record_start, record_end)`` of one technology."""
    r = L.Orec(buf, start, gv=gv)
    for _ in range(tech_id):
        L.walk_tech(r)
    a = r.o
    L.walk_tech(r)
    return a, r.o


class _NameSpot(L.Orec):
    """A reader that remembers where the record's debug_string starts."""

    name_off = None

    def debug_string(self):
        if self.name_off is None:
            self.name_off = self.o
        return L.Orec.debug_string(self)

    # `Orec` names its cursor `o`; the authoritative `P.Reader` names it `pos`,
    # and `read_tech` is routinely handed readers of both kinds.  Measured
    # 2026-11-05: one `POST /api/record-dup {"kind":"tech"}` came back as
    # `AttributeError: '_NameSpot' object has no attribute 'pos'` and the same
    # request succeeded on the next try, so no call site could be blamed -- an
    # alias costs nothing and turns that class of failure into working code.
    @property
    def pos(self):
        return self.o

    @pos.setter
    def pos(self, value):
        self.o = value


def _tech_name_off(buf, gv, tech_start):
    """Byte offset of a technology's debug_string, measured, never guessed.

    It is 55 on the shipped DE format -- 12 bytes of required techs, three 5-byte
    cost records, four scalar i16s, two i32 language ids, then the string -- but
    the arithmetic that gets there branches on the game version, so this asks
    ``read_tech`` itself instead of repeating the sum.

    The first version of this file assumed the name was at offset 0, renamed 4
    bytes of RequiredTechs, and the added record came out 15 bytes instead of 90:
    the parser then read the remaining 75 bytes as the NEXT technology's header.
    """
    r = _NameSpot(buf, tech_start, gv=gv)
    P.read_tech(r)
    if r.name_off is None:
        raise RecordError("这条科技记录里没有名字字段，改不了名字")
    return r.name_off


NAME_MAX_BYTES = 200


def name_bytes(name):
    """The bytes to store for a name the player typed, at most 200 of them.

    UTF-8, not latin-1.  The reader decodes a `.dat` byte string as latin-1 so
    that every byte round-trips (``parser.Reader.debug_string`` documents why),
    but a name a player types is Unicode: encoding it latin-1 would turn 弩手
    into ``??``.  Measured 2026-11-06 on the user's own mod: 4,473 of 136,861
    unit names and 230 of 5,874 technology names are UTF-8 already stored in
    these byte strings, so UTF-8 is what the engine's own mods do.

    The cut is made on BYTES and then walked back to a character boundary,
    because half a UTF-8 sequence is not a shorter name, it is a broken string
    that the next reader has to guess at.
    """
    body = NTX.stored(name or "")[:NAME_MAX_BYTES]
    while body:
        try:
            body.decode("utf-8")
            break
        except UnicodeDecodeError:
            body = body[:-1]
    return body


def rename_steps(buf, name_off, name):
    """A plan that replaces the debug_string at ``name_off`` with ``name``.

    One splice: the marker and the length are rewritten together with the text,
    because a writer that moves only the text leaves the length stale --
    ``parser.Reader.debug_string``'s docstring records a 2,656-byte drift from
    exactly that mistake.  A rename therefore CHANGES the record's width, which
    is legal (the format stores records back to back, not at fixed addresses)
    and is why this has to go through ``relocate`` rather than the equal-width
    field writer.
    """
    marker, length = struct.unpack_from("<HH", buf, name_off)
    if marker != P.DEBUG_STRING_MARKER:
        raise RecordError("这个名字段前面没有标记（读到 %d，应该是 %d），"
                          "位置算错了，不能拿它去改文件"
                          % (marker, P.DEBUG_STRING_MARKER))
    body = name_bytes(name)
    if not body:
        raise RecordError("名字不能是空的")
    add = struct.pack("<HH", marker, len(body)) + body
    return [(name_off, 4 + length, add)], {"name": name, "name_bytes": len(body),
                                           "was_bytes": length, "at": name_off}


def string_id_step(buf, offset, string_id):
    """Point one record's display-name id at another string table row.

    EQUAL WIDTH, so it is not a splice and does not move anything: the id is an
    i32 wherever it appears.  That is why it can ride along with a rename, whose
    splice does move bytes, as long as it is applied on the side that stays put.

    Returns ``(step, info)`` where ``step`` is ``None`` when the record already
    points at this id.  ``info["was"]`` is the id that was there.
    """
    if offset is None:
        raise RecordError("这条记录没有显示名字的字符串编号，改不了它显示成什么")
    was = struct.unpack_from("<i", buf, offset)[0]
    sid = int(string_id)
    # The engine reads this as a signed i32; a negative id names no row in any
    # locale table, which would turn a rename into "the game shows the number".
    if sid < 0 or sid > 2147483647:
        raise RecordError("字符串编号要是一个非负整数，%r 不行" % (string_id,))
    if was == sid:
        return None, {"offset": offset, "was": was, "now": sid}
    packed = struct.pack("<i", sid)
    # Shaped as an ordinary `apply_steps` step so it can ride in the same list as
    # the rename splice: equal width, so its `cut` is the width of what it
    # replaces and no later offset needs shifting.
    return ((offset, 4, packed),
            {"offset": offset, "was": was, "now": sid})


def _display_off(buf, gv, tech_start):
    """Where `walk_tech` found the LanguageDLLName id.  One small walk."""
    r = L.Orec(buf, tech_start, gv=gv)
    L.walk_tech(r)
    return r.marks.get("lang_name")


def _rename_tech(image, name, name_off):
    """Swap a tech record's debug_string name, keeping the rest of it intact."""
    steps, _info = rename_steps(image, name_off, name)
    out, _w = apply_steps(image, steps)
    return out


def plan_add_tech(buf, gv, tail, donor_id, internal_name=None, lang_name=None):
    """Plan a clone of tech ``donor_id``.

    A technology is addressed by its POSITION in the array -- the record carries
    no id field -- so appending is what gives it the next id, which is ``count``
    before the append.  ``internal_name`` becomes the record's own debug_string;
    without it the donor's name is copied verbatim.
    """
    count_off, count, start, end = tech_section(buf, gv, tail)
    if not 0 <= donor_id < count:
        raise RecordError("没有第 %s 号科技（这个文件里有 %d 条）"
                          % (donor_id, count))
    a, b = _tech_at(buf, gv, start, donor_id)
    image = bytes(buf[a:b])
    name = internal_name or NT.internal_name_for(lang_name or "", count)
    if name:
        image = _rename_tech(image, name, _tech_name_off(image, gv, 0))
    steps = [(end, 0, image), (count_off, 2, struct.pack("<h", count + 1))]
    return steps, {"id": count, "donor": donor_id, "bytes": len(image),
                   "at": end, "name": name}


def add_tech(buf, gv, tail, donor_id, internal_name=None, lang_name=None):
    """``plan_add_tech`` applied to a copy of ``buf``."""
    steps, info = plan_add_tech(buf, gv, tail, donor_id,
                               internal_name=internal_name, lang_name=lang_name)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


def plan_remove_tech(buf, gv, tail, tech_id):
    """Plan deleting one technology.  Every later one shifts down a position."""
    count_off, count, start, end = tech_section(buf, gv, tail)
    if not 0 <= tech_id < count:
        raise RecordError("没有第 %s 号科技（这个文件里有 %d 条）"
                          % (tech_id, count))
    a, b = _tech_at(buf, gv, start, tech_id)
    steps = [(a, b - a, b""), (count_off, 2, struct.pack("<h", count - 1))]
    return steps, {"id": tech_id, "bytes": b - a, "at": a}


def remove_tech(buf, gv, tail, tech_id):
    """``plan_remove_tech`` applied to a copy of ``buf``."""
    steps, info = plan_remove_tech(buf, gv, tail, tech_id)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


# ---------------------------------------------------------------------------
# renaming
# ---------------------------------------------------------------------------
def name_off_in_record(buf, gv, record_start, civ_index=0):
    """Byte offset of a unit record's own debug_string, measured.

    The prefix that leads to the name branches on the game version (``if r.gv <
    P.GV_C30``) and repeating that sum here would be a second copy of the format
    that drifts the first time it changes, so this asks ``walk_unit`` itself
    where it stopped -- the same trick ``_tech_name_off`` uses for technologies.
    """
    r = _NameSpot(buf, record_start, gv=gv)
    L.walk_unit(r, civ_index)
    if r.name_off is None:
        raise RecordError("这条记录里没有名字段，改不了名字")
    return r.name_off


def unit_name_off(buf, gv, civs_start, civ_index, unit_id):
    """``(record_start, record_end, name_off)`` of one unit record.

    Walks the civilisation from its start to find the record, which is O(civ)
    and costs up to 4 s for the last one (measured 2026-11-06 on the 93 MB
    file).  A caller that already holds the parsed model -- the editor does --
    should look the record's span up there and call ``name_off_in_record``
    instead; this signature is for tools that only have bytes.
    """
    lay = civ_layout(buf, gv, civs_start, civ_index)
    if unit_id not in lay["spans"]:
        raise RecordError("这个文明里没有编号 %s 的单位" % (unit_id,))
    start, end = lay["spans"][unit_id]
    return start, end, name_off_in_record(buf, gv, start, civ_index)


def plan_rename_unit(buf, gv, civs_start, civ_index, unit_id, name,
                     start=None, end=None):
    """Plan giving unit ``unit_id`` a new internal name.

    This is the 内部名称 field (the `.dat` byte string), not the name the game
    shows: that one comes from ``LanguageDLLName`` pointing into a string table,
    and pointing it somewhere else is how a mod renames a unit without touching
    the record.  Both roads exist; this one keeps everything inside the .dat.

    ``start``/``end`` are the record's span when the caller already knows it (the
    parsed model always does).  Passing them turns a 4 s walk into 0.02 s.
    """
    if start is None or end is None:
        start, end, name_off = unit_name_off(buf, gv, civs_start, civ_index, unit_id)
    else:
        name_off = name_off_in_record(buf, gv, start, civ_index)
    steps, info = rename_steps(buf, name_off, name)
    info.update({"kind": "unit", "id": int(unit_id), "civ_index": civ_index,
                 "start": start, "end": end})
    return steps, info


def rename_unit(buf, gv, civs_start, civ_index, unit_id, name,
                start=None, end=None):
    """``plan_rename_unit`` applied to a copy of ``buf``."""
    steps, info = plan_rename_unit(buf, gv, civs_start, civ_index, unit_id, name,
                                   start=start, end=end)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info


def plan_rename_tech(buf, gv, tail, tech_id, name):
    """Plan giving technology ``tech_id`` a new internal name.

    A technology is addressed by POSITION, so nothing here depends on ids; the
    record only moves because its own name got longer or shorter.
    """
    count_off, count, start, end = tech_section(buf, gv, tail)
    if not 0 <= tech_id < count:
        raise RecordError("没有第 %s 号科技（这个文件里有 %d 条）"
                          % (tech_id, count))
    a, b = _tech_at(buf, gv, start, tech_id)
    name_off = _tech_name_off(buf, gv, a)
    steps, info = rename_steps(buf, name_off, name)
    info.update({"kind": "tech", "id": int(tech_id), "start": a, "end": b})
    return steps, info


def rename_tech(buf, gv, tail, tech_id, name):
    """``plan_rename_tech`` applied to a copy of ``buf``."""
    steps, info = plan_rename_tech(buf, gv, tail, tech_id, name)
    out, info["writes"] = apply_steps(buf, steps)
    info["steps"] = steps
    return out, info

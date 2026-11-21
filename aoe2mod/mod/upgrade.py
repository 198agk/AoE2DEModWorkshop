# -*- coding: utf-8 -*-
"""Carry a data mod's changes onto a newer shipped ``.dat``.

WHY THIS EXISTS
---------------
A data mod ships a WHOLE ``empires2_x2_p1.dat`` (93 MB raw, ~12 MB deflated on
disk).  That is how a data mod works, and it is also why every official patch
breaks every one of them: the installed mod keeps handing the engine the OLD
stream, so the patch's data changes silently vanish.  ``repair.py`` answers
"what did this mod change, and can it be replayed as intents"; that answer is
enough for the edits the intent schema can express, and for mods this project
built.  It is not enough for a third-party mod, and it is not enough for a mod
that ADDS or REMOVES records, because there is no intent verb for "graphic
1205's SlpID is 77 now".

This module answers the same question at a lower level and with no schema: it
reads the mod against the official stream it was built from, expresses every
difference as a SYMBOLIC coordinate -- ``(civ, unit id, field name)``,
``(tech index, field name)``, ``(effect index, "#3.b")``, ``(civ,
"resources.7")``, ``(table, ID, field)`` -- and then writes those same
coordinates onto today's shipped stream.  A coordinate survives a version
change; a byte offset does not.

THREE-WAY, NOT TWO-WAY
----------------------
The merge is: ``base`` (the official data the mod was built from) vs ``mod``
(what the author changed), applied onto ``new`` (today's official data).  Bytes
the author never touched therefore follow ``new`` for free -- that is the whole
point, and it is why "diff the two official files and copy the official changes
across" is the wrong mental model.  Nothing needs copying over; only the
author's own edits need re-addressing.

Edits are carried as BYTES, not as values.  A field's bytes are copied from the
mod verbatim, so an f32 keeps its exact bit pattern and no float round-trip can
quietly change a coefficient.  Only the ADDRESS is symbolic.

WHAT COUNTS AS DONE
-------------------
``upgrade()`` is not finished when it writes bytes; it is finished when
``_verify()`` proves the result is the intended one:

  * the output parses to the last byte (``Parser.parse`` consumes everything);
  * ``locate`` reports contiguous civ blocks ending exactly at the tail;
  * every table walk leaves zero leftover bytes;
  * a byte diff of the output against ``new`` covers EXACTLY the ranges this
    module meant to write -- no stray byte, no forgotten edit;
  * when records were added or removed, the output's record KEY SETS are the
    expected ones and each added record's bytes are byte-identical to the
    author's.

A region this module cannot express is never dropped.  It lands in
``report["unmapped"]`` with its stage, offset and reason, and ``upgrade()``
refuses by default rather than shipping a mod that quietly lost a change.

WHAT IT DOES NOT DO
-------------------
Nothing here installs, deletes or edits the user's profile unless asked; the
default is a folder on disk plus a report.  It also does not invent art: a mod
that adds a unit needs that unit's string ids and icon slot to still exist in
``new``, and when they do not, the record is reported rather than guessed.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import pickle
import struct
import tempfile
import time
import zlib

import aoe2mod.dat.locate as L
import aoe2mod.dat.parsecache as PC
import aoe2mod.dat.parser as P
import aoe2mod.dat.records as R
import aoe2mod.dat.tablefields as TB
import aoe2mod.dat.techfields as TF
import aoe2mod.dat.unitfields as UF
import aoe2mod.mod.portgen as PG
from . import archives as AR
from ..game import locations as GL

__all__ = ["UpgradeError", "analyze", "upgrade", "describe", "VERDICTS",
           "IDENTICAL", "UP_TO_DATE", "MERGEABLE", "CONFLICTS", "IMPOSSIBLE"]

#: Same relative path every other module uses for the one streamable `.dat`.
DAT_REL = GL.DAT_REL

#: Outcomes, spelled as words so a caller cannot typo a comparison silently.
IDENTICAL = "identical"      # mod stream IS the new official stream
UP_TO_DATE = "up_to_date"    # mod was built from this exact official data
MERGEABLE = "mergeable"      # every edit can be carried, nothing lost
CONFLICTS = "conflicts"      # carryable, but the official data moved under it
IMPOSSIBLE = "impossible"    # no usable base, generation moved, or gaps left
VERDICTS = (IDENTICAL, UP_TO_DATE, MERGEABLE, CONFLICTS, IMPOSSIBLE)

#: Declared widths of the scalar shapes the field readers report.  A ``str``
#: field has no declared width -- its extent is the gap to the next field, which
#: ``_field_ranges`` derives, because a length-prefixed string's length IS the
#: information and guessing it would be the one thing this module must not do.
_KIND_W = {"u8": 1, "u16": 2, "i16": 2, "i32": 4, "u32": 4, "f32": 4}

#: Tables a ``.dat`` mod can plausibly edit, in file order.  ``task`` and
#: ``effect`` are the two whose per-record walks are not free (5.6 s and 0.3 s),
#: which is why the same-length path lets the byte diff say whether to look.
_TABLES = ("effect", "graphic", "sound", "terrain", "task", "restriction",
           "colour")

#: Tables whose section is "count, then fixed-shape records, then nothing".
#: Those are the only ones that can be rebuilt in one splice when the author
#: added or removed records: their record offsets depend only on the records
#: before them.  ``terrain`` (nested block + random maps), ``task``
#: (header -> exists flag -> nested tasks) and the two fixed-size tables are
#: left out on purpose -- rebuilding those means re-serialising a section this
#: module does not model, and a wrong guess there is a file the game refuses.
_TABLE_FLAT = ("sound", "graphic", "effect")

# Tables carried field-by-field instead of being rebuilt from pieces: their
# records live behind section headers this module does not re-serialise, but
# every number in them has a name that survives a rebuild.
_TABLE_CARRY = ("task", "restriction")

#: Tables whose records can be REPLACED whole but whose section cannot be
#: rebuilt from pieces: nothing here appends or deletes, and there is no count
#: word this module can write for them.  ``terrain`` records are 417..479 bytes
#: of nested tile frames and their stage continues with a block tail and the
#: random maps, so the splice has to end at the last record; ``colour`` is 16
#: records of 36 bytes that close stage 1 exactly.
#:
#: Measured on 310130: three terrain records grew (417 -> 431, 455, 444) and
#: every one of them was dropped here without a word, because this function
#: only ever walked ``_TABLE_FLAT``.  A record the planner decided to copy is
#: a promise; a table this function silently skips is that promise broken.
_TABLE_REPLACE = ("terrain", "colour")

#: The two tables that live at the very END of the file: the seven i32 counters
#: and the tech-tree connections.  They are named and walkable (`tablefields`
#: has carried both for a long time), but they are not in `_TABLES` because
#: reaching them costs a walk over the whole 89 MB civ block -- measured 12 s
#: for the counters and 13.7 s for the tree on a 94 MB mod.  Paying that on
#: every analysis to learn "nothing changed there" is not a measurement, it is
#: a habit, so the cost is spent only when the end of the file actually differs.
_TABLES_EXTRA = ("tail", "techtree")

#: How much of the end of a `.dat` the cheap screen compares before it pays for
#: a tail walk.  The counters are 28 bytes and the tree is tens of kilobytes,
#: so 64 KiB covers both with room to spare.
_TAIL_SCREEN = 1 << 16

#: The seven i32 scalars that sit between the last tech record and the tech tree.
#: The names are `tablefields`' own (`TimeSlice`, `UnitKillRate`, ...), not a
#: second spelling of them: a field is addressed by the name the reader reports,
#: and a private lowercase copy addressed every one of these as "no such field"
#: in the target frame.
_TAIL_SCALARS = tuple(n for n, _zh, _h in TB._TAIL_FIELDS)


def _fmt_widths(widths):
    """"69" or "2680 / 2940" for a table's observed record widths."""
    if not widths:
        return "（空表）"
    if len(widths) == 1:
        return str(widths[0])
    return " / ".join(str(w) for w in widths[:4])


def _key_order(key):
    """A total order over table keys, so a rebuild is deterministic.

    Keys are ``("index", 3)`` for effects and ``("ID", 1234)`` for everything
    with an ID field; comparing the mixed tuples directly raises ``TypeError``
    as soon as one table has both shapes, so the tag is stringified.
    """
    parts = list(key) + [None, None]
    return (str(parts[0]),
            -1 if parts[1] is None else int(parts[1]),
            -1 if parts[2] is None else int(parts[2]))


class UpgradeError(Exception):
    """A refusal that carries a sentence the player can act on."""


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------

def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _head_ver(raw):
    """``VER 8.9`` from the first bytes of a raw stream."""
    if not raw:
        return None
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def _inflate(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        raw, _how = P.load_dat(path)
    except Exception:
        return None
    return raw


#: Slots this module keeps of its own, next to (not instead of) the product's
#: single-slot ``parsecache`` file.  Three streams are in play on every upgrade
#: -- the mod's base, the mod itself, today's official data -- and the product
#: cache holds exactly one, so each stream would evict the previous one and the
#: next run would parse all three again.  Six slots covers "the last few mods
#: the player touched" without unbounded growth; measured, one slot is ~30 MB
#: compressed and 22 MB at level 6.
_SLOT_DIR_NAME = "upgrade_slots"
_SLOTS_KEPT = 6

#: In-process memo, keyed on raw sha256.  A single ``analyze`` call already
#: touches the same stream twice (base for the mod's provenance, then base again
#: as the target when nothing changed); without this the second touch costs the
#: full parse. Only the six-tuple is kept, never the raw stream, so a memo entry
#: is the same size as a cache hit.
_FRAME_MEMO = {}


def _slot_dir():
    return os.path.join(PC.cache_dir(), _SLOT_DIR_NAME)


def _slot_path(sha):
    return os.path.join(_slot_dir(), "%s_%s.bin" % (PC._PY_TAG, sha[:16]))


def _slot_payload(raw, six):
    stats, civs, civs_start, gv, tail, how = six
    return {"raw_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_bytes": len(raw), "stats": stats, "civs": civs,
            "civs_start": civs_start, "gv": gv, "tail": tail, "how": how}


def _slot_load(raw, sha):
    """One slot back, or ``None``.  Every failure is a miss, never an error.

    A cache is an optimisation: a truncated file, a slot written by a different
    Python, a payload from an older layout -- all of them must degrade to "parse
    it again", because the alternative is a wrong parse that looks fast.
    """
    path = _slot_path(sha)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            box = pickle.loads(zlib.decompress(f.read()))
    except Exception:
        return None
    if not isinstance(box, dict):
        return None
    if box.get("raw_sha256") != hashlib.sha256(raw).hexdigest():
        return None
    if box.get("raw_bytes") != len(raw):
        return None
    # A slot outlives the code that wrote it, and a model without spans loads
    # without complaint: `build_unit_index` then raises `KeyError: _start`
    # somewhere far from here.  The span check is the cheap shape assertion --
    # 136k dict lookups, under 0.1 s -- that turns a stale slot back into a miss.
    civs = box.get("civs")
    if not civs:
        return None
    for c in civs:
        if c.get("_start") is None or c.get("_end") is None:
            return None
        for u in c.get("units") or ():
            if u.get("_start") is None:
                return None
    try:
        return (box["stats"], box["civs"], box["civs_start"], box["gv"],
                box["tail"], "slot")
    except Exception:
        return None


def _slot_save(raw, sha, six):
    """Write one slot, atomically, and drop the oldest beyond ``_SLOTS_KEPT``."""
    try:
        d = _slot_dir()
        os.makedirs(d, exist_ok=True)
        payload = pickle.dumps(_slot_payload(raw, six), protocol=5)
        blob = zlib.compress(payload, 1)
        path = _slot_path(sha)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, path)
    except Exception:
        return
    try:
        names = [n for n in os.listdir(d) if n.endswith(".bin")]
        if len(names) <= _SLOTS_KEPT:
            return
        rows = sorted((os.path.getmtime(os.path.join(d, n)), n) for n in names)
        for _m, n in rows[:len(rows) - _SLOTS_KEPT]:
            if os.path.join(d, n) == _slot_path(sha):
                continue
            try:
                os.remove(os.path.join(d, n))
            except Exception:
                pass
    except Exception:
        pass


def forget_memo():
    """Drop the in-process memo.  For probes that measure cold cost."""
    _FRAME_MEMO.clear()


def _parse(raw):
    """``(stats, civs, civs_start, gv, tail, how)``, cheapest source first.

    Order: the in-process memo, the product's own single-slot cache, this
    module's multi-slot cache, then a real parse.  Every layer is keyed on the
    raw sha256, so a stale entry can only ever be a miss.
    """
    sha = hashlib.sha256(raw).hexdigest()
    hit = _FRAME_MEMO.get(sha)
    if hit is not None:
        return hit[0], hit[1], hit[2], hit[3], hit[4], "memo"
    six = PC.load(raw)
    if six is not None:
        _FRAME_MEMO[sha] = six[:5]
        return six
    six = _slot_load(raw, sha)
    if six is not None:
        _FRAME_MEMO[sha] = six[:5]
        return six
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    if p.r.pos != len(raw):
        raise UpgradeError("这份 .dat 解析到第 %d 字节就停了（一共 %d 字节），"
                           "结构对不上，不敢在它上面合并"
                           % (p.r.pos, len(raw)))
    civs, civs_start, gv, tail = L.locate(raw, p)
    six = (p.stats, civs, civs_start, gv, tail, "parsed")
    PC.save(raw, p.stats, civs, civs_start, gv, tail, "parsed")
    _slot_save(raw, sha, six)
    _FRAME_MEMO[sha] = six[:5]
    return six


def _civ_keys(civs):
    """Stable per-civilization keys: the name, or ``#index`` if it repeats.

    The name is what a report should print, and it is stable across versions;
    the index is what the format guarantees.  Using the name when it is unique
    and the index when it is not means a report never shows two rows that look
    identical while addressing different blocks.
    """
    names = [c.get("name") or "" for c in civs]
    seen = {}
    for c, n in zip(civs, names):
        seen[n] = seen.get(n, 0) + 1
    out = []
    for c, n in zip(civs, names):
        out.append(n if n and seen[n] == 1 else "#%d" % c["index"])
    return out


# ---------------------------------------------------------------------------
# the frame: where every record lives in one stream
# ---------------------------------------------------------------------------

class Frame(object):
    """One parsed stream, with every record family addressable by key.

    Built once per distinct stream.  The expensive part is ``_parse`` (about
    10 s cold on 93 MB, 1.6 s from the cache); everything in here is arithmetic
    over the spans ``locate`` already walked, so a frame costs ~0.1 s on top.
    """

    def __init__(self, raw, label="", spans_from=None):
        self.raw = raw
        self.label = label
        self.size = len(raw)
        self.sha = _sha(raw)
        self.ver = _head_ver(raw)
        if spans_from is not None:
            # Same length and same generation: `locate` walking the base walked
            # exactly these spans, because a record's position depends only on
            # the records before it, and those are byte-identical in length.
            self.stats = spans_from.stats
            self.civs = spans_from.civs
            self.civs_start = spans_from.civs_start
            self.gv = spans_from.gv
            self.tail = spans_from.tail
            self.how = "shared-with-%s" % (spans_from.label,)
        else:
            (self.stats, self.civs, self.civs_start, self.gv, self.tail,
             self.how) = _parse(raw)
        self.keys = _civ_keys(self.civs)
        self._unit_index = None
        self._unit_spans = None
        self._civ_by_key = None
        self._tech_spans = None
        self._tech_index = None
        self._fields_cache = {}
        self._table_cache = {}
        self._table_index = {}

    # -- units ------------------------------------------------------------
    def build_unit_index(self):
        if self._unit_index is not None:
            return self._unit_index
        by_key = {}
        spans = []
        for civ, cn in zip(self.civs, self.keys):
            for u in civ["units"]:
                by_key[(cn, u["id"])] = (u["_start"], u["_end"])
                spans.append((u["_start"], u["_end"], cn, u["id"]))
            by_key[(cn, None)] = (civ["_start"], civ["_end"])
        spans.sort()
        self._unit_index = by_key
        self._unit_spans = spans
        self._civ_by_key = dict(zip(self.keys, self.civs))
        return by_key

    def unit_span(self, civ_key, unit_id):
        self.build_unit_index()
        return self._unit_index.get((civ_key, unit_id))

    def civ_block(self, civ_key):
        self.build_unit_index()
        return self._unit_index.get((civ_key, None))

    def civ_of(self, civ_key):
        self.build_unit_index()
        return self._civ_by_key.get(civ_key)

    def unit_keys(self):
        self.build_unit_index()
        return set(k for k in self._unit_index if k[1] is not None)

    def find_unit_span_by_offset(self, off):
        """``(civ_key, unit_id, start, end)`` for the record covering ``off``."""
        self.build_unit_index()
        spans = self._unit_spans
        lo, hi = 0, len(spans)
        while lo < hi:
            mid = (lo + hi) // 2
            if spans[mid][0] <= off:
                lo = mid + 1
            else:
                hi = mid
        for i in (lo - 1, lo - 2):
            if 0 <= i < len(spans):
                s, e, cn, uid = spans[i]
                if s <= off < e:
                    return (cn, uid, s, e)
        return None

    # -- techs ------------------------------------------------------------
    def build_tech_spans(self):
        if self._tech_spans is not None:
            return self._tech_spans
        r = L.Orec(self.raw, self.tail, gv=self.gv)
        n = r.i16()
        spans = []
        for _i in range(n):
            s = r.o
            L.walk_tech(r)
            spans.append((s, r.o))
        self._tech_spans = spans
        return spans

    def tech_count(self):
        return len(self.build_tech_spans())

    def tech_index_of_offset(self, off):
        spans = self.build_tech_spans()
        lo, hi = 0, len(spans)
        while lo < hi:
            mid = (lo + hi) // 2
            if spans[mid][0] <= off:
                lo = mid + 1
            else:
                hi = mid
        for i in (lo - 1, lo - 2):
            if 0 <= i < len(spans):
                s, e = spans[i]
                if s <= off < e:
                    return i
        return None

    def tech_tail_end(self):
        spans = self.build_tech_spans()
        return spans[-1][1] if spans else self.tail + 2

    # -- generic tables ---------------------------------------------------
    def table_spans(self, table):
        if table in self._table_cache:
            return self._table_cache[table]
        recs, leftover = TB.scan(self.raw, table)
        if leftover:
            raise UpgradeError("「%s」这张表扫到最后一字节还剩 %d 字节没走完，"
                               "偏移不可信" % (table, leftover))
        self._table_cache[table] = recs
        return recs

    def table_key_of(self, table, rec, raw=None):
        """The stable key of one table record.

        Graphics are keyed by their own ``ID`` field, never by array position:
        measured on the shipped file, 19,861 of 20,883 positions differ from the
        id stored at that position, so a position is not an identity.

        ``raw`` defaults to this frame's own bytes, and a caller that has
        already spliced the stream MUST pass it: after the first table is
        rewritten, every offset in ``self.raw`` points at bytes that are no
        longer there, so a key read from it is silently some other record's
        id.  Measured on a real 114 MB mod: the graphic table's 8 rewritten
        records were keyed against a shifted buffer, none of the keys matched,
        and the rewrite quietly did nothing while the run still reported
        success.
        """
        if table == "effect":
            return ("index", rec["index"])
        if table == "task":
            # A task's own ID repeats inside every unit header (the shipped
            # file has 26 ids across 1,701 headers), so the id is a name
            # inside a header, not an identity.  Its position in its header
            # is: 2,315 of 2,329 keys match between the base and the mod.
            return ("task", rec.get("unit"), rec.get("task"))
        f = TB.fields_at(self.raw if raw is None else raw, self.gv, rec,
                         table=table)
        for name in ("ID", "Id", "id"):
            if name in f and f[name].get("value") is not None:
                return ("ID", f[name]["value"])
        return ("index", rec.get("index"))

    def table_index(self, table):
        if table in self._table_index:
            return self._table_index[table]
        idx = {}
        for rec in self.table_spans(table):
            idx[self.table_key_of(table, rec)] = rec
        self._table_index[table] = idx
        return idx

    def duplicate_keys(self, table):
        """Keys that more than one record claims.

        A key that two records share is not an identity, and aligning by it
        would silently pick one and lose the other.  Measured on a hand-built
        mod that appended two byte-identical sound records: the second copy
        collapsed onto the first one's ``ID``, the key sets came out equal, and
        the append was reported as "no change" -- the one failure mode this
        module exists to prevent.
        """
        seen, dup = set(), set()
        for rec in self.table_spans(table):
            key = self.table_key_of(table, rec)
            if key in seen:
                dup.add(key)
            seen.add(key)
        return dup

    def find_table_record_by_offset(self, table, off):
        recs = self.table_spans(table)
        lo, hi = 0, len(recs)
        while lo < hi:
            mid = (lo + hi) // 2
            if recs[mid]["start"] <= off:
                lo = mid + 1
            else:
                hi = mid
        for i in (lo - 1, lo - 2):
            if 0 <= i < len(recs):
                if recs[i]["start"] <= off < recs[i]["end"]:
                    return recs[i]
        return None

    # -- record fields ----------------------------------------------------
    def unit_fields(self, start, end):
        key = ("unit", start)
        if key in self._fields_cache:
            return self._fields_cache[key]
        f = UF.fields_at(self.raw, self.gv, start)
        out = _field_ranges(f, start, end)
        self._fields_cache[key] = out
        return out

    def tech_fields(self, index):
        key = ("tech", index)
        if key in self._fields_cache:
            return self._fields_cache[key]
        s, e = self.build_tech_spans()[index]
        f = TF.fields_at(self.raw, self.gv, s)
        out = _field_ranges(f, s, e)
        self._fields_cache[key] = out
        return out

    def table_fields(self, table, rec):
        key = (table, rec["start"])
        if key in self._fields_cache:
            return self._fields_cache[key]
        f = TB.fields_at(self.raw, self.gv, rec, table=table)
        out = _field_ranges(f, rec["start"], rec["end"])
        self._fields_cache[key] = out
        return out

    # -- civ header -------------------------------------------------------
    def civ_header_fields(self, civ_key):
        """Every scalar in a civ's header, including its flag array.

        Derived by arithmetic from ``civ["_start"]`` instead of a second walker:
        the layout is ``u8 player_type``, debug string, ``i16`` resource count,
        ``i16`` tech tree id, ``i16`` team bonus id, ``f32[count]`` resources,
        ``u8 icon_set``, ``i16 m``, ``i32[m]`` flags -- and ``locate`` already
        proved where the block starts and ends.  A second walker is a second
        place for the format to disagree with itself, so this one refuses
        (returns ``None``) the moment the arithmetic does not land exactly on
        ``civ["_end"]``.
        """
        block = self.civ_block(civ_key)
        if not block:
            return None
        s, e = block
        raw = self.raw
        out = []
        o = s
        out.append(("player_type", o, 1))
        o += 1
        marker = struct.unpack_from("<H", raw, o)[0]
        ln = struct.unpack_from("<H", raw, o + 2)[0]
        if marker != P.DEBUG_STRING_MARKER:
            return None
        out.append(("name", o, 4 + ln))
        o += 4 + ln
        n = struct.unpack_from("<h", raw, o)[0]
        out.append(("resource_count", o, 2))
        o += 2
        out.append(("tech_tree_id", o, 2))
        o += 2
        out.append(("team_bonus_id", o, 2))
        o += 2
        res_off = o
        for i in range(max(0, n)):
            out.append(("resources.%d" % i, res_off + 4 * i, 4))
        o = res_off + 4 * max(0, n)
        out.append(("icon_set", o, 1))
        o += 1
        m = struct.unpack_from("<h", raw, o)[0]
        out.append(("flag_count", o, 2))
        o += 2
        for uid in range(max(0, m)):
            out.append(("flag.%d" % uid, o + 4 * uid, 4))
        o += 4 * max(0, m)
        if o != e:
            return None
        return out


def _field_ranges(fields, rec_start, rec_end):
    """``[(offset, width, name)]`` in file order, strings sized by their gap."""
    offs = sorted((m["offset"], name, m.get("kind"))
                  for name, m in fields.items())
    out = []
    for i, (off, name, kind) in enumerate(offs):
        w = _KIND_W.get(kind)
        if w is None:
            nxt = offs[i + 1][0] if i + 1 < len(offs) else rec_end
            w = max(0, nxt - off)
        out.append((off, w, name))
    return out


def _slice_of(ranges, a, b):
    """Split the byte range ``[a, b)`` into field pieces.

    Each piece is ``(name, field_off, rel, width)``: ``field_off`` is where the
    field starts in the file, ``rel`` is where the differing bytes start inside
    that field.  Both are needed.  ``rel`` alone is not enough, because a
    difference rarely begins at byte 0 of a field -- an f32 whose low byte
    changed starts at byte 0, but one whose high byte changed starts at byte 3
    -- and adding ``rel`` to the start of the DIFF instead of the start of the
    FIELD reads the neighbour's bytes and calls it the author's edit.  That
    mistake is silent: the numbers look plausible, they are just somebody
    else's.  Measured on a real 115 MB mod: 34 of 500 sampled carries read back
    a value the author never wrote.
    """
    out = []
    for off, w, name in ranges:
        if w <= 0:
            continue
        lo = max(a, off)
        hi = min(b, off + w)
        if lo < hi:
            out.append((name, off, lo - off, hi - lo))
    return out


def _unclaimed(ranges, a, b):
    """``[(lo, hi)]`` inside ``[a, b)`` that no field range covers.

    The counterpart to :func:`_slice_of`: that one says what the author changed
    and this one says what nothing claims.  Both are needed because a table
    record is not guaranteed to be fully named.  A byte-diff region that no field
    covers used to be dropped without a note -- the author's edit was real, the
    bytes were there, and the report said there was nothing to port.  Reporting
    the gap turns a silent lie into an honest "this part I cannot carry".
    """
    holes = []
    cur = a
    for off, w, _name in ranges:
        if w <= 0 or off + w <= cur:
            continue
        if off >= b:
            break
        if off > cur:
            holes.append((cur, min(off, b)))
        cur = max(cur, off + w)
        if cur >= b:
            break
    if cur < b:
        holes.append((cur, b))
    return [(lo, hi) for lo, hi in holes if lo < hi]


# ---------------------------------------------------------------------------
# analysis: base vs mod -> symbolic plan
# ---------------------------------------------------------------------------

def _needs_structural(base, mod, regions=None):
    """Whether a byte diff is even meaningful between these two streams.

    A byte diff only means anything when the two files have the same shape.  Two
    kinds of change break that: a different length (something was spliced), and
    the same length with a different record SET (one record deleted and another
    of exactly the same width added -- the file length matches and every offset
    after the pair is wrong).  The second one is the dangerous case, because a
    naive diff would happily attribute the shifted bytes to innocent records, so
    it is checked explicitly rather than assumed away.

    The table half of that check is deferred: reading every table record's key
    costs 2.3 s on the shipped file, and a table can only be misattributed if a
    differing byte actually lands inside it.  When ``regions`` is given, only
    the tables those regions touch are keyed.
    """
    if len(base.raw) != len(mod.raw):
        return True
    if base.unit_keys() != mod.unit_keys():
        return True
    if base.tech_count() != mod.tech_count():
        return True
    for table in ("graphic", "effect"):
        if regions is not None and not _regions_touch_table(base, table,
                                                            regions):
            continue
        try:
            if set(base.table_index(table)) != set(mod.table_index(table)):
                return True
        except Exception:
            return True
    return False


def _regions_touch_table(frame, table, regions):
    """Whether any differing region could fall inside this table.

    Free where it matters: every table lives *below* the civ section, so a
    region at or above ``civs_start`` cannot touch one and needs no scan at all.
    Only when a region really does sit down there does this spend the walk --
    and even then the answer only matters for ``graphic`` and ``effect``, the
    two tables whose keys a naive diff could misattribute.
    """
    try:
        top = frame.civs_start
    except AttributeError:                          # pragma: no cover
        return True
    if top and not any(off < top for off, _n in regions):
        return False
    try:
        recs = frame.table_spans(table)
    except UpgradeError:
        return True
    if not recs:
        return False
    lo, hi = recs[0]["start"], recs[-1]["end"]
    for off, n in regions:
        if off < hi and off + n > lo:
            return True
    return False


def _cap_note(plan, limit):
    """Record "the check stopped counting" once for the whole plan.

    The cap belongs to the plan, not to a record, so every later record that
    hits it would append the identical sentence: a mod with 240k records
    produced 3,000+ copies and a 2.5 MB JSON report (measured on
    15373_Multiple Buffs Mod v1).  Callers still break their own loop; this
    just makes the sentence appear once.
    """
    if plan.get("capped"):
        return
    plan["capped"] = True
    plan["notes"].append(
        "改动太多，按当前上限只数到 %d 处，剩下的还没数（更新时会全部数完）"
        % limit)


def _plan(base, mod, limit=20000, alias=None, new=None, on_progress=None):
    """Every difference between ``base`` and ``mod``, expressed symbolically.

    ``on_progress(fraction)`` reports how far through the comparison this is,
    0..1.  It exists because the comparison -- not the parsing -- is where a big
    mod spends most of its check: measured on ``209785_Civilization Alliance``
    (2026-11-12), 23.5 s of a 37.5 s analysis sat between "the three files are
    parsed" and "the plan is ready", and a bar that holds still for two thirds
    of the wait is indistinguishable from a bar that has hung.
    """
    plan = {
        "edits": [],          # byte-range carries, addressed symbolically
        "replace": [],        # whole records whose LENGTH the author changed
        "add_unit": [],       # records the author added
        "del_unit": [],       # records the author deleted
        "add_tech": [],       # tech records appended by the author
        "del_tech": [],       # tech indices the author removed
        "unmapped": [],       # regions this module will not guess about
        "notes": [],
        "structural": False,
        "capped": False,      # stopped counting, not "cannot carry"
        "add_table": [],      # records the author appended to a flat table
        "del_table": [],      # records the author removed from a flat table
        "replace_table": [],  # flat-table records whose LENGTH the author changed
        "replace_tech": [],   # tech records whose LENGTH the author changed
    }
    def _emit(frac):
        if on_progress is None:
            return
        try:
            on_progress(max(0.0, min(1.0, frac)))
        except Exception:                # noqa: BLE001
            pass

    # The diff comes first and it is pure walk: two streams compared 64 KB at a
    # time has an honest fraction, so it owns the first 8% of the bar instead of
    # showing nothing until the plan is done.  Measured 5.4 s of a 25 s analysis
    # on `209785_Civilization Alliance` (2026-11-12).
    #
    # One diff, read twice: the region list costs 0.2 s and it is the evidence
    # both for "is this even a same-shape diff" and for what the author touched.
    regions = L.diff_regions(base.raw, mod.raw,
                             on_progress=lambda f: _emit(0.08 * (f or 0.0)))
    _emit(0.08)
    plan["structural"] = _needs_structural(base, mod, regions)
    if plan["structural"]:
        _plan_structural(base, mod, plan, limit, alias=alias, new=new,
                         on_progress=lambda f: _emit(0.08 + 0.92 * (f or 0.0)))
        _emit(1.0)
        return plan
    _last = [-1.0]
    for _i, (off, n) in enumerate(regions):
        _sub = round(min(1.0, (_i + 1) / max(1, len(regions))), 2)
        if _sub != _last[0]:
            _last[0] = _sub
            _emit(0.08 + 0.92 * _sub)
        if limit and len(plan["edits"]) >= limit:
            # A cap is "we stopped counting", NOT "these bytes cannot be
            # carried".  Reporting each remaining region as unmapped made a big
            # mod look like it had 962 unfixable problems when it had three --
            # measured on a real 115 MB third-party mod: 962 rows, every one of
            # them the same sentence about the cap, and the three real gaps
            # buried underneath.  The cap is a speed knob for the CHECK; the
            # APPLY runs uncapped.
            _cap_note(plan, limit)
            break
        _plan_region(base, mod, off, n, plan)
    return plan


def _plan_region(base, mod, off, n, plan):
    """Attribute one differing byte range to the record family that owns it."""
    hit = base.find_unit_span_by_offset(off)
    if hit:
        cn, uid, s, e = hit
        _plan_unit_bytes(base, mod, cn, uid, off, n, plan,
                         base_start=s, mod_start=s)
        return
    cn = _civ_covering(base, off)
    if cn is not None:
        hdr = base.civ_header_fields(cn)
        pieces = _slice_of(hdr, off, off + n) if hdr else []
        if pieces:
            for name, foff, rel, w in pieces:
                plan["edits"].append({
                    "space": "civ", "civ": cn, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[foff + rel:foff + rel + w],
                    "mod": mod.raw[foff + rel:foff + rel + w],
                })
            return
        plan["unmapped"].append({
            "off": off, "len": n, "space": "civ", "civ": cn,
            "why": "落在文明 %s 的头部字段缝隙里（布局说法不一致）" % cn})
        return
    ti = base.tech_index_of_offset(off)
    if ti is not None:
        pieces = _slice_of(base.tech_fields(ti), off, off + n)
        if pieces:
            for name, foff, rel, w in pieces:
                plan["edits"].append({
                    "space": "tech", "index": ti, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[foff + rel:foff + rel + w],
                    "mod": mod.raw[foff + rel:foff + rel + w],
                })
            return
        plan["unmapped"].append({
            "off": off, "len": n, "space": "tech", "index": ti,
            "why": "落在第 %d 条科技的字段缝隙里" % ti})
        return
    for table in _TABLES:
        try:
            rec = base.find_table_record_by_offset(table, off)
        except UpgradeError:
            continue
        if rec is None:
            continue
        pieces = _slice_of(base.table_fields(table, rec), off, off + n)
        key = base.table_key_of(table, rec)
        if not pieces:
            plan["unmapped"].append({
                "off": off, "len": n, "space": table, "key": list(key),
                "why": "落在「%s」这条记录的字段缝隙里" % table})
            return
        for name, foff, rel, w in pieces:
            plan["edits"].append({
                "space": table, "key": key, "field": name,
                "rel": rel, "width": w,
                "base": base.raw[foff + rel:foff + rel + w],
                "mod": mod.raw[foff + rel:foff + rel + w],
            })
        return
    # The seven counters come BEFORE the tree and used to be reported as part of
    # it -- "the tech tree, this module has no semantics for it" about a 4-byte
    # integer at a fixed offset.  They are now carried like any other field.
    tail_at = base.tech_tail_end()
    tail_w = 4 * len(_TAIL_SCALARS)
    if tail_at <= off < tail_at + tail_w:
        for i in range(len(_TAIL_SCALARS)):
            foff = tail_at + 4 * i
            lo, hi = max(off, foff), min(off + n, foff + 4)
            if lo >= hi:
                continue
            plan["edits"].append({
                "space": "tail", "key": ("index", i),
                "field": _TAIL_SCALARS[i], "rel": lo - foff, "width": hi - lo,
                "base": base.raw[lo:hi], "mod": mod.raw[lo:hi],
            })
        return
    if off >= base.tech_tail_end():
        plan["unmapped"].append({
            "off": off, "len": n, "space": "techtree",
            "why": "这一处在科技树（TechTree）里：%d 条连线按编号对齐会撞车"
                   "（编号在四个家族之间重复），所以这一层不搬。" % n})
        return
    plan["unmapped"].append({
        "off": off, "len": n, "space": "unknown",
        "why": "这一处不属于任何已知记录（不是单位、文明头、科技、效果或表记录）"})


def _plan_tail_tables(base, mod, plan):
    """Carry the seven counters, and say honestly what the tech tree is."""

    # The seven i32 counters sit between the last technology and the tree, at a
    # fixed offset with a fixed width, so they are the easiest thing in the file
    # to carry -- and they were not carried at all: a change there fell into the
    # "this is inside the tech tree, this module has no semantics for it" bucket,
    # which is a false statement about the file.  Measured by hand-editing
    # `TimeSlice` on the shipped data: the plan said `space: tech_tree`.
    width = 4 * len(_TAIL_SCALARS)
    # `frame.tail` is where the TECH SECTION begins (its header count), not where
    # the counters begin: the counters start after the last tech record, which is
    # what `tech_tail_end()` answers.  Reading them at `tail` would have been the
    # same class of mistake this module exists to avoid -- a plausible address
    # holding a neighbour's bytes.
    b_at, m_at = base.tech_tail_end(), mod.tech_tail_end()
    if b_at + width <= base.size and m_at + width <= mod.size:
        for i in range(len(_TAIL_SCALARS)):
            b = base.raw[b_at + 4 * i:b_at + 4 * i + 4]
            m = mod.raw[m_at + 4 * i:m_at + 4 * i + 4]
            if b == m:
                continue
            plan["edits"].append({
                "space": "tail", "key": ("index", i),
                "field": _TAIL_SCALARS[i], "rel": 0, "width": 4,
                "base": b, "mod": m,
            })

    # The tree itself: 475-550 connections in four families.  Its records are
    # keyed by their own ID, and that id REPEATS across families (measured 53
    # duplicates on the shipped 8.9 data), so aligning by it would silently pick
    # one of each pair.  Saying so is the honest answer, and it is a different
    # sentence from "this module has no semantics" -- which was also false.
    if base.size != mod.size:
        return
    # The screen: the tree starts right after the counters, so comparing the first
    # 64 KiB below the tail answers "did the author touch the tree" in one slice --
    # and answers "no" for the overwhelming majority of mods, at which point the
    # 13.7 s walk would only be able to say what the bytes already said.
    head_b = base.raw[b_at + width:b_at + width + _TAIL_SCREEN]
    head_m = mod.raw[m_at + width:m_at + width + _TAIL_SCREEN]
    if head_b == head_m:
        return
    try:
        recs_b = base.table_spans("techtree")
        recs_m = mod.table_spans("techtree")
    except Exception:
        return
    changed = [r for r, s in zip(recs_b, recs_m)
               if base.raw[r["start"]:r["end"]] != mod.raw[s["start"]:s["end"]]]
    added = len(recs_m) - len(recs_b)
    if not changed and not added:
        return
    names = {"age": "时代", "building": "建筑", "unit": "单位",
             "research": "科技"}
    first = (changed or recs_m[len(recs_b):] or recs_b)[0]
    extra = ""
    if added > 0:
        extra = "，另外多了 %d 条" % added
    elif added < 0:
        extra = "，另外少了 %d 条" % (-added)
    plan["unmapped"].append({
        "space": "techtree", "key": [first.get("kind"), first.get("id")],
        "why": "作者动了科技树：%d 条连线改过%s（第一条是%s %s，位置 %d）。"
               "连线的编号在四个家族之间会重复（这份数据里有 %d 个编号被两条"
               "连线同时用着），按编号对齐会静默丢掉其中一条，所以这一层不搬，"
               "也不猜。"
               % (len(changed), extra, names.get(first.get("kind"), "连线"),
                  first.get("id"), first["start"], len(base.duplicate_keys("techtree"))),
    })


def _civ_covering(frame, off):
    for civ, cn in zip(frame.civs, frame.keys):
        if civ["_start"] <= off < civ["_end"]:
            return cn
    return None


def _plan_unit_bytes(base, mod, cn, uid, off, n, plan, base_start, mod_start,
                     bspan=None, mspan=None):
    """Express one differing range of a unit record as field carries.

    ``cn`` is the civilization name the TARGET file uses, because that is what
    the resulting edit has to resolve against.  It is not necessarily the name
    either source file uses: the mod may say `Ethopians` where the target says
    `Ethiopians` (see `_civ_alias`), so a caller that already holds the two
    spans passes them in rather than having them looked up by a name one of the
    frames does not have.
    """
    if bspan is None:
        bspan = base.unit_span(cn, uid)
    if mspan is None:
        mspan = mod.unit_span(cn, uid)
    if bspan is None or mspan is None:
        plan["unmapped"].append({
            "off": off, "len": n, "space": "unit", "civ": cn, "unit": uid,
            "why": "这条单位记录只在一份文件里有，不能按字段搬"})
        return
    pieces = _slice_of(base.unit_fields(bspan[0], bspan[1]), off, off + n)
    if not pieces:
        plan["unmapped"].append({
            "off": off, "len": n, "space": "unit", "civ": cn, "unit": uid,
            "why": "落在单位 %d（%s）的字段缝隙里" % (uid, cn)})
        return
    shift = mspan[0] - bspan[0]
    for name, foff, rel, w in pieces:
        a = foff + rel
        plan["edits"].append({
            "space": "unit", "civ": cn, "unit": uid, "field": name,
            "rel": rel, "width": w,
            "base": base.raw[a:a + w],
            "mod": mod.raw[a + shift:a + shift + w],
        })


def _unit_names(frame, start, end):
    """The named-field list of one unit record, or ``None`` if it will not walk.

    Used as an identity test, not as data: two records of the same width can
    still lay out differently when a run-length array's count moved, and a
    byte-level diff across that difference reads values out of the wrong
    offsets.  ``None`` on failure makes the caller treat the record as
    unknown and carry it whole, which is always safe.
    """
    try:
        return tuple(name for _o, _w, name in frame.unit_fields(start, end))
    except Exception:
        return None


def _table_same(frame_a, frame_b, table):
    """True when two frames hold the SAME bytes for one whole table."""
    a = frame_a.table_spans(table)
    b = frame_b.table_spans(table)
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if (x["end"] - x["start"]) != (y["end"] - y["start"]):
            return False
        if frame_a.raw[x["start"]:x["end"]] != frame_b.raw[y["start"]:y["end"]]:
            return False
    return True


def _plan_carry_table(base, mod, new, table, plan):
    """Carry a table whose numbers this module can name but cannot re-serialise.

    ``task`` and ``restriction`` did not fit either camp this module had.  They
    are not flat -- a flat table is a count followed by records and nothing
    else, while these two sit behind section structure (``7 UnitHeaders`` holds
    a header array whose entries carry their own task counts; the restriction
    block sits behind two counts and two pointer arrays) that is not rewritten
    wholesale here.  They are also not unaddressable: every number inside them
    has a name that survives a rebuild.

    Measured on ``15373_Multiple Buffs Mod v1``: task records are 69 bytes in the
    base, the mod and the target with identical field names, and 2,315 of 2,329
    keys are shared; restriction records differ only in how many terrain slots
    they cover (2,620 / 2,940 / 2,680 bytes = 20 bytes per ``terrains_used1``
    slot) while all three name their fields ``Mult.N`` / ``Pass.N.*`` by slot.
    So the honest operation is per field: compare the author's value with the
    base's and write the author's bytes into the TARGET's field of that name.
    That is exactly what ``plan['edits']`` already means, and ``_apply_edits``
    resolves it against the target frame, so a width change between generations
    costs nothing.

    What cannot be carried is stated, not guessed:

    * a task on a header the target does not have -- the mod numbers new units'
      tasks past ``unit_header_count`` (measured 1,868 such tasks on headers
      1,701..5,394) has no slot in the target file at all;
    * a restriction record past the target's record count covers a terrain the
      target does not have (the mod's ``terrains_used1`` is 147, the target's
      134);
    * a task the author DELETED is not carried, because a task is addressed by
      its position inside its header -- the same reason a deleted tech is not
      carried.

    Those are counted on the report as a sentence, not as an unmapped edit: an
    edit with nowhere to go is not this module failing to understand something.
    """
    try:
        bidx = base.table_index(table)
        midx = mod.table_index(table)
        nidx = new.table_index(table)
    except Exception as exc:
        plan["unmapped"].append({
            "space": table, "why": "「%s」表读不出来：%s" % (table, exc)})
        return

    if table == "task":
        room = int((new.stats or {}).get("unit_header_count") or 0)
        def fits(key):
            return room <= 0 or key[1] < room
    else:
        room = len(new.table_spans(table))
        def fits(key):
            return key[1] < room

    carried = 0
    shared = set(bidx) & set(midx)
    for key in sorted(shared, key=_key_order):
        nr = nidx.get(key)
        if nr is None:
            continue
        br, mr = bidx[key], midx[key]
        bf = TB.fields_at(base.raw, base.gv, br, table=table)
        mf = TB.fields_at(mod.raw, mod.gv, mr, table=table)
        nf = TB.fields_at(new.raw, new.gv, nr, table=table)
        for name in (set(bf) & set(mf) & set(nf)):
            w = TB.KINDS.get(nf[name].get("kind"))
            if not w:
                continue
            bo = bf[name]["offset"]
            mo = mf[name]["offset"]
            if base.raw[bo:bo + w] == mod.raw[mo:mo + w]:
                continue
            plan["edits"].append({
                "space": table, "key": key, "field": name,
                "rel": 0, "width": w,
                "base": bytes(base.raw[bo:bo + w]),
                "mod": bytes(mod.raw[mo:mo + w]),
            })
            carried += 1

    went, added, deleted = 0, 0, 0
    for key in sorted(set(midx) - set(bidx), key=_key_order):
        if not fits(key):
            went += 1
            continue
        if table == "task":
            mr = midx[key]
            plan.setdefault("task_add", []).append({
                "header": key[1],
                "bytes": bytes(mod.raw[mr["start"]:mr["end"]])})
            added += 1
        else:
            went += 1
    for key in set(bidx) - set(midx):
        if fits(key):
            deleted += 1

    plan.setdefault("carried", {})[table] = {
        "records": len(shared), "fields": carried,
        "added": added, "deleted": deleted, "gone": went}
    if went:
        plan["notes"].append(
            "「%s」表里有 %d 条记录在这份新数据里没有位置：模组的表比目标文件"
            "多出来的那一截（任务挂在目标文件没有的单位头上、通行表覆盖的地形"
            "比这一代多），搬过去也没有地方放，所以没有搬" % (table, went))
    if added:
        plan["notes"].append(
            "「%s」表里作者多的 %d 条记录，目标文件有它们的位置，按整条追加"
            % (table, added))
    if deleted:
        plan["notes"].append(
            "作者从「%s」表里删了 %d 条记录：这条表的记录按位置编号，删掉哪一条"
            "没有可证的答案，所以这一层按目标文件自己的保留" % (table, deleted))
    if carried:
        plan["notes"].append(
            "「%s」表按字段名搬了 %d 处（记录长度和这一代不同，位置不能对，"
            "名字可以）" % (table, carried))


def _apply_task_add(target, plan, raw):
    """Append the author's extra tasks to their headers, in one splice.

    A header is ``u8 exists`` followed, when present, by ``i16 count`` and that
    many 69-byte tasks.  Appending to a header therefore only moves the bytes
    after it, and the whole ``7 UnitHeaders`` section can be laid out again from
    its pieces -- the same one-pass rebuild the flat tables use, and the reason
    this is one splice instead of one per record.
    """
    adds = plan.get("task_add") or []
    done = {"added": 0, "rules": []}
    if not adds:
        return raw, done, 0
    by_header = {}
    for row in adds:
        by_header.setdefault(int(row["header"]), []).append(bytes(row["bytes"]))
    try:
        bounds, _stats = TB.stage_offsets(raw, "7 UnitHeaders")
        start, end = bounds["7 UnitHeaders"]
    except Exception:
        return raw, done, 0
    gv = P.GV_C32 if target.gv is None else target.gv
    r = P.Reader(raw, gv)
    r.pos = start
    headers = r.i32()
    parts = [struct.pack("<i", headers)]
    extra = 0
    for h in range(headers):
        if not r.u8():
            parts.append(b"\x00")
            continue
        n = r.i16()
        body_start = r.pos
        r.pos = body_start + 69 * n
        body = bytes(raw[body_start:r.pos])
        more = by_header.get(h) or []
        if more:
            body += b"".join(more)
            n += len(more)
            extra += len(more)
        parts.append(b"\x01" + struct.pack("<h", n) + body)
    # A header index the target does not have has nowhere to go: those rows were
    # counted as gone by `_plan_carry_table` and never enter `by_header`.
    parts.append(bytes(raw[r.pos:end]))
    blob = b"".join(parts)
    if blob == bytes(raw[start:end]):
        return raw, done, 0
    grew = len(blob) - (end - start)
    out = bytes(raw[:start]) + blob + bytes(raw[end:])
    done["added"] = extra
    done["rules"].append((start, grew))
    return out, done, grew

def _plan_structural(base, mod, plan, limit, alias=None, new=None,
                     on_progress=None):
    """The author changed the file's SHAPE: records were added or removed.

    Here a byte offset means nothing across the two files, so every difference
    has to come from comparing record SETS.  Nothing is inferred from a shifted
    offset, which is the only honest way to handle a stream whose geometry the
    author moved.

    ``on_progress(fraction)`` walks 0..1 across the three set comparisons in
    the order they run.  The weights are the shapes of the work, not measured
    seconds: the shared-record loop is the one that reads two field-name lists
    per record and it dominates (measured 23 s of 37.5 s total on a 96 MB mod),
    the tech loop is a file-order walk, and the table loop is five sections.
    """
    def _say(frac):
        if on_progress is None:
            return
        try:
            on_progress(max(0.0, min(1.0, frac)))
        except Exception:                # noqa: BLE001
            pass

    alias = alias or {}
    # `new` is shadowed further down by the set of added table keys, which is
    # older than this parameter; keep the frame under a name of its own.
    new_frame = new
    bkeys = base.unit_keys()
    mkeys = mod.unit_keys()
    # Work in the TARGET file's spelling of every civilization.  The mod says
    # `Ethopians` (what its base said) and the target says `Ethiopians`; the
    # records are addressed by (civilization, id), so unless both sides are
    # translated into one namespace every record of that civilization looks
    # added on one side and deleted on the other.  `alias` is built from
    # (tech_tree_id, team_bonus_id), the two numbers the game itself uses to
    # decide which civilization a player is -- see `_civ_alias`.
    morig = {}
    if alias:
        for _cn, _uid in mkeys:
            _t = alias.get(_cn, _cn)
            if _t != _cn:
                morig[(_t, _uid)] = _cn
        bkeys = set((alias.get(cn, cn), uid) for (cn, uid) in bkeys)
        mkeys = set((alias.get(cn, cn), uid) for (cn, uid) in mkeys)

    # A civilization that exists on ONE side only is not a pile of added or
    # removed records -- it is the same civilization under a different name, and
    # reading it record by record produces the worst possible pair of mistakes at
    # once: the records the author invented are "added" to a civ the new file
    # does not have (so they go nowhere), and the records the new file DOES have
    # are "removed" (so they get deleted).  Measured on
    # `15373_Multiple Buffs Mod v1`: it spells Ethiopian as "Ethopians", and the
    # merge deleted the official Ethiopians records while dropping all 4,168 of
    # the author's replacements on the floor.  The verify caught it, which is why
    # nothing was written -- but the report should say what happened, so this
    # refuses both sides by name instead.
    bcn = set(cn for cn, _u in bkeys)
    mcn = set(cn for cn, _u in mkeys)
    only_mod = mcn - bcn
    only_base = bcn - mcn
    # A civilization that only the mod has is normally a rename, and guessing
    # is worse than refusing.  But there is a second reading the file can
    # settle by itself: if the TARGET stream has that civilization, then the
    # base is simply older than the mod and predates it -- measured on
    # 310130_1233, built on the 60-civilization 8.9 and carrying the three the
    # current 8.9 added.  Those records are ordinary additions; refusing them
    # would refuse a mod for being newer than its base.
    newcn = set(c.get('name') for c in new.civs if c.get('name')) if new else set()
    adopt = set(cn for cn in only_mod if cn in newcn)
    if adopt:
        only_mod = only_mod - adopt
        plan['notes'].append(
            '模组里有 %d 个文明是基准数据还没有的（%s）：目标文件已经有它们，'
            '这些记录按新增搬运' % (len(adopt), '、'.join(sorted(adopt))))
    if only_mod or only_base:
        for cn in sorted(only_mod):
            n = len([1 for k in mkeys if k[0] == cn])
            plan["unmapped"].append({
                "space": "civ", "civ": cn,
                "why": "这个文明只出现在模组里（%d 条记录），官方数据里没有同名的"
                       "文明。作者大概是给它改了名字：改名字会让这个文明的每一条"
                       "记录都变成「新增」，而官方那一份变成「删除」，本模块不猜"
                       "这两者是不是同一个。" % n})
            plan["notes"].append(
                "模组里叫「%s」的文明在官方数据里不存在，可能是改过名" % cn)
        for cn in sorted(only_base):
            n = len([1 for k in bkeys if k[0] == cn])
            plan["unmapped"].append({
                "space": "civ", "civ": cn,
                "why": "这个文明只出现在官方数据里（%d 条记录），模组里没有同名"
                       "的文明。如果作者是给它改了名，那不是「删掉了这个文明」，"
                       "本模块不猜。" % n})
        skip_civs = only_mod | only_base
    else:
        skip_civs = set()

    bpos = dict(((alias.get(cn, cn), uid), (s, e))
                for (cn, uid), (s, e) in base.build_unit_index().items()
                if uid is not None)
    mpos = dict(((alias.get(cn, cn), uid), (s, e))
                for (cn, uid), (s, e) in mod.build_unit_index().items()
                if uid is not None)

    _say(0.02)
    for cn, uid in sorted(mkeys - bkeys):
        if cn in skip_civs:
            continue
        s, e = mpos[(cn, uid)]
        row = {"civ": cn, "unit": uid, "bytes": bytes(mod.raw[s:e]),
               "start": s, "end": e}
        if (cn, uid) in morig:
            row["was_civ"] = morig[(cn, uid)]
        plan["add_unit"].append(row)
    for cn, uid in sorted(bkeys - mkeys):
        if cn in skip_civs:
            continue
        plan["del_unit"].append({"civ": cn, "unit": uid})

    _say(0.10)

    # Records present in both: same width means in-place field edits, a
    # different width means the author rewrote the record whole (a rename, an
    # added train location) and only the whole blob can carry that.
    _both = sorted(bkeys & mkeys)
    _nboth = max(1, len(_both))
    _lastp = [-1.0]
    for _i, (cn, uid) in enumerate(_both):
        _p = round(0.10 + 0.55 * (_i + 1) / _nboth, 2)
        if _p != _lastp[0]:
            _lastp[0] = _p
            _say(_p)
        bs, be = bpos[(cn, uid)]
        ms, me = mpos[(cn, uid)]
        if base.raw[bs:be] == mod.raw[ms:me]:
            continue
        # Equal width is NOT equal layout.  A unit record holds two run-length
        # arrays (`Type50.Attacks`, `Type50.Armours`) whose counts the author
        # can change; moving one count up and the other down keeps the total
        # length identical while every byte after the first array slides.  A
        # byte diff then maps changes onto BASE's field offsets and reads the
        # author's value out of whatever now sits there -- measured on 297820:
        # 184 records per generation with a re-balanced pair, and the resulting
        # 'edits' wrote Armour class values into attack slots, which moved a
        # record end and made the file unwalkable past civ 20.  The field name
        # lists are the only thing that can tell the two apart, so compare them
        # and carry such a record whole.
        if be - bs != me - ms or _unit_names(base, bs, be) != _unit_names(mod, ms, me):
            row = {"civ": cn, "unit": uid,
                   "bytes": bytes(mod.raw[ms:me]),
                   "base_bytes": bytes(base.raw[bs:be]),
                   "start": ms, "end": me}
            if (cn, uid) in morig:
                row["was_civ"] = morig[(cn, uid)]
            plan["replace"].append(row)
            continue
        for roff, rn in L.diff_regions(base.raw[bs:be], mod.raw[ms:me]):
            if limit and len(plan["edits"]) >= limit:
                _cap_note(plan, limit)
                break
            _plan_unit_bytes(base, mod, cn, uid, bs + roff, rn, plan,
                             base_start=bs, mod_start=ms,
                             bspan=(bs, be), mspan=(ms, me))
        if plan["capped"]:
            # The cap is global, so without this every remaining record walks
            # its own diff and appends the same sentence again.
            break

    _say(0.65)

    btech = base.tech_count()
    mtech = mod.tech_count()
    if mtech > btech:
        spans = mod.build_tech_spans()
        for i in range(btech, mtech):
            s, e = spans[i]
            plan["add_tech"].append({"at": i, "bytes": bytes(mod.raw[s:e]),
                                     "start": s, "end": e})
    elif mtech < btech:
        plan["del_tech"].extend(range(mtech, btech))
    _bs_spans = base.build_tech_spans()
    _ms_spans = mod.build_tech_spans()
    _ntech = max(1, min(btech, mtech))
    _lastt = [-1.0]
    for i in range(min(btech, mtech)):
        _q = round(0.65 + 0.10 * (i + 1) / _ntech, 2)
        if _q != _lastt[0]:
            _lastt[0] = _q
            _say(_q)
        bs, be = _bs_spans[i]
        ms, me = _ms_spans[i]
        if base.raw[bs:be] == mod.raw[ms:me]:
            continue
        if be - bs != me - ms:
            # A tech record whose WIDTH changed is a whole-record rewrite, for
            # the same reason a unit record's is: the author added or removed a
            # ``debug_string`` byte, a research location or a resource cost.
            # Byte-diffing across two widths is the trap here -- the shifted
            # tail lines up with ``Name.len`` and ``Name``, so the planner
            # "finds" an author edit that writes a string's length word without
            # writing the same number of text bytes.  Measured on
            # ``15373_Multiple Buffs``: 506 of its 1510 shared techs differ in
            # width, and mapping those diffs onto fields produced 1,340 edits
            # against ``Name``/``Name.len`` and a file whose tech section could
            # no longer be walked at all.
            plan["replace_tech"].append({"index": i,
                                         "bytes": bytes(mod.raw[ms:me]),
                                         "start": ms, "end": me})
            continue
        ranges = base.tech_fields(i)
        for roff, rn in L.diff_regions(base.raw[bs:be], mod.raw[ms:me]):
            a = bs + roff
            for name, foff, rel, w in _slice_of(ranges, a, a + rn):
                plan["edits"].append({
                    "space": "tech", "index": i, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[foff + rel:foff + rel + w],
                    "mod": mod.raw[ms + (foff + rel - bs):
                                   ms + (foff + rel - bs) + w],
                })

    _say(0.75)

    # Build the five tables' indexes FIRST, one frame at a time, before any of
    # them is used.  Reading an index costs a full parse of the stream
    # (measured 3.9 s per frame on a 96 MB mod), and building them lazily inside
    # the comparison below meant 13.5 s of the bar sitting on one number --
    # measured 2026-11-12 by wall-clock marks rather than guessed.  Doing it here
    # is the same total work (the loop below needs every table anyway) with a
    # mark between each frame, so the number moves while the parsing happens.
    for _fi, _fr in enumerate((base, mod)):
        for _ti, table in enumerate(_TABLES):
            try:
                _fr.table_index(table)
            except Exception:                       # noqa: BLE001
                pass        # the loop below reports the same failure by name
            _say(0.75 + 0.08 * (_fi * len(_TABLES) + _ti + 1)
                 / max(1, 2 * len(_TABLES)))

    # Tables are compared by key, never by offset: their counts sit in front of
    # them, so one added record moves every later offset in the section.
    for _ti, table in enumerate(_TABLES):
        _say(0.83 + 0.17 * _ti / max(1, len(_TABLES)))
        _unnamed = {}
        try:
            bidx = base.table_index(table)
            midx = mod.table_index(table)
        except Exception as exc:                       # pragma: no cover
            plan["unmapped"].append({
                "space": table, "why": "「%s」表读不出来：%s" % (table, exc)})
            continue
        # Only the tables this module aligns by key need a unique key.  `task`
        # is keyed by its own ID *within* a unit header, so the shipped file
        # legitimately has 26 repeated ids across 1,701 headers; demanding
        # global uniqueness there would refuse a file that is perfectly normal.
        for frame, label in (((base, "基准数据"), (mod, "这个模组"))
                             if table in _TABLE_FLAT else ()):
            dup = frame.duplicate_keys(table)
            if dup:
                plan["unmapped"].append({
                    "space": table,
                    "why": "%s的「%s」表里有 %d 个编号被两条记录同时用（例如 %r），"
                           "编号不唯一就不是身份，按它对齐会静默丢掉其中一条"
                           % (label, table, len(dup), sorted(dup, key=_key_order)[0])})
                break
        else:
            dup = None
        if dup:
            continue
        gone = set(bidx) - set(midx)
        new = set(midx) - set(bidx)
        if gone or new:
            if table not in _TABLE_FLAT:
                # Two readings of "the key sets differ" mean there is nothing
                # to carry at all, and both are settled by the bytes rather
                # than by a guess:
                #
                #   the mod's copy equals the TARGET's copy -- the author's
                #   table already is what the new file has, so the difference
                #   against the BASE is the official patch, not the author's
                #   work.  Measured on 310130: restriction 53 records at 2,620
                #   bytes in the base, 54 at 2,680 in the mod, and those 54 are
                #   byte-identical to the target's 54.  Nothing to move.
                #
                #   the mod's copy equals the BASE's copy -- the author never
                #   touched this table, and whatever the new file did to it is
                #   the new file's business.  Carrying a table nobody edited
                #   would import an OLD generation's numbers over the new one.
                if new_frame is not None and _table_same(mod, new_frame, table):
                    plan["notes"].append(
                        '「%s」表在模组里和目标文件完全一致，这一层不用搬'
                        % table)
                    continue
                if _table_same(base, mod, table):
                    plan["notes"].append(
                        '作者没动过「%s」表，这一层按目标文件自己的'
                        % table)
                    continue
                if table in _TABLE_CARRY:
                    # `task` and `restriction` are addressed by keys this
                    # module can read, but their sections are not rebuilt
                    # here, so the difference is carried field by field onto
                    # the target's own record.  Reached only after both
                    # byte-equality readings above came back false: a table
                    # the author did not touch, or one that already matches
                    # the target, needs nothing carried onto it.  See
                    # `_plan_carry_table` for what cannot go across.
                    _plan_carry_table(base, mod, new_frame, table, plan)
                    continue
                # Say what the file shows, not what the code is afraid of.
                # The old sentence here was "the records are nested and
                # variable length", which is measurably false: a task record is
                # 69 bytes and a restriction record is 2680 bytes, one width
                # each in the shipped file, so "variable length" was never the
                # reason.  The real reasons are the two numbers below, and only
                # the file can supply them.
                # Count RECORDS, not keys.  `bidx` is keyed by the record's own
                # id, and on this table the id repeats across parents, so
                # ``len(bidx)`` reports 26 for a table that holds 2329 records.
                # Saying "26 条" about a 2329-record table is the same class of
                # mistake this whole module exists to avoid: a number that looks
                # authoritative and describes something else.
                b_recs = base.table_spans(table)
                m_recs = mod.table_spans(table)
                b_w = sorted(set(r["end"] - r["start"] for r in b_recs))
                m_w = sorted(set(r["end"] - r["start"] for r in m_recs))
                why = ("作者改了「%s」表：数据这边 %d 条记录（每条 %s 字节，"
                       "%d 个不同编号），模组那边 %d 条（每条 %s 字节，"
                       "%d 个不同编号）。"
                       % (table, len(b_recs), _fmt_widths(b_w), len(bidx),
                          len(m_recs), _fmt_widths(m_w), len(midx)))
                if table in _TABLE_REPLACE:
                    why += ("这张表按编号整条替换可以，但记录条数不一样，而它的"
                            "记录区后面紧跟本模块不重新序列化的块，多一条少一条"
                            "都说不清位置，所以这一层不动。")
                elif b_w != m_w:
                    why += ("记录长度都不一样，说明这两份文件不是同一套表结构，"
                            "按编号或按位置对齐都会张冠李戴，所以这一层不动。")
                else:
                    why += ("这条表的记录是挂在别的记录下面的（单位头 / 地形表），"
                            "而挂在哪一条下面，编号本身没说，"
                            "所以这一层不动。")
                plan["unmapped"].append({"space": table, "why": why})
                continue
            # A flat table is a count, then records, then nothing: the offset of
            # record k depends only on records 0..k-1, so an append at the end
            # moves nothing, and the whole section can be rebuilt in one splice.
            # Measured on a real mod: 5000 added graphics all sit in one
            # contiguous run at the table's tail (3,521,340..3,955,660), which is
            # what makes "append" the honest operation rather than a guess.
            for key in sorted(new, key=_key_order):
                rec = midx[key]
                plan["add_table"].append({
                    "table": table, "key": key,
                    "bytes": bytes(mod.raw[rec["start"]:rec["end"]])})
            for key in sorted(gone, key=_key_order):
                plan["del_table"].append({"table": table, "key": key})
        # The shared records of ONE table can be most of the remaining wait:
        # the graphic table holds ~21,000 of them and this loop reads a
        # field-name list per record (measured 13 s of the 14 s the tables
        # take).  Walking the table's own slice of the bar is what stops the
        # number from freezing on the biggest table in the file.
        _shared = sorted(set(bidx) & set(midx), key=_key_order)
        _nsh = max(1, len(_shared))
        _tbase = 0.83 + 0.17 * _ti / max(1, len(_TABLES))
        _tslice = 0.17 / max(1, len(_TABLES))
        _lastr = [-1.0]
        for _ki, key in enumerate(_shared):
            _r = round(_tbase + _tslice * (_ki + 1) / _nsh, 2)
            if _r != _lastr[0]:
                _lastr[0] = _r
                _say(_r)
            br, mr = bidx[key], midx[key]
            if br["end"] - br["start"] != mr["end"] - mr["start"]:
                # A flat-table record whose length changed is a whole-record
                # rewrite, exactly like a unit record whose length changed: the
                # author added or dropped an effect command (11 bytes each), an
                # extra sound file entry, or one more animation frame.
                #
                # A changed length used to be refused for `graphic`, on the
                # grounds that a record's delta/angle tail decides where every
                # later record starts, so re-cutting one would shift the rest.
                # That was true of the per-record splice this module used to do;
                # it is not true of the one-pass rebuild, which asks "what is the
                # ordered list of records now?" and lays the whole area out again
                # from the pieces.  Measured on two real 三国 mods: the refusal
                # was the ONLY thing standing between them and a clean merge --
                # 8 rows each, all of them one extra animation frame on graphic
                # ids 18004-18011, and nothing else.
                plan["replace_table"].append({
                    "table": table, "key": key,
                    "base": bytes(base.raw[br["start"]:br["end"]]),
                    "bytes": bytes(mod.raw[mr["start"]:mr["end"]]),
                })
                continue
            if (base.raw[br["start"]:br["end"]]
                    == mod.raw[mr["start"]:mr["end"]]):
                continue
            ranges = base.table_fields(table, br)
            # Collect this record's field edits first, because a record is
            # ported either field by field or as a whole, never half of each.
            _mine = []
            _hole = False
            for roff, rn in L.diff_regions(base.raw[br["start"]:br["end"]],
                                           mod.raw[mr["start"]:mr["end"]]):
                a = br["start"] + roff
                shift = mr["start"] - br["start"]
                for name, foff, rel, w in _slice_of(ranges, a, a + rn):
                    _mine.append({
                        "space": table, "key": key, "field": name,
                        "rel": rel, "width": w,
                        "base": base.raw[foff + rel:foff + rel + w],
                        "mod": mod.raw[foff + rel + shift:
                                       foff + rel + shift + w],
                    })
                if _unclaimed(ranges, a, a + rn):
                    _hole = True
            if _hole:
                # Part of what the author changed sits in bytes this record
                # gives no name to, so no field edit can express it.  A flat
                # table has an honest escape: copy the record whole, which is
                # the same answer already used when a record's length changed.
                #
                # The old code dropped those bytes without a note: `_slice_of`
                # came back empty, the `for` had nothing to append, and the
                # record read as "nothing to port" while the bytes sat there
                # changed.  Measured on 310130: 16 graphics lost their frame
                # edits that way, 408773 lost 18, and nothing in the report
                # mentioned it.
                #
                # A table that is not rebuilt in one splice (`terrain`) cannot
                # use that escape, and saying "carried" about a record nobody
                # carries is worse than refusing it.
                # ``_TABLE_REPLACE`` tables take the same escape: a record can
                # be copied whole there even though the section around it
                # cannot be rebuilt from pieces.  Measured on 167396: 15
                # terrain records changed 29 bytes that no field name covers.
                if table in _TABLE_FLAT or table in _TABLE_REPLACE:
                    plan["replace_table"].append({
                        "table": table, "key": key,
                        "base": bytes(base.raw[br["start"]:br["end"]]),
                        "bytes": bytes(mod.raw[mr["start"]:mr["end"]]),
                    })
                    _unnamed[table] = _unnamed.get(table, 0) + 1
                    continue
                plan["unmapped"].append({
                    "space": table, "key": list(key),
                    "why": "作者改了这一条记录里没有字段名的那几个字节，而「%s」"
                           "表不能整条重排，所以这一条搬不过去" % table,
                })
                continue
            plan["edits"].extend(_mine)
        if _unnamed:
            plan["notes"].append(
                "「%s」表里有 %d 条记录的改动落在没有字段名的字节上，这些记录整条"
                "照抄了：字段名没覆盖到那里，逐字段搬会漏掉作者的改动。"
                % (table, _unnamed[table]))

    # The two tables at the very end of the file.  Reaching them costs a walk over
    # the whole civ block, so `_plan_tail_tables` screens the bytes first and only
    # pays when something down there really differs.
    _plan_tail_tables(base, mod, plan)
    _say(1.0)


# ---------------------------------------------------------------------------
# applying onto the new stream
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# carrying records across a generation change
# ---------------------------------------------------------------------------

def _civ_ids(frame):
    """{civ name: (tech_tree_id, team_bonus_id)} for one frame.

    Two numbers the GAME uses to decide which civilization a player is, and the
    only stable name in the file: a civ's own name string is free text, and the
    resource array and flag count around it grow with every patch, so neither
    can identify anything across generations.  Measured 2026-11-11 on VER 7.8 ->
    8.9: all 45 shared civilizations carry byte-identical (tech_tree_id,
    team_bonus_id) pairs, and the one civilization that was renamed -- VER 7.8
    spells Ethiopia as `Ethopians`, 8.9 spells it `Ethiopians` -- kept (48, 49).
    """
    out = {}
    for civ in frame.civs:
        cn = civ.get('name')
        tt = civ.get('tech_tree_id')
        tb = civ.get('team_bonus_id')
        if not cn or tt is None or tb is None:
            continue
        try:
            out.setdefault(cn, (int(tt), int(tb)))
        except (TypeError, ValueError):
            continue
    return out


def _civ_alias(base_f, new_f):
    """{old civ name: the name the target file uses}, when the id pair agrees.

    A rename is not a defect and not a guess: a mod says `Ethopians` because
    that is what the file it was built on said, and the new official file says
    `Ethiopians` for the same civilization.  Without this, every field edit
    inside that civilization resolves to "the new version has no such field".
    Measured on 297820: 1,214 of those, every one a real edit on a civilization
    the file merely spells differently now.

    Only a UNIQUE id pair on both sides is accepted.  When two civilizations
    share a pair the file has no identity to offer, and none is invented here.
    """
    b = _civ_ids(base_f)
    n = _civ_ids(new_f)
    back = {}
    for cn, key in n.items():
        back.setdefault(key, []).append(cn)
    alias = {}
    for cn, key in b.items():
        if cn in n:
            continue
        if key[0] <= 0 and key[1] <= 0:
            # (0, 0) / (-1, -1) means "unset", not "this civilization":
            # several entries legitimately share it, and pairing on it would
            # join two unrelated civilizations.
            continue
        hit = back.get(key) or []
        if len(hit) == 1 and hit[0] not in b:
            alias[cn] = hit[0]
    return alias


def _apply_civ_alias(plan, alias):
    """Rewrite every record-addressed row onto the target's spelling."""
    if not alias:
        return 0
    moved = 0
    for bucket in ('add_unit', 'del_unit', 'replace'):
        for row in plan.get(bucket) or []:
            cn = row.get('civ')
            if cn in alias:
                row['civ'] = alias[cn]
                row['was_civ'] = cn
                moved += 1
    for e in plan.get('edits') or []:
        cn = e.get('civ')
        if cn in alias:
            e['civ'] = alias[cn]
            e['was_civ'] = cn
            moved += 1
    for t in ('add_tech', 'replace_tech'):
        for row in plan.get(t) or []:
            cn = row.get('civ')
            if cn in alias:
                row['civ'] = alias[cn]
                moved += 1
    return moved


def _alias_note(alias):
    """One sentence naming every civilization this run had to rename."""
    return '；'.join(
        '模组的「%s」和官方的「%s」是同一个文明（科技树编号与团队加成编号在两代'
        '之间一致），它的记录改到新名字下面搬运' % (old, new)
        for old, new in sorted(alias.items()))


def _port_plan(plan, mod_f, new_f, on_progress=None):
    '''Re-lay-out every record this plan carries, for the new generation.

    A generation change moves bytes; it does not move FIELDS.  portgen decodes
    a record at the mod's generation by field NAME and writes it back in the
    target generation's order, using the same field readers the parser is
    tested against.  Measured: 12,000 added records across three real
    third-party mods re-encoded and walked clean at the target generation with
    zero failures, and every record of four archived generations round-trips
    byte for byte at its own generation.

    Added records also land on ids the new official file already uses --
    measured 9,660 / 19,872 / 1,878 of them.  A refused id used to abort the
    whole merge.  Here the id is either dropped (an empty shell: no name, no
    hit points, no standing graphic, no train entry -- pure array padding, and
    5,980 / 19,872 / 1,878 of the collisions were exactly that, measured) or
    renumbered into the free range above the target's highest id, with every
    id-valued field inside the ported record rewritten to match, so a
    renumbered unit still trains what it used to train.

    ``on_progress(fraction)`` walks 0..1 across the re-encoding, which is the
    single most expensive stage of a cross-generation check (measured 7.2 s of
    25 s on `209785_Civilization Alliance`, 2026-11-12) and is otherwise one
    unbroken silence between 'the plan is ready' and 'the apply starts'.

    Returns a report; mutates the plan in place.
    '''
    def _emit(frac):
        if on_progress is None:
            return
        try:
            on_progress(max(0.0, min(1.0, frac)))
        except Exception:                # noqa: BLE001
            pass

    gv_from, gv_to = mod_f.gv, new_f.gv
    out = {'from': mod_f.ver, 'to': new_f.ver, 'units': 0, 'techs': 0,
           'tables': 0, 'renumbered': 0, 'dropped': 0, 'defaulted': 0,
           'filled': 0, 'refused': [], 'idmap': {}}
    if gv_from is None or gv_to is None:
        out['refused'].append({
            'why': '这一代文件头看不出记录格式（%s → %s），不能按字段重编码'
                   % (mod_f.ver, new_f.ver)})
        return out

    occupied = set(uid for (_cn, uid) in new_f.unit_keys())
    # The id space is global, not per civilization: two records that end up
    # with the same number ARE the same unit, whichever civ lists it.  A new
    # number therefore has to clear the official file's ids AND every id this
    # very batch is about to insert -- measured on 209785: handing out
    # top+1, top+2, ... while ignoring the batch created 19,872 pairs that put
    # two records on one number, and _verify caught 32 of them by bytes.
    batch = set(r['unit'] for r in plan['add_unit'])
    taken = occupied | batch
    top = max(taken) if taken else 0

    def _blank(row):
        '''An array-padding record: nothing a player could ever see.'''
        f = UF.fields_at(mod_f.raw, gv_from, row['start'])
        name = str((f.get('Name') or {}).get('value') or '').strip()
        hp = (f.get('HitPoints') or {}).get('value') or 0
        stand = (f.get('StandingGraphic.0') or {}).get('value') or 0
        trains = 0
        for k, m in f.items():
            if k.startswith('Creatable.TrainLocations') and m.get('value'):
                trains += 1
        return not name and not hp and not stand and not trains

    # The id pass reads every added record's fields to tell an empty shell from
    # a real unit, so it is not free either; it gets the first eighth of the
    # bar and the re-encoding gets the rest.
    _nadd = max(1, len(plan['add_unit']))
    _emit(0.0)
    idmap = {}
    kept = []
    for _ai, row in enumerate(plan['add_unit']):
        _emit(0.12 * (_ai + 1) / _nadd)
        uid = row['unit']
        clash = (uid in occupied
                 or new_f.unit_span(row['civ'], uid) is not None)
        if not clash:
            kept.append(row)
            continue
        if _blank(row):
            out['dropped'] += 1
            continue
        if uid not in idmap:
            top += 1
            while top in taken:
                top += 1
            if top > 32767:
                out['refused'].append({
                    'space': 'unit', 'civ': row['civ'], 'unit': uid,
                    'why': '编号空间用完了（新的编号已经排到 32767），这条记录塞不进新版本'})
                continue
            idmap[uid] = top
            taken.add(top)
        kept.append(row)
    plan['add_unit'] = kept
    out['renumbered'] = len(idmap)
    out['idmap'] = dict(idmap)

    def _encode(row, unit=True):
        if row.get('start') is None or row.get('end') is None:
            out['refused'].append({
                'space': 'unit' if unit else 'tech', 'civ': row.get('civ'),
                'unit': row.get('unit'), 'index': row.get('index'),
                'why': '这条记录没有留下它在模组里的位置，不能重编码'})
            return None
        try:
            if unit:
                blob, tape = PG.encode_unit(mod_f.raw, row['start'],
                                            row['end'], gv_from, gv_to, idmap)
            else:
                blob, tape = PG.encode_tech(mod_f.raw, row['start'],
                                            row['end'], gv_from, gv_to, idmap)
        except Exception as exc:
            out['refused'].append({
                'space': 'unit' if unit else 'tech', 'civ': row.get('civ'),
                'unit': row.get('unit'), 'index': row.get('index'),
                'why': '重编码这条记录时出错：%s' % exc})
            return None
        hard = [m for m in tape.missing
                if m.endswith('!range') or m.endswith('!truncated')]
        if hard:
            out['refused'].append({
                'space': 'unit' if unit else 'tech', 'civ': row.get('civ'),
                'unit': row.get('unit'), 'index': row.get('index'),
                'why': '这条记录里有 %d 个字段放不进新版本的宽度（%s）'
                       % (len(hard), '、'.join(sorted(set(hard))[:4]))})
            return None
        out['defaulted'] += len(tape.missing)
        # `missing` is a guess and `absent` is a measured default for a field the
        # source generation simply did not have.  Counted apart so a rebuild can
        # be told "we had to invent 70,996 cells" from "8.9 added 14 fields and
        # we wrote each one's official value".
        out['filled'] += len(tape.absent)
        return blob

    # Every record that has to be re-encoded, counted up front so the fraction
    # below is 'records done / records to do' rather than a guess.  49,336
    # records on 209785; a count over four lists costs nothing next to one
    # encode.
    _todo = (len(plan['add_unit']) + len(plan['replace'])
             + len(plan['add_tech']) + len(plan['replace_tech']))
    _done = [0]

    def _tick():
        _done[0] += 1
        if _todo:
            _emit(0.12 + 0.88 * _done[0] / _todo)

    _emit(0.12)
    for row in plan['add_unit']:
        blob = _encode(row, unit=True)
        _tick()
        if blob is None:
            continue
        old = row['unit']
        row['bytes'] = blob
        row['ported'] = True
        if old in idmap:
            row['unit'] = idmap[old]
            row['was'] = old
        out['units'] += 1
    for row in plan['replace']:
        blob = _encode(row, unit=True)
        _tick()
        if blob is None:
            continue
        row['bytes'] = blob
        row['ported'] = True
        out['units'] += 1

    for row in plan['add_tech']:
        blob = _encode(row, unit=False)
        _tick()
        if blob is None:
            continue
        row['bytes'] = blob
        row['ported'] = True
        out['techs'] += 1
    for row in plan['replace_tech']:
        blob = _encode(row, unit=False)
        _tick()
        if blob is None:
            continue
        row['bytes'] = blob
        row['ported'] = True
        out['techs'] += 1

    out['tables'] = (len(plan.get('add_table') or [])
                     + len(plan.get('replace_table') or []))

    if idmap:
        for e in plan['edits']:
            fld = e.get('field') or ''
            w = e.get('width') or 0
            if w not in (2, 4) or not PG.is_id_field(fld):
                continue
            try:
                old = struct.unpack('<h' if w == 2 else '<i', e['mod'])[0]
            except struct.error:
                continue
            new = idmap.get(old)
            if new is None:
                continue
            e['mod'] = struct.pack('<h' if w == 2 else '<i', new)
            e['remapped'] = new
    return out

def port_refused(rep):
    '''The port's own refusals, which are about records, not about fields.'''
    return list((rep.get("port") or {}).get("refused") or [])


def _record_name(raw, gv, start):
    """The Name field of the unit record at start, stripped."""
    try:
        f = UF.fields_at(raw, gv, start)
    except Exception:
        return None
    return str((f.get("Name") or {}).get("value") or "").strip()


def _blob_name(blob, gv):
    """The Name field of a unit record held as a standalone blob."""
    try:
        r = UF.Rec(blob, gv)
        UF.read_unit_fields(r)
    except Exception:
        return None
    for name, _off, _kind, value in r.fields:
        if name == "Name":
            return str(value or "").strip()
    return None


def _adopt_clashes(plan, base_f, mod_f, new_f):
    """Records the author wrote on an id the target file already uses.

    A mod built on an older build of the SAME generation breaks the added/
    replaced split inside _plan: the target has since grown whole
    civilizations, so every record the author copied into those civilizations
    arrives as an addition on an id the target already holds.  _rebuild_civ
    refuses those -- it cannot insert a second record under one id -- and that
    refusal was silent data loss, not a correct refusal: measured on 310130,
    8,431 clashes, of which 493 carried real author changes (TrainSound,
    Bird.MoveSound, ResourceStorages.0.Amount, HitPoints, CollisionSize).

    The file settles which reading is right, so this asks it instead of
    guessing:

    * the target's bytes for that id are already exactly the author's -> there
      is nothing to write, drop the row;
    * same NAME -> the same unit, and the author's version belongs in that
      slot, so the row becomes a whole-record replacement (which the rebuild
      already does, with no id conflict);
    * a different name -> two unrelated units contesting one id, which is not
      this module's guess to make: the row stays an addition and the rebuild
      refuses it exactly as before.

    Runs after _port_plan so the bytes it moves are already in the target's
    layout.  Returns a report, or None when there was nothing to look at.
    """
    adds = plan.get("add_unit") or []
    if not adds:
        return None
    gv = new_f.gv
    keep = []
    out = {"clashes": 0, "adopted": 0, "same_bytes": 0, "contested": 0}
    for row in adds:
        uid = row["unit"]
        span = new_f.unit_span(row["civ"], uid)
        if span is None:
            keep.append(row)
            continue
        out["clashes"] += 1
        official = bytes(new_f.raw[span[0]:span[1]])
        blob = row.get("bytes")
        if blob is None:
            keep.append(row)
            continue
        if official == blob:
            out["same_bytes"] += 1
            continue
        if _record_name(new_f.raw, gv, span[0]) == _blob_name(blob, gv):
            out["adopted"] += 1
            plan.setdefault("replace", []).append({
                "civ": row["civ"], "unit": uid, "bytes": blob,
                "base_bytes": official,
                "start": row.get("start"), "end": row.get("end"),
                "adopted": True,
                "was_civ": row.get("was_civ")})
            continue
        out["contested"] += 1
        keep.append(row)
    plan["add_unit"] = keep
    if out["adopted"] or out["same_bytes"]:
        plan.setdefault("notes", []).append(
            "有 %d 条记录落在了目标文件已经用着的编号上：其中 %d 条同名同号，"
            "已按整条替换写进原槽（作者的改动不会丢）；%d 条与目标本来就"
            "一字不差，不必再写。"
            % (out["clashes"], out["adopted"], out["same_bytes"]))
    return out


# ---------------------------------------------------------------------------
# moving the author's techs off slots the target has since reused
# ---------------------------------------------------------------------------

def _tech_name(raw, gv, start):
    """The name the game shows for the tech record at start, or a blank.

    A technology has no id field -- its position IS its identity -- so the only
    question available is "is this still the same technology?", and the name is
    the answer.  The unit helpers (_record_name, _blob_name) decode with
    unitfields and return garbage for a tech record; the tech layout lives in
    techfields.
    """
    try:
        f = TF.fields_at(raw, gv, start)
    except Exception:                    # noqa: BLE001
        return ""
    v = (f.get("Name") or {}).get("value")
    return v if isinstance(v, str) else ""


def _slot_reused(base_name, mod_name, now_name):
    """True when the author wrote a tech where the official file now keeps another.

    Three names, one record: what the base called this position, what the
    author called it, what the target calls it.  Only the case where all
    three disagree is a collision -- every other combination has an in-place
    answer:

      * base == mod: the author never touched the record, so there is nothing
        to carry and the official record stands.
      * mod == now: both sides ended up calling the slot the same thing (a
        plain rename by the official file, or a placeholder it also left
        empty), so writing the author`s fields there writes his tech.
      * now == base: the official file still calls it what it always did, so
        the author`s rename is the only change and it belongs there.
      * any name blank: a blank name is a placeholder, not an identity, and
        two blanks say nothing about each other.

    Measured on 314918 against VER 7.8 -> 8.9: positions 18, 78, 79 and 121
    went base `New Research` -> mod `Fabric Armor` / `Economic Development` /
    `Raiding Military Development` / `Trade Alliance`, while 8.9 filled those
    same slots with `[SCEN] Move Huskarl`, `[FTT] Enable Regionals`,
    `Disable Regionals` and `[FTT] Adjust Regionals Positions`.
    """
    bn = (base_name or "").strip()
    mn = (mod_name or "").strip()
    nn = (now_name or "").strip()
    if not bn or not mn or not nn:
        return False
    return mn != bn and mn != nn and nn != bn

def _relocate_techs(plan, base_f, mod_f, new_f):
    """Move author techs out of slots the target has since handed to a new tech.

    THE FAULT
    ---------
    A tech record carries no id, so every carry path in this module addresses
    technologies by POSITION.  That is safe while the two files agree on what
    sits at each position, and it stops being safe the moment the official
    file fills a former placeholder slot with a real technology.  Measured on
    314918_New Civil Great Britain: 8.9 turned VER 7.8 placeholders at
    18/78/79/121 into [SCEN] Move Huskarl, [FTT] Enable Regionals,
    Disable Regionals and [FTT] Adjust Regionals Positions, while the author
    had built Fabric Armor, Economic Development, Raiding Military Development
    and Trade Alliance in those same slots.  Writing the author record over
    position 78 does not carry the edit -- it deletes an official technology,
    and the installed file showed exactly that: three of the new official
    [FTT] techs were gone.

    Whole-record replacement is no answer either: it still lands on position
    78, so the official tech dies either way.

    WHAT THIS DOES
    --------------
    For each position where BOTH sides changed identity -- the author renamed
    the slot away from its base name, and the target renamed it too, to
    something else again -- drop the field edits and the whole-record row that
    addressed that position and append the author record after the target
    array instead.  The official technology keeps its slot; the author keeps
    its bytes.  _repair_tech_refs then repoints every RequiredTechs that named
    the old position.

    The three-name test is deliberately narrow.  mod == base means the author
    never touched the record (nothing to carry); mod == new means both sides
    agree on what the slot is (a plain rename, or a placeholder the official
    file also left empty) and an in-place write is right.
    """
    bspans = base_f.build_tech_spans()
    mspans = mod_f.build_tech_spans()
    nspans = new_f.build_tech_spans()
    hits = {}
    for i in range(min(len(bspans), len(mspans), len(nspans))):
        bs, be = bspans[i]
        ms, me = mspans[i]
        if base_f.raw[bs:be] == mod_f.raw[ms:me]:
            continue
        bn = _tech_name(base_f.raw, base_f.gv, bs)
        mn = _tech_name(mod_f.raw, mod_f.gv, ms)
        nn = _tech_name(new_f.raw, new_f.gv, nspans[i][0])
        if not _slot_reused(bn, mn, nn):
            continue
        hits[i] = (bn, mn, nn)

    out = {"moved": [], "map": {}, "count": 0}

    # SECOND KIND OF REUSE, and the commoner one: the author APPENDED techs of
    # his own (314918: 24 of them, at 1268..1291 of his 1,292-record array),
    # and the target array has since grown past those numbers with real
    # technologies of its own.  _apply_records appends every add_tech row at
    # count+k, so the author record does not live at 1277 any more either --
    # the official tech does.  Every reference that still says 1277 has to be
    # repointed, and no EffectID may be written into position 1277.
    ncount = new_f.tech_count()
    for k, row in enumerate(plan.get("add_tech") or []):
        at = row.get("at")
        if isinstance(at, int) and 0 <= at < ncount:
            out["map"][at] = ncount + k

    if not hits and not out["map"]:
        return out

    # The author bytes are already on their way in as field edits or as one
    # whole-record row; both address the OLD position, so both must go before
    # the record is re-appended at the tail.
    plan["edits"] = [e for e in plan["edits"]
                     if not (e.get("space") == "tech"
                             and e.get("index") in hits)]
    plan["replace_tech"] = [r for r in (plan.get("replace_tech") or [])
                            if r.get("index") not in hits]

    at0 = new_f.tech_count() + len(plan["add_tech"])
    for j, i in enumerate(sorted(hits)):
        ms, me = mspans[i]
        plan["add_tech"].append({
            "at": i, "bytes": bytes(mod_f.raw[ms:me]),
            "start": ms, "end": me, "relocated": True})
        bn, mn, nn = hits[i]
        out["moved"].append({"index": i, "new_index": at0 + j,
                             "base_name": bn, "name": mn, "now_name": nn})
        out["map"][i] = at0 + j
    out["count"] = len(out["moved"])
    if out["moved"]:
        # Only when something actually moved.  A plan that merely appended
        # author technologies -- out["map"] non-empty, hits empty -- used to
        # print this sentence with two empty parentheses: "0 technologies sit
        # in slots the official file reused (): ... (record )".  A report that
        # announces an event and leaves the list of what happened blank
        # teaches the reader to distrust every other line in it.
        plan["notes"].append(
            "有 %d 条科技写在了官方新版本已经另作他用的槽位上（%s）：那些位置现在"
            "是别人的科技，所以作者的那几条整条搬到了科技表末尾（第 %s 条），"
            "官方新增的科技一条都没被覆盖。"
            % (out["count"],
               "、".join("%d「%s」" % (m["index"], m["name"]) for m in out["moved"]),
               "、".join(str(m["new_index"]) for m in out["moved"])))
    return out


def _patch_refs(blob, gv, mp):
    """Repoint every RequiredTechs.N inside blob that names a moved slot."""
    try:
        f = TF.fields_at(blob, gv, 0)
    except Exception:                    # noqa: BLE001
        return blob, 0
    out = bytearray(blob)
    n = 0
    for name, m in f.items():
        if not name.startswith("RequiredTechs.") or m.get("kind") != "i16":
            continue
        v = m.get("value")
        new = mp.get(v) if isinstance(v, int) else None
        if new is None:
            continue
        off = m["offset"]
        out[off:off + 2] = struct.pack("<h", new)
        n += 1
    return bytes(out), n


def _repair_tech_refs(plan, mod_f, new_f, reloc):
    """Follow a relocated tech: every prerequisite that named it names the copy.

    A technology is reached through RequiredTechs, so moving one without moving
    its references leaves the author tree pointing at a slot that now holds
    somebody else tech -- measured on 314918: 25 references, all
    RequiredTechs.1, from the author own additions (1268..1285, the Trade
    Routes..Blanco-Raider block) and from techs he edited (133/136/139/141 ->
    78, 168/169/170 -> 79).  Three places can hold such a reference: an
    already-planned field edit, the bytes of a whole-record row, and a record
    that stays where it is.
    """
    mp = (reloc or {}).get("map") or {}
    if not mp:
        return 0
    fixed = 0
    seen = set()
    for e in plan["edits"]:
        if e.get("space") != "tech":
            continue
        fld = e.get("field") or ""
        seen.add((e.get("index"), fld))
        if not fld.startswith("RequiredTechs.") or (e.get("width") or 0) != 2:
            continue
        try:
            old = struct.unpack("<h", e["mod"])[0]
        except struct.error:             # pragma: no cover
            continue
        new = mp.get(old)
        if new is None:
            continue
        e["mod"] = struct.pack("<h", new)
        e["relocated_from"] = old
        fixed += 1

    whole = set(r.get("index") for r in (plan.get("replace_tech") or []))
    # A record that travels as a whole is patched in its own bytes above; it
    # must NOT also get a field edit, because an edit addresses a position in
    # the TARGET file -- and that position holds an official tech, not this
    # one (the author additions sit at 1268..1291 of a 1,510-record official
    # array, which is inside it).
    whole |= set(r.get("at") for r in (plan.get("add_tech") or []))
    rows = list(plan.get("add_tech") or []) + list(plan.get("replace_tech") or [])
    for row in rows:
        blob = row.get("bytes")
        if not blob:
            continue
        patched, n = _patch_refs(blob, new_f.gv, mp)
        if n:
            row["bytes"] = patched
            fixed += n

    mspans = mod_f.build_tech_spans()
    nspans = new_f.build_tech_spans()
    for i in range(min(len(mspans), len(nspans))):
        if i in mp or i in whole:
            # i in mp: that position now holds the official own tech, and an
            # edit there would rewrite a record the author never owned.
            continue
        try:
            f = TF.fields_at(mod_f.raw, mod_f.gv, mspans[i][0])
        except Exception:                # noqa: BLE001
            continue
        # What the target holds TODAY in that cell is the value an edit must
        # quote as its `base`; quoting the mod copy instead would raise a
        # conflict against a cell nobody contested.
        try:
            cur = TF.fields_at(new_f.raw, new_f.gv, nspans[i][0])
        except Exception:                # noqa: BLE001
            cur = f
        for name, m in f.items():
            if not name.startswith("RequiredTechs.") or m.get("kind") != "i16":
                continue
            if (i, name) in seen:
                continue
            v = m.get("value")
            new = mp.get(v) if isinstance(v, int) else None
            if new is None:
                continue
            hold = (cur.get(name) or {}).get("value")
            if not isinstance(hold, int):
                hold = v
            plan["edits"].append({
                "space": "tech", "index": i, "field": name,
                "rel": 0, "width": 2,
                "base": struct.pack("<h", hold),
                "mod": struct.pack("<h", new),
                "relocated_from": v})
            seen.add((i, name))
            fixed += 1

    if fixed:
        plan["notes"].append(
            "引用那几条科技的前置条件一共改了 %d 处，前置链没有断。" % fixed)
    return fixed


# ---------------------------------------------------------------------------
# linking the author's effects to the target's effect table
# ---------------------------------------------------------------------------

def _effect_records(raw):
    '''Every effect record in `raw`, as raw bytes, in table order.

    A record's bytes already hold its name, its command count and its
    commands, so the bytes ARE the content.  Identity by decoded fields would
    add a second way to describe the same record and therefore a second way to
    be wrong about it -- and an effect carries no id to compare in the first
    place, which is the whole difficulty.
    '''
    recs, leftover = TB.scan(raw, "effect")
    if leftover:
        raise UpgradeError(
            "「effect」这张表扫到最后一字节还剩 %d 字节没走完，记录边界不可信。"
            "这种情况下认不出哪条效果是哪条，接过去只会张冠李戴，"
            "所以这次一条科技效果都没动。" % leftover)
    return [bytes(raw[r["start"]:r["end"]]) for r in recs]


def _effect_name(blob):
    '''The debug name at the head of one effect record, or None.'''
    try:
        r = P.Reader(blob, P.GV_C32)
        _marker, name = r.debug_string()
        return name
    except Exception:                               # pragma: no cover
        return None


def _tech_pointer(raw, gv, start):
    '''`(offset, value)` of a technology record's EffectID, or None.'''
    m = TF.fields_at(raw, gv, start).get("EffectID")
    if m is None or m["kind"] != "i16":
        return None
    return int(m["offset"]), int(m["value"])


def _patch_pointer(blob, gv, value):
    '''Rewrite the EffectID inside an encoded technology record.'''
    try:
        m = TF.fields_at(blob, gv, 0).get("EffectID")
    except Exception:                               # pragma: no cover
        return None
    if m is None or m["kind"] != "i16":
        return None
    off = int(m["offset"])
    try:
        return blob[:off] + struct.pack("<h", int(value)) + blob[off + 2:]
    except (struct.error, TypeError, ValueError):    # pragma: no cover
        return None


def _join_effects(mb, nb):
    '''Map every author effect onto the merged table, and name the tail.

    Returns ``(emap, tail, join)``:

      * ``emap[i]`` -- where author effect `i` ends up in the merged table;
      * ``tail``    -- the author indices appended after the target's own
                       records, in the order they are appended (so author
                       tail item `k` lands at index ``len(nb) + k``);
      * ``join``    -- how each author record was settled, for the report.

    Split out from :func:`_link_effects` because this is the part with a right
    answer that can be checked without a single .dat: feed it two lists of
    bytes and the mapping must keep content, drop nothing, and never append a
    record the target already holds.  Everything else in `_link_effects` is
    bookkeeping around this decision.

    The four tests, in order, and why the order matters:

      1. keep      -- `nb[i] == mb[i]`: the target already holds these bytes at
                      this exact index.  Asked FIRST, and against the TARGET,
                      never against the base: the base question reads as "the
                      author never edited this slot, keep it", which is wrong
                      exactly when the target has since reused that index.
      2. find      -- some target slot holds these bytes (first occurrence wins,
                      so the mapping is deterministic).
      3. tail-dupe -- an earlier author record was already appended with these
                      bytes (most of an author's table duplicates the base).
      4. tail      -- append.
    '''
    first = {}
    for i, blob in enumerate(nb):
        first.setdefault(blob, i)
    emap = [0] * len(mb)
    tail = []
    tail_at = {}
    join = {"keep": 0, "find": 0, "tail": 0, "tail_dupe": 0}
    for i, blob in enumerate(mb):
        if i < len(nb) and nb[i] == blob:
            emap[i] = i
            join["keep"] += 1
            continue
        j = first.get(blob)
        if j is not None:
            emap[i] = j
            join["find"] += 1
            continue
        j = tail_at.get(blob)
        if j is not None:
            emap[i] = j
            join["tail_dupe"] += 1
            continue
        emap[i] = len(nb) + len(tail)
        tail_at[blob] = emap[i]
        tail.append(i)
        join["tail"] += 1
    return emap, tail, join


def _link_effects(plan, base_f, mod_f, new_f, reloc=None):
    '''Point every carried technology at the effect its author actually meant.

    WHY THIS EXISTS
    ---------------
    An effect record has no id: `table_key_of` identifies it by its POSITION
    (`("index", 3)`), which is correct only while the bytes around it are the
    ones the author built them on.  Applied onto a newer file the target's
    effect table is not the author's table, so a technology copied over
    verbatim points at whatever now sits in that slot.  Measured on 408773
    (VER 8.8 -> 8.9): 1,731 live pointers, 247 of them naming a different
    effect and 5 naming nothing at all.  That is what "the mod updated and
    every effect vanished" looks like from the player's chair.

    WHAT THE MERGE IS
    -----------------
    The result's effect table is the TARGET's own records, untouched, plus the
    author's own records appended after them.  Nothing is inserted before the
    target's last record: every effect index in the official technology
    section is a position, and an insert would move all of them.

    A mod record joins the table by this order, and only this order:

      1. keep      -- `target[k]` is byte-identical at the SAME index: the
                      record was inherited unchanged and needs no move;
      2. find      -- some target slot already holds exactly these bytes;
      3. tail-dupe -- an earlier author record was appended with these bytes
                      (most of an author's table is duplicates of the base);
      4. tail      -- nothing holds them: append.

    Note the first test asks about TARGET[k] versus MOD[k], never BASE[k]
    versus MOD[k].  Asking the base first reads as "the author never edited
    this slot, so keep it", and that is wrong in exactly the case that hurts:
    the author's slot is inherited, but the TARGET has since reused that index
    for different content -- 8.9 shortened every `X Tech Tree` effect.
    Measured that way, 111 of 1,731 pointers still named the wrong effect while
    the mapping reported success.

    WHO GETS REWRITTEN
    ------------------
    A technology's pointer is rewritten only when the effect the author meant
    is not the effect the target would hand it -- that is, when the mod's
    record at that pointer differs from the base's record at the base's
    pointer.  When the two are equal the author never touched this effect and
    the target's own pointer is the newer official answer; downgrading it to
    the old bytes would revert an official patch, which is the opposite of the
    job this module exists to do.

    Returns a small report, or None when there was nothing to link.
    '''
    mb = _effect_records(mod_f.raw)
    nb = _effect_records(new_f.raw)
    if not mb or mb == nb:
        return None
    bb = _effect_records(base_f.raw)

    emap, tail, join = _join_effects(mb, nb)

    # The target's own records are never patched in place: an edit there lands
    # on a record some official technology still points at, and a whole-record
    # replace rewrites that same slot.  The author's version travels as a whole
    # record at the tail instead, byte for byte, which is also why every
    # `effect` row already in the plan is dropped here rather than merged.
    plan["add_table"] = [r for r in (plan.get("add_table") or [])
                         if r.get("table") != "effect"]
    plan["del_table"] = [r for r in (plan.get("del_table") or [])
                         if r.get("table") != "effect"]
    plan["replace_table"] = [r for r in (plan.get("replace_table") or [])
                             if r.get("table") != "effect"]
    kept = []
    for e in plan.get("edits") or []:
        if e.get("space") == "effect":
            continue
        if e.get("space") == "tech" and e.get("field") == "EffectID":
            # The pointer is decided below from what the author's effect
            # record actually says.  A diff of those two bytes is a weaker
            # statement about the same thing and would be re-decided anyway.
            continue
        kept.append(e)
    plan["edits"] = kept
    for k, i in enumerate(tail):
        plan["add_table"].append({
            "table": "effect", "key": ("index", len(nb) + k),
            "bytes": mb[i]})

    mspans = mod_f.build_tech_spans()
    nspans = new_f.build_tech_spans()
    bspans = base_f.build_tech_spans()

    # Technologies whose record the author owns outright: the ones moved off a
    # slot the official file reused, and the ones he appended himself.  See
    # _relocate_techs -- every key in that map is a position in the TARGET that
    # holds somebody else technology, so the author's answer is the only one
    # that can be inherited there.
    own = set((reloc or {}).get("map") or {})

    def _decide(i):
        '''``(want, now)`` for mod tech ``i``: the pointer the merged file must
        hold, and the pointer the target's own bytes hold today.

        ``want is None`` only when the bytes cannot answer (an unreadable
        pointer); every other answer is a concrete index, ``-1`` included, so
        a caller that rewrites a whole record can always patch it and a caller
        that edits one field can compare against ``now`` and skip a no-op.

        ONE question decides it -- did the author touch this effect?

          * ``base[base_pointer] == mod[mod_pointer]``: no.  The author
            inherited the record, so the OFFICIAL answer wins, whatever it now
            is: a rebalanced percentage under an unchanged name, a renamed
            effect, a slot reused for something else, or a pointer officially
            retired to -1.

          * anything else -- including no base record at all, because the
            author is the one who added this technology: the author's record
            is what the technology means, so point at wherever the merged
            table put those bytes.

        The old rule asked a SECOND question -- "does the target's slot still
        carry the same NAME?" -- and followed the official answer only when it
        did.  A balance patch is exactly a change of numbers under an
        unchanged name, so that test put the pre-patch copy back into play:
        measured on 314918, 61 technologies had their pointer pulled off the
        official answer and 46 of them landed on the author's stale copy in
        the tail ('C-Bonus, Military cost -10%' pinned to -10% while the
        official record had moved to -15%).  Name equality was never the
        right question; authorship of the edit is.
        '''
        if not (0 <= i < len(mspans)):
            return None, None
        pm = _tech_pointer(mod_f.raw, mod_f.gv, mspans[i][0])
        if pm is None:
            return None, None
        v = pm[1]
        pn = (_tech_pointer(new_f.raw, new_f.gv, nspans[i][0])
              if 0 <= i < len(nspans) else None)
        now = pn[1] if pn is not None else None
        pb = (_tech_pointer(base_f.raw, base_f.gv, bspans[i][0])
              if 0 <= i < len(bspans) else None)
        if i in own:
            # The author owns this technology outright -- he filled a slot the
            # official file has since put to another use, or he appended one of
            # his own.  There is no "official answer" to inherit: whatever his
            # record says is the meaning of his technology, so the pointer is
            # his, mapped onto the merged table.
            return (emap[v], now) if 0 <= v < len(mb) else (v, now)
        if not (0 <= v < len(mb)):
            # A pointer outside the author's own table is not a mistake: -1 is
            # how the format says "this technology grants no effect".  The
            # author removed the effect (314918: techs 381/382/403/967, where
            # that field is the ONLY byte he changed, so the diff still knows
            # the record was touched).  Inheriting the official pointer here
            # would hand the effect back.
            if pb is not None and pb[1] == v and now is not None:
                return now, now
            if v < 0:
                return v, now
            return None, now
        mc = mb[v]
        if pb is not None and 0 <= pb[1] < len(bb) and bb[pb[1]] == mc \
                and now is not None:
            return now, now
        return emap[v], now

    rewritten = 0
    overflow = 0
    repl = set(r.get("index") for r in (plan.get("replace_tech") or []))
    # A relocated tech left its old position behind for the official file to
    # keep: writing an EffectID there would rewrite somebody else record.
    # Every position in `map` holds a OFFICIAL technology in the target: the
    # author record was either moved off a reused slot or appended past the
    # target array (the author additions at 1268..1291 sit INSIDE a 1,510-record
    # official array).  Writing EffectID into such a position would rewrite a
    # tech the author never owned -- only the travelling record itself may be
    # patched, and _repack does that.
    skip = set((reloc or {}).get("map") or {})
    for i in range(min(len(mspans), len(nspans))):
        if i in repl or i in skip:
            continue
        want, now = _decide(i)
        if want is None or now is None or want == now:
            continue
        if want > 32767 or want < -32768:
            overflow += 1
            continue
        plan["edits"].append({
            "space": "tech", "index": i, "field": "EffectID",
            "rel": 0, "width": 2,
            "base": struct.pack("<h", now),
            "mod": struct.pack("<h", want)})
        rewritten += 1

    # Records that travel as a whole (a re-laid-out tech, or one the author
    # added) cannot be steered by an edit: their bytes are built from the mod
    # and land outside the target's own array.  Rewrite the pointer inside the
    # encoded blob instead, so the bytes that get appended are already right.
    def _repack(row, i):
        # NOT `now == want: skip`.  This row travels as a whole record whose
        # bytes were authored against an older layout, so its EffectID says
        # nothing about the target's own pointer at that index -- it says what
        # the author's table looked like.  A record that lands in a different
        # slot must be patched even when the number happens to be equal.
        if row.get("bytes") is None:
            return False
        want, _now = _decide(i)
        if want is None:
            return False
        if want > 32767 or want < -32768:
            return False
        blob = _patch_pointer(row["bytes"], new_f.gv, want)
        if blob is None:
            return False
        row["bytes"] = blob
        return True

    for row in plan.get("replace_tech") or []:
        if _repack(row, row.get("index")):
            rewritten += 1
    for row in plan.get("add_tech") or []:
        if _repack(row, row.get("at")):
            rewritten += 1

    out = {
        "mod": len(mb), "new": len(nb), "out": len(nb) + len(tail),
        "appended": len(tail), "join": join,
        "pointers": rewritten, "overflow": overflow,
    }
    if tail or rewritten:
        plan["notes"].append(
            "科技效果按内容接到了目标文件的效果表上：目标表 %d 条原样保留，"
            "作者自己的效果按原顺序接在后面 %d 条（共 %d 条）；"
            "%d 个科技的效果编号跟着改成了新位置。"
            % (len(nb), len(tail), len(nb) + len(tail), rewritten))
    return out


def _gone_in_target(frame, row):
    '''True when the field an unmapped row wanted does not exist in `frame`.

    A generation change drops fields: 8.9 removed `Creatable.HotKeyFromUnit`
    (present on all 82,934 VER 7.8 records, measured) and widened the bird task
    list from 10 slots to 12, which retires `Bird.Tasks.10.*` and `.11.*`.
    An author edit that lands on one of those cells has nowhere to go -- the
    cell is not in the target layout at all.  That is a fact about the two
    generations, not a defect in the merge, and it must not be the sentence
    that refuses an otherwise fully carried mod.
    '''
    field = row.get('field')
    if not field:
        return False
    space = row.get('space')
    try:
        if space == 'unit':
            span = frame.unit_span(row.get('civ'), row.get('unit'))
            if span is None:
                return False
            names = frame.unit_fields(span[0], span[1])
        elif space == 'tech':
            idx = row.get('index')
            if idx is None or idx >= frame.tech_count():
                return False
            names = frame.tech_fields(idx)
        elif space in ('graphic', 'sound', 'effect', 'terrain', 'task'):
            key = row.get('key')
            # Report rows carry the key as a JSON-friendly list; the index is
            # keyed by the tuple the frame built.  Without this the lookup
            # raised TypeError, the except below swallowed it, and every
            # table-side gone field stayed in `unmapped`.
            rec = frame.table_index(space).get(
                tuple(key) if isinstance(key, list) else key)
            if rec is None:
                return False
            names = frame.table_fields(space, rec)
        else:
            return False
    except Exception:
        return False
    return field not in names


def _classify_gone(rep, plan, new_f):
    """Move author edits that landed on deleted fields out of ``unmapped``.

    A field the NEW generation no longer has is not a defect in this merge:
    the cell the author edited does not exist in the target layout, so there
    is nowhere to put the number.  It is still said out loud -- it goes in
    the report as ``port_gone`` -- but it cannot be the reason to refuse a mod
    that is otherwise fully carried.  Measured on 209785 (8.4 -> 8.9): 54 such
    cells, all of them ``Creatable.HotKeyFromUnit``, a field 8.9 removed.

    Idempotent: the check and the apply each own a report and classify it.
    """
    if not rep.get("unmapped"):
        return 0
    gone = [r for r in rep["unmapped"] if _gone_in_target(new_f, r)]
    if not gone:
        return 0
    rep["unmapped"] = [r for r in rep["unmapped"]
                       if not _gone_in_target(new_f, r)]
    rep["port_gone"] = [
        {"space": r.get("space"), "civ": r.get("civ"),
         "unit": r.get("unit"), "index": r.get("index"),
         "key": r.get("key"), "field": r.get("field")} for r in gone]
    sentence = ("作者改过 %d 个新版本已经删掉的字段，那些改动没有去处"
                "（已列在报告里）" % len(gone))
    if sentence not in plan.get("notes", []):
        plan.setdefault("notes", []).append(sentence)
    return len(gone)


def _resolve(target, edit):
    """Where this edit lives in ``target``, or ``None`` if it is gone."""
    space = edit["space"]
    if space == "civ":
        ranges = target.civ_header_fields(edit["civ"])
        if not ranges:
            return None
        for name, off, w in ranges:
            if name == edit["field"]:
                if edit["rel"] + edit["width"] > w:
                    return None
                return off + edit["rel"]
        return None

    # Everything below goes through `_field_ranges`, whose tuples are
    # ``(offset, width, name)`` -- a different order from ``civ_header_fields``
    # because the two are built for different readers.  Unpacking one as the
    # other is silent: every comparison against a field name just fails, and the
    # edit is reported as "the new version has no such field", which is a lie
    # about the file rather than about this function.  Keeping the two branches
    # apart is what makes that mistake impossible to reintroduce.
    if space == "unit":
        span = target.unit_span(edit["civ"], edit["unit"])
        if not span:
            return None
        ranges = target.unit_fields(span[0], span[1])
    elif space == "tech":
        if edit["index"] >= target.tech_count():
            return None
        ranges = target.tech_fields(edit["index"])
    else:
        rec = target.table_index(space).get(edit["key"])
        if rec is None:
            return None
        ranges = target.table_fields(space, rec)
    if not ranges:
        return None
    return _found(ranges, edit["field"], edit)


def _found(ranges, field, edit):
    """The offset of `field` inside `ranges`, following a generation rename.

    A byte diff reads its field names out of the BASE file, so an edit is
    addressed by the name the OLD generation used.  When the target renamed
    that field, the name is simply not in `ranges` and the edit looks like it
    landed on a deleted field -- which is a false report, and a lossy one: the
    author's value is dropped while the same number sits one level down under
    its new name.  Measured on 209785 (8.4 -> 8.9): 54 author edits of
    `Creatable.HotKeyFromUnit` became "the new version has no such field" while
    8.9 keeps it at `Creatable.TrainLocations.0.HotKeyID`.

    `portgen._SIMPLE_FOLD` already owns that mapping -- the tape needs it to
    re-lay-out whole records -- so the planner asks the same table instead of
    keeping a second copy that can drift.
    """
    for off, w, name in ranges:
        if name == field:
            if edit["rel"] + edit["width"] > w:
                return None
            return off + edit["rel"]
    moved = PG.folded_name(field)
    if moved is None:
        return None
    for off, w, name in ranges:
        if name == moved:
            # The slice, not the field, is what has to fit.  A byte diff emits
            # the narrowest run that differs -- the measured hotkey edit on 209785
            # is two bytes (`5a41` -> `c43e`, 16730 -> 16068) inside a four-byte
            # i32 whose high half never changed -- so demanding `w == edit["width"]`
            # rejects every real hotkey edit while accepting only the invented case
            # it was meant to guard.  Comparing the whole field would be wrong in
            # the other direction too: the two generations must agree on the CELL
            # width (i16/i16, u8/u8, i32/i32, measured for every pair in
            # `_SIMPLE_FOLD`), and writing a narrow slice into a wider cell is
            # exactly what the unrenamed branch above already does.
            if edit["rel"] + edit["width"] > w:
                return None
            return off + edit["rel"]
    return None


def _apply_edits(target, edits, work, official_wins=False):
    """Write every carryable edit into ``work`` (a bytearray of ``target.raw``).

    Returns ``(applied, refused, conflicts, ranges)``.  ``conflicts`` are edits
    where the official stream had already moved that exact field: the author's
    value still wins (that is what "my mod" means), but the row is reported so
    the user is never surprised by which side won.
    """
    applied, refused, conflicts, ranges = [], [], [], []
    for e in edits:
        off = _resolve(target, e)
        if off is None:
            refused.append({
                "space": e["space"], "civ": e.get("civ"),
                "unit": e.get("unit"), "index": e.get("index"),
                "key": list(e["key"]) if e.get("key") else None,
                "field": e["field"],
                "why": "新版本里没有这个字段了（记录被删了，或者字段名变了）"})
            continue
        w = e["width"]
        now = bytes(work[off:off + w])
        was = e["base"]
        # A conflict is "we disagree", not "you touched it".  When the official
        # patch moved this field to exactly the value the author wanted, the two
        # of us agree: there is nothing to report and nothing to choose, and
        # calling that a conflict would bury the real ones under hundreds of
        # rows -- measured on a fixture that edits one field in 63 civilizations,
        # 63 agreement rows read as 63 alarms.
        conflict = now != was and now != e["mod"]
        if conflict:
            conflicts.append({
                "space": e["space"], "civ": e.get("civ"),
                "unit": e.get("unit"), "index": e.get("index"),
                "key": list(e["key"]) if e.get("key") else None,
                "field": e["field"],
                "base_was": was.hex(), "official_now": now.hex(),
                "mod_wants": e["mod"].hex(),
                "won": "official" if official_wins else "mod"})
            if official_wins:
                continue
        if now != e["mod"]:
            work[off:off + w] = e["mod"]
            ranges.append((off, w))
        applied.append({
            "space": e["space"], "civ": e.get("civ"),
            "unit": e.get("unit"), "index": e.get("index"),
            "key": list(e["key"]) if e.get("key") else None,
            "field": e["field"], "at": off, "width": w,
            "base_hex": was.hex(), "mod_hex": e["mod"].hex(),
            "official_changed": conflict})
    return applied, refused, conflicts, ranges


def _all_civ_layouts(raw, gv, civs_start, count=None, civs_end=None):
    """Every civilization's layout in ONE walk.

    ``records.civ_layout`` re-walks from the first civ on every call, which is
    fine for a single edit and quadratic for a mod that touched many civs.  This
    is the same loop without the early return, so N civs cost one pass instead
    of N passes.

    ``count`` is what stops the walk: the parser already told us how many
    civilizations there are, and that number does not move when a record is
    spliced in.  A byte bound would: after an insert the tail is stale by the
    inserted length, and a stale bound either truncates the last civ or -- with
    no bound at all, as this function first did -- runs on into the technology
    section and reads 8 more "civs" out of bytes that are not civilizations
    (measured on the shipped file: 71 blocks instead of 63, the last 8 inside
    the tech records).
    """
    if count is None:
        stop = len(raw) if civs_end is None else min(civs_end, len(raw))
    else:
        stop = len(raw)
    r = L.Orec(raw, civs_start, gv=gv)
    out = []
    while r.o < stop:
        start = r.o
        try:
            r.u8()                                  # player_type
            r.debug_string()                        # name
            n = r.i16()                             # resource count
            r.i16()                                 # tech_tree_id
            r.i16()                                 # team_bonus_id
            r.f32_array(n)
            r.u8()                                  # icon_set
            m_off = r.o
            m = r.i16()
            ptr_off = r.o
            flags = r.i32_array(m)
            spans = {}
            for k in range(m):
                if flags[k]:
                    s = r.o
                    u = L.walk_unit(r, 0)
                    spans[u["id"]] = (s, r.o)
        except Exception:
            break
        if m_off + 2 + 4 * m != ptr_off + 4 * m:
            break
        out.append({"start": start, "end": r.o, "m_off": m_off, "m": m,
                    "ptr_off": ptr_off, "run_start": ptr_off + 4 * m,
                    "run_end": r.o, "flags": flags, "spans": spans})
        if r.o <= start:
            break
        if count is not None and len(out) >= count:
            break
    return out


def _splice(raw, at, add):
    return raw[:at] + add + raw[at:]


def _replace_record(raw, lay, uid, blob):
    """Swap one record's bytes for ``blob``, keeping ids and flags in place."""
    s, e = lay["spans"][uid]
    delta = len(blob) - (e - s)
    raw = raw[:s] + blob + raw[e:]
    lay["spans"][uid] = (s, s + len(blob))
    if delta:
        lay["spans"] = dict(
            (k, (a + delta, b + delta) if a >= e else (a, b))
            for k, (a, b) in lay["spans"].items())
        lay["spans"][uid] = (s, s + len(blob))
    lay["run_end"] += delta
    return raw, delta


def _insert_unit(raw, lay, uid, blob):
    """Insert ``blob`` as the record for ``uid`` and mark it present.

    The record goes at its id's own position, not at the end: ids stay sorted,
    which is what every later lookup assumes, and what makes a second run of
    this function land the same bytes in the same place.
    """
    if uid + 1 > lay["m"]:
        grow = 4 * (uid + 1 - lay["m"])
        raw = _splice(raw, lay["run_start"], bytes(grow))
        raw = raw[:lay["m_off"]] + struct.pack("<h", uid + 1) \
            + raw[lay["m_off"] + 2:]
        lay["run_start"] += grow
        lay["run_end"] += grow
        lay["m"] = uid + 1
        lay["spans"] = dict((k, (a + grow, b + grow))
                            for k, (a, b) in lay["spans"].items())
    at = lay["run_end"]
    for other in sorted(lay["spans"]):
        if other > uid:
            at = lay["spans"][other][0]
            break
    raw = _splice(raw, at, blob)
    lay["spans"] = dict((k, (a + len(blob), b + len(blob)) if a >= at
                         else (a, b)) for k, (a, b) in lay["spans"].items())
    lay["spans"][uid] = (at, at + len(blob))
    lay["run_end"] += len(blob)
    off = lay["ptr_off"] + 4 * uid
    raw = raw[:off] + struct.pack("<i", 1) + raw[off + 4:]
    return raw, len(blob)


def _apply_records(target, plan, work, civs_start=None, tail=None):
    """Add, remove and rewrite whole records.  Returns ``(raw, report, expect)``.

    One splice per civilization, not one per record.  A splice copies the whole
    file, so doing it per record costs O(records x file): a real third-party mod
    asks for 31,563 added records, which at 100 MB apiece is 3 TB of memcpy and
    never finishes.  Rebuilding each civ's record run in one slice makes the
    same work O(civs) copies instead.

    Ordered so that every offset stays valid as it is used: civs from the last
    one down (a splice inside civ *i* only moves civs after it, all of which have
    already been handled), then the tech section, which is the last thing before
    the tail.
    """
    raw = bytes(work)
    gv = target.gv
    if civs_start is None:
        civs_start = target.civs_start
    if tail is None:
        tail = target.tail
    done = {"units": [], "techs": [], "removed": [], "refused": []}

    layouts = _all_civ_layouts(raw, gv, civs_start,
                               count=len(target.civs))
    if len(layouts) != len(target.civs):
        done["refused"].append({
            "why": "走文件时数出 %d 个文明，解析说有 %d 个，不敢在这种文件上做"
                   "结构改动" % (len(layouts), len(target.civs))})
        return raw, done, None

    per_civ_add = {}
    for row in plan["add_unit"]:
        per_civ_add.setdefault(row["civ"], []).append(row)
    per_civ_repl = {}
    for row in plan["replace"]:
        per_civ_repl.setdefault(row["civ"], []).append(row)
    per_civ_del = {}
    for row in plan["del_unit"]:
        per_civ_del.setdefault(row["civ"], []).append(row["unit"])

    for idx in range(len(target.keys) - 1, -1, -1):
        cn = target.keys[idx]
        dels = per_civ_del.get(cn)
        adds = per_civ_add.get(cn)
        repls = per_civ_repl.get(cn)
        if not (dels or adds or repls):
            continue
        lay = layouts[idx]
        was = len(raw)
        raw, got = _rebuild_civ(raw, lay, cn, dels, repls, adds, done)
        if got is None:
            return raw, done, None
        done["units"].extend(got["units"])
        # The tech section lives after every civ, so every byte this rebuild
        # added moved it.  Measured on a 115 MB third-party mod: 31,563 added
        # records pushed the tech section 21,198,543 bytes down; reading it at
        # the pre-rebuild offset landed in the middle of a unit run, the count
        # word there was garbage, and the appended technologies went into the
        # middle of a civilization -- the file then could not be walked past
        # civ 51 at all.
        if tail is not None:
            tail += len(raw) - was

    if plan["del_tech"]:
        done["refused"].append({
            "ids": list(plan["del_tech"]),
            "why": "作者删了科技记录；科技没有 id 字段、位置即 id，"
                   "删掉会让后面每一条的 id 前移，本模块不猜这件事"})
    repl_tech = dict((row["index"], row["bytes"]) for row in plan["replace_tech"])
    if repl_tech or plan["add_tech"]:
        if tail is None:
            tail = target.tail
        count_off, count, start, end = R.tech_section(raw, gv, tail)
        del count_off
        # The record area is rebuilt once, for the same reason the flat tables
        # are: a rewrite changes the record's own length, so the next record's
        # start moves with it, and splicing them one by one would copy the file
        # once per rewritten record.  Appending 1,190 techs one at a time was
        # 1,190 copies of 93 MB before this.
        spans = _tech_spans(raw, gv, start, count)
        if len(spans) != count:
            done["refused"].append({
                "why": "科技区说有 %d 条，实际只走出 %d 条，不敢在这种文件上做"
                       "结构改动" % (count, len(spans))})
            return raw, done, None
        parts, rewritten = [], 0
        at = start
        for i, (a, b) in enumerate(spans):
            blob = repl_tech.get(i)
            if blob is None:
                blob = bytes(raw[a:b])
            else:
                rewritten += 1
            parts.append(blob)
            at += len(blob)
        for row in plan["add_tech"]:
            done["techs"].append({"at": at, "bytes": len(row["bytes"]),
                                  "how": "appended"})
            parts.append(row["bytes"])
            at += len(row["bytes"])
        if rewritten:
            done["techs"].append({"rewritten": rewritten,
                                  "why": "作者改过这些科技记录的长度（多/少了"
                                         "研究地点、资源或名字），整条照抄"})
        body = b"".join(parts)
        raw = raw[:start] + body + raw[end:]
        raw = (raw[:tail] + struct.pack("<h", count + len(plan["add_tech"]))
               + raw[tail + 2:])
    return raw, done, None


def _tech_spans(raw, gv, start, count):
    """The ``(start, end)`` of each of the ``count`` tech records.

    ``R.tech_section`` reports where the section ends but not where each record
    does, and a rewrite needs the per-record spans.  ``L.walk_tech`` is the only
    thing that knows the layout (it branches on the game version), so this asks
    it rather than repeating the arithmetic -- the same rule that
    ``records._tech_name_off`` follows after assuming offset 0 renamed four
    bytes of ``RequiredTechs``.
    """
    r = L.Orec(raw, start, gv=gv)
    spans = []
    for _i in range(count):
        a = r.o
        L.walk_tech(r)
        spans.append((a, r.o))
    return spans


def _rebuild_civ(raw, lay, cn, dels, repls, adds, done):
    """Rewrite one civilization's record run in a single splice.

    ``(raw, report)``; ``report`` is ``None`` when this civ cannot be rebuilt
    and the caller should stop.  Deleted records are dropped, replaced ones swap
    their bytes, added ones are inserted at their id's own place, and the flag
    array is extended (never shrunk) so every id below still has a slot.
    """
    spans = lay["spans"]
    dels = set(dels or [])
    repl_by_id = {}
    for row in (repls or []):
        repl_by_id[row["unit"]] = row["bytes"]

    ids = [uid for uid in sorted(spans) if uid not in dels]
    add_ids = []
    for row in sorted(adds or [], key=lambda r: r["unit"]):
        uid = row["unit"]
        if uid in spans and uid not in dels:
            done["refused"].append({
                "civ": cn, "id": uid,
                "why": "新版本自己已经用了这个编号，插不进去"})
            continue
        if not 1 <= uid <= 32767:
            done["refused"].append({"civ": cn, "id": uid,
                                    "why": "编号超出 1..32767"})
            continue
        if uid in add_ids:
            done["refused"].append({"civ": cn, "id": uid,
                                    "why": "同一个编号在这批里出现了两次"})
            continue
        add_ids.append(uid)
    new_by_id = dict((row["unit"], row["bytes"]) for row in (adds or []))

    units = []
    body = []
    # Records stay ordered by id: every later lookup assumes it, and it is what
    # makes a second run of this module land the same bytes in the same place.
    plan_ids = sorted([uid for uid in ids if uid in repl_by_id or uid in spans]
                      + add_ids)
    for uid in plan_ids:
        if uid in add_ids:
            blob = new_by_id[uid]
            how = "inserted"
        elif uid in repl_by_id:
            blob = repl_by_id[uid]
            how = "replaced"
        else:
            a, b = spans[uid]
            blob = bytes(raw[a:b])
            how = None
        body.append(blob)
        if how:
            units.append({"civ": cn, "id": uid, "bytes": len(blob),
                          "how": how, "delta": None})
    for uid in sorted(dels):
        if uid in spans:
            a, b = spans[uid]
            done["removed"].append({"civ": cn, "ids": [uid], "bytes": b - a})

    new_body = b"".join(body)
    old_len = lay["run_end"] - lay["run_start"]
    top = max(list(spans) + add_ids + [0])
    want_m = max(lay["m"], top + 1)
    grow = 4 * (want_m - lay["m"])
    delta = grow + len(new_body) - old_len

    raw = (raw[:lay["run_start"]] + bytes(grow) + new_body
           + raw[lay["run_end"]:])
    if grow:
        raw = (raw[:lay["m_off"]] + struct.pack("<h", want_m)
               + raw[lay["m_off"] + 2:])

    # The flag array now spans ptr_off .. run_start+grow and has to say "yes" for
    # exactly the ids that have a record.  Written as one slice, in place: the
    # zeros for the new slots were inserted above, so the length already agrees.
    flags = bytearray(raw[lay["ptr_off"]:lay["ptr_off"] + 4 * want_m])
    present = set(plan_ids)
    for uid in range(want_m):
        off = 4 * uid
        flags[off:off + 4] = struct.pack("<i", 1 if uid in present else 0)
    raw = (raw[:lay["ptr_off"]] + bytes(flags)
           + raw[lay["ptr_off"] + 4 * want_m:])

    for row in units:
        row["delta"] = delta if row["how"] == "inserted" else None
    return raw, {"units": units, "delta": delta}


# ---------------------------------------------------------------------------
# flat tables: count + fixed-shape records, rebuilt in one splice
# ---------------------------------------------------------------------------

def _table_geometry(raw, table):
    """Where a flat table's count, flag array and records start.

    Read from the parser's own stage boundaries instead of repeating the
    layout: ``sound`` is ``i16 count`` then records; ``effect`` is ``i32
    count`` then records; ``graphic`` is ``i16 count`` then ``count`` i32
    existence flags then records.  Measured on the shipped file, the flag
    array is what makes ``graphic_count`` 21,001 while only 20,883 records
    exist -- 118 flags are zero, and a zero flag means "no record here".
    """
    bounds, stats = TB.stage_offsets(raw, "5 ")
    spec = TB.TABLES[table]
    start, end = bounds[spec["stage"]]
    count = stats.get(spec["count"])
    if count is None:
        raise UpgradeError("读不到「%s」表的条数" % table)
    if table == "effect":
        return {"count_off": start, "count_kind": "i32", "count": count,
                "flags_start": None, "flags_count": 0,
                "records_start": start + 4, "end": end}
    rec_start = start + 2
    flags_count = 0
    if table == "graphic":
        # The parser keeps a flag per *slot*, and only non-zero flags are
        # records, so the record area begins after the whole flag array.
        flags_count = count
        rec_start = start + 2 + 4 * count
    return {"count_off": start, "count_kind": "i16", "count": count,
            "flags_start": (start + 2) if table == "graphic" else None,
            "flags_count": flags_count,
            "records_start": rec_start, "end": end}


def _pack_count(kind, value):
    return struct.pack("<i" if kind == "i32" else "<h", int(value))


def _apply_tables(target, plan, raw):
    """Add, remove and rewrite whole records in the flat tables.

    ``(raw, done, delta)``.  Every flat table sits *before* the civ section, so
    all of these splices move the civs and the techs by the same amount, and the
    caller only has to add ``delta`` to ``civs_start`` and ``tail`` afterwards.
    That is why this runs first: doing it after the civ splices would invalidate
    every civ offset that had already been used.

    The record area is rebuilt in one pass rather than edited in place, because
    all three operations (append, delete, rewrite) are the same question -- what
    is the ordered list of records now? -- and answering it once means a
    replaced record cannot leave a hole whose size the count word still believes.
    """
    done = {"tables": [], "refused": [], "rules": [], "marks": []}
    adds, dels = plan.get("add_table") or [], plan.get("del_table") or []
    repls = plan.get("replace_table") or []
    if not adds and not dels and not repls:
        return raw, done, 0
    delta = 0
    rules = done["rules"]
    marks = done["marks"]

    for table in _TABLE_FLAT + _TABLE_REPLACE:
        tadds = [r for r in adds if r["table"] == table]
        tdels = [r for r in dels if r["table"] == table]
        trepl = {r["key"]: r for r in repls if r["table"] == table}
        if not tadds and not tdels and not trepl:
            continue
        if table in _TABLE_REPLACE and (tadds or tdels):
            # Appending a terrain or colour record means moving the block that
            # follows the record area -- a terrain block tail plus the random
            # maps, or the end of stage 1 -- and this module does not
            # re-serialise either.  Replacing a record in place is the one
            # operation whose answer is still the file itself.
            done["refused"].append({
                "space": table,
                "why": "作者在「%s」表里加了 %d 条、删了 %d 条记录。这张表的记录区"
                       "后面紧跟着本模块不重新序列化的块，只有整条替换说不清"
                       "位置，所以这一层不动。"
                       % (table, len(tadds), len(tdels))})
            tadds, tdels = [], []
            if not trepl:
                continue
        if table == "graphic" and tdels:
            done["refused"].append({
                "space": table,
                "why": "作者从「graphic」表里删了 %d 条记录。图形表每个记录槽前面"
                       "还有一个 i32 存在标志，而标志的下标和记录里的 ID 并不是"
                       "一回事（实测 20,883 条里 0 条相等），删哪一格没有可证的"
                       "答案，所以这一层不猜。" % len(tdels)})
            tdels = []

        recs, leftover = TB.scan(raw, table)
        if leftover:
            done["refused"].append({
                "space": table,
                "why": "「%s」表扫到最后一字节还剩 %d 字节没走完，偏移不可信"
                       % (table, leftover)})
            continue
        if table in _TABLE_REPLACE:
            # No count word to write and no flag array: the section this table
            # owns is exactly its records, so the splice is bounded by the
            # records themselves.  Measured on the shipped file, stage 4 holds
            # ``terrain`` 3,502,159..3,588,524 and then 71 more bytes of block
            # tail plus the random maps, and stage 1 ends exactly on the last
            # colour record (145,742).
            if not recs:
                done["refused"].append({
                    "space": table,
                    "why": "「%s」表里一条记录都没扫到，这一层不动。" % table})
                continue
            geo = {"count_off": None, "count_kind": None, "count": len(recs),
                   "flags_start": None, "flags_count": 0,
                   "records_start": recs[0]["start"], "end": recs[-1]["end"]}
        else:
            geo = _table_geometry(raw, table)

        del_keys = set(r["key"] for r in tdels)
        parts, removed, rewritten = [], [], []
        for rec in recs:
            key = target.table_key_of(table, rec, raw=raw)
            if key in del_keys:
                removed.append(list(key))
                continue
            blob = bytes(raw[rec["start"]:rec["end"]])
            rep = trepl.get(key)
            if rep is not None:
                blob = rep["bytes"]
                rewritten.append({"key": list(key),
                                  "bytes": [len(rep["base"]), len(blob)]})
            parts.append(blob)
        for row in tadds:
            parts.append(row["bytes"])
        blob = b"".join(parts)

        old_span = geo["end"] - geo["records_start"]
        grew = len(blob) - old_span
        flags = b""
        if table == "graphic" and tadds:
            # A record needs a non-zero flag in front of it and the array has to
            # stay exactly ``graphic_count`` long, so both grow together: the
            # flags sit before the record area, so they are spliced first.
            flags = struct.pack("<i", 1) * len(tadds)
            grew += len(flags)
        if not grew and not removed and not tadds and not rewritten:
            continue

        # One splice for the whole record area (plus the flags, which sit right
        # in front of it): recording a single rule at `records_start` means every
        # later offset moves by the same amount, which is exactly what happened,
        # and it keeps the rule list short enough to reason about.
        raw = (raw[:geo["records_start"]] + flags + blob
               + raw[geo["end"]:])
        rules.append((geo["records_start"], grew))
        delta += grew

        if geo["count_off"] is not None:
            # A replace-only table has no count word to correct: its record
            # count is the file's own and nothing here added or removed one.
            new_count = geo["count"] + len(tadds) - len(removed)
            width = 4 if geo["count_kind"] == "i32" else 2
            raw = (raw[:geo["count_off"]]
                   + _pack_count(geo["count_kind"], new_count)
                   + raw[geo["count_off"] + width:])
            marks.append((geo["count_off"], width))

        row = {"table": table, "bytes_added": sum(len(r["bytes"]) for r in tadds),
               "bytes_freed": None, "added": [list(r["key"]) for r in tadds],
               "removed": removed, "rewritten": rewritten}
        if removed:
            # How many bytes the deletions actually took out, as opposed to how
            # much the section shrank (a rewrite can cancel a deletion out).
            row["bytes_freed"] = len(removed) and sum(
                rec["end"] - rec["start"] for rec in recs
                if target.table_key_of(table, rec, raw=raw) in del_keys)
        done["tables"].append(row)

    # Sorted ascending: a range that starts at or after a splice moved with it,
    # and the rules compose because each splice only touches bytes after itself.
    rules.sort()
    return raw, done, delta


def _shift_after(rules, off):
    """Where ``off`` lands once every recorded splice has been applied."""
    for at, d in rules:
        if off >= at:
            off += d
    return off


def _shift_ranges(rules, ranges):
    """Rewrite ``(off, width)`` pairs into post-splice coordinates.

    A range that straddles a splice cannot be represented as one range any
    more; it is dropped here and reported by the caller's stray check, because
    silently widening it would claim bytes this module never wrote.
    """
    out = []
    for off, w in ranges:
        a, b = off, off + w
        moved_a, moved_b = _shift_after(rules, a), _shift_after(rules, b)
        if moved_b - moved_a == w:
            out.append((moved_a, w))
    return out


# ---------------------------------------------------------------------------
# verification: prove the output is the intended one
# ---------------------------------------------------------------------------

def _verify(raw, new_raw, ranges, expect=None, tables=None):
    """Prove ``raw`` is the intended stream, not merely a parseable one.

    Every statement here is cheap and falsifiable:

    * the stream parses to its last byte;
    * the civ blocks are contiguous and end at the tail;
    * every table walk leaves zero leftover;
    * every byte that differs from ``new`` is inside a range this module meant
      to write;
    * when records moved, the record key sets and the added records' bytes are
      the expected ones.

    ``tables`` narrows the table walks.  A walk is proof about *that table*, and
    it costs 5.6 s for ``task`` and 0.3 s each for the others; when no written
    range reaches a table's own bytes the walk cannot fail, and paying 7 s for a
    statement that cannot fail is not proof, it is ceremony.  ``None`` means
    walk them all, which is what a caller without a range list should do.

    A failure is a defect in this module, not in the mod, so it is raised with
    the offending offsets rather than reported as a user-facing verdict.
    """
    out = {"ok": True, "parsed_bytes": 0, "civs": 0, "tables": {},
           "stray": [], "written_bytes": sum(w for _o, w in ranges)}
    if len(raw) == len(new_raw):
        out["same_length"] = True
        stray = [[off, n] for off, n in L.diff_regions(new_raw, raw)
                 if not _covered(off, n, ranges)]
        out["stray"] = stray[:64]
        out["stray_count"] = len(stray)
        if stray:
            out["ok"] = False
    else:
        out["same_length"] = False
        out["delta_bytes"] = len(raw) - len(new_raw)

    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    out["parsed_bytes"] = p.r.pos
    if p.r.pos != len(raw):
        out["ok"] = False
        out["parse_leftover"] = len(raw) - p.r.pos
        return out
    civs, civs_start, _gv, tail = L.locate(raw, p)
    del civs_start
    out["civs"] = len(civs)
    out["contiguous"] = all(civs[i]["_start"] == civs[i - 1]["_end"]
                            for i in range(1, len(civs)))
    out["tail_ok"] = bool(civs) and civs[-1]["_end"] == tail
    if not out["contiguous"] or not out["tail_ok"]:
        out["ok"] = False
    # ``colour`` is here because ``_apply_tables`` can now rewrite one of its
    # records; a walk left out of this list is a section nobody proves still
    # ends where its own records say it does.
    all_tables = ("graphic", "sound", "effect", "terrain", "task",
                  "restriction", "colour")
    want = all_tables if tables is None else tuple(
        t for t in all_tables if t in tables)
    out["tables_skipped"] = [t for t in all_tables if t not in want]
    for table in want:
        try:
            _recs, leftover = TB.scan(raw, table)
        except Exception as exc:                    # pragma: no cover
            out["tables"][table] = "error: %s" % exc
            out["ok"] = False
            continue
        out["tables"][table] = leftover
        if leftover:
            out["ok"] = False

    if expect:
        keys = _civ_keys(civs)
        got = set()
        pos = {}
        for civ, cn in zip(civs, keys):
            for u in civ["units"]:
                got.add((cn, u["id"]))
                pos[(cn, u["id"])] = (u["_start"], u["_end"])
        missing = expect["units"] - got
        extra = got - expect["units"]
        out["units_missing"] = sorted(list(missing))[:32]
        out["units_extra"] = sorted(list(extra))[:32]
        if missing or extra:
            out["ok"] = False
        bad = []
        for row in expect["added"]:
            k = (row["civ"], row["unit"])
            span = pos.get(k)
            if span is None:
                bad.append([row["civ"], row["unit"], "missing"])
            elif raw[span[0]:span[1]] != row["bytes"]:
                bad.append([row["civ"], row["unit"], "bytes differ"])
        out["added_checked"] = len(expect["added"])
        out["added_bad"] = bad[:32]
        if bad:
            out["ok"] = False
    return out


def _covered(off, n, ranges):
    end = off + n
    cur = off
    for a, w in sorted(ranges):
        if a > cur:
            break
        if a <= cur < a + w:
            cur = a + w
            if cur >= end:
                return True
    return cur >= end


# ---------------------------------------------------------------------------
# resolving the three streams
# ---------------------------------------------------------------------------

def _civ_names(raw):
    """The civilization names in one .dat, or None when it cannot be read."""
    try:
        _stats, civs, _cs, _gv, _tail, _how = _parse(raw)
    except BaseException:
        return None
    names = set(c.get('name') for c in civs if c.get('name'))
    return names or None


def _pick_base_by_civs(ver, mod_raw, exclude=None):
    """The archived build of ``ver`` whose civilization list is the mod's.

    ``archives.pick_base`` answers "this generation, newest", and its own
    docstring justifies that with "any one of them is the right ancestor".  That
    holds while a generation ships one shape; it stops holding the moment a
    patch to the same generation adds civilizations.  Measured 2026-11-11: VER
    7.8 has four archived builds, three of them with 49 civilizations and one
    with 46, and `297820_10 倍资源文明联盟3倍科技` -- 46 civilizations, built on the
    one with 46 -- was handed a 49-civilization base.  The report then said
    47,991 records were "rewritten whole" and 7,752 were "deleted", which is
    the fingerprint of comparing two unrelated files, not of a mod that edited
    its own.

    The civilization list is the cheapest measurement that separates them and it
    is the one the merge itself depends on: records are addressed by
    (civilization, id), so a base that does not speak the mod's civilization
    names cannot be its parent no matter what its date says.  Score is overlap
    minus names the candidate has and the mod does not, so a superset scores
    below the exact match.
    """
    try:
        sizes = (AR.size_candidates(ver).get('sizes') or {})
    except BaseException:
        return None
    shas = []
    for _size, group in sizes.items():
        for sha in group:
            if sha not in shas:
                shas.append(sha)
    if exclude:
        shas = [s for s in shas if s not in exclude]
    if len(shas) < 2:
        # Nothing to choose between: `pick_base` says the same thing for free.
        return None
    want = _civ_names(mod_raw)
    if not want:
        return None
    best = None
    for sha in shas:
        raw = AR.raw_of(sha)
        if not raw:
            continue
        got = _civ_names(raw)
        if not got:
            continue
        score = len(want & got) - len(got - want)
        if best is None or score > best[0]:
            best = (score, sha, len(raw))
        if score == len(want):
            break
    if best is None:
        return None
    _score, sha, size = best
    raw = AR.raw_of(sha)
    if not raw:
        return None
    return {'sha256': sha, 'raw': raw, 'ver': ver, 'raw_bytes': len(raw),
            'exact_len': False, 'candidates': len(shas)}


def _load_pair(mod_dat, base_dat, new_dat, game_root):
    """Resolve the three streams and say honestly where each came from."""
    mod_raw = _inflate(mod_dat)
    if mod_raw is None:
        raise UpgradeError("读不出这个模组的 .dat：%s" % (mod_dat,))
    new_raw = _inflate(new_dat) if new_dat else None
    new_src = "explicit"
    if new_raw is None:
        root = game_root or GL.find_game_root()
        if not root:
            raise UpgradeError("找不到游戏安装目录，也就拿不到「新版本的官方数据」。"
                               "请显式给 new_dat。")
        path = GL.dat_path(root)
        new_raw = _inflate(path)
        if new_raw is None:
            raise UpgradeError("游戏目录里的 .dat 读不出来：%s" % (path,))
        new_src = "game"
        new_dat = path

    base_raw = _inflate(base_dat) if base_dat else None
    base_src = "explicit"
    base_path = base_dat
    note = None
    if base_raw is None:
        # Ask the index for sizes BEFORE asking for a diff.  `best_base` falls
        # back to a same-generation-but-other-length build when the same-length
        # pool is empty, and that fallback costs 5.7 s plus ~900 MB of region
        # tuples to answer a question we are about to reject anyway.
        ver = _head_ver(mod_raw)
        cands = AR.size_candidates(ver)
        have = cands["sizes"]
        if not have:
            # No archived build of this generation means there is no "before"
            # at all.  The nearest generation is NOT a substitute: VER 7.8 and
            # VER 8.9 do not agree on record layout, so every offset would be
            # fiction.  This is the one refusal that cannot be worked around.
            raise UpgradeError(
                "档案库里还没有 %s 这一代的官方数据。先在更新之前打开一次工具、"
                "跑一次「记录官方数据」，下次更新才有「作者当初改的是什么」"
                "可作依据。" % (ver or "这个版本",))
        # A different LENGTH is not by itself a different parent.  A mod that
        # added its own records is legitimately bigger (measured: 310130 is
        # 94,301,151 raw bytes and carries 7,248 more unit records than the
        # shipped file), and the record-set planner is exactly the path for that.
        # What a length difference DOES forbid is the BYTE path: `diff_regions`
        # across two geometries reports tens of millions of regions meaning
        # "these are two different files", and calling each one an author edit
        # would be fabrication.
        #
        # When the length matches, `best_base` diffs the same-length pool and
        # picks the true ancestor, which is worth its 0.06-0.25 s.  When it does
        # not, no diff can improve on "same generation, newest", and asking
        # `best_base` anyway would spend 5.7 s and ~900 MB of tuples to learn
        # nothing -- so the index alone decides.
        if have.get(len(mod_raw)):
            # Same length, so this is a MEASUREMENT and not a guess:
            # `best_base` diffs every same-length build of this generation and
            # returns the closest one.  Measured 2026-11-11 on the five local
            # fixtures: they differ from the shipped file by 0, 2, 2, 2 and 63
            # bytes, i.e. they ARE built on it.  Forcing a different base made
            # those two-byte edits replay as 1,453 edits and wrote a
            # 93,276,684-byte file that resembled neither stream.
            best = AR.best_base(mod_raw)
            measured = True
        else:
            # A length the shelf does not have does not mean 'any build of
            # this generation will do': the generation can have more than one
            # shape, and the mod's own civilization list is the measurement
            # that tells them apart (see `_pick_base_by_civs`).
            best = _pick_base_by_civs(ver, mod_raw) or AR.pick_base(
                ver, prefer_len=None)
            measured = False
        new_sha = _sha(new_raw)
        mod_sha = _sha(mod_raw)
        # A pick that comes back holding the stream we are carrying the mod ONTO
        # means two very different things, and only one of them is a lie.
        #   * The generation has other archived builds: the diff above compared
        #     them and this one won, so the mod really was built on today's data.
        #     `base == new` below answers "nothing to carry", and that is true.
        #   * It is the ONLY build of its generation: nothing was compared.  The
        #     shelf is filled by this tool at launch, so today is always the
        #     newest entry, and a blind pick lands on it by default.  Then
        #     "already current" is a guess -- the kind that silently leaves the
        #     official changes outside the mod on exactly the day (patch day)
        #     this feature exists for.  Today cannot be its own before: strike it
        #     out and ask again.
        if (best.get("sha256") == new_sha and mod_sha != new_sha
                and not (measured and int(cands.get("entries") or 0) > 1)):
            best = AR.pick_base(ver, prefer_len=len(mod_raw), exclude=[new_sha])
        if best.get("raw") is None and mod_sha != new_sha:
            # Nothing else of this generation is on the shelf.  Then "already
            # current" and "built on a build nobody archived" are the same
            # observation, and they differ by whether the player silently loses
            # the official changes.  Refuse, and name the missing half.
            raise UpgradeError(
                "档案库里 %s 这一代只存了今天这一份官方数据（%s 字节，%s），"
                "而这个模组是 %s 字节、和它不一样。作者当初照着改的那一份"
                "没被存下来，所以「官方改了什么、模组改了什么」分不开。"
                "要是现在硬做，官方的改动会被当成模组已经写过的内容留在门外，"
                "而工具会告诉你「本来就是新版」。两条路：指定 base_dat"
                "（作者当初照着改的那一份官方数据），或者等下一次游戏更新"
                "再适配——那时这一代的前后两份都在档案里，有据可依。"
                % (ver or "这个版本", format(len(new_raw), ","),
                   _head_ver(new_raw) or "未知版本",
                   format(len(mod_raw), ",")))
        if best.get("raw") is not None:
            base_raw = best["raw"]
            base_src = "archive"
            base_path = AR.blob_path(best["sha256"])
            if len(base_raw) == len(mod_raw):
                note = ("基准来自档案库：%s（%s 字节，与模组同代同长）"
                        % (os.path.basename(base_path or ""),
                           format(len(base_raw), ",")))
            else:
                note = ("基准来自档案库：%s（%s 字节）；模组是 %s 字节。"
                        "长度不同说明作者改过记录的增删，所以这次按「记录集合」"
                        "对齐，不按字节位置搬。"
                        % (os.path.basename(base_path or ""),
                           format(len(base_raw), ","),
                           format(len(mod_raw), ",")))
        else:
            raise UpgradeError(
                "不知道这个模组是按哪一版官方数据做的，也就在「改之前是什么」上"
                "没有依据。请指定 base_dat，或者先把官方数据收进档案库"
                "（打开一次工具、跑一次「记录官方数据」就会记下）。")
    if base_src == "explicit" and len(base_raw) != len(mod_raw):
        # An explicit base may differ in length, and that is not an error: a mod
        # that ADDED or REMOVED whole records is legitimately a different size
        # from the file it was built on, and the structural planner is exactly
        # the path that handles it (it compares record key sets, not bytes).
        # Measured on the fixtures: `unit_added_by_mod` is +110,005 bytes and
        # `unit_removed_by_mod` is -957, both of which the planner replays
        # correctly.  The strict rule belongs only to a base we CHOSE for the
        # caller, because there a wrong length really does mean "wrong parent".
        #
        # What this cannot protect against is a caller deliberately handing over
        # an unrelated file; the note makes that visible in the report rather
        # than letting it look like a clean merge.
        note = ("基准是调用方指定的 %s（%s 字节），模组是 %s 字节：长度不同，"
                "按记录集合对齐而不是按字节搬。"
                % (os.path.basename(base_path) if base_path else "base_dat",
                   format(len(base_raw), ","), format(len(mod_raw), ",")))
    return (mod_raw, mod_dat, base_raw, base_path, base_src,
            new_raw, new_dat, new_src, note)


def _frames(base_raw, mod_raw, new_raw):
    """Three frames, sharing one parse when the shapes allow it."""
    base = Frame(base_raw, "base")
    mod = (Frame(mod_raw, "mod", spans_from=base)
           if len(mod_raw) == len(base_raw) and _head_ver(mod_raw) == base.ver
           else Frame(mod_raw, "mod"))
    new = Frame(new_raw, "new")
    return base, mod, new


def _empty_counts():
    return {"edits": 0, "conflicts": 0, "units_added": 0, "units_removed": 0,
            "units_replaced": 0, "techs_added": 0, "techs_removed": 0,
            "techs_replaced": 0,
            "unmapped": 0, "tables_added": 0, "tables_removed": 0,
            "tables_replaced": 0}


# ---------------------------------------------------------------------------
# public: analyze
# ---------------------------------------------------------------------------

def analyze(mod_dat=None, base_dat=None, new_dat=None, game_root=None,
            limit=20000, on_step=None):
    """What would change, and what cannot be carried.  Touches nothing.

    Every difference between the mod and its base is either an ``edit`` (a field
    at a symbolic address), a record add/remove, or an ``unmapped`` row with a
    reason.  ``unmapped`` is the honest half: it is what stops this module from
    shipping a mod that quietly lost a change.
    """
    rep, _frames_kept = _analyze_core(mod_dat, base_dat, new_dat, game_root,
                                      limit, on_step)
    return rep


def _analyze_core(mod_dat=None, base_dat=None, new_dat=None, game_root=None,
                  limit=20000, on_step=None):
    """``(report, frames_or_None)``.

    ``upgrade`` needs the same three frames this builds, and building them is
    the whole cost of an analysis (measured 40 s of a 107 s upgrade was the two
    streams being parsed a second time for no new information).  Returning them
    turns "analyze then re-derive" into "analyze and reuse"; ``analyze`` throws
    them away, so the public shape is unchanged.

    ``on_step(label, fraction)`` is called at every stage boundary with a
    sentence and how far through *this one mod* the work is.  It exists because
    the CHECK parses every installed data mod: 666 s measured for nineteen of
    them (2026-11-10), behind a button that until now showed one static word.  A
    callback cannot report bytes here the way ``unitfields.scan`` does -- the
    cost is spread over three parses, a plan and a port, none of which walk a
    file linearly -- so the stages report *where they are* and the caller turns
    that into a number over all the mods.  A stage that throws must not take the
    analysis down with it: progress is a courtesy, the answer is the product.
    """
    def _step(label, frac):
        if on_step is None:
            return
        try:
            on_step(label, frac)
        except Exception:                # noqa: BLE001
            pass

    _step("读取数据文件", 0.02)
    t0 = time.time()
    (mod_raw, mod_dat, base_raw, base_path, base_src,
     new_raw, new_dat, new_src, base_note) = _load_pair(
        mod_dat, base_dat, new_dat, game_root)
    _step("读完了三份数据文件", 0.12)
    rep = {
        "ok": True,
        "official_wins": False,
        "mod": {"path": mod_dat, "raw_bytes": len(mod_raw),
                "ver": _head_ver(mod_raw), "sha256": _sha(mod_raw)},
        "base": {"path": base_path, "how": base_src,
                 "raw_bytes": len(base_raw), "ver": _head_ver(base_raw),
                 "sha256": _sha(base_raw)},
        "new": {"path": new_dat, "how": new_src, "raw_bytes": len(new_raw),
                "ver": _head_ver(new_raw), "sha256": _sha(new_raw)},
    }
    for key in ("edits", "conflicts", "unmapped"):
        rep[key] = []
    rep["added"] = {"units": [], "techs": []}
    rep["removed"] = {"units": [], "techs": []}
    rep["structural"] = False
    rep["capped"] = False

    if rep["mod"]["sha256"] == rep["new"]["sha256"]:
        rep["verdict"] = IDENTICAL
        rep["counts"] = _empty_counts()
        rep["notes"] = ["这个模组的 .dat 就是现在这版官方数据，不用更新"]
        rep["seconds"] = round(time.time() - t0, 2)
        return rep, None
    if rep["base"]["sha256"] == rep["new"]["sha256"]:
        rep["verdict"] = UP_TO_DATE
        rep["counts"] = _empty_counts()
        rep["notes"] = ["这个模组本来就是按现在这版官方数据做的，"
                        "官方没有变过，不用更新"]
        rep["seconds"] = round(time.time() - t0, 2)
        return rep, None
    if rep["mod"]["ver"] != rep["base"]["ver"]:
        # The mod's own header is the cheapest possible witness that it is not
        # a child of this base: a VER 7.8 body cannot be diffed against a VER
        # 8.9 one byte for byte, and trying it does not fail cleanly -- the
        # parser reads civ pointers out of tech records and dies with
        # `struct.error: bad char in struct format`, which tells the user
        # nothing.  Say which two generations were put together instead.
        rep["verdict"] = IMPOSSIBLE
        rep["counts"] = _empty_counts()
        rep["notes"] = [
            "这个模组的文件头写的是 %s，基准数据是 %s：两者不是同一代记录格式，"
            "偏移不能互相搬。找一份与模组同代的官方数据当基准（base_dat），"
            "或者按作者的意图重建。"
            % (rep["mod"]["ver"], rep["base"]["ver"])]
        rep["seconds"] = round(time.time() - t0, 2)
        return rep, None
    cross_gen = rep["base"]["ver"] != rep["new"]["ver"]
    rep["cross_gen"] = cross_gen

    t = time.time()
    base_f, mod_f, new_f = _frames(base_raw, mod_raw, new_raw)
    rep["seconds_parse"] = round(time.time() - t, 2)
    _step("三份数据都解析完了", 0.22)

    # A civilization the target file spells differently from the one the mod
    # was built on is not a defect: the official file renamed it.  Measured on
    # 297820, where VER 7.8 says `Ethopians` and 8.9 says `Ethiopians`, and on
    # 310130, whose three custom civilizations carry GBK-mangled names.  The
    # pairing is settled by (tech_tree_id, team_bonus_id), the two numbers the
    # game itself uses to decide which civilization a player is, and it has to
    # be known BEFORE planning: records are addressed by (civilization, id),
    # so a name the target does not have turns every record of that civ into
    # an addition on one side and a deletion on the other.
    #
    # Both sides are asked because cross-generation runs read the mod, while a
    # same-generation run can only disagree on the base's spelling.  In that
    # case the plan used to refuse outright (see the note at the top of
    # `_plan_structural`): measured on 15373, merging by name deleted the
    # official `Ethiopians` records and threw away 4,168 of the author's.  With
    # the identity established from the file headers, that merge is now safe.
    alias = dict(_civ_alias(base_f, new_f))
    alias.update(_civ_alias(mod_f, new_f))

    t = time.time()

    # The two expensive stages are the comparison and, when the generations
    # differ, the re-encoding.  Their share of the bar is measured, not guessed
    # (209785, 2026-11-12): load 2.8 s, parse 1.4 s, diff 5.4 s, plan 6.0 s,
    # port 7.2 s, apply 0.5 s.  A bar that gives the comparison the same window
    # whether or not a port follows is wrong by a third of the run.
    _PLAN_LO, _PLAN_HI = 0.22, (0.69 if cross_gen else 0.97)

    def _plan_step(frac):
        # The label stays put while the number moves: a label that rewrites
        # itself twice a second reads as a slot machine.
        _step("比对出作者改了什么",
              _PLAN_LO + (_PLAN_HI - _PLAN_LO) * max(0.0, min(1.0, frac or 0.0)))

    plan = _plan(base_f, mod_f, limit=limit, alias=alias, new=new_f,
                 on_progress=_plan_step)
    rep["seconds_plan"] = round(time.time() - t, 2)
    _step("比对出作者改了什么", _PLAN_HI)

    if alias:
        rep["civ_alias"] = dict(alias)
        plan["notes"].append(_alias_note(alias))

    # Positions the official file has since handed to a different tech cannot
    # be written in place at all, so this runs before the port: a record that
    # is going to travel to a new slot must be encoded as a whole record, not
    # left behind as field edits against a neighbour slot.
    reloc = _relocate_techs(plan, base_f, mod_f, new_f)
    if reloc["count"]:
        rep["techs_relocated"] = reloc["count"]
        rep["relocated"] = reloc["moved"]

    if cross_gen:
        # The check must run the same port the apply will, or the verdict it
        # prints describes a merge nobody is going to perform: without this,
        # every added record sits on an id the new official file has taken,
        # and the check calls a fully carryable mod impossible.
        # The port is the most expensive single stage of a cross-generation
        # check and it is pure per-record work, so it reports from inside its
        # own loop rather than jumping from one boundary to the next.
        t = time.time()
        _PORT_LO, _PORT_HI = 0.69, 0.97

        def _port_step(frac):
            _step("把记录搬进新版本的格式",
                  _PORT_LO + (_PORT_HI - _PORT_LO) * max(0.0, min(1.0, frac or 0.0)))

        rep["port"] = _port_plan(plan, mod_f, new_f, on_progress=_port_step)
        rep["seconds_port"] = round(time.time() - t, 2)
        _step("把记录搬进新版本的格式", _PORT_HI)

    # After the port, never before: the encoder rebuilds a travelling record
    # from the mod's own bytes, so a reference patched earlier would be
    # overwritten with the pre-move number on the way through.
    if reloc.get("map"):
        rep["relocated_refs"] = _repair_tech_refs(plan, mod_f, new_f, reloc)

    # A mod built on an older build of the same generation carries records on
    # ids the target has since taken (310130: 8,431 of them).  Asking the
    # target's own bytes settles each one, and the ones that are the same unit
    # become whole-record replacements instead of refusals.
    rep["clashes"] = _adopt_clashes(plan, base_f, mod_f, new_f)

    # Run on every path, not only cross-generation ones: a same-generation
    # rebuild of a 60-civ build onto the 63-civ one keeps every effect index
    # the author wrote while the target's table has moved on, which is the
    # same fault with a different headline.  It is also cheap -- three table
    # walks and one pass over the technology records.
    t = time.time()
    rep["effects"] = _link_effects(plan, base_f, mod_f, new_f, reloc=reloc)
    rep["seconds_effects"] = round(time.time() - t, 2)

    applied, refused, conflicts, ranges = _apply_edits(
        new_f, plan["edits"], bytearray(new_raw))
    _step("试算能不能搬", 0.99)

    rep["structural"] = plan["structural"]
    rep["edits"] = applied
    rep["conflicts"] = conflicts
    rep["unmapped"] = plan["unmapped"] + refused + port_refused(rep)
    rep["added"] = {
        "units": [{"civ": r["civ"], "unit": r["unit"], "bytes": len(r["bytes"])}
                  for r in plan["add_unit"]],
        "techs": [{"at": r["at"], "bytes": len(r["bytes"])}
                  for r in plan["add_tech"]],
    }
    rep["removed"] = {
        "units": [{"civ": r["civ"], "unit": r["unit"]} for r in plan["del_unit"]],
        "techs": list(plan["del_tech"]),
    }
    rep["counts"] = {
        "edits": len(applied),
        "conflicts": len(conflicts),
        "units_added": len(plan["add_unit"]),
        "units_removed": len(plan["del_unit"]),
        "units_replaced": len(plan["replace"]),
        "techs_added": len(plan["add_tech"]),
        "techs_removed": len(plan["del_tech"]),
        # A tech whose record WIDTH changed is carried as a whole-record copy,
        # not as field edits: its length prefix, its research locations and its
        # costs all move together, and patching the diffs one field at a time
        # wrote string length words without writing the text they announce.
        "techs_replaced": len(plan.get("replace_tech") or []),
        # Flat-table record adds/removes are a different kind of change from a
        # unit add: no civ owns them, and they are counted per record rather
        # than per civilization, so mixing them into `units_added` would make
        # one appended sound look like one new unit.
        "tables_added": len(plan.get("add_table") or []),
        "tables_removed": len(plan.get("del_table") or []),
        "tables_replaced": len(plan.get("replace_table") or []),
        "unmapped": len(rep["unmapped"]),
    }
    # Deleted fields are classified on EVERY run, not only cross-generation
    # ones.  A generation is not a single layout: VER 8.9 shipped as a 60-civ
    # build and later as a 63-civ one, and the unit records changed shape in
    # between (a bird block of 20 task slots became 7).  Measured on 15373,
    # whose mod is VER 8.9 and whose base is VER 8.9, yet 30 author edits land
    # on `Bird.Tasks.18/19.ClassID` -- fields the target build does not have.
    # Classifying only when the generation string differed left those 30 in
    # `unmapped` and the whole mod impossible for no reason.
    _classify_gone(rep, plan, new_f)
    # The counts were taken before the classification, when a deleted field
    # still looked like an unmapped edit.
    rep["counts"]["unmapped"] = len(rep["unmapped"])
    rep["counts"]["gone"] = len(rep.get("port_gone") or [])
    rep["counts"]["port_refused"] = len(port_refused(rep))
    rep["bytes_to_write"] = sum(w for _o, w in ranges)
    # "Capped" means the CHECK stopped counting, so the numbers above are a
    # floor, not a total.  It is deliberately NOT part of the verdict: a cap is
    # a speed knob, and letting it turn into "impossible" is how a 3-problem mod
    # gets reported as a 962-problem one.
    rep["capped"] = bool(plan.get("capped"))
    if rep["unmapped"]:
        rep["verdict"] = IMPOSSIBLE
    elif conflicts:
        rep["verdict"] = CONFLICTS
    else:
        rep["verdict"] = MERGEABLE
    # Notes come from several places and are rendered one line each; a sentence
    # that arrives twice says nothing the first copy did not.
    if cross_gen:
        # Not a refusal any more, but the loudest true sentence in the report:
        # the mod was built against a different generation, and every record
        # this run carries is re-laid-out by field name rather than copied.
        plan["notes"].insert(0,
            "这个模组是按 %s 做的，现在官方是 %s：记录按字段名重新编码到新布局，"
            "不是按字节位置搬。" % (rep["base"]["ver"], rep["new"]["ver"]))
    _notes = []
    for _n in ([base_note] if base_note else []) + list(plan["notes"]):
        if _n not in _notes:
            _notes.append(_n)
    rep["notes"] = _notes
    rep["seconds"] = round(time.time() - t0, 2)
    return rep, (base_f, mod_f, new_f)


# ---------------------------------------------------------------------------
# public: upgrade
# ---------------------------------------------------------------------------

def upgrade(mod_dat=None, out_dir=None, title=None, base_dat=None,
            new_dat=None, game_root=None, install=False, profile_root=None,
            official_wins=False, force=False, limit=20000):
    """Write an updated copy of the mod, carrying every change onto ``new``.

    ``force=True`` ships even when something could not be carried; the report
    still lists it, so "forced" never means "silent".  The default is to refuse,
    because a mod that silently lost one of its own edits is worse than one that
    was not rebuilt at all: the player blames the game, not the tool.
    """
    t0 = time.time()
    rep, kept = _analyze_core(mod_dat=mod_dat, base_dat=base_dat,
                              new_dat=new_dat, game_root=game_root,
                              limit=limit)
    rep["official_wins"] = bool(official_wins)
    if rep["verdict"] in (IDENTICAL, UP_TO_DATE):
        rep["out"] = None
        rep["installed"] = None
        rep["notes"].append("没有写出任何文件（%s）" % rep["verdict"])
        return rep
    if rep["verdict"] == IMPOSSIBLE and not force:
        raise UpgradeError(_why_impossible(rep))

    (mod_raw, mod_dat, base_raw, _bp, _bs,
     new_raw, new_dat, _ns, _base_note) = _load_pair(
        mod_dat, base_dat, new_dat, game_root)

    t = time.time()
    if kept is not None:
        # The frames `_analyze_core` just built address exactly these streams;
        # rebuilding them here used to parse 93 MB twice for no new fact.
        base_f, mod_f, new_f = kept
    else:
        base_f, mod_f, new_f = _frames(base_raw, mod_raw, new_raw)
    # Same rename handling as the check, on the plan this run will actually
    # apply -- the check stops counting at `limit`, the apply may not, so the
    # two plans are separate objects and each needs its own translation.
    alias = dict(_civ_alias(base_f, new_f))
    alias.update(_civ_alias(mod_f, new_f))
    if alias:
        rep["civ_alias"] = dict(alias)
    plan = _plan(base_f, mod_f, limit=0, alias=alias, new=new_f)
    if alias:
        plan["notes"].append(_alias_note(alias))
    rep["seconds_parse"] = round(time.time() - t, 2)

    # The check built its own plan and already ran this, but the plan about to
    # be written is a different object, so the relocation has to be decided
    # again against the plan that will actually be applied.
    reloc = _relocate_techs(plan, base_f, mod_f, new_f)
    if reloc["count"]:
        rep["techs_relocated"] = reloc["count"]
        rep["relocated"] = reloc["moved"]

    if rep.get("cross_gen"):
        t = time.time()
        port = _port_plan(plan, mod_f, new_f)
        rep["port"] = port
        rep["unmapped"] = rep["unmapped"] + port["refused"]
        rep["seconds_port"] = round(time.time() - t, 2)

    if reloc.get("map"):
        rep["relocated_refs"] = _repair_tech_refs(plan, mod_f, new_f, reloc)

    # Same step as the check side, on the plan that will actually be written:
    # the check builds its own plan with `limit`, so the two plans are separate
    # objects and each has to have its clashes settled against the target.
    rep["clashes"] = _adopt_clashes(plan, base_f, mod_f, new_f)

    # The check ran this on its own plan; the plan about to be applied is a
    # different object (the check stops counting at `limit`, the apply does
    # not), so the pointer rewrites and the tail records have to be built again
    # against the one that will actually be written.
    t = time.time()
    rep["effects"] = _link_effects(plan, base_f, mod_f, new_f, reloc=reloc)
    rep["seconds_effects"] = round(time.time() - t, 2)

    t = time.time()
    work = bytearray(new_raw)
    applied, refused, conflicts, ranges = _apply_edits(
        new_f, plan["edits"], work, official_wins=official_wins)
    rep["edits"] = applied
    rep["conflicts"] = conflicts
    rep["unmapped"] = plan["unmapped"] + refused + port_refused(rep)
    rep["seconds_apply"] = round(time.time() - t, 2)

    t = time.time()
    raw_t, tab_done, tab_delta = _apply_tables(new_f, plan, bytes(work))
    rules = list(tab_done["rules"])
    marks = list(tab_done["marks"])
    if tab_done["tables"] or tab_done["refused"]:
        rep["tables"] = tab_done
        rep["seconds_tables"] = round(time.time() - t, 2)
        rep["unmapped"] = rep["unmapped"] + tab_done["refused"]
        work = bytearray(raw_t)

    # Tasks the author added live in `7 UnitHeaders`, which sits after every
    # flat table and before the civilizations.  One splice for the whole
    # header block, exactly like the flat-table rebuild, and its shift joins
    # the table shifts because everything below it moves too.
    t = time.time()
    raw_h, task_done, task_delta = _apply_task_add(new_f, plan, bytes(work))
    if task_done["added"]:
        rep["task_added"] = task_done["added"]
        rep["seconds_tasks"] = round(time.time() - t, 2)
        work = bytearray(raw_h)
    rules = rules + list(task_done["rules"])
    rules.sort()

    if rules:
        # Splicing a table moves every civ and the tech section along with it,
        # because the tables all sit before them.  The edit bytes travelled with
        # the splice (they are just bytes in the same buffer), so only the
        # recorded addresses have to be corrected -- leaving them stale would
        # make the stray check accuse this module of writing where it did not.
        ranges = _shift_ranges(rules, ranges)
        ranges = ranges + [(_shift_after(rules, off), w) for off, w in marks]
        civs_start_2 = _shift_after(rules, new_f.civs_start)
        tail_2 = _shift_after(rules, new_f.tail)
    else:
        civs_start_2, tail_2 = new_f.civs_start, new_f.tail

    expect = None
    if plan["add_unit"] or plan["del_unit"] or plan["replace"] \
            or plan["add_tech"] or plan["del_tech"] or plan["replace_tech"]:
        t = time.time()
        raw2, done, _unused = _apply_records(new_f, plan, work,
                                             civs_start=civs_start_2,
                                             tail=tail_2)
        rep["records"] = done
        rep["seconds_records"] = round(time.time() - t, 2)
        work = bytearray(raw2)
        rep["unmapped"] = rep["unmapped"] + done["refused"]
        # The apply rebuilt `plan` with limit=0, so the check's earlier
        # classification was about a different list -- classify this one.
        # Unconditional for the same reason as the check side: two builds of
        # one generation can disagree on a record's layout.
        _classify_gone(rep, plan, new_f)
        # A record the rebuild refused was not written, so it cannot be part of
        # what the verification expects to find: the id it asked for still holds
        # whatever the official file had there, and comparing that against the
        # author's bytes reported "the module wrote the wrong record" for a
        # record it had honestly declined to write.  Measured on 310130 (8,431
        # refusals, every added id already taken by this build of 8.9): the
        # check raised "32 new records do not match" and buried the real,
        # actionable reason underneath it.
        refused_pairs = set(
            (row["civ"], row["id"]) for row in done["refused"]
            if row.get("civ") and row.get("id") is not None)
        present = set(new_f.unit_keys())
        expect = {
            "units": ((present
                       - set((r["civ"], r["unit"]) for r in plan["del_unit"])
                       | set((r["civ"], r["unit"]) for r in plan["add_unit"]))
                      - set(p for p in refused_pairs if p not in present)),
            # A clash this run settled by whole-record replacement is checked
            # the same way an addition is: after the rebuild, that id must hold
            # the author's bytes exactly.  Leaving it out would let the one
            # stage that moves the author's records write anything at all.
            "added": ([r for r in plan["add_unit"]
                       if (r["civ"], r["unit"]) not in refused_pairs]
                      + [r for r in plan["replace"] if r.get("adopted")]),
        }

    t = time.time()
    # Which table walks are proof here and which are ceremony: a range that
    # does not reach a table's bytes cannot have broken that table's walk.
    reached = [t for t in ("graphic", "sound", "effect", "terrain", "task",
                           "colour")
               if _regions_touch_table(new_f, t, ranges)]
    # A table this run rebuilt has to be re-walked no matter what the edit
    # ranges say: the point of the walk is "the section still ends exactly where
    # the count says it does", and an append is precisely how that can break.
    for row in (tab_done.get("tables") or []):
        if row.get("table") and row["table"] not in reached:
            reached.append(row["table"])
    ver = _verify(bytes(work), new_raw, ranges, expect=expect,
                  tables=reached)
    rep["verify"] = ver
    rep["seconds_verify"] = round(time.time() - t, 2)

    if not ver["ok"] and not force:
        raise UpgradeError(
            "重建出来的数据没通过自检：%s。为了不让你拿到一个坏模组，"
            "这次没有写出任何文件。" % _verify_why(ver))
    if rep["unmapped"] and not force:
        raise UpgradeError(_why_unmapped(rep))

    raw_out = bytes(work)
    rep["out_raw_bytes"] = len(raw_out)
    rep["out_sha256"] = _sha(raw_out)

    if out_dir is None:
        out_dir = tempfile.mkdtemp(prefix="dsh_upgrade_")
    name = title or _title_of(mod_dat)
    mod_dir = _emit(out_dir, raw_out, name, rep, _mod_dir_of(mod_dat), rep)
    rep["out"] = {"mod_dir": mod_dir, "dat": _dat_of(mod_dir),
                  "dat_bytes": (os.path.getsize(_dat_of(mod_dir))
                                if os.path.isfile(_dat_of(mod_dir)) else None)}
    rep["installed"] = None
    if install:
        rep["installed"] = _install(mod_dir, name, profile_root)
    rep["seconds"] = round(time.time() - t0, 2)
    return rep


def _mod_dir_of(mod_dat):
    """The mod's own folder: the nearest ancestor holding an ``info.json``."""
    d = os.path.dirname(os.path.abspath(mod_dat or ""))
    while True:
        if os.path.isfile(os.path.join(d, "info.json")):
            return d
        parent = os.path.dirname(d)
        if not parent or parent == d:
            return None
        d = parent


def _author_text(src_mod_dir, fallback_title):
    """The author's own Title / Author / Description, or honest placeholders.

    Rebuilding a mod used to overwrite all three with this tool's own sentence,
    so a player who adapted someone else's mod lost the description that told
    them what they had just installed (reported 2026-11-14: `209785` came back
    with "由「一键适配新版本」重建：..." as its 简介).  The rebuild changes the
    `.dat`; it has no business renaming the author's work.

    Two of the values in shipped `info.json` files are the ENGINE's placeholders
    rather than anything a human wrote -- `Author: "Unpublished"` and
    `Description: "No Description"` (measured on `15373_Multiple Buffs Mod v1`
    and `19968_Eternal Civilization`).  Keeping those would be worse than
    writing our own sentence, so they fall through to the fallback.
    """
    from . import emitter as E
    info = {}
    if src_mod_dir and os.path.isdir(src_mod_dir):
        info = E.read_info_soft(os.path.join(src_mod_dir, "info.json"))
    title = str(info.get("Title") or "").strip()
    if not title or E.title_bytes(title) > E.TITLE_MAX_BYTES:
        title = fallback_title
    author = str(info.get("Author") or "").strip()
    if not author or author == "Unpublished":
        author = "dsh"
    desc = str(info.get("Description") or "")
    if not desc.strip() or desc.strip() == "No Description":
        desc = ""
    return {"Title": title, "Author": author, "Description": desc}


def _emit(out_dir, raw_out, title, rep, src_mod_dir, _again=None):
    """Write the mod folder, carrying the author's non-.dat files across.

    The ``.dat`` is the merged stream; everything else in the mod (art, strings,
    UI json) is the author's own work and is copied verbatim.  Losing those is
    exactly the kind of half-done update this module exists to avoid, so
    ``carry_over`` runs even when it finds nothing.
    """
    from . import emitter as E
    from .. import repair as Rr
    mod_dir = os.path.join(out_dir, _safe_name(title))
    keep = _author_text(src_mod_dir, title)
    desc = keep["Description"]
    if not desc:
        desc = ("由「一键适配新版本」重建：搬了 %d 处字段改动，"
                "新增记录 %d 条，基准来自 %s"
                % (rep["counts"]["edits"], rep["counts"]["units_added"],
                   os.path.basename(rep["base"]["path"] or "?")))
    info = E.make_info(keep["Title"], author=keep["Author"], description=desc)
    rep["info"] = {"Title": keep["Title"], "Author": keep["Author"],
                   "Description": desc,
                   "description_kept": bool(keep["Description"])}
    man = E.emit_data_mod(mod_dir, raw_out, info, overwrite=True)
    mod_dir = man.get("mod_dir") or mod_dir
    notes = []
    if src_mod_dir and os.path.isdir(src_mod_dir):
        Rr.carry_over(src_mod_dir, mod_dir, log=notes)
    rep.setdefault("notes", []).extend(
        "带上原模组的文件：%s" % n for n in notes)
    # The caller needs the manifest to record this build's origin: without it the
    # next patch cannot tell "official data moved under my mod" from "my mod was
    # never rebuilt", and the one-click update would have to guess.
    rep["manifest"] = man
    return mod_dir


def _install(mod_dir, title, profile_root):
    from .. import api as A
    tk = A.open_toolkit()
    # No `describe()` here: it takes an entity id and renders one unit, and
    # calling it with nothing raised `TypeError: missing 1 required positional
    # argument` on the very first install attempt.  `install()` reaches
    # `self._ensure()` itself.
    return tk.install(mod_dir, name=_safe_name(title or "upgrade"),
                      title=title, enabled=True, profile_root=profile_root,
                      overwrite=True)


def _dat_of(mod_dir):
    return os.path.join(mod_dir, DAT_REL)


def _title_of(mod_dat):
    d = _mod_dir_of(mod_dat)
    if d:
        return os.path.basename(d)
    return "upgraded mod"


def _safe_name(title):
    bad = '\\/:*?"<>|'
    out = "".join("_" if c in bad else c for c in (title or "mod")).strip()
    return out or "mod"


# ---------------------------------------------------------------------------
# human-facing sentences
# ---------------------------------------------------------------------------

def _why_impossible(rep):
    # Rows that could not be carried come FIRST, even though a note is usually
    # the pleasanter sentence.  A note can be bookkeeping -- "the base came from
    # the archive, and it is a different size" -- and returning that as the
    # refusal tells the user where the base came from while leaving out the
    # thing that actually stopped the run.  Measured: a real third-party mod
    # with 962 uncarried rows refused with "基准来自档案库：…" and never named a
    # single one of them.
    if rep.get("unmapped"):
        head = _why_unmapped(rep)
        if rep["notes"]:
            return head + "（" + rep["notes"][0] + "）"
        return head
    if rep["notes"]:
        return rep["notes"][0]
    return "这个模组的改动没法按字节搬到新版本上"


def _why_unmapped(rep):
    rows = rep.get("unmapped") or []
    if not rows:
        return "没有搬不过去的改动"
    head = "；".join("%s（%s）" % (r.get("why") or "说不清", _where(r))
                    for r in rows[:4])
    more = "" if len(rows) <= 4 else "，另有 %d 处" % (len(rows) - 4)
    return ("有 %d 处改动搬不过去：%s%s。这些不会悄悄丢掉，也不会被猜着搬。"
            "确认可以放弃它们时，用 force 再跑一次。"
            % (len(rows), head, more))


def _where(row):
    bits = []
    for k in ("space", "civ", "unit", "index", "field"):
        v = row.get(k)
        if v not in (None, ""):
            bits.append("%s=%s" % (k, v))
    if row.get("key"):
        bits.append("key=%s" % (row["key"],))
    if row.get("off") is not None:
        bits.append("@%d" % row["off"])
    return " ".join(bits) or "位置不明"


def _verify_why(ver):
    bits = []
    if ver.get("parse_leftover"):
        bits.append("还有 %d 字节没解析完" % ver["parse_leftover"])
    if ver.get("stray_count"):
        bits.append("%d 处字节改动不在计划内" % ver["stray_count"])
    for t, left in (ver.get("tables") or {}).items():
        if left:
            bits.append("「%s」表还剩 %s 字节" % (t, left))
    if ver.get("contiguous") is False:
        bits.append("文明块接不上")
    if ver.get("tail_ok") is False:
        bits.append("文明区结尾和科技区起点对不上")
    if ver.get("units_missing"):
        bits.append("少了 %d 条记录" % len(ver["units_missing"]))
    if ver.get("units_extra"):
        bits.append("多了 %d 条记录" % len(ver["units_extra"]))
    if ver.get("added_bad"):
        bits.append("%d 条新增记录字节对不上" % len(ver["added_bad"]))
    return "、".join(bits) or "自检失败"


def describe(rep):
    """A few Chinese lines a panel can print without knowing the report shape."""
    lines = []
    c = rep.get("counts") or {}
    lines.append("判定：%s" % (rep.get("verdict") or "?"))
    lines.append("要搬的改动：%d 处字段" % (c.get("edits") or 0))
    if c.get("units_added") or c.get("units_removed") or c.get("units_replaced"):
        lines.append("记录：新增 %d、删除 %d、整条替换 %d"
                     % (c.get("units_added") or 0, c.get("units_removed") or 0,
                        c.get("units_replaced") or 0))
    if c.get("techs_replaced"):
        lines.append("整条照抄的科技：%d 条（作者改过它们的长度）"
                     % c["techs_replaced"])
    if c.get("techs_added") or c.get("techs_removed"):
        lines.append("科技：新增 %d、删除 %d"
                     % (c.get("techs_added") or 0, c.get("techs_removed") or 0))
    if rep.get("techs_relocated"):
        # A tech whose slot the official file has since reused is neither "in
        # place" nor "added": it moved to the tail so that the official tech
        # keeps its own slot.  Saying the number, and that the references were
        # followed, is what makes the report honest about where they went.
        lines.append("科技换了位置：%d 条（原来那几个槽位官方已经另作他用，"
                     "整条搬到表尾；%d 处前置引用跟着改了指）"
                     % (rep["techs_relocated"], rep.get("relocated_refs") or 0))
    eff = rep.get("effects") or {}
    only_effects = (eff.get("appended") == (c.get("tables_added") or 0)
                    and not (c.get("tables_removed") or 0))
    if (c.get("tables_added") or c.get("tables_removed")) and not only_effects:
        # A table row is not a unit: no civ owns it and there is no record
        # header, so it gets its own line rather than being folded into the
        # record count above.  When every added row is an effect record the
        # line below already says it, in the words that matter for an effect
        # table (positions), so this one would only restate the number.
        lines.append("音效/图形/效果表：新增 %d 条、删除 %d 条"
                     % (c.get("tables_added") or 0, c.get("tables_removed") or 0))
    if c.get("tables_replaced"):
        # A record copied whole is a promise the author can check: those bytes
        # are in the output, unedited by this tool.  It used to be counted and
        # never printed, so "tables_replaced: 99" in the JSON had no sentence in
        # the panel -- and a replacement the writer skipped (terrain, colour)
        # looked exactly like one it wrote.
        lines.append("整条照抄的表记录：%d 条（作者把它们改长了，或改动落在没有字段名"
                     "的字节上）" % c["tables_replaced"])
    if eff.get("out"):
        # An effect record has no id at all -- the technology's EffectID field
        # is what points at it. So "how many effects came over" is not the
        # number that decides whether the port worked; the pointers are.
        lines.append("科技效果：目标表 %d 条原样留着，作者的 %d 条接在后面，共 %d 条；"
                     "%d 个科技的效果编号跟着改了位置"
                     % (eff.get("new") or 0, eff.get("appended") or 0,
                        eff.get("out") or 0, eff.get("pointers") or 0))
        if eff.get("overflow"):
            lines.append("效果编号溢出：%d 个（这张表装不下这么多条）" % eff["overflow"])
    cl = rep.get("clashes") or {}
    if cl.get("adopted") or cl.get("same_bytes"):
        # An "addition" that lands on an id the target already uses is not an
        # addition; saying how it was settled is the difference between "the
        # author's edit is in" and "the author's edit was dropped quietly".
        lines.append("编号撞车：%d 条落在目标已用的编号上，其中 %d 条同名同号"
                     "（按整条替换写进原槽）、%d 条本来就一模一样"
                     % (cl.get("clashes") or 0, cl.get("adopted") or 0,
                        cl.get("same_bytes") or 0))
    if rep.get("capped"):
        # "counts are a floor" has to be said out loud, or a capped check reads
        # as a complete inventory of a smaller change.
        lines.append("这次只数到这里（上限到了，实际改动只会更多）")
    if c.get("conflicts"):
        lines.append("官方也改过同一处：%d 处（%s）"
                     % (c["conflicts"],
                        "按官方" if rep.get("official_wins") else "按你的改法"))
    if c.get("unmapped"):
        lines.append("搬不过去：%d 处（已在报告里逐条列出）" % c["unmapped"])
    if c.get("gone"):
        # Not a failure: the target build deleted the field the author edited.
        # Silence here would make the edit look like it vanished on its own.
        lines.append("新版本已经删掉的字段：%d 处（作者改的是这些格子，新版没有它们）"
                     % c["gone"])
    if rep.get("cross_gen"):
        lines.append("跨代：模组是按 %s 做的，目标 %s 的记录布局不同；"
                     "已按字段名逐条重新编码，不是按字节位置搬"
                     % (rep["base"]["ver"], rep["new"]["ver"]))
    if rep.get("verify"):
        lines.append("自检：%s" % ("通过" if rep["verify"].get("ok")
                                   else "没通过"))
    if rep.get("out"):
        lines.append("输出：%s" % rep["out"].get("mod_dir"))
    if rep.get("installed"):
        lines.append("已安装：%s" % (rep["installed"],))
    lines.append("耗时：%s 秒" % rep.get("seconds"))
    return "\n".join(lines)

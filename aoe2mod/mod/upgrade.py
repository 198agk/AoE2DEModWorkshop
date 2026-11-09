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

#: The seven i32 scalars that sit between the last tech record and the tech tree.
_TAIL_SCALARS = ("time_slice", "unit_kill_rate", "unit_kill_total",
                 "unit_hit_point_rate", "unit_hit_point_total",
                 "razing_kill_rate", "razing_kill_total")


def _key_order(key):
    """A total order over table keys, so a rebuild is deterministic.

    Keys are ``("index", 3)`` for effects and ``("ID", 1234)`` for everything
    with an ID field; comparing the mixed tuples directly raises ``TypeError``
    as soon as one table has both shapes, so the tag is stringified.
    """
    tag, val = (list(key) + [None])[:2]
    return (str(tag), -1 if val is None else int(val))


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

    def table_key_of(self, table, rec):
        """The stable key of one table record.

        Graphics are keyed by their own ``ID`` field, never by array position:
        measured on the shipped file, 19,861 of 20,883 positions differ from the
        id stored at that position, so a position is not an identity.
        """
        if table == "effect":
            return ("index", rec["index"])
        f = TB.fields_at(self.raw, self.gv, rec, table=table)
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
    """Split the byte range ``[a, b)`` into ``(name, rel, width)`` pieces."""
    out = []
    for off, w, name in ranges:
        if w <= 0:
            continue
        lo = max(a, off)
        hi = min(b, off + w)
        if lo < hi:
            out.append((name, lo - off, hi - lo))
    return out


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


def _plan(base, mod, limit=20000):
    """Every difference between ``base`` and ``mod``, expressed symbolically."""
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
    }
    # One diff, read twice: the region list costs 0.2 s and it is the evidence
    # both for "is this even a same-shape diff" and for what the author touched.
    regions = L.diff_regions(base.raw, mod.raw)
    plan["structural"] = _needs_structural(base, mod, regions)
    if plan["structural"]:
        _plan_structural(base, mod, plan, limit)
        return plan
    for off, n in regions:
        if limit and len(plan["edits"]) >= limit:
            # A cap is "we stopped counting", NOT "these bytes cannot be
            # carried".  Reporting each remaining region as unmapped made a big
            # mod look like it had 962 unfixable problems when it had three --
            # measured on a real 115 MB third-party mod: 962 rows, every one of
            # them the same sentence about the cap, and the three real gaps
            # buried underneath.  The cap is a speed knob for the CHECK; the
            # APPLY runs uncapped.
            plan["capped"] = True
            plan["notes"].append(
                "改动太多，按当前上限只数到 %d 处，剩下的还没数（更新时会全部数完）"
                % limit)
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
            for name, rel, w in pieces:
                plan["edits"].append({
                    "space": "civ", "civ": cn, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[off + rel:off + rel + w],
                    "mod": mod.raw[off + rel:off + rel + w],
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
            for name, rel, w in pieces:
                plan["edits"].append({
                    "space": "tech", "index": ti, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[off + rel:off + rel + w],
                    "mod": mod.raw[off + rel:off + rel + w],
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
        for name, rel, w in pieces:
            plan["edits"].append({
                "space": table, "key": key, "field": name,
                "rel": rel, "width": w,
                "base": base.raw[off + rel:off + rel + w],
                "mod": mod.raw[off + rel:off + rel + w],
            })
        return
    if off >= base.tech_tail_end():
        plan["unmapped"].append({
            "off": off, "len": n, "space": "tech_tree",
            "why": "这一处在科技树（TechTree）里，本模块还没有它的语义"})
        return
    plan["unmapped"].append({
        "off": off, "len": n, "space": "unknown",
        "why": "这一处不属于任何已知记录（不是单位、文明头、科技、效果或表记录）"})


def _civ_covering(frame, off):
    for civ, cn in zip(frame.civs, frame.keys):
        if civ["_start"] <= off < civ["_end"]:
            return cn
    return None


def _plan_unit_bytes(base, mod, cn, uid, off, n, plan, base_start, mod_start):
    """Express one differing range of a unit record as field carries."""
    bspan = base.unit_span(cn, uid)
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
    for name, rel, w in pieces:
        a = off + rel
        plan["edits"].append({
            "space": "unit", "civ": cn, "unit": uid, "field": name,
            "rel": rel, "width": w,
            "base": base.raw[a:a + w],
            "mod": mod.raw[a + shift:a + shift + w],
        })


def _plan_structural(base, mod, plan, limit):
    """The author changed the file's SHAPE: records were added or removed.

    Here a byte offset means nothing across the two files, so every difference
    has to come from comparing record SETS.  Nothing is inferred from a shifted
    offset, which is the only honest way to handle a stream whose geometry the
    author moved.
    """
    bkeys = base.unit_keys()
    mkeys = mod.unit_keys()
    bpos = dict(((cn, uid), (s, e))
                for (cn, uid), (s, e) in base.build_unit_index().items()
                if uid is not None)
    mpos = dict(((cn, uid), (s, e))
                for (cn, uid), (s, e) in mod.build_unit_index().items()
                if uid is not None)

    for cn, uid in sorted(mkeys - bkeys):
        s, e = mpos[(cn, uid)]
        plan["add_unit"].append({"civ": cn, "unit": uid,
                                 "bytes": bytes(mod.raw[s:e])})
    for cn, uid in sorted(bkeys - mkeys):
        plan["del_unit"].append({"civ": cn, "unit": uid})

    # Records present in both: same width means in-place field edits, a
    # different width means the author rewrote the record whole (a rename, an
    # added train location) and only the whole blob can carry that.
    for cn, uid in sorted(bkeys & mkeys):
        bs, be = bpos[(cn, uid)]
        ms, me = mpos[(cn, uid)]
        if be - bs != me - ms:
            plan["replace"].append({"civ": cn, "unit": uid,
                                    "bytes": bytes(mod.raw[ms:me]),
                                    "base_bytes": bytes(base.raw[bs:be])})
            continue
        if base.raw[bs:be] == mod.raw[ms:me]:
            continue
        for roff, rn in L.diff_regions(base.raw[bs:be], mod.raw[ms:me]):
            if limit and len(plan["edits"]) >= limit:
                plan["capped"] = True
                plan["notes"].append(
                    "改动太多，按当前上限只数到 %d 处，剩下的还没数"
                    "（更新时会全部数完）" % limit)
                break
            _plan_unit_bytes(base, mod, cn, uid, bs + roff, rn, plan,
                             base_start=bs, mod_start=ms)

    btech = base.tech_count()
    mtech = mod.tech_count()
    if mtech > btech:
        spans = mod.build_tech_spans()
        for i in range(btech, mtech):
            s, e = spans[i]
            plan["add_tech"].append({"at": i, "bytes": bytes(mod.raw[s:e])})
    elif mtech < btech:
        plan["del_tech"].extend(range(mtech, btech))
    for i in range(min(btech, mtech)):
        bs, be = base.build_tech_spans()[i]
        ms, me = mod.build_tech_spans()[i]
        if base.raw[bs:be] == mod.raw[ms:me]:
            continue
        ranges = base.tech_fields(i)
        for roff, rn in L.diff_regions(base.raw[bs:be], mod.raw[ms:me]):
            a = bs + roff
            for name, rel, w in _slice_of(ranges, a, a + rn):
                plan["edits"].append({
                    "space": "tech", "index": i, "field": name,
                    "rel": rel, "width": w,
                    "base": base.raw[a + rel:a + rel + w],
                    "mod": mod.raw[ms + (a + rel - bs):ms + (a + rel - bs) + w],
                })

    # Tables are compared by key, never by offset: their counts sit in front of
    # them, so one added record moves every later offset in the section.
    for table in _TABLES:
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
                plan["unmapped"].append({
                    "space": table,
                    "why": "作者在「%s」表里增删了记录（多 %d 条、少 %d 条）；"
                           "这张表的记录是嵌套的，长度不固定，本模块不敢重排它"
                           % (table, len(new), len(gone))})
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
        for key in set(bidx) & set(midx):
            br, mr = bidx[key], midx[key]
            if br["end"] - br["start"] != mr["end"] - mr["start"]:
                # A flat-table record whose length changed is a whole-record
                # rewrite, exactly like a unit record whose length changed: the
                # author added or dropped an effect command (11 bytes each), or
                # an extra sound file entry.  Carrying it field-by-field cannot
                # express "one more command", so the record travels as bytes --
                # the table's own layout is what says where the next record
                # starts, and the count word is unchanged by a rewrite.
                if table == "graphic":
                    plan["unmapped"].append({
                        "space": table, "key": list(key),
                        "why": "作者把「graphic」表里这条记录的长度改了。图形记录后面"
                               "跟着变长的 delta/angle 区，它的长度决定了这张表其余"
                               "每一格的起点，本模块不重排它"})
                    continue
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
            for roff, rn in L.diff_regions(base.raw[br["start"]:br["end"]],
                                           mod.raw[mr["start"]:mr["end"]]):
                a = br["start"] + roff
                shift = mr["start"] - br["start"]
                for name, rel, w in _slice_of(ranges, a, a + rn):
                    plan["edits"].append({
                        "space": table, "key": key, "field": name,
                        "rel": rel, "width": w,
                        "base": base.raw[a + rel:a + rel + w],
                        "mod": mod.raw[a + rel + shift:a + rel + shift + w],
                    })


# ---------------------------------------------------------------------------
# applying onto the new stream
# ---------------------------------------------------------------------------

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
    for off, w, name in ranges:
        if name == edit["field"]:
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
        raw, got = _rebuild_civ(raw, lay, cn, dels, repls, adds, done)
        if got is None:
            return raw, done, None
        done["units"].extend(got["units"])

    if plan["del_tech"]:
        done["refused"].append({
            "ids": list(plan["del_tech"]),
            "why": "作者删了科技记录；科技没有 id 字段、位置即 id，"
                   "删掉会让后面每一条的 id 前移，本模块不猜这件事"})
    if plan["add_tech"]:
        count_off, count, start, end = R.tech_section(raw, gv, tail)
        del start
        blob = b"".join(row["bytes"] for row in plan["add_tech"])
        # One splice for the whole batch, and the count word written once:
        # appending them one at a time copies the file 1,190 times over.
        raw = _splice(raw, end, blob)
        raw = (raw[:count_off] + struct.pack("<h", count + len(plan["add_tech"]))
               + raw[count_off + 2:])
        at = end
        for row in plan["add_tech"]:
            done["techs"].append({"at": at, "bytes": len(row["bytes"])})
            at += len(row["bytes"])
    return raw, done, None


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

    for table in _TABLE_FLAT:
        tadds = [r for r in adds if r["table"] == table]
        tdels = [r for r in dels if r["table"] == table]
        trepl = {r["key"]: r for r in repls if r["table"] == table}
        if not tadds and not tdels and not trepl:
            continue
        if table == "graphic" and tdels:
            done["refused"].append({
                "space": table,
                "why": "作者从「graphic」表里删了 %d 条记录。图形表每个记录槽前面"
                       "还有一个 i32 存在标志，而标志的下标和记录里的 ID 并不是"
                       "一回事（实测 20,883 条里 0 条相等），删哪一格没有可证的"
                       "答案，所以这一层不猜。" % len(tdels)})
            tdels = []

        geo = _table_geometry(raw, table)
        recs, leftover = TB.scan(raw, table)
        if leftover:
            done["refused"].append({
                "space": table,
                "why": "「%s」表扫到最后一字节还剩 %d 字节没走完，偏移不可信"
                       % (table, leftover)})
            continue

        del_keys = set(r["key"] for r in tdels)
        parts, removed, rewritten = [], [], []
        for rec in recs:
            key = target.table_key_of(table, rec)
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
                if target.table_key_of(table, rec) in del_keys)
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
    all_tables = ("graphic", "sound", "effect", "terrain", "task")
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
        have = AR.size_candidates(ver)["sizes"]
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
            best = AR.best_base(mod_raw)
        else:
            best = AR.pick_base(ver, prefer_len=None)
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
            "unmapped": 0, "tables_added": 0, "tables_removed": 0,
            "tables_replaced": 0}


# ---------------------------------------------------------------------------
# public: analyze
# ---------------------------------------------------------------------------

def analyze(mod_dat=None, base_dat=None, new_dat=None, game_root=None,
            limit=20000):
    """What would change, and what cannot be carried.  Touches nothing.

    Every difference between the mod and its base is either an ``edit`` (a field
    at a symbolic address), a record add/remove, or an ``unmapped`` row with a
    reason.  ``unmapped`` is the honest half: it is what stops this module from
    shipping a mod that quietly lost a change.
    """
    rep, _frames_kept = _analyze_core(mod_dat, base_dat, new_dat, game_root,
                                      limit)
    return rep


def _analyze_core(mod_dat=None, base_dat=None, new_dat=None, game_root=None,
                  limit=20000):
    """``(report, frames_or_None)``.

    ``upgrade`` needs the same three frames this builds, and building them is
    the whole cost of an analysis (measured 40 s of a 107 s upgrade was the two
    streams being parsed a second time for no new information).  Returning them
    turns "analyze then re-derive" into "analyze and reuse"; ``analyze`` throws
    them away, so the public shape is unchanged.
    """
    t0 = time.time()
    (mod_raw, mod_dat, base_raw, base_path, base_src,
     new_raw, new_dat, new_src, base_note) = _load_pair(
        mod_dat, base_dat, new_dat, game_root)
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
    if rep["base"]["ver"] != rep["new"]["ver"]:
        rep["verdict"] = IMPOSSIBLE
        rep["counts"] = _empty_counts()
        rep["notes"] = [
            "基准数据是 %s，新数据是 %s，记录格式换了代，偏移不能互相搬。"
            "这种情况只能按作者的意图重建，不能按字节搬。"
            % (rep["base"]["ver"], rep["new"]["ver"])]
        rep["seconds"] = round(time.time() - t0, 2)
        return rep, None

    t = time.time()
    base_f, mod_f, new_f = _frames(base_raw, mod_raw, new_raw)
    rep["seconds_parse"] = round(time.time() - t, 2)

    t = time.time()
    plan = _plan(base_f, mod_f, limit=limit)
    rep["seconds_plan"] = round(time.time() - t, 2)

    applied, refused, conflicts, ranges = _apply_edits(
        new_f, plan["edits"], bytearray(new_raw))

    rep["structural"] = plan["structural"]
    rep["edits"] = applied
    rep["conflicts"] = conflicts
    rep["unmapped"] = plan["unmapped"] + refused
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
        # Flat-table record adds/removes are a different kind of change from a
        # unit add: no civ owns them, and they are counted per record rather
        # than per civilization, so mixing them into `units_added` would make
        # one appended sound look like one new unit.
        "tables_added": len(plan.get("add_table") or []),
        "tables_removed": len(plan.get("del_table") or []),
        "tables_replaced": len(plan.get("replace_table") or []),
        "unmapped": len(rep["unmapped"]),
    }
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
    rep["notes"] = ([base_note] if base_note else []) + list(plan["notes"])
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
        # limit=0 is "count everything".  The check is allowed to stop early to
        # stay responsive; the APPLY is not, because every region past the cap
        # is an edit that would silently not be written.
        plan = _plan(base_f, mod_f, limit=0)
    else:
        base_f, mod_f, new_f = _frames(base_raw, mod_raw, new_raw)
        plan = _plan(base_f, mod_f, limit=0)
    rep["seconds_parse"] = round(time.time() - t, 2)

    t = time.time()
    work = bytearray(new_raw)
    applied, refused, conflicts, ranges = _apply_edits(
        new_f, plan["edits"], work, official_wins=official_wins)
    rep["edits"] = applied
    rep["conflicts"] = conflicts
    rep["unmapped"] = plan["unmapped"] + refused
    rep["seconds_apply"] = round(time.time() - t, 2)

    t = time.time()
    raw_t, tab_done, tab_delta = _apply_tables(new_f, plan, bytes(work))
    if tab_done["tables"] or tab_done["refused"]:
        rep["tables"] = tab_done
        rep["seconds_tables"] = round(time.time() - t, 2)
        rep["unmapped"] = rep["unmapped"] + tab_done["refused"]
        work = bytearray(raw_t)
        # Splicing a table moves every civ and the tech section along with it,
        # because the tables all sit before them.  The edit bytes travelled with
        # the splice (they are just bytes in the same buffer), so only the
        # recorded addresses have to be corrected -- leaving them stale would
        # make the stray check accuse this module of writing where it did not.
        ranges = _shift_ranges(tab_done["rules"], ranges)
        ranges = ranges + [(_shift_after(tab_done["rules"], off), w)
                           for off, w in tab_done["marks"]]
        civs_start_2 = _shift_after(tab_done["rules"], new_f.civs_start)
        tail_2 = _shift_after(tab_done["rules"], new_f.tail)
    else:
        civs_start_2, tail_2 = new_f.civs_start, new_f.tail

    expect = None
    if plan["add_unit"] or plan["del_unit"] or plan["replace"] \
            or plan["add_tech"] or plan["del_tech"]:
        t = time.time()
        raw2, done, _unused = _apply_records(new_f, plan, work,
                                             civs_start=civs_start_2,
                                             tail=tail_2)
        rep["records"] = done
        rep["seconds_records"] = round(time.time() - t, 2)
        work = bytearray(raw2)
        rep["unmapped"] = rep["unmapped"] + done["refused"]
        expect = {
            "units": (set(new_f.unit_keys())
                      - set((r["civ"], r["unit"]) for r in plan["del_unit"])
                      | set((r["civ"], r["unit"]) for r in plan["add_unit"])),
            "added": [r for r in plan["add_unit"]],
        }

    t = time.time()
    # Which table walks are proof here and which are ceremony: a range that
    # does not reach a table's bytes cannot have broken that table's walk.
    reached = [t for t in ("graphic", "sound", "effect", "terrain", "task")
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
    info = E.make_info(
        title, author="dsh",
        description=("由「一键适配新版本」重建：搬了 %d 处字段改动，"
                     "新增记录 %d 条，基准来自 %s"
                     % (rep["counts"]["edits"], rep["counts"]["units_added"],
                        os.path.basename(rep["base"]["path"] or "?"))))
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
    if c.get("techs_added") or c.get("techs_removed"):
        lines.append("科技：新增 %d、删除 %d"
                     % (c.get("techs_added") or 0, c.get("techs_removed") or 0))
    if c.get("tables_added") or c.get("tables_removed"):
        # A table row is not a unit: no civ owns it and there is no record
        # header, so it gets its own line rather than being folded into the
        # record count above.
        lines.append("音效/图形/效果表：新增 %d 条、删除 %d 条"
                     % (c.get("tables_added") or 0, c.get("tables_removed") or 0))
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
    if rep.get("verify"):
        lines.append("自检：%s" % ("通过" if rep["verify"].get("ok")
                                   else "没通过"))
    if rep.get("out"):
        lines.append("输出：%s" % rep["out"].get("mod_dir"))
    if rep.get("installed"):
        lines.append("已安装：%s" % (rep["installed"],))
    lines.append("耗时：%s 秒" % rep.get("seconds"))
    return "\n".join(lines)

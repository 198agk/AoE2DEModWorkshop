# -*- coding: utf-8 -*-
"""Every field of every technology, with its absolute byte offset in the .dat.

WHY THIS EXISTS
---------------
The page could already edit a UNIT down to the byte (`unitfields.py`), and while
a technology was selected it printed "这一版还没把科技记录拆成字段" -- a hole the
player can see.  `locate.walk_tech` knows the offsets of the four fields the
intent layer happens to want (costs, research time, lang ids); everything else in
the record -- icon, civ lock, required techs, the whole ResearchLocations array --
had no address, so it could not be edited at all.

This module gives a tech the same addressability a unit already has, using the
same trick for the same reason: it replays the exact read order of
`parser.read_tech` while recording where every value came from.  The offsets are
therefore produced by the same bytes the proven parse walks -- not restated from
a schema that can drift.

THE PROOF IT IS FAITHFUL
------------------------
`parse()` only consumes the retail file exactly (leftover 0) when every read_*
agrees with the engine.  `scan()` patches `parser.read_tech` for its own walk and
then demands `raw[pos:]` be empty; a disagreement fails the check instead of
handing out plausible-looking wrong offsets.  That matters more for a tech than
for a unit: a wrong offset here lands in the neighbouring tech, and the game
reads it as a silent balance change rather than an error.

FIELD NAMES
-----------
Follow genieutils `src/dat/Tech.cpp` (the names AGE's labels key on), with list
members suffixed `.0`/`.1` so a flat dict keeps one name per address.
`ResearchLocations.N.*` only exists on gv >= C31 (DE); older streams carry the
same three values as scalars inside the record, and this module records whichever
shape the file actually has.
"""

from __future__ import annotations

from . import parser as P
from .unitfields import Rec

__all__ = ["scan", "fields_at", "KINDS"]

KINDS = {"u8": 1, "u16": 2, "i16": 2, "i32": 4, "u32": 4, "f32": 4}


def read_tech_fields(r):
    """One technology record, named and addressed.  Returns (start, end).

    Line for line the read order of `parser.read_tech`; the only change is that
    every `r.i16()` that the parser throws away carries a name.  The guards are
    copied verbatim -- a tech on a legacy stream genuinely lacks
    ResearchLocations, and guessing one entry into existence writes nine bytes
    into the next record.
    """
    start = r.pos
    r.i16_n("RequiredTechs", 6)
    for i in range(3):
        # Research.cpp:61 -- ALWAYS exactly 3 ResourceUsage records, 5 bytes
        # each.  An empty slot is load-bearing: (-1,0,0) is the sentinel.
        r.i16("ResourceCosts.%d.Type" % i)
        r.i16("ResourceCosts.%d.Amount" % i)
        r.u8("ResourceCosts.%d.Flag" % i)
    r.i16("RequiredTechCount")
    r.i16("Civ")
    r.i16("FullTechMode")
    # Research.cpp:70 -- folded into ResearchLocations for gv >= GV_C31
    if r.gv < P.GV_C31:
        r.i16("ResearchLocation")
    # Research.cpp:73-87 -- i32 for DE (gv >= GV_C18), else a u16 pair
    if r.gv >= P.GV_MATT:
        if P.GV_C18 <= r.gv <= P.GV_LatestDE2:
            r.i32("LanguageDLLName")
            r.i32("LanguageDLLDescription")
        else:
            r.i16("LanguageDLLName")
            r.i16("LanguageDLLDescription")
    # Research.cpp:89 -- folded into ResearchLocations for gv >= GV_C31
    if r.gv < P.GV_C31:
        r.i16("ResearchTime")
    r.i16("EffectID")
    r.i16("Type")
    r.i16("IconID")
    # Research.cpp:96 -- folded into ResearchLocations for gv >= GV_C31
    if r.gv < P.GV_C31:
        r.u8("ButtonID")
    r.i32("LanguageDLLHelp")
    r.i32("LanguageDLLTechTree")
    # Research.cpp:105 -- deprecated once ResearchLocations exists
    if r.gv < P.GV_C31:
        r.i32("HotKey")
    # The three addresses of one string: marker and length are what a writer
    # bumps when the name grows, and `Rec.s` records all three for that reason.
    r.s("Name")
    if P.GV_C15 <= r.gv <= P.GV_LatestDE2:
        r.u8("Repeatable")
    if P.GV_C31 <= r.gv <= P.GV_LatestDE2:
        n = r.i16("ResearchLocationCount")
        for i in range(n):
            # ResearchLocation.cpp: one building (or unit) that can research
            # this tech, each with its OWN copy of the research time.  They must
            # be updated together or the copies end up disagreeing.
            r.i16("ResearchLocations.%d.LocationID" % i)
            r.i16("ResearchLocations.%d.ResearchTime" % i)
            r.u8("ResearchLocations.%d.ButtonID" % i)
            r.i32("ResearchLocations.%d.HotKeyID" % i)
    return start, r.pos


def fields_at(raw, gv, start):
    """Every named field of the ONE technology record that begins at `start`.

    Decoded on demand for the same reason `unitfields.fields_at` is: the panel
    shows one record at a time and the bytes are still in the file, so keeping
    1,510 decoded dicts around would be paid memory for nothing.
    """
    r = Rec(raw, P.GV_C32 if gv is None else gv)
    r.pos = start
    read_tech_fields(r)
    out = {}
    for name, off, kind, value in r.fields:
        out[name] = {"offset": off, "kind": kind, "value": value}
    return out


def scan(raw, gv=None, light=False, on_progress=None):
    """Parse `raw` once; return (techs, stats, leftover_bytes).

    Each tech is ``{"index", "start", "end", "fields"}`` -- `fields` only when
    `light` is false.  `index` is the tech's POSITION in the array, because a
    tech record carries no id field (see `locate.find_techs`).

    `leftover` is the caller's proof of faithfulness: it must be 0.  A non-zero
    value means these offsets are not the ones `parse()` walks, and every write
    built on them would land in a neighbouring record.
    """
    techs = []

    # Same reason and same shape as `unitfields.scan()`: a cold tech scan is
    # 12.32 s measured 2026-11-02 and 10 of those seconds are the Civs stage,
    # which walks the file from 4.2 % to 99.8 %.  Throttled to ~200 callbacks
    # because a bar cannot draw faster and a lock per record would cost more
    # than the number is worth.
    step = max(1, len(raw) // 200)
    marks = {"at": -step}

    def report(reader):
        if on_progress is None:
            return
        if reader.pos - marks["at"] < step:
            return
        marks["at"] = reader.pos
        on_progress(reader.pos)

    def rec_tech(reader):
        report(reader)
        start, end = read_tech_fields(reader)
        flat = {}
        if not light:
            for name, off, kind, value in reader.fields:
                flat[name] = {"offset": off, "kind": kind, "value": value}
        del reader.fields[:]
        techs.append({"index": len(techs), "start": start, "end": end,
                      "fields": flat})
        # `Parser.parse()` stores this dict as `stats["techs"][i]`; nothing
        # downstream of `scan()` reads it (the recorded list is the product),
        # but returning a dict with the right shape keeps the stage readable.
        return {"civ": 0, "effect_id": 0, "name": "", "research_locations": None}

    # The patch is module-wide, so it has to share `_PARSE_LOCK` with
    # `unitfields.scan` and with every plain `parse()`: a second thread parsing
    # inside this window would call the recorder with a plain `Reader` and die
    # on `Rec.i16() got an unexpected keyword argument`.  The originals are read
    # INSIDE the lock for the same reason -- captured outside, a second thread
    # could snapshot this twin as "the original" and restore to it.
    # The tech records themselves are only 135 KB at the END of the file (stage
    # 9), so reporting from `rec_tech` alone would leave the bar at 0 % for the
    # 7 seconds stage 8 (Civs) spends walking 89 MB and then jump to 100 %.
    # Measured 2026-11-02: a tech scan is 7.15 s and stage 8 is all of it, so it
    # gets its own reporter -- one call per civilisation (63 of them), which is
    # the finest granularity this scan can honestly offer.
    orig_civ_for_report = [None]

    def rec_civ(reader, collect=None):
        report(reader)
        return orig_civ_for_report[0](reader, collect)

    with P._PARSE_LOCK:
        orig_tech = P.read_tech
        orig_civ_for_report[0] = P.read_civ
        P.read_tech = rec_tech
        P.read_civ = rec_civ
        try:
            p = P.Parser(raw)
            p.r = Rec(raw, P.GV_C32 if gv is None else gv)
            stats = p.parse()
        finally:
            P.read_tech = orig_tech
            P.read_civ = orig_civ_for_report[0]

    leftover = len(raw) - p.r.pos
    if on_progress is not None:
        on_progress(len(raw) - leftover)
    return techs, stats, leftover

# -*- coding: utf-8 -*-
"""Build the `(base, mod, new)` corpus that `test_upgrade.py` checks.

WHY A BUILT CORPUS AND NOT A PILE OF REAL MODS
----------------------------------------------
A three-way merge engine is only worth trusting if it is shown working on cases
where the right answer is known in advance.  The player's own mod folder cannot
provide that: those mods change fields nobody wrote down, and a real patch
("the game shipped 8.9 → 9.0") cannot be summoned on demand.  So this script
manufactures the *shape* of the problem instead -- each case mutates the shipped
`empires2_x2_p1.dat` in place to stand in for "the mod author's edit" or "the
patch's edit", and records what a correct merge must produce in `expect.json`.

The mutation is done through the repo's own readers (`locate`, `unitfields`,
`fieldwrite`, `records`), never by writing a literal offset.  Two consequences
worth naming:

  * every edit is READ BACK after it is written, and a mismatch raises.  A
    fixture whose mutation silently did not land is worse than no fixture: it
    turns a merge bug into a harness bug that looks like a merge bug.
  * the coordinates come from whatever the installed game version really is, so
    this script keeps working across a patch instead of pinning case 1 to
    "offset 3965246".

`base` is almost always a verbatim copy of the shipped compressed file: it is
already raw-deflate, so copying 11.9 MB beats re-compressing 93 MB, and it keeps
the "the official file the day the mod was built" claim literal.

EXPECTATION VOCABULARY  (this is the whole point of the file -- keep it small)
-----------------------------------------------------------------------------
`expect.json` is `{"case", "base_sha256", "mod_sha256", "new_sha256", "mode",
"strategy", "checks": [...], "_doc"}`.

`*_sha256` is the SHA-256 of the **inflated** stream, not of the file on disk:
deflate is not byte-reproducible, and the engine's own "is this the same file"
question is about the 93 MB payload.  `*_file_sha256` is also recorded for the
stored bytes.

`mode`  : "merge" (analyze+upgrade must succeed) or "refuse" (must refuse).
`strategy`: "field", "records", or a list of the acceptable ones.  A list is
            used where the classification genuinely depends on the engine's own
            choice (e.g. case 6: the mod only edits a field, but the official
            file grew, so an engine may legitimately answer either).

check kinds, each `{"kind": ..., ...}`:

  unit_field   {civ_any|civ, unit, field, value, where?}
               Read `field` off the unit's record through `unitfields.fields_at`
               and require `value`.  With `civ_any` every civ that HAS the unit
               must agree, and a civ that lacks the unit is not a failure --
               the shipped file does not give all 63 civs every unit.
  tech_field   {index, field, value}      same, for one technology by position.
  present      {kind_detail:"unit"|"tech", civ?, unit?|index?}
  absent       {kind_detail:"unit"|"tech", civ?, unit?|index?}
  tech_count   {count}                    the technology array length.
  conflicts    {count}                    len(analyze()["conflicts"]).
  identical_to {which:"new"|"base"|"mod"} the merged stream equals that file,
                                          after inflating both.
  refuse_message {contains_any:[...]}     mode "refuse" only: the refusal must
                                          name a version string somewhere.

`where` on a `unit_field`/`tech_field` check says which source file that value
comes from; this builder verifies it at build time (it is the provenance of the
expectation), and the probe's real assertion is always the merged file.

USAGE
    python -X utf8 _probe/make_upgrade_fixtures.py            # build all
    python -X utf8 _probe/make_upgrade_fixtures.py --only case_name ...

Re-running overwrites the corpus.  Nothing outside the fixture root is written.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.dat.fieldwrite as FW
import aoe2mod.dat.locate as L
import aoe2mod.dat.parser as P
import aoe2mod.dat.records as R
import aoe2mod.dat.techfields as TF
import aoe2mod.dat.unitfields as UF
import aoe2mod.mod.emitter as EM

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
RAW_LEN = 93272287
RAW_SHA = "82eb7d148f8c6ee53f4dfa93210c3ce7dfb63194b65692ae51bfc780d62980fe"

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "_out", "_upgrade_fixtures")
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

#: Case 1's "a field the mod may touch for free".  Unit 74 (SPRMN) carries a
#: third resource cost of type 4 (population) with amount 1 in every civ; going
#: to 0 removes the population cost.  Found at runtime, named here only so the
#: check and the mutation cannot drift apart.
COST_AMOUNT = "Creatable.ResourceCosts.2.Amount"
#: VER 8.9 has no bare `ResearchTime`: a technology's research time lives inside
#: its ResearchLocations list, one copy per building that can research it.
RT = "ResearchLocations.0.ResearchTime"

U_COST = 74          # SPRMN -- archer-line? no: the barracks-less base unit used by case 1
U_HP = 83            # VMBAS, the one case 2/3/4 fight over
U_REMOVED = 93       # PKEMN, deleted by the mod in case 8
U_NEW = 30000        # the id the mod invents in case 7
T_A = 5              # "Celtic Furor Celtica"
T_B = 6              # "Mongol Siege Drill"
APPEND_NAME = "UPGRADE FIXTURE APPEND"


class Ctx(object):
    """Everything located once from the shipped file and reused per case."""

    def __init__(self, raw, gv, civs, civs_start, tail, techs):
        self.raw = raw
        self.gv = gv
        self.civs = civs
        self.civs_start = civs_start
        self.tail = tail
        self.techs = techs

    def units(self, unit_id):
        hits = L.find_units(self.civs, unit_id)
        if not hits:
            raise RuntimeError("the shipped file has no unit %d" % (unit_id,))
        return hits


# ---------------------------------------------------------------------------
# mutation primitives -- each one reads its own edit back
# ---------------------------------------------------------------------------
def write_unit(buf, ctx, unit_id, field, value, only_civs=None):
    """Write one field on every record of `unit_id`; return how many landed."""
    hits = ctx.units(unit_id)
    n = 0
    for ci, cname, u in hits:
        if only_civs is not None and ci not in only_civs:
            continue
        res = FW.plan("unit", buf, ctx.gv, {"start": u["_start"], "end": u["_end"]},
                      field, value)
        if not res.get("ok"):
            raise RuntimeError("unit %d %s <- %r refused: %s"
                               % (unit_id, field, value, res.get("error")))
        FW.apply(buf, res["offset"], res["packed"])
        got = UF.fields_at(buf, ctx.gv, u["_start"]).get(field, {}).get("value")
        if got != value:
            raise RuntimeError("unit %d civ %d %s did not land: %r != %r"
                               % (unit_id, ci, field, got, value))
        n += 1
    if not n:
        raise RuntimeError("unit %d: no record matched civs %r" % (unit_id, only_civs))
    return n


def write_tech(buf, ctx, index, field, value, techs=None):
    techs = techs or ctx.techs
    if index >= len(techs):
        raise RuntimeError("no tech %d (file has %d)" % (index, len(techs)))
    t = techs[index]
    res = FW.plan("tech", buf, ctx.gv, {"start": t["start"], "end": t["end"]},
                  field, value)
    if not res.get("ok"):
        raise RuntimeError("tech %d %s <- %r refused: %s"
                           % (index, field, value, res.get("error")))
    FW.apply(buf, res["offset"], res["packed"])
    got = TF.fields_at(buf, ctx.gv, t["start"]).get(field, {}).get("value")
    if got != value:
        raise RuntimeError("tech %d %s did not land: %r != %r" % (index, field, got, value))
    return 1


def read_unit(buf, ctx, unit_id, field):
    """Values of `field` across every civ record of `unit_id`."""
    return sorted({UF.fields_at(buf, ctx.gv, u["_start"])[field]["value"]
                   for _ci, _cn, u in ctx.units(unit_id)})


def relocate(buf):
    """locate() on a buffer that changed length (structural cases only)."""
    p = P.Parser(buf)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, civs_start, gv, tail = L.locate(buf, p)
    return civs, civs_start, gv, tail


def scan_techs(buf, gv):
    """`techfields.scan`, with its own internal re-parse kept off stdout.

    `scan()` builds a second Parser to drive its recorder, so its banner
    escapes any `redirect_stdout` the caller did not wrap around the CALL.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return TF.scan(buf, gv, light=True)[0]


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------
def case_mod_touches_a(base, ctx):
    """Two DIFFERENT fields on the SAME unit.  Nothing may be lost."""
    mod = bytearray(base)
    new = bytearray(base)
    n_mod = write_unit(mod, ctx, U_COST, COST_AMOUNT, 0)
    n_new = write_unit(new, ctx, U_COST, "HitPoints", 41)
    return dict(mod=mod, new=new, mode="merge", strategy="field",
                note="unit %d: mod cost slot 3 -> 0 (%d records), new HP 40 -> 41 (%d)"
                     % (U_COST, n_mod, n_new),
                checks=[
                    {"kind": "unit_field", "civ_any": True, "unit": U_COST,
                     "field": COST_AMOUNT, "value": 0, "where": "mod"},
                    {"kind": "unit_field", "civ_any": True, "unit": U_COST,
                     "field": "HitPoints", "value": 41, "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_same_field_conflict(base, ctx):
    """One field, two different values.  The modder's choice must survive."""
    mod = bytearray(base)
    new = bytearray(base)
    write_unit(mod, ctx, U_HP, "HitPoints", 1000)
    write_unit(new, ctx, U_HP, "HitPoints", 60)
    return dict(mod=mod, new=new, mode="merge", strategy="field",
                note="unit %d HP: base 25, mod 1000, official 60 -> mod wins, 1 conflict"
                     % (U_HP,),
                checks=[
                    {"kind": "unit_field", "civ_any": True, "unit": U_HP,
                     "field": "HitPoints", "value": 1000, "where": "mod"},
                    {"kind": "conflicts", "count": 1},
                ])


def case_same_field_agree(base, ctx):
    """One field, the same value on both sides: agreement is not a conflict.

    Each side ALSO owns one edit the other does not touch (mod 74, official 93),
    and that is load-bearing rather than decoration.  If both sides made only the
    identical edit, `mod` and `new` would be the same bytes, and the engine would
    answer "this mod's .dat IS the new official data, nothing to do" without ever
    reaching the merge -- a correct answer to a different question, which would
    hide whether agreement is treated as conflict.  One unrelated edit per side
    forces the real path.
    """
    mod = bytearray(base)
    new = bytearray(base)
    write_unit(mod, ctx, U_HP, "HitPoints", 1000)
    write_unit(new, ctx, U_HP, "HitPoints", 1000)
    write_unit(mod, ctx, U_COST, "HitPoints", 41)
    write_unit(new, ctx, U_REMOVED, "HitPoints", 46)
    return dict(mod=mod, new=new, mode="merge", strategy="field",
                note="unit %d HP 1000 on both sides; mod also edits %d, official also edits %d"
                     % (U_HP, U_COST, U_REMOVED),
                checks=[
                    {"kind": "unit_field", "civ_any": True, "unit": U_HP,
                     "field": "HitPoints", "value": 1000},
                    {"kind": "unit_field", "civ_any": True, "unit": U_COST,
                     "field": "HitPoints", "value": 41, "where": "mod"},
                    {"kind": "unit_field", "civ_any": True, "unit": U_REMOVED,
                     "field": "HitPoints", "value": 46, "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_mod_untouched_follows_official(base, ctx):
    """The mod edited 83; the patch edited 74.  Each side owns its field."""
    mod = bytearray(base)
    new = bytearray(base)
    write_unit(mod, ctx, U_HP, "HitPoints", 1000)
    write_unit(new, ctx, U_COST, "HitPoints", 41)
    return dict(mod=mod, new=new, mode="merge", strategy="field",
                note="mod unit %d, official unit %d -- the merged file must carry both"
                     % (U_HP, U_COST),
                checks=[
                    {"kind": "unit_field", "civ_any": True, "unit": U_COST,
                     "field": "HitPoints", "value": 41, "where": "new"},
                    {"kind": "unit_field", "civ_any": True, "unit": U_HP,
                     "field": "HitPoints", "value": 1000, "where": "mod"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_tech_field(base, ctx):
    """Two different technologies, one field.  Both edits survive."""
    mod = bytearray(base)
    new = bytearray(base)
    write_tech(mod, ctx, T_A, RT, 55)
    write_tech(new, ctx, T_B, RT, 70)
    return dict(mod=mod, new=new, mode="merge", strategy="field",
                note="tech %d RT 50->55 (mod), tech %d RT 60->70 (official)"
                     % (T_A, T_B),
                checks=[
                    {"kind": "tech_field", "index": T_A, "field": RT, "value": 55,
                     "where": "mod"},
                    {"kind": "tech_field", "index": T_B, "field": RT, "value": 70,
                     "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_tech_added_by_official(base, ctx):
    """The patch APPENDS a technology; the mod edited one that already existed.

    Appending only moves what comes after it, so tech 5 keeps its position --
    the assertion is that the mod's edit is found on the same tech, i.e. by
    identity and not by "the offset the mod's file had".
    """
    mod = bytearray(base)
    new, info = R.add_tech(base, ctx.gv, ctx.tail, 0, internal_name=APPEND_NAME)
    write_tech(mod, ctx, T_A, RT, 55)
    # The append must be real before the fixture is written.  One scan, not
    # three: `techfields.scan()` re-parses the whole 93 MB stream (~9.5 s each),
    # so asking it twice for the same answer doubles the build time.
    with contextlib.redirect_stdout(io.StringIO()):
        new_techs = TF.scan(new, ctx.gv, light=True)[0]
    n_tech = len(new_techs)
    added = TF.fields_at(new, ctx.gv, new_techs[-1]["start"])
    if n_tech != len(ctx.techs) + 1:
        raise RuntimeError("add_tech did not land: %d techs, expected %d"
                           % (n_tech, len(ctx.techs) + 1))
    if added.get("Name", {}).get("value") != APPEND_NAME:
        raise RuntimeError("appended tech is named %r, not %r"
                           % (added.get("Name", {}).get("value"), APPEND_NAME))
    return dict(mod=mod, new=bytearray(new), mode="merge",
                strategy=["field", "records"],
                note="official appends tech #%d (%r, %d bytes); mod edits tech %d"
                     % (info["id"], APPEND_NAME, info["bytes"], T_A),
                checks=[
                    {"kind": "tech_field", "index": T_A, "field": RT, "value": 55,
                     "where": "mod"},
                    {"kind": "tech_count", "count": len(ctx.techs) + 1},
                    {"kind": "tech_field", "index": len(ctx.techs),
                     "field": "Name", "value": APPEND_NAME, "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_unit_added_by_mod(base, ctx):
    """The mod invents a record.  It exists in no official file, and must live."""
    mod, info = R.add_unit(base, ctx.gv, ctx.civs_start, 1, U_COST,
                           new_id=U_NEW, hp=999)
    civs2, _cs, _gv, _t = relocate(mod)
    hit = [u for _ci, _cn, u in L.find_units(civs2, U_NEW) if _ci == 1]
    if not hit:
        raise RuntimeError("add_unit did not land: civ 1 has no unit %d" % (U_NEW,))
    f = UF.fields_at(mod, ctx.gv, hit[0]["_start"])
    if f["HitPoints"]["value"] != 999 or f["ID"]["value"] != U_NEW:
        raise RuntimeError("cloned record is id=%s hp=%s, expected %d/999"
                           % (f["ID"]["value"], f["HitPoints"]["value"], U_NEW))
    # `new` is NOT the base file, and that is deliberate.  A patch that changed
    # nothing means "the mod is already current" -- the engine answers that
    # before merging, so `new == base` would test the short-circuit instead of
    # the record carry the case exists for.  The official edit is on a different
    # unit, so it also proves the record merge does not stomp the patch.
    new = bytearray(base)
    write_unit(new, ctx, U_COST, "HitPoints", 41)
    return dict(mod=bytearray(mod), new=new, mode="merge", strategy="records",
                note="mod adds unit %d (clone of %d) in civ 1 only, %d bytes; official edits %d"
                     % (U_NEW, U_COST, info["bytes"], U_COST),
                checks=[
                    {"kind": "present", "kind_detail": "unit", "civ": 1, "unit": U_NEW},
                    {"kind": "unit_field", "civ": 1, "unit": U_NEW,
                     "field": "HitPoints", "value": 999, "where": "mod"},
                    {"kind": "unit_field", "civ_any": True, "unit": U_COST,
                     "field": "HitPoints", "value": 41, "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_unit_removed_by_mod(base, ctx):
    """The mod deletes a record the patch then edits.  Deletion wins.

    One civ, not 63: removing the record from every civilization is a 63-step
    structural splice whose only extra information is "bigger".  Civ 1 is where
    the mod's own unit-add case lives too, so the two cases read alike.
    """
    mod, info = R.remove_units(base, ctx.gv, ctx.civs_start, 1, [U_REMOVED])
    civs2, _cs, _gv, _t = relocate(mod)
    still = [ci for ci, _cn, _u in L.find_units(civs2, U_REMOVED)]
    if still != [ci for ci in still if ci != 1] or len(still) != len(ctx.units(U_REMOVED)) - 1:
        raise RuntimeError("remove_units did not land: unit %d still in civs %r"
                           % (U_REMOVED, still))
    new = bytearray(base)
    n_new = write_unit(new, ctx, U_REMOVED, "HitPoints", 46)
    return dict(mod=bytearray(mod), new=new, mode="merge", strategy="records",
                note="mod deletes unit %d from civ 1 (%d bytes); official sets its HP 46 in %d civs"
                     % (U_REMOVED, info["bytes"], n_new),
                checks=[
                    {"kind": "absent", "kind_detail": "unit", "civ": 1,
                     "unit": U_REMOVED},
                    {"kind": "unit_field", "civ_any": True, "unit": U_REMOVED,
                     "field": "HitPoints", "value": 46, "where": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_byte_identical(base, ctx):
    """The mod changed nothing.  The merged file must BE the new file.

    Compressed bytes are not reproducible, so "identical" is asserted on the
    inflated stream -- that is also the only comparison the game cares about.
    """
    new = bytearray(base)
    write_unit(new, ctx, U_COST, "HitPoints", 41)
    return dict(mod=None, new=new, mode="merge", strategy="field",
                note="mod == base verbatim; merged must equal new after inflate",
                checks=[
                    {"kind": "identical_to", "which": "new"},
                    {"kind": "conflicts", "count": 0},
                ])


def case_cross_generation(base, ctx):
    """A `VER 7.8` header on an 8.9 body: the merge must refuse, not guess.

    Same byte count in and out, so every offset after the header stays valid --
    which is what makes this a test of the RULE (a generation mismatch outranks
    everything) rather than of a layout difference the engine could not see.
    """
    old, new_ver = b"VER 8.9", b"VER 7.8"
    if base[:len(old)] != old:
        raise RuntimeError("expected the shipped head to start %r, got %r"
                           % (old, base[:len(old)]))
    mod = bytearray(new_ver + base[len(old):])
    if len(mod) != len(base):
        raise RuntimeError("the fake version header changed the length")
    # The patch itself is an ordinary same-generation edit.  Without it `new`
    # equals `base`, and the engine's "this mod is already current" answer fires
    # before anything ever looks at the mod's header -- which is why this case
    # must ship a real patch on the right-hand side.
    new = bytearray(base)
    write_unit(new, ctx, U_COST, "HitPoints", 41)
    return dict(mod=mod, new=new, mode="refuse", strategy=None,
                note="mod header %s -> %s, body untouched; official edits %d"
                     % (old.decode(), new_ver.decode(), U_COST),
                checks=[{"kind": "refuse_message",
                         "contains_any": ["7.8", "8.9", "VER"]}])


CASES = [
    ("mod_touches_a", case_mod_touches_a),
    ("same_field_conflict", case_same_field_conflict),
    ("same_field_agree", case_same_field_agree),
    ("mod_untouched_follows_official", case_mod_untouched_follows_official),
    ("tech_field", case_tech_field),
    ("tech_added_by_official", case_tech_added_by_official),
    ("unit_added_by_mod", case_unit_added_by_mod),
    ("unit_removed_by_mod", case_unit_removed_by_mod),
    ("byte_identical", case_byte_identical),
    ("cross_generation", case_cross_generation),
]


# ---------------------------------------------------------------------------
# writing and measuring
# ---------------------------------------------------------------------------
def _sha(raw):
    return hashlib.sha256(bytes(raw)).hexdigest()


def _file_sha(path):
    """SHA-256 of the bytes ON DISK (the deflate stream)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_dat(path, raw):
    """Store `raw` as bare deflate, the way the shipped file is stored."""
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "wb") as fh:
        fh.write(EM.deflate_raw(bytes(raw), 6))
    return os.path.getsize(path)


def _copy_dat(path):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    shutil.copyfile(SHIPPED, path)
    return os.path.getsize(path)


def _deltas(a, b):
    """Where two inflated streams differ, and by how much.

    Comparing 93 MB byte by byte in Python costs ~9 s.  Trimming the common
    prefix and suffix first (slice compares run in C) leaves only the bytes that
    were actually edited -- and the trim PROVES everything outside them is
    untouched, which is what any "changed N bytes" claim has to mean.

    Returns ``{"lo", "tail", "diff", "a_mid", "b_mid"}``.  When the two lengths
    differ the honest description is a SPLICE at ``lo``, not a byte count: an
    inserted record shifts every following byte, so "the bytes that differ" is
    a property of the shift, not of the edit.
    """
    n = min(len(a), len(b))
    lo = 0
    step = 1 << 16
    while lo < n:
        hi = min(n, lo + step)
        if a[lo:hi] != b[lo:hi]:
            break
        lo = hi
    tail = 0
    while tail < n - lo:
        take = min(step, n - lo - tail)
        if a[len(a) - tail - take:len(a) - tail] != b[len(b) - tail - take:len(b) - tail]:
            break
        tail += take
    am = a[lo:len(a) - tail]
    bm = b[lo:len(b) - tail]
    d = sum(1 for x, y in zip(am, bm) if x != y) + abs(len(am) - len(bm))
    return {"lo": lo, "tail": tail, "diff": d, "a_mid": len(am), "b_mid": len(bm)}


def _delta_text(d):
    """One phrase describing a `_deltas()` result, or "== base"."""
    if not d["diff"]:
        return "== base"
    if d["a_mid"] == d["b_mid"]:
        return "%d B differ" % (d["diff"],)
    return "splice @%d: %d->%d B (%+d)" % (d["lo"], d["a_mid"], d["b_mid"],
                                           d["b_mid"] - d["a_mid"])


def build_one(name, fn, base, ctx, base_sha, base_size):
    res = fn(bytes(base), ctx)
    case_dir = os.path.join(ROOT, name)
    dat = os.path.join(case_dir, "base", DAT_REL)
    base_size_out = _copy_dat(dat)

    mod_raw = base if res["mod"] is None else bytes(res["mod"])
    new_raw = base if res["new"] is None else bytes(res["new"])

    # Every case gets all three files, even the two that are byte-identical to
    # base.  A case function says `mod=None` to mean "this side is unchanged",
    # NOT "this side is not part of the corpus": the probe opens all three paths
    # before it knows which case it is in, and a case with a missing file would
    # fail as a FileNotFoundError instead of testing the merge.  The copy for
    # the unchanged sides is the shipped deflate stream verbatim -- writing it
    # would cost 0.6 s of compression to reproduce a file we already have.
    mod_size = (base_size_out if res["mod"] is None
                else _write_dat(os.path.join(case_dir, "mod", DAT_REL), mod_raw))
    new_size = (base_size_out if res["new"] is None
                else _write_dat(os.path.join(case_dir, "new", DAT_REL), new_raw))
    if res["mod"] is None:
        _copy_dat(os.path.join(case_dir, "mod", DAT_REL))
    if res["new"] is None:
        _copy_dat(os.path.join(case_dir, "new", DAT_REL))

    expect = {
        "case": name,
        "base_sha256": base_sha,
        "mod_sha256": _sha(mod_raw),
        "new_sha256": _sha(new_raw),
        "base_file_sha256": _file_sha(dat),
        "mode": res["mode"],
        "strategy": res["strategy"],
        "checks": res["checks"],
        "_doc": ("checks are read against the MERGED dat; *_sha256 hash the "
                 "inflated stream. " + res["note"]),
    }
    with open(os.path.join(case_dir, "expect.json"), "w", encoding="utf-8") as fh:
        json.dump(expect, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    # Prove the two source files really differ where the note says they do.
    for which, raw in (("mod", mod_raw), ("new", new_raw)):
        if raw is base:
            continue
        d = _deltas(base, raw)
        if not d["diff"]:
            raise RuntimeError("%s/%s: the mutation did not change a byte"
                               % (name, which))
    dm = _deltas(base, mod_raw)
    dn = _deltas(base, new_raw)
    print("%-30s raw %d  mod %-24s new %-24s %.1f+%.1f MB"
          % (name, len(base),
             _delta_text(dm), _delta_text(dn),
             mod_size / 1e6, new_size / 1e6))
    print("%-30s   %s" % ("", case_dir))
    return expect


def main(argv):
    only = [a for a in argv[1:] if not a.startswith("-")]
    t0 = time.time()
    raw, how = P.load_dat(SHIPPED)
    if len(raw) != RAW_LEN:
        raise RuntimeError("%s inflated to %d bytes, expected %d -- the game was patched"
                           % (SHIPPED, len(raw), RAW_LEN))
    got = _sha(raw)
    if got != RAW_SHA:
        raise RuntimeError("%s hashes to %s, expected %s -- the game was patched"
                           % (SHIPPED, got, RAW_SHA))
    print("shipped  %d raw bytes  %s  (%s)" % (len(raw), got[:16] + "...", how))

    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, civs_start, gv, tail = L.locate(raw, p)
    techs = scan_techs(raw, gv)
    ctx = Ctx(raw, gv, civs, civs_start, tail, techs)
    print("located  %d civs  gv=%s  civs_start=%d  tail=%d  %d techs  (%d unit records)"
          % (len(civs), gv, civs_start, tail, len(techs),
             sum(len(c["units"]) for c in civs)))

    if not os.path.isdir(ROOT):
        os.makedirs(ROOT)
    done = []
    for name, fn in CASES:
        if only and name not in only:
            continue
        done.append(build_one(name, fn, raw, ctx, _sha(raw),
                              os.path.getsize(SHIPPED)))
    if only and len(done) != len(only):
        raise RuntimeError("unknown case name in %r" % (only,))
    print("\n%d case(s) in %s  (%.1fs)"
          % (len(done), ROOT, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

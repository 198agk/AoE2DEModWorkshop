# -*- coding: utf-8 -*-
"""probe/test_portgen.py -- portgen.py moves a record between generations intact.

WHY THIS SUITE EXISTS
---------------------
The module's own docstring has claimed since it was written that
_probe/test_portgen.py proves it by round trip.  That file did not exist, so the
claim was decoration.  It exists now.

Two separate things are checked, because they fail in different ways:

1. SAME-GENERATION ROUND TRIP.  Decode a record at generation X and re-encode
   it at generation X; the bytes must be identical, field for field.  This is
   the only way to catch a field the replay forgets to emit -- a forgotten
   field does not raise, it just shifts everything after it.

2. THE NAME FOLDS.  Two generations hold the same fact under different names,
   and a name-by-name tape then writes a default.  Measured on the 209785 mod
   (VER 8.4) re-encoded as VER 8.9: every unit's Creatable.TrainLocationsCount
   went out as 0, so no train location was written and AGE showed an empty
   training list; every one of the 3,030 techs lost its research building the
   same way.  The fold pairs are asserted against real archived builds in both
   directions, plus the two things a fold must NOT do: invent a count for a
   record that never had the group, and silently drop the slots a narrower
   generation cannot hold.

WHICH GENERATIONS ARE EXERCISED
-------------------------------
Every archived build that upgrade.Frame can parse.  Six archived builds
(VER 7.1/7.2/7.3/7.4/7.5/7.7) cannot be parsed at all -- parser.read_bird asks
for an i16 array of negative length -- which is a pre-existing parser limit and
not this module's subject; they are named in a NOTE line rather than silently
skipped.  A generation that parses today and stops parsing later makes this
suite red, which is the point: coverage must not quietly shrink.

    python -X utf8 _probe/test_portgen.py
    python -X utf8 _probe/test_portgen.py -v
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P                    # noqa: E402
from aoe2mod.dat import techfields as TF               # noqa: E402
from aoe2mod.dat import unitfields as UF               # noqa: E402
from aoe2mod.mod import archives as AR                 # noqa: E402
from aoe2mod.mod import portgen as PG                  # noqa: E402
from aoe2mod.mod import upgrade as UP                  # noqa: E402

VERBOSE = "-v" in sys.argv
FAILS = []

#: The generations this suite insists are still parseable.  Every one of them is
#: in the local shelf today; losing one is a coverage loss, not a passing run.
MUST_PARSE = ("VER 7.8", "VER 8.4", "VER 8.8", "VER 8.9")

UNITS = 40
TECHS = 60


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label
          + ((" :: " + str(detail)) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)
    return cond


def note(label, detail=""):
    print("  NOTE " + label + ((" :: " + str(detail)) if detail else ""))


def val(fields, name, default=None):
    slot = fields.get(name)
    return default if slot is None else slot["value"]


# -- the shelf ---------------------------------------------------------------
def shelf():
    """ver -> path, newest archived build of each generation."""
    out = {}
    for e in AR.describe()["entries"]:
        out.setdefault(e["ver"], e["path"])
    return out


def load(ver, path):
    raw = AR._inflate(path)[0]
    return raw, UP.Frame(raw, ver)


# -- 1. same-generation round trip ------------------------------------------
def round_trip(ver, raw, fr):
    rnd = random.Random(20261114)
    keys = sorted(fr.unit_keys())
    picked = rnd.sample(keys, min(UNITS, len(keys)))
    spans = fr.build_tech_spans()
    tpicked = rnd.sample(range(len(spans)), min(TECHS, len(spans)))
    bad = []
    for civ, uid in picked:
        sp = fr.unit_span(civ, uid)
        if not sp:
            continue
        out, tape = PG.encode_unit(raw, sp[0], sp[1], fr.gv, fr.gv)
        if out != raw[sp[0]:sp[1]]:
            bad.append("unit %s/%s wrote %d of %d bytes%s"
                       % (civ, uid, len(out), sp[1] - sp[0],
                          (" missing=%s" % (tape.missing[:4],))
                          if tape.missing else ""))
    for i in tpicked:
        s0, e0 = spans[i]
        out, tape = PG.encode_tech(raw, s0, e0, fr.gv, fr.gv)
        if out != raw[s0:e0]:
            bad.append("tech %d wrote %d of %d bytes" % (i, len(out), e0 - s0))
    check("%s (%d units, %d techs) re-encodes byte for byte"
          % (ver, len(picked), len(tpicked)), not bad, bad[:4])
    return not bad


# -- 2. the folds -----------------------------------------------------------
def find_unit(fr, raw, pred, limit=6000):
    """The first (civ, id, span, fields) whose fields satisfy pred."""
    for civ, uid in sorted(fr.unit_keys())[:limit]:
        sp = fr.unit_span(civ, uid)
        if not sp:
            continue
        f = UF.fields_at(raw, fr.gv, sp[0])
        if pred(f):
            return civ, uid, sp, f
    return None


def find_tech(fr, raw, pred):
    for i, (s0, _e0) in enumerate(fr.build_tech_spans()):
        f = TF.fields_at(raw, fr.gv, s0)
        if pred(f):
            return i, s0, f
    return None


def fold_forward(ver_from, raw_from, fr_from, ver_to, raw_to, fr_to):
    """8.4 -> 8.9: the fixed slot becomes a counted group."""
    hit = find_unit(fr_from, raw_from,
                    lambda f: (val(f, "Creatable.TrainLocations.0.TrainTime", 0) or 0) > 0)
    if not check("%s carries a train location to probe" % ver_from, hit is not None):
        return
    civ, uid, sp, src = hit
    out, tape = PG.encode_unit(raw_from, sp[0], sp[1], fr_from.gv, fr_to.gv)
    got = UF.fields_at(out, fr_to.gv, 0)
    want = val(src, "Creatable.TrainLocations.0.TrainTime")
    check("unit %s/%s keeps its train time across the fold (%s)"
          % (civ, uid, want),
          val(got, "Creatable.TrainLocations.0.TrainTime") == want,
          (val(got, "Creatable.TrainLocations.0.TrainTime"),
           val(got, "Creatable.TrainLocationsCount")))
    check("unit %s/%s gets TrainLocationsCount 1, not 0" % (civ, uid),
          val(got, "Creatable.TrainLocationsCount") == 1,
          val(got, "Creatable.TrainLocationsCount"))
    check("unit %s/%s keeps the unit it trains" % (civ, uid),
          val(got, "Creatable.TrainLocations.0.UnitID")
          == val(src, "Creatable.TrainLocations.0.UnitID"))
    check("unit %s/%s moves HotKeyFromUnit into slot 0" % (civ, uid),
          val(got, "Creatable.TrainLocations.0.HotKeyID")
          == val(src, "Creatable.HotKeyFromUnit", PG.NO_HOTKEY),
          (val(got, "Creatable.TrainLocations.0.HotKeyID"),
           val(src, "Creatable.HotKeyFromUnit")))
    check("unit fold reports the rebuilt names as carried, not defaulted",
          "Creatable.TrainLocationsCount" in tape.synth and not tape.missing,
          (tape.synth[:4], tape.missing[:4]))

    # The result must itself survive a same-generation re-encode: a fold that
    # only looks right through one reader is a fold that shifted bytes.
    again, _ = PG.encode_unit(out, 0, len(out), fr_to.gv, fr_to.gv)
    check("the folded unit record is stable when re-encoded at %s" % ver_to,
          again == out)

    thit = find_tech(fr_from, raw_from,
                     lambda f: (val(f, "ResearchLocation", -1) or -1) > 0)
    if not check("%s carries a research location to probe" % ver_from, thit is not None):
        return
    i, ts0, tsrc = thit
    tend = fr_from.build_tech_spans()[i][1]
    tout, ttape = PG.encode_tech(raw_from, ts0, tend, fr_from.gv, fr_to.gv)
    tgot = TF.fields_at(tout, fr_to.gv, 0)
    for src_name, dst_name in (("ResearchLocation", "ResearchLocations.0.LocationID"),
                               ("ResearchTime", "ResearchLocations.0.ResearchTime"),
                               ("ButtonID", "ResearchLocations.0.ButtonID"),
                               ("HotKey", "ResearchLocations.0.HotKeyID")):
        check("tech %d carries %s -> %s" % (i, src_name, dst_name),
              val(tgot, dst_name) == val(tsrc, src_name),
              (val(tgot, dst_name), val(tsrc, src_name)))
    check("tech %d gets ResearchLocationCount 1, not 0" % i,
          val(tgot, "ResearchLocationCount") == 1,
          val(tgot, "ResearchLocationCount"))

    # A tech with NO research building is still count 1 with LocationID -1 --
    # that is how the official 8.9 file spells it (871 records measured).  The
    # value itself is carried, not remapped: the official 8.9 file ALSO carries
    # 159 techs with LocationID 0, so 8.4's -1 and 8.4's 0 are both real answers
    # and neither may be rewritten.  What must never happen is count 0, because
    # that is a tech with no research location AT ALL, which 8.4 cannot express.
    for want_loc, label in ((-1, "-1 (no research building)"), (0, "0 (a real id)")):
        nhit = find_tech(fr_from, raw_from,
                         lambda f, w=want_loc: val(f, "ResearchLocation") == w)
        if not check("%s has a tech with ResearchLocation %s" % (ver_from, label),
                     nhit is not None):
            continue
        j, ns0, nsrc = nhit
        nend = fr_from.build_tech_spans()[j][1]
        nout, _ = PG.encode_tech(raw_from, ns0, nend, fr_from.gv, fr_to.gv)
        ngot = TF.fields_at(nout, fr_to.gv, 0)
        check("tech %d with ResearchLocation %s becomes count 1, not count 0"
              % (j, label),
              val(ngot, "ResearchLocationCount") == 1,
              val(ngot, "ResearchLocationCount"))
        check("tech %d carries ResearchLocation %s through untouched"
              % (j, label),
              val(ngot, "ResearchLocations.0.LocationID") == want_loc,
              (val(ngot, "ResearchLocations.0.LocationID"), want_loc))


def fold_reverse(ver_from, raw_from, fr_from, ver_to, raw_to, fr_to):
    """8.9 -> 8.4: the group collapses back onto four scalars."""
    hit = find_unit(fr_from, raw_from,
                    lambda f: (val(f, "Creatable.TrainLocationsCount", 0) or 0) >= 1)
    if check("%s carries a counted train location to probe" % ver_from,
             hit is not None):
        civ, uid, sp, src = hit
        out, tape = PG.encode_unit(raw_from, sp[0], sp[1], fr_from.gv, fr_to.gv)
        got = UF.fields_at(out, fr_to.gv, 0)
        check("unit %s/%s restores HotKeyFromUnit from slot 0" % (civ, uid),
              val(got, "Creatable.HotKeyFromUnit")
              == val(src, "Creatable.TrainLocations.0.HotKeyID", PG.NO_HOTKEY),
              (val(got, "Creatable.HotKeyFromUnit"),
               val(src, "Creatable.TrainLocations.0.HotKeyID")))
        check("unit %s/%s drops the count name %s cannot hold"
              % (civ, uid, ver_to),
              "Creatable.TrainLocationsCount" not in got)
        check("the reverse unit fold defaults nothing", not tape.missing,
              tape.missing[:4])

    thit = find_tech(fr_from, raw_from,
                     lambda f: (val(f, "ResearchLocationCount", 0) or 0) >= 1)
    if check("%s carries a counted research location to probe" % ver_from,
             thit is not None):
        i, s0, src = thit
        e0 = fr_from.build_tech_spans()[i][1]
        out, tape = PG.encode_tech(raw_from, s0, e0, fr_from.gv, fr_to.gv)
        got = TF.fields_at(out, fr_to.gv, 0)
        for src_name, dst_name in (("ResearchLocations.0.LocationID", "ResearchLocation"),
                                   ("ResearchLocations.0.ResearchTime", "ResearchTime"),
                                   ("ResearchLocations.0.ButtonID", "ButtonID"),
                                   ("ResearchLocations.0.HotKeyID", "HotKey")):
            check("tech %d restores %s from %s" % (i, dst_name, src_name),
                  val(got, dst_name) == val(src, src_name),
                  (val(got, dst_name), val(src, src_name)))
        check("tech %d gets all four scalars and no count" % i,
              "ResearchLocationCount" not in got)
        again, _ = PG.encode_tech(out, 0, len(out), fr_to.gv, fr_to.gv)
        check("the folded-back tech record is stable at %s" % ver_to, again == out)

    # A three-building tech: slot 0 survives, the other two are REPORTED.
    multi = find_tech(fr_from, raw_from,
                      lambda f: (val(f, "ResearchLocationCount", 0) or 0) >= 3)
    if multi is not None:
        i, s0, _src = multi
        e0 = fr_from.build_tech_spans()[i][1]
        _out, tape = PG.encode_tech(raw_from, s0, e0, fr_from.gv, fr_to.gv)
        check("tech %d keeps slot 0 and reports slots 1/2 as unrepresentable" % i,
              "ResearchLocations.1" in tape.folded
              and "ResearchLocations.2" in tape.folded,
              tape.folded)


def no_invented_counts(ver_from, raw_from, fr_from, ver_to):
    """A record with no Creatable section must not gain a train location."""
    hit = find_unit(fr_from, raw_from,
                    lambda f: "Creatable.TrainLocations.0.TrainTime" not in f
                    and int(val(f, "Type", 99) or 99) < 70)
    if not check("%s has a record with no Creatable section" % ver_from,
                 hit is not None):
        return
    civ, uid, sp, _f = hit
    out, tape = PG.encode_unit(raw_from, sp[0], sp[1], fr_from.gv, fr_from.gv)
    got = UF.fields_at(out, fr_from.gv, 0)
    check("unit %s/%s (type < 70) gains no train location" % (civ, uid),
          "Creatable.TrainLocationsCount" not in got, sorted(got)[:6])
    check("no fold was consulted for a record without the group",
          not [n for n in tape.synth if "TrainLocations" in n or "Research" in n],
          tape.synth[:4])


def absent_defaults(ver_from, raw_from, fr_from, ver_to, raw_to, fr_to):
    """Fields the newer generation added: measured, not zeroed.

    8.4 has no `Type50.FriendlyFireDamage`, and zero is a real value for every
    field in the table, so "the source never had this" has to be answered with
    the number the official file uses -- 1.0 for friendly fire (0 would silently
    make the ported unit unable to hurt its own allies), -1 for the graphic and
    button slots (0 is graphic 0, icon 0, tooltip 0).  This section pins three
    things: the names really are new, the table's value really is the official
    file's commonest value, and a ported record carries them without a single
    entry left in `missing`.
    """

    def name_set(raw, fr, step):
        got = set()
        for k in sorted(fr.unit_keys())[::step]:
            sp = fr.unit_span(k[0], k[1])
            if not sp:
                continue
            got |= set(UF.fields_at(raw, fr.gv, sp[0]))
        return got

    src = name_set(raw_from, fr_from, 40)
    dst = name_set(raw_to, fr_to, 40)
    new_names = []
    for name in sorted(PG._ABSENT_DEFAULT):
        if check("%s has no field called %s" % (ver_from, name), name not in src):
            new_names.append(name)
        check("%s does have %s" % (ver_to, name), name in dst)

    # The table's value must be what the official file writes, not what reads
    # nicely.  Sample the target; the modal value is stable at 1/40.
    tally = dict((n, {}) for n in PG._ABSENT_DEFAULT)
    seen = 0
    for k in sorted(fr_to.unit_keys())[::40]:
        sp = fr_to.unit_span(k[0], k[1])
        if not sp:
            continue
        seen += 1
        f = UF.fields_at(raw_to, fr_to.gv, sp[0])
        for n in PG._ABSENT_DEFAULT:
            if n in f:
                v = f[n]["value"]
                tally[n][v] = tally[n].get(v, 0) + 1
    for name in new_names:
        want = PG._ABSENT_DEFAULT[name][0]
        got = tally[name]
        if not got:
            continue
        top = max(got.items(), key=lambda kv: kv[1])[0]
        check("%s writes %.6g for %s on %d of %d sampled records"
              % (ver_to, want, name, got.get(want, 0), seen),
              top == want and got.get(want, 0) * 2 > seen,
              (want, top, got.get(want, 0), seen))

    # One real 8.4 record through the port: every new field lands, none is a
    # guess, and nothing else was invented to go with it.
    hit = find_unit(fr_from, raw_from,
                    lambda f: "Type50.AttacksCount" in f
                    and "Creatable.TrainLocations.0.TrainTime" in f)
    if not check("%s carries a record with both a Type50 and a Creatable section"
                 % ver_from, hit is not None):
        return
    civ, uid, sp, _f = hit
    out, tape = PG.encode_unit(raw_from, sp[0], sp[1], fr_from.gv, fr_to.gv)
    got = UF.fields_at(out, fr_to.gv, 0)
    for name in sorted(PG._ABSENT_DEFAULT):
        if name not in got:
            continue
        want = PG._ABSENT_DEFAULT[name][0]
        check("ported %s/%s carries %.6g in %s" % (civ, uid, want, name),
              abs(float(got[name]["value"]) - float(want)) < 1e-6,
              (got[name]["value"], want))
        check("ported %s/%s reports %s as filled, not missing" % (civ, uid, name),
              name in tape.absent and name not in tape.missing,
              (name in tape.absent, name in tape.missing))
    check("the ported record leaves nothing for the tape to guess",
          not tape.missing, tape.missing[:6])


def id_fields_are_not_folded():
    """The id renumbering must see the folded group's id slots, and only those."""
    check("Creatable.TrainLocations.N.UnitID is an id field",
          PG.is_id_field("Creatable.TrainLocations.0.UnitID"))
    check("Creatable.TrainLocations.N.HotKeyID is NOT an id field",
          not PG.is_id_field("Creatable.TrainLocations.0.HotKeyID"))
    check("ResearchLocations.N.LocationID is NOT an id field",
          not PG.is_id_field("ResearchLocations.0.LocationID"))



def planner_follows_rename(ver_to, raw_to, fr_to, ver_old, raw_old, fr_old):
    """The planner addresses a field by the BASE file's name, so a rename is not a deletion.

    upgrade.py diffs two files byte by byte and then looks each differing field
    up in the TARGET file by name.  When the target renamed that field, the
    lookup misses and the edit is reported as "the new version has no such
    field" -- the author's number is dropped even though the tape happily lays
    the same field out one level down.  Measured on 209785 (8.4 -> 8.9): 54
    author edits of Creatable.HotKeyFromUnit perished that way.

    So what is asserted here is the planner's own resolution, not the tape's:
    given an edit addressed by the OLD name, _resolve must land on the byte the
    NEW name occupies.  Byte offsets, because a wrong-but-plausible offset is
    exactly the failure mode that silently rewrites a neighbouring field.
    """
    # ---- forward: Creatable.HotKeyFromUnit (8.4) -> TrainLocations.0.HotKeyID (8.9)
    picked = None
    for key in sorted(fr_to.unit_keys(), key=lambda k: (str(k[0]), int(k[1]))):
        span = fr_to.unit_span(key[0], key[1])
        if not span:
            continue
        fields = fr_to.unit_fields(span[0], span[1])
        names = {n: (o, w) for o, w, n in fields}
        if "Creatable.TrainLocations.0.HotKeyID" in names:
            picked = (key, names)
            break
    if picked is None:
        check("a %s unit carries the folded hotkey slot" % ver_to, False)
        return
    (civ, uid), names = picked
    want_off, want_w = names["Creatable.TrainLocations.0.HotKeyID"]
    edit = {"space": "unit", "civ": civ, "unit": uid, "index": None,
            "key": None, "field": "Creatable.HotKeyFromUnit", "rel": 0,
            "width": want_w}
    got = UP._resolve(fr_to, edit)
    check("%s %s/%d resolves Creatable.HotKeyFromUnit to its renamed cell"
          % (ver_to, civ, uid), got == want_off, (got, want_off))

    # A byte diff emits the narrowest differing run, so a 2-byte slice inside
    # the 4-byte hotkey is the normal case (measured: 5a41 -> c43e).  The
    # resolution must shift by rel rather than insist the slice fills the cell.
    edit["rel"], edit["width"] = 2, 2
    got = UP._resolve(fr_to, edit)
    check("%s the resolution keeps a partial slice at the right offset" % ver_to,
          got == want_off + 2, (got, want_off + 2))

    # ---- a name both generations spell the same must still resolve directly
    edit = {"space": "unit", "civ": civ, "unit": uid, "index": None,
            "key": None, "field": "HitPoints", "rel": 0, "width": 2}
    got = UP._resolve(fr_to, edit)
    check("%s an unrenamed field resolves by name alone" % ver_to,
          got == names["HitPoints"][0], (got, names.get("HitPoints")))

    # ---- reverse: ResearchLocations.0.LocationID (8.9) -> ResearchLocation (8.4)
    picked = None
    for i in range(min(fr_old.tech_count(), 4000)):
        fields = fr_old.tech_fields(i)
        names = {n: (o, w) for o, w, n in fields}
        if "ResearchLocation" in names:
            picked = (i, names)
            break
    if picked is None:
        check("a %s tech carries the scalar research location" % ver_old, False)
        return
    idx, names = picked
    want_off, want_w = names["ResearchLocation"]
    edit = {"space": "tech", "civ": None, "unit": None, "index": idx,
            "key": None, "field": "ResearchLocations.0.LocationID", "rel": 0,
            "width": want_w}
    got = UP._resolve(fr_old, edit)
    check("%s tech %d resolves ResearchLocations.0.LocationID back to ResearchLocation"
          % (ver_old, idx), got == want_off, (got, want_off))

def main():
    paths = shelf()
    if not paths:
        print("SKIP: no archived builds (run the tool once, or set "
              "AOE2MOD_ARCHIVE_DIR)")
        return 2

    print("=== 0. the fold table")
    id_fields_are_not_folded()
    check("NO_HOTKEY is the value 8.4 called 'no hotkey'", PG.NO_HOTKEY == 16000,
          PG.NO_HOTKEY)

    parsed = {}
    unparseable = {}
    for ver in sorted(paths):
        if ver not in P.VER_TO_GV:
            unparseable[ver] = "no generation number"
            continue
        try:
            parsed[ver] = (paths[ver],) + load(ver, paths[ver])
        except Exception as exc:                       # noqa: BLE001
            unparseable[ver] = "%s: %s" % (type(exc).__name__, exc)
    if unparseable:
        note("archived builds upgrade.Frame cannot parse (pre-existing parser "
             "limit, not this module's subject)", unparseable)
    missing = [v for v in MUST_PARSE if v not in parsed]
    check("the generations this suite stands on still parse", not missing, missing)

    print("=== 1. same-generation round trip")
    for ver in MUST_PARSE:
        if ver in parsed:
            _p, raw, fr = parsed[ver]
            round_trip(ver, raw, fr)

    print("=== 2. the folds, forward (fixed slot -> counted group)")
    if "VER 8.4" in parsed and "VER 8.9" in parsed:
        _p, raw8, fr8 = parsed["VER 8.4"]
        _q, rawn, frn = parsed["VER 8.9"]
        fold_forward("VER 8.4", raw8, fr8, "VER 8.9", rawn, frn)
        no_invented_counts("VER 8.4", raw8, fr8, "VER 8.9")
    else:
        print("  SKIP: need an 8.4 and an 8.9 build on the shelf")

    print("=== 3. the folds, reverse (counted group -> fixed slot)")
    if "VER 8.9" in parsed and "VER 8.4" in parsed:
        _q, rawn, frn = parsed["VER 8.9"]
        _p, raw8, fr8 = parsed["VER 8.4"]
        fold_reverse("VER 8.9", rawn, frn, "VER 8.4", raw8, fr8)
    else:
        print("  SKIP: need an 8.9 and an 8.4 build on the shelf")

    print("=== 4. fields the newer generation added (measured, not zeroed)")
    # 7.8, not 8.4: the whole Type50 damage-reflection / friendly-fire block and
    # the Creatable button block already exist at 8.4 (the 8.4-vs-8.9 name diff
    # is only the train-location group), so 8.4 cannot exercise the fill path.
    # 7.8 is the oldest archived build that both parses and lacks those fields.
    if "VER 7.8" in parsed and "VER 8.9" in parsed:
        _p, raw7, fr7 = parsed["VER 7.8"]
        _q, rawn, frn = parsed["VER 8.9"]
        absent_defaults("VER 7.8", raw7, fr7, "VER 8.9", rawn, frn)
    else:
        print("  SKIP: need a 7.8 and an 8.9 build on the shelf")

    print("=== 5. the planner follows a rename instead of calling it a deletion")
    # The tape and the planner are two different readers of the same fold table.
    # A fold that lands in the product but is never addressed by the diff still
    # loses the author's number, which is how 209785 lost 54 hotkeys.
    if "VER 8.9" in parsed and "VER 8.4" in parsed:
        _q, rawn, frn = parsed["VER 8.9"]
        _p, raw8, fr8 = parsed["VER 8.4"]
        planner_follows_rename("VER 8.9", rawn, frn, "VER 8.4", raw8, fr8)
    else:
        print("  SKIP: need an 8.9 and an 8.4 build on the shelf")

    print()
    if FAILS:
        print("PORTGEN: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("PORTGEN: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

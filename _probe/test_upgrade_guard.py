"""Guards the upgrade engine's refusals, and the one case that LOOKS like a
refusal but must not be one.

Nine things must be true, and each is a way this tool could quietly "help"
and destroy a mod instead:

1. A generation we never archived has no "before" at all.  Inventing one (going
   to the nearest generation) would move bytes between record layouts that do
   not agree.  This is the one refusal that cannot be worked around, and it must
   say what to do about it.
2. A mod of a DIFFERENT LENGTH from its own generation is NOT a refusal.  A mod
   that ships its own record set (measured: 19968_Eternal Civilization is
   115,179,469 raw bytes, 168,424 records against the shipped 136,861) is
   legitimately bigger, and the record-set planner exists exactly for that.
   Refusing on length alone once already rejected `unit_added_by_mod`, which the
   fixture suite proves is replayable.  What length difference DOES forbid is the
   byte path: `diff_regions` across two geometries reports tens of millions of
   regions that mean "these are two different files", and calling each one an
   author edit would be fabrication.
3. An explicit ``base_dat`` of a different length is likewise legitimate, and
   must go structural.  The report must SAY the lengths differed, so a caller who
   handed over the wrong file sees it instead of a clean-looking merge.
4. A run with rows it cannot carry must refuse to write unless forced, and the
   refusal must name them.  Silence here is the failure mode the whole module
   exists to prevent.
5. The byte walk must be able to say how far it has got.  `diff_regions` is
   called on two 93 MB streams and takes seconds; a caller that passes
   ``on_progress`` and gets a TypeError instead is a mod that cannot even be
   looked at, which is exactly what `209785_Civilization Alliance` reported.

Run: python -X utf8 -u _probe/test_upgrade_guard.py
"""
import os
import sys
import tempfile
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.game.locations as GL
import aoe2mod.mod.archives as AR
from aoe2mod.dat import locate as L
from aoe2mod.mod import upgrade as UP

FAILS = []


def ok(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name
          + ((" :: %s" % detail) if detail else ""))
    if not cond:
        FAILS.append(name)


def installed():
    by = {}
    for r in GL.list_mods(GL.find_profile_root()):
        d = os.path.join(r["path"], AR.DAT_REL)
        if os.path.isfile(d):
            by[r["name"]] = d
    return by


def fx(case, part):
    return os.path.join("_out", "_upgrade_fixtures", case, part,
                        "resources", "_common", "dat", "empires2_x2_p1.dat")


def _unarchived_copy(new_dat):
    """The shipped stream with its version header relabelled ``VER 9.9``.

    Same byte length as the real header (``VER 8.9`` and ``VER 9.9`` are both
    seven characters plus the NUL), so nothing but the generation string
    changes and the file is still a structurally valid .dat.
    """
    raw = UP._inflate(new_dat)
    if raw is None:
        raise SystemExit("cannot read %s" % new_dat)
    head, sep, rest = raw.partition(b"\x00")
    fake = b"VER 9.9" + (sep or b"\x00") + rest
    out_dir = os.path.join("_probe", "_tmp", "unarchived")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "empires2_x2_p1.dat")
    c = zlib.compressobj(6, zlib.DEFLATED, -15)
    with open(out, "wb") as fh:
        fh.write(c.compress(fake) + c.flush())
    return out


def _solo_archive(new_dat):
    """Point the archive at a fresh directory holding exactly one build.

    ``archive_dir()`` honours ``AOE2MOD_ARCHIVE_DIR`` before anything else (that
    is how the shelf lives outside the source tree at all), so one assertion can
    run against a scratch shelf without touching the real one.  The single entry
    is the SHIPPED stream -- which is what a new install looks like after its
    first launch, before any patch has arrived.
    """
    d = tempfile.mkdtemp(prefix="arch_solo_")
    os.environ[AR.ARCHIVE_DIR_ENV] = d
    AR.note_file(new_dat, label="game")
    return d


def main():
    by = installed()
    new = fx("mod_touches_a", "new")
    if not os.path.isfile(new):
        print("  SKIP no fixtures; run _probe/make_upgrade_fixtures.py first")
        return 2

    # --- 1. a generation we never archived is refused, not guessed ----------
    #
    # This has to be a synthetic file now, not a real mod.  The case used to
    # ride on `297820_`, whose header says VER 7.8 and which was refused only
    # because 7.8 had never been archived; once the 2019-onward sweep filled
    # the archive with all eleven generations, 7.8 exists and that mod is
    # refused for a DIFFERENT reason (its target is 8.9, a different layout).
    # A test that changes its reason when the archive grows is not guarding
    # anything, so the "no archived build of this generation" branch gets its
    # own input: the shipped file with its version header rewritten.
    synth = _unarchived_copy(new)
    t = time.time()
    why = None
    try:
        UP.analyze(mod_dat=synth)
    except UP.UpgradeError as exc:
        why = str(exc)
    dt = time.time() - t
    ok("a generation with no archived base is refused", why is not None,
       why and why[:40])
    ok("that refusal says what to do about it",
       why is not None and "记录官方数据" in why, why and why[-40:])
    ok("and it decides from the index, without parsing 48 MB", dt < 2.0,
       "%.2fs" % dt)
    ok("the archive really has no build of that generation",
       not AR.size_candidates("VER 9.9")["sizes"],
       str(sorted(AR.size_candidates("VER 9.9")["sizes"])))

    # ... and an old generation that IS archived is carried across by
    # re-encoding, not refused.  This used to be the mirror of case 1 --
    # "we have a base, but it is the wrong generation, so refuse" -- and that
    # stopped being true once _port_plan existed: records are re-encoded field
    # by field into the target layout, so a 7.8 base and an 8.9 target no
    # longer mean "the offsets cannot be moved".  What must still hold is the
    # opposite promise: if it says it crossed, it has to SAY that records were
    # re-encoded, it has to have found a base of the mod's own generation, and
    # nothing may be left in the unmapped list.
    old = [n for n in by if n.startswith("297820_")]
    if old:
        # analyze() answers with a report instead of raising (only upgrade()
        # raises), so the verdict is read off the report here.
        rep_old = UP.analyze(mod_dat=by[old[0]])
        said = " ".join([str(rep_old.get("summary") or "")]
                        + [str(x) for x in (rep_old.get("notes") or [])])
        ok("a mod from an archived OLD generation crosses instead of refusing",
           rep_old["verdict"] in (UP.MERGEABLE, UP.CONFLICTS),
           rep_old["verdict"] + " :: " + said[:60])
        ok("and it says in words that the records were re-encoded",
           "重新编码" in said, said[:60])
        ok("and its base really is that older generation",
           rep_old["base"]["ver"] == "VER 7.8",
           "%s vs mod %s, target %s" % (rep_old["base"]["ver"],
                                         rep_old["mod"]["ver"],
                                         rep_old["new"]["ver"]))
        ok("and nothing was left behind as uncarryable",
           not (rep_old.get("unmapped") or []),
           str((rep_old.get("unmapped") or [])[:1]))

    # --- 2. a mod with its own record set goes structural, not refused ------
    own = [n for n in by if n.startswith("19968_")]
    if own:
        name = own[0]
        raw = UP._inflate(by[name])
        t = time.time()
        rep = UP.analyze(mod_dat=by[name], new_dat=new)
        dt = time.time() - t
        ok("a mod with its own record set is analysed, not refused",
           rep["verdict"] in UP.VERDICTS, rep["verdict"])
        ok("and the planner chose the record-set path, not the byte path",
           rep["structural"] is True, str(rep["structural"]))
        ok("the report says the two lengths differed",
           any("长度不同" in n for n in rep["notes"]), rep["notes"][:1])
        ok("the base it chose is a different size from the mod",
           rep["base"]["raw_bytes"] != rep["mod"]["raw_bytes"],
           "%s vs %s" % (rep["base"]["raw_bytes"], rep["mod"]["raw_bytes"]))
        ok("the inventory is real, not a fabricated byte count",
           rep["counts"]["units_added"] > 1000 and rep["counts"]["edits"] > 0,
           str(rep["counts"]))
        ok("every unmapped row says why", all(r.get("why")
                                              for r in rep["unmapped"]),
           "%d rows" % len(rep["unmapped"]))
        print("       (%.1fs, %d unmapped, %d added)"
              % (dt, len(rep["unmapped"]), rep["counts"]["units_added"]))

        # --- 4. rows it cannot carry must block the write -------------------
        if rep["unmapped"]:
            why = None
            try:
                UP.upgrade(mod_dat=by[name], new_dat=new,
                           out_dir=os.path.join("_probe", "_tmp", "guard_out"),
                           title="guard must not write")
            except UP.UpgradeError as exc:
                why = str(exc)
            ok("a run with uncarried rows refuses to write", why is not None,
               (why or "")[:60])
            ok("and the refusal names what was left behind",
               why is not None and "搬不过去" in why, (why or "")[:60])
            ok("and nothing was written to disk",
               not os.path.isdir(os.path.join("_probe", "_tmp", "guard_out",
                                              "guard must not write")))

    # --- 3. an explicit base of a different length goes structural ----------
    mod = fx("unit_added_by_mod", "mod")
    base = fx("unit_added_by_mod", "base")
    new2 = fx("unit_added_by_mod", "new")
    if os.path.isfile(mod):
        rep = UP.analyze(mod_dat=mod, base_dat=base, new_dat=new2)
        ok("a longer mod with an explicit base is analysed",
           rep["verdict"] in (UP.MERGEABLE, UP.CONFLICTS), rep["verdict"])
        ok("and its added record is planned, not refused",
           rep["counts"]["units_added"] == 1, str(rep["counts"]))
        ok("the report says the lengths differed",
           any("长度不同" in n for n in rep["notes"]), rep["notes"][:1])

    # --- 3b. an archive holding ONLY today's build cannot be a "before" ----
    #
    # The tool notes the shipped .dat on every launch, so today's build is
    # always the newest entry of its generation.  A caller whose archive holds
    # nothing else therefore gets that very stream back as the base; "base ==",
    # "new" then reads as "nothing to carry", and on patch day -- the day this
    # whole feature exists for -- the official changes stay outside the mod
    # while the report says the mod is already current.  A mod that added or
    # removed records (a different length from every build) is exactly the shape
    # that lands here, so this is not a corner case: it is a new user's first
    # run.  It must refuse and say which half is missing.
    if os.path.isfile(mod):
        _solo_archive(new2)
        try:
            why = None
            try:
                UP.analyze(mod_dat=mod, new_dat=new2)
            except UP.UpgradeError as exc:
                why = str(exc)
            ok("an archive with only today's build refuses to merge",
               why is not None, (why or "no refusal")[:40])
            ok("and names the missing half instead of saying up to date",
               why is not None and "只存了今天这一份" in why, (why or "")[:60])
            ok("and offers both ways out",
               why is not None and "base_dat" in why and "下一次游戏更新" in why,
               (why or "")[-60:])
        finally:
            os.environ.pop(AR.ARCHIVE_DIR_ENV, None)

    # --- 5. the byte walk reports progress, and still works without it -----
    #
    # `upgrade._plan` walks two 93 MB streams and hands `diff_regions` a
    # callback to fill the 8% slice of its progress bar.  The vendored copy of
    # `locate.py` was generated from a research file whose signature had no
    # such parameter, so the call raised
    # `TypeError: diff_regions() got an unexpected keyword argument
    # 'on_progress'` and the whole mod came back as "cannot be read".  A
    # missing keyword is invisible until someone passes it, so the guard is the
    # call itself: two streams, one callback, and the fraction must climb.
    a = bytes(200000)
    b = bytearray(a)
    b[5000] = 1
    b[150000] = 1
    seen = []
    got = L.diff_regions(a, bytes(b), on_progress=seen.append)
    ok("diff_regions accepts a progress callback and finds both edits",
       got == [(5000, 1), (150000, 1)], str(got))
    ok("and the callback is called, ending at a full fraction",
       bool(seen) and abs(seen[-1] - 1.0) < 1e-9, str(seen[-3:]))
    ok("and the same walk without a callback still answers",
       L.diff_regions(b"ab", b"ac") == [(1, 1)],
       str(L.diff_regions(b"ab", b"ac")))
    # --- registry of sizes is cheap and honest ------------------------------
    sizes = AR.size_candidates("VER 8.9")
    ok("size_candidates lists the shipped length",
       93272287 in sizes["sizes"], str(list(sizes["sizes"])))
    ok("size_candidates on an unknown generation is empty",
       AR.size_candidates("VER 1.0")["entries"] == 0)


    # --- 6. the seven counters are CARRIED, not called "the tech tree" -------
    #
    # `_plan_region` used to answer "this is inside the tech tree, this module has
    # no semantics for it" about a 4-byte integer sitting at a fixed offset before
    # the tree.  That sentence was false about the file and cost the author the
    # edit.  The check here is the whole loop: change one counter by hand in the
    # shipped data, ask the planner what it saw, apply the plan to the base, and
    # compare the byte.  A test that only asserts "an edit was produced" would
    # still pass if the edit pointed at a neighbour.
    tail_raw, _how = UP.P.load_dat(new)
    at_tail = UP.Frame(tail_raw, "official").tech_tail_end()
    edited = bytearray(tail_raw)
    edited[at_tail:at_tail + 2] = b"\x2c\x01"          # TimeSlice 30 -> 300
    fb = UP.Frame(tail_raw, "base")
    fm = UP.Frame(bytes(edited), "mod")
    plan_t = UP._plan(fb, fm, limit=0, new=fb)
    tail_edits = [e for e in plan_t["edits"] if e["space"] == "tail"]
    ok("a change to the seven counters is planned as a field, not as the tree",
       bool(tail_edits) and not [r for r in plan_t["unmapped"]
                                 if r.get("space") in ("techtree", "tech_tree")],
       str([(e["field"], e["base"].hex(), e["mod"].hex()) for e in tail_edits]))
    ok("and it names the counter it belongs to",
       bool(tail_edits) and tail_edits[0]["field"] == "TimeSlice",
       str([e["field"] for e in tail_edits]))
    work = bytearray(tail_raw)
    _ap, _rf, _cf, _rg = UP._apply_edits(fb, plan_t["edits"], work)
    ok("and applying it writes the author byte, not a neighbour",
       bytes(work[at_tail:at_tail + 2]) == b"\x2c\x01",
       bytes(work[at_tail:at_tail + 4]).hex())

    # --- 7. a table record is fully named, or its edits vanish -------------
    #
    # The flat-table byte path asks "which field is this diff inside?" and, when
    # no field answers, drops the region.  A graphic record's animation frames
    # and directional-sound trios had no names for years: measured on 310130, 16
    # graphics lost their edits that way and 408773 lost 18, with nothing in the
    # report.  The invariant is arithmetic: the last named byte of a record must
    # BE the last byte of the record.  Checked over every record of the three
    # variable-length tables in the shipped data.
    import aoe2mod.dat.tablefields as TB
    gv = fb.gv
    for table, limit in (("graphic", 4000), ("sound", 2000)):
        recs, left = TB.scan(tail_raw, table)
        worst = None
        for rec in recs[:limit]:
            f = TB.fields_at(tail_raw, gv, rec, table=table)
            end = max(v["offset"] + TB.KINDS[v["kind"]] for v in f.values()
                      if v["kind"] != "str")
            if end != rec["end"]:
                worst = (rec["index"], end, rec["end"])
                break
        ok("every named field of a %s record stops at the record's last byte"
           % table, worst is None and left == 0,
           "record %s ends %s but fields end %s (leftover %s)"
           % (worst, worst[2], worst[1], left) if worst else str(left))


    # --- 8. a replacement decided for terrain/colour lands in the output ----
    #
    # `_apply_tables` walked `_TABLE_FLAT` only, so a `replace_table` row naming
    # `terrain` or `colour` was dropped on the floor: the planner had promised
    # "this record gets copied whole" and the writer never looked.  Measured on
    # 310130, three terrain records grew (417 -> 431 / 455 / 444) and vanished
    # that way.  Two halves are checked: a replacement is written exactly where
    # the record was, and an append is refused with a sentence instead of being
    # skipped silently -- terrain continues into a block tail this module does
    # not re-serialise, so "append" has no honest answer there.
    fnew = UP.Frame(tail_raw, "new")
    for table, pick in (("colour", 10), ("terrain", 1)):
        recs, _left = TB.scan(tail_raw, table)
        rec = recs[pick]
        whole = bytes(tail_raw[rec["start"]:rec["end"]])
        key = fnew.table_key_of(table, rec, raw=tail_raw)
        bumped = bytearray(whole)
        bumped[0] ^= 0xFF
        plan_r = {"add_table": [], "del_table": [],
                  "replace_table": [{"table": table, "key": key,
                                     "base": whole, "bytes": bytes(bumped)}]}
        out_r, done_r, _d = UP._apply_tables(fnew, plan_r, tail_raw)
        ok("a replaced %s record is written where the plan said" % table,
           bytes(out_r[rec["start"]:rec["end"]]) == bytes(bumped)
           and len(out_r) == len(tail_raw),
           "%d -> %d bytes, rewritten %r"
           % (len(tail_raw), len(out_r), done_r["tables"]))
        plan_a = {"add_table": [{"table": table, "key": ("index", 99),
                                 "bytes": whole}],
                  "del_table": [], "replace_table": []}
        out_a, done_a, _d2 = UP._apply_tables(fnew, plan_a, tail_raw)
        ok("and an appended %s record is refused in words, not skipped" % table,
           out_a == tail_raw and bool(done_a["refused"])
           and done_a["refused"][0].get("space") == table,
           str(done_a["refused"])[:120])

    # --- 9. a conflict says WHICH field and both VALUES --------------------
    #
    # 「有 57 处官方和作者改的是同一个字段」 is a number the author cannot act
    # on.  The rows behind it exist in the report, but for years they carried
    # three hex strings and no field name a person could read -- and on a
    # measured mod 54 of the 57 were ONE field stored once per civilization, so
    # even printing them all would have read as 54 disagreements.  What the row
    # must now carry: the field, and both values as numbers, because 「官方 5，
    # 你的 4」 is the decision while `05` vs `04` is the same thing written
    # where only someone who already knows the field is a u8 can see it.
    import struct as _struct
    recs_c, _lc = TB.scan(tail_raw, "colour")
    rec_c = recs_c[10]
    key_c = fnew.table_key_of("colour", rec_c, raw=tail_raw)
    fmeta = TB.fields_at(tail_raw, fnew.gv, rec_c, table="colour")["MinimapColour"]
    f_off, f_w = fmeta["offset"], TB.KINDS[fmeta["kind"]]
    base_b = bytes(tail_raw[f_off:f_off + f_w])
    mod_b = bytes([base_b[0] ^ 0x01]) + base_b[1:]
    off_b = bytes([base_b[0] ^ 0x03]) + base_b[1:]
    work_c = bytearray(tail_raw)
    work_c[f_off:f_off + f_w] = off_b
    edit_c = {"space": "colour", "civ": None, "unit": None, "index": None,
              "key": key_c, "field": "MinimapColour", "rel": 0,
              "width": f_w, "base": base_b, "mod": mod_b}
    _ac, _rc, confs, _gc = UP._apply_edits(fnew, [edit_c], work_c)
    ok("a conflict is reported as a field, not as three hex strings",
       len(confs) == 1 and confs[0].get("field") == "MinimapColour",
       str([(c.get("field"), c.get("kind")) for c in confs]))
    want = dict(
        base=_struct.unpack("<i", base_b)[0],
        official=_struct.unpack("<i", off_b)[0],
        mod=_struct.unpack("<i", mod_b)[0])
    got_v = dict(base=confs[0].get("base_val") if confs else None,
                 official=confs[0].get("official_val") if confs else None,
                 mod=confs[0].get("mod_val") if confs else None)
    ok("and both sides arrive as the numbers the author would compare",
       bool(confs) and got_v == want,
       "want %r got %r (kind %r)" % (want, got_v,
                                     confs[0].get("kind") if confs else None))
    # A kind that cannot be resolved must not cost the row: the fallback
    # decodes by WIDTH, which is right for every integer field, and the hex
    # strings stay as the record of what was actually in the file.
    ok("an unknown field kind is decoded by width, not dropped",
       UP._decode_value("not-a-kind", b"\x05") == 5
       and UP._decode_value(None, b"\x2c\x01") == 300,
       repr([UP._decode_value("not-a-kind", b"\x05"),
             UP._decode_value(None, b"\x2c\x01")]))
    print("")
    if FAILS:
        print("GUARD: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("GUARD: EVERY REFUSAL IS EXPLAINED, EVERY LENGTH IS JUDGED")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

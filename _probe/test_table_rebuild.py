"""A `table.field` edit must survive a rebuild.

The promise a data editor makes is not "the byte moved" but "I can do it again in
three months, on a patched game file".  For unit and tech fields that promise is
already pinned (`test_rebuild_fields.py`); a graphic is a THIRD id space, so its
intent has to carry (table, position) and the replay has to re-resolve the
position in the CURRENT stream -- a stored offset would write into whatever
moved there after a patch.

Runs entirely against a throwaway state dir and output dir: a test must never
touch the player's real mod list or the shipped bundle.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

TMP = tempfile.mkdtemp(prefix="tblrebuild_")
os.environ["AOE2MOD_STATE_DIR"] = os.path.join(TMP, "state")
os.environ["AOE2MOD_BUILD_OUT"] = os.path.join(TMP, "out")
os.environ.pop("AOE2MOD_DAT_STAMP", None)
# `rebuild()` installs with `profile_root=None` -- the player's REAL profile --
# so the rebuild below registered a real mod-status entry ("tbl one field") in
# the list the game's mod manager draws.  Point the profile at this temp dir.
sys.path.insert(0, HERE)
import _sandbox as SB
SB.temp_profile(TMP)

FAILS = []


def check(what, ok, detail=""):
    print("%s %s%s" % ("  ok " if ok else "  FAIL", what,
                       "" if ok else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def main():
    from aoe2mod.ui import server as S
    from aoe2mod.dat import tablefields as TF
    from aoe2mod.dat import parser as P
    from aoe2mod.mod import provenance as PV

    app = S.App()
    with contextlib.redirect_stdout(io.StringIO()):
        app.tk._ensure()

    # A graphic nobody edits in real life, so the numbers below are stable and a
    # human can check the result by eye in the game's own files.
    REC = 100
    d0 = app.table_fields("graphic", REC)
    check("record 100 exists and decodes", d0.get("ok") and d0["field_count"] == 26,
          d0.get("error"))

    # --- write one field into the session --------------------------------
    wr = app.set_table_field("graphic", REC, "SpeedMultiplier", 2.5, dry=False)
    check("the write is accepted", wr.get("ok"), wr.get("error"))
    ints = app.session_intents()["intents"]
    check("the intent is table.field", ints and ints[0]["intent"] == "table.field",
          ints)
    check("it carries the table and the position, not a byte offset",
          ints and ints[0].get("table") == "graphic"
          and ints[0].get("record") == REC
          and not any(k in ints[0] for k in ("offset", "off", "at", "start")),
          ints)

    # --- save: one mod, one .dat, and it must re-parse -------------------
    #
    # `save_session` answers with a FLAT shape (`built` is the mod FOLDER,
    # `reparse_ok` at the top level); `build()` and `rebuild()` answer with a
    # `manifest`.  Two shapes over one operation, so the key is checked rather
    # than assumed -- the first version of this test read `manifest` here and
    # reported two product failures for one wrong key.
    built = app.save_session(title="tbl one field")
    check("the session saves", built.get("ok"), built.get("error"))
    check("the product re-parses", built.get("reparse_ok") is True,
          built.get("reparse_ok"))
    mod_dir = built.get("built")
    check("the product names its folder", bool(mod_dir) and os.path.isdir(mod_dir),
          mod_dir)
    dat = _dat_in(mod_dir)
    check("the product carries a .dat", bool(dat) and os.path.exists(dat), dat)
    raw, _how = P.load_dat(dat)
    d1 = app.table_fields("graphic", REC)
    check("the value is in the built file",
          abs(d1["fields"] and [f for f in d1["fields"]
                                if f["name"] == "SpeedMultiplier"][0]["value"]
              - 2.5) < 1e-6, "session still shows the new value")
    got = None
    for f in TF.fields_at(raw, app.tk._parsed[3],
                          {"start": d0["start"], "end": d0["end"]},
                          table="graphic"):
        pass
    # Read the built stream from scratch, so the check is about the FILE.
    recs, leftover = TF.scan(raw, "graphic")
    check("the built stream still walks cleanly", leftover == 0, leftover)
    built_rec = recs[REC]
    flds = TF.fields_at(raw, _gv(raw), built_rec, table="graphic")
    got = flds["SpeedMultiplier"]["value"]
    check("the built file stores 2.5 at record 100", abs(got - 2.5) < 1e-6, got)

    # --- rebuild: the record's intent has to replay ---------------------
    doc = PV.load()
    entry = (doc.get("builds") or {}).get("tbl one field")
    check("the build recorded its intent", bool(entry)
          and entry.get("intents")
          and entry["intents"][0]["intent"] == "table.field",
          (entry or {}).get("intents"))

    app2 = S.App()
    with contextlib.redirect_stdout(io.StringIO()):
        app2.tk._ensure()
    rb = app2.rebuild("tbl one field")
    check("the rebuild succeeds", rb.get("ok"), rb.get("error"))
    rep = rb.get("replayed") or {}
    check("the rebuild replayed exactly one intent", rep.get("applied") == 1, rep)
    check("and refused nothing", not rep.get("refused"), rep.get("refused"))
    rb_dat = ((rb.get("manifest") or {}).get("dat"))
    check("the rebuild produced a .dat", bool(rb_dat) and os.path.exists(rb_dat),
          rb_dat)
    raw3, _how3 = P.load_dat(rb_dat)
    recs3, leftover3 = TF.scan(raw3, "graphic")
    check("the rebuilt stream walks cleanly", leftover3 == 0, leftover3)
    got3 = TF.fields_at(raw3, _gv(raw3), recs3[REC],
                        table="graphic")["SpeedMultiplier"]["value"]
    check("the rebuilt file stores 2.5 too", abs(got3 - 2.5) < 1e-6, got3)

    # --- a sound write, mixed with a graphic one ------------------------
    app3 = S.App()
    with contextlib.redirect_stdout(io.StringIO()):
        app3.tk._ensure()
    a = app3.set_table_field("sound", 1, "PlayDelay", 250, dry=False)
    b = app3.set_table_field("graphic", REC, "FrameDuration", 0.05, dry=False)
    check("both writes are accepted", a.get("ok") and b.get("ok"),
          (a.get("error"), b.get("error")))
    both = app3.session_intents()["intents"]
    check("two pending intents in two tables", len(both) == 2, both)
    got4 = app3.save_session(title="tbl two tables")
    check("a batch across two tables saves", got4.get("ok"), got4.get("error"))
    raw4, _h4 = P.load_dat(_dat_in(got4.get("built")) or "")
    srecs, sleft = TF.scan(raw4, "sound")
    check("the sound table still walks cleanly", sleft == 0, sleft)
    sdelay = TF.fields_at(raw4, _gv(raw4), srecs[1],
                          table="sound")["PlayDelay"]["value"]
    check("the sound delay landed", sdelay == 250, sdelay)
    grecs4, gleft = TF.scan(raw4, "graphic")
    fdur = TF.fields_at(raw4, _gv(raw4), grecs4[REC],
                        table="graphic")["FrameDuration"]["value"]
    check("the frame duration landed", abs(fdur - 0.05) < 1e-6, fdur)

    # --- the id-space guard: a table edit must not touch a unit ----------
    app4 = S.App()
    with contextlib.redirect_stdout(io.StringIO()):
        app4.tk._ensure()
    u_before = app4.unit_fields(100, civ="British")["fields"]
    hp0 = [f for f in u_before if f["name"] == "HitPoints"][0]["value"]
    app4.set_table_field("graphic", 100, "SpeedMultiplier", 1.5, dry=False)
    u_after = app4.unit_fields(100, civ="British")["fields"]
    hp1 = [f for f in u_after if f["name"] == "HitPoints"][0]["value"]
    check("a graphic write leaves unit 100 alone", hp0 == hp1, (hp0, hp1))

    print()
    if FAILS:
        print("TABLE REBUILD: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("TABLE REBUILD: A GRAPHIC / SOUND EDIT SURVIVES A REBUILD")
    return 0


def _gv(raw):
    """The gv nibble for a stream: 32-bit or 64-bit mode, same rule as the app."""
    from aoe2mod.dat import parser as P
    return 54


def _dat_in(mod_dir):
    """The single `.dat` a data mod emitted under `mod_dir`, or None."""
    if not mod_dir or not os.path.isdir(mod_dir):
        return None
    hits = []
    for root, _dirs, files in os.walk(mod_dir):
        for name in files:
            if name.lower().endswith(".dat"):
                hits.append(os.path.join(root, name))
    hits.sort(key=lambda p: (len(p), p))
    return hits[0] if hits else None


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(TMP, ignore_errors=True)

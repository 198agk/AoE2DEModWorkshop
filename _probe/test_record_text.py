# -*- coding: utf-8 -*-
"""改显示文字: the words go in, and the id is the server's job.

WHY THIS EXISTS
---------------
`LanguageDLLName` is an i32 that means "row N of a string table beside the
.dat".  The column editor has always offered the integer, which is legal to
write and points at nothing: the game then prints the bare number.  Before this
feature the only way to change 「显示的名字」 was to hand-write a row into
`key-value-modded-strings-utf8.txt` and type its id into the box.

`/api/record-text` takes the words, allocates the id, writes the table row and
points the record at it.  What this suite pins:

  * a dry run resolves every copy and ALLOCATES NOTHING (a preview that burned
    an id would leave an orphan in the shipped table every time someone looked);
  * a real write lands in the session buffer AND in the table, and the pane can
    read the words back before anything is saved;
  * 保存成 mod ships the table with the .dat -- an id is meaningless alone;
  * a rebuild re-allocates against the CURRENT game and ships its own table,
    because the id the first build wrote was allocated in a process that is
    gone.

Run:  python -X utf8 _probe/test_record_text.py
"""
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

TMP = os.path.join(os.environ.get("TEMP") or "/tmp", "aoe2mod-record-text")
STATE = os.path.join(TMP, "state")
OUT = os.path.join(TMP, "out")
STATE_ENV = "AOE2MOD_STATE_DIR"
OUT_ENV = "AOE2MOD_BUILD_OUT"

sys.path.insert(0, HERE)
import _sandbox as SB

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    if got == want:
        return check(label, True)
    return check("%s :: %r" % (label, want), False, "got %r" % (got,))


def fresh():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(STATE)
    os.makedirs(OUT)
    with io.open(os.path.join(STATE, "builds.json"), "w", encoding="utf-8") as f:
        f.write(u'{"builds":{}}')


def table_rows(mod_dir):
    """`{id: text}` from whatever this mod ships, over every locale it wrote."""
    out = {}
    root = os.path.join(mod_dir, "resources")
    for loc in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, loc, "strings", "key-value",
                            "key-value-modded-strings-utf8.txt")
        if not os.path.isfile(path):
            continue
        with io.open(path, encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("//") or " \"" not in line:
                    continue
                head, rest = line.split(" ", 1)
                if not head.isdigit():
                    continue
                out[int(head)] = rest.strip().strip('"').replace('\\"', '"')
    return out


def strings_shipped(mod_dir):
    """The tables this mod FOLDER really wrote, one per locale.

    `save_session` answers with `built` (a path) and not with the emitter's
    manifest, so the folder is the thing to look at -- the manifest's `files`
    list is an emitter-side detail a caller of the route never sees.
    """
    out = []
    root = os.path.join(mod_dir, "resources")
    for loc in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        rel = "resources/%s/strings/key-value/key-value-modded-strings-utf8.txt" % loc
        if os.path.isfile(os.path.join(mod_dir, *rel.split("/"))):
            out.append(rel)
    return out


def main():
    fresh()
    os.environ[STATE_ENV] = STATE
    os.environ[OUT_ENV] = OUT
    SB.temp_profile(TMP)

    from aoe2mod.ui.server import App
    a = App()
    a.reset_session()

    # A unit that exists in the British run, picked at runtime: hard-coding an id
    # would make this suite fail on a patch that renumbers one, and the point
    # here is the text path, not that unit's identity.
    uid = None
    for (ci, u), _r in a._unit_index().items():
        if ci == a.tk._civ_index("British"):
            uid = u
            break
    check("found a unit in the British run", uid is not None, str(uid))

    print("\n=== 1. a dry run names the copies and allocates nothing ===")
    d = a.set_record_text("unit", uid, "LanguageDLLName", "测试名字甲",
                          civ="British", dry=True)
    check("the dry run is accepted", d.get("ok") is True, str(d.get("error")))
    eq("it reports one copy", d.get("copies"), 1)
    eq("it previews no id", d.get("string_id"), None)
    eq("and nothing was allocated", len(a._new_strings), 0)
    check("it says what the record says today",
          isinstance(d.get("was_text"), str), repr(d.get("was_text")))
    eq("nothing is pending after a preview", len(a.pending_edits()), 0)

    print("\n=== 2. a real write allocates an id and the pane can read it back ===")
    w = a.set_record_text("unit", uid, "LanguageDLLName", "测试名字乙",
                          civ="British", dry=False)
    check("the write is accepted", w.get("ok") is True, str(w.get("error")))
    sid = w.get("string_id")
    check("it got an id", isinstance(sid, int), repr(sid))
    eq("the id is one nobody shipped", sid > 30030001, True)
    eq("the words are readable back", a._text_of(sid), "测试名字乙")
    eq("one edit is pending", len(a.pending_edits()), 1)
    note = a.pending_edits()[0]
    eq("the note carries the words", note.get("text"), "测试名字乙")
    eq("it is marked as a rename, so undo re-reads the display ids",
       note.get("op"), "rename")

    print("\n=== 3. the field table shows the words, not only the number ===")
    # This is the half the player sees: 「名称文本编号 30030002」 alone is what
    # made the old screen unusable.
    got = a.set_record_text("unit", uid, "LanguageDLLName", "别的话",
                            civ="British", dry=True)
    eq("a second preview reuses nothing", got.get("string_id"), None)
    e = a.pending_edits()[0]
    eq("still one edit, not two", len(a.pending_edits()), 1)
    eq("the earlier words survived the preview", e.get("text"), "测试名字乙")

    print("\n=== 4. 保存成 mod ships the table beside the .dat ===")
    saved = a.save_session(title="text one unit")
    check("the build produced a mod", saved.get("ok") is True,
          str(saved.get("error")))
    built = saved.get("built") or ""
    rels = strings_shipped(built)
    check("a string table went with it", bool(rels), str(rels))
    rows = table_rows(built)
    eq("the table holds the words", rows.get(sid), "测试名字乙")

    print("\n=== 5. the .dat really points at that row ===")
    dat = os.path.join(built, "resources", "_common", "dat",
                       "empires2_x2_p1.dat") if saved.get("carries_dat") else ""
    if check("the mod carries a .dat", bool(dat) and os.path.isfile(dat), str(dat)):
        from aoe2mod.dat import parser as P
        from aoe2mod.dat import locate as L
        from aoe2mod.dat import fieldwrite as FW
        raw, _how = P.load_dat(dat)
        civs, _cs, gv, _tail = L.locate(bytes(raw), parser=None)
        idx = FW.index("unit", bytes(raw), gv)
        hit = None
        for (ci, u2), r in idx.items():
            if u2 != uid:
                continue
            nm = civs[ci].get("name") if 0 <= ci < len(civs) else str(ci)
            if nm == "British":
                hit = FW.fields_at("unit", bytes(raw), gv, r).get("LanguageDLLName")
        check("the British copy is in the rebuilt file", hit is not None, str(hit))
        eq("and its name id is the one the table carries",
           (hit or {}).get("value"), sid)

    print("\n=== 6. a rebuild re-allocates and ships its own table ===")
    from aoe2mod.mod import provenance as PV
    entry = (PV.load().get("builds") or {}).get("text one unit") or {}
    it = (entry.get("intents") or [{}])[0]
    # THE POINT: the id is NOT what a rebuild can use.  It was allocated in this
    # process; the table row it names exists only in the folder this build wrote.
    eq("the intent carries the words", it.get("text"), "测试名字乙")
    r = a.rebuild("text one unit")
    check("the rebuild succeeds", r.get("ok") is True, str(r.get("error")))
    man2 = r.get("manifest") or {}
    eq("no edit was refused", (r.get("replayed") or {}).get("refused"), [])
    eq("one edit was replayed", (r.get("replayed") or {}).get("applied"), 1)
    rows2 = table_rows(man2.get("mod_dir") or "")
    check("the rebuilt mod carries a table", bool(rows2), str(sorted(rows2)[:4]))
    if rows2:
        eq("and the words are in it", "测试名字乙" in rows2.values(), True)
    dat2 = man2.get("dat")
    if check("the rebuild emitted a .dat", bool(dat2), str(dat2)):
        from aoe2mod.dat import parser as P
        from aoe2mod.dat import locate as L
        from aoe2mod.dat import fieldwrite as FW
        raw, _how = P.load_dat(dat2)
        civs, _cs, gv, _tail = L.locate(bytes(raw), parser=None)
        idx = FW.index("unit", bytes(raw), gv)
        hit = None
        for (ci, u2), rec in idx.items():
            if u2 != uid:
                continue
            nm = civs[ci].get("name") if 0 <= ci < len(civs) else str(ci)
            if nm == "British":
                hit = FW.fields_at("unit", bytes(raw), gv, rec).get("LanguageDLLName")
        sid2 = (hit or {}).get("value")
        check("the rebuilt .dat names some id", isinstance(sid2, int), repr(sid2))
        # The id may or may not equal the first build's -- what matters is that
        # it resolves to the words in the table THIS folder ships.
        eq("and that id resolves to the words in this folder",
           rows2.get(sid2), "测试名字乙")

    print("\n=== 7. refusals say what is wrong, in Chinese ===")
    bad = a.set_record_text("unit", uid, "HitPoints", "几个字", civ="British")
    eq("a number column is not a text column", bad.get("ok"), False)
    check("and the sentence names the usable ones",
          "能写文字的是" in (bad.get("error") or ""), str(bad.get("error")))
    bad = a.set_record_text("unit", uid, "LanguageDLLName", "   ", civ="British")
    eq("empty text is refused", bad.get("ok"), False)
    bad = a.set_record_text("building", uid, "LanguageDLLName", "几个字")
    eq("a third kind is refused", bad.get("ok"), False)
    bad = a.set_record_text("tech", 999999, "LanguageDLLName", "几个字")
    eq("a missing technology is refused", bad.get("ok"), False)

    print("")
    if FAILS:
        print("RECORD TEXT: %d FAILED" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("RECORD TEXT: THE WORDS GO IN AND THE ID IS THE SERVER'S JOB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

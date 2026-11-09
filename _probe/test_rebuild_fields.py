# -*- coding: utf-8 -*-
"""A field edit must survive being rebuilt months later.

WHY THIS EXISTS
---------------
Storing the intents is the whole promise of the mod panel: after an official
patch the player should not have to remember the sentence they wrote weeks ago.
But the field editor (the unit/tech column tables) does not go through the intent
compiler at all -- it writes straight into the session buffer, because "set this
named field of record N to V" is not a shape any sentence resolves to.  So a
build recorded from it carries intents the compiler REJECTS.

Measured 2026-10-30: `/api/rebuild` handed those intents to `C.resolve()` and
died with "unknown intent" -- that message was the only thing a player saw for
all nine field builds in `builds.json`.  Nine of nine historical builds were
unrebuildable, and the tool reported it as a data problem.

The decision this suite pins: a rebuild must NOT store byte offsets.  After a
patch the records move, and an offset resolved against the old file writes into
a neighbouring field while reporting success.  What is stored is (which record,
which field name, what value), and it is re-located in the CURRENT file.

Run:  python -X utf8 _probe/test_rebuild_fields.py
"""
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

TMP = os.path.join(os.environ.get("TEMP") or "/tmp", "aoe2mod-rebuild-fields")
STATE = os.path.join(TMP, "state")
OUT = os.path.join(TMP, "out")
STATE_ENV = "AOE2MOD_STATE_DIR"
OUT_ENV = "AOE2MOD_BUILD_OUT"

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def fresh():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(STATE)
    os.makedirs(OUT)
    with io.open(os.path.join(STATE, "builds.json"), "w", encoding="utf-8") as f:
        f.write(u'{"builds":{}}')


def main():
    fresh()
    # Both overrides exist because two runners at once would otherwise share
    # `_mods_out/<title>` and delete each other's output, and a test must never
    # write into the player's real builds record.
    os.environ[STATE_ENV] = STATE
    os.environ[OUT_ENV] = OUT

    from aoe2mod.ui.server import App
    a = App()

    print("\n=== 1. a pure field build is recorded, then rebuilt ===")
    a.reset_session()
    w = a.set_unit_field(1810, "HitPoints", 137, civ="British", dry=False)
    check("the field write is accepted", w.get("ok") is True, str(w.get("error")))
    eq("it went to memory only", len(a.pending_edits()), 1)
    saved = a.save_session(title="rb one field")
    check("the build produced a mod", saved.get("ok") is True,
          str(saved.get("error")))
    check("and the emitted file re-parses to its last byte",
          saved.get("reparse_ok") is True, str(saved.get("reparse_ok")))
    recorded = (saved.get("provenance") or {}).get("title")
    eq("provenance recorded the build", recorded, "rb one field")

    print("\n=== 2. what was stored is a NAME, not a byte offset ===")
    from aoe2mod.mod import provenance as PV
    doc = PV.load()
    entry = (doc.get("builds") or {}).get("rb one field") or {}
    intents = entry.get("intents") or []
    eq("one intent was stored", len(intents), 1)
    it = intents[0] if intents else {}
    eq("it names the record's own kind", it.get("intent"), "unit.field")
    eq("it names the unit", it.get("unit"), 1810)
    eq("it names the field", it.get("field"), "HitPoints")
    eq("it carries the value", it.get("value"), 137)
    eq("it names the civilization", it.get("civ"), "British")
    # THE POINT OF THIS ASSERTION: a stored offset is a lie after a patch, and
    # it would be a lie that reports success.  Nothing downstream may depend on
    # one, so nothing upstream may record one.
    check("it stores NO byte offset",
          not any(k in it for k in ("offset", "off", "start", "at")),
          str(sorted(it.keys())))

    print("\n=== 3. the rebuild replays it into the CURRENT file ===")
    r = a.rebuild("rb one field")
    check("the rebuild succeeds", r.get("ok") is True, str(r.get("error")))
    # `reparse_ok` lives in the MANIFEST, not at the top level: `_emit_replay`
    # sets it on the manifest and `_build_reply` nests the manifest under
    # `manifest`.  Reading it off the reply would say None forever and look like
    # a broken rebuild.
    check("and its output re-parses",
          ((r.get("manifest") or {}).get("reparse_ok")) is True,
          str((r.get("manifest") or {}).get("reparse_ok")))
    eq("one edit was replayed", (r.get("replayed") or {}).get("applied"), 1)
    eq("none was refused", (r.get("replayed") or {}).get("refused"), [])
    # Read the emitted file back and check the number, not the report: a report
    # that says 137 while the bytes say 25 is exactly the failure this is for.
    dat = (r.get("manifest") or {}).get("dat")
    check("the rebuild emitted a .dat", bool(dat), str(dat))
    if dat:
        from aoe2mod.dat import parser as P
        from aoe2mod.dat import locate as L
        from aoe2mod.dat import fieldwrite as FW
        raw, _how = P.load_dat(dat)
        civs, _cs, gv, _tail = L.locate(bytes(raw), parser=None)
        idx = FW.index("unit", bytes(raw), gv)
        found = None
        for (ci, uid), rec in idx.items():
            if uid != 1810:
                continue
            got = FW.fields_at("unit", bytes(raw), gv, rec).get("HitPoints")
            nm = civs[ci].get("name") if 0 <= ci < len(civs) else str(ci)
            if nm == "British":
                found = got
        check("the British copy of the villager is in the rebuilt file",
              found is not None, str(found))
        eq("and its HitPoints really is 137", (found or {}).get("value"), 137)

    print("\n=== 4. a blanket edit replays all 63 copies, not one ===")
    a.reset_session()
    w = a.set_unit_field(1810, "HitPoints", 150, civ="*", dry=False)
    check("the blanket write is accepted", w.get("ok") is True, str(w.get("error")))
    eq("it says how many copies it spans", w.get("copies"), 63)
    saved = a.save_session(title="rb all civs")
    check("the build produced a mod", saved.get("ok") is True,
          str(saved.get("error")))
    doc = PV.load()
    entry = (doc.get("builds") or {}).get("rb all civs") or {}
    it = (entry.get("intents") or [{}])[0]
    eq("the intent keeps the blanket flag", it.get("civ_all"), True)
    # Storing 63 expanded intents would lose the meaning the moment a
    # civilization is added; storing the FLAG and re-locating every copy is what
    # makes the rebuild produce the same mod the first build did.
    check("and does not expand into 63 entries", len(entry.get("intents") or []) == 1,
          str(len(entry.get("intents") or [])))
    r = a.rebuild("rb all civs")
    check("the blanket rebuild succeeds", r.get("ok") is True,
          str(r.get("error")))
    # `replayed.applied` counts INTENTS, not copies: a blanket edit is one intent
    # that lands on 63 records, which is exactly why it is stored as a flag.
    # Reading `applied` as the copy count would say "1" for a mod that changed 63
    # villagers.  The byte-level truth is checked below, on the emitted file.
    rep = (r.get("replayed") or {}).get("applied")
    eq("it counts one INTENT", rep, 1)
    dat = (r.get("manifest") or {}).get("dat")
    if dat:
        from aoe2mod.dat import parser as P
        from aoe2mod.dat import locate as L
        from aoe2mod.dat import fieldwrite as FW
        raw, _how = P.load_dat(dat)
        civs, _cs, gv, _tail = L.locate(bytes(raw), parser=None)
        idx = FW.index("unit", bytes(raw), gv)
        hits = 0
        for (ci, uid), rec in idx.items():
            if uid != 1810:
                continue
            got = FW.fields_at("unit", bytes(raw), gv, rec).get("HitPoints")
            if (got or {}).get("value") == 150:
                hits += 1
        print("     copies of the villager holding 150: %d" % hits)
        check("every civilization's copy really holds 150", hits == 63, str(hits))

    print("\n=== 5. mixed build: sentences first, field writes laid on top ===")
    a.reset_session()
    w = a.set_unit_field(1810, "HitPoints", 160, civ="British", dry=False)
    check("the field write is accepted", w.get("ok") is True, str(w.get("error")))
    saved = a.save_session(title="rb mixed")
    check("the field build produced a mod", saved.get("ok") is True,
          str(saved.get("error")))
    # Append a plain sentence intent to the SAME record, simulating the mixed
    # case the real panel produces when a player uses both screens.
    doc = PV.load()
    entry = dict((doc.get("builds") or {}).get("rb mixed") or {})
    entry["intents"] = list(entry.get("intents") or []) + [
        {"intent": "tech.research_time", "tech": 22, "value": 30}]
    doc.setdefault("builds", {})["rb mixed"] = entry
    PV.save(doc)
    r = a.rebuild("rb mixed")
    check("a mixed rebuild succeeds", r.get("ok") is True, str(r.get("error")))
    check("and its output re-parses",
          ((r.get("manifest") or {}).get("reparse_ok")) is True,
          str((r.get("manifest") or {}).get("reparse_ok")))
    check("the field edit is still accounted for",
          (r.get("replayed") or {}).get("applied") is not None,
          str(r.get("replayed")))

    print("\n=== 6. a field that no longer exists is REFUSED, never approximated ===")
    doc = PV.load()
    entry = dict((doc.get("builds") or {}).get("rb one field") or {})
    entry["intents"] = [{"intent": "unit.field", "unit": 1810,
                         "field": "NoSuchField", "value": 1, "civ": "British"}]
    doc.setdefault("builds", {})["rb one field"] = entry
    PV.save(doc)
    r = a.rebuild("rb one field")
    rep = r.get("replayed") or {}
    eq("nothing was applied", rep.get("applied"), 0)
    refused = rep.get("refused") or []
    check("and the refusal names the field", bool(refused), str(refused))
    check("a rebuild that cannot do the work does not claim it did",
          r.get("ok") is True and rep.get("applied") == 0, str(rep))

    print("\n=== 7. a build with no record says so ===")
    r = a.rebuild("no such build at all")
    eq("it is refused", r.get("ok"), False)
    check("with a sentence a player can act on",
          u"\u8bb0\u5f55" in (r.get("error") or ""), str(r.get("error")))

    shutil.rmtree(TMP, ignore_errors=True)
    print()
    if FAILS:
        print("REBUILD FIELDS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("REBUILD FIELDS: A FIELD EDIT IS STORED AS (record, field, value) AND "
          "RE-LOCATED IN THE CURRENT FILE -- NEVER AS A BYTE OFFSET")
    return 0


if __name__ == "__main__":
    sys.exit(main())

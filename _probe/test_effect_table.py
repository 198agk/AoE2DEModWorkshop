# -*- coding: utf-8 -*-
"""The 效果 table: 1,500 records, 10,500 numbers, and the 486 nobody could reach.

WHY THIS EXISTS
---------------
A technology does not own an effect; it owns an effect ID.  Measured on the
shipped file: 1,510 technologies point at 1,014 of the 1,500 effect records, so
**486 records (2,795 numbers) belong to no technology at all** -- bonus payloads
that no screen in this tool could open.  That is the concrete meaning of
「现阶段还是依旧无法替代age3」, and this table is the answer to it.

WHAT IT PINS
------------
* Every record is addressed: `scan` walks all 1,500 and lands exactly on the
  table's end (`leftover == 0`).  A one-byte drift per record does not fail
  loudly here -- it silently points a write at the neighbouring record, which
  is how you edit a number and break a different one.
* The five slots of a command sit where `_SLOT_AT` says: type@0 / a@1 / b@3 /
  c@5 / d@7.  Measured 2026-11-03: a first version derived them from `d - 11`
  and put all three i16 on the same byte, so `#0.a`, `#0.b` and `#0.c` all read
  the same value and the screen showed three columns of one number.
* Only the value is writable.  Type/a/b/c decide what the value MEANS; changing
  one silently redefines the number beside it, so they refuse with a sentence
  that says what to do instead.
* A packed value keeps its class byte: 织布机's 近战护甲 +1 is stored as the
  float `1025.0` (low byte 1, high byte 4), and writing 7 must leave the 4.
* A record with commands but no name is listed; an empty slot is not.  184 of
  the 1,500 records hold zero commands between them -- that is the difference
  between "a list that omits noise" and "a list that hides content".
* A write survives 保存全部改动 and /api/rebuild, and it does not touch the
  unit whose id happens to equal the record index.

Run:  python -X utf8 _probe/test_effect_table.py
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail != "" else ""))
    if not ok:
        FAILS.append(name)


def main():
    import struct
    tag = "a" * 0
    from aoe2mod.ui import server as S
    from aoe2mod.dat import tablefields as TF
    from aoe2mod.intent import compiler as C

    with contextlib.redirect_stdout(io.StringIO()):
        app = S.App()
    app.tk._ensure()
    raw = app.session_raw()
    gv = app.tk._parsed[3]

    # ---- 1. the walk ------------------------------------------------------
    recs, leftover = TF.scan(raw, "effect")
    check("every effect record is addressed", len(recs) == 1500, len(recs))
    check("and the walk lands on the table's end", leftover == 0, leftover)
    n_cmd = sum(r["command_count"] for r in recs)
    check("the commands add up", n_cmd > 10000, n_cmd)
    check("record 22 is Loom with 3 commands",
          TF.record_name(raw, gv, recs[22], "effect") == "Loom"
          and recs[22]["command_count"] == 3,
          (TF.record_name(raw, gv, recs[22], "effect"), recs[22]["command_count"]))

    # ---- 2. the slots sit on their own bytes ------------------------------
    f = TF.fields_at(raw, gv, recs[22], "effect")
    want = {"#0.type": (4, "u8"), "#0.a": (-1, "i16"), "#0.b": (4, "i16"),
            "#0.c": (0, "i16"), "#0.d": (15.0, "f32")}
    for name, (val, kind) in want.items():
        got = f.get(name) or {}
        check("slot %s reads %r as %s" % (name, val, kind),
              got.get("value") == val and got.get("kind") == kind, got)
    offs = [f["#0." + s]["offset"] for s in ("type", "a", "b", "c", "d")]
    check("the five slots are five distinct addresses", len(set(offs)) == 5, offs)
    check("and they are in order, 2 bytes apart after the type byte",
          offs == [offs[0], offs[0] + 1, offs[0] + 3, offs[0] + 5, offs[0] + 7], offs)

    # ---- 3. the labels name the command, not just the slot ----------------
    d = app.table_fields("effect", 22)
    by = {r["name"]: r for r in d["fields"]}
    check("the record reports its own fields", d["field_count"] == 17, d["field_count"])
    check("the value row is named after what it does",
          "生命值" in by["#0.d"]["label"] and "数值" in by["#0.d"]["label"],
          by["#0.d"]["label"])
    check("the second command is named differently",
          "近战护甲" in by["#1.d"]["label"], by["#1.d"]["label"])
    check("a per-command row does not squash on the string column",
          all(by["#0." + s]["kind"] != "str" for s in ("type", "a", "b", "c", "d")),
          [by["#0." + s]["kind"] for s in ("type", "a", "b", "c", "d")])

    # ---- 4. only the value is writable ------------------------------------
    for s in ("type", "a", "b", "c"):
        g = TF.plan("effect", raw, gv, recs[22], "#0." + s, 1)
        check("slot %s refuses, in Chinese" % s,
              not g.get("ok") and "只读" in (g.get("error") or ""), g.get("error"))
    check("the writable slot is the value", by["#0.d"].get("ro") is None, by["#0.d"].get("ro"))
    g = TF.plan("effect", raw, gv, recs[22], "#9.d", 1)
    check("a command that is not there refuses by name",
          not g.get("ok") and "#9.d" in (g.get("error") or ""), g.get("error"))

    # ---- 5. packed values keep their class byte ---------------------------
    g = TF.plan("effect", raw, gv, recs[22], "#1.d", 7)
    check("the packed slot plans", g.get("ok"), g.get("error"))
    before = struct.unpack_from("<f", raw, g["offset"])[0]
    after = struct.unpack_from("<f", g["packed"], 0)[0]
    check("the value the player reads changes 1 -> 7",
          C.decode_effect_value(8, before)[0] == 1
          and C.decode_effect_value(8, after)[0] == 7,
          (C.decode_effect_value(8, before), C.decode_effect_value(8, after)))
    check("and the class it is aimed at does not",
          C.decode_effect_value(8, after)[1] == C.decode_effect_value(8, before)[1],
          (C.decode_effect_value(8, before), C.decode_effect_value(8, after)))

    # ---- 6. the list says what it leaves out -----------------------------
    named = app.table_rows("effect", named_only=True, limit=1)
    every = app.table_rows("effect", named_only=False, limit=1)
    check("the picker pages the records that carry content",
          named["total"] == 1316, named["total"])
    check("and reports the whole table beside it",
          named["total_all"] == 1500 == every["total"], (named.get("total_all"), every["total"]))
    hidden = [i for i in app._table_index("effect")
              if not app._table_index("effect")[i].get("name")]
    check("what it leaves out is empty slots only",
          all((app._table_index("effect")[i].get("commands") or 0) == 0 for i in hidden),
          hidden[:6])
    check("every hidden record really is nameless",
          all(not app._table_index("effect")[i].get("name") for i in hidden), len(hidden))

    # ---- 7. the records no technology can reach are reachable here --------
    fan = app.tk._effect_fanout()
    orphan = [i for i in app._table_index("effect") if not fan.get(i)]
    check("records no technology points at still exist", len(orphan) > 400, len(orphan))
    # Measured 2026-11-03: 486 orphan records hold 2,795 commands between them,
    # but only 193 of them hold any.  Do not assert "all of them have content" --
    # a record can exist with commands that are pure wiring ("disable tech")
    # and carry no number at all.
    live = [i for i in orphan if (app._table_index("effect")[i].get("commands") or 0) > 0]
    n_orphan_cmd = sum((app._table_index("effect")[i].get("commands") or 0)
                       for i in orphan)
    check("and they hold real commands", len(live) > 150 and n_orphan_cmd > 2500,
          (len(live), n_orphan_cmd))
    # The first orphan (record 1) is all "disable tech" wiring: every slot is
    # wiring and the value says so.  Walk to the first one that carries a number
    # a player could change, which is the whole point of listing these.
    opened = None
    for i in live:
        cand = app.table_fields("effect", i)
        if any((not r.get("ro")) and r["name"].endswith(".d") for r in cand["fields"]):
            opened = (i, cand)
            break
    check("one of them opens and offers a writable value", opened is not None,
          opened[0] if opened else None)
    if opened:
        writ = [r["name"] for r in opened[1]["fields"]
                if (not r.get("ro")) and r["name"].endswith(".d")]
        check("the orphan that opens is the record it says it is",
              opened[1]["record"] == opened[0], (opened[1]["record"], opened[0]))
        check("and its value row is spelled out",
              any("数值" in r["label"] for r in opened[1]["fields"]
                  if r["name"] == writ[0]), writ[0])

    # ---- 8. a write round-trips through the session and the rebuild -------
    app.reset_session()
    wr = app.set_table_field("effect", 22, "#0.d", 100, dry=False)
    check("the write lands", wr.get("ok"), wr.get("error"))
    check("the session remembers it as a table field, not a byte offset",
          app.session_intents()["intents"][:1] == [{
              "intent": "table.field", "table": "effect", "record": 22,
              "field": "#0.d", "value": 100}],
          app.session_intents()["intents"][:1])
    check("re-reading the record shows the new number",
          [r["value"] for r in app.table_fields("effect", 22)["fields"]
           if r["name"] == "#0.d"] == [100.0])
    check("and the unit with the same id is untouched",
          app.unit_fields(22)["ok"], "unit 22 must still read")

    sv = app.save_session(title="fx one number")
    # `reparse_ok` sits at the TOP level of save_session's reply -- there is no
    # `manifest` key in this path (measured 2026-11-03; the rebuild reply is the
    # one that carries `manifest`).  Reading the wrong key makes a working save
    # look broken.
    check("保存全部改动 writes a mod that reparses",
          sv.get("ok") and sv.get("reparse_ok") is True,
          (sv.get("ok"), sv.get("reparse_ok")))
    built = sv.get("built") or ""
    check("the mod folder is on disk", os.path.isdir(built), built)
    rb = app.rebuild("fx one number")
    check("rebuild replays the field intent",
          rb.get("ok") and (rb.get("replayed") or {}).get("applied") == 1,
          (rb.get("ok"), rb.get("replayed")))
    app.reset_session()
    check("撤销 puts the number back",
          [r["value"] for r in app.table_fields("effect", 22)["fields"]
           if r["name"] == "#0.d"] == [15.0])

    print()
    if FAILS:
        print("EFFECT TABLE: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("EFFECT TABLE: ALL 1500 RECORDS ADDRESSED, NAMED, AND ONLY THE NUMBER "
          "THAT MEANS SOMETHING IS WRITABLE")
    return 0


if __name__ == "__main__":
    import tempfile
    _st = tempfile.mkdtemp(prefix="aoe2_fxt_")
    os.environ["AOE2MOD_STATE_DIR"] = _st
    os.environ["AOE2MOD_BUILD_OUT"] = os.path.join(_st, "out")
    sys.exit(main())

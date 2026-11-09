# -*- coding: utf-8 -*-
"""The three tables nobody could open: 地形 200×19, 通行表 54×670, 颜色 16×9.

WHY THIS EXISTS
---------------
User said (2026-11-03) 「依旧不足，你自己查一下，对比一下」.  The comparison
found this product edits 5 record spaces and AGE3 lists 13.  The largest
concrete gaps that needed no new parsing at all -- the numbers were already in
`Parser.parse()` -- were 地形 (200 records × 19 fields), 地形通行表 (54 records
× 670 numbers = 134 terrain kinds × (1 multiplier + 4 pass numbers)) and
玩家颜色 (16 × 9).  None of those 14,616 numbers could be reached from any
screen.

WHAT IT PINS
------------
* Each table walks to its own end: `leftover == 0`.  A one-byte drift per
  record points every later write at the wrong record, which is how a tool
  edits one thing and breaks another.  Measured 2026-11-03: the restriction
  walk was off by exactly 2 bytes because `_colour_count_at()` returns the
  offset of the count field itself, not of the data after it.
* `地形通行表` record width is 2,680 bytes = 134 slots × 20 bytes, and every
  record reports 670 numbers.  The slot count is derived from the record's own
  width, never hardcoded: the first version called `P.TERRAINS_USED1_DEFAULT`,
  which does not exist, so the whole table raised AttributeError.
* Labels are Chinese and specific: 「地形 7 的伤害倍率」 not 「Mult.7」.  The 670
  field names are `Mult.<n>` / `Pass.<n>.<what>`, so the lookup has to match by
  PREFIX -- a suffix lookup finds none of them.
* Record names are readable: 地形 uses its own debug string (`Grass`), 通行表
  has no name in the file so it says 「第 N 张通行表」, 颜色 says the colour
  (「绿（颜色 2）」).
* A read-only field refuses with a sentence that says why (the terrain shape
  pointer is a runtime memory address; storing it means nothing).
* A write lands on the byte it named, survives 保存全部改动, and does not touch
  the unit / tech / graphic whose id equals the record index.

Run:  python -X utf8 _probe/test_new_tables.py
"""
import contextlib
import io
import os
import sys
import tempfile

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
    tmp = tempfile.mkdtemp(prefix="aoe2_newtables_")
    os.environ["AOE2MOD_STATE_DIR"] = tmp
    os.environ["AOE2MOD_BUILD_OUT"] = os.path.join(tmp, "out")
    from aoe2mod.ui import server as S
    from aoe2mod.dat import tablefields as TF

    with contextlib.redirect_stdout(io.StringIO()):
        app = S.App()
        app.tk._ensure()
    tk = app.tk
    gv = tk._parsed[3]
    raw = app.session_raw()

    # ---- A. every record space is walked to the exact end ----------------
    for table, n in (("terrain", 200), ("restriction", 54), ("colour", 16)):
        recs, left = TF.scan(raw, table)
        check("%s: all %d records, exact end" % (table, n),
              len(recs) == n and left == 0, (len(recs), left))

    trecs = TF.scan(raw, "terrain")[0]
    rrecs = TF.scan(raw, "restriction")[0]
    crecs = TF.scan(raw, "colour")[0]

    # ---- B. field inventory --------------------------------------------
    f = TF.fields_at(raw, gv, trecs[1], "terrain")
    check("terrain: 19 numbers", len(f) == 19, len(f))
    check("terrain: every one has a Chinese label",
          all(TF.meta_for("terrain", k).get("zh") for k in f),
          [k for k in f if not TF.meta_for("terrain", k).get("zh")])
    check("terrain: 形状指针 is read-only",
          bool(TF.meta_for("terrain", "ShapePtr").get("ro")),
          TF.meta_for("terrain", "ShapePtr"))

    f = TF.fields_at(raw, gv, rrecs[1], "restriction")
    mult = [k for k in f if k.startswith("Mult.")]
    pas = [k for k in f if k.startswith("Pass.")]
    check("restriction: 670 numbers = 134 multipliers + 536 pass values",
          len(f) == 670 and len(mult) == 134 and len(pas) == 536,
          (len(f), len(mult), len(pas)))
    check("restriction: labels name the terrain kind, not the field",
          "地形" in TF.meta_for("restriction", "Mult.7").get("zh", ""),
          TF.meta_for("restriction", "Mult.7"))
    check("restriction: a pass label says which number it is",
          "行走" in TF.meta_for("restriction", "Pass.7.Walk").get("zh", ""),
          TF.meta_for("restriction", "Pass.7.Walk"))
    check("restriction: 2,680 bytes a record = 134 x 20",
          (rrecs[1]["end"] - rrecs[1]["start"]) == 2680,
          rrecs[1]["end"] - rrecs[1]["start"])

    f = TF.fields_at(raw, gv, crecs[2], "colour")
    check("colour: 9 numbers", len(f) == 9, len(f))
    check("colour: 颜色编号 is read-only and 队伍色基色 is not",
          bool(TF.meta_for("colour", "ID").get("ro"))
          and not TF.meta_for("colour", "PlayerColorBase").get("ro"),
          (TF.meta_for("colour", "ID").get("ro"),
           TF.meta_for("colour", "PlayerColorBase").get("ro")))

    # ---- C. names ------------------------------------------------------
    names = [TF.record_name(raw, gv, r, "terrain") for r in trecs[:4]]
    check("terrain: names come from the file", names[0] == "Grass", names)
    check("restriction: says which table it is",
          TF.record_name(raw, gv, rrecs[0], "restriction") == "第 1 张通行表",
          TF.record_name(raw, gv, rrecs[0], "restriction"))
    cnames = [TF.record_name(raw, gv, r, "colour") for r in crecs[:4]]
    check("colour: names the colour", cnames[2].startswith("绿"), cnames)

    # ---- D. the numbers agree with what the parser read -----------------
    one = {k: v["value"] for k, v in
           TF.fields_at(raw, gv, trecs[1], "terrain").items()}
    check("terrain 1 is the shallow water the game names",
          one.get("Name") == "Water, Shallow" and one.get("IsWater") == 4,
          (one.get("Name"), one.get("IsWater")))
    two = {k: v["value"] for k, v in
           TF.fields_at(raw, gv, crecs[2], "colour").items()}
    check("colour 2 is the green the game uses",
          two.get("PlayerColorBase") == 241 and two.get("MinimapColour") == 48,
          two)

    # ---- E. plan / apply ------------------------------------------------
    bad = TF.plan("terrain", raw, gv, trecs[0], "ShapePtr", 1)
    check("terrain: the shape pointer refuses in words",
          not bad.get("ok") and "只读" in (bad.get("error") or ""),
          bad.get("error"))

    job = TF.plan("colour", raw, gv, crecs[2], "PlayerColorBase", 250)
    check("colour: a writable field plans one change",
          job.get("ok") and job.get("changed") == 1, job)
    off = job["offset"]
    body = bytearray(raw)
    TF.apply(body, off, job["packed"])
    check("colour: the byte it wrote is the byte it named",
          struct.unpack_from("<i", bytes(body), off)[0] == 250,
          struct.unpack_from("<i", bytes(body), off)[0])

    job = TF.plan("restriction", raw, gv, rrecs[1], "Pass.3.Walk", 77)
    check("restriction: a pass value plans", job.get("ok"), job)
    check("restriction: its label names the terrain kind",
          "地形" in (job.get("label") or ""), job.get("label"))

    job = TF.plan("terrain", raw, gv, trecs[1], "BlendPriority", 200)
    check("terrain: a blend priority plans", job.get("ok"), job)

    # ---- F. a real write through the App, then save ---------------------
    dry = app.set_table_field("terrain", 1, "BlendPriority", 200, dry=True)
    check("terrain: the dry run reports bytes and changes nothing",
          dry.get("ok") and dry.get("bytes_before") and dry.get("changes_dat"),
          (dry.get("bytes_before"), dry.get("changes_dat")))
    wr = app.set_table_field("terrain", 1, "BlendPriority", 200, dry=False)
    # The reply spells it `bytes_changed`, not `changed`: one byte moved, and
    # the key says which unit the number is in (`TF.plan` calls it `changed`).
    check("terrain: the write lands",
          wr.get("ok") and wr.get("bytes_changed") == 1, wr)
    check("terrain: one pending edit", len(app.pending_edits()) == 1,
          len(app.pending_edits()))
    ints = app.session_intents()["intents"]
    check("terrain: the replay record names record and field, never offsets",
          bool(ints) and ints[0].get("table") == "terrain"
          and ints[0].get("field") == "BlendPriority"
          and "offset" not in ints[0] and "off" not in ints[0], ints)
    live = app.session_raw()
    got = {k: v["value"] for k, v in
           TF.fields_at(live, gv, TF.scan(live, "terrain")[0][1], "terrain").items()}
    check("terrain: re-reading the live buffer shows the new number",
          got.get("BlendPriority") == 200, got.get("BlendPriority"))

    with contextlib.redirect_stdout(io.StringIO()):
        saved = app.save_session(title="new tables pin")
        app.reset_session()
    check("terrain: 保存全部改动 emits a mod that reparses",
          saved.get("ok") and saved.get("reparse_ok"), saved.get("reparse_ok"))

    # ---- G. the id spaces stay separate ---------------------------------
    with contextlib.redirect_stdout(io.StringIO()):
        again = S.App()
        again.tk._ensure()
    hp = [x for x in again.unit_fields(1)["fields"] if x["name"] == "HitPoints"]
    check("unit 1 is untouched by a write to terrain 1",
          not hp or hp[0]["value"] != 200, hp and hp[0]["value"])

    print()
    print("NEW TABLES: " + ("ALL PASSED" if not FAILS
                            else "%d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())

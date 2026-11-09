# -*- coding: utf-8 -*-
"""Every operation leaves exactly one line, and a broken log cannot fail it.

Reported 2026-11-09: 「那怎么记录每一次的操作，要不在工具目录创建一个专门的 log
文件夹」.  The record is written by `Handler._guard`, so no route can be added and
silently left out; this file guards the WRITER, which is the half a route test
cannot see.

What is asserted, and why each one has a measurement behind it:

  1. A record creates `log/` on demand and names the file after the day.  The
     folder does not ship with the tool: it has to appear on the first edit.
  2. The line parses back as one JSON object carrying time, pid and duration.
     A "readable log" the About page cannot parse is only half the promise.
  3. `detail` is a WHITELIST.  The first draft copied every payload key, so
     `/api/sprite` would have written a whole sprite family and `/api/icon-set`
     a PNG into a line a human reads.
  4. Preview routes (`/api/parse`, `/api/plan`, `/api/session-info`) are NOT
     recorded.  They are called on every keystroke; recording them buries the
     eleven edits that matter under four hundred previews.
  5. A 4 KB summary is clipped rather than written whole.
  6. A day file past `MAX_BYTES` is rolled to `.1` BEFORE the append, so the live
     file the page reads is never one operation behind.  The first version
     rotated after writing and the guard caught it: only `.1` existed and the
     fresh file was missing.
  7. A day file older than `KEEP_DAYS` is deleted.
  8. Every mutating route can produce a sentence with no payload and no result.
     A blank row is a record that says nothing, which is worse than no record.
  9. An unwritable log folder returns "" instead of raising.  Measured
     2026-11-09: the first draft let `OSError` out of `record()` and the page
     showed 「保存失败：Permission denied」 for a mod that had in fact been
     written -- the log broke the thing it was supposed to describe.

The sandbox is `tempfile.mkdtemp` and `AOE2MOD_LOG_DIR`, so this never appends to
the player's real record.
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FAILS = []


def check(name, ok, detail=""):
    print(("ok  " if ok else "FAIL") + " " + name
          + ((" :: " + str(detail)) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


def main():
    root = tempfile.mkdtemp(prefix="aoe2mod_log_")
    os.environ["AOE2MOD_LOG_DIR"] = root
    from aoe2mod import oplog as OPLOG
    OPLOG.configure(ROOT)

    try:
        check("the folder starts empty",
              not os.path.isdir(root) or not OPLOG.files())

        p = OPLOG.record(route="/api/field-set", ok=True,
                         summary="改字段：单位 74 的 生命值 40 → 777",
                         detail={"unit": 74},
                         ms=12.5)
        check("a record creates the folder and writes a file",
              bool(p) and os.path.isfile(p), p)
        check("the file name carries the day",
              os.path.basename(p).startswith(OPLOG.PREFIX)
              and p.endswith(OPLOG.SUFFIX), p)

        rows = OPLOG.tail(5)
        check("the line parses back as one JSON object",
              len(rows) == 1 and rows[0]["route"] == "/api/field-set", rows)
        check("it carries the time, pid and duration",
              all(k in rows[0] for k in ("t", "epoch", "pid", "ms")), rows[0])

        OPLOG.record(route="/api/field-set", ok=True, summary="y",
                     detail={"unit": 2, "dat_bytes": "A" * 100000,
                             "secret": "nope"})
        last = OPLOG.tail(1)[0]
        detail = last.get("detail") or {}
        check("an unlisted key never reaches the file",
              "secret" not in detail and "dat_bytes" not in detail, detail)
        check("the whitelisted keys survive", detail.get("unit") == 2, detail)

        check("/api/parse is not an operation", not OPLOG.logs("/api/parse"))
        check("/api/session-info is not an operation",
              not OPLOG.logs("/api/session-info"))
        check("/api/session-save is an operation", OPLOG.logs("/api/session-save"))

        before = len(OPLOG.tail(200))
        OPLOG.record(route="/api/session-reset", ok=True, summary="z")
        check("a second operation appends rather than replacing",
              len(OPLOG.tail(200)) == before + 1)

        OPLOG.record(route="/api/session-save", ok=True,
                     summary="s" * 4000)
        check("a 4 KB summary is clipped",
              len(OPLOG.tail(1)[0]["summary"]) <= OPLOG.DETAIL_MAX + 1,
              len(OPLOG.tail(1)[0]["summary"]))

        day = OPLOG.day_path()
        with io.open(day, "a", encoding="utf-8") as fh:
            fh.write("x" * (OPLOG.MAX_BYTES + 10) + "\n")
        OPLOG.record(route="/api/undo", ok=True, summary="roll")
        names = [f["name"] for f in OPLOG.files()]
        archived = [n for n in names if n.endswith(".1" + OPLOG.SUFFIX)]
        fresh = [n for n in names
                 if n.endswith(OPLOG.SUFFIX) and not n.endswith(".1" + OPLOG.SUFFIX)]
        check("an oversized day file is rolled to .1", bool(archived), names)
        check("and the line that triggered the roll lands in the LIVE file",
              bool(fresh), names)
        live = [r for r in OPLOG.tail(3) if r.get("summary") == "roll"]
        check("the triggering line is readable back", bool(live), OPLOG.tail(3))

        old = os.path.join(root, OPLOG.PREFIX + "2000-01-01" + OPLOG.SUFFIX)
        with io.open(old, "w", encoding="utf-8") as fh:
            fh.write('{"t": "2000-01-01 00:00:00"}\n')
        OPLOG._LAST_TRIM = 0.0
        OPLOG.record(route="/api/undo", ok=True, summary="trim")
        check("a day file older than KEEP_DAYS is deleted",
              not os.path.exists(old), OPLOG.files())

        for route in sorted(OPLOG._VERBS):
            line = OPLOG.summary_of(route, {}, {})
            check("%s has a sentence with no payload" % route,
                  bool(line.strip()), line)

        blocked = os.path.join(root, "blocked")
        with io.open(blocked, "w", encoding="utf-8") as fh:
            fh.write("not a folder")
        os.environ["AOE2MOD_LOG_DIR"] = blocked
        check("an unwritable log folder returns '' instead of raising",
              OPLOG.record(route="/api/undo", ok=True, summary="q") == "")

        check("the summary names the value that moved",
              "40 → 777" in OPLOG.summary_of(
                  "/api/field-set",
                  {"kind": "unit", "unit": 74, "field": "HitPoints"},
                  {"before": 40, "value": 777, "label": "生命值"}),
              OPLOG.summary_of("/api/field-set",
                               {"kind": "unit", "unit": 74},
                               {"before": 40, "value": 777}))
        check("a refused write says so instead of printing ? → ?",
              "没改成" in OPLOG.summary_of(
                  "/api/field-set", {"unit": 99999, "field": "Nope"},
                  {"ok": False, "error": "no such unit"}),
              OPLOG.summary_of("/api/field-set", {"unit": 99999},
                               {"ok": False}))
        check("a save names the mod and the count",
              "3 项改动" in OPLOG.summary_of(
                  "/api/session-save", {},
                  {"applied": 3, "info": {"Title": "单位「SPRMN」 生命值"}}),
              OPLOG.summary_of("/api/session-save", {},
                               {"applied": 3,
                                "info": {"Title": "单位「SPRMN」 生命值"}}))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if FAILS:
        print("OPLOG: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("OPLOG: EVERY OPERATION LEAVES ONE LINE, AND A BROKEN LOG FOLDER "
          "CANNOT FAIL AN OPERATION")
    return 0


if __name__ == "__main__":
    sys.exit(main())

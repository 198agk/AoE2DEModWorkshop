"""The 「找字段」 placeholder must name fields the record actually has.

WHY THIS PIN EXISTS
-------------------
The placeholder on the field-search box is the only copy on the editor screen
that promises something: type this, you will find it.  It is a ternary chain in
`aoe2mod/ui/static/index.html`, one branch per table, and it grew by copy: the
fallback branch was written when 图形 was the only table with a field search, so
every new table that forgot a branch inherited 「图形文件编号 / 帧数 / 播放速度」.

Measured 2026-11-04, before this pin: a 文明 record showed 图形's three examples
(a civ record has none of them), 地形 showed 「名称 / 水面」 (its fields are
地形名字 / 水域类型), 颜色 showed 「描边」 (its fields are 队伍色基色 /
单位轮廓色), and 效果 showed 「生命值」, which names one attribute class and
exists in 67 of 1,500 records.

The failure mode is quiet: the search box answers 「没有匹配的字段。」 to a query
the page itself suggested, and the player concludes the search is broken rather
than the sentence.  So this pin reads both sides -- the copy in the HTML and the
labels the server builds -- and requires every example to hit.

WHAT IT DOES NOT DO
-------------------
It does not require the examples to hit EVERY record.  An effect that names no
attribute has no 生命值 row, and that is a fact about the record, not about the
sentence.  One hit across the table's records is what makes the promise true.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import aoe2mod.ui.server as S                      # noqa: E402
from aoe2mod.dat import tablefields as TF          # noqa: E402

FAILS = []


def ck(what, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (("  ::  %r" % (detail,))
                                                    if not ok else ""))
    if not ok:
        FAILS.append((what, detail))


#: How many records of each table to open.  A promise is kept by one hit, so a
#: sample is enough for the big tables; the small ones are read whole.
SAMPLE = {"graphic": 120, "sound": 120, "task": 240, "effect": 1500}


def placeholder_map():
    """`{table: [example, ...]}` read out of the page's own ternary chain."""
    src = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"), encoding="utf-8").read()
    # The chain is `d.table === "x" ? "搜字段名，例如 a / b / c"` repeated, with
    # the last one a bare string.  Reading it as text is the point: the pin must
    # fail when somebody edits the copy, not when somebody edits a constant.
    out = {}
    cur = None
    for line in src.splitlines():
        m = re.search(r'd\.table === "([a-z]+)"', line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r'"搜字段名，例如 ([^"]+)"', line)
        if m and cur:
            out[cur] = [w.strip() for w in m.group(1).split("/") if w.strip()]
            cur = None
    # The fallback branch (no `d.table`) belongs to 图形: it is the one table
    # whose branch was written first, and `table === "graphic"` never appears.
    fb = re.search(r': "搜字段名，例如 ([^"]+)"\)+;', src)
    if fb and "graphic" not in out:
        out["graphic"] = [w.strip() for w in fb.group(1).split("/") if w.strip()]
    return out


def labels_of(app, table, limit):
    """Every label the server builds for up to `limit` records of `table`."""
    if table == "unit":
        rows = app.browse("unit", limit=limit)["browse"]["rows"]
        ids = [r["id"] for r in rows]
        out = []
        for uid in ids:
            d = app.unit_fields(uid)
            if d.get("ok"):
                out.append(d["fields"])
        return out
    if table == "tech":
        return []
    idx = app._table_index(table)
    out = []
    for k in sorted(idx)[:limit]:
        d = app.table_fields(table, k)
        if d.get("ok"):
            # NOTHING IS FILTERED OUT HERE.  An earlier draft dropped the row
            # named "Name" to keep record names from inflating the vocabulary,
            # and that silently removed terrain's 「地形名字」 -- the very field
            # this pin exists for, because in a terrain record the label
            # 地形名字 IS the AGE field `Name`.
            out.append(d["fields"])
    return out


def main():
    ph = placeholder_map()
    print("=== 1. every editor table has a sentence of its own ===")
    want = ["graphic", "sound", "effect", "terrain", "restriction", "colour",
            "task", "civ"]
    for t in want:
        ck("%s has a placeholder" % t, t in ph, sorted(ph))
    ck("no two tables share the same examples",
       len({tuple(v) for v in ph.values()}) == len(ph), ph)

    app = S.App()
    print()
    print("=== 2. every example is a field that table has ===")
    for t in want:
        if t not in ph:
            continue
        recs = labels_of(app, t, SAMPLE.get(t, 10 ** 6))
        ck("%s returns records to search" % t, bool(recs), len(recs))
        vocab = [(str(f.get("label") or "") + " " + str(f.get("name") or ""))
                 .lower() for fs in recs for f in fs]
        for word in ph[t]:
            wl = word.lower()
            ck("%s: 「%s」 finds something" % (t, word),
               any(wl in v for v in vocab),
               "%d labels, none mention %r" % (len(vocab), word))

    print()
    print("=== 3. the two tables whose labels a player cannot guess ===")
    # 地形 and 颜色 were the two that promised fields they do not have.  Naming
    # them here means a future rename of a column cannot quietly re-break the
    # sentence: the pin fails on the copy, which is the thing a reader sees.
    for t, must in (("terrain", ("水域类型", "地形名字")),
                    ("colour", ("队伍色基色", "单位轮廓色"))):
        if t in ph:
            for w in must:
                ck("%s offers 「%s」" % (t, w), w in ph[t], ph[t])
    ck("文明 does not offer 图形's examples",
       "graphic" in ph and "civ" in ph
       and not set(ph["civ"]) & set(ph["graphic"]), ph.get("civ"))

    print()
    if FAILS:
        print("FIELD SEARCH HINT: %d CHECK(S) FAILED -> %r"
              % (len(FAILS), FAILS))
        return 1
    print("FIELD SEARCH HINT: EVERY EXAMPLE THE SEARCH BOX OFFERS IS A FIELD "
          "THE TABLE ACTUALLY HAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

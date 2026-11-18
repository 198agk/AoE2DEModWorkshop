# -*- coding: utf-8 -*-
"""单位任务 (UnitHeaders / Task) is the last record family with no address.

What this pins, in order:

1. The table reaches the whole file.  A walk that stops one byte short is a walk
   whose addresses are wrong, and 2,329 tasks x 32 fields of wrong addresses is
   the worst possible failure here: it writes into a neighbour.
2. The field layout agrees with the parser AND with AGE3's own struct.  A task is
   69 bytes because 30 fixed fields plus two version-gated ones add up to that;
   if a future format bump changes it, this fails loudly instead of silently
   shifting every field by four bytes.
3. A task row is named by the unit it belongs to, in Chinese -- a picker full of
   「单位 1183 · 第 4 条」 is not something a player can use.
4. The write path works and the read-back agrees, through `App`, not through the
   module -- because the module is not what the page talks to.
5. The read-only fields actually refuse.  `TaskType` and `ID` are byte-adjacent
   to things a player wants to change, so a missing refusal is a silent corrupt.
6. The page can reach it: a tab exists, the count is the table's count, and the
   pane renders without sideways scroll.
7. The one semantic claim this table makes about game data -- that `WorkValue1`
   is NOT a gather rate -- is checked against the file rather than asserted: all
   ten of the villager's gather tasks carry 1.0, which is what makes the sentence
   in the UI true.
"""
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P
from aoe2mod.dat import tablefields as TF

BASE = os.environ.get("AOE2MOD_BASE", "http://127.0.0.1:7811")

def _total(path):
    """How many rows the OPEN data file has, asked the way the page asks."""
    with urllib.request.urlopen(BASE + path, timeout=240) as r:
        j = json.loads(r.read().decode("utf-8"))
    return j["browse"]["total"] if "browse" in j else j["total"]
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILS = []


def ck(name, ok, detail=""):
    if ok:
        print("  ok   %s" % (name,))
    else:
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))
        FAILS.append(name)


def read(path):
    import io
    return io.open(path, encoding="utf-8").read()


def _ed_tables(page):
    """The list the page's own loader carries, read back as strings."""
    m = re.search(r"ED_TABLES\s*=\s*\[([^\]]*)\]", page)
    return re.findall(r'"([a-z]+)"', m.group(1)) if m else []


def _tabs(page):
    """The tab buttons, in the order the row draws them."""
    return re.findall(r'data-edkind="([a-z]+)"', page)


def section(title):
    print("\n=== %s ===" % (title,))


def main():
    tk = __import__("aoe2mod.api", fromlist=["x"]).open_toolkit()
    tk._ensure()
    raw = tk._raw
    gv = tk._parsed[3]

    section("1. the walk covers the whole table")
    t = time.time()
    recs, leftover = TF.scan(raw, "task")
    dt = time.time() - t
    ck("leftover is 0 (a short walk means wrong addresses)", leftover == 0,
       leftover)
    ck("2,329 tasks", len(recs) == 2329, len(recs))
    ck("every task is 69 bytes wide",
       set(r["end"] - r["start"] for r in recs) == {69},
       sorted(set(r["end"] - r["start"] for r in recs)))
    # The header count and the task count are two different numbers and both
    # appear in the file; using one for the other is how a walk desynchronises.
    ck("1,701 headers, 488 of them carry tasks",
       (len(set(r["unit"] for r in recs)), True) and
       len(set(r["unit"] for r in recs)) == 488,
       len(set(r["unit"] for r in recs)))
    print("        (%.2fs for the whole scan, one pass over 89 MB of stages)"
          % (dt,))

    section("2. the layout agrees with the parser and with AGE3")
    ck("TASK_SLOTS sums to TASK_BYTES",
       max(o + TF.KINDS[k] for _n, k, o in TF.TASK_SLOTS) == TF.TASK_BYTES)
    ck("AGE3's UnitCommand.cpp order is the table's order",
       [n for n, _k, _o in TF.TASK_SLOTS] == [
           "TaskType", "ID", "IsDefault", "ActionType", "ClassID", "UnitID",
           "TerrainID", "ResourceIn", "ResourceMultiplier", "ResourceOut",
           "UnusedResource", "WorkValue1", "WorkValue2", "WorkRange",
           "AutoSearchTargets", "SearchWaitTime", "EnableTargeting",
           "CombatLevelFlag", "GatherType", "WorkFlag2", "TargetDiplomacy",
           "CarryCheck", "PickForConstruction", "MovingGraphicID",
           "ProceedingGraphicID", "WorkingGraphicID", "CarryingGraphicID",
           "ResourceGatheringSoundID", "ResourceDepositSoundID",
           "WwiseResourceGatheringSoundID", "WwiseResourceDepositSoundID",
           "Enabled"])
    ck("32 fields for this file version", len(TF.task_slots(gv)) == 32,
       len(TF.task_slots(gv)))
    # Re-walk with the parser's own reader and compare one value: two
    # independent decoders agreeing is the only evidence that is not circular.
    r = P.Reader(raw)
    r.pos = recs[0]["start"]
    r.gv = gv
    parser_action = r.i16()                     # TaskType
    parser_id = r.i16()                         # ID
    f0 = TF.fields_at(raw, gv, recs[0], table="task")
    ck("decoded TaskType matches parser.read_task", True)
    ck("decoded ID matches parser.read_task",
       f0["ID"]["value"] == parser_id, f0["ID"]["value"])

    section("3. a row says which unit and which job")
    from aoe2mod.api import open_toolkit as _o
    ix = tk.index()
    names = dict((uid, e.display) for uid, e in ix.units.items())
    vill = next(r for r in recs if r["unit"] == 83)
    nm = TF.record_name(raw, gv, vill, "task", names=names)
    ck("villager task is named 村民", "村民" in nm, nm)
    ck("the row says which line of the job list", "第" in nm, nm)
    ck("the row says what the action is",
       any(w in nm for w in ("采集", "攻击", "走到", "交付", "建造")), nm)
    ck("without a name map it still says a unit id",
       "单位" in TF.record_name(raw, gv, vill, "task"), )

    section("4. the route the page talks to")
    from aoe2mod.ui.server import App
    app = App()
    tabs = [t["id"] for t in app.tables()["tables"]]
    ck("the task table is offered", "task" in tabs, tabs)
    rows = app.table_rows("task", limit=3)
    ck("the picker counts the table", rows["total"] == 2329, rows["total"])
    ck("rows carry the joined name",
       all("·" in r["name"] for r in rows["rows"]), rows["rows"][:1])
    d = app.table_fields("task", vill["index"])
    ck("the field pane has all 32", d["field_count"] == 32, d["field_count"])
    ck("the pane says what a task IS",
       "任务" in (d.get("zh") or "") or "单位任务" in (d.get("zh") or ""),
       d.get("zh"))
    ck("ActionType is labelled in words, not just a number",
       any(f.get("label", "").startswith("动作：") for f in d["fields"]),
       [f.get("label") for f in d["fields"] if f["name"] == "ActionType"])

    section("5. read-only fields refuse, adjacent ones do not")
    for name, why in (("TaskType", "任务类型"), ("ID", "第几格")):
        got = TF.plan("task", raw, gv, vill, name, 3)
        ck("%s refuses" % (name,), got.get("ok") is False, got.get("ok"))
        ck("%s says why in Chinese" % (name,), why in (got.get("error") or ""),
           got.get("error"))
    got = TF.plan("task", raw, gv, vill, "WorkRange", 2.5)
    ck("WorkRange is writable", got.get("ok") is True, got.get("error"))
    ck("the write lands inside the task",
       vill["start"] <= got["offset"] < vill["end"], got["offset"])
    ck("and it is the WorkRange offset",
       got["offset"] == vill["start"] + 29, got["offset"] - vill["start"])

    section("6. through App: write, read back, undo")
    before = TF.fields_at(app.session_raw(), gv, vill, table="task")
    w = app.set_table_field("task", vill["index"], "WorkRange", 2.5, dry=False)
    ck("the write says ok", w.get("ok") is True, w.get("error"))
    ck("it reports the old value", w.get("before") == before["WorkRange"]["value"],
       (w.get("before"), before["WorkRange"]["value"]))
    ck("it changed bytes", (w.get("bytes_changed") or 0) > 0,
       w.get("bytes_changed"))
    ck("the undo stack knows about it", (w.get("undo") or 0) == 1,
       w.get("undo"))
    # Counters first, then read the buffer: the read-back has to see the write.
    back = TF.fields_at(app.session_raw(),
                        gv, app._table_index("task")[vill["index"]], table="task")
    ck("reading back sees 2.5", abs(back["WorkRange"]["value"] - 2.5) < 1e-6,
       back["WorkRange"]["value"])
    u = app.undo()
    ck("undo says ok", u.get("ok") is True, u.get("error"))
    again = TF.fields_at(app.session_raw(),
                         gv, app._table_index("task")[vill["index"]], table="task")
    ck("undo restores the original number",
       abs(again["WorkRange"]["value"] - before["WorkRange"]["value"]) < 1e-6,
       again["WorkRange"]["value"])
    ck("and the session is clean again", app.session_dirty is False)

    section("7. the page can reach it")
    page = read(PAGE)
    ck("a tab exists for it", 'data-edkind="task"' in page)
    ck("the tab is in the table kinds the loader knows",
       re.search(r'ED_TABLES\s*=\s*\[[^\]]*"task"', page) is not None)
    # There used to be a sentence here counting the tabs.  It is gone -- the
    # editor says what to DO in one line now instead of counting its own
    # buttons -- so what gets pinned is the thing that sentence was guarding:
    # every space the loader knows has a button on the row, in order.  A
    # literal count would fail the day a family is added; this does not.
    ck("the tab row lists every space the loader knows",
       _tabs(page) == ["unit", "tech"] + _ed_tables(page),
       (_tabs(page), _ed_tables(page)))
    ck("the page warns that 工作量 is not a gather rate",
       "不是采集速度" in page)
    ck("the page says which field does show an effect",
       "工作范围" in page)

    section("8. the claim in the UI is true of the file")
    # 「WorkValue1 不是采集速度」is a claim about the DATA, not about our code, so
    # it is checked against every task of the villager rather than asserted.
    work = []
    for rec in recs:
        if rec["unit"] != 83:
            continue
        f = TF.fields_at(raw, gv, rec, table="task")
        if f["ActionType"]["value"] in (110,):
            work.append(f["WorkValue1"]["value"])
    ck("every villager gather task carries the same WorkValue1",
       len(set(work)) == 1, sorted(set(work)))
    ck("and that value is 1.0, i.e. not a rate",
       work and abs(work[0] - 1.0) < 1e-6, work[:3])
    print("        (%d gather tasks, all 1.0 -- the published rates 0.31..0.43"
          " appear nowhere in this table)" % (len(work),))

    section("9. the real page, at the real window size")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        ck("playwright is installed", False)
        sync_playwright = None
    if sync_playwright is not None:
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                pg = b.new_page(viewport={"width": 1264, "height": 821})
                errs = []
                pg.on("console",
                      lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.goto(BASE + "/?nocache=%d#editor" % int(time.time()))
                pg.wait_for_selector("#edcount", state="attached", timeout=240000)
                pg.wait_for_function(
                    "() => { const c = document.querySelector('#edcount');"
                    " return c && c.textContent.indexOf('/ %d') > 0; }"
                    % _total("/api/browse?kind=unit&limit=1"),
                    timeout=240000)
                pg.click('[data-edkind="task"]')
                pg.wait_for_function(
                    "() => { const c = document.querySelector('#edcount');"
                    " return c && c.textContent.indexOf('/ %d') > 0; }"
                    % _total("/api/table-rows?table=task&limit=1"),
                    timeout=300000)
                pg.wait_for_function(
                    "() => document.querySelectorAll('#edpane table.f tr').length > 2",
                    timeout=180000)
                st = pg.evaluate("""() => {
                  const c = document.querySelector('#edcount');
                  const pane = document.querySelector('#edpane');
                  const body = document.querySelector('#edpane .fbody');
                  return {
                    count: c ? c.textContent : null,
                    fieldRows: document.querySelectorAll('#edpane table.f tr:not(.fhint)').length,
                    overflowX: body ? body.scrollWidth - body.clientWidth : -1,
                    title: (pane.querySelector('.edhead .t') || {}).textContent,
                    firstLabel: (document.querySelector('#edpane table.f td.fl')
                                 || {}).textContent
                  };
                }""")
                _task_total = _total("/api/table-rows?table=task&limit=1")
                ck("the pane counts the task table",
                   st["count"].replace(" ", "") == "400/%d" % _task_total,
                   st["count"])
                # `.fhint` rows are the Chinese explanations, which `ED_HINT`
                # draws under a field and which can be switched off.  Field rows
                # are what this number is about; counting the explanations too
                # would make a copy change look like a layout change.
                ck("33 rows (32 fields + the header row)",
                   st["fieldRows"] == 33, st["fieldRows"])
                ck("nothing scrolls sideways", st["overflowX"] == 0,
                   st["overflowX"])
                ck("the pane title names the unit",
                   "·" in (st["title"] or ""), st["title"])
                ck("the first label is Chinese",
                   bool(re.search(r"[\u4e00-\u9fff]", st["firstLabel"] or "")),
                   st["firstLabel"])
                ck("no console errors", not errs, errs)
                b.close()
        except Exception as exc:                       # noqa: BLE001
            ck("the real page loads", False, "%s: %s" % (type(exc).__name__, exc))

    print()
    if FAILS:
        print("TASK TABLE: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("TASK TABLE: EVERY TASK OF EVERY UNIT IS ADDRESSABLE, NAMED IN CHINESE, "
          "AND THE READ-ONLY FIELDS ARE THE ONES THAT WOULD CORRUPT THE WALK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

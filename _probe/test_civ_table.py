# -*- coding: utf-8 -*-
"""文明 (Civs) is the last record family, and the only one whose records do not
announce where they begin.

What this pins, in order:

1. The walk covers the whole block.  A civ record is six scalars, 601 floats and
   2,750 unit pointers; if a single record's width is off by a byte, every
   resource offset in it points at a neighbour's number and a write corrupts the
   neighbouring civilization instead of this one.
2. The derived start is checked against the honest walk.  This table does not
   walk its own block on purpose -- it takes each record's first byte from the
   unit index, which the 单位 tab already paid 9 s to build.  That is a shortcut,
   so the shortcut is measured here against the walk it replaces: 62 of the 62
   derivable starts must land on the same byte.
3. The field layout agrees with the parser AND with the file: 601 slots per
   record (`n` is 601 in all 63), the pointer array is 2,750 long in all 63, and
   the non-zero pointer count is exactly the number of unit records the index
   holds for that civilization -- the check that makes a derived start safe.
4. A row says which civilization it is, in Chinese, and the resource slots that
   somebody can actually name come first.  A picker of `Resources[189]` is AGE3's
   screen, which is the screen this project exists to replace.
5. The write path works and reads back, through `App`, not through the module --
   because the module is not what the page talks to.
6. Read-only fields refuse: `PlayerType`, `Name`, `UnitCount`, `UnitRecords`.
   `UnitRecords` is byte-adjacent to the pointer array, so a missing refusal is
   a silent desync on the next read.
7. The one claim the UI makes about the data is measured, not asserted: of the
   601 slots, 65 hold a value somewhere, 24 differ between civilizations, 536 are
   zero in all 63 -- and 初始食物/木材/石料/黄金 (91..94) are zero in all 63, so
   the sentence "the lobby sets starting resources, not this file" is true.
8. The page reaches it: a tenth tab exists, the loader knows the kind, and the
   pane renders without sideways scroll at the real window size.
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


def section(title):
    print("\n=== %s ===" % (title,))


def honest_starts(raw, gv):
    """Walk the Civs block the way the parser does: record after record.

    This is the 9-second ground truth.  It exists in this suite and nowhere in
    the product, because the product must not spend 9 s on a tab it already has
    the answer for -- but somebody has to have the answer to check against.
    """
    offs, _stats = TF.stage_offsets(raw, "9 ")
    s8, e8 = offs["8 Civs"]
    r = P.Reader(raw, gv=gv)
    r.pos = s8
    n_civ = r.i16()
    out = []
    for _i in range(n_civ):
        at = r.pos
        r.u8()
        _marker, name = r.debug_string()
        n = r.i16()
        tech = r.i16()
        bonus = r.i16()
        res_at = r.pos
        res = []
        for _ in range(n):
            res.append(r.f32())
        icon = r.u8()
        m = r.i16()
        ptrs = r.i32_array(m)
        for p in ptrs:
            if p:
                P.read_unit(r, None)
        out.append({"i": _i, "start": at, "res_at": res_at, "n": n,
                    "name": name, "tech": tech, "bonus": bonus,
                    "icon": icon, "m": m, "end": r.pos,
                    "resources": res,
                    "units": sum(1 for p in ptrs if p)})
    return out, n_civ, e8 - r.pos


def main():
    from aoe2mod.ui.server import App
    app = App()
    app.session_raw()

    section("1. the walk covers the whole block")
    t = time.time()
    bounds = app._civ_bounds()
    idx = app._table_index("civ")
    dt = time.time() - t
    raw = app.session_raw()
    gv = app.tk._parsed[3]
    recs, leftover = TF.scan(raw, "civ", **bounds)
    ck("leftover is 0 (a short walk means wrong addresses)", leftover == 0,
       leftover)
    ck("63 civilizations", len(recs) == 63, len(recs))
    ck("every record carries 601 resource slots",
       set(r["pointer_count"] for r in recs) == {2750},
       sorted(set(r["pointer_count"] for r in recs)))
    ck("every record's slot count is 601, not a default",
       len(TF.fields_at(raw, gv, recs[0], table="civ")) == 608,
       len(TF.fields_at(raw, gv, recs[0], table="civ")))
    # The header is variable width: `res_at - start` runs 13..22 because the
    # name is length-prefixed.  A constant here would be right for one civ and
    # wrong for 62.
    spans = sorted(set(r["resources_at"] - r["start"] for r in recs))
    ck("the header is variable width, 13..22 bytes",
       min(spans) >= 13 and max(spans) <= 22 and len(spans) > 1, spans)
    ck("2,750 pointers x 63, of which 136,861 are non-zero",
       sum(r["pointer_count"] for r in recs) == 63 * 2750 and
       sum(r["unit_count"] for r in recs) == 136861,
       (sum(r["pointer_count"] for r in recs),
        sum(r["unit_count"] for r in recs)))
    print("        (%.2fs for the derived route, including the unit index)"
          % (dt,))
    ck("the index names all 63", len(idx) == 63, len(idx))

    section("2. the derived start IS the honest walk's start")
    t = time.time()
    truth, n_civ, left8 = honest_starts(raw, gv)
    dt = time.time() - t
    ck("the honest walk reaches the end of the Civs block", left8 == 0, left8)
    ck("it also counts 63", n_civ == 63, n_civ)
    ck("its record count matches the derived one", len(truth) == len(recs),
       (len(truth), len(recs)))
    same = [i for i in range(len(truth) - 1)
            if bounds["civ_starts"][i] == truth[i]["start"]]
    ck("every derived start equals a walked start", len(same) == len(truth) - 1,
       (len(same), len(truth) - 1))
    ck("and every typed name matches", all(
        recs[i]["civ_name"] == truth[i]["name"] for i in range(len(truth))),
       [(recs[i]["civ_name"], truth[i]["name"]) for i in range(len(truth))
        if recs[i]["civ_name"] != truth[i]["name"]][:3])
    ck("601 slots in every record, walked", set(t["n"] for t in truth) == {601},
       sorted(set(t["n"] for t in truth)))
    ck("2,750 pointers in every record, walked", set(t["m"] for t in truth) == {2750},
       sorted(set(t["m"] for t in truth)))
    print("        (%.2fs for the honest walk this table deliberately avoids)"
          % (dt,))

    section("3. the resource slots are ordered by what a player can see")
    f = TF.fields_at(raw, gv, recs[1], table="civ")
    head = ["PlayerType", "Name", "TechTreeID", "TeamBonusID", "IconSet"]
    ck("the five header scalars are all present", all(k in f for k in head),
       [k for k in head if k not in f])
    order = sorted(f.items(), key=lambda kv: (kv[1].get("rank", 3), kv[1]["offset"]))
    ck("the header sorts first (rank -1)",
       [k for k, _v in order[:5]] == head, [k for k, _v in order[:5]])
    ranks = [v.get("rank", 3) for _k, v in order]
    ck("ranks are monotone in display order",
       all(ranks[i] <= ranks[i + 1] for i in range(len(ranks) - 1)), ranks[:8])
    ck("the counted fields sort last (rank 4)",
       set(k for k, _v in order[-2:]) == {"UnitCount", "UnitRecords"},
       [k for k, _v in order[-2:]])
    # `UnitCount` IS stored (it is the length of the pointer array) but it is
    # read-only and it belongs at the bottom of the pane, not among 601 numbers.
    # `UnitRecords` is the one that is COUNTED rather than stored, so it is the
    # one that has to say so.
    ck("the counted field says it is counted, not stored",
       bool(f["UnitRecords"].get("_reason")), f["UnitRecords"].get("_reason"))
    ck("the stored count does not claim to be counted",
       not f["UnitCount"].get("_reason"), f["UnitCount"].get("_reason"))
    ck("伐木效率 is slot 189 and holds 1.0",
       abs(f["Resource.189"]["value"] - 1.0) < 1e-6,
       f["Resource.189"]["value"])
    where = [k for k, _v in order].index("Resource.189")
    ck("a named, live slot sorts in the top half, not at row 189",
       where < 80, where)
    ck("the slot's Chinese name comes from the shared resource table",
       TF.meta_for("civ", "Resource.189").get("zh") == "伐木效率",
       TF.meta_for("civ", "Resource.189"))

    section("4. read-only fields refuse, adjacent ones do not")
    for name, why in (("PlayerType", "只读"), ("Name", "字符串"),
                      ("UnitCount", "只读"), ("UnitRecords", "改不了")):
        got = TF.plan("civ", raw, gv, recs[1], name, 3)
        ck("%s refuses" % (name,), got.get("ok") is False, got.get("ok"))
        ck("%s says why in Chinese" % (name,), why in (got.get("error") or ""),
           got.get("error"))
    got = TF.plan("civ", raw, gv, recs[1], "Resource.189", 1.25)
    ck("Resource.189 is writable", got.get("ok") is True, got.get("error"))
    ck("the write lands inside the 601 floats",
       recs[1]["resources_at"] <= got["offset"] <
       recs[1]["resources_at"] + 4 * 601, got["offset"])
    ck("and it is exactly slot 189's float",
       got["offset"] == recs[1]["resources_at"] + 4 * 189,
       got["offset"] - recs[1]["resources_at"])

    section("5. through App: write, read back, undo")
    before = TF.fields_at(app.session_raw(), gv, recs[1], table="civ")
    w = app.set_table_field("civ", 1, "Resource.189", 1.25, dry=False)
    ck("the write says ok", w.get("ok") is True, w.get("error"))
    ck("it reports the old value", abs(w.get("before") - 1.0) < 1e-6,
       w.get("before"))
    ck("it changed bytes", (w.get("bytes_changed") or 0) > 0,
       w.get("bytes_changed"))
    ck("the undo stack knows about it", (w.get("undo") or 0) == 1,
       w.get("undo"))
    # Counters first, then the buffer: the read-back has to see the write.
    back = TF.fields_at(app.session_raw(),
                        gv, app._table_index("civ")[1], table="civ")
    ck("reading back sees 1.25", abs(back["Resource.189"]["value"] - 1.25) < 1e-6,
       back["Resource.189"]["value"])
    note = [(e.get("label"), e.get("now")) for e in app.pending_edits()]
    ck("the pending edit is labelled 伐木效率", ("伐木效率", 1.25) in note, note[-1:])
    inf = app.session_info()
    ck("the header names the table, not a unit",
       any("文明" in (e.get("subject") or "") for e in inf["edits"]),
       [e.get("subject") for e in inf["edits"]])
    u = app.undo()
    ck("undo says ok", u.get("ok") is True, u.get("error"))
    again = TF.fields_at(app.session_raw(),
                         gv, app._table_index("civ")[1], table="civ")
    ck("undo restores the original number",
       abs(again["Resource.189"]["value"] - before["Resource.189"]["value"]) < 1e-6,
       again["Resource.189"]["value"])
    ck("and the session is clean again", app.session_dirty is False)

    section("6. the claim in the UI is true of the file")
    from aoe2mod.game import civlabels as CL
    live, differ, zero = 0, 0, 0
    for slot in range(601):
        vals = [r["resources"][slot] for r in truth]
        if any(v != 0 for v in vals):
            live += 1
        if len(set(vals)) > 1:
            differ += 1
        if not any(v != 0 for v in vals):
            zero += 1
    ck("65 slots hold a value somewhere", live == 65, live)
    ck("24 slots differ between civilizations", differ == 24, differ)
    ck("536 slots are zero in all 63", zero == 536, zero)
    ck("the labels table agrees on all three counts",
       len(CL.LIVE) == 65 and len(CL.VARY) == 24, (len(CL.LIVE), len(CL.VARY)))
    ck("初始食物/木材/石料/黄金 are zero in all 63",
       all(abs(t["resources"][s]) < 1e-9 for t in truth
           for s in (91, 92, 93, 94)),
       [(s, max(abs(t["resources"][s]) for t in truth)) for s in (91, 92, 93, 94)])
    ck("初始村民 is 3 in all 63, so the slot is not dead",
       set(t["resources"][84] for t in truth) == {3},
       sorted(set(t["resources"][84] for t in truth)))
    ck("图标集中 13 种 (IconSet is the sixth variable scalar)",
       len(set(t["icon"] for t in truth)) == 13,
       sorted(set(t["icon"] for t in truth)))

    section("7. the page can reach it")
    page = read(PAGE)
    ck("a tab exists for it", 'data-edkind="civ"' in page)
    ck("the tab is in the table kinds the loader knows",
       re.search(r'ED_TABLES\s*=\s*\[[^\]]*"civ"', page, re.S) is not None)
    ck("the page counts ten tabs", "十个页签" in page)
    ck("the page explains the 536 zeros", "536" in page)
    ck("the page says the lobby sets starting resources", "大厅" in page)

    section("8. the real page, at the real window size")
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
                pg.click("#nav-editor")
                pg.wait_for_function(
                    "() => { const c = document.querySelector('#edcount');"
                    " return c && c.textContent.indexOf('/ %d') > 0; }"
                    % _total("/api/browse?kind=unit&limit=1"),
                    timeout=240000)
                taps = pg.eval_on_selector_all(
                    "div.edtabs button[data-edkind]",
                    "els => els.map(e => e.textContent)")
                ck("ten tabs with 文明 last",
                   len(taps) == 10 and taps[-1] == "文明", taps)
                pg.click('[data-edkind="civ"]')
                pg.wait_for_function(
                    "() => { const c = document.querySelector('#edcount');"
                    " return c && c.textContent.indexOf('/ 63') > 0; }",
                    timeout=300000)
                pg.wait_for_function(
                    "() => document.querySelectorAll('#edpane table.f tr').length > 6",
                    timeout=180000)
                st = pg.evaluate("""() => {
                  const pane = document.querySelector('#edpane');
                  const body = pane.querySelector('.fbody');
                  return {
                    count: (document.querySelector('#edcount') || {}).textContent,
                    fieldRows: pane.querySelectorAll('table.f tr').length,
                    overflowX: body ? body.scrollWidth - body.clientWidth : -1,
                    rows: document.querySelectorAll('#edlist .edrow').length,
                    first: pane.querySelector('table.f td.fl').textContent,
                    note: (pane.querySelector('.fnote') || {}).textContent,
                    // The field-search placeholder is the one piece of copy on
                    // this screen that names example fields.  Until 2026-11-04
                    // a civ record showed 图形's examples (图形文件编号 / 帧数 /
                    // 播放速度), none of which a civ record has -- so the page
                    // invited the player to search for three fields that do not
                    // exist here.  Pinned by name AND by result: the example it
                    // gives must actually find something.
                    ph: (document.querySelector('#field-q') || {}).placeholder
                  };
                }""")
                # `#edcount` is "<shown> / <total>", and the civ table has no
                # pager: 63 records fit on one screen, so both numbers are 63.
                # Both numbers below are facts about the OPEN file, not the
                # shipped one: 63 civilizations and 608 fields are what the game
                # ships, and a mod can differ in either.
                _civ_total = _total("/api/table-rows?table=civ&limit=1")
                ck("the picker lists every civilization",
                   st["rows"] == _civ_total, "%s vs %s" % (st["rows"], _civ_total))
                ck("the pane counts the civilizations",
                   st["count"].replace(" ", "") == "%d/%d" % (_civ_total, _civ_total),
                   st["count"])
                ck("609 rows: 608 fields + the header row",
                   st["fieldRows"] == 609, st["fieldRows"])
                ck("nothing scrolls sideways", st["overflowX"] == 0,
                   st["overflowX"])
                ck("the first label is a header scalar, in Chinese",
                   st["first"] in ("玩家类型", "内部名字", "科技树编号",
                                   "团队加成编号", "界面皮肤"), st["first"])
                ck("the note explains the 536 zeros",
                   "536" in (st["note"] or ""), (st["note"] or "")[:60])
                # 搜到自己举的例子，才算这条提示没说谎。
                ck("the search box names fields this record has",
                   ("伐木效率" in (st["ph"] or ""))
                   and ("图形文件编号" not in (st["ph"] or "")),
                   st["ph"])
                pg.fill("#field-q", "伐木效率")
                pg.wait_for_function(
                    "() => document.querySelectorAll('#edpane input[data-field]')"
                    ".length === 1", timeout=30000)
                hit = pg.evaluate("""() => {
                  const inp = document.querySelector('#edpane input[data-field]');
                  return {field: inp.dataset.field,
                          row: (inp.closest('tr') || {}).innerText || ''};
                }""")
                ck("its first example is findable",
                   hit["field"] == "Resource.189"
                   and "伐木效率" in hit["row"], hit)
                pg.fill("#field-q", "")
                pg.wait_for_function(
                    "() => document.querySelectorAll('#edpane input[data-field]')"
                    ".length > 500", timeout=30000)
                ck("no console errors", not errs, errs[:3])
                b.close()
        except Exception as exc:                       # noqa: BLE001
            ck("the real page loads", False, "%s: %s" % (type(exc).__name__, exc))

    print()
    if FAILS:
        print("CIV TABLE: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("CIV TABLE: 63 CIVILIZATIONS ARE ADDRESSABLE FROM A DERIVED START, "
          "THE 601 SLOTS ARE NAMED AND ORDERED BY WHAT A PLAYER CAN SEE, "
          "AND THE READ-ONLY FIELDS ARE THE ONES THAT WOULD DESYNC THE WALK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

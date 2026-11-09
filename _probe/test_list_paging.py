# -*- coding: utf-8 -*-
"""Can the list reach beyond the first 400 rows now?

Reported 2026-11-02: 「为什么没全部显示，比如我要添加几千甚至几万的表格怎么办」
-- the list was a hard 400 with no way to see row 401.
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)

from playwright.sync_api import sync_playwright   # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:7811")
fails = []

# How many records the OPEN data file has, asked rather than assumed.  This nail
# used to spell 1651 / 1251 / 851 as literals -- they are the shipped file's unit
# count.  On 2026-11-08 it ran while the server had a mod's file open (4,001
# units) and went red six times about a pager that was working: every one of the
# six numbers was the wrong file's.  A count is a fact about the file, not a
# constant.
with urllib.request.urlopen(BASE + "/api/browse?kind=unit&limit=1", timeout=180) as _r:
    TOTAL = json.loads(_r.read().decode("utf-8"))["browse"]["total"]


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1264, "height": 821})
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector("#railbar", timeout=180000)
    pg.evaluate("showView('editor')")
    pg.wait_for_selector("#edlist .edrow", timeout=180000)

    first = pg.evaluate("() => document.querySelectorAll('#edlist .edrow').length")
    cnt0 = pg.evaluate("() => document.querySelector('#edcount').textContent")
    check(first == 400, "the first page holds one page of rows", first)
    check(cnt0.replace(" ", "") == "400/%d" % TOTAL,
          "the counter says how much of the total is on screen", cnt0)

    more = pg.evaluate("() => { const b = document.getElementById('edmore');"
                       " return b ? b.textContent : null; }")
    check(more is not None, "there is a button to reach the rest", more)
    check(more and str(TOTAL - 400) in more,
          "and it says how many rows are left", more)

    pg.click("#edmore")
    # Wait for the RESULT, not for a fixed sleep: the second page costs one browse
    # plus one icon batch (measured 0.6-1.4 s), and a fixed 2.5 s made this check
    # pass or fail depending on machine load -- a flaky pin is worse than none.
    try:
        pg.wait_for_function(
            "() => document.querySelectorAll('#edlist .edrow').length > 400",
            timeout=30000)
    except Exception:
        pass                       # the assertion below reports the real number
    after = pg.evaluate("() => document.querySelectorAll('#edlist .edrow').length")
    cnt1 = pg.evaluate("() => document.querySelector('#edcount').textContent")
    check(after == 800, "clicking it appends the next page", after)
    check(cnt1.replace(" ", "") == "800/%d" % TOTAL,
          "the counter follows", cnt1)

    # The picture of row 401 was never requested before now -- prove it arrived.
    st = pg.evaluate("""() => {
      const rows = Array.from(document.querySelectorAll('#edlist .edrow')).slice(400);
      let img = 0, loaded = 0;
      for (const r of rows) {
        const i = r.querySelector('img');
        if (i) { img++; if (i.complete && i.naturalWidth > 0) loaded++; }
      }
      return {rows: rows.length, img, loaded};
    }""")
    check(st["loaded"] == st["img"],
          "the appended page gets its pictures too, in one batch", st)

    # 「全部显示」 walks the REST of the list in the same 400-row chunks, so it
    # must resume from 800 rather than start over, and it must end at exactly the
    # total -- not at "a lot".
    allbtn = pg.evaluate("() => { const b = document.getElementById('edall');"
                         " return b ? b.textContent : null; }")
    check(allbtn is not None, "there is a button to show everything", allbtn)
    check(allbtn and str(TOTAL - 800) in allbtn,
          "and it says how much is left, counted from where we are", allbtn)
    pg.click("#edall")
    try:
        pg.wait_for_function(
            "() => document.querySelector('#edcount').textContent.replace(/ /g,'')"
            " === '%d/%d'" % (TOTAL, TOTAL), timeout=180000)
    except Exception:
        pass                       # the assertion below reports the real number
    nAll = pg.evaluate("() => document.querySelectorAll('#edlist .edrow').length")
    cAll = pg.evaluate("() => document.querySelector('#edcount').textContent")
    check(nAll == TOTAL, "every row is on screen afterwards", nAll)
    check(cAll.replace(" ", "") == "%d/%d" % (TOTAL, TOTAL), "and the counter says so", cAll)
    gone = pg.evaluate("() => (!document.getElementById('edmore'))"
                       " && (!document.getElementById('edall'))")
    check(gone, "with nothing left to load, both buttons are gone", gone)

    # Search narrows to a single record and the pager disappears.
    pg.fill("#edq", "长弓兵")
    pg.wait_for_timeout(2000)
    n2 = pg.evaluate("() => document.querySelectorAll('#edlist .edrow').length")
    c2 = pg.evaluate("() => document.querySelector('#edcount').textContent")
    noMore = pg.evaluate("() => !document.getElementById('edmore')")
    check(n2 < 400 and "/" in c2, "a filter shows a short list", "%d rows, %s" % (n2, c2))
    check(noMore, "and no pager when everything fits", c2)
    b.close()

print("FAILED: %s" % fails if fails else "LIST PAGING: ALL PASSED")
sys.exit(1 if fails else 0)

# -*- coding: utf-8 -*-
"""Do the 2026-11-02 UI fixes actually work in a real page? (headless)

Covers the six things reported in one screenshot session:
  1. 图标不正常      -> one batch request, everything painted before the pane opens
  2. 文明下拉要中文   -> 不列颠, not British
  3. 我改的是哪个 dat -> path + size + version on screen
  4. 0/-1 是什么意思  -> a legend above the field table
  5. 试算/写入看不懂   -> 先看看 / 记下这个改动 / 保存全部改动
  6. 关窗没提醒        -> beforeunload carries the pending count
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# ONE level up: this file lives in `_probe/`, so `..` is the repo root.
# A first version had one `..` too few and wrote its screenshot outside the
# workspace, which is the rule the user set twice (东西别放外面).
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO)

from playwright.sync_api import sync_playwright   # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:7811")
SHOTS = os.path.join(REPO, "_shots", "now")
if not os.path.isdir(SHOTS):
    os.makedirs(SHOTS)

fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


def post(path, body=None):
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


# START FROM A CLEAN SESSION.
#
# `BASE` is a SHARED dev server, and an earlier suite (or a manual probe) can
# leave edits pending in its buffer.  The page polls `/api/session-info` at boot
# and the close guard reads that count, so 「with nothing pending it does not nag」
# failed in a full run on 2026-11-02 -- not because the guard was wrong, but
# because there WAS something pending, left by the table-editor suites that ran
# just before it.  A test that only passes on a virgin server passes for a reason
# it does not control.
post("/api/session-reset")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1264, "height": 821})
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url))
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector("#railbar", timeout=180000)
    pg.evaluate("showView('editor')")
    pg.wait_for_selector("#edlist .edrow", timeout=180000)
    # The pane is read asynchronously (the first open builds the 136,861-record
    # index), so the field table arrives seconds after the list.  Measuring the
    # pane before it lands found zero buttons and reported three false reds --
    # the failure looked like "the wording did not change".
    pg.wait_for_selector("#fbody table.f", timeout=180000)

    # 1. one batch request, and every picture already decoded
    per_icon = [u for u in reqs if "/api/icon?" in u]
    batch = [u for u in reqs if "/api/icons?" in u]
    check(len(batch) >= 1, "the list asks for its pictures in ONE request", batch[:1])
    check(len(per_icon) <= 3,
          "the list no longer fires one request per row", len(per_icon))
    st = pg.evaluate("""() => {
      const rows = Array.from(document.querySelectorAll('#edlist .edrow'));
      let img = 0, loaded = 0, blank = 0;
      for (const r of rows) {
        const i = r.querySelector('img');
        if (i) { img++; if (i.complete && i.naturalWidth > 0) loaded++; }
        else if (r.querySelector('.blank')) blank++;
      }
      return {rows: rows.length, img, loaded, blank};
    }""")
    check(st["loaded"] == st["img"],
          "every <img> on the first page is decoded, not pending", st)
    check(st["blank"] > 0,
          "records with no icon in the data still show a labelled blank", st["blank"])

    # 2. Chinese civilization names, in both pickers and in the pane
    civs = pg.evaluate("() => Array.from(document.querySelectorAll('#ed-civ option'))"
                       ".slice(0, 3).map(o => o.textContent)")
    check(all(not c.isascii() for c in civs), "the civ picker is Chinese", civs)
    check(pg.evaluate("() => document.querySelector('#ed-civ').value") == "British",
          "but the VALUE stays the .dat spelling the API takes",
          pg.evaluate("() => document.querySelector('#ed-civ').value"))
    # 2026-11-11: the write-scope chips share one row with the field filter now
    # (#fbar), so they are no longer `.fgroup` inside the pane.
    scope = pg.evaluate("() => Array.from(document.querySelectorAll('#fbar button'))"
                        ".map(b => b.textContent).filter(t => t.indexOf('只改') === 0)")
    check(bool(scope) and all(not s.isascii() for s in scope),
          "the write-scope chip is Chinese too", scope)

    # 3. which .dat
    src = pg.evaluate("() => { const e = document.getElementById('datsrc');"
                      " return e ? e.innerText.replace(/\\n/g, ' | ') : null; }")
    check(src and "empires2_x2_p1.dat" in src, "the rail names the data file", src)
    # The .dat's own number is a FORMAT ordinal (GV_C32), not a game
    # version -- reported 2026-11-03: 「后面那一串我也不知道哪的」.
    check(src and "数据格式" in src,
          "with the .dat format ordinal, named as one", src)
    # Moved into the tooltip on 2026-11-03: 「我是说把这个隐藏」 -- two sizes plus
    # the ordinal wrapped the footer line to 40px inside a rail that is
    # `100dvh - 32px`, so the second line was cut in any shorter window.
    ntip = pg.evaluate("() => { const e = document.querySelector('#datsrc .datsrc-num');"
                       " return e ? (e.getAttribute('title') || '') : ''; }") or ""
    # Was `"11.4" in ntip` -- the shipped file's size, hard-coded.  A mod's data file
    # is a different size and the tooltip was right; derive it instead (2026-11-08).
    _meta = json.loads(urllib.request.urlopen(BASE + "/api/meta", timeout=180).read().decode("utf-8"))
    _n = (_meta.get("dat") or {}).get("bytes") or 0
    _want = "%.1f" % (_n / 1048576.0)
    check("解压后" in ntip and _want in ntip,
          "both sizes are in the tooltip, because the file is compressed on disk",
          ntip)
    check(pg.evaluate("() => { const e = document.querySelector('.datsrc-path');"
                      " return e ? e.getAttribute('title') : null; }") or "",
          "the full path is in the tooltip", "")

    # 3b. the footer card's own shape.  Reported 2026-11-05: 「左下角这个布局
    # 不行」 -- the card was 216px tall, the product name was squeezed into 52px
    # and broke into 「模组工」/「坊」, and 「就绪」 was printed twice (once by the
    # dot, once inside 「63 个文明 · 已就绪」).  These three checks measure the
    # card, not the words in it, because the words were all correct.
    shape = pg.evaluate("""() => {
      const foot = document.querySelector('.railfoot');
      const nm = document.querySelector('.railprodname');
      const r = nm.getBoundingClientRect();
      const lh = parseFloat(getComputedStyle(nm).lineHeight) || 0;
      return {
        footH: Math.round(foot.getBoundingClientRect().height),
        nameW: Math.round(r.width), nameH: Math.round(r.height),
        lines: lh ? Math.round(r.height / lh) : null,
        ready: (foot.innerText.match(/就绪/g) || []).length,
        footText: foot.innerText,
      };
    }""")
    check(shape["lines"] == 1,
          "the product name is one line, not 「模组工」/「坊」", shape)
    check(shape["nameW"] >= 90,
          "and it is given the width a four-character name needs", shape["nameW"])
    check(shape["ready"] == 1,
          "「就绪」 is printed once, not by the dot and by the count as well", shape)
    check(shape["footH"] <= 180,
          "the card stays under 180px in a 821px window", shape["footH"])

    # 4. the 0/-1 legend.  2026-11-11: it is a shut `<details id="edlegend">`
    # inside the record strip now, and its body is filled on first open, so the
    # probe has to open it before reading.  The words are the assertion; where
    # they sit on the page is not.
    pg.evaluate("() => { const d = document.getElementById('edlegend');"
                " if (d) d.open = true; }")
    pg.wait_for_timeout(300)
    leg = pg.evaluate("() => { const d = document.querySelector('#edlegend');"
                      " return d ? d.innerText : null; }")
    check(leg and "-1" in leg and "0" in leg,
          "a legend explains -1 and 0 where the numbers are", (leg or "")[:60])

    # 5. plain wording
    btns = pg.evaluate("() => Array.from(document.querySelectorAll('#fbody button'))"
                       ".slice(0, 2).map(b => b.textContent)")
    check(btns and btns[0] == "先看看", "the preview button says 先看看", btns)
    check(pg.evaluate("() => document.querySelector('#ed-save').textContent")
          == "保存全部改动", "the save button says 保存全部改动")
    check(bool(pg.evaluate("() => document.getElementById('ed-save-as')")),
          "there is a 另存为 button")
    check(bool(pg.evaluate("() => document.getElementById('ed-name')")),
          "and a name box, so a second mod can have its own name")

    # 6. the close guard reads the count.  `ED_PENDING` is a module-scope `let`,
    # so it is NOT a property of `window` -- a probe that sets `window.ED_PENDING`
    # changes nothing and would report a false green.  Drive the real setter.
    guard = pg.evaluate("""() => {
      const out = {fn: typeof window.__edGuard};
      const ev = new Event('beforeunload', {cancelable: true});
      window.dispatchEvent(ev);
      out.blockedWithZero = ev.defaultPrevented;
      edSyncPending(3, [{civ_all: false, copies: 1}, {civ_all: false, copies: 1},
                        {civ_all: true, copies: 63}]);
      out.label = document.querySelector('#edpend-n').textContent;
      const ev2 = new Event('beforeunload', {cancelable: true});
      window.dispatchEvent(ev2);
      out.blockedWithThree = ev2.defaultPrevented;
      out.ret = ev2.returnValue;
      edSyncPending(0);
      const ev3 = new Event('beforeunload', {cancelable: true});
      window.dispatchEvent(ev3);
      out.blockedAfterSave = ev3.defaultPrevented;
      return out;
    }""")
    check(guard["fn"] == "boolean", "the close guard is installed", guard["fn"])
    check(guard["blockedWithZero"] is False,
          "with nothing pending it does not nag", guard)
    check("已改 3 项" in (guard["label"] or "") and "63" in (guard["label"] or ""),
          "the header counts the edits and the records they cover",
          guard["label"])
    check(guard["blockedWithThree"] is True,
          "with 3 edits pending it blocks the close and asks", guard)
    check(guard["blockedAfterSave"] is False,
          "after the batch is saved it stops blocking", guard)

    # --- 7. prose fills the card instead of stopping at half of it --------
    #
    # Reported twice as a picture of the editor page (m19909 「怎么所有页面都变成
    # 这样了」 / m19912 「我没让你把这些留个那么大一片空啊」).  The paragraph was
    # capped at `--measure` (62ch, about 32 Chinese glyphs) inside a 1056px card,
    # which measured 509px of text and 526px of blank beside it, on seventeen
    # paragraphs across five views.  The first fix set the long ones in two
    # columns and made it worse: a sentence cut down the middle reads as broken.
    page = urllib.request.urlopen(BASE + "/static/index.html", timeout=60).read().decode("utf-8")
    cap = re.search(r"\.hint, \.box p, \.detailtext \{([^}]*)\}", page)
    check(bool(cap) and "max-width: none" in cap.group(1),
          "prose is not capped to a measure inside a card that wide",
          (cap.group(1).strip().splitlines()[-1:] if cap else []))
    check(".hint.split" not in page and 'class="hint split"' not in page,
          "and no hint is split into two columns")
    check(re.search(r"\.ablist p \{[^}]*max-width: var\(--measure\)", page) is not None,
          "while the about page keeps its measure, because its columns are narrow")

    pg.evaluate("showView('editor')")
    pg.wait_for_selector("#edlist .edrow", timeout=180000)
    wide = pg.evaluate("""() => {
      const out = [];
      for (const el of document.querySelectorAll('#view-editor .hint, #view-editor .box p')) {
        if (el.textContent.trim().length < 40) continue;
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        const lh = parseFloat(cs.lineHeight) || 1;
        const boxEl = el.closest('.box');
        const box = boxEl.getBoundingClientRect();
        // Is the space to this paragraph's right actually empty?  A hint that
        // shares its row with a button is narrow on purpose; one that has
        // nothing beside it and still stops at half the card is the report.
        const bx = Math.min(box.right, window.innerWidth) - 8;
        const hit = document.elementFromPoint(bx, r.top + r.height / 2);
        const beside = hit === boxEl ? "empty" : (boxEl.contains(hit) ? "self" : "other");
        out.push({
          chars: el.textContent.trim().length,
          display: cs.display,
          lines: Math.max(1, Math.round(r.height / lh)),
          w: Math.round(r.width),
          boxW: Math.round(box.width),
          blank: Math.round(box.right - r.right),
          beside: beside,
        });
      }
      return out;
    }""")
    check(len(wide) >= 1, "the editor has a long hint to measure", wide)
    # An inline `.hint` (the count next to a select, for one) is as wide as its
    # words; that is not a paragraph with half a card of nothing beside it.
    # Judged on the ones that actually wrap: a paragraph on two or more lines
    # has to use the width it was given.
    wraps = [x for x in wide if x["lines"] >= 2]
    check(len(wraps) >= 1, "at least one hint wraps onto two lines", wide)
    alone = [x for x in wraps if x["beside"] == "empty" and x["blank"] >= 200]
    check(not alone,
          "and none of them wraps with half a card of blank beside it", alone)

    # m20489 「预览，还没动任何文件」这张卡片里什么都没有：`#preview:empty`
    # hides the whole well, and `boot()` cleared the static empty sentence and
    # then removed its own 「正在读」 placeholder -- so the card drew as a heading
    # and a rule with nothing under it, which reads as a failed load.
    # The script switched to the editor above, and a hidden view measures 0 --
    # go back to home first or this reports "the well has no height".
    pg.evaluate("showView('home')")
    pg.wait_for_timeout(200)
    well = pg.evaluate("""() => {
      const pv = document.querySelector("#preview");
      const b = pv.getBoundingClientRect();
      return {disp: getComputedStyle(pv).display, h: Math.round(b.height),
              kids: pv.children.length,
              txt: (pv.textContent || "").trim()};
    }""")
    check(well["disp"] != "none" and well["h"] > 40,
          "the preview well is drawn before anything is written", well)
    check(bool(well["txt"]),
          "and it says what to do rather than drawing an empty box", well["txt"][:40])
    check("上面写点什么" in well["txt"], "the sentence is the one in the markup")

    # m20441 「这个右键菜单其实没必要有」.  The window is not a browser tab, but
    # WebView2 still offers 返回 / 刷新 / 另存为 / 打印 — 刷新 throws away an
    # unsaved edit and 另存为 writes the page's HTML to disk.  A text field
    # keeps its own menu: that is where 粘贴 lives.
    menu = pg.evaluate("""() => {
      const fire = (node) => {
        const ev = new MouseEvent("contextmenu",
          {bubbles: true, cancelable: true, clientX: 40, clientY: 40});
        return !node.dispatchEvent(ev);
      };
      return {
        body: fire(document.body),
        say: fire(document.querySelector("#say")),
      };
    }""")
    check(menu["body"] is True,
          "a right click on the page opens no menu", menu)
    check(menu["say"] is False,
          "but a text box keeps its own, where paste lives", menu)
    check('addEventListener("contextmenu"' in page,
          "the page owns the menu rather than the shell")
    check('tag === "input" || tag === "textarea"' in page,
          "and names the fields it leaves alone")

    pg.screenshot(path=os.path.join(SHOTS, "fixes_2026_11_02.png"))
    b.close()

print("FAILED: %s" % fails if fails else "UI FIXES: ALL PASSED")
sys.exit(1 if fails else 0)

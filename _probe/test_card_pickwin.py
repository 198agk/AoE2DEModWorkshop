# -*- coding: utf-8 -*-
"""The icon window: click a box, get a wall of pictures, click one to place it.

Reported 2026-11-09, verbatim: 「你应该改成我点格子就能让我输入名字或编码，或者给
我个窗口，把全部内容都列出来，像手机桌面那样一个个图标，图标下面有名字和id」 and,
about the same build, 「我现在点格子什么反应都没有」.

The second sentence was not a missing feature: the click handler ran, the strip
was drawn, and it was drawn 912 px down a 1000 px window -- below the fold.  So
this nail checks both halves: the STRIP is on screen after a click on a box that
has something, and an EMPTY box opens the window instead of collapsing the strip.

What must not come back:
  * a second way to add a unit.  `cardPut` read `cardFreeBox()` (the first free
    box off the DOM), so picking box 16 put the unit in box 5 -- and its toast
    named a box the player never touched.  `cardPickTake` uses `CARD_PICKBOX`.
  * the always-empty inline list.  `drawPickList` kept painting a `CARD_PICK`
    array nobody filled, under a search box that now opens the window.
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO)

BASE = os.environ.get("BASE", "http://127.0.0.1:7811")
PAGE = os.path.join(REPO, "aoe2mod", "ui", "static", "index.html")
SHOTS = os.path.join(REPO, "_shots", "now")

FAILS = []


def check(ok, what, got=""):
    if ok:
        print("  ok   %s :: %s" % (what, got))
    else:
        print("  FAIL %s :: %s" % (what, got))
        FAILS.append(what)


def section(title):
    print()
    print("=== %s" % title)


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=240) as r:
        return json.loads(r.read().decode("utf-8"))


def get_until(path, ready, timeout=180.0):
    """GET `path` until `ready(json)` says yes, riding out a reset socket.

    WHY THIS EXISTS: a real write here is 20-31 s of server work (63
    civilizations spliced plus a re-walk of the model), and a client that
    asks for the result too early can see the connection reset rather than
    an answer -- measured 2026-11-12: `[WinError 10054] 远程主机强迫关闭了
    一个现有的连接。` on the pseudo-page read right after an icon click, with
    the write itself landing fine a moment later.  A reset is therefore a
    retry, and "not yet" is a wait, not a failure.
    """
    deadline = time.time() + timeout
    last = None
    while True:
        try:
            got = get(path)
            last = got
            if ready(got):
                return got
        except Exception as exc:                            # noqa: BLE001
            last = {"error": str(exc)}
        if time.time() >= deadline:
            return last
        time.sleep(1.0)


def main():
    with io.open(PAGE, "r", encoding="utf-8") as fh:
        page = fh.read()

    section("1. the window exists, and it is a dialog")
    check('id="cardpick" role="dialog" aria-modal="true"' in page,
          "the panel is announced as a modal dialog")
    check('aria-labelledby="cardpick-title"' in page,
          "and it names its own heading, so a screen reader has a title")
    for part, why in (("cardpick-q", "the search box"),
                      ("cardpick-go", "the search button"),
                      ("cardpick-grid", "the wall of pictures"),
                      ("cardpick-more", "再加载一批"),
                      ("cardpick-seen", "which box, how many units"),
                      ("cardpick-close", "关上"),
                      ("cardpick-x", "the × in the corner")):
        check('id="%s"' % part in page, "the window has %s" % why, part)

    section("2. it is a fixed overlay, not another row in the page")
    # `position: fixed; inset: 0` is what separates "a window" from "a block that
    # happens to be lower down" -- the exact failure this report was about.
    check("#cardpick {\n    position: fixed;" in page
          or "#cardpick {\r\n    position: fixed;" in page,
          "the overlay is pinned to the viewport")
    check("#cardpick.open { display: flex; }" in page,
          "opening it is a class, and the class is what draws it")
    check("#cardpick .ckpanel" in page and "min(900px, 100%)" in page,
          "the panel is capped at 900px and never wider than the window")

    section("3. the two halves of 「点格子什么反应都没有」")
    # (a) an empty box SELECTS, it does not select nothing.  The first fix here
    # opened the picker window straight away, which answered the click and hid
    # the answer: the strip -- and with it the 伪翻页 block -- never appeared, so
    # a player who wanted a paging button got a wall of unit icons and nothing
    # else (reported 2026-11-10 with a screenshot: 「没看到有啊」).
    check("""  if (!info) {
    CARD_SLOT = box;
    CARD_CHAIN_UNIT = null;
    drawSlotStrip();""" in page,
          "an empty box is SELECTED, so the strip under it is the one that offers "
          "放一个单位进这一格 and 建伪翻页按钮")
    # (a2) ...AND the window opens on top of that strip.  2026-11-10 second
    # report: 「你怎么把我图标窗口给关了，你就不能在图标窗口那给这个功能吗」.
    # Both halves are answered at once now: the strip is drawn (so it survives
    # the window closing) and the window opens over it.
    check("""    drawSlotStrip();
    const host0 = $("#card-slot");
    if (host0 && host0.scrollIntoView) host0.scrollIntoView({ block: "nearest" });"""
          in page,
          "and its strip is drawn before the window covers it")
    empty = page[page.find("if (!info) {"):]
    empty = empty[:empty.find("return;")]
    check("cardPickOpen(box);" in empty,
          "an empty box opens the picker window as well, which is where the "
          "player looks for it")
    check("""  if (CARD_SLOT === null) {
    host.appendChild(el("div", "cslotrow",""" in page,
          "and with nothing selected the strip still says what a click would do, "
          "instead of hiding itself")
    # (b) a box with content scrolls its strip into view
    check('host.scrollIntoView({ block: "nearest" })' in page,
          "a box with content brings its strip on screen")
    # the scroll must live in the CLICK, not in the draw: `loadCard` redraws the
    # strip after every edit, and a redraw that scrolls moves the page under the
    # player's hands.
    strip = page[page.find("function drawSlotStrip()"):]
    strip = strip[:strip.find("\nfunction ", 10) if strip.find("\nfunction ", 10) > 0 else len(strip)]
    check("scrollIntoView" not in strip,
          "drawing the strip never moves the page")
    # A REDRAW MUST NOT THROW WHEN THE GRID IS NOT ON SCREEN.  `cardCyclesRefresh`
    # runs after 撤回 / a live tick against whatever building is loaded, and
    # `cardCellAt` answers null whenever `#cardgrid` is empty or the box was
    # filtered out by the age chips.  Measured 2026-11-12 in the browser, on the
    # card page itself:
    #   TypeError: Cannot read properties of null (reading 'querySelector')
    #       at drawSlotStrip (index.html:11097:21)
    #       at cardCyclesRefresh (index.html:11307:3)
    # One null dereference took `cardPaintAges()` and every badge repaint down
    # with it, so the age filter and the 伪翻页 counts silently stopped matching
    # the file.  The name is decoration -- `pick.name` names the unit anyway.
    check('const name = cell ? cell.querySelector(".cardname") : null;' in strip,
          "the strip survives a box whose cell is not in the grid")
    check(not re.search(r"^\s*const name = cell\.querySelector", strip, re.M),
          "and never dereferences that cell unguarded")
    check('fill.id = "card-slot-add";' in page,
          "an empty box offers a button, because a sentence is not a control")
    check('fill.onclick = () => cardPickOpenKind(CARD_SLOT, "unit");' in page,
          "and that button opens the SAME window, on the unit list")
    check('fillBld.onclick = () => cardPickOpenKind(CARD_SLOT, "building");' in page,
          "while the button beside it opens the list of buildings -- one box, "
          "no list chosen for the player")
    check("drawCycleBlock(host, CARD_SLOT);" in strip,
          "a box with no unit still shows its pseudo-pages")
    # ...and it must not call that box empty while listing five pages under it.
    check('line = "第 " + CARD_SLOT + " 格没有单位，但有 " + nPages + " 页。";' in page,
          "a box with pages is not described as empty")
    check('const cyc0 = CARD_CYCLES[String(CARD_SLOT)];' in page,
          "the sentence reads the page count the badge reads")

    section("4. the unit lands in the box that was clicked")
    check("const box = CARD_PICKBOX;" in page,
          "the put reads the box the window was opened for")
    take = page[page.find("async function cardPickTake"):]
    take = take[:take.find("\n// ----", 10)]
    check("= cardFreeBox()" not in take,
          "and NOT the first free box off the DOM", "cardFreeBox in cardPickTake")
    check('box: box,' in take, "the request carries that box")
    check("CARD_SLOT = box;" in take, "the strip reopens on that box")
    check('if (kind !== "tech") CARD_CHAIN_UNIT = id;' in take,
          "and it follows the unit, because a technology is not the unit "
          "this box is showing")

    section("4b. the same window also fills a PSEUDO PAGE")
    # 「就不能直接让我选那个格子，创建一个伪翻页按钮，再在这页里自己按格子来添加吗」
    # (2026-11-10).  The answer is one window with two meanings: a dashed tile on
    # a page opens the SAME picker, and the click lands on the page's effect
    # record instead of on the box's training list.  A second picker would be
    # the second implementation this file exists to forbid.
    check("function cardPickOpenPage(box, page, slot)" in page,
          "a page's dashed tile opens the window, aimed at that page")
    check("CARD_PICKPAGE_AT !== null" in take,
          "and the click decides between the two writes, not the open")
    check('api("/api/pseudo-page-put"' in take,
          "the page branch asks the page route")
    check("CARD_PICKPAGE_AT = null;" in page,
          "closing the window clears the aim, so the next pick is a box again")
    # The three sentences were pulled into one function so a box, a page and a
    # page cell can each name themselves -- pin the function, not one branch.
    check("function cardPickSyncTitle()" in page
          and 'if (CARD_PICKPAGE_AT === null) {' in page,
          "and the title says which of the two the click will do")

    section("4c. 伪翻页 lives INSIDE the window, above the list")
    # 「你怎么把我图标窗口给关了，你就不能在图标窗口那给这个功能吗」 (2026-11-10).
    # The window is the answer to 「这一格放什么」, and a paging button is one of
    # the answers, so the chips that aim it are drawn in the window itself.
    check('<div class="ckpages" id="cardpick-pages"></div>' in page,
          "the window has a strip of its own for the page chips")
    check("function cardPickPagesDraw()" in page,
          "and it is drawn from the same page list the badge counts")
    check('chip.id = "cardpick-page-" + (k + 1);' in page,
          "one chip per page")
    check('const add = el("button", "chip",' in page
          and '"在这一格建一个伪翻页按钮") ' in page
          or 'pages.length ? "再加一页（空的）" : "在这一格建一个伪翻页按钮"' in page,
          "the first chip makes the paging button, later ones add a page")
    check("function cardPickAim(box, page, slot)" in page,
          "clicking a chip aims the SAME window, it does not close it")
    check("cardPickPagesDraw();\n  host.classList.add(\"open\");" in page,
          "the chips are drawn before the window is shown, not after a request")
    # 2026-11-11: the redraw is no longer a bare `cardPickPagesDraw()` in the
    # click handler.  A page write answers with the box's new `page_list`, and
    # `cardLivePaint` repaints the strip, the tile badge and the chips from it
    # -- so what must be pinned is that the click reaches that repaint.
    check("cardLivePaint(box);" in take
          and "cardPagesSet(box, rr.page_list);" in take,
          "and after a page edit the strip, the badge and the chips are repainted",
          "from the answer, not from a whole card re-read")
    check("cardPickClose();" not in take[take.find("CARD_PICKPAGE_AT !== null"):
                                        take.find("if (cell) cell.classList.add(\"busy\");",
                                                  take.find("CARD_PICKPAGE_AT !== null"))],
          "a page put does NOT close the window: a page is several units in a row")
    check("b.disabled = dead;" in page,
          "the 建筑 and 科技 tabs are switched off while aimed at a page, instead "
          "of staying clickable and doing nothing")

    section("5. one picker, not two")
    # Both paths must end in the same window: a second implementation is how the
    # two answers drifted apart in the first place.
    check("function cardPick(q) {" in page and "cardPickOpen(box || 1);" in page,
          "the inline search box opens the same window")
    for gone, why in (("drawPickList", "the dead list painter"),
                      ("cardPut(", "the second add-a-unit path"),
                      ('id="card-pick-list"', "the empty list container"),
                      (".cpickrow", "the row style for that list"),
                      ("let CARD_PICK = []", "the array nobody filled")):
        check(gone not in page, "%s is gone" % why, page.count(gone))

    section("6. a page of 120, and the icon batch")
    check("const CARD_PICKPAGE = 120;" in page,
          "the window asks for 120 rows at a time (one icon costs 8.56 ms)")
    check('api("/api/icons?kind=" + kind + "&size=40&ids="' in page,
          "the pictures come in ONE batch request, not 120 of them")
    # The batch is SMALLER than the route's 800-id cap on purpose.  Measured
    # 2026-11-09 against the shipped build: a batch is painted only after it
    # comes back, so one 800-id call left all 120 cells on 「?」 for 7.7 s.  A
    # batch no bigger than the page makes the first pictures land in ~0.6 s.
    _pb = re.search(r"const CARD_PICKBATCH = (\d+);", page)
    check(_pb is not None and 0 < int(_pb.group(1)) <= 120,
          "and in batches no bigger than one page, so the first pictures land at once",
          _pb.group(1) if _pb else "missing")
    check("cell.onclick = () => cardPickTake(row.id, cell);" in page,
          "a tile is the button -- clicking the picture places the unit")
    check('cell.appendChild(el("div", "nid", "编号 " + row.id));' in page,
          "each tile prints its id under the name, as asked")

    section("7. Esc closes this window, and only this window")
    check('const p = $("#cardpick");' in page
          and 'if (p && p.classList && p.classList.contains("open")) cardPickClose();'
          in page,
          "there is a keydown listener that only knows about this window")
    check('if (ev && ev.target === ev.currentTarget) cardPickClose();' in page,
          "clicking the backdrop closes it, clicking the panel does not")

    section("8. in a real page: click an empty box, get icons, place one")
    if not os.path.isdir(SHOTS):
        os.makedirs(SHOTS)
    from playwright.sync_api import sync_playwright
    post("/api/session-reset", {})
    wrote = []

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1360, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/", wait_until="load")
        pg.wait_for_selector("#mods .mod", state="attached", timeout=90000)
        pg.evaluate("showView('card')")
        pg.wait_for_function(
            "() => document.querySelectorAll('#cardgrid .cardslot').length >= 15",
            timeout=180000)
        pg.wait_for_timeout(400)

        check(pg.evaluate("""() => {
            const p = document.querySelector('#cardpick');
            return !!p && getComputedStyle(p).display === 'none';
        }"""), "the window starts closed")

        # Pick a box with no unit in it.  Depending on the file it may still
        # carry research buttons, in which case the strip opens and offers the
        # button -- both routes must reach the same window.
        target = pg.evaluate("""() => {
            const c = [...document.querySelectorAll('#cardgrid .cardslot')]
              .find(x => !x.dataset.unit);
            return c ? Number(c.dataset.box) : null;
        }""")
        check(target is not None, "some box has no unit in this file", target)
        if target is None:
            br.close()
            print()
            print("PICK WINDOW: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
            return 1

        pg.click('#cardgrid .cardslot[data-box="%d"]' % target)
        pg.wait_for_timeout(1200)
        opened = pg.evaluate("""() => {
            const p = document.querySelector('#cardpick');
            return !!(p && p.classList.contains('open'));
        }""")
        if not opened:
            # A tech-only box: the strip opened and carries the button.
            has = pg.evaluate("() => !!document.querySelector('#card-slot-add')")
            check(has, "a box with research but no unit offers the button", has)
            if has:
                pg.click("#card-slot-add")
                pg.wait_for_timeout(900)
                opened = pg.evaluate("""() => {
                    const p = document.querySelector('#cardpick');
                    return !!(p && p.classList.contains('open'));
                }""")
        check(opened, "clicking box %s opened the window" % target, opened)
        # A wall that is empty because the answer has not arrived is not an
        # empty wall: 2026-11-09 this nail failed six checks at once under load.
        pg.wait_for_function(
            "() => { const g = document.querySelector('#cardpick.open #cardpick-grid');"
            " if (!g) return false; const c = g.querySelectorAll('.cell');"
            " return c.length > 0 && !!(c[0].querySelector('.nid') || {}).textContent; }",
            timeout=180000)

        body = pg.evaluate("""() => {
            const g = document.querySelector('#cardpick-grid');
            const cells = g ? [...g.querySelectorAll('.cell')] : [];
            const first = cells[0] || null;
            return {
              box: window.CARD_PICKBOX === undefined ? null : null,
              title: (document.querySelector('#cardpick-title') || {}).textContent || '',
              tiles: cells.length,
              nm: first ? (first.querySelector('.nm') || {}).textContent || '' : '',
              nid: first ? (first.querySelector('.nid') || {}).textContent || '' : '',
              unit: first ? first.dataset.unit || '' : '',
              seen: (document.querySelector('#cardpick-seen') || {}).textContent || '',
              note: (document.querySelector('#cardpick-note') || {}).textContent || '',
              more: (() => { const m = document.querySelector('#cardpick-more');
                             return m ? !m.hidden : false; })(),
            };
        }""")
        check("第 %d 格" % target in body["title"],
              "the title names the box that was clicked", body["title"])
        check(body["tiles"] >= 100, "the wall is a page of icons, not a list",
              body["tiles"])
        check(bool(body["nm"]) and bool(body["nid"]),
              "each tile has a name AND an id under it",
              (body["nm"], body["nid"]))
        check("编号 " in body["nid"], "and the id line says 编号", body["nid"])
        check("单位一共" in body["seen"], "the footer counts the units",
              body["seen"])
        # Taken HERE, while the wall is on screen: a screenshot after the window
        # closes proves the strip and says nothing about the thing that was asked
        # for.  「像手机桌面那样一个个图标，图标下面有名字和id」.
        pg.screenshot(path=os.path.join(SHOTS, "card_pick_window.png"))

        # Type the id of the first tile; the wall must narrow to it.  Using the
        # tile's OWN id keeps this nail independent of which file is loaded.
        # 83 是村民，名字里没有第二个人拿它当子串；用 0 会同时命中「雪山 2」，
        # 因为搜索是子串匹配不是编号匹配（实测：`q=0` 两行）。
        want = "83"
        pg.fill("#cardpick-q", want)
        pg.click("#cardpick-go")
        # 搜索是子串匹配，不是编号匹配：`q=83` 的答案里除了 83 还有 283、483、
        # 1083，以及名字里带 83 的（实测 total 34，第一行就是 83）。所以这里钉
        # 的是「那一条排在第一」，加上「其余每一条要么编号里有这几个字，要么名字
        # 里有」，而不是旧的那套「结果不超过四条」。2026-11-16 用户原话：检索
        # 应该把含这几个字的全列出来。
        pg.wait_for_function(
            "(w) => { const c = [...document.querySelectorAll('#cardpick-grid .cell')];"
            " return c.length > 0 && c[0].dataset.unit === w; }",
            arg=want, timeout=180000)
        one = pg.evaluate("""(w) => {
            const cells = [...document.querySelectorAll('#cardpick-grid .cell')];
            const bad = cells.filter(c => {
                const u = c.dataset.unit || '';
                const nm = ((c.querySelector('.nm') || {}).textContent || '');
                return !u.includes(w) && nm.toLowerCase().indexOf(w.toLowerCase()) < 0;
            }).map(c => c.dataset.unit);
            return {n: cells.length,
                    first: cells[0] ? cells[0].dataset.unit : '',
                    units: cells.slice(0, 4).map(c => c.dataset.unit),
                    bad: bad.slice(0, 4),
                    nm: cells[0] ? (cells[0].querySelector('.nm') || {}).textContent : ''};
        }""", want)
        check(one["n"] >= 1 and one["first"] == want,
              "typing an id puts that unit on the first tile", one)
        check(one["bad"] == [],
              "and every other tile spells those digits, in its number or its name",
              one["bad"])

        # Place it.  The unit must land in the box that was clicked.
        pg.click("#cardpick-grid .cell")
        pg.wait_for_function(
            """(a) => {
                const c = document.querySelector(
                    '#cardgrid .cardslot[data-box="' + a.box + '"]');
                return !!(c && c.dataset.unit === a.unit);
            }""", arg={"box": target, "unit": want}, timeout=180000)
        wrote.append((target, want))
        state = pg.evaluate("""(b) => {
            const c = document.querySelector('#cardgrid .cardslot[data-box="' + b + '"]');
            const p = document.querySelector('#cardpick');
            return {unit: c ? (c.dataset.unit || '') : '',
                    open: !!(p && p.classList.contains('open')),
                    strip: (() => { const s = document.querySelector('#card-slot');
                                    return s ? !s.hidden : false; })()};
        }""", target)
        check(state["unit"] == want,
              "the unit landed in box %d, the box that was clicked" % target,
              (state["unit"], want))
        check(not state["open"], "and the window closed itself", state["open"])
        check(state["strip"], "the strip follows the unit that landed", state["strip"])

        # Escape, from a freshly opened window.
        pg.evaluate("showView('card')")
        pg.click('#cardgrid .cardslot[data-box="%d"]' % target)
        pg.wait_for_timeout(600)
        pg.evaluate("""() => { const c = document.querySelector('#cardgrid .cardslot'
            + '[data-box="' + 1 + '"]'); if (c) c.click(); }""")
        pg.wait_for_timeout(600)
        is_open = pg.evaluate("""() => {
            const p = document.querySelector('#cardpick');
            return !!(p && p.classList.contains('open'));
        }""")
        if is_open:
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(400)
        after_esc = pg.evaluate("""() => {
            const p = document.querySelector('#cardpick');
            return !!(p && p.classList.contains('open'));
        }""")
        check(not after_esc, "Escape closes the window", (is_open, after_esc))

        pg.screenshot(path=os.path.join(SHOTS, "card_pick_placed.png"))
        check(not errs, "no page errors", errs)
        pg.close()
        br.close()

    section("8b. in a real page: the window makes a paging button and fills a page")
    # 「你怎么把我图标窗口给关了，你就不能在图标窗口那给这个功能吗」 (2026-11-10).
    # End to end: click an empty box, the window opens, the window carries 伪翻页,
    # the first click makes an empty page, clicking 第 1 页 aims the SAME window at
    # it, one icon click fills it and the window STAYS OPEN -- because a page is
    # several units in a row.
    try:
        post("/api/session-reset", {})
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1360, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/", wait_until="load")
            pg.wait_for_selector("#mods .mod", state="attached", timeout=90000)
            pg.evaluate("showView('card')")
            pg.wait_for_function(
                "() => document.querySelectorAll('#cardgrid .cardslot').length >= 15",
                timeout=180000)
            pg.wait_for_timeout(400)
            box = pg.evaluate("""() => {
                const c = [...document.querySelectorAll('#cardgrid .cardslot')]
                    .find(x => !x.dataset.unit && !x.dataset.tech);
                return c ? Number(c.dataset.box) : null;
            }""")
            check(box is not None, "there is an empty box to build a pager on", box)
            pg.click('#cardgrid .cardslot[data-box="%d"]' % box)
            pg.wait_for_timeout(1200)
            check(pg.evaluate("() => { const p = document.querySelector('#cardpick');"
                              " return !!(p && p.classList.contains('open')); }"),
                  "the click on an empty box opens the window")
            check(pg.evaluate("() => !!document.querySelector('#cardpick-pages')"),
                  "and the window has a 伪翻页 strip of its own")
            check(pg.evaluate("() => !!document.querySelector('#cardpick-page-add')"),
                  "with the button that makes the paging button")
            pg.click("#cardpick-page-add")
            pg.wait_for_function(
                "() => !!document.querySelector('#cardpick-page-1')",
                timeout=120000)
            chips = pg.evaluate("""() => {
                const h = document.querySelector('#cardpick-pages');
                return [...h.querySelectorAll('button')].map(b => b.textContent);
            }""")
            check(any("第 1 页" in c for c in chips),
                  "the first page appears as a chip IN the window", chips)
            check(pg.evaluate("() => { const p = document.querySelector('#cardpick');"
                              " return !!(p && p.classList.contains('open')); }"),
                  "and the window is still open -- making a page is not a reason to close it")
            pg.click("#cardpick-page-1")
            pg.wait_for_timeout(700)
            title = pg.eval_on_selector("#cardpick-title", "e => e.textContent")
            check("第 1 页" in title, "clicking the chip aims the window at that page",
                  title)
            check(pg.evaluate("() => document.querySelector('#cardpick-page-1')"
                              ".getAttribute('aria-pressed') === 'true'"),
                  "and the chip says it is the one being filled")
            check(pg.evaluate("() => document.querySelector('#cardpick-tech').disabled"),
                  "the 科技 tab is off while aimed at a page: a page holds units")
            pg.fill("#cardpick-q", "83")
            pg.click("#cardpick-go")
            pg.wait_for_function(
                "(w) => [...document.querySelectorAll('#cardpick-grid .cell')]"
                " .some(x => x.dataset.unit === w)", arg="83", timeout=180000)
            pg.click('#cardpick-grid .cell[data-unit="83"]')
            pg.wait_for_timeout(2500)
            check(pg.evaluate("() => { const p = document.querySelector('#cardpick');"
                              " return !!(p && p.classList.contains('open')); }"),
                  "one icon fills one slot and the window STAYS open for the next one")
            aim = pg.eval_on_selector("#cardpick-title", "e => e.textContent")
            check("第 1 页" in aim, "still aimed at the same page", aim)
            pg.screenshot(path=os.path.join(SHOTS, "card_pick_page.png"))
            bld = pg.evaluate("() => Number(CARD_BUILDING || 0)")
            # WAIT FOR THE PAGE TO BE ON DISK, do not read once and call it a
            # failure.  A write is 20-31 s of server work, and a read that lands
            # in the middle of it can come back as a reset socket rather than an
            # answer (see `get_until`).  Waiting for the CONTENT -- one page,
            # with 村民 on it -- is also the honest assertion: the strip can be
            # repainted a frame before the record it draws exists.
            got = get_until(
                "/api/pseudo-pages?building=%d&box=%d" % (bld, box),
                lambda j: len(j.get("page_list") or []) == 1
                and [u.get("name") for p in (j.get("page_list") or [])
                     for u in (p.get("on_list") or [])] == ["村民 (男性)"])
            pages = got.get("page_list") or []
            check(len(pages) == 1, "the page exists on disk",
                  got.get("error") or len(pages))
            names = [u.get("name") for p in pages for u in (p.get("on_list") or [])]
            check(names == ["村民 (男性)"],
                  "and 村民 is on it, by name", names)
            # Close, then confirm the strip under the card is still the way back in.
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(400)
            strip = pg.evaluate("() => { const s = document.querySelector('#card-slot');"
                                " return s ? (s.textContent || '') : ''; }")
            check("伪翻页" in strip,
                  "and with the window closed the strip under the box still carries it",
                  strip[:120])
            check(not errs, "no page errors on the way", errs)
            pg.close()
            br.close()
    except Exception as exc:                                # noqa: BLE001
        check(False, "a paging button can be made and filled from the window", exc)
    finally:
        try:
            for _ in range(int(get("/api/session-info").get("undo") or 0)):
                post("/api/undo", {})
        except Exception:                                   # noqa: BLE001
            pass

    section("9. two lists in one window, and 全部显示 is a layout choice")
    # The user asked (2026-11-09) for 「两个列表，一个单位，一个科技」 and for
    # 「给个全部显示」.  Both are the same window: a kind switch, and a limit that
    # stops being 120 without stopping being honest about pictures still coming.
    for part, why in (("cardpick-unit", "the unit chip"),
                      ("cardpick-tech", "the technology chip"),
                      ("cardpick-all", "the 全部显示 chip")):
        check('id="%s"' % part in page, "the window has %s" % why, part)
    check('let CARD_PICKKIND = "unit";' in page,
          "the window opens on the unit list")
    check('let CARD_PICKALL = false;' in page,
          "and starts on one page, because pictures are the expensive half")
    _pb2 = re.search(r"const CARD_PICKBATCH = (\d+);", page)
    check(_pb2 is not None and 0 < int(_pb2.group(1)) <= 120,
          "pictures are fetched in batches no bigger than one page",
          _pb2.group(1) if _pb2 else "missing")
    check("function cardPickSetKind(kind) {" in page,
          "switching lists is one function, so the chips and the words cannot drift")
    check("打科技名或编号，比如 织布机、22" in page,
          "the search box says which list it is searching")
    check('const key = kind + ":" + row.id;' in page
          and "cell.dataset.pick = key;" in page,
          "a cell knows which list it came from, not just its number")
    # A BUILDING is a unit record (type 80), so it lands under `data-unit` too --
    # the attribute the `/api/card-put` write path reads.  Written as a test so
    # the day a third list grows a fourth attribute, this says which one is
    # wrong instead of a cell silently writing to a key nothing reads.
    check('if (kind === "tech") cell.dataset.tech = String(row.id);' in page
          and "else cell.dataset.unit = String(row.id);" in page,
          "and it lands under the attribute that list's write path reads")
    check("const limit = CARD_PICKALL ? 20000 : CARD_PICKPAGE;" in page,
          "全部显示 asks for the whole list in one call")
    check("async function cardPickFillIcons(rows) {" in page,
          "and the pictures arrive after the names do")
    check("#cardpick .cell.waiting .blank" in page,
          "「图还没到」 and 「没有图」 are two different states")
    check('api("/api/card-put-tech", {' in page and 'api("/api/card-put", {' in page,
          "a click goes down one of two write paths, by list")
    # A box that holds a technology is not empty either.  Same lesson as the
    # pseudo-page one, one level over.
    check("没有单位，但有" in page, "a box with technologies is not called empty")
    check("nTech" in page, "and the sentence counts them")

    section("10. the technology write path, in bytes")
    # A unit's button lives on the BUILDING; a technology's button lives on the
    # TECHNOLOGY.  Two directions, so two write paths -- and the technology one
    # gets its room by re-using a slot that already says 「not placed anywhere」
    # (`location_id == -1`), which is why hanging a button on a tech costs 0 bytes.
    base = None
    try:
        post("/api/session-reset", {})
        base = int(get("/api/session-info").get("bytes") or 0)
        check(base > 0, "the file has bytes to begin with", base)

        first = post("/api/card-put-tech", {"tech": 37, "building": 12, "box": 16})
        check(first.get("ok") is True, "a technology can be put on a box", first.get("error"))
        want = first.get("label") or ""
        check("炮舰" in want or "37" in want, "and the label says which one", want)
        check(first.get("slot") is not None and int(first.get("slot")) >= 0,
              "it landed in an existing research slot", first.get("slot"))

        card = get("/api/card?building=12")
        box = [b for b in (card.get("boxes") or []) if int(b.get("button") or 0) == 16]
        box = box[0] if box else {}
        got = [int(t.get("tech") or 0) for t in (box.get("techs") or [])]
        check(37 in got, "the card now lists it on box 16", got)
        check(int(box.get("count") or 0) == 0,
              "and it is a technology, not a unit", box.get("count"))

        # ALREADY ON THIS BOX IS AN OVERWRITE, NOT A REFUSAL.  Until 2026-11-11
        # this answered 「已经在这座建筑的第 16 格上了」, the same wall the unit
        # picker had; the player's answer was 【格子上有了东西，谁告诉你不能覆盖放
        # 更多的】.  So the second write lands on the SAME slot and the card still
        # shows one button -- what must not come back is a second slot holding the
        # same technology on the same box.
        again = post("/api/card-put-tech", {"tech": 37, "building": 12, "box": 16})
        check(again.get("ok") is True and not again.get("grew"),
              "the same technology twice on one box overwrites that box",
              again.get("error") or again.get("slot"))
        check(int(again.get("slot") if again.get("slot") is not None else -2)
              == int(first.get("slot")),
              "and it lands on the slot that was already there, not a second one",
              (first.get("slot"), again.get("slot")))
        card = get("/api/card?building=12")
        box = [b for b in (card.get("boxes") or []) if int(b.get("button") or 0) == 16]
        box = box[0] if box else {}
        check([int(t.get("tech") or 0) for t in (box.get("techs") or [])] == [37],
              "so the card still carries exactly one button for it",
              [t.get("tech") for t in (box.get("techs") or [])])

        over = post("/api/card-put-tech", {"tech": 37, "building": 12, "box": 31})
        check(over.get("ok") is False and "30" in (over.get("error") or ""),
              "a box past the second screen is refused", over.get("error"))

        # Tech 22 「织布机」 has its one and only slot on the Town Center.  Until
        # 2026-11-10 that was a refusal with advice attached, which the player
        # answered with 「都说了编辑所有都可以做，不能有任何限制，除非是引擎无法
        # 识别运行」 -- the record can grow, so the refusal was the tool's own
        # opinion, not the engine's.  470 of the 536 named technologies had no
        # free slot, so this was most of the list.
        grown_from = int(get("/api/session-info").get("bytes") or 0)
        full = post("/api/card-put-tech", {"tech": 22, "building": 12, "box": 20})
        check(full.get("ok") is True and full.get("grew") is True,
              "a technology with every slot spoken for gets a NEW slot",
              full.get("error"))
        check(int(get("/api/session-info").get("bytes") or 0) == grown_from + 9,
              "and the record grew by exactly one nine-byte slot",
              (grown_from, get("/api/session-info").get("bytes")))
        card = get("/api/card?building=12")
        box = [b for b in (card.get("boxes") or []) if int(b.get("button") or 0) == 20]
        box = box[0] if box else {}
        check(22 in [int(t.get("tech") or 0) for t in (box.get("techs") or [])],
              "and the card lists it on the box that was clicked",
              [t.get("tech") for t in (box.get("techs") or [])])

        for _ in range(int(get("/api/session-info").get("undo") or 0)):
            post("/api/undo", {})
        check(int(get("/api/session-info").get("bytes") or 0) == base,
              "one undo per write puts the file back", get("/api/session-info").get("bytes"))

        # THE REGRESSION THIS SECTION EXISTS FOR: the write patches `tk._techs`
        # in place so the card page can see it before saving.  Undo puts the
        # bytes back and, until 2026-11-09, left that patch standing -- the same
        # box then answered 「已经在这座建筑的第 16 格上了」 for a technology that
        # was no longer anywhere.  A model patched by the write has to be dropped
        # by the undo.
        second = post("/api/card-put-tech", {"tech": 37, "building": 12, "box": 16})
        check(second.get("ok") is True,
              "undone and put again: the same technology still lands",
              second.get("error"))
        card = get("/api/card?building=12")
        box = [b for b in (card.get("boxes") or []) if int(b.get("button") or 0) == 16]
        box = box[0] if box else {}
        check(37 in [int(t.get("tech") or 0) for t in (box.get("techs") or [])],
              "and the card shows it once, in the same slot",
              [t.get("tech") for t in (box.get("techs") or [])])
    except Exception as exc:                                # noqa: BLE001
        check(False, "the technology write path answers in bytes", exc)
    finally:
        try:
            for _ in range(int(get("/api/session-info").get("undo") or 0)):
                post("/api/undo", {})
            if base:
                check(int(get("/api/session-info").get("bytes") or 0) == base,
                      "the technology section left the file as it found it",
                      get("/api/session-info").get("bytes"))
        except Exception as exc:                            # noqa: BLE001
            check(False, "the technology section cleans up", exc)

    section("11. a box with something in it, a second copy, and the era filter")
    # Three reports in a row, all about the same wall: 「都说了格子上有东西，就点
    # 不出来」 (a box with a unit offered no way in), 「添加了，也不刷新」 (the write
    # landed and the grid looked untouched) and 「谁告诉你不能重复的」 (the tool
    # refused a unit that was already on ANOTHER box of the same building).
    check("function cardPickOpenKind(box, kind) {" in page,
          "there is one entry point that opens the window onto a box AND a list")
    check('addUnit.id = "card-slot-addunit";' in page
          and 'addTech.id = "card-slot-addtech";' in page,
          "a box that already holds something offers both writes")
    check('addUnit.onclick = () => cardPickOpenKind(CARD_SLOT, "unit");' in page
          and 'addTech.onclick = () => cardPickOpenKind(CARD_SLOT, "tech");' in page,
          "and each button names the list it wants, so the player does not land "
          "on units and have to find technologies")
    check('let CARD_FRESH = "";' in page,
          "the box just written to is remembered")
    check("!!want && !usable && !fresh" in page,
          "the era filter leaves that one box lit instead of erasing the answer "
          "to what the player just did")
    check('CARD_FRESH = String(box);' in page,
          "the write is what marks the box")

    # The rule the report was about, run against a real page: with an era picked
    # that hides the box, writing into it must still leave it readable.
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1360, "height": 1000})
            pg.goto(BASE + "/", wait_until="load")
            pg.wait_for_selector("#mods .mod", state="attached", timeout=90000)
            pg.evaluate("showView('card')")
            pg.wait_for_function(
                "() => document.querySelectorAll('#cardgrid .cardslot').length >= 15",
                timeout=180000)
            got = pg.evaluate("""() => {
                const cell = [...document.querySelectorAll('#cardgrid .cardslot')]
                  .find(x => !x.dataset.unit);
                if (!cell) return null;
                CARD_AGE = "1";              // 黑暗时代: almost everything dims
                CARD_FRESH = String(cell.dataset.box);
                cardPaintAges();
                const kept = !cell.classList.contains("agegone");
                CARD_FRESH = "";
                cardPaintAges();
                const dimmed = cell.classList.contains("agegone");
                CARD_AGE = "";
                cardPaintAges();
                return {box: cell.dataset.box, kept: kept, dimmed: dimmed};
            }""")
            check(bool(got) and got.get("kept") is True,
                  "the box a write just landed in stays visible under a filter "
                  "that would otherwise hide it", got)
            check(bool(got) and got.get("dimmed") is True,
                  "and the filter goes back to hiding it once the write is old "
                  "news -- so the exemption is a moment, not a hole", got)
            br.close()
    except Exception as exc:                                # noqa: BLE001
        check(False, "a real page draws the fresh box", exc)

    # THE DUPLICATE RULES, AT THE WRITE PATH -- both of them gone.
    #
    # 2026-11-09 removed 「already on this BUILDING」 and kept 「already on this
    # BOX」.  The second one survived one more day: it answered
    # 「第 5 号单位已经在这一格上了」 for a box the panel was drawing EMPTY,
    # because `train_locations` carries every entry of the civilisation,
    # including the ones the era filter is hiding.  Answering with state the
    # player cannot see is worse than the duplicate it prevented -- two entries
    # on one box draw as one button, which is exactly what was asked for.
    try:
        post("/api/session-reset", {})
        base = int(get("/api/session-info").get("bytes") or 0)
        first = post("/api/card-put", {"unit": 74, "building": 12, "box": 5,
                                       "dry": True})
        check(first.get("ok") is True,
              "a unit already on one box of a building goes onto another box "
              "of the same building", first.get("error"))
        again = post("/api/card-put", {"unit": 74, "building": 12, "box": 5,
                                       "dry": False})
        check(again.get("ok") is True,
              "the same unit twice on the SAME box is allowed: the tool no longer "
              "answers with entries the era filter is hiding",
              again.get("error") or again.get("label"))
        for _ in range(int(get("/api/session-info").get("undo") or 0)):
            post("/api/undo", {})
        check(int(get("/api/session-info").get("bytes") or 0) == base,
              "and the one real write above is undone, back to the byte it started at",
              get("/api/session-info").get("bytes"))
    except Exception as exc:                                # noqa: BLE001
        check(False, "the duplicate rule answers at the write path", exc)

    # Clean up: the section wrote a unit into the card, so replay the undo.
    try:
        info = post("/api/session-info", {})
        for _ in range(int(info.get("undo") or 0)):
            post("/api/undo", {})
        got = get("/api/session-info")
        check(int(got.get("pending") or 0) == 0,
              "the writes this suite made are undone", got.get("pending"))
    except Exception as exc:                                # noqa: BLE001
        check(False, "the suite cleans up after itself", exc)

    section("12. buildings are a list of their own, and the last entry can go")
    # Reported 2026-11-10, verbatim: 「怎么建筑放不了，谁告诉你这个不能删的，都
    # 说了编辑所有都可以做，不能有任何限制，除非是引擎无法识别运行」.  Two
    # separate walls hide behind that one sentence.
    #
    # 「建筑放不了」 was never the write path: /api/card-put has always taken a
    # building id, because in this data a building IS a unit record (type 80).
    # What was missing was a way to FIND one -- the card page's dropdown listed
    # only the 48 records some other card already pointed at, so 房屋, 城门 and
    # the tower variants were unreachable from the screen.  Measured on this
    # install: 427 named type-80 records against those 42-48.
    # 「谁告诉你这个不能删」 was a real refusal: card.py raised on the LAST train
    # entry, on the theory that a unit which trains nowhere is not what "take it
    # off the card" means.  The engine reads a zero-entry record fine (the
    # shipped data has 904 of them per civ), so that was the tool's opinion.
    bld = get("/api/browse?kind=building&limit=20000").get("browse") or {}
    bld_ids = {int(r.get("id") or 0) for r in (bld.get("rows") or [])}
    check(int(bld.get("total") or 0) > 400,
          "the building list is the whole .dat, not the list of cards that "
          "happen to exist", bld.get("total"))
    for wid, why in ((70, "房屋, which has no training entry of its own"),
                     (82, "城堡, which was already reachable"),
                     (109, "城镇中心, which only hosts technologies")):
        check(wid in bld_ids, "and it contains " + why, wid)
    check('id="cardpick-bld"' in page,
          "the window has a third tab, so buildings are their own list")
    check('for (const [tabId, kind] of [["unit", "unit"], ["bld", "building"],'
          in page,
          "the tab id and the value the server takes are one table, not a guess")
    check('addBld.id = "card-slot-addbld";' in page
          and 'addBld.onclick = () => cardPickOpenKind(CARD_SLOT, "building");'
              in page,
          "a box that already holds something offers the building list too")
    check('kind === "building") ? "建筑"' in page,
          "and the words follow the list: 建筑, not 单位")
    card = get("/api/card?building=12")
    allb = card.get("all_buildings") or []
    check(len(allb) > 400 and all(("id" in r and "host" in r) for r in allb),
          "the card payload carries every named building, flagged host or not",
          len(allb))
    check(len(card.get("buildings") or []) < len(allb),
          "so the dropdown really can show two groups",
          (len(card.get("buildings") or []), len(allb)))

    # The write itself.  A building goes through /api/card-put, which is the
    # only route that can add a training entry.  Sent to the technology route it
    # would rewrite whichever technology happens to carry that number.
    try:
        post("/api/session-reset", {})
        base = int(get("/api/session-info").get("bytes") or 0)
        put = post("/api/card-put", {"unit": 70, "building": 12, "box": 5,
                                     "dry": True})
        check(put.get("ok") is True,
              "a building goes onto a barracks card as a unit record",
              put.get("error"))
        empty = get("/api/card?building=70")
        check(empty.get("has_data") is False,
              "before: 房屋's own card holds nothing", empty.get("has_data"))
        live = post("/api/card-put", {"unit": 70, "building": 70, "box": 3})
        check(live.get("ok") is True,
              "and a card with nothing on it takes its first entry",
              live.get("error"))
        house = get("/api/card?building=70")
        check(house.get("has_data") is True,
              "after: 房屋's card has content, which is what makes it editable",
              house.get("has_data"))

        # THE LAST ENTRY.  Unit 882 「意大利佣兵」 has exactly one training entry
        # in this data, on barracks box 3, so taking it off empties its table.
        was = get("/api/card?building=12")
        box3 = [b for b in (was.get("boxes") or [])
                if int(b.get("button") or 0) == 3]
        check(bool(box3)
              and [int(u.get("unit") or 0)
                   for u in (box3[0].get("units") or [])] == [882],
              "unit 882 sits alone on barracks box 3", box3)
        here = int(get("/api/session-info").get("bytes") or 0)
        gone = post("/api/card-take", {"unit": 882, "building": 12})
        # The traceback, not just the sentence: when this used to fail the bytes
        # had ALREADY shrunk correctly and only the answer carried an error, so
        # which frame raised it is the whole diagnosis.
        check(gone.get("ok") is True,
              "the LAST training entry comes off, because the engine reads a "
              "zero-entry record",
              (gone.get("error"), (gone.get("where") or "").strip().splitlines()[-3:]))
        check((gone.get("info") or {}).get("count") == 0,
              "and its build table is empty, not quietly repaired behind the "
              "player's back", (gone.get("info") or {}).get("count"))
        # NINE BYTES TIMES SIXTY-THREE.  `train_locations` lives on the UNIT
        # record, and that record is duplicated once per civilization, so an
        # 「全部文明」 take splices the same nine bytes out of 63 separate byte
        # ranges.  Measured 2026-11-12: 93272964 -> 93271720 is -567 = 63 * -9,
        # i.e. this line used to read as a failure only because it still
        # expected the single-civilization figure.
        civs_n = len(get("/api/card?building=12").get("civs") or []) or 63
        check(int(get("/api/session-info").get("bytes") or 0) == here - 9 * civs_n,
              "the record shrank by one nine-byte entry per civilization",
              (here, get("/api/session-info").get("bytes"), civs_n))
        after = get("/api/card?building=12")
        check(not [b for b in (after.get("boxes") or [])
                   if int(b.get("button") or 0) == 3],
              "the box is gone from the card, because nothing is on it")
        for _ in range(int(get("/api/session-info").get("undo") or 0)):
            post("/api/undo", {})
        back = get("/api/card?building=12")
        box3 = [b for b in (back.get("boxes") or [])
                if int(b.get("button") or 0) == 3]
        check(bool(box3)
              and [int(u.get("unit") or 0)
                   for u in (box3[0].get("units") or [])] == [882],
              "one undo puts the last entry back on the same box", box3)
        check(int(get("/api/session-info").get("bytes") or 0) == base,
              "and the file is byte-identical to where the section started",
              get("/api/session-info").get("bytes"))
    except Exception as exc:                                # noqa: BLE001
        check(False, "the building and last-entry paths answer in bytes", exc)
    finally:
        try:
            for _ in range(int(get("/api/session-info").get("undo") or 0)):
                post("/api/undo", {})
        except Exception:                                   # noqa: BLE001
            pass

    # A real page: the tab exists, choosing it lists buildings, and a click
    # lands one in the box that was clicked.
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1360, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/", wait_until="load")
            pg.wait_for_selector("#mods .mod", state="attached", timeout=90000)
            pg.evaluate("showView('card')")
            pg.wait_for_function(
                "() => document.querySelectorAll('#cardgrid .cardslot').length"
                " >= 15", timeout=180000)
            groups = pg.evaluate("""() => {
                const s = document.querySelector("#card-build");
                if (!s) return null;
                return [...s.querySelectorAll("optgroup")].map(
                    g => ({label: g.label, n: g.children.length}));
            }""")
            check(bool(groups) and len(groups) == 2,
                  "the dropdown separates 「卡上有东西的」 from 「卡是空的」",
                  groups)
            box = pg.evaluate("""() => {
                const c = [...document.querySelectorAll("#cardgrid .cardslot")]
                    .find(x => !x.dataset.unit && !x.dataset.tech);
                return c ? Number(c.dataset.box) : null;
            }""")
            check(box is not None, "there is an empty box to write into", box)
            pg.evaluate("""(b) => {
                const c = document.querySelector(
                    '#cardgrid .cardslot[data-box="' + b + '"]');
                if (c) c.click();
            }""", box)
            pg.wait_for_timeout(1200)
            # An empty box selects AND opens the window (2026-11-10: 「你怎么把我
            # 图标窗口给关了」), so by the time the click returns the wall is already
            # up.  Only fall back to the strip's own button if it is not, because
            # that button is behind the window now.
            if not pg.evaluate("() => { const p = document.querySelector('#cardpick');"
                               " return !!(p && p.classList.contains('open')); }"):
                pg.click("#card-slot-add")
                pg.wait_for_timeout(1200)
            pg.click("#cardpick-bld")
            # The footer is painted by the answer of one /api/browse call, and
            # that call is a walk of the building list -- so wait for the text,
            # not for a fixed number of milliseconds (measured 2026-11-11: the
            # 1.5 s this used to sleep was sometimes not enough and the check
            # read an empty footer, which looked like a missing label).
            try:
                pg.wait_for_function(
                    "() => { const s = document.querySelector('#cardpick-seen');"
                    " return !!(s && s.textContent && s.textContent.indexOf('建筑') >= 0); }",
                    timeout=30000)
            except Exception:                                  # noqa: BLE001
                pass
            seen = pg.eval_on_selector("#cardpick-seen", "e => e.textContent")
            check("建筑" in str(seen),
                  "the footer names the list on screen", seen)
            pg.fill("#cardpick-q", "房屋")
            pg.press("#cardpick-q", "Enter")
            pg.wait_for_timeout(2000)
            rows = pg.evaluate("""() => [...document.querySelectorAll(
                '#cardpick-grid .cell')].map(c => ({
                    nm: (c.querySelector(".nm") || {}).textContent,
                    unit: c.dataset.unit || null,
                    tech: c.dataset.tech || null}))""")
            check(bool(rows) and all(r["unit"] and not r["tech"] for r in rows),
                  "a building tile carries a UNIT id, because that is the id "
                  "the write path reads", rows[:3])
            pg.click("#cardpick-grid .cell")
            # A REAL WRITE TAKES 20-31 SECONDS.  It splices nine bytes into 63
            # separate unit records, then re-walks the model.  A fixed 5 s sleep
            # read an empty toast and called the write broken -- measured
            # 2026-11-12, the same click answered 「把「房屋」放进第 5 格了」 24 s
            # later.  So wait for the toast to SAY something, and for the box to
            # carry the id, instead of guessing how long the server needs.
            try:
                pg.wait_for_function(
                    "() => { const t = document.querySelector('#toast');"
                    " return !!(t && /建筑|房屋/.test(t.textContent || '')); }",
                    timeout=180000)
            except Exception:                              # noqa: BLE001
                pass
            toast = pg.evaluate(
                """() => (document.querySelector("#toast") || {}).textContent""")
            check("建筑" in str(toast) or "房屋" in str(toast),
                  "the toast names a building, not a unit", toast)
            # The selector is built HERE, not inside the page: Python glues
            # adjacent string literals together, so '" + b + "' used to be
            # shipped to the browser verbatim and querySelector threw
            # 「not a valid selector」 -- which the except below swallowed, and
            # the box it was watching never got a chance to fill in.
            try:
                pg.wait_for_function(
                    "(sel) => { const c = document.querySelector(sel);"
                    " return !!(c && c.dataset.unit); }",
                    arg='#cardgrid .cardslot[data-box="%d"]' % (box,),
                    timeout=180000)
            except Exception:                              # noqa: BLE001
                pass
            landed = pg.evaluate("""(b) => {
                const c = document.querySelector(
                    '#cardgrid .cardslot[data-box="' + b + '"]');
                return c ? (c.dataset.unit || null) : null;
            }""", box)
            check(landed is not None,
                  "and the box that was clicked is the box that changed",
                  (box, landed))
            check(not errs, "no page errors on the way", errs)
            pg.screenshot(path=os.path.join(SHOTS, "card_pick_building.png"))
            br.close()
    except Exception as exc:                                # noqa: BLE001
        check(False, "a real page offers the building list", exc)
    finally:
        try:
            for _ in range(int(get("/api/session-info").get("undo") or 0)):
                post("/api/undo", {})
        except Exception:                                   # noqa: BLE001
            pass

    print()
    if FAILS:
        print("PICK WINDOW: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("PICK WINDOW: A CLICK ON A BOX IS AN ANSWER -- THE BOX IS SELECTED, THE "
          "STRIP UNDER IT OFFERS 放一个单位进这一格 AND 建伪翻页按钮, THE WINDOW "
          "IT OPENS CARRIES A NAME AND AN ID UNDER EVERY PICTURE, AND A CLICK ON "
          "A PICTURE PLACES THAT RECORD IN THE BOX THAT WAS CLICKED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

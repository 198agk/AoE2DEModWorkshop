# -*- coding: utf-8 -*-
"""Nail: the start-up 防伪声明 window, measured in a real page.

What only a live page can answer, and why each part could be false:

1.  `boot()` really opens it.  A `maybeShowNotice()` that exists but is not
    called passes every source-text assertion there is.  So this probe lets a
    clean profile load and waits for `#notice.open`.

2.  The six sentences are the page's own.  The panel is empty in the markup and
    is filled by copying `#notice-src p` when it opens; if that copy is ever
    replaced by a second hand-written list, the words drift apart and nothing
    crashes.  The probe compares the panel with the section, sentence by
    sentence, and checks the 再看一次 button did not come along.

3.  "Not now" and "not this week" are different decisions.  ×, Esc and 我知得了
    with the box clear must leave `localStorage` alone; only the ticked box
    writes the timestamp.  A single "dismiss" path would silently make every
    close permanent, which is the failure a player reports as
    「它怎么再也不提示了」.

4.  Seven days is rolling.  Measured by moving the stored stamp back eight days
    rather than by waiting a week -- `noticeDue(now)` takes the clock as an
    argument precisely so this is possible.

5.  People get it; an automated browser does not.  `navigator.webdriver` is true
    under Playwright, so every OTHER page probe loads without a modal on top of
    its clicks.  This probe is the one that puts the flag back to false, and it
    is the only place that difference is exercised.

6.  The name is a name.  Reported 2026-11-08: 「我的署名字体加深，窗口标题哪有」.
    Two things at once -- the word inside the sentence should look like a name
    (heavier and darker than the prose around it), and the sentence that says
    「署名见窗口顶部」 needs the header to actually carry it.  The rule asked
    here is a relation (name heavier than its sentence, header lighter than the
    name), never one particular weight: a re-themed page stays green.

Run: BASE=http://127.0.0.1:7811 python -X utf8 _probe/test_notice_modal.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
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


STATE = """() => {
  const n = document.querySelector('#notice');
  const box = n ? n.getBoundingClientRect() : null;
  const lis = [...document.querySelectorAll('#notice-list li')]
    .map(x => (x.textContent || '').trim());
  const st = n ? getComputedStyle(n) : null;
  let stamp = '';
  try { stamp = localStorage.getItem('aoe2mod.notice.dismissed_at') || ''; }
  catch (e) { stamp = 'ERR'; }
  return { open: !!(n && n.classList.contains('open')),
           shown: st ? st.display : '',
           cover: box ? Math.round(box.width * box.height
                                   / (innerWidth * innerHeight) * 100) : 0,
           title: (document.querySelector('#notice-title') || {}).textContent,
           ok: ((document.querySelector('#notice-ok') || {}).textContent || '').trim(),
           items: lis, n: lis.length, stamp: stamp,
           panel: (() => {
             const p = document.querySelector('#notice .npanel');
             return p ? getComputedStyle(p).backgroundColor : '';
           })(),
           primary: (() => {
             const b = document.querySelector('#notice-ok');
             return b ? String(b.className) : '';
           })() };
}"""


# 段9：这个名字是名字，不是名词。玩家 2026-11-08 的原话是「我的署名字体加深，
# 窗口标题哪有」——两件事：声明里那个名字要看起来像名字（比周围重、比周围深），
# 而第一句说「署名见窗口顶部」，顶部就必须真的写着它，否则那句话是假的。
# 钉子问的是**关系**（名字比正文重），不是某个具体的 650：换字号体系也该绿。
CREDIT = """() => {
  const by = document.querySelector('#notice-by');
  const lis = [...document.querySelectorAll('#notice-list li')];
  const first = lis[0] || null;
  const last = lis[lis.length - 1] || null;
  const bold = first ? first.querySelector('b') : null;
  // 正文那一半是第一个 <span>：fillNotice() 把一句话切成 span + b + span。
  const plain = first ? first.querySelector('span') : null;
  const author = document.querySelector('#about-author');
  const w = (e) => e ? parseInt(getComputedStyle(e).fontWeight, 10) : 0;
  return {
    by: by ? (by.textContent || '').trim() : '',
    byWeight: w(by),
    byColor: by ? getComputedStyle(by).color : '',
    boldText: bold ? (bold.textContent || '').trim() : '',
    boldWeight: w(bold),
    boldColor: bold ? getComputedStyle(bold).color : '',
    plainWeight: w(plain),
    firstText: first ? (first.textContent || '').replace(/\\s+/g, ' ').trim() : '',
    lastText: last ? (last.textContent || '').replace(/\\s+/g, ' ').trim() : '',
    authorWeight: w(author)
  };
}"""


def main():
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1360, "height": 1000},
                             device_scale_factor=2)
        # The page hides the notice from an automated browser on purpose; this
        # is the one probe that asks to be treated as a person.
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', "
                            "{get: () => false, configurable: true});")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(BASE + "/#about", wait_until="domcontentloaded")
        pg.wait_for_selector("#notice.open", timeout=180000)
        time.sleep(0.4)
        s = pg.evaluate(STATE)
        check(s["open"] and s["shown"] == "flex",
              "a clean profile gets the notice on boot", s["shown"])
        check(s["cover"] >= 90, "it covers the window it is guarding",
              "%d%% of the viewport" % s["cover"])
        check(s["title"] == "防伪声明", "its title says 防伪声明", s["title"])
        check(s["ok"] == "我知道了", "its button says 我知道了", s["ok"])
        check(s["n"] == 6, "it carries six statements", s["n"])
        # Light panel, like every other surface in this window.  The reference
        # the player sent was dark because that is the other program's theme;
        # borrowing the colour made this window look like something else had
        # opened on top of the tool (reported 2026-11-08).  The rule is
        # brightness, not one particular hex: a re-themed page may change the
        # exact white and stay green here, but it cannot go dark.
        _rgb = [int(x) for x in
                (s["panel"].replace("rgb(", "").replace(")", "").split(",") or [])]
        _mean = sum(_rgb) / float(len(_rgb)) if _rgb else 0
        check(_mean > 200, "the panel is light, not the reference's dark theme",
              "%s (mean %.0f)" % (s["panel"], _mean))
        check("primary" in s["primary"],
              "the one thing to press is the page's primary button", s["primary"])

        # 段9：名字是名字。
        c = pg.evaluate(CREDIT)
        check(c["by"] == "作者 RemonBo",
              "the header names the author, because the first sentence points at it",
              c["by"])
        check(c["byWeight"] < c["boldWeight"],
              "and that header line is lighter than the name in the sentence",
              (c["byWeight"], c["boldWeight"]))
        check(c["boldText"] == "RemonBo", "the name in the sentence is the name",
              c["boldText"])
        check(c["plainWeight"] >= 400 and c["boldWeight"] >= c["plainWeight"] + 150,
              "it is set heavier than the sentence around it",
              (c["boldWeight"], c["plainWeight"]))
        check(c["boldWeight"] == c["authorWeight"],
              "and it reads like the same name on the 关于 page",
              (c["boldWeight"], c["authorWeight"]))
        check("窗口顶部" in c["firstText"],
              "the first sentence still points at the header", c["firstText"])
        check("永远不需要付费" not in c["lastText"],
              "the sponsor line invites first and does not excuse itself",
              c["lastText"])
        check("全凭自愿" in c["lastText"],
              "and says the choice is the reader's", c["lastText"])

        src = pg.eval_on_selector_all(
            "#notice-src p", "els => els.map(e => (e.textContent || '').replace(/\\s+/g, ' ').trim())")
        want = [t for t in src if "再看一次" not in t]
        check(want == s["items"],
              "the panel is a copy of the 关于 section, sentence for sentence",
              "%d vs %d" % (len(want), s["n"]))
        check(all("再看一次" not in t for t in s["items"]),
              "the way back to the window is not one of the statements")
        check(not s["stamp"],
              "opening it writes nothing", s["stamp"])
        pg.screenshot(path=os.path.join(SHOTS, "ed_notice.png"))

        pg.click("#notice-ok")
        time.sleep(0.2)
        s = pg.evaluate(STATE)
        check(not s["open"] and s["shown"] == "none",
              "我知道了 closes it", s["shown"])
        check(not s["stamp"], "closing with the box clear writes nothing", s["stamp"])

        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector("#notice.open", timeout=180000)
        pg.keyboard.press("Escape")
        time.sleep(0.2)
        check(not pg.evaluate(STATE)["open"], "Escape closes it")
        pg.click("#about-notice-again")
        time.sleep(0.2)
        check(pg.evaluate(STATE)["open"], "the 关于 page opens it again")
        pg.click("#notice-x")
        time.sleep(0.2)
        check(not pg.evaluate(STATE)["open"], "the × closes it")
        check(not pg.evaluate(STATE)["stamp"],
              "none of the three wrote a timestamp", pg.evaluate(STATE)["stamp"])

        pg.click("#about-notice-again")
        pg.check("#notice-week")
        pg.click("#notice-ok")
        time.sleep(0.2)
        s = pg.evaluate(STATE)
        check(s["stamp"].isdigit(), "the ticked box writes the timestamp", s["stamp"])

        pg.reload(wait_until="domcontentloaded")
        time.sleep(2.0)
        check(not pg.evaluate(STATE)["open"],
              "a reload inside the week stays quiet", pg.evaluate(STATE)["shown"])

        pg.evaluate("() => localStorage.setItem('aoe2mod.notice.dismissed_at',"
                    " String(Date.now() - 8 * 24 * 60 * 60 * 1000))")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector("#notice.open", timeout=180000)
        check(pg.evaluate(STATE)["open"], "eight days later it is due again")
        pg.click("#notice-x")

        heads = pg.eval_on_selector_all(
            "#view-about .box h2", "els => els.map(e => (e.textContent || '').trim())")
        check(heads == ["关于", "作者", "赞助者", "版权", "可以做什么",
                        "不可以做什么（倒卖与盗版）", "防伪声明", "免责",
                        "操作记录", "版本"],
              "the 关于 page lists ten sections in reading order", heads)
        check("还没有名单" in pg.inner_text("#view-about"),
              "the sponsor section says there is nobody yet")
        pg.screenshot(path=os.path.join(SHOTS, "ed_about_sections.png"),
                      full_page=True)
        check(not errs, "no page errors", errs[:2])
        br.close()

    print()
    if fails:
        for name in fails:
            print("FAILED: %s" % name)
        print("NOTICE MODAL: %d CHECK(S) FAILED" % len(fails))
        return 1
    print("NOTICE MODAL: A DIALOG THAT COMES UP BEFORE THE TOOL OPENS, COPIES "
          "ITS SIX SENTENCES FROM THE ABOUT PAGE INSTEAD OF KEEPING A SECOND "
          "COPY, DISTINGUISHES 'NOT NOW' FROM 'NOT THIS WEEK' BY WRITING A "
          "TIMESTAMP, AND SETS THE AUTHOR'S NAME HEAVIER THAN THE SENTENCE "
          "THAT POINTS AT IT")
    return 0


sys.exit(main())

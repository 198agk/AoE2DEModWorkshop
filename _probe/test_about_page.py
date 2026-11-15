# -*- coding: utf-8 -*-
"""Nail: 关于页 -- ten sections, three addresses, one honest version line, and
the anti-piracy notice that borrows its words from this page.

What is being pinned, and why each part could be false:

1.  「搞个关于页面 / 把法律、侵权、倒卖、盗版等等的都弄一下」 (2026-11-07).  A tool
    that edits a commercial game's data file needs to say, in its own window,
    who made it, what may be done with it, and what it does NOT do.  Every one of
    those sentences is a promise the code cannot enforce, so the page itself is
    the only artifact that can be pinned.

2.  No anchor may navigate the window away.  The desktop shell is a Tauri WebView
    pointed at the local server; there is no address bar and no back button.  An
    `<a href>` to afdian would replace the workshop with a web page the player
    cannot leave.  So the three addresses are PRINTED, and `anchors == 0` is the
    assertion, not a style preference.  They are reachable two ways instead: a
    copy button, and -- since 2026-11-08, 「链接给个可直接打开的功能」 -- an open
    button that posts the address to `/api/open-url` and lets the SERVER hand it
    to the system browser, which leaves this window alone.

3.  The version line quotes THIS run.  A constant baked into the markup is the
    one line a bug report copies, and it is wrong from the second release on.  So
    `drawAbout(meta)` is called from `boot()` with `/api/meta`, and this nail
    proves the wiring by reading the page for the call, not by trusting the text.

4.  Nine sections, and the seventh view.  `VIEWS` feeds both `showView` and the
    nav binding loop; a view added to the markup but not to `VIEWS` is a button
    that jumps to a blank screen.  The count is pinned so a section cannot be
    silently dropped.  It went from seven to nine on 2026-11-08 when 赞助者 and
    防伪声明 were added: the second of those is not decoration, it is the SOURCE
    the start-up notice copies its six sentences from, so a page that dropped it
    would leave the notice with nothing to say (assertion 5b).

5.  The copy has to survive a design gate.  The page is Chinese prose, and the
    project bans the em dash (`——`) in shipped copy; one slipped in during the
    first draft of the age filter, so the wording is pinned here too.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + (("  " + str(detail)) if detail else ""))
    if not ok:
        BAD.append((name, detail))


def _bp_number(page):
    """那条 `max-width` 断点的数。"""
    got = re.search(r"@media \(max-width: (\d+)px\) \{ #view-about", page)
    return int(got.group(1)) if got else 0


def main():
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()

    # --- 1. the seventh view exists and is reachable ----------------------
    views = re.search(r"const VIEWS = \[([^\]]*)\];", page)
    check("there is a VIEWS list to add a seventh view to", bool(views))
    names = re.findall(r'"([a-z]+)"', views.group(1)) if views else []
    check("about is in VIEWS", "about" in names, names)
    # It was the seventh view when it was added; the tree view was inserted
    # earlier in the rail later, so a fixed count would go red for a reason
    # that has nothing to do with this page.  What matters is that it was
    # added rather than swapped in for something else: exactly one entry,
    # and it is the last one, because the rail is read top to bottom.
    check("and it was added rather than swapped in", names.count("about") == 1, names)
    check("and it sits last in the rail", names[-1] == "about", names)
    check("a nav button carries the same id",
          'id="nav-about"' in page)
    check("the button is labelled 关于",
          bool(re.search(r'id="nav-about"[^>]*>\s*(?:<svg[\s\S]{0,400}?</svg>)?\s*关于\s*</button>',
                         page)))
    check("the view section exists",
          bool(re.search(r'<section class="view" id="view-about">', page)))
    # The nav binding loop reads VIEWS, so a missing entry is a dead button --
    # and a section without the class would never be hidden by showView.
    check("the nav loop still reads VIEWS, so no second list to update",
          'for (const v of VIEWS)' in page and '$("#nav-" + v)' in page,
          '$("#nav-" + v)' in page)

    # --- 2. seven sections ------------------------------------------------
    block = page.split('<section class="view" id="view-about">', 1)
    check("the about view is a real section, not a stub", len(block) == 2)
    body = block[1].split("</section>", 1)[0] if len(block) == 2 else ""
    heads = re.findall(r"<h2[^>]*>([^<]+)</h2>", body)
    print("     heads: %s" % heads)
    # Ten since 2026-11-09: 操作记录 joined between 免责 and 版本, because a
    # log is something a reader goes looking for while a version line is the last
    # thing they read.  The order is pinned, not just the count.
    check("it has ten sections", len(heads) == 10, heads)
    for want in ["关于", "作者", "赞助者", "版权", "可以做什么",
                 "不可以做什么（倒卖与盗版）", "防伪声明", "免责",
                 "操作记录", "版本"]:
        check("section %r is there" % want, want in heads, heads)
    check("the order is the order the reader needs",
          heads == ["关于", "作者", "赞助者", "版权", "可以做什么",
                    "不可以做什么（倒卖与盗版）", "防伪声明", "免责",
                    "操作记录", "版本"],
          heads)

    # --- 3. the promises --------------------------------------------------
    for word, why in [("倒卖", "resale"), ("盗版", "piracy"), ("侵权", "infringement"),
                      ("版权", "copyright"), ("免责", "disclaimer"),
                      ("Microsoft", "the trademark owner"),
                      ("不包含、不分发", "it does not ship the game"),
                      ("不提供、不索取、不校验游戏本体", "it does not crack the game"),
                      ("RemonBo", "the author")]:
        check("the page says something about %s" % why, word in body, word)
    check("it forbids selling the tool itself", "不可以卖这个工具" in body)
    check("it forbids re-signing somebody else's mod", "不可以把别人的模组改成自己的" in body)
    check("it says the tool does not hand over the game", "不提供、不索取、不校验游戏本体" in body)
    check("and that piracy in the player's hands is their own problem",
          "盗版副本出的任何问题" in body)
    check("no em dash reaches the shipped copy", "\u2014" not in body,
          body.count("\u2014"))

    # --- 4. no anchor can take the window away ----------------------------
    hrefs = re.findall(r"<a\b[^>]*>", body)
    check("no anchor in the about view", not hrefs, hrefs)
    check("no anchor anywhere on the page navigates out",
          not re.search(r'<a\s[^>]*href="https?://', page))

    # --- 5. the three addresses, printed and copied -----------------------
    for url, label in [("https://afdian.com/a/RemonBo", "afdian"),
                       ("https://space.bilibili.com/6978282", "bilibili"),
                       ("https://github.com/198agk", "github")]:
        check("the %s address is on the page" % label, url in body, url)
    for btn in ["about-copy-fan", "about-copy-bili", "about-copy-gh"]:
        check("there is a copy button %s" % btn, 'id="%s"' % btn in body)
    for btn in ["about-open-fan", "about-open-bili", "about-open-gh"]:
        check("there is an open button %s" % btn, 'id="%s"' % btn in body)
    # Both buttons on the same row: a copy you have to find on another screen is
    # the same problem as no copy at all.
    for kind, url in [("fan", "https://afdian.com/a/RemonBo"),
                      ("bili", "https://space.bilibili.com/6978282"),
                      ("gh", "https://github.com/198agk")]:
        row = re.search(r'<span class="abv" id="about-%s-url">([^<]*)</span>(.{0,240}?)</div>'
                        % kind, body, re.S)
        check("the %s row carries a copy and an open button" % kind,
              row is not None
              and 'id="about-copy-%s"' % kind in row.group(2)
              and 'id="about-open-%s"' % kind in row.group(2),
              (row.group(2)[:90] if row else None))
    # Opening must not be `window.open`: in a WebView it either does nothing or
    # takes the workshop's own window.
    check("opening posts the address to the server, not window.open(",
          'api("/api/open-url", {url})' in page and "window.open(" not in page)
    check("the open helper is a named function, so a harness can call it",
          re.search(r"async function aboutOpen\(url\)", page) is not None)
    check("...and says what happened either way",
          "已经在浏览器里打开" in page and "打不开这个地址" in page)
    check("one table drives every copy button",
          re.search(r"const ABOUT_LINKS = \[[\s\S]{0,400}?afdian\.com/a/RemonBo", page)
          is not None)
    check("copying falls back when the clipboard API says no",
          "navigator.clipboard" in page and 'document.execCommand("copy")' in page)
    check("...and the failure says what to do instead",
          "复制不了" in page and "手动选中" in page)

    # The two buttons on a link row wrap as ONE group.  Measured 2026-11-09 at
    # 1360px: row 478px, address 292px, so "复制链接" sat on the first line at
    # x=396 and "浏览器打开" fell to the second at x=0 -- one button right of the
    # address and one far left, which reads as two unrelated rows.  A plain pair
    # of siblings cannot be pinned: the flex algorithm is free to split them.
    check("both buttons of a row live in one group",
          re.search(r"\.abact \{ flex: none; display: flex; gap: 8px; "
                    r"margin-left: auto; \}", page) is not None)
    for kind in ("fan", "bili", "gh"):
        block = re.search(r'<span class="abact">\s*'
                          r'<button class="chip" id="about-copy-%s">[^<]*</button>\s*'
                          r'<button class="chip" id="about-open-%s">[^<]*</button>\s*'
                          r'</span>' % (kind, kind), body)
        check("the %s row keeps its two buttons in that group" % kind,
              block is not None)
    check("the log row groups its two buttons too",
          re.search(r'<span class="abact">\s*'
                    r'<button class="chip" id="log-open">[^<]*</button>\s*'
                    r'<button class="chip" id="log-refresh">[^<]*</button>\s*'
                    r'</span>', body) is not None)

    # --- 6. the version line quotes this run ------------------------------
    check("drawAbout takes the meta object",
          re.search(r"function drawAbout\(meta\)", page) is not None)
    boot = page.split("async function boot(", 1)
    tail = boot[1] if len(boot) == 2 else ""
    check("boot fills it", "drawAbout(META);" in tail,
          "drawAbout(META);" in tail)
    check("...after the mods are drawn, so a failure there cannot blank it",
          tail.index("renderMods(META.mods);") < tail.index("drawAbout(META);")
          if "drawAbout(META);" in tail and "renderMods(META.mods);" in tail else False)
    check("the version line names the author", "，作者 RemonBo。" in page, "")
    # 「版本应该是指模组工坊的版本，写个 ver1.0」 (2026-11-08).  The card used to
    # print only the .dat's format ordinal, so a page about the TOOL carried no
    # version of the tool.  Two lines now, and both are filled from the run:
    # `app_version` from `aoe2mod/appversion.py`, the rest from `/api/meta`.
    check("the version line prints the tool's own version",
          'm.app_version ? ("ver " + m.app_version)' in page, "")
    check("...in the form the player asked for",
          re.search(r'"ver " \+ m\.app_version', page) is not None, "")
    check("and the format line is a line of its own",
          'id="about-read"' in body, "")
    check("the format line quotes what this run read, not a constant",
          "这次读到的数据格式是" in page and "文明" in page)
    check("the tool's version is not written into the markup",
          not re.search(r">\s*ver 1\.0", body), "")
    check("the server reports it from one constant",
          'import appversion as AV' in io.open(
              os.path.join(ROOT, "aoe2mod", "ui", "server.py"), encoding="utf-8").read(), "")
    check("the bundle manifest agrees with that constant",
          __import__("json").load(io.open(
              os.path.join(ROOT, "desktop", "src-tauri", "tauri.conf.json"),
              encoding="utf-8"))["version"].startswith(
                  __import__("aoe2mod.appversion", fromlist=["VERSION"]).VERSION), "")
    # 「截图这个删掉」 (2026-11-08, m18360/m18362): the second line of the
    # version card explained that the number above it was read at run time.  That
    # is a note to the author, printed on the player's screen.
    check("the「这次运行真正读到的」sentence is gone",
          "这次运行真正读到的" not in page)
    check("and the dead span went with it", "about-datver" not in page,
          re.search(r'id="about-datver"', body) is not None)
    check("the bug-report hint asks for a picture instead of three things",
          "截图或录屏" in page and "三样东西" not in page)
    check("there is a placeholder before boot answers, so it is never blank",
          re.search(r'id="about-version"[^>]*>\s*[^<\s]', body) is not None,
          re.search(r'id="about-version"[^>]*>([^<]{0,40})', body).group(1)
          if re.search(r'id="about-version"[^>]*>([^<]{0,40})', body) else None)

    # --- 5b. the start-up notice -----------------------------------------
    # 「再写一个这样的窗口」 (2026-11-08).  Two things can go wrong here and neither
    # shows up as a crash: the window can never open (a `maybeShowNotice()` that
    # boot does not call), and the six sentences can be a SECOND copy that drifts
    # from the page.  So: the panel exists, boot calls it last, the words are
    # copied out of `#notice-src`, and the three ways out are three different
    # decisions.
    check("the notice panel is a real dialog in the markup",
          re.search(r'id="notice"[^>]*role="dialog"', page) is not None
          and 'aria-modal="true"' in page)
    check("it carries a title, a list, a weekly box and one button",
          all(('id="%s"' % k) in page
              for k in ("notice-title", "notice-list", "notice-week", "notice-ok")))
    check("boot opens it, after the about page was drawn",
          page.index("drawAbout(META);") < page.index("maybeShowNotice();"),
          "drawAbout at %d, notice at %d"
          % (page.index("drawAbout(META);"), page.index("maybeShowNotice();")))
    check("the words are copied out of the 关于 section, not written twice",
          'id="notice-src"' in page
          and 'querySelectorAll("#notice-src p")' in page,
          page.count("如果你是花钱买到的"))
    check("so the sentence exists exactly once in the page",
          page.count("如果你是花钱买到的") == 1,
          page.count("如果你是花钱买到的"))
    check("the six statements are six paragraphs on the page",
          len(re.findall(r"<p>", body.split('id="notice-src"', 1)[1]
                         .split("</div>", 1)[0])) == 7,
          "six statements plus the way back to the window")
    check("a week is seven rolling days, not a calendar week",
          "7 * 24 * 60 * 60 * 1000" in page)
    check("dismissing with the box ticked is what writes the timestamp",
          re.search(r"hideNotice\(!!\(week && week\.checked\)\)", page)
          is not None)
    check("closing without the box does not write it",
          "hideNotice(false)" in page)
    check("Escape closes it", 'ev.key !== "Escape"' in page)
    check("the about page can open it again",
          'id="about-notice-again"' in page
          and 'onclick = () => showNotice()' in page)
    check("every touch of localStorage is guarded for the harness",
          "typeof localStorage" in page
          and page.count("typeof localStorage") >= 2)
    check("people get the notice and an automated browser does not",
          "function noticeForPeople()" in page
          and "navigator.webdriver" in page
          and "if (noticeForPeople() && noticeDue()) showNotice();" in page)
    check("the panel is a modal, not a toast",
          re.search(r"#notice \{[^}]*position:\s*fixed", page) is not None
          and re.search(r"#notice\.open \{[^}]*display:\s*flex", page) is not None)

    # --- 7. styling that the design gate already constrains ---------------
    # The prose column is capped by the existing measure token.  The first draft
    # of this assertion wrote `max-width:var(--measure)` with no leading space and
    # failed on `var(--measure)` spelled `max-width: var(--measure)` -- the gate
    # accepts either, so the nail must too.
    check("the prose rows use the measure token, not a new width",
          "--measure" in page
          and re.search(r"\.ablist p \{[^}]*max-width:\s*var\(--measure\)", page)
          is not None)
    check("the value column can break a long URL",
          re.search(r"\.abv \{[^}]*word-break:\s*break-all", page) is not None)
    check("no new font size was invented for this page",
          not re.search(r"\.ab[a-z]+ \{[^}]*font-size:\s*\d", page))

    # -----------------------------------------------------------------------
    # 排版：一页说明文字写成两栏（2026-11-08，玩家「你右边空那么多空白干什么」）
    # -----------------------------------------------------------------------
    # 九张卡各占满整列、每张里的段落被 `--measure`（62ch）限在 509px，右边
    # 547px 是空的。两栏之后那段被 `\u5b89\u6392` 吃掉了，但栏是 grid 时每行
    # 高的卡决定行高，矮卡底下留 252px 的空 —— 所以用 column-count 按栏平衡。
    check("the about page sets its cards in columns, not one per row",
          re.search(r"#view-about\.on \{[^}]*column-count:\s*2", page) is not None)
    check("a card is never split across the two columns",
          re.search(r"#view-about\.on > \.box \{[^}]*break-inside:\s*avoid", page)
          is not None)
    check("the cards keep the page's spacing between them",
          re.search(r"#view-about\.on > \.box \{[^}]*margin:\s*0 0 16px", page) is not None)
    check("the gap is the same 16px the rest of the page uses",
          re.search(r"#view-about\.on \{[^}]*column-gap:\s*16px", page) is not None)
    check("a narrow window goes back to one column",
          re.search(r"@media \(max-width: 760px\) \{ #view-about\.on \{ column-count: 1",
                    page) is not None)
    check("and that breakpoint is not set so wide it undoes the columns at 1000px",
          _bp_number(page) < 800)

    print()
    if BAD:
        for name, detail in BAD:
            print("FAILED: %s :: %s" % (name, detail))
        print("ABOUT PAGE: %d CHECK(S) FAILED" % len(BAD))
        return 1
    print("ABOUT PAGE: A SEVENTH VIEW, TEN SECTIONS, THREE ADDRESSES THAT CANNOT "
          "NAVIGATE THE WINDOW AWAY BUT CAN BE COPIED OR HANDED TO THE SYSTEM "
          "BROWSER, ONE VERSION LINE THAT QUOTES THIS RUN, AND A START-UP NOTICE "
          "THAT BORROWS ITS SIX SENTENCES FROM THIS PAGE INSTEAD OF KEEPING A "
          "SECOND COPY THAT WOULD DRIFT")
    return 0


sys.exit(main())

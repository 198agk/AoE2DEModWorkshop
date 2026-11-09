# -*- coding: utf-8 -*-
"""防伪声明窗里那张图：窗口右半边从第一版起就没人占过。

玩家 2026-11-08 先指着一张插画说「右边那么大一片空白，要不你放个这张图片上去」，
我把图放进了「关于」卡；他又说「我说的是图片放这个窗口这里」，并把启动时的
防伪声明窗截图圈出右边那块空白。于是图从关于页搬进这扇窗，关于页还原。

量出来的事实：窗里的六条声明受 `--measure`（62ch）限制，每条只有 509px 宽，
而面板比这宽得多，右边那半张一直是空的。

这条钉子钉五件事：
  1. 图真的在仓库里，而且服务端按 image/jpeg 送，不是当页面送走；
  2. 标记：`<figure class="nfig">` 在 `#notice .nbody` 里、在六条之后、
     `src` 指向静态路由、`alt` 非空、`width`/`height` 与真图一致
     （不一致的 width/height 会让浏览器在图片到达前按错的框排版）；
  3. 样式：面板 `min(900px, 100%)`、正文行 `flex-wrap: wrap`、六条 `flex: 1 1 320px`、
     图 `margin: 0 0 0 auto`、图宽 240 且 `max-width: 100%`、用既有圆角与发丝线、
     不引入新字号；
  4. 关于页确实还原了：没有 `.abfig`、没有 `.abhero`，关于卡又只是一段 `.hint`；
  5. 真页面：三档窗口下窗口自己打开、图解码出来、宽度是 240、右沿对齐内容盒的
     右沿、每条声明仍只有 509px、宽窗口下与六条并排、窄窗口下不掉出面板。

第 5 段要跑浏览器；服务没起就报「服务没起」，不假装通过。
"""
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
IMG = os.path.join(ROOT, "aoe2mod", "ui", "static", "art", "preview-girl.jpg")
BASE = os.environ.get("AOE2MOD_BASE", "http://127.0.0.1:7811")

FAILED = []


def check(ok, what, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what, (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)


def section(name):
    print("=== %s" % name)


def jpeg_size(path):
    from struct import unpack
    raw = io.open(path, "rb").read()
    i = 2
    while i < len(raw) - 9:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        seglen = unpack(">H", raw[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            return (unpack(">H", raw[i + 7:i + 9])[0],
                    unpack(">H", raw[i + 5:i + 7])[0])
        i += 2 + seglen
    return None


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"), encoding="utf-8").read()

    section("1. the picture is a file, and the server knows how to send it")
    check(os.path.isfile(IMG), "the picture is in the tree", IMG)
    size = os.path.getsize(IMG) if os.path.isfile(IMG) else 0
    check(20000 < size < 400000, "and it is a picture, not a stub", "%d bytes" % size)
    head = io.open(IMG, "rb").read(3) if size else b""
    check(head == b"\xff\xd8\xff", "and it is a JPEG the browser will decode", head)
    ctypes = re.search(r"_CTYPES\s*=\s*\{(.*?)\}", server, re.S)
    check(bool(ctypes), "the static route has a type table", "")
    if ctypes:
        check('".jpg": "image/jpeg"' in ctypes.group(1),
              "which already names jpg", ctypes.group(1).count("jpg"))

    section("2. the markup: the figure is inside the window, after the six lines")
    body = re.search(r'<div class="nbody">(.*?)\n    </div>', page, re.S)
    check(bool(body), "the window has a body row", "")
    block = body.group(1) if body else ""
    check('id="notice-list"' in block, "the six statements are in that row", "")
    fig = re.search(r'<figure class="nfig">(.*?)</figure>', block, re.S)
    check(bool(fig), "and so is a figure", "")
    figblock = fig.group(1) if fig else ""
    check('src="/static/art/preview-girl.jpg"' in figblock,
          "pointing at the shipped file, through the static route", "")
    m = re.search(r'alt="([^"]*)"', figblock)
    check(bool(m) and len(m.group(1)) >= 8,
          "with a description a screen reader can read", m.group(1) if m else "")
    wh = re.search(r'width="(\d+)"\s+height="(\d+)"', figblock)
    check(bool(wh), "and intrinsic sizes", wh.group(0) if wh else "")
    if wh and os.path.isfile(IMG):
        real = jpeg_size(IMG)
        check(real == (int(wh.group(1)), int(wh.group(2))),
              "and those numbers are the file's own", "%s vs %s" % (real, wh.groups()))
    if block and fig:
        check(block.index('id="notice-list"') < block.index('<figure class="nfig">'),
              "the statements come first in the source, so a reader hears them first", "")

    section("3. the stylesheet gives the picture the room the words do not use")
    panel = re.search(r"#notice \.npanel \{(.*?)\}", page, re.S)
    check(bool(panel) and "min(900px, 100%)" in (panel.group(1) if panel else ""),
          "the panel is wide enough for a 509px measure and a 240px picture",
          (panel.group(1) if panel else "").replace("\n", " ")[:110])
    bodycss = re.search(r"#notice \.nbody \{(.*?)\}", page, re.S)
    bbody = bodycss.group(1) if bodycss else ""
    check(bool(bodycss), "the body row is a rule of its own", "")
    check("display: flex" in bbody, "laid out as a row", bbody.replace("\n", " ")[:100])
    check("flex-wrap: wrap" in bbody,
          "that wraps instead of squeezing the statements", "")
    check("gap: 16px" in bbody, "with a gap on the scale", "")
    listcss = re.search(r"#notice \.nlist \{([^}]*)\}", page)
    lb = listcss.group(1) if listcss else ""
    check("flex: 1 1 320px" in lb,
          "the statements take the room they can and no more", lb)
    check("min-width: 0" in lb, "and are allowed to shrink", "")
    figcss = re.search(r"#notice \.nfig \{([^}]*)\}", page)
    check(bool(figcss) and "margin: 0 0 0 auto" in figcss.group(1),
          "the picture is pushed to the right edge", figcss.group(1) if figcss else "")
    imgcss = re.search(r"#notice \.nfig img \{(.*?)\}", page, re.S)
    ibody = imgcss.group(1) if imgcss else ""
    check("width: 240px" in ibody, "the picture is 240 wide", "")
    check("max-width: 100%" in ibody, "and never wider than the window", "")
    check("border-radius: var(--r-surface)" in ibody,
          "a corner radius this page already owns", "")
    check("border: 1px solid var(--line)" in ibody,
          "and a hairline, like everything else", "")
    check("font-size" not in ibody, "no new type size for a picture", "")

    section("4. the about page went back to what it was")
    check('class="abfig"' not in page, "the about card carries no figure now", "")
    check('class="abhero"' not in page, "and no row wrapper either", "")
    check(".abfig" not in page, "nor any style left behind for it", "")
    check(".abhero" not in page, "nor for its row", "")
    about = re.search(r'<section class="view" id="view-about">(.*?)</section>', page, re.S)
    first = about.group(1) if about else ""
    check('<h2>关于</h2>' in first, "the about card is still there", "")
    check(re.search(r'<h2>关于</h2>\s*<div class="hint">', first) is not None,
          "and it is a plain paragraph again", "")

    section("5. the real page")
    try:
        got = json.loads(urllib.request.urlopen(BASE + "/api/meta", timeout=60).read().decode("utf-8"))
        check(bool(got.get("ok")), "the service answers", "")
    except Exception as exc:  # noqa: BLE001
        check(False, "the service answers", repr(exc)[:90])
        print("NOTICE: start tools/run_ui.py --port 7811 --serve-only first")
        return report()
    try:
        req = urllib.request.urlopen(BASE + "/static/art/preview-girl.jpg", timeout=60)
        raw = req.read()
        check(req.status == 200 and len(raw) == size,
              "the picture comes back whole over the route",
              "%s %d" % (req.status, len(raw)))
        check(req.headers.get("Content-Type", "").startswith("image/"),
              "typed as an image, not as a page", req.headers.get("Content-Type"))
    except Exception as exc:  # noqa: BLE001
        check(False, "the picture comes back whole over the route", repr(exc)[:90])

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        check(False, "playwright is installed", repr(exc)[:90])
        return report()

    with sync_playwright() as p:
        br = p.chromium.launch()
        for w, h in ((1160, 704), (1360, 1000), (900, 900)):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
            # 窗口只挡人：探针必须把 webdriver 改回 false 才看得见它；
            # 同时清掉「本周不再提示」，否则上一档装过的会话会把它藏起来。
            ctx.add_init_script(
                "try { localStorage.removeItem('aoe2mod.notice.dismissed_at'); } catch (e) {}\n"
                "Object.defineProperty(navigator, 'webdriver', {get: () => false,"
                " configurable: true});")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/", wait_until="domcontentloaded")
            pg.wait_for_selector("#notice.open", timeout=180000)
            pg.wait_for_function(
                "() => { const i = document.querySelector('#notice .nfig img');"
                " return !!i && i.complete && i.naturalWidth > 0; }", timeout=60000)
            s = pg.evaluate("""() => {
              const panel = document.querySelector('#notice .npanel');
              const body = document.querySelector('#notice .nbody');
              const list = document.querySelector('#notice-list');
              const fig = document.querySelector('#notice .nfig');
              const img = fig.querySelector('img');
              const pr = panel.getBoundingClientRect(), brr = body.getBoundingClientRect();
              const lr = list.getBoundingClientRect(), fr = fig.getBoundingClientRect();
              const ir = img.getBoundingClientRect();
              const last = list.lastElementChild.getBoundingClientRect();
              return {
                items: document.querySelectorAll('#notice-list li').length,
                natural: [img.naturalWidth, img.naturalHeight],
                drawn: [Math.round(ir.width), Math.round(ir.height)],
                panel: Math.round(pr.width),
                listW: Math.round(lr.width), figW: Math.round(fr.width),
                liW: Math.round(last.width),
                sameRow: Math.abs(Math.round(fr.top) - Math.round(lr.top)) <= 4,
                figRight: Math.round(fr.right),
                bodyRight: Math.round(brr.right),
                bodyPadR: Math.round(parseFloat(getComputedStyle(body).paddingRight) || 0),
                overflow: Math.round(fr.bottom) > Math.round(brr.bottom) + 1,
                alt: img.getAttribute('alt') || ''
              };
            }""")
            print("  %dx%d %s" % (w, h, s))
            check(s["items"] == 6, "%dpx: the six statements are still there" % w, s["items"])
            check(s["natural"] == [895, 670], "%dpx: the browser decoded the file" % w, s["natural"])
            check(s["drawn"][0] == 240, "%dpx: drawn at the width the sheet asks for" % w, s["drawn"])
            # body 的 rect 含内边距，图的右沿对齐的是内容盒的右沿。
            edge = s["bodyRight"] - s["bodyPadR"]
            check(abs(s["figRight"] - edge) <= 1,
                  "%dpx: it ends where the window's content ends" % w, (s["figRight"], edge))
            # 判据是「每条声明自己的宽度」，不是容器：容器按 flex 分到 602，
            # 真正的行宽上限写在 li 的 max-width 上。
            check(s["liW"] <= 540, "%dpx: every statement keeps its measure" % w, s["liW"])
            if w >= 1100:
                check(s["sameRow"] and s["figW"] == 240,
                      "%dpx: the picture sits beside the statements, not under them" % w,
                      (s["listW"], s["figW"]))
            check(not s["overflow"], "%dpx: the picture stays inside the body" % w, s["overflow"])
            check("插画" in s["alt"], "%dpx: the picture carries a description" % w, s["alt"])
            check(not errs, "%dpx: no page errors" % w, errs[:2])
            ctx.close()
        br.close()
    return report()


def report():
    if FAILED:
        print("NOTICE FIGURE: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("NOTICE FIGURE: THE HALF OF THE START-UP WINDOW THAT NOBODY USED NOW HOLDS ONE "
          "PICTURE -- SHIPPED AS A FILE THE ROUTE SERVES TYPED AS AN IMAGE, SIZED BY THE "
          "STYLESHEET RATHER THAN THE SOURCE PIXELS, BESIDE THE SIX LINES WHERE THERE IS "
          "ROOM AND UNDER THEM WHERE THERE IS NOT, WHILE THE ABOUT PAGE WENT BACK TO PLAIN "
          "TEXT")
    return 0


if __name__ == "__main__":
    sys.exit(main())

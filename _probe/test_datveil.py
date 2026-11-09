# -*- coding: utf-8 -*-
"""换数据文件时那层遮罩：真浏览器里量，不猜。

玩家 2026-11-08 的原话是「点了之后我也不知道是不是在加载，要等一段时间，
但这段时间我切别的页面又做什么的，这很容易出问题」。那两句话各是一种失败：
一条不动的界面让人以为没反应，一条能点的界面让人在重建途中把页面切走。

这条探针量两条路，因为这台机器上真实存在两条：

  慢的那条（第一次打开某个 .dat）：解析 9-22 秒。这时候必须有窗、必须有真
    百分比、必须锁住页面，否则玩家会以为程序死了。
  快的那条（这个 .dat 在本进程里已经打开过，或 parse_cache 命中）：0.4-0.5 秒。
    这时候**不该**有窗。一扇一闪而过、写着 100% 的全屏面板比不弹更糟。

所以遮罩的设计是「锁立刻上、画晚 600 ms」：`DATVEIL_ON` 在同一行置真，
`#datveil.open` 由 `DATVEIL_SHOW_MS = 600` 的定时器加上。快路径在面板出现
之前就收工，玩家看到的是一次干脆的切换。

用法
    python -X utf8 _probe/test_datveil.py
    python -X utf8 _probe/test_datveil.py --slow "WAIFor Arcade"
"""
import argparse
import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"
GAME = "empires2_x2_p1.dat"
SHOW_MS = 600     # must match DATVEIL_SHOW_MS in index.html

FAILED = []


def check(ok, what, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what,
                         (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)


def section(name):
    print("=== %s" % name)


# Everything the probe asks the page, in one shot: the veil, the picker, the
# view.  Reading them together is the point -- the veil and the view are the
# same question ("is the page locked?") from two sides.
STATE = """() => {
  const dv = document.getElementById('datveil');
  const sel = document.getElementById('ed-dat');
  const fill = document.getElementById('datveil-fill');
  const pct = document.getElementById('datveil-pct');
  const note = document.getElementById('datveil-note');
  const on = document.querySelector('.view.on');
  return {
    veil: !!dv,
    open: !!(dv && dv.classList.contains('open')),
    openDisplay: dv ? getComputedStyle(dv).display : '',
    openZ: dv ? getComputedStyle(dv).zIndex : '',
    fillW: fill ? (fill.style.width || '') : '',
    pct: pct ? (pct.textContent || '') : '',
    note: note ? (note.textContent || '') : '',
    what: (document.getElementById('datveil-what') || {}).textContent || '',
    selValue: sel ? sel.value : '',
    selDisabled: sel ? !!sel.disabled : null,
    view: on ? on.id : '',
    hash: location.hash,
    flag: (typeof DATVEIL_ON === 'undefined') ? 'undefined' : DATVEIL_ON,
    timer: (typeof DATVEIL_TIMER === 'undefined') ? -1 : DATVEIL_TIMER,
    show: (typeof DATVEIL_SHOW === 'undefined') ? -1 : DATVEIL_SHOW,
  };
}"""


def wait_ready(pg, timeout=180000):
    pg.wait_for_function(
        "() => document.readyState === 'complete'"
        " && typeof DATVEIL_ON !== 'undefined'", timeout=timeout)


def wait_open(pg, timeout=4000):
    pg.wait_for_function(
        "() => { const d = document.getElementById('datveil');"
        " return !!d && d.classList.contains('open'); }", timeout=timeout)


def click_chip(pg, label):
    """Click the 「改这一份」 chip whose row is for `label`."""
    return pg.evaluate(
        """(label) => {
             const rows = [...document.querySelectorAll('#dp-list .dprow')];
             const row = rows.find(r => r.querySelector('.dplabel')
               && r.querySelector('.dplabel').textContent.indexOf(label) >= 0);
             if (!row) return {ok: false, why: 'row not found', rows: rows.length};
             const chip = [...row.querySelectorAll('button')]
               .find(b => b.textContent.trim() === '改这一份');
             if (!chip) return {ok: false, why: 'no chip'};
             chip.click();
             return {ok: true, scope: (row.querySelector('.dpscope') || {}).textContent || ''};
           }""", label)


def track(pg, limit_s=90.0):
    """Follow one switch from click to clean-up, keeping every frame that said
    something new.  `ever_open` answers the flash question: 100 ms sampling is
    quick enough to catch a panel that lives for the whole slow path."""
    seen = []
    ever_open = False
    t0 = time.time()
    while time.time() - t0 < limit_s:
        st = pg.evaluate(STATE)
        if st["open"]:
            ever_open = True
        pair = (st["fillW"], st["pct"])
        if not seen or seen[-1][0] != pair:
            seen.append((pair, round(time.time() - t0, 2)))
        if not st["flag"] and time.time() - t0 > 0.25:
            return st, seen, round(time.time() - t0, 2), ever_open
        time.sleep(0.1)
    return pg.evaluate(STATE), seen, round(time.time() - t0, 2), ever_open


def nums(widths):
    out = []
    for w in widths:
        try:
            out.append(float(str(w).replace("%", "")))
        except (TypeError, ValueError):
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slow", default="WAIFor Arcade",
                    help="a row this server process has NOT opened yet (slow path)")
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1237, "height": 880})
        # `setDat` asks `window.confirm` when the editor holds unsaved edits and
        # Playwright DISMISSES dialogs by default.  A dismissed confirm is the
        # "no" branch: the picker snaps back and the switch never starts, which
        # reads in the log exactly like a broken veil.  Answer as the player
        # would.  Whether there are pending edits depends on what earlier runs
        # left behind, so this has to be unconditional.
        pg.on("dialog", lambda d: d.accept())
        pg.goto(a.url, wait_until="domcontentloaded")
        wait_ready(pg)

        section("0. 起点")
        src = pg.evaluate("() => (window.DAT_SOURCES || []).map(x => ({label: x.label,"
                          " scope: x.scope, path: x.path, current: !!x.current}))")
        if not src:
            pg.evaluate("() => loadDatSources()")
            pg.wait_for_timeout(800)
            src = pg.evaluate("() => DAT_SOURCES.map(x => ({label: x.label,"
                              " scope: x.scope, path: x.path, current: !!x.current}))")
        check(bool(src), "页面拿到了候选文件清单", "%d 个" % len(src or []))
        base = [x for x in (src or []) if x["current"]]
        check(len(base) == 1, "当前改的只有一份", base[0]["label"] if base else None)
        base_path = base[0]["path"] if base else ""
        tgt = [x for x in (src or []) if a.slow in x["label"]]
        check(bool(tgt), "找得到慢路径那一份", a.slow)
        if not tgt:
            b.close()
            sys.exit(1)
        tgt = tgt[0]
        check(tgt["path"].lower().endswith(GAME), "它也有一份 .dat", tgt["path"])

        st = pg.evaluate(STATE)
        check(st["veil"], "#datveil 在页面上")
        check(st["open"] is False, "此刻是关着的")
        check(st["openDisplay"] == "none", "关着时 display 是 none", st["openDisplay"])
        check(st["openZ"] == "90", "z-index 90（盖住 #notice 的 80 / #toast 的 60）",
              st["openZ"])
        pend = pg.evaluate("() => (typeof ED_PENDING === 'undefined') ? null : ED_PENDING")
        print("     编辑器里未保存的改动：%s（有的话切换前会问一句，探针按「继续」答）"
              % pend)

        # ---------------------------------------------------------------- slow
        section("1. 慢路径：第一次打开这一份")
        pg.evaluate("() => showView('mods')")
        # `/api/dat-sources` measures the version head of every candidate (0.2 to
        # 0.5 s each, nineteen here) and the cold-server first call is the slow
        # one.  Clicking before the rows exist is a probe bug that looks exactly
        # like the feature being broken, so wait for the rows themselves.
        try:
            pg.wait_for_function(
                "() => document.querySelectorAll('#dp-list .dprow').length > 0",
                timeout=180000)
        except Exception as exc:                       # noqa: BLE001
            check(False, "#dp-list 画出了候选行", str(exc)[:120])
        pg.wait_for_timeout(200)
        t_click = time.time()
        r = click_chip(pg, a.slow)
        check(r.get("ok"), "点到了那一行上的「改这一份」", r)
        st0 = pg.evaluate(STATE)
        check(st0["flag"] is True, "锁在点击的同一 tick 就上了", st0["flag"])
        check(st0["selDisabled"] is True, "下拉框同时被禁用")
        check(st0["what"] == a.slow,
              "标题旁写的是人话标签，不是所有候选都一样的文件名", st0["what"])

        try:
            wait_open(pg, timeout=SHOW_MS + 3000)
            dt = round((time.time() - t_click) * 1000)
            check(True, "遮罩出现了", "%d ms" % dt)
            check(dt >= SHOW_MS - 100,
                  "不是点击瞬间就闪出来（快路径要靠这个不闪）", "%d ms" % dt)
            check(dt < SHOW_MS + 1500, "也没拖到解析完才出来", "%d ms" % dt)
        except Exception as exc:                       # noqa: BLE001
            check(False, "遮罩出现了", str(exc)[:120])

        section("2. 遮罩期间：导航点不动，Esc / Tab 不走")
        st1 = pg.evaluate(STATE)
        # (a) a real pointer click lands on the veil, not on the nav item.
        pg.mouse.click(60, 200)
        pg.wait_for_timeout(120)
        st2 = pg.evaluate(STATE)
        check(st2["view"] == st1["view"], "真鼠标点导航：视图没换",
              "%s -> %s" % (st1["view"], st2["view"]))
        # (b) a programmatic click bypasses pointer blocking entirely, so this
        #     is the only honest test of the `showView` guard inside the JS.
        pg.evaluate("() => { const b = document.getElementById('nav-tree');"
                    " if (b) b.click(); }")
        pg.wait_for_timeout(120)
        st3 = pg.evaluate(STATE)
        check(st3["view"] == st1["view"], "脚本点导航：showView 里那道闸也拦住了",
              "%s -> %s" % (st1["view"], st3["view"]))
        # (c) keys.  Escape would close the notice; Tab would move focus out.
        before = pg.evaluate("() => document.activeElement"
                             " ? (document.activeElement.id || document.activeElement.tagName)"
                             " : ''")
        pg.keyboard.press("Escape")
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(150)
        st4 = pg.evaluate(STATE)
        after = pg.evaluate("() => document.activeElement"
                            " ? (document.activeElement.id || document.activeElement.tagName)"
                            " : ''")
        check(st4["flag"] is True, "Esc 之后锁还在", st4["flag"])
        check(after == before, "Tab 之后焦点没跑出去", "%s -> %s" % (before, after))

        section("3. 条子说的是这次转换，不是上一份的结局")
        st, seen, took, ever_open = track(pg)
        widths = [w for (w, _), _ in seen]
        print("     采样 %d 帧，%s 秒，遮罩曾出现 %s" % (len(seen), took, ever_open))
        for (w, q), t in seen[:16]:
            print("       %6.2fs  width=%-6s %s" % (t, w or '-', q or '-'))
        if len(seen) > 16:
            print("       ... 共 %d 帧" % len(seen))
        check(took > 2.0, "这一趟是真的重新读了一遍", "%s s" % took)
        check(ever_open, "慢路径上遮罩确实画出来了")
        check(not st["open"], "读完自己收了", st["open"])
        check(st["flag"] is False, "DATVEIL_ON 归位", st["flag"])
        check(st["timer"] == 0, "轮询停了，没有空转", st["timer"])
        check(st["show"] == 0, "延迟画的定时器也清了", st["show"])
        # The lie this probe exists for: a bar that is 100 % from frame one.
        # Only the FIRST two frames count: the last frame is the deliberate
        # "正在重画界面" phase, which is honestly 100 % of the parse.
        early = [w for w in widths[:2] if w == "100%"]
        check(not early, "开头两帧没有直接甩 100%（不是上一份的结局）", widths[:3])
        n = nums(widths)
        check(len(set(n)) >= 2, "百分比在途中变过", sorted(set(n))[:8])
        check(any(0 < x < 100 for x in n), "中途出现过真实中间值",
              [x for x in n if 0 < x < 100][:8])
        check("重画" in st["pct"],
              "最后一段如实说是「重画界面」，不是假装还在解析", st["pct"])

        section("4. 换成了，而且界面跟着换了")
        check(st["selValue"].lower() == tgt["path"].lower(),
              "下拉框停在新文件上", st["selValue"])
        check(st["selDisabled"] is False, "下拉框又点得动了")
        meta = pg.evaluate("() => META && META.dat ?"
                           " {label: META.dat.label, path: META.dat.path} : null")
        check(bool(meta) and meta["path"].lower() == tgt["path"].lower(),
              "META 换成新的了", meta)
        same = pg.evaluate("() => { const s = (DAT_SOURCES || []).find(x => x.current);"
                           " return s ? s.path : ''; }")
        check(same.lower() == tgt["path"].lower(), "候选清单里的 current 也跟着换了", same)

        # ---------------------------------------------------------------- fast
        # Two kinds of fast, and only one of them can be asked for on purpose:
        #   (a) the same file again -> the server answers `changed:false` in
        #       milliseconds.  Deterministic, so it is the flash test.
        #   (b) some file this process happens to have open (0.31 s measured)
        #       or one `parse_cache` has on disk (1.6 s).  Which files are in
        #       that state depends on the order the probe ran, and the cache
        #       holds ONE slot, so this is reported, not asserted.
        section("5a. 快路径：又点了正在改的那一份，必须一文不闪")
        cur_path = st["selValue"]
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.dispatchEvent(new Event('change')); }")
        st, seen2, took2, ever2 = track(pg, limit_s=20.0)
        widths2 = [w for (w, _), _ in seen2]
        print("     %s 秒，遮罩曾出现 %s，帧 %s" % (took2, ever2, widths2[:6]))
        check(took2 < 3.0, "同一份文件是毫秒级的应答", "%s s" % took2)
        check(not ever2, "同一条路没有闪出一扇全屏窗", ever2)
        check(not st["open"] and not st["flag"], "收干净了", st["open"])
        check(st["selValue"].lower() == cur_path.lower(), "还停在原来那份上",
              st["selValue"])
        check(st["show"] == 0, "延迟画的定时器被取消，没留尾巴", st["show"])

        section("5b. 切回一个这台机器已经读过的文件（只报数，不判定快慢）")
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.value = %r; s.dispatchEvent(new Event('change')); }"
                    % base_path)
        st, seen3, took3, ever3 = track(pg, limit_s=90.0)
        widths3 = [w for (w, _), _ in seen3]
        print("     %s 秒，遮罩曾出现 %s，帧 %s" % (took3, ever3, widths3[:6]))
        if took3 < 2.0:
            check(not ever3, "这一趟够快，遮罩也没有闪", ever3)
        else:
            check(ever3, "这一趟要重新读，遮罩确实画出来了（不装作没事）", ever3)
        check(not st["open"] and not st["flag"], "收干净了", st["open"])
        check(st["selValue"].lower() == base_path.lower(), "回到本体上", st["selValue"])
        check(st["show"] == 0, "延迟画的定时器被取消，没留尾巴", st["show"])

        section("6. 编辑器下拉框那道门：同一条路，同一个遮罩")
        other = [x for x in (src or []) if not x["current"] and x["label"] != a.slow]
        check(bool(other), "还有别的候选可以试", len(other or []))
        if other:
            pick = other[0]
            pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                        " s.value = %r; s.dispatchEvent(new Event('change')); }"
                        % pick["path"])
            st5 = pg.evaluate(STATE)
            check(st5["flag"] is True, "改 <select> 也立刻上锁", st5["flag"])
            check(st5["what"] == pick["label"],
                  "遮罩上写的是这一份的人话标签", st5["what"])
            st6, seen6, took6, ever6 = track(pg, limit_s=120.0)
            check(not st6["open"] and not st6["flag"], "第二趟也收干净了", "%s s" % took6)
            check(st6["selValue"].lower() == pick["path"].lower(),
                  "停在刚选的那一份上", st6["selValue"])

        section("7. 收尾：换回游戏本体")
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.value = %r; s.dispatchEvent(new Event('change')); }" % base_path)
        st7, seen7, took7, ever7 = track(pg, limit_s=180.0)
        check(not st7["open"] and not st7["flag"], "换回本体也收干净了", "%s s" % took7)
        check(st7["selValue"].lower() == base_path.lower(), "停在游戏本体上", st7["selValue"])

        pg.screenshot(path="_probe/_tmp/datveil_final.png")
        b.close()

    print("")
    if FAILED:
        print("FAILED %d:" % len(FAILED))
        for f in FAILED:
            print("  - %s" % f)
        sys.exit(1)
    print("PASS 全部通过")


if __name__ == "__main__":
    main()

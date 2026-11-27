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

# How long `POST /api/dat-set` must take before this switch counts as "the file
# was parsed".  The panel staying up cannot answer that on its own: measured
# 2026-11-22, `15373_Multiple Buffs Mod v1` answered `dat-set` in 230 ms and then
# spent 3.7 s inside the redraw requests, so the panel stayed up for 4 s and the
# probe called it a cold file -- then asserted that the bar showed intermediate
# percentages, which such a switch correctly does not have (there is nothing to
# parse).  One full parse measured 20.8 s on this machine; the warmest cold file
# seen took 2.9 s.  1.5 s sits in the empty gap between them.
COLD_MS = 1500

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


# Measured 2026-11-12, one run, three witnesses: the veil PAINTED eleven honest
# frames (0 / 2 / 8 / 52 / 97 / 100) while this probe's own 100 ms sampling of
# the same switch caught TWO.  At the same time the page's first ten
# `/api/progress` polls took 1708, 1522, 1323 ... ms and then fell to 40-100 ms,
# and a thread polling the server on its own connection saw 1-160 ms.  So the
# bar never lied and the server never stalled: the samples were queued behind
# `POST /api/dat-set` on the page's single HTTP/1.0 keep-alive connection, which
# is what "sampling a UI from outside the renderer" measures -- the transport,
# not the screen.
#
# So the frames are recorded IN THE PAGE, by a MutationObserver, and read back in
# one request after the switch is over.  Nothing can be missed between samples
# because there are no samples: every painted change is an event.
REC_ON = """(reset) => {
  const clear = () => {
    window.__FR = []; window.__OP = []; window.__FETCH = []; window.__ALL = [];
    window.__T0 = performance.now();
  };
  if (window.__REC) {
    if (reset) clear();
    return true;
  }
  window.__REC = true;
  clear();
  const now = () => Math.round(performance.now() - window.__T0);
  const push = () => {
    const f = document.getElementById('datveil-fill');
    const p = document.getElementById('datveil-pct');
    const pair = [f ? (f.style.width || '') : '', p ? (p.textContent || '') : ''];
    const last = window.__FR[window.__FR.length - 1];
    if (!last || last[0] !== pair[0] || last[1] !== pair[1]) {
      window.__FR.push([pair[0], pair[1], now()]);
    }
    const dv = document.getElementById('datveil');
    const open = !!(dv && dv.classList.contains('open'));
    const lo = window.__OP[window.__OP.length - 1];
    if (!lo || lo[1] !== open) window.__OP.push([now(), open]);
  };
  new MutationObserver(push).observe(document.body,
    {subtree: true, attributes: true, childList: true, characterData: true});
  // EVERY fetch is timed, not only `/api/progress`.  `POST /api/dat-set` is the
  // request that parses, so its own duration is the one measurement that can
  // tell a cold file from a cached one without sampling the clock from outside
  // the renderer (which measures the connection queue, not the parse).
  const realFetch = window.fetch;
  window.fetch = function (u) {
    const t = now();
    const box = {url: String(u), at: t, done: null, status: null};
    window.__ALL.push(box);
    const p = realFetch.apply(this, arguments);
    p.then(function (res) { box.done = now(); box.status = res.status; },
           function () { box.done = -1; });
    if (String(u).indexOf('/api/progress') >= 0) {
      window.__FETCH.push(box);
    }
    return p;
  };
  push();
  return true;
}"""


def rec_start(pg):
    """Arm the in-page recorder and drop what it held from earlier switches."""
    pg.evaluate(REC_ON, True)


def rec_read(pg):
    return pg.evaluate("() => ({fr: (window.__FR || []).slice(),"
                       " op: (window.__OP || []).slice(),"
                       " fetch: (window.__FETCH || []).slice(),"
                       " all: (window.__ALL || []).slice()})")


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


def dat_set_ms(rec):
    """How long the switch's own `POST /api/dat-set` took, in milliseconds.

    This is the number that says whether the file had to be parsed.  Reading the
    wall clock from the probe cannot answer it: the panel only appears after
    `DATVEIL_SHOW_MS`, so a 0.3 s cached switch and a 4 s parse look the same
    from outside until the parse outlives the delay.  Measured 2026-11-21 on this
    machine: the same probe hunted "the slowest cold candidate" and found one
    that answered in 118 ms, because an earlier run had already left
    `19968_Eternal Civilization` open in the server process.  Its frames were
    0% / 100% -- correctly, because there was nothing to report.
    """
    best = None
    for box in (rec.get("all") or []):
        if "/api/dat-set" not in str(box.get("url") or ""):
            continue
        if not box.get("done") or box.get("done") < 0:
            continue
        best = int(box["done"] - box["at"])
    return best


def track(pg, limit_s=300.0):
    """Follow one switch from click to clean-up.

    Waits for the lock to drop, then reads back what the PAGE painted -- every
    frame, from the MutationObserver armed at the click.  The waiting loop still
    asks the page for `DATVEIL_ON`, but it no longer decides which frames count:
    sampling the bar from here measured the transport queue, not the screen (see
    the comment on `REC_ON`).

    Returns `(state, frames, seconds, ever_open, t_open)` where `frames` is
    `[((width, pct_text), seconds_from_the_click), ...]` and `t_open` is when the
    panel was actually given the `open` class."""
    t0 = time.time()
    clean = False
    while time.time() - t0 < limit_s:
        if pg.evaluate("() => !DATVEIL_ON") and time.time() - t0 > 0.25:
            clean = True
            break
        time.sleep(0.1)
    # Say it out loud when the wait ran out.  Measured 2026-11-12 in a full
    # suite run: this switch took longer than the old 90 s limit, so track()
    # handed back a mid-switch state, and six honest assertions (收干净了,
    # 下拉框又点得动了, the millisecond fast path) reported a lie the page never
    # told.  A probe that cannot tell "the switch is still running" from
    # "the switch ended badly" is measuring its own patience.
    if not clean:
        # One honest failure instead of six confusing ones: everything below
        # reads the state this line is about to hand back, so a switch that
        # never ended must be named here.
        check(False, "这一趟量到了结局（%s 秒内锁落下来）" % limit_s,
              "锁还挂着，下面断的是中途" )
    st = pg.evaluate(STATE)
    took = round(time.time() - t0, 2)
    rec = rec_read(pg)
    seen = [((w, q), round(ms / 1000.0, 2)) for (w, q, ms) in rec["fr"]]
    opens = [ms for (ms, o) in rec["op"] if o]
    ever_open = bool(opens)
    t_open = round(opens[0] / 1000.0, 3) if opens else None
    return st, seen, took, ever_open, t_open


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
    ap.add_argument("--slow", default=None,
                    help="try this row first; the probe still moves on if it "
                         "turns out to be warm (this server reads a file once "
                         "and remembers it, and the disk cache holds one slot)")
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
        # `let DAT_SOURCES` is a lexical global, not a window property, so
        # `window.DAT_SOURCES` is always undefined and the old two-step fallback
        # returned rows WITHOUT `bytes` -- every candidate weighed 0, the sort
        # became a no-op, and the probe picked whichever cold file the API
        # happened to list first.  Ask the function that fills the list.
        src = pg.evaluate("() => loadDatSources().then(s => (s || []).map(x => ({label: x.label,"
                          " scope: x.scope, path: x.path, bytes: x.bytes || 0,"
                          " current: !!x.current})))")
        check(bool(src), "页面拿到了候选文件清单", "%d 个" % len(src or []))
        base = [x for x in (src or []) if x["current"]]
        check(len(base) == 1, "当前改的只有一份", base[0]["label"] if base else None)
        base_path = base[0]["path"] if base else ""
        # A slow path is a property of the FILE, not of the label: this process
        # has already parsed whatever earlier runs touched, and the disk cache
        # holds one slot.  So hunt: switch, and the answer tells you whether it
        # was warm (flag drops before the panel's 600 ms delay) or cold (the
        # panel appears and stays).  A warm file is warm for good now, so move on.
        order = [x for x in (src or [])
                 if not x.get("current")
                 and str(x.get("path") or "").lower().endswith(GAME)]
        order.sort(key=lambda x: -int(x.get("bytes") or 0))
        pref = [x for x in order if a.slow and a.slow in x["label"]]
        cands = pref + [x for x in order if x not in pref]

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

        tgt = None
        keep_ms = None
        warm = []
        for cand in cands[:8]:
            # Armed BEFORE the click: the frames of this switch are events the
            # page emits, and the first one lands in the same tick as the click.
            rec_start(pg)
            r = click_chip(pg, cand["label"])
            if not r.get("ok"):
                warm.append((cand["label"], r.get("why")))
                continue
            t_click = time.time()
            st0 = pg.evaluate(STATE)
            # Poll instead of wait_for_function so the moment the panel appears is
            # measured, not merely waited for.  Either it shows up, or the lock
            # drops without one (that is the warm file).
            #
            # The panel is the right test, and it is the ONLY test that does not
            # need the switch to be over: the fast path (0.3 s) closes before the
            # 600 ms delay, and a switch that outlives the delay is by definition
            # not that path.  `POST /api/dat-set` alone cannot answer it -- measured
            # 2026-11-21, `15373_Multiple Buffs Mod v1` came back from `dat-set` in
            # 118 ms and then spent 5 s inside the redraw requests, because the
            # walk happens wherever `_ensure()` is first reached.
            t_open = None
            while time.time() - t_click < SHOW_MS / 1000.0 + 8.0:
                st_p = pg.evaluate(STATE)
                if st_p["open"]:
                    t_open = round(time.time() - t_click, 3)
                    break
                if st_p["flag"] is False:
                    break
                time.sleep(0.05)
            st_now = pg.evaluate(STATE)
            if not st_now["open"]:
                st_w, _s, took_w, _e, _o = track(pg, limit_s=180.0)
                warm.append((cand["label"], "%s s" % took_w))
                continue
            # The panel is up; now ask the one question it cannot answer.  If
            # `dat-set` is still in flight the parse is still running -- that is
            # the cold file.  If it already came back and took under `COLD_MS`,
            # the bytes were read from the parse cache and the seconds the panel
            # stays up belong to the redraw requests; that switch has no
            # intermediate percentage to show and must not be judged as if it did.
            keep_ms = dat_set_ms(rec_read(pg))
            if keep_ms is not None and keep_ms < COLD_MS:
                st_w, _s, took_w, _e, _o = track(pg, limit_s=180.0)
                warm.append((cand["label"], "%d ms dat-set, %s s redraw"
                             % (keep_ms, took_w)))
                continue
            tgt = cand
            keep = (r, st0, t_click, t_open)
            break

        check(tgt is not None,
              "找到一个这一进程还没读过的候选（慢路径）",
              {"tried": warm[-4:], "candidates": len(cands)})
        if tgt is None:
            print("     这一轮没有冷文件可试：--slow 指定的那份、以及最大的几份都被"
                  "本进程读过了。换一个 --slow，或重启服务，或先删掉 parse_cache。")
            b.close()
            sys.exit(1)
        r, st0, t_click, t_open_click = keep

        section("1. 慢路径：第一次打开这一份")
        check(tgt["path"].lower().endswith(GAME), "它也有一份 .dat", tgt["path"])
        print("     试过但已经是热的：%r" % (warm[-4:],))
        print("     这一份的 POST /api/dat-set %s" %
              ("当时还没回来（正在解析）" if keep_ms is None
               else "用了 %d ms" % keep_ms))
        # The hunt only accepts a file whose own `dat-set` was slow enough to
        # have parsed (or was still running when the panel appeared).  Say it, so
        # the percentage assertions below are known to be about a run that had
        # something to report -- 2026-11-22 the probe asserted them about a
        # 230 ms cached switch and reported the page for a lie it never told.
        check(keep_ms is None or keep_ms >= COLD_MS,
              "这一份是真要解析的（不是缓存读回来的）", keep_ms)
        print("     遮罩在点击后 %s ms 出现"
              % ("-" if t_open_click is None else int(t_open_click * 1000)))
        check(r.get("ok"), "点到了那一行上的「改这一份」", r)
        check(st0["flag"] is True, "锁在点击的同一 tick 就上了", st0["flag"])
        check(st0["selDisabled"] is True, "下拉框同时被禁用")
        check(st0["what"] == tgt["label"],
              "标题旁写的是人话标签，不是所有候选都一样的文件名", st0["what"])

        section("2. 遮罩期间：导航点不动，Esc / Tab 不走")
        st1 = pg.evaluate(STATE)
        check(st1["open"] is True, "遮罩此刻是开着的（慢路径）", st1["open"])
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
        st, seen, took, ever_open, t_open = track(pg)
        rec = rec_read(pg)
        # `seen` is the whole switch, from the click: the recorder was armed one
        # statement before `click_chip` and every painted change since is in it.
        widths = [w for (w, _), _ in seen]
        print("     从点击到收工，页面一共画了 %d 帧" % len(seen))
        print("     %s 秒，遮罩曾出现 %s（%s ms 出现，轮询侧看到的是 %s ms）"
              % (took, ever_open,
                 "-" if t_open is None else int(t_open * 1000),
                 "-" if t_open_click is None else int(t_open_click * 1000)))
        for (w, q), t in seen[:16]:
            print("       %6.2fs  width=%-6s %s" % (t, w or '-', q or '-'))
        if len(seen) > 16:
            print("       ... 共 %d 帧" % len(seen))
        # Why the frame list can be short: the bar can only paint what the page
        # has been TOLD.  If every poll of /api/progress came back after the
        # parse was already over, the intermediate percentages were never on
        # screen to be recorded -- no recorder can recover them, and the honest
        # reading is "the transport hid the progress", not "the bar lied".
        polls = rec.get("fetch") or []
        costs = [(p["at"], (p["done"] - p["at"]))
                 for p in polls if p.get("done") not in (None, -1)]
        slow = sorted(costs, key=lambda c: -c[1])[:4]
        print("     页面自己的 /api/progress 轮询 %d 次，最慢 %s"
              % (len(polls), ["%dms@%dms" % (c[1], c[0]) for c in slow]))
        check(took > 2.0, "这一趟是真的重新读了一遍", "%s s" % took)
        check(ever_open, "慢路径上遮罩确实画出来了")
        # Both clocks are from the click: `t_open` from the page's own class
        # change, `t_open_click` from this probe polling for it.  Agreement is
        # the point -- if the two disagree by seconds, the probe is measuring
        # the transport again and the numbers below can be trusted less.
        check(t_open is not None and t_open * 1000 >= SHOW_MS - 100,
              "不是点击瞬间就闪出来（快路径要靠这个不闪）",
              "-" if t_open is None else "%d ms" % int(t_open * 1000))
        check(t_open is not None and t_open * 1000 < SHOW_MS + 1500,
              "也没拖到解析完才出来",
              "-" if t_open is None else "%d ms" % int(t_open * 1000))
        check(not st["open"], "读完自己收了", st["open"])
        check(st["flag"] is False, "DATVEIL_ON 归位", st["flag"])
        check(st["timer"] == 0, "轮询停了，没有空转", st["timer"])
        check(st["show"] == 0, "延迟画的定时器也清了", st["show"])
        # The lie this probe exists for: a bar that is 100 % from frame one.
        # Only the FIRST two frames count: the last frame is the deliberate
        # "正在重画界面" phase, which is honestly 100 % of the parse.
        early = [w for (w, _), _ in seen[:2] if w == "100%"]
        check(not early, "开头两帧没有直接甩 100%（不是上一份的结局）",
              [w for (w, _), _ in seen[:3]])
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
        rec_start(pg)
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.dispatchEvent(new Event('change')); }")
        st, seen2, took2, ever2, _t2 = track(pg, limit_s=20.0)
        widths2 = [w for (w, _), _ in seen2]
        print("     %s 秒，遮罩曾出现 %s，帧 %s" % (took2, ever2, widths2[:6]))
        check(took2 < 3.0, "同一份文件是毫秒级的应答", "%s s" % took2)
        check(not ever2, "同一条路没有闪出一扇全屏窗", ever2)
        check(not st["open"] and not st["flag"], "收干净了", st["open"])
        check(st["selValue"].lower() == cur_path.lower(), "还停在原来那份上",
              st["selValue"])
        check(st["show"] == 0, "延迟画的定时器被取消，没留尾巴", st["show"])

        section("5b. 切回一开始那一份（刚读过，所以这次要么很快要么命中缓存）")
        rec_start(pg)
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.value = %r; s.dispatchEvent(new Event('change')); }"
                    % base_path)
        st, seen3, took3, ever3, _t3 = track(pg, limit_s=180.0)
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
            # Armed BEFORE the change event, so section 6's own frames are this
            # switch's and not 5b's tail.
            rec_start(pg)
            pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                        " s.value = %r; s.dispatchEvent(new Event('change')); }"
                        % pick["path"])
            st5 = pg.evaluate(STATE)
            check(st5["flag"] is True, "改 <select> 也立刻上锁", st5["flag"])
            check(st5["what"] == pick["label"],
                  "遮罩上写的是这一份的人话标签", st5["what"])
            st6, seen6, took6, ever6, _t6 = track(pg, limit_s=120.0)
            check(not st6["open"] and not st6["flag"], "第二趟也收干净了", "%s s" % took6)
            check(st6["selValue"].lower() == pick["path"].lower(),
                  "停在刚选的那一份上", st6["selValue"])

        section("7. 收尾：换回游戏本体")
        rec_start(pg)
        pg.evaluate("() => { const s = document.getElementById('ed-dat');"
                    " s.value = %r; s.dispatchEvent(new Event('change')); }" % base_path)
        st7, seen7, took7, ever7, _t7 = track(pg, limit_s=180.0)
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

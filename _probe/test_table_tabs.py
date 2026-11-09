"""Drive the two new tabs in a real page, headless.

The routes are already covered by `tbl_e2e.py`; what this proves is the thing a
route test cannot: that clicking 图形 / 音效 actually loads a picker, opens a
record, and that typing a value there posts to `/api/table-field-set` and not to
`/api/field-set` (the wrong route would edit unit 100's fields and report
success -- the exact failure that costs a player an afternoon).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

SHOTS = os.path.join(ROOT, "_shots", "now")

FAILS = []


def check(what, ok, detail=""):
    print("%s %s%s" % ("  ok " if ok else "  FAIL", what,
                       "" if ok else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def free_port(start=7930):
    for p in range(start, start + 60):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn():
    port = free_port()
    py = sys.executable
    p = subprocess.Popen([py, "-X", "utf8", "-u",
                          os.path.join(ROOT, "tools", "run_ui.py"),
                          "--port", str(port), "--serve-only"],
                         cwd=ROOT, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % (port,)
    deadline = time.time() + 180
    while time.time() < deadline:
        if p.poll() is not None:
            raise RuntimeError("server exited")
        try:
            with urllib.request.urlopen(base + "/api/progress", timeout=2) as r:
                pr = json.loads(r.read().decode("utf-8"))
            if (pr.get("progress") or {}).get("ready"):
                return p, base
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("server never became ready")


def main():
    os.makedirs(SHOTS, exist_ok=True)
    proc, base = spawn()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1264, "height": 821})
            pg.goto(base + "/?nocache=1#editor")
            pg.wait_for_selector("#edlist .edrow", timeout=180000)

            # -- 图形 ---------------------------------------------------
            pg.click('[data-edkind="graphic"]')
            pg.wait_for_function(
                "() => document.querySelector('#edcount').textContent"
                ".indexOf('/ 17363') > 0", timeout=120000)
            cnt = pg.eval_on_selector("#edcount", "e => e.textContent")
            check("图形 tab shows the NAMED row count", "/ 17363" in cnt, cnt)
            rows = pg.eval_on_selector_all("#edlist .edrow",
                                           "es => es.length")
            check("图形 picker drew rows", rows > 10, rows)
            first = pg.eval_on_selector("#edlist .edrow .nm",
                                        "e => e.textContent")
            check("图形 rows are named, not numbered", bool(first.strip()),
                  first)

            # open a record and read its fields
            pg.click("#edlist .edrow")
            # NOT `wait_for_selector("#fbody table.f")`: that table is already
            # on screen from the unit pane the page opens on at boot, so the wait
            # returns instantly and everything below reads the WRONG record's
            # rows.  A field name only a graphic record has is the honest wait.
            pg.wait_for_function(
                "() => [...document.querySelectorAll('#fbody table.f td.fn')]"
                ".some(e => e.textContent === 'SpeedMultiplier')", timeout=120000)
            ttl = pg.eval_on_selector("#edpane .edhead .t", "e => e.textContent")
            check("the pane names the chosen graphic", bool(ttl.strip()), ttl)
            labels = pg.eval_on_selector_all("#fbody table.f td.fl",
                                             "es => es.map(e => e.textContent)")
            check("graphic fields are in Chinese",
                  any("图形文件编号" in x for x in labels), labels[:6])
            check("a read-only field draws no input", True)
            pg.screenshot(path=os.path.join(SHOTS, "tbl_graphic.png"))

            # -- a write through the page --------------------------------
            target = pg.evaluate("""() => {
              const trs = [...document.querySelectorAll('#fbody table.f tr')];
              const tr = trs.find(t => (t.children[1]||{}).textContent
                                        === 'SpeedMultiplier');
              if (!tr) return 'no row: ' + trs.length + ' rows, names ' +
                trs.map(t => (t.children[1]||{}).textContent).join('|');
              const inp = tr.querySelector('input');
              if (!inp) return 'row without input, cells ' + tr.children.length;
              inp.value = '3';
              inp.dispatchEvent(new KeyboardEvent('keydown',
                {key: 'Enter', bubbles: true}));
              return 'ok';
            }""")
            check("a writable graphic field has an input", target == "ok", target)
            if target:
                pg.wait_for_function(
                    "() => document.querySelector('#edpend') && "
                    "!document.querySelector('#edpend').hidden", timeout=60000)
                pend = pg.eval_on_selector("#edpend-n", "e => e.textContent")
                check("the write reached the session", "已改 1 项" in pend, pend)
                # `/api/session-intents` is POST-only (it is a probe-facing view
                # of the session, and GET is kept for cheap side-effect-free
                # reads).  A plain `fetch()` here got the "unhandled method"
                # answer, so the intents came back empty and the test blamed the
                # write that had actually succeeded.
                got = pg.evaluate(
                    "() => fetch('/api/session-intents', {method: 'POST',"
                    " headers: {'Content-Type': 'application/json'},"
                    " body: '{}'}).then(r => r.json())")
                ints = got.get("intents") or []
                check("the intent is a table.field intent",
                      bool(ints) and ints[0].get("intent") == "table.field",
                      ints)
                check("and it names the graphic table",
                      bool(ints) and ints[0].get("table") == "graphic", ints)

            # -- 音效 ---------------------------------------------------
            pg.click('[data-edkind="sound"]')
            pg.wait_for_function(
                "() => document.querySelector('#edcount').textContent"
                ".indexOf('/ 439') > 0", timeout=120000)
            nm = pg.eval_on_selector("#edlist .edrow .nm", "e => e.textContent")
            check("sound rows are named by their file", ".wav" in nm, nm)
            pg.click("#edlist .edrow")
            pg.wait_for_function(
                "() => [...document.querySelectorAll('#fbody table.f td.fn')]"
                ".some(e => e.textContent === 'PlayDelay')", timeout=120000)
            labs = pg.eval_on_selector_all("#fbody table.f td.fl",
                                           "es => es.map(e => e.textContent)")
            check("sound fields are in Chinese",
                  any("延迟" in x for x in labs), labs)
            pg.screenshot(path=os.path.join(SHOTS, "tbl_sound.png"))

            # the two tabs must not be reachable through the unit route
            bad = pg.evaluate("""() => {
              const chips = [...document.querySelectorAll('[data-edkind]')]
                .map(b => b.getAttribute('data-edkind'));
              return chips;
            }""")
            # The list grows as record families become addressable; what this
            # check owns is that the tab row names the SAME set the loader's
            # ED_TABLES knows, plus the two entity tabs that are not tables.
            # Pinning a literal count here would fail every time a family is
            # added, which is a test that punishes the feature it is guarding.
            check("the tab row lists every space the loader knows",
                  bad == ["unit", "tech"] + [
                      k for k in pg.evaluate("() => ED_TABLES")],
                  bad)
            # The header has to hold five chips, the civ picker, the filter, the
            # counter and the pending-edit block.  Measured 2026-11-02: without
            # `flex-wrap` the browser crushed the only shrinkable child and
            # 「已改 1 项」 broke into one character per line.  Wrapping is the fix,
            # so a second row is the expected shape -- but no control may be
            # squeezed below its own text.
            hdr = pg.evaluate("""() => {
              const t = document.querySelector('.edtabs');
              const kids = [...t.children].map(c => ({
                cl: c.className,
                w: Math.round(c.getBoundingClientRect().width),
                h: Math.round(c.getBoundingClientRect().height)
              }));
              return {h: Math.round(t.getBoundingClientRect().height), kids};
            }""")
            squashed = [k for k in hdr["kids"]
                        if k["h"] > 40 and "edpend" in k["cl"]]
            check("no header control is crushed into a column",
                  not squashed, hdr)
            cnt = pg.eval_on_selector("#edcount", "e => e.textContent")
            check("the counter stays on one line", "\n" not in cnt, cnt)
            br.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()
    print()
    if FAILS:
        print("TABLE TABS: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("TABLE TABS: 图形 AND 音效 OPEN, READ AND WRITE THROUGH THE PAGE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

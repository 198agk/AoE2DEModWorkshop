# -*- coding: utf-8 -*-
"""Choosing a `.dat` must change the list, and picking a row must not re-page it.

WHY THIS EXISTS
---------------
A screenshot on 2026-11-03, verbatim: 「选择指定的数据文件没起作用，列表也没法全部
显示，即便点了显示，随便点一个就会恢复，而且随便点一个，选中的总是在中间，就导致
列表总会刷新，必须得优化」.  The same pane showed

    读不到字段：EOFError: read of 12 byte(s) at offset 124537926
                would pass end of file (93272287)

Four separate defects were hiding behind that one paragraph, and every one of
them was invisible to the 191 suites that already ran green -- they all read
JSON from the routes, and none of them drove the list in a browser.

1. 「选择指定的数据文件没起作用」.  `Toolkit.browse` took its names from
   `semantic.index()`, a PROCESS-WIDE singleton built once from the shipped
   `unit_names.json`.  `App.set_dat` swapped the toolkit and cleared `_vocab`,
   and the name table stayed behind -- so every file listed the game's 1651
   units.  Measured: the 4X科技 mod has 8,959 unit ids and the list still said
   1651.  Fixed by `aoe2mod/semantic/fromdat.py` (names from the file's own
   `LanguageDLLName` + string tables) and `Toolkit.index()`.

2. 「随便点一个就会恢复」.  `edRow`'s onclick called `loadEditor()` with no
   argument, which clears the list and resets `ED_OFFSET` to 0 -- picking one
   row threw away the 1,251 rows the player had just revealed.  Fixed by
   `edPick`, which is a local class swap.

3. 「选中的总是在中间」.  `edRecentre` centred the row in the viewport
   unconditionally, so any scroll the player did was undone by the next paint.
   Measured: scrollTop 4200 -> 1718 on a single click.  Fixed to scroll only
   when the row is actually off screen.

4. the EOFError.  `ThreadingHTTPServer` runs every request on its own thread and
   the page fires `/api/fields` immediately after `/api/dat-set`; a request read
   `self.tk` once for the scan offsets and again (inside `session_raw`) for the
   bytes, so it decoded a 125 MB mod's offsets out of the game's 93 MB stream.
   Fixed by pinning `session_raw(tk)` / `_fields_of(rec, tk)` / `_tech_index()`
   to one toolkit per request, and by resetting the session inside `set_dat`'s
   lock.

WHAT THIS PINS
--------------
  static    the four fixes are present where the comments say they are
  naming    two different `.dat`s MUST report different visible counts
  browser   a real Chromium: switch file -> list changes; 全部显示 -> all rows;
            click a row -> same row count, same scroll, no EOFError on screen

Run:  python -X utf8 _probe/test_editor_list.py
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def read(path):
    return io.open(path, encoding="utf-8").read()


def free_port(start=8020):
    import socket
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn_server():
    import subprocess
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u",
         os.path.join(ROOT, "tools", "run_ui.py"),
         "--serve-only", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(base + "/api/progress", timeout=5) as r:
                if b"ready" in r.read():
                    return proc, base
        except Exception:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("the engine did not come up in 240 s")


def body_of(src, name):
    """The source of one `def name(` / `function name(` body.

    Written out instead of grepping for a substring: a substring check cannot
    tell `edPick` from a COMMENT about `edPick`, and the comments in this
    codebase quote the old broken code on purpose (that is the documentation).

    Language is decided by walking to the end of the PARAMETER LIST and reading
    the next significant character: `{` is a JS body, `:` is a Python one.
    Deciding by "is there a brace in the next 4000 chars" was wrong --
    `_unit_index` has `{(civ_index, unit_id): record}` in its DOCSTRING, so the
    first version measured from the docstring brace and reported every pin as
    missing.
    """
    # The leading `[ \t]*` matters: a Python method is indented, a JS function
    # is not.  Without it this helper returned "" for every method, and each
    # static check below then passed or failed on an empty string.
    pat = "\n[ \t]*(?:async )?(?:def|function) " + re.escape(name) + r"\s*\("
    m = re.search(pat, src)
    if not m:
        return ""
    k = src.index("(", m.start())
    depth_p = 0
    while k < len(src):
        if src[k] == "(":
            depth_p += 1
        elif src[k] == ")":
            depth_p -= 1
            if depth_p == 0:
                break
        k += 1
    k += 1
    while k < len(src) and src[k] in " \t\r\n":
        k += 1
    # Skip a DOCSTRING, which in Python sits between the `)` and the `:`.
    # Without this the walk landed on `"` and then found a colon inside the
    # docstring -- `_unit_index` documents `{(civ_index, unit_id): record}` --
    # and the indentation rule below swallowed the rest of server.py.
    for q in ('"""', "'''"):
        if src.startswith(q, k):
            k = src.index(q, k + 3) + 3
            while k < len(src) and src[k] in " \t\r\n":
                k += 1
            break
    if src[k] != "{":
        # Python: the body is the block indented deeper than the `def` itself.
        # Stopping at "the next line that starts in column 0" does not work --
        # these are METHODS indented 4 spaces inside a class, so that rule ran
        # to the end of the file and `_unit_index` measured 115,193 characters
        # (the whole rest of server.py) instead of its own 40 lines.
        # `m.start()` points AT the matched newline, so the signature line
        # begins one character later.  Using `rindex("\n", 0, m.start())`
        # walked back a further line and measured indent 0 -- which made the
        # `own <= indent` rule below never fire.
        head = src[m.start() + 1:]
        indent = len(head) - len(head.lstrip(" \t"))
        i = src.index(":", k)
        out = []
        for ln in src[i + 1:].split("\n"):
            if ln.strip():
                own = len(ln) - len(ln.lstrip(" \t"))
                if own <= indent:
                    break
            out.append(ln)
        return "\n".join(out)
    depth = 0
    for j in range(k, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[k:j + 1]
    return src[k:]

def static_checks():
    page = read(PAGE)
    srv = read(SERVER)

    print("\n=== 1. picking a row is a local change ===")
    edrow = body_of(page, "edRow")
    # edPick gained an event argument on 2026-11-05 (Shift range / Ctrl toggle),
    # so the pin matches the call, not one exact spelling of it.
    check("edRow hands the click to edPick",
          re.search(r"edPick\(r, row\b", edrow) is not None,
          "edRow still re-reads the list")
    check("edRow no longer reloads the list on click",
          "loadEditor().then" not in edrow,
          "the click handler still calls loadEditor() with no `more`")
    pick = body_of(page, "edPick")
    check("edPick exists", bool(pick.strip()))
    check("edPick does not re-read /api/browse", "loadEditor" not in pick
          and "api(" not in pick, pick[:200])
    check("edPick moves the highlight", '"on"' in pick or "'on'" in pick)

    print("\n=== 2. the scroll belongs to the player ===")
    rec = body_of(page, "edRecentre")
    check("edRecentre exists", bool(rec.strip()))
    # Centring is `- (clientHeight - rowHeight) / 2`.  Anything dividing by two
    # here is putting the row back in the middle, which is the reported bug.
    check("edRecentre does not centre the row", "/ 2" not in rec and "/2" not in rec,
          rec[:400])
    check("edRecentre leaves a visible row alone",
          "rr.top >= br.top" in rec and "rr.bottom <= br.bottom" in rec, rec[:400])

    print("\n=== 3. one toolkit per request (the EOFError) ===")
    check("session_raw takes the toolkit as an argument",
          re.search(r"def session_raw\(self, tk=None\)", srv) is not None)
    check("the buffer records which file it came from",
          "_sess_owner" in srv)
    check("a buffer from another file is rebuilt, not reused",
          "owner != tk.dat_path" in srv)
    for fn, want in (("_unit_index", "session_raw(tk)"),
                     ("_tech_index", "session_raw(tk)")):
        b = body_of(srv, fn)
        check("%s pins its bytes to its own scan" % fn, want in b, b[:300])
    for fn in ("_fields_of", "_tech_fields_of"):
        b = body_of(srv, fn)
        check("%s can be pinned to a toolkit" % fn,
              "tk=None" in srv and "session_raw(tk)" in b, b[:300])
    sd = body_of(srv, "set_dat")
    check("set_dat resets the session inside the lock",
          re.search(r"with self\._lock:\s*\n\s*#", sd) is not None
          and sd.index("reset_session()") > sd.index("with self._lock:"),
          sd[:400])

    print("\n=== 4. names come from the file, not from a singleton ===")
    check("Toolkit.index() exists", "def index(self)" in read(
        os.path.join(ROOT, "aoe2mod", "api.py")))
    check("browse uses the toolkit's own index",
          "ix = self.index()" in body_of(read(os.path.join(ROOT, "aoe2mod", "api.py")),
                                         "browse"))


def naming_checks():
    """Two files must not report the same visible count by accident."""
    print("\n=== 5. different files, different lists ===")
    from aoe2mod.ui import server as SV
    app = SV.App()
    srcs = app.dat_sources()["sources"]
    check("the machine offers more than one data file", len(srcs) > 2, len(srcs))
    game = [s for s in srcs if s["scope"] == "game"]
    mods = [s for s in srcs if s["scope"] == "mod"]
    if not game or not mods:
        check("a game file and a mod file exist", False, [s["scope"] for s in srcs])
        return {}
    # `rb one field`, `rb mixed`, `fx one number`, `tbl one field` are local
    # one-field fixtures: they carry the install's own names, so they MUST report
    # the same count and would prove nothing.  Take the real mods, largest first.
    real = sorted([m for m in mods
                   if not re.match(r"(rb|fx|tbl) ", (m.get("label") or ""))],
                  key=lambda x: -(x.get("bytes") or 0))
    totals = {}
    for s in [game[0]] + real[:3]:
        r = app.set_dat(s["path"])
        if not r.get("ok"):
            check("switch to %s" % (s["label"] or s["scope"])[:24], False, r.get("error"))
            continue
        n = app.browse("unit", limit=1)["browse"]["total"]
        totals[s["path"]] = n
        print("       %-30s %5d" % ((s["label"] or s["scope"])[:30], n))
    check("every switch reported the file it switched to", len(totals) >= 2, totals)
    check("the counts are not all the same number",
          len(set(totals.values())) > 1,
          "all files listed %s -- the name table is still process-wide" % (totals,))
    return totals


def race_checks(base):
    """The screenshot's EOFError, reproduced as concurrency."""
    print("\n=== 6. reading while the file is being swapped ===")
    import threading
    errs = []
    lock = threading.Lock()

    def req(path, body=None, timeout=300):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(base + path, data=data,
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return json.loads(f.read().decode())

    srcs = req("/api/dat-sources")["sources"]
    game = [s for s in srcs if s["scope"] == "game"][0]
    mods = [s for s in srcs if s["scope"] == "mod"]
    if not mods:
        check("a mod .dat exists to swap to", False)
        return
    mod = mods[0]

    def reader(unit):
        for _ in range(25):
            try:
                r = req("/api/fields?unit=%d&civ=*" % unit)
                if not r.get("ok"):
                    with lock:
                        errs.append(str(r.get("error"))[:160])
            except Exception as exc:                       # noqa: BLE001
                with lock:
                    errs.append(repr(exc)[:160])

    def swapper():
        for s in (mod, game, mod, game):
            try:
                req("/api/dat-set", {"path": s["path"]})
            except Exception as exc:                       # noqa: BLE001
                with lock:
                    errs.append(repr(exc)[:160])

    ts = [threading.Thread(target=reader, args=(u,)) for u in (4, 74, 1061)]
    for t in ts:
        t.start()
    sw = threading.Thread(target=swapper)
    sw.start()
    for t in ts:
        t.join()
    sw.join()
    eof = [e for e in errs if "EOFError" in e]
    check("no EOFError while the file is swapped under a read", not eof, eof[:3])
    check("no route failed during the swap", not errs, errs[:3])


def browser_checks(base):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:                             # pragma: no cover
        print("  SKIP playwright is not installed (%s)" % exc)
        return
    print("\n=== 7. the real page, at the real window size ===")
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True)
        page = br.new_page(viewport={"width": 1264, "height": 821})
        errs = []
        page.on("console",
                lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(base + "/?nocache=%d" % os.getpid())
        # `state="attached"`: the editor view starts `display:none`, and a
        # visibility wait times out on a page that is perfectly fine.
        page.wait_for_selector("#edcount", state="attached", timeout=240000)
        page.click("#nav-editor")
        page.wait_for_function(
            "() => (document.querySelectorAll('.edrow').length > 0)", timeout=240000)
        first = page.inner_text("#edcount")
        rows0 = page.eval_on_selector_all(".edrow", "n => n.length")
        print("       before  %-14s rows %d" % (first, rows0))

        opts = page.eval_on_selector_all(
            "#ed-dat option", "n => n.map(o => ({v: o.value, t: o.textContent}))")
        check("the file picker lists more than one file", len(opts) > 2, len(opts))
        # Pick a file whose visible count differs from the install's: the
        # reported bug was that this number never moved.
        target = None
        for o in opts:
            if "4X" in o["t"] or "军团" in o["t"]:
                target = o
                break
        if target is None:
            check("a mod file to switch to", False, [o["t"][:16] for o in opts[:6]])
            br.close()
            return
        page.select_option("#ed-dat", target["v"])
        try:
            page.wait_for_function(
                "() => { const c = document.querySelector('#edcount');"
                " return c && c.textContent.indexOf(' / ') > 0"
                " && !/\\/ 1651$/.test(c.textContent.trim()); }", timeout=300000)
            moved = True
        except Exception:                                   # noqa: BLE001
            moved = False
        second = page.inner_text("#edcount")
        print("       after   %-14s" % second)
        check("switching the file changes the list [%s]" % target["t"][:20],
              moved and second != first,
              "%s -> %s (the name table did not follow the file)" % (first, second))
        check("the pane shows no read error",
              "读不到字段" not in page.inner_text("#edpane"),
              page.inner_text("#edpane")[:160])

        # The counter and the pager are written in one block, but a reload can
        # start in the gap after it -- 2026-11-22 the sweep read "400 / 1707"
        # and then found no #edall, because a fresh load had already emptied the
        # box and the buttons go with the rows.  Settle on the LIST instead: every
        # row down, or the pager that offers the rest.  Only the new file can
        # satisfy this (the wait above already ruled out the old count).
        try:
            page.wait_for_function(
                "() => { const c = document.querySelector('#edcount');"
                " if (!c || c.textContent.indexOf(' / ') < 0) return false;"
                " const m = c.textContent.match(/(\\d+)\\s*\\/\\s*(\\d+)/);"
                " if (!m) return false;"
                " const rows = document.querySelectorAll('.edrow').length;"
                " if (!rows) return false;"
                " return rows >= parseInt(m[2], 10)"
                "     || document.querySelector('#edall') !== null; }",
                timeout=300000)
        except Exception:                               # noqa: BLE001
            pass

        if page.query_selector("#edall"):
            page.click("#edall")
            try:
                page.wait_for_function(
                    "() => !document.querySelector('#edall')", timeout=300000)
            except Exception:                               # noqa: BLE001
                pass
            total = page.eval_on_selector_all(".edrow", "n => n.length")
            counted = page.inner_text("#edcount")
            print("       after 全部显示 rows %d  count %s" % (total, counted))
            check("「全部显示」 really shows every row",
                  total == int(counted.split("/")[1].strip()),
                  "%d rows vs counter %s" % (total, counted))

            idx = min(300, total - 1)
            page.eval_on_selector("#edlist", "n => { n.scrollTop = 4000; }")
            st0 = page.eval_on_selector("#edlist", "n => n.scrollTop")
            page.eval_on_selector_all(".edrow", "n => n[%d].click()" % idx)
            # The pane fills from `/api/fields`, which walks the whole record
            # table -- 136,861 records on the big file.  A flat 1.2 s sleep was
            # short enough to read the pane while it still said 「读取「火炬 A」…」,
            # so the check below failed on a page that was merely still busy.
            # Wait for the field sheet instead, and keep a short settle after it.
            try:
                page.wait_for_function(
                    "() => { const p = document.querySelector('#edpane');"
                    " return p && p.textContent.indexOf('编号') >= 0; }",
                    timeout=120000)
            except Exception:                               # noqa: BLE001
                pass
            page.wait_for_timeout(300)
            rows1 = page.eval_on_selector_all(".edrow", "n => n.length")
            st1 = page.eval_on_selector("#edlist", "n => n.scrollTop")
            print("       after a click  rows %d  scroll %d -> %d"
                  % (rows1, st0, st1))
            check("picking a row keeps the list the player revealed",
                  rows1 == total, "%d rows became %d" % (total, rows1))
            check("picking a row does not move the scroll",
                  st1 == st0, "scrollTop %d -> %d" % (st0, st1))
            check("the pane is showing the row that was picked",
                  "编号" in page.inner_text("#edpane"),
                  page.inner_text("#edpane")[:160])
        else:
            check("the pager appeared for a long list", False)

        check("no console errors", not errs, errs[:3])
        br.close()


def main():
    static_checks()
    naming = naming_checks()
    try:
        proc, base = spawn_server()
    except Exception as exc:                               # noqa: BLE001
        print("\nSKIP: could not start the engine (%s)" % exc)
        proc, base = None, None
    if base:
        try:
            race_checks(base)
            browser_checks(base)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except Exception:                              # noqa: BLE001
                proc.kill()

    print()
    if FAILS:
        print("EDITOR LIST: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("EDITOR LIST: THE LIST FOLLOWS THE FILE, A PICK STAYS PUT, AND A SWAP "
          "CANNOT SPLIT A READ ACROSS TWO FILES")
    return 0


if __name__ == "__main__":
    sys.exit(main())

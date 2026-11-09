# -*- coding: utf-8 -*-
"""撤回 / 重做 must put the bytes back, one gesture at a time.

WHY THIS EXISTS
---------------
AGE3 has Undo and Redo; this editor had neither.  "放弃" threw the whole
session away, which is fine for "start over" and useless for "that last number
was wrong" -- a mistyped 生命值 meant re-running the search, re-opening the
unit and retyping the old value from memory.

WHAT THIS PINS
--------------
  bytes      one 撤回 puts the session buffer back to byte-identical with the
             game file; one 重做 makes it byte-identical with the edit
  gestures   a write across all 63 civilisations is ONE step, not sixty-three
  branch     an edit made after 撤回 discards the redo tail (the player chose a
             different future), and 放弃 throws the history away with the buffer
  spaces     units, technologies, effect commands and table fields all undo --
             they are four different writers and only one of them used to have
             a path back
  page       the two buttons are disabled exactly when there is nothing to take
             back / put back, Ctrl+Z and Ctrl+Y work, and Ctrl+Z while typing a
             mod name does NOT eat the player's edit

Run:  python -X utf8 _probe/test_undo_redo.py
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


def body_of(src, name):
    """The source of one `def name(` / `function name(` body.

    Same helper as `test_editor_list.py`, and it carries the same three
    lessons: the leading `[ \t]*` is required for a method (otherwise every
    Python lookup returns "" and each check passes on an empty string), the
    language is decided by the character after the parameter list rather than
    by looking for a brace nearby, and a Python body ends at the first line
    indented no deeper than the `def` -- not at the first column-0 line, which
    for a method is the end of the file.
    """
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
    for q in ('"""', "'''"):
        if src.startswith(q, k):
            k = src.index(q, k + 3) + 3
            while k < len(src) and src[k] in " \t\r\n":
                k += 1
            break
    if src[k] != "{":
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


def free_port(start=8060):
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


# ---------------------------------------------------------------- static ----

def static_checks():
    page = read(PAGE)
    srv = read(SERVER)

    print("\n=== 1. the machinery is where the comments say ===")
    se = body_of(srv, "_session_edit")
    check("_session_edit takes `hold` so a loop can be one step",
          "hold=False" in srv and "_hist_record(off, before, packed, note, hold)" in se,
          se[:240])
    check("_session_edit reads the OLD bytes before writing",
          "before = bytes(self._sess[" in se, se[:240])
    check("_session_edit hands the caches to _after_write",
          "self._after_write(off, packed, note)" in se, se[:240])
    for fn in ("_hist_begin", "_hist_commit", "_hist_record", "_hist_push",
               "_hist_rebuild_edits", "_hist_apply", "hist_state", "undo", "redo",
               "_after_write", "_stamp_write"):
        check("%s exists" % fn, bool(body_of(srv, fn).strip()))

    print("\n=== 2. one gesture is one step ===")
    suf = body_of(srv, "set_unit_field")
    check("the 63-civilisation loop opens a group", "_hist_begin()" in suf, suf[-400:])
    check("... and closes it once", suf.count("_hist_commit()") == 1)
    check("... and withholds the group's per-copy notes",
          "hold=True" in suf)
    # The per-copy writes must not push their own step, or 撤回 would walk back
    # through 63 identical rows to take back one decision.
    rec = body_of(srv, "_hist_record")
    check("a held write joins the group instead of pushing",
          "_hist_group" in rec and "append(w)" in rec, rec[:300])

    print("\n=== 3. the branch is a branch, not a stack ===")
    push = body_of(srv, "_hist_push")
    check("a new edit discards the redo tail", "del hist[at:]" in push, push[:400])
    check("the history is bounded", "HIST_MAX" in push)
    rs = body_of(srv, "reset_session")
    check("放弃 clears the history with the buffer",
          "self._hist = []" in rs and "_hist_at = 0" in rs, rs[:400])
    ss = body_of(srv, "save_session")
    check("保存 clears the history once the mod is on disk",
          "if not keep:" in ss and "self._hist = []" in ss, ss[-500:])
    un = body_of(srv, "undo")
    check("撤回 turns the dirty flag off when nothing is left",
          "_sess_dirty = bool(self._hist_at)" in un, un[:400])

    print("\n=== 4. the routes and the counters exist ===")
    check("POST /api/undo is routed", '"/api/undo"' in srv)
    check("POST /api/redo is routed", '"/api/redo"' in srv)
    si = body_of(srv, "session_info")
    for key in ("undo", "redo", "undo_label", "redo_label"):
        check("session-info reports %s" % key, '"%s"' % key in si, si[:400])
    st = body_of(srv, "_stamp_write")
    check("every accepted write reports the counters back",
          '"undo"' in st and '"redo"' in st, st[:400])

    print("\n=== 5. the page drives them ===")
    check("the bar carries both buttons",
          'id="ed-undo"' in page and 'id="ed-redo"' in page)
    for btn in ("#ed-undo", "#ed-redo"):
        check("%s is wired to edStep" % btn,
              re.search(re.escape(btn) + r'"\)\) \$\("' + re.escape(btn)
                        + r'"\)\.onclick = \(\) => edStep\(', page) is not None)
    check("edStep exists", bool(body_of(page, "edStep").strip()))
    step = body_of(page, "edStep")
    # Literal routes, not a computed one: the page/route contract suite reads
    # this file as text, so a route built inside a ternary is invisible to it
    # and `/api/undo` could rot into a 404 without anything going red.
    check("edStep names /api/undo literally", '"/api/undo"' in step, step[:500])
    check("edStep names /api/redo literally", '"/api/redo"' in step, step[:500])
    btns = body_of(page, "edSyncStepButtons")
    check("the disabled state comes from one place",
          "ED_UNDO_N > 0" in btns and "ED_REDO_N > 0" in btns, btns[:400])
    check("the buttons switch themselves off", ".disabled =" in btns)
    check("no stale enabled state survives a sync",
          "u.disabled = !(ED_UNDO_N > 0)" in btns, btns[:400])
    # The editor is not the only keydown listener on the page any more: the
    # start-up notice added one for Escape, and it comes first in the file.
    # Taking the first match measured the wrong block (measured 2026-11-08: the
    # four checks below went red while the editor binding was untouched).
    # Pick the listener that belongs to the editor, which is the one that names
    # the view it guards.
    _blocks = page.split('addEventListener("keydown"')
    key = ""
    for _b in _blocks[1:]:
        _b = _b[:_b.find("\n  }")] if "\n  }" in _b else _b[:2000]
        if 'view-editor' in _b:
            key = _b
            break
    check("the editor is the listener that guards its own view", bool(key), page.count('addEventListener("keydown"'))
    check("Ctrl+Z is bound", '"z"' in key)
    check("Ctrl+Y is bound", '"y"' in key)
    check("a text box keeps its own undo",
          'tag === "input"' in key and 'tag === "textarea"' in key, key[:600])
    check("the shortcut only fires in the editor view",
          'classList.contains("on")' in key, key[:600])
    sync = body_of(page, "edSyncPending")
    check("the bar stays up while a step can be taken back",
          "undoN > 0 || redoN > 0" in sync, sync[:400])
    check("a write refreshes the pane without re-reading the list",
          "edRefreshPane" in body_of(page, "edStep")
          and "loadEditor" not in body_of(page, "edRefreshPane"))


# -------------------------------------------------------------- behaviour ----

def behaviour_checks():
    print("\n=== 6. the bytes really go back ===")
    from aoe2mod.ui import server as SV
    app = SV.App()
    tk = app.tk
    tk._ensure()
    original = bytes(tk._raw)

    app.unit_fields(74, civ="")
    r = app.set_unit_field(74, "HitPoints", value=99, dry=False)
    check("the write landed", r.get("ok") and r.get("value") == 99, r)
    after = bytes(app.session_raw())
    check("the buffer is no longer the game file", after != original)
    check("the write reports how many steps are available", r.get("undo") == 1, r)

    st = app.session_info()
    check("the header knows one step back", st["undo"] == 1 and st["redo"] == 0, st)

    u = app.undo()
    check("撤回 succeeded", u.get("ok") is True, u)
    back = bytes(app.session_raw())
    check("the buffer is byte-identical with the game file again",
          back == original,
          "%d bytes differ" % sum(1 for a, b in zip(back, original) if a != b))
    hp = [f for f in app.unit_fields(74, civ="British")["fields"]
          if f["name"] == "HitPoints"][0]["value"]
    check("the decoded value is the old number", hp == 40, hp)
    check("there is nothing left to take back", app.session_info()["undo"] == 0)

    rd = app.redo()
    check("重做 succeeded", rd.get("ok") is True, rd)
    check("the buffer is the edited file again", bytes(app.session_raw()) != original)
    hp2 = [f for f in app.unit_fields(74, civ="British")["fields"]
           if f["name"] == "HitPoints"][0]["value"]
    check("the decoded value is the new number", hp2 == 99, hp2)

    print("\n=== 7. one gesture, one step (63 civilisations) ===")
    app.reset_session()
    check("放弃 empties the history",
          app.session_info()["undo"] == 0 and app.session_info()["redo"] == 0)
    many = app.set_unit_field(74, "HitPoints", value=88, civ="*", dry=False)
    check("the blanket write touched every copy",
          many.get("ok") and (many.get("copies_changing") or 0) > 1, many)
    check("... and it is ONE step, not one per copy",
          app.session_info()["undo"] == 1, app.session_info()["undo"])
    app.undo()
    check("one 撤回 took every copy back",
          bytes(app.session_raw()) == original,
          "the blanket write did not collapse into one step")

    print("\n=== 8. an edit after 撤回 ends the old future ===")
    app.reset_session()
    app.set_unit_field(74, "HitPoints", value=99, dry=False)
    app.undo()
    check("there is a branch to redo", app.session_info()["redo"] == 1)
    app.set_unit_field(74, "HitPoints", value=77, dry=False)
    check("the redo tail is gone", app.session_info()["redo"] == 0)
    wait = app.redo()
    check("重做 refuses instead of inventing a step", wait.get("ok") is False, wait)
    check("... and it says why in a sentence the player can act on",
          "重做" in str(wait.get("error")), wait)

    print("\n=== 9. four record spaces, one way back ===")
    app.reset_session()
    base = bytes(app.session_raw())
    tech = app.tech_fields(22)
    tname = [f["name"] for f in tech["fields"] if f["name"].startswith("ResourceCosts")
             and f["name"].endswith("Amount")]
    tname = tname[0] if tname else tech["fields"][2]["name"]
    app.set_tech_field(22, tname, value=2, dry=False)
    app.undo()
    check("a technology edit undoes", bytes(app.session_raw()) == base)

    rows = app.effect_rows(22)
    check("the effect list was read", bool(rows.get("ok")) and rows.get("rows"), rows.get("ok"))
    app.set_effect_value(22, 0, value=5, dry=False)
    app.undo()
    check("an effect command undoes", bytes(app.session_raw()) == base,
          "effect writes are at a different offset width")

    app.set_table_field("terrain", 1, "BlendPriority", 200, dry=False)
    app.undo()
    check("a table field undoes", bytes(app.session_raw()) == base)

    print("\n=== 10. the history is bounded and the label is readable ===")
    app.reset_session()
    for v in (11, 12, 13):
        app.set_unit_field(74, "HitPoints", value=v, dry=False)
    st = app.session_info()
    check("three writes are three steps", st["undo"] == 3, st["undo"])
    check("the pending list still merges to ONE row per field",
          st["pending"] == 1, st["pending"])
    check("the label names the field", st["undo_label"] == "生命值", st["undo_label"])
    check("the oldest value is still the one reported",
          st["edits"][0]["was"] == 40, st["edits"][0].get("was"))
    app.reset_session()
    return original


# ---------------------------------------------------------------- browser ----

def browser_checks(base):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:                             # pragma: no cover
        print("  SKIP playwright is not installed (%s)" % exc)
        return
    print("\n=== 11. the real page, at the real window size ===")

    def req(p, body=None, timeout=300):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(base + p, data=data,
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return json.loads(f.read().decode())

    req("/api/session-reset", {})

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True)
        page = br.new_page(viewport={"width": 1264, "height": 821})
        errs = []
        page.on("console",
                lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(base + "/?nocache=undo%d#editor" % os.getpid())
        page.wait_for_selector("#edcount", state="attached", timeout=240000)
        page.wait_for_function(
            "() => { const c = document.querySelector('#edcount');"
            " return c && c.textContent.indexOf('/') > 0; }", timeout=240000)

        check("with nothing changed the bar is hidden",
              page.eval_on_selector("#edpend", "e => e.hidden") is True)
        check("撤回 starts off", page.eval_on_selector("#ed-undo", "e => e.disabled") is True)
        check("重做 starts off", page.eval_on_selector("#ed-redo", "e => e.disabled") is True)

        w = page.evaluate("""async () => {
          const j = await api('/api/field-set',
            {unit: 74, field: 'HitPoints', value: 99, dry: false});
          edSyncPending(j.pending, [{civ_all: !!j.civ_all, copies: j.copies || 1}], j);
          return j;
        }""")
        check("the write went through the page", w.get("ok") is True, w)
        check("the bar appeared", page.eval_on_selector("#edpend", "e => e.hidden") is False)
        check("撤回 turned on", page.eval_on_selector("#ed-undo", "e => !e.disabled") is True)
        check("重做 is still off",
              page.eval_on_selector("#ed-redo", "e => e.disabled") is True)
        check("the button says what it will take back",
              "生命值" in page.eval_on_selector("#ed-undo", "e => e.title"),
              page.eval_on_selector("#ed-undo", "e => e.title"))

        page.click("#ed-undo")
        page.wait_for_timeout(1200)
        st = req("/api/session-info")
        check("the button undid the step", st["undo"] == 0 and st["pending"] == 0, st)
        check("撤回 switched itself off",
              page.eval_on_selector("#ed-undo", "e => e.disabled") is True)
        check("重做 switched itself on",
              page.eval_on_selector("#ed-redo", "e => !e.disabled") is True)
        check("the bar is still up so 重做 is reachable",
              page.eval_on_selector("#edpend", "e => e.hidden") is False)
        check("Ctrl+Z does not raise the unsaved warning", st["dirty"] is False, st)

        page.eval_on_selector("#edlist", "n => n.click()")
        page.keyboard.press("Control+y")
        page.wait_for_timeout(1200)
        st = req("/api/session-info")
        check("Ctrl+Y redid the step", st["undo"] == 1 and st["pending"] == 1, st)
        page.keyboard.press("Control+z")
        page.wait_for_timeout(1200)
        st = req("/api/session-info")
        check("Ctrl+Z undid it again", st["undo"] == 0, st)

        # Typing into the mod-name box must not be hijacked: the browser's own
        # text undo has to win there, or one keystroke takes back a field while
        # the player is fixing a typo in a name.
        before = req("/api/session-info")["undo"]
        page.click("#ed-name")
        page.keyboard.press("Control+z")
        page.wait_for_timeout(700)
        after = req("/api/session-info")["undo"]
        check("Ctrl+Z inside a text box leaves the history alone",
              after == before, "%s -> %s" % (before, after))

        req("/api/field-set", {"unit": 74, "field": "HitPoints", "value": 88,
                               "dry": False})
        req("/api/session-reset", {})
        st = req("/api/session-info")
        check("放弃 clears both directions",
              st["undo"] == 0 and st["redo"] == 0, st)

        check("no console errors", not errs, errs[:3])
        br.close()


def main():
    static_checks()
    try:
        behaviour_checks()
    except Exception as exc:                               # noqa: BLE001
        check("the behaviour walk finished", False, repr(exc)[:300])
    try:
        proc, base = spawn_server()
    except Exception as exc:                               # noqa: BLE001
        print("\nSKIP: could not start the engine (%s)" % exc)
        proc, base = None, None
    if base:
        try:
            browser_checks(base)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except Exception:                              # noqa: BLE001
                proc.kill()

    print()
    if FAILS:
        print("UNDO REDO: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("UNDO REDO: BYTES GO BACK EXACTLY, ONE GESTURE IS ONE STEP, AND THE "
          "BRANCH ENDS WHEN A NEW EDIT STARTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

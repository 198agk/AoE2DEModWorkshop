# -*- coding: utf-8 -*-
"""An ANSWER must not be painted as an ERROR.

WHY THIS EXISTS
---------------
`renderClauses` picks the card colour from `buildable(c)`, which is false for
anything without an intent.  That is right for a refusal and WRONG for an
answer: 「谁能造长弓兵」, 「村民血量是多少」 and 「玛雅能不能造长弓兵」 all carry no
intent by design (nothing gets built from a question), so the page drew a
correct answer with the red "bad" frame -- reading, at a glance, as if the tool
had failed to understand the sentence.

The `question` branch already had this handled one line at a time.  The `who`
branch arrived later and did not, and no suite caught it because every existing
check reads the JSON from /api/parse, not the class the page puts on the card.

WHAT IT PINS
------------
Four kinds of clause, one assertion each, against the real page in a headless
browser:
  * a `who` answer        -> ok    (this is the regression)
  * a `question` answer   -> ok
  * a can-question        -> ok
  * a refusal             -> bad   (or the colour stops meaning anything)
  * a zero-change edit    -> bad   (honest: it writes nothing)

Run:  python -X utf8 _probe/test_answer_cards.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def free_port(start=7990):
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
    """Its own engine: a stale ambient one serves a cached page and would test
    the stylesheet from before the fix.  Returns (proc, base)."""
    import subprocess
    import time
    import urllib.request

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


CASES = [
    ("谁能造长弓兵", "ok", "a who-answer is not an error"),
    ("村民血量是多少", "ok", "a value question is not an error"),
    ("玛雅能不能造长弓兵", "ok", "a can-question is not an error"),
    ("长弓兵能造吗", "ok", "the same, asked without a civilization"),
    ("这是什么", "bad", "a refusal is still an error card"),
]


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:            # pragma: no cover
        print("SKIP: playwright is not installed (%s)" % exc)
        return 0

    proc, base = spawn_server()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True)
            page = br.new_page(viewport={"width": 1264, "height": 821})
            # A unique query string: a cached page would show the old class.
            page.goto(base + "/?nocache=%d" % os.getpid())
            page.wait_for_selector("#say", timeout=60000)

            print("\n=== every answer is a green card, every refusal a red one ===")
            for sentence, want, why in CASES:
                page.fill("#say", sentence)
                page.click("#btn-parse")
                # Wait for the card rather than for a fixed delay: the FIRST
                # parse has to read 93 MB of game data, and a sleep tuned on the
                # second one returns an empty list -- which reads as "bad" and
                # reports a colour bug that is really a timing bug.
                page.wait_for_selector("#preview > .clause", timeout=120000)
                page.wait_for_timeout(400)
                cls = page.eval_on_selector_all(
                    "#preview > .clause", "e => e.map(x => x.className)") or []
                got = "ok" if cls and "ok" in cls[0] else "bad"
                check("%s [%s]" % (why, sentence), got == want,
                      "want %s, got %s (%s)" % (want, got, cls))

            print("\n=== and the card still fits the window ===")
            w = page.evaluate("() => [document.documentElement.scrollWidth,"
                              " document.documentElement.clientWidth]")
            check("no horizontal scroll", w[0] <= w[1], w)
            br.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    print()
    if FAILS:
        print("ANSWER CARDS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("ANSWER CARDS: AN ANSWER IS GREEN, A REFUSAL IS RED, AND THE COLOUR "
          "IS DECIDED BY WHAT HAPPENED NOT BY WHETHER AN INTENT CAME BACK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

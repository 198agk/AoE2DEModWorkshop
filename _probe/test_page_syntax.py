# -*- coding: utf-8 -*-
"""The whole product is one inline <script>, so one bad string is a blank page.

WHY THIS PIN EXISTS
-------------------
`aoe2mod/ui/static/index.html` carries ~6,000 lines of JavaScript inside a single
`<script>` tag.  A syntax error anywhere in it does not degrade one feature: the
browser refuses the entire script, so the nav stops working, the editor list stays
empty, and the page looks like a server that did not answer.

Measured 2026-11-05, while adding the record buttons.  A rewrite put a raw
newline inside a string literal:

    window.confirm(e.message + "

    还是要删吗？")

and the result was `pageerror :: Invalid or unexpected token`, `#edlist` with 0
rows, and a Playwright probe that sat on `wait_for_function` for 180 seconds
before timing out.  Twelve suites in the fast set load that page; NONE of them
reports "the file does not parse", because each one waits for something and then
blames the wait.  That is the same shape as the pendulum in
`_probe/test_pages_shipped.py`: a pin that reports a timeout sends the reader to
look at a timeout.

WHAT IT CHECKS
--------------
1. every inline `<script>` in the page parses as JavaScript (`node --check` on
   the extracted text, through a temp file, because `--check` reads a path);
2. the page has exactly ONE such script -- the count this pin's own extraction
   depends on, and a second block that nobody extracts is a second blind spot;
3. the syntax check is not vacuous: the extracted text is large, mentions
   `loadEditor`, and contains no `</script>` splice;
4. the same check runs on the other hand-written page in the tree
   (`desktop/`'s shell page) when `node` is available.

WHAT IT DOES NOT DO
-------------------
It does not execute the script (that is what the browser pins are for), and it
does not lint it: a valid program that does the wrong thing is not this pin's
business.  When `node` is missing it reports that instead of passing, because a
skipped syntax check that prints "ok" is worse than no check.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")

FAILS = []


def ck(name, ok, detail=""):
    if ok:
        print("  ok   %s" % (name,))
    else:
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))
        FAILS.append(name)


def section(title):
    print("\n=== %s ===" % (title,))


def scripts(html):
    """The body of every inline `<script>` with no `src` attribute."""
    out = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", html, re.S):
        attrs, body = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs):
            continue
        out.append(body)
    return out


NODE = shutil.which("node")


def syntax_error(source):
    """`None` when the text parses, else node's own first line of complaint."""
    if not NODE:
        return "node is not on PATH, so nothing was checked"
    fd, path = tempfile.mkstemp(suffix=".js", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(source)
        p = subprocess.run([NODE, "--check", path],
                           capture_output=True, text=True, timeout=180)
        if p.returncode == 0:
            return None
        # node prints a stack with the temp path; the message is the last line.
        lines = [ln for ln in (p.stderr or "").strip().splitlines() if ln.strip()]
        return lines[-1] if lines else "node --check failed silently"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


section("1. the page's script parses")
html = io.open(PAGE, encoding="utf-8").read()
bodies = scripts(html)
print("   %d inline script(s), node %s" % (len(bodies), NODE or "MISSING"))
ck("node is available, so this pin can actually check something", bool(NODE),
   "install Node.js or this pin proves nothing")
ck("the page has exactly one inline script", len(bodies) == 1, len(bodies))
for i, body in enumerate(bodies):
    err = syntax_error(body)
    ck("inline script #%d parses as JavaScript" % (i,), err is None, err)

section("2. the check is not vacuous")
big = max(bodies, key=len) if bodies else ""
ck("the extracted text is the size of the page's own script",
   len(big) > 150000, len(big))
ck("it is the editor's script, not a stub", "loadEditor" in big and "api(" in big)
ck("the extraction did not stop at an escaped `</script>`",
   "</script" not in big.lower())

section("3. the same check on every other hand-written page")
# `_cache` holds copies of this tree from earlier builds; `_out` holds the shipped
# bundle, which is the same file `sync_app_package` copies.  Neither is a source,
# and checking them would report the same page four times.
SKIP = (".git", "node_modules", "target", "__pycache__", "_out", "_probe",
        "runtime", "_cache", "_age_analysis", "_golden")
others = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for name in files:
        if name.endswith(".html"):
            others.append(os.path.join(base, name))
scanned = 0
with_script = 0
for path in sorted(others):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    bodies = scripts(text)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    scanned += 1
    if not bodies and rel != "aoe2mod/ui/static/index.html":
        print("   %s: no inline script" % (rel,))
        continue
    with_script += 1
    for i, body in enumerate(bodies):
        err = syntax_error(body)
        ck("%s script #%d parses" % (rel, i), err is None, err)
ck("the walk found the page in the source tree, not only in a cache",
   scanned >= 1 and with_script >= 1, (scanned, with_script))

print("")
if FAILS:
    print("PAGE SYNTAX: %d CHECK(S) FAILED -- %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("PAGE SYNTAX: EVERY INLINE SCRIPT IN THE TREE PARSES, SO A BROKEN STRING "
      "FAILS HERE IN A SECOND INSTEAD OF BECOMING A BLANK PAGE AND A 180-SECOND TIMEOUT")

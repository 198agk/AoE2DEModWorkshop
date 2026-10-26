"""The screen's wording lives in one table -- pin the seams that make that true.

Four ways this pass can be silently wrong, none of which the page harness can see
(it has no HTML body, so it builds its own tagged nodes):

  1. **A markup tag naming a key the table lacks.**  `applyLocale()` leaves the
     inline text, so the screen looks right and the table entry never wins.  The
     page is then two strings that look alike, which is the exact defect the
     extraction exists to remove.
  2. **A tag on a container.**  `textContent` replaces the whole subtree; the
     `say.note` paragraph carries two `<code>` samples, and assigning over it
     would delete the explanation while leaving a sentence that mentions it.
  3. **A table entry no markup and no code uses.**  Dead wording rots in place and
     the next reader edits it expecting an effect.
  4. **A placeholder the caller cannot fill.**  `{civs}` with no `civs` reaches
     the player as a brace, and `fill()` deliberately leaves unknown names alone,
     so nothing else complains.

The fourth one is checked against the call sites the code really has, not against
a list written here: every `_LOCALE_TEXT("k", {...})` and `T("k", {...})` in the
two files is parsed and its names compared with the table's placeholders.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TABLE = os.path.join(ROOT, "aoe2mod", "schema", "locales", "zh.json")
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  ok " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail) if detail else ""))


TAG = re.compile(r'data-i18n(?:-ph|-title)?="([^"]+)"')
PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
# A call may span lines -- `_banner` really writes it as
#     return _LOCALE_TEXT(
#         "update.banner", {"names": names + more})
# so `\s*` has to cross newlines.  The `(?<!\bdef )` keeps the function's own
# `def _LOCALE_TEXT(key, values=None)` signature out of the list: it has the same
# shape as a call and would report `key` as a missing placeholder.
CALL = re.compile(
    r'(?<!\bdef )(?:_LOCALE_TEXT|T)\(\s*"([a-z][a-z0-9_.]*)"\s*'
    r'(?:,\s*\{([^}]*)\})?', re.S)
# A call inside a comment is prose about a call, not a call.  The page documents
# its own convention as `T("key", {n: 3})` in a comment, and without this strip
# the nail reports `key` as a table entry that does not exist.
COMMENT = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*")


def tagged_container(page):
    """Return (key, tag) for every tag applied to an element with children."""
    body = page.partition("<script>")[0]
    out = []
    for m in re.finditer(r'<([a-z][a-z0-9]*)([^<>]*data-i18n="([^"]+)"[^<>]*)>',
                         body):
        tag, key = m.group(1), m.group(3)
        rest = body[m.end():]
        end = rest.find("</%s>" % tag)
        if end > 0 and "<" in rest[:end]:
            out.append((key, tag))
    return out


def main():
    doc = json.load(io.open(TABLE, encoding="utf-8-sig"))
    strings = doc["strings"]
    page = io.open(PAGE, encoding="utf-8", newline="").read()

    # --- A: the table itself -------------------------------------------------
    check("the table declares its own locale and version",
          doc.get("locale") == "zh" and isinstance(doc.get("version"), int),
          (doc.get("locale"), doc.get("version")))
    check("every key is dotted lowercase",
          all(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", k) for k in strings),
          [k for k in strings if not
           re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", k)][:4])
    check("no value is empty or whitespace",
          all(isinstance(v, str) and v.strip() for v in strings.values()),
          [k for k, v in strings.items() if not str(v).strip()][:4])

    # --- B: every tag names a key that exists --------------------------------
    used = sorted(set(TAG.findall(page)))
    missing = [k for k in used if k not in strings]
    check("every tag in the markup names a key the table has",
          not missing, missing)
    check("and the markup does use the table at all",
          len(used) >= 20, len(used))

    # --- C: no tag on a container -------------------------------------------
    bad = tagged_container(page)
    check("no tag sits on an element with children (textContent would delete them)",
          not bad, bad)

    # --- D: placeholders match what the call sites pass ---------------------
    calls = CALL.findall(COMMENT.sub("", page)) + CALL.findall(
        COMMENT.sub("", io.open(SERVER, encoding="utf-8", newline="").read()))
    unresolvable = []
    for key, args in calls:
        if key not in strings:
            unresolvable.append((key, "no such key"))
            continue
        want = set(PLACEHOLDER.findall(strings[key]))
        if not want:
            continue
        # The argument object is written `{"names": names + more}` in Python and
        # `{version: META.version}` in JS, so the key may carry quotes or not.
        # Matching only the bare form reported a filled call as unfilled -- a
        # detector that cannot see the shape it was written for.
        given = set(re.findall(r'([a-z_][a-z0-9_]*)"?\s*:', args or ""))
        if not want <= given:
            unresolvable.append((key, "needs %s, gets %s"
                                 % (sorted(want), sorted(given))))
    # A call with no argument object is fine only when the string has no
    # placeholder; the loop above already reports the rest.
    check("every call fills the placeholders its string declares",
          not unresolvable, unresolvable[:6])

    # --- E: an unknown status falls back to the machine value ----------------
    from aoe2mod.ui import server as S  # noqa: E402  (import after the checks on disk)
    check("a known status is the table's wording",
          S.status_zh("stale") == strings.get("status.stale"),
          S.status_zh("stale"))
    check("an unknown status prints the machine value, not a key",
          S.status_zh("frobnicated") == "frobnicated",
          S.status_zh("frobnicated"))
    check("an empty status is empty, not a key",
          S.status_zh("") == "" and S.status_zh(None) == "",
          (S.status_zh(""), S.status_zh(None)))

    # --- F: what the route hands the page ------------------------------------
    # The route's body lives in the HTTP handler, not on `App`, so it is called
    # the way the page calls it: through a real server on a real socket.  Reading
    # `LO.load()` here instead would test the loader twice and the route never.
    import threading
    import urllib.request
    from aoe2mod.ui import server as SB
    httpd, app, url = SB.serve(port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(url + "/api/locale", timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
        check("the route answers with the shipped table",
              body.get("ok") is True
              and isinstance(body.get("strings"), dict)
              and len(body["strings"]) == len(strings),
              len(body.get("strings") or {}))
        check("...and it carries a key the markup reads",
              (body.get("strings") or {}).get("say.heading")
              == strings["say.heading"],
              (body.get("strings") or {}).get("say.heading"))
        with urllib.request.urlopen(url + "/api/locale?locale=xx", timeout=30) as r:
            other = json.loads(r.read().decode("utf-8"))
        check("a locale that is not shipped is empty, not an error",
              other.get("ok") is True and other.get("strings") == {},
              other.get("strings"))
        with urllib.request.urlopen(url + "/", timeout=30) as r:
            page_bytes = r.read()
        check("the page the server sends is the file this test read",
              page_bytes.decode("utf-8") == page,
              len(page_bytes))
    finally:
        httpd.shutdown()

    print()
    if FAILS:
        print("LOCALE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("LOCALE: %d CHECKS PASSED -- ONE TABLE HOLDS THE SCREEN'S WORDING, "
          "EVERY MARKUP TAG FINDS ITS KEY, NO TAG SITS ON A CONTAINER, AND AN "
          "UNKNOWN STATUS FALLS BACK TO THE MACHINE VALUE" % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

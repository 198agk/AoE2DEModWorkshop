"""The forms route answers, and its answers match the table on disk.

Two questions, and they are different:
  1. Does the route exist and answer with the shape the page reads?
  2. Are the forms it hands out the SAME forms the round-trip nail measured?

The second is the one worth writing down.  `test_compose_roundtrip.py` reads the
table straight off disk; the page reads it through this route.  If the route
filtered, re-sorted or re-labelled anything, the page could offer a form the nail
never checked -- and a form the reader refuses is invisible until someone clicks
it.
"""

import os
import sys
import threading
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.ui import compose as CP  # noqa: E402
from aoe2mod.ui import server as S  # noqa: E402

FAILS = []
CHECKS = [0]


def check(name, cond, detail=""):
    CHECKS[0] += 1
    if cond:
        print("  ok   %s%s" % (name, "" if not detail else "  ::  " + str(detail)))
    else:
        FAILS.append(name)
        print("  FAIL %s%s" % (name, "" if not detail else "  ::  " + str(detail)))


def get(url):
    with urllib.request.urlopen(url, timeout=120) as resp:
        import json
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    httpd, app, base = S.serve(port=0)
    # `serve()` builds the server and hands back its URL; it does not run it.
    # Measured the hard way: without this thread the first `urlopen` blocks
    # forever and the nail writes 54 bytes before being killed -- which reads
    # exactly like a hang inside the route under test.
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        print("=== A. the route answers")
        st, body = get(base + "/api/forms")
        check("status is 200", st == 200, st)
        check("ok is true", body.get("ok") is True, body.get("ok"))
        check("it carries forms", bool(body.get("forms")), len(body.get("forms") or []))
        check("it carries the op words", body.get("op_choices"),
              body.get("op_choices"))

        print()
        print("=== B. the route hands out exactly the table on disk")
        disk = CP.forms()
        over_the_wire = body.get("forms") or []
        check("same count", len(over_the_wire) == len(disk),
              "%d vs %d" % (len(over_the_wire), len(disk)))
        _key = lambda f: (f.get("intent") or "", f.get("id") or "")  # noqa: E731
        check("same forms, same order",
              [_key(f) for f in over_the_wire] == [_key(f) for f in disk])
        _tpl = lambda rows: {_key(f): f.get("template") for f in rows}  # noqa: E731
        check("same templates", _tpl(over_the_wire) == _tpl(disk))

        print()
        print("=== C. filtering by intent works and is not a second table")
        _one = disk[0]["intent"]
        st, body2 = get(base + "/api/forms?intent=" + urllib.parse.quote(_one))
        check("status is 200", st == 200, st)
        _ids = {f["intent"] for f in body2.get("forms") or []}
        check("only that intent came back", _ids == {_one}, _ids)
        _want = [f for f in disk if f["intent"] == _one]
        check("and all of its forms", len(body2.get("forms") or []) == len(_want),
              "%d vs %d" % (len(body2.get("forms") or []), len(_want)))

        print()
        print("=== D. an unknown intent is empty, not an error")
        st, body3 = get(base + "/api/forms?intent=unit.no_such_intent")
        check("status is 200", st == 200, st)
        check("ok stays true", body3.get("ok") is True, body3.get("ok"))
        check("no forms", body3.get("forms") == [], body3.get("forms"))
    finally:
        httpd.shutdown()

    print()
    if FAILS:
        print("FORMS ROUTE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("FORMS ROUTE: %d CHECKS PASSED -- THE PAGE GETS THE SAME FORMS THE "
          "ROUND-TRIP NAIL MEASURED, AND AN UNKNOWN INTENT IS EMPTY RATHER THAN AN ERROR"
          % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

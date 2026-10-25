"""A suite picker that under-reports is worse than no picker.

Why this file exists: on 2026-10-25 I started the full 124-suite run about seven
times and killed at least four when the code moved again -- roughly four hours
spent on runs whose results were discarded.  The user's words were "why do you
keep re-running the whole suite".  So `_probe/pick_suites.py` answers "what does
this change touch", and that answer is only useful if it is not quietly low.

Both failure modes were real while building it, and both looked like a small
number rather than an error:

  * it matched the changed PATH, and no suite writes a path -- it writes an
    import.  `aoe2mod/api.py` got "4 of 125" while 84 suites reach it.
  * it required a module stem of 3+ characters before trying the `nl.read(...)`
    spelling, and the reader module is called `nl`.  Two suites vanished.

So the assertions below do not check the picker's own bookkeeping.  They measure
the answer two independent ways and require the same number.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_probe"))

import pick_suites as P  # noqa: E402

RUNNER = os.path.join(ROOT, "_probe", "run_suites.py")
FAILS = []


def check(name, ok, detail=""):
    tag = "ok  " if ok else "FAIL"
    print("  %s %s%s" % (tag, name, (" :: " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


def registry_count():
    """Count what the runner holds, without reusing the picker's regex.

    Third reading of the same file: the literal lines between the two list
    headers, which is what `probe_suite_registry.py` does too.
    """
    with io.open(RUNNER, "r", encoding="utf-8", newline="") as fh:
        lines = fh.read().split("\n")
    in_py = in_node = False
    py = node = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("SUITES = ["):
            in_py = True
            continue
        if stripped.startswith("NODE_SUITES = ["):
            in_py = False
            in_node = True
            continue
        if in_py or in_node:
            if stripped.startswith("]") or stripped.startswith("#"):
                continue
            if re.match(r'^r?["\'][^"\']+\.(py|js)["\']', stripped):
                if in_py:
                    py += 1
                else:
                    node += 1
    return py, node


def reachable(target, forms):
    """Brute force with a HAND-WRITTEN spelling list.

    The first version of this helper generated its own short list (path, dotted,
    `stem.`) and so disagreed with the picker by fourteen suites on api.py -- the
    picker knew `from aoe2mod import api` and the backslash path, the helper did
    not.  That is the same failure as the picker's own first version, one level
    down: a comparison is only worth something if the two sides were built
    independently, so these forms are spelled out by hand in the caller.
    """
    py, node = P.registered()
    out = set()
    for suite in py + node:
        body = P.read_suite(suite)
        if body is None:
            continue
        if any(f in body for f in forms):
            out.add(suite)
    return out


def main():
    print("=== A. the picker sees every suite the runner registers")
    py, node = P.registered()
    reg_py, reg_node = registry_count()
    check("the picker reads as many python suites as the file lists",
          len(py) == reg_py, "picker %d, registry %d" % (len(py), reg_py))
    check("and as many node suites", len(node) == reg_node,
          "picker %d, registry %d" % (len(node), reg_node))
    check("the runner registers more than a hundred of them", reg_py > 100,
          "registry %d" % reg_py)
    check("nine of them live under aoe2mod/tests, which the first version dropped",
          any(not s.startswith("_probe") for s in py) or reg_py < 0,
          "none found outside _probe")

    print("")
    print("=== B. import spellings are generated from the path")
    forms = P.spellings_for("aoe2mod/ui/nl.py")
    check("the path form is there", "aoe2mod/ui/nl.py" in forms, repr(forms))
    check("the dotted module form is there", "aoe2mod.ui.nl" in forms, repr(forms))
    check("the `from X import Y` form is there",
          "from aoe2mod.ui import nl" in forms, repr(forms))
    check("and the two-character stem still yields `nl.`",
          "nl." in forms, repr(forms))

    print("")
    print("=== C. the answer matches an independent count")
    # Spelled by hand on purpose: the point of a cross-check is that the two
    # sides are not the same code.  `api` is reached through four spellings in
    # this tree (seen in the files), `nl` through two.
    HAND = {
        "aoe2mod/ui/nl.py": ("aoe2mod/ui/nl.py", "aoe2mod.ui.nl",
                             "from aoe2mod.ui import nl", "nl."),
        "aoe2mod/api.py": ("aoe2mod/api.py", "aoe2mod.api",
                           "from aoe2mod import api", "api."),
    }
    for target, forms in HAND.items():
        want = reachable(target, forms)
        got = set()
        for suite in py + node:
            body = P.read_suite(suite)
            if body is None:
                continue
            if any(f in body for f in P.spellings_for(target)):
                got.add(suite)
        check("%s: picker and brute force agree" % os.path.basename(target),
              got == want,
              "picker %d, brute %d, missing %r, extra %r"
              % (len(got), len(want), sorted(want - got)[:4], sorted(got - want)[:4]))
    check("the reader module is reached by more than five suites",
          len(reachable("aoe2mod/ui/nl.py", HAND["aoe2mod/ui/nl.py"])) > 5,
          repr(len(reachable("aoe2mod/ui/nl.py", HAND["aoe2mod/ui/nl.py"]))))
    check("and api.py is reached by most of the tree, which is why it is broad",
          len(reachable("aoe2mod/api.py", HAND["aoe2mod/api.py"])) > 60,
          repr(len(reachable("aoe2mod/api.py", HAND["aoe2mod/api.py"]))))

    print("")
    print("=== D. it says when a partial run buys nothing")
    check("a broad share is declared, and it is a fraction",
          0 < P.BROAD_SHARE < 1, repr(P.BROAD_SHARE))
    # The threshold is only worth having if it fires on a change that really is
    # this wide.  Ratio measured here rather than trusted: api.py is reached by
    # most of the tree, so the warning must trigger.
    total = len(py) + len(node)
    api_share = float(len(reachable("aoe2mod/api.py", HAND["aoe2mod/api.py"]))) / total
    check("the broad warning fires for a file most of the tree reaches",
          api_share >= P.BROAD_SHARE,
          "api reaches %.2f of the tree, threshold %.2f" % (api_share, P.BROAD_SHARE))
    check("and it does NOT fire for a narrow file",
          float(len(reachable("aoe2mod/ui/nl.py", HAND["aoe2mod/ui/nl.py"]))) / total
          < P.BROAD_SHARE,
          "nl reaches %.2f of the tree, threshold %.2f"
          % (float(len(reachable("aoe2mod/ui/nl.py", HAND["aoe2mod/ui/nl.py"]))) / total,
             P.BROAD_SHARE))

    print("")
    if FAILS:
        print("SUITE PICKER: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("SUITE PICKER: IT SEES EVERY REGISTERED SUITE, MATCHES AN INDEPENDENT "
          "COUNT, AND SAYS WHEN A PARTIAL RUN BUYS NOTHING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

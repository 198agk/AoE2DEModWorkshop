"""Which suites does this change actually touch?

Why this exists: on 2026-10-25 the full 124-suite run took ~75 minutes and I
started it about seven times, killing at least four when the code moved again --
roughly four hours spent on runs whose results were then discarded.  The user's
words were "why do you keep re-running the whole suite".  The rule "run the whole
thing only on a frozen tree" is not enough on its own, because deciding which
suites a change touches was done by memory, and memory is what produced the
wasted hours.

Why it matches the way it does: the first version matched the changed PATH
(`aoe2mod/api.py`) and answered "4 of 125 suites".  Measured, the same file is
named by `import aoe2mod.api` in 62 suites and reached by 84 once the
`from aoe2mod import api` spelling is counted -- because no suite ever writes a
path, it writes an import.  A tool that answers "run 4" when 84 move is worse
than no tool: it manufactures confidence.  So the matcher works from the module
spelling, and it prints the measured basis of each hit rather than a bare count.

What it does NOT do: prove the set is complete.  A suite that reaches a file
through a helper (or a probe that builds its own path from a string) is still
invisible, and a suite that imports a widely used module is listed even when the
edit is irrelevant to it.  So the honest use is "these plus the registry check";
the full run stays the thing that proves a tree, not the thing that finds out
what to run.

    python _probe/pick_suites.py                 # whatever git says changed
    python _probe/pick_suites.py aoe2mod/ui/nl.py
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "_probe", "run_suites.py")

# Touching one of these moves most of the tree.  The threshold is measured, not
# felt: `aoe2mod/api.py` is reached by 84 of 125 suites, `aoe2mod/ui/nl.py` by 10.
BROAD_SHARE = 0.25


def registered():
    """The suite paths the runner holds, plus the node ones.

    Nine entries live under `aoe2mod/tests/` rather than `_probe/`, so matching
    only `_probe\\...` silently dropped them (the picker said 3 of 116 while the
    registry said 124).
    """
    with io.open(RUNNER, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    start = text.index("SUITES = [")
    end = text.index("NODE_SUITES")
    py = re.findall(r'r"([^"]+\.py)"', text[start:end])
    node = re.findall(r'r"([^"]+\.js)"', text[end:])
    return [p.replace("\\", os.sep) for p in py], [p.replace("\\", os.sep) for p in node]


def changed():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    paths = []
    for line in out.stdout.decode("utf-8", "replace").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        paths.append(path.replace("/", os.sep))
    return paths


def spellings_for(rel):
    """Every way a suite could name this file, derived from its path.

    `aoe2mod/api.py`       -> path form, `aoe2mod.api`,
                              `from aoe2mod import api`
    `aoe2mod/ui/nl.py`     -> path form, `aoe2mod.ui.nl`,
                              `from aoe2mod.ui import nl`, `nl.read`, `nl.`
    `_probe/test_x.py`     -> only the path form: nothing imports a probe.
    """
    norm = rel.replace(os.sep, "/")
    out = [norm, norm.replace("/", "\\")]
    if not norm.endswith(".py") or "/" not in norm:
        return out
    parts = norm[:-3].split("/")
    if parts[-1] in ("__init__",):
        return out
    stem = parts[-1]
    dotted = ".".join(parts)
    out.append(dotted)
    if len(parts) >= 2:
        out.append("from %s import %s" % (".".join(parts[:-1]), stem))
    if len(parts) >= 3:
        out.append("from .%s import %s" % (".".join(parts[1:-1]), stem))
    # `nl.read(...)`, `nl.Vocabulary` -- a suite that uses the module it imported.
    # The length floor used to be 3, which silently dropped `nl.` and cost two
    # suites (test_ai_entry, test_screen_reach) -- measured 2026-10-25.
    if len(stem) >= 2:
        out.append(stem + ".")
    return out


def read_suite(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return None
    with io.open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read()


def main(argv):
    py, node = registered()
    everything = py + node
    paths = argv[1:] or changed()
    if not paths:
        print("nothing changed (git status is clean) -- nothing to run")
        return 0

    print("changed (%d):" % len(paths))
    for p in paths:
        print("  " + p)

    bodies = {s: read_suite(s) for s in everything}
    basis = {}
    for rel in paths:
        forms = spellings_for(rel)
        for suite, body in bodies.items():
            if body is None:
                continue
            for f in forms:
                if f in body:
                    basis.setdefault(suite, []).append("%s<-%s" % (rel, f))
                    break

    print("")
    print("suites that reach a changed file, and how:")
    for suite in everything:
        if suite in basis:
            print("  %-46s %s" % (suite, ", ".join(basis[suite])))

    total = len(everything)
    n = len(basis)
    print("")
    print("=> %d of %d suites (%d py + %d node)" % (n, total, len(py), len(node)))
    if total and float(n) / total >= BROAD_SHARE:
        print("")
        print("That is %.0f%% of the tree, so the honest answer is: run the whole"
              % (100.0 * n / total))
        print("thing on a frozen tree.  A partial run this wide buys nothing.")
    print("")
    print("always also run: _probe\\probe_suite_registry.py (it catches a test_*.py")
    print("that no runner names, which no other suite can see)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

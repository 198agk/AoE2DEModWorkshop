# -*- coding: utf-8 -*-
"""Count the registered suites and name any probe nobody runs.

A registration list is a hand-maintained thing, so it drifts.  This prints the
count and, more usefully, the `test_*.py` files present in `_probe/` that no
runner names -- the same defect that let ten probes rot unrun before.

Four files are named `test_*.py` but are MEASUREMENTS, not assertions: they print
what they saw and exit 0 whether the news is good or bad.  Registering one in a
runner would add a suite that cannot fail -- exactly the "green pin telling the
opposite story" shape this project spent a round removing.  They are declared
below WITH the reason, and the reason is required: a newly orphaned test still
fails this probe, so the exemption list cannot quietly absorb the next one.
"""
import ast
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: path -> why this file is a measurement rather than a regression pin.  Every
#: entry must also say where its CONCLUSION lives, because a one-off dump with no
#: recorded conclusion is a file nobody can act on.
_NOT_A_SUITE = {
    r"_probe\datparse\test_random_maps.py":
        "prints the RandomMap record widths against genieutils and a synthetic "
        "round-trip; exits 0 either way.  Its conclusion (all five shipped "
        "datasets have count 0, so the reader/writer have no real data to fight) "
        "is recorded in 数据模组能力目录v1.md.",
    r"_probe\schema\test_branch_extract.py":
        "regenerates regen_preview.json so a human can read what the AGE branch "
        "extractor saw; the checked-in tables beside it are built from that "
        "preview.  It has no pass/fail question to ask.",
}


def _list_body(text, opener):
    """Return the entries of a module-level list literal, via the parser.

    Earlier versions split on `]` (wrong: a `]` inside a comment truncated the list,
    2026-10-25) and then scanned quotes by hand (also wrong: comments are not quoted,
    so an apostrophe in prose opened a string that never closed).  The file is Python;
    parse it.
    """
    name = opener.replace(" = [", "").strip()
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    names = [elt.value for elt in node.value.elts
                             if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
                    return "\n".join(names)
    raise ValueError("no module-level %s = [...] found" % name)


def named_in(path):
    try:
        text = io.open(path, encoding="utf-8").read()
    except IOError:
        return set()
    return set(re.findall(r"([\w./\\-]+\.py)", text))


def _drop_ignored(paths):
    """Remove paths git ignores; they are scratch, not part of the repo."""
    if not paths:
        return set()
    # git wants forward slashes on the command line even on Windows; a
    # backslashed path is read as an escape and silently matches nothing.
    slash = {p: p.replace("\\", "/") for p in paths}
    try:
        # `-z`: without it git C-quotes every path it echoes back
        # ("_probe/_tmp/..." with literal quotes), and a naive comparison then
        # matches nothing -- the filter would look like it ran and remove zero.
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"],
            cwd=ROOT, input="\0".join(sorted(slash.values())),
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return set(paths)
    if proc.returncode not in (0, 1):
        return set(paths)
    ignored = {ln.strip().replace("\\", "/") for ln in proc.stdout.split("\0") if ln.strip()}
    return {p for p in paths if slash[p] not in ignored}


def main():
    fast = os.path.join(HERE, "run_suites.py")
    slow = os.path.join(HERE, "run_long.py")
    fast_text = io.open(fast, encoding="utf-8").read()
    entries = [e for e in _list_body(fast_text, "SUITES = [").splitlines() if e]
    print("run_suites.py registers %d suites" % len(entries))

    # The page's script is exercised from Node, not from Python -- a Python test
    # can only read the file, and reading it is what let two page defects ship.
    # Those suites are registered in a second list, so count them here too or the
    # registry would under-report what a full run actually covers.
    node_body = ""
    if "NODE_SUITES = [" in fast_text:
        node_body = _list_body(fast_text, "NODE_SUITES = [")
    node_entries = [e for e in node_body.splitlines() if e]
    print("run_suites.py additionally registers %d node suites" % len(node_entries))

    dupes = [e for e in set(entries) if entries.count(e) > 1]
    print("duplicates: %s" % (dupes or "none"))

    registered = named_in(fast) | named_in(slow)
    found = set()
    for dirpath, _dirs, files in os.walk(HERE):
        if os.path.basename(dirpath) == "team":
            continue
        for fn in files:
            if fn.startswith("test_") and fn.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                found.add(rel.replace(os.sep, "\\"))
    # Only what the repository ships counts as coverage.  Since 2026-11-18
    # `_probe/*` is git-ignored except for an allow-list, so a working tree
    # still holds scratch copies (`_probe/_tmp/_pylib/numpy/**` alone carries
    # 191 `test_*.py` files nobody wrote) that no clone would ever see.
    # Asking git which paths are ignored keeps this gate about the repo, not
    # about whatever a probe happened to download last week.
    present = _drop_ignored(found)

    missing_file = [e for e in entries + node_entries
                    if not os.path.exists(os.path.join(ROOT, e))]
    print("registered but not on disk: %s" % (missing_file or "none"))

    # A harness nobody runs is the same defect as a probe nobody runs: it reads
    # like coverage and provides none.  `_probe/*.js` is a small enough set that
    # this can just name them.
    js_present = sorted(f for f in os.listdir(HERE) if f.endswith(".js"))
    js_unrun = [f for f in js_present
                if not any(e.endswith(f) for e in node_entries)]
    if js_unrun:
        print("\nUNREGISTERED .js HARNESS (%d): %s" % (len(js_unrun), js_unrun))

    registered_base = {os.path.basename(r) for r in registered}
    unrun = sorted(p for p in present
                   if os.path.basename(p) not in registered_base
                   and p not in _NOT_A_SUITE)
    excused = sorted(p for p in present
                     if os.path.basename(p) not in registered_base
                     and p in _NOT_A_SUITE)
    print("\n%d test_*.py files exist; %d are named by a runner"
          % (len(present), len(present) - len(unrun) - len(excused)))
    print("declared as measurements, not suites (%d):" % len(excused))
    for p in excused:
        print("  %s -- %s" % (p, _NOT_A_SUITE[p]))
    # An exemption for a file that is gone, or that a runner now names, is a
    # stale claim: it would keep excusing nothing while looking like it explains
    # something.  Same rule as the sweep's _VERIFIED_ELSEWHERE table.
    stale = sorted(p for p in _NOT_A_SUITE
                   if p not in present
                   or os.path.basename(p) in registered_base)
    if stale:
        print("\nSTALE EXEMPTIONS (drop them): %s" % stale)
        return 1
    if unrun:
        print("NOT NAMED BY ANY RUNNER (%d):" % len(unrun))
        for p in unrun:
            print("  %s" % p)
        return 1
    if js_unrun:
        return 1
    print("every test_*.py is either reachable from a runner or declared a "
          "measurement")
    return 0


if __name__ == "__main__":
    sys.exit(main())

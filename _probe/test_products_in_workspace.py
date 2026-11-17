# -*- coding: utf-8 -*-
"""PIN: every build product lives inside the checkout.

Why this is a file and not a habit
----------------------------------
The shipping bundle and the cargo build tree used to be written to two sibling
folders outside the repository, and twenty-odd probes each spelled those absolute
paths out by hand.  Two things went wrong, both of them real:

  * the workspace was not self-contained: `git clean`, a fresh clone, or moving
    the folder left the products behind, and probes then failed for a reason
    that had nothing to do with the code;
  * the folders outside the checkout did not carry the same Integrity Label as
    the ones inside, so a copied `python.exe` that ran fine out there died with
    0xC0000135 in here (2026-11-01, six hours of bisecting).

The owner's instruction was plain, twice: keep it in the workspace.  So the
paths live in exactly one module (`_probe/_paths.py`) and this pin holds the
line -- a probe that goes back to an absolute path fails here instead of
quietly writing to `C:\\` again.

Run: python -X utf8 _probe/test_products_in_workspace.py
"""
import ast
import io
import os
import re
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import _paths as P                                              # noqa: E402

# `ast.parse` warns about the invalid escapes a handful of old probes carry in
# docstrings (`\p`, `\765`).  Those warnings are about the FILES being scanned,
# not about this pin, and printing fifteen lines of them buries the report.
warnings.filterwarnings("ignore", category=SyntaxWarning)

FAILS = []
OKS = [0]


def check(name, ok, detail=""):
    if ok:
        OKS[0] += 1
        print("  ok   %s" % name)
    else:
        FAILS.append(name)
        print("  FAIL %s :: %s" % (name, detail))


def under_repo(path):
    a = os.path.normcase(os.path.abspath(path))
    b = os.path.normcase(os.path.abspath(ROOT))
    return a == b or a.startswith(b + os.sep)


def main():
    print("=== A. the three product paths are inside the checkout")
    for label, value in (("BUNDLE", P.BUNDLE), ("BUILD", P.BUILD),
                         ("EXE", P.EXE), ("BUNDLED_EXE", P.BUNDLED_EXE)):
        check("%s is inside the repository" % label, under_repo(value), value)
    check("the bundle is under _out", under_repo(os.path.join(ROOT, "_out"))
          and os.path.normcase(os.path.abspath(P.BUNDLE)).startswith(
              os.path.normcase(os.path.join(ROOT, "_out")) + os.sep), P.BUNDLE)
    check("the build tree is under _cache",
          os.path.normcase(os.path.abspath(P.BUILD)).startswith(
              os.path.normcase(os.path.join(ROOT, "_cache")) + os.sep),
          P.BUILD)

    print("=== B. both are gitignored, so a product cannot become a commit")
    gi = io.open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    check("_out/ is ignored", re.search(r"(?m)^_out/\s*$", gi) is not None)
    check("_cache/ is ignored", re.search(r"(?m)^_cache/\s*$", gi) is not None)

    print("=== C. no file in _probe still names an out-of-workspace product path")
    # The patterns are the shapes that were actually there, not a guess: the old
    # bundle, the old cargo tree, and the C:\\dsh-build tree.  Prose in a
    # docstring describing the move is fine; a code literal is not.
    banned = (
        re.compile(r"[A-Za-z]:[\\/]+Software[\\/]+AI[\\/]+AoE2ModWorkshop"),
        re.compile(r"[A-Za-z]:[\\/]+Software[\\/]+AI[\\/]+AGE2"),
        re.compile(r"[A-Za-z]:[\\/]+dsh-build"),
    )
    offenders = []
    scanned = 0
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs
                   if d not in ("__pycache__", "source", "_tmp", "_oneoff")]
        for f in sorted(files):
            if not f.endswith(".py") or f in ("_paths.py",
                                             "test_products_in_workspace.py"):
                continue
            path = os.path.join(root, f)
            scanned += 1
            try:
                tree = ast.parse(io.open(path, encoding="utf-8",
                                         errors="replace").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                # Only str CONSTANTS count: a comment or a docstring that
                # explains the move must not fail the pin.
                if not (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)):
                    continue
                for pat in banned:
                    if pat.search(node.value):
                        offenders.append("%s:%d" % (
                            os.path.relpath(path, ROOT), node.lineno))
                        break
    check("scanned a plausible number of probe files", scanned > 100, scanned)
    check("no probe carries an absolute product path", not offenders,
          offenders[:8])

    print("=== D. the products are where this pin says they are")
    check("the bundle folder exists", os.path.isdir(P.BUNDLE), P.BUNDLE)
    check("its exe ships", os.path.isfile(P.BUNDLED_EXE), P.BUNDLED_EXE)
    check("the build tree exists", os.path.isdir(P.BUILD), P.BUILD)
    check("the cargo release exe is there", os.path.isfile(P.EXE), P.EXE)
    # The reason the bundle had to move: the runtime launcher is a copied
    # python.exe, and where it sits decides whether Windows loads its sibling
    # VCRUNTIME140.dll or falls back to System32 and dies with 0xC0000135.
    rt = os.path.join(P.BUNDLE, "runtime", "python.exe")
    check("the bundled runtime launcher is inside the workspace", os.path.isfile(rt))
    check("and the app package sits beside it",
          os.path.isdir(os.path.join(P.BUNDLE, "app", "aoe2mod")))
    check("and it carries the stale-.dat stamp",
          os.path.isfile(os.path.join(P.BUNDLE, "app", "_golden",
                                      "dat_stamp.json")))

    print()
    if FAILS:
        print("PRODUCTS IN WORKSPACE: %d CHECK(S) FAILED -> %r"
              % (len(FAILS), FAILS))
        return 1
    print("PRODUCTS IN WORKSPACE: %d CHECKS PASSED -- every build product is "
          "inside the checkout, gitignored, and named in exactly one module"
          % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

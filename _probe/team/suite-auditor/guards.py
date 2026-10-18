# -*- coding: utf-8 -*-
"""Find blocks of check()/assert statements that sit behind a runtime guard
which can be false, so the checks silently never run (the suite still exits 0).

Reports: file, guard line, guard source, number of checks inside, and whether
there is an `else` that asserts the negation.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LIST = os.path.join(HERE, "suite_list.txt")

SKIP = ("", "None", "True")


def n_checks(node):
    n = 0
    for x in ast.walk(node):
        if isinstance(x, ast.Call):
            f = x.func
            nm = getattr(f, "attr", None) or getattr(f, "id", None)
            if nm in ("check", "_check"):
                n += 1
        elif isinstance(x, ast.Assert):
            n += 1
    return n


def guardish(test):
    """Does the guard depend on the environment rather than the product?"""
    src = ast.unparse(test)
    keys = ("isdir", "isfile", "exists", "listdir", "glob", "len(", "getsize",
            "environ", "platform", "isdir(", "which(")
    return any(k in src for k in keys)


def walk(body, rel, out):
    for st in body:
        if isinstance(st, ast.If):
            n = n_checks(ast.Module(body=st.body, type_ignores=[]))
            if n and guardish(st.test):
                has_else = bool(st.orelse)
                out.append((rel, st.lineno, ast.unparse(st.test)[:88], n,
                            has_else, n_checks(ast.Module(body=st.orelse,
                                                         type_ignores=[]))
                            if has_else else 0))
            walk(st.body, rel, out)
            walk(st.orelse, rel, out)
        elif isinstance(st, (ast.Try, ast.With)):
            walk(st.body, rel, out)
            for h in getattr(st, "handlers", []):
                walk(h.body, rel, out)
            walk(getattr(st, "finalbody", []), rel, out)
            walk(st.orelse if isinstance(st, ast.Try) else [], rel, out)
        elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            walk(st.body, rel, out)
        elif isinstance(st, (ast.For, ast.While)):
            walk(st.body, rel, out)
            walk(st.orelse, rel, out)


def main():
    paths = [ln.strip() for ln in open(LIST, encoding="utf-8") if ln.strip()]
    rows = []
    for rel in paths:
        p = os.path.join(ROOT, rel)
        src = open(p, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        out = []
        walk(tree.body, rel, out)
        rows.extend(out)
    print("%-40s %5s %5s %5s %s" % ("file", "line", "chk", "else", "guard"))
    for rel, ln, g, n, he, ne in rows:
        print("%-40s %5d %5d %5s %s"
              % (os.path.basename(rel), ln, n, ne if he else "-", g))
    print()
    print("guard-wrapped check blocks: %d in %d files"
          % (len(rows), len({r[0] for r in rows})))
    print("of those, with NO else branch: %d"
          % sum(1 for r in rows if not r[4]))


if __name__ == "__main__":
    main()

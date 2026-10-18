# -*- coding: utf-8 -*-
"""Rank every registered suite by how much evidence it emits, and find
suites whose success path can be reached without executing assertions.

Signals per suite:
  n_check      number of literal check(...)/assert statements in the source
  exit0_guards [ (line, guard_expr) ] guards that lead to sys.exit(0)
  skip_prints  lines that print SKIP
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LIST = os.path.join(HERE, "suite_list.txt")


def is_exit0(node):
    if not isinstance(node, ast.Expr):
        return False
    call = node.value
    if not isinstance(call, ast.Call):
        return False
    fn = call.func
    name = getattr(fn, "attr", None) or getattr(fn, "id", None)
    if name != "exit":
        return False
    return bool(call.args) and isinstance(call.args[0], ast.Constant) \
        and call.args[0].value == 0


def walk_guards(stmts, path):
    """Yield (line, guard_src, reached_exit0)."""
    out = []
    for st in stmts:
        if isinstance(st, ast.If):
            has0 = any(is_exit0(x) for x in ast.walk(ast.Module(body=st.body, type_ignores=[])))
            if has0:
                out.append((st.lineno, ast.unparse(st.test)[:90]))
            out.extend(walk_guards(st.body, path))
        elif isinstance(st, (ast.Try, ast.With)):
            out.extend(walk_guards(st.body, path))
            for h in getattr(st, "handlers", []):
                out.extend(walk_guards(h.body, path))
            out.extend(walk_guards(getattr(st, "finalbody", []), path))
        elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.extend(walk_guards(st.body, path))
        elif isinstance(st, ast.For):
            out.extend(walk_guards(st.body, path))
    return out


def count_checks(tree):
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name in ("check", "_check"):
                n += 1
    return n


def main():
    paths = [ln.strip() for ln in open(LIST, encoding="utf-8") if ln.strip()]
    print("%-44s %6s %7s  %s" % ("suite", "check", "lines", "exit-0 guards"))
    rows = []
    for rel in paths:
        p = os.path.join(ROOT, rel)
        src = open(p, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            print("%-44s SYNTAX %s" % (rel, e))
            continue
        g = walk_guards(tree.body, rel)
        rows.append((rel, count_checks(tree), src.count("\n"), g))
    for rel, n, nl, g in sorted(rows, key=lambda r: r[1]):
        gl = "; ".join("L%d %s" % (ln, s) for ln, s in g) if g else ""
        print("%-44s %6d %7d  %s" % (os.path.basename(rel), n, nl, gl[:80]))
    print()
    print("suites with a skip-to-green guard: %d"
          % sum(1 for r in rows if r[3]))
    print("suites with ZERO check() calls: %d"
          % sum(1 for r in rows if r[1] == 0))


if __name__ == "__main__":
    main()

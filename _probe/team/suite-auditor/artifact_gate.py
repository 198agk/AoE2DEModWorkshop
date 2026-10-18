# -*- coding: utf-8 -*-
"""Find suites whose whole body is gated on an artifact that may not exist, and
that exit 0 (green) when the artifact is absent.  Also report whether the
artifact is present on THIS machine -- an absent artifact proves the suite
cannot fail today.
"""
import ast
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def load_list():
    with open(os.path.join(HERE, "suite_list.txt"), encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def is_exit_zero(node):
    """sys.exit(0) / raise SystemExit(0) / return 0 inside main()."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        f = node.value.func
        nm = getattr(f, "attr", None) or getattr(f, "id", None)
        if nm == "exit" and node.value.args:
            a = node.value.args[0]
            if isinstance(a, ast.Constant) and a.value == 0:
                return True
    return False


def reachable_exit0(body):
    for st in body:
        if is_exit_zero(st):
            return True
        if isinstance(st, ast.If):
            for sub in st.body + st.orelse:
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    if is_exit_zero(sub):
                        return True
            if reachable_exit0(st.body) or reachable_exit0(st.orelse):
                return True
        if isinstance(st, ast.With):
            if reachable_exit0(st.body):
                return True
        if isinstance(st, ast.Try):
            if reachable_exit0(st.body) or reachable_exit0(st.orelse) or reachable_exit0(st.finalbody):
                return True
    return False


hits = []
for rel in load_list():
    full = os.path.join(ROOT, rel)
    if not os.path.isfile(full):
        continue
    with io.open(full, encoding="utf-8", errors="replace") as f:
        src = f.read()
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # does the guard test for existence?  isdir / isfile / exists
            seg = ast.get_source_segment(src, node.test) or ""
            if any(k in seg for k in ("isdir", "isfile", "exists", "Path(")) \
                    and reachable_exit0(node.body):
                found.append((node.lineno, " ".join(seg.split())[:70],
                              "exit0-in-guard"))
        if isinstance(node, ast.FunctionDef) and node.name in ("main",):
            if reachable_exit0(node.body):
                pass
    if found:
        hits.append((rel, found))

print("artifact-gated green exits: %d file(s)" % len(hits))
for rel, found in hits:
    print("\n%s" % rel)
    for ln, seg, kind in found:
        print("   %5d  %-6s  %s" % (ln, kind, seg))

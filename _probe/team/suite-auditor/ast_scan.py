# -*- coding: utf-8 -*-
"""AST scan of every registered suite + aoe2mod/tests for defect shapes.

Read-only. Prints one line per finding: file:line  KIND  snippet
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def load_list():
    p = os.path.join(HERE, "suite_list.txt")
    with open(p, encoding="utf-8") as f:
        names = [ln.strip() for ln in f if ln.strip()]
    extra = []
    tdir = os.path.join(ROOT, "aoe2mod", "tests")
    for fn in sorted(os.listdir(tdir)):
        if fn.endswith(".py"):
            extra.append(os.path.join("aoe2mod", "tests", fn))
    seen = set()
    out = []
    for n in names + extra:
        n2 = n.replace("\\", "/")
        if n2 in seen:
            continue
        seen.add(n2)
        out.append(n)
    return out


def src_of(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def dump(node, src):
    seg = ast.get_source_segment(src, node)
    if seg is None:
        seg = "<unavailable>"
    seg = " ".join(seg.split())
    return seg[:160]


def is_const(node, val=True):
    return isinstance(node, ast.Constant) and node.value is val


def is_empty_collection(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts) == 0
    if isinstance(node, ast.Dict):
        return len(node.keys) == 0
    if isinstance(node, ast.Call):
        f = node.func
        name = getattr(f, "id", None) or getattr(f, "attr", None)
        if name in ("list", "tuple", "set", "dict") and not node.args:
            return True
        if name == "range" and len(node.args) == 1 and isinstance(
                node.args[0], ast.Constant) and node.args[0].value == 0:
            return True
    return False


def norm(node):
    try:
        return ast.dump(node)
    except Exception:
        return None


findings = []


def add(path, node, kind, src):
    try:
        line = node.lineno
    except Exception:
        line = 0
    findings.append((path, line, kind, dump(node, src)))


class V(ast.NodeVisitor):
    def __init__(self, path, src):
        self.path = path
        self.src = src

    # 1. `X or True`, `True or X`
    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.Or):
            for v in node.values:
                if is_const(v, True):
                    add(self.path, node, "TAUTOLOGY-or-true", self.src)
                    break
        if isinstance(node.op, ast.And):
            for v in node.values:
                if is_const(v, False):
                    add(self.path, node, "NEVER-and-false", self.src)
                    break
        self.generic_visit(node)

    # 2. `if True:` / `while True:` (while True is legit for loops; flag only if)
    def visit_If(self, node):
        if is_const(node.test, True):
            add(self.path, node, "IF-TRUE", self.src)
        if is_const(node.test, False):
            add(self.path, node, "IF-FALSE-unreachable", self.src)
        self.generic_visit(node)

    # 3. assert <const>
    def visit_Assert(self, node):
        if isinstance(node.test, ast.Constant):
            add(self.path, node, "ASSERT-CONST(%r)" % (node.test.value,), self.src)
        self.generic_visit(node)

    # 4. comparisons
    def visit_Compare(self, node):
        ops = node.ops
        # x - x  anywhere on either side
        sides = [node.left] + list(node.comparators)
        for side in sides:
            if isinstance(side, ast.BinOp) and isinstance(side.op, ast.Sub):
                if norm(side.left) == norm(side.right):
                    add(self.path, node, "IDENTITY-ARITH(x-x)", self.src)
                    break
        # same expression both sides: x == x
        if len(node.comparators) == 1:
            if norm(node.left) == norm(node.comparators[0]):
                add(self.path, node, "SELF-COMPARE", self.src)
        # comparing a length-difference to a constant 0 tautologically
        self.generic_visit(node)

    # 5. loop over provably empty iterable
    def visit_For(self, node):
        if is_empty_collection(node.iter):
            add(self.path, node, "LOOP-OVER-EMPTY", self.src)
        self.generic_visit(node)

    def visit_comprehension(self, node):
        if is_empty_collection(node.iter):
            add(self.path, node, "COMP-OVER-EMPTY", self.src)
        self.generic_visit(node)

    # 6. `except ...: pass` that swallows
    def visit_Try(self, node):
        for h in node.handlers:
            body = h.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                add(self.path, h, "EXCEPT-PASS", self.src)
            if (len(body) == 1 and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)):
                add(self.path, h, "EXCEPT-SILENT", self.src)
        self.generic_visit(node)

    # 7. `return` inside a loop body (early exit / unreachable rest)
    # handled separately

    # 8. `check(..., cond)` where the call result is discarded? covered by or-true
    # 9. `if <cond>: pass  # comment`
    def visit_FunctionDef(self, node):
        self.generic_visit(node)


def scan(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return
    src = src_of(full)
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print("SYNTAX %s: %s" % (path, e))
        return
    V(path, src).visit(tree)


files = load_list()
for f in files:
    scan(f)

print("scanned files:", len(files))
print("findings:", len(findings))
print()
for path, line, kind, snip in sorted(findings, key=lambda t: (t[0], t[1])):
    print("%s:%d  %-28s %s" % (path.replace("\\", "/"), line, kind, snip))

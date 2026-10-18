# -*- coding: utf-8 -*-
"""Second-pass scan: find check()/assert conditions that are compile-time constant,
float literals compared with ==/!=, and `len(x) >= 0` style always-true bounds.
"""
import ast
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

CHECK_NAMES = {"check", "ok", "expect", "assert_true", "verify", "_check"}


def load_list():
    p = os.path.join(HERE, "suite_list.txt")
    with open(p, encoding="utf-8") as f:
        names = [ln.strip() for ln in f if ln.strip()]
    tdir = os.path.join(ROOT, "aoe2mod", "tests")
    for fn in sorted(os.listdir(tdir)):
        if fn.endswith(".py"):
            names.append(os.path.join("aoe2mod", "tests", fn))
    seen, out = set(), []
    for n in names:
        k = n.replace("\\", "/")
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    return out


def seg(src, node):
    s = ast.get_source_segment(src, node) or "<none>"
    return " ".join(s.split())[:150]


def const_eval(node):
    """Return (True, value) when the expression is a compile-time constant."""
    if isinstance(node, ast.Constant):
        return True, node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        ok, v = const_eval(node.operand)
        if ok:
            return True, (not v)
    if isinstance(node, ast.BoolOp):
        vals = []
        for v in node.values:
            ok, val = const_eval(v)
            if not ok:
                return False, None
            vals.append(val)
        if isinstance(node.op, ast.And):
            return True, all(vals)
        return True, any(vals)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        okl, vl = const_eval(node.left)
        okr, vr = const_eval(node.comparators[0])
        if okl and okr:
            op = node.ops[0]
            try:
                if isinstance(op, ast.Eq):
                    return True, vl == vr
                if isinstance(op, ast.NotEq):
                    return True, vl != vr
                if isinstance(op, ast.Lt):
                    return True, vl < vr
                if isinstance(op, ast.Gt):
                    return True, vl > vr
                if isinstance(op, ast.LtE):
                    return True, vl <= vr
                if isinstance(op, ast.GtE):
                    return True, vl >= vr
            except Exception:
                return False, None
    if isinstance(node, ast.Call):
        f = node.func
        nm = getattr(f, "id", None) or getattr(f, "attr", None)
        if nm in ("len", "str", "repr") and len(node.args) == 1:
            oka, va = const_eval(node.args[0])
            if oka:
                try:
                    if nm == "len":
                        return True, len(va)
                    if nm == "str":
                        return True, str(va)
                    return True, repr(va)
                except Exception:
                    return False, None
    return False, None


findings = []


class V(ast.NodeVisitor):
    def __init__(self, path, src):
        self.path, self.src = path, src

    def visit_Call(self, node):
        f = node.func
        nm = getattr(f, "id", None) or getattr(f, "attr", None)
        if nm in CHECK_NAMES:
            args = list(node.args)
            # locate the condition: first non-string arg
            cond = None
            for a in args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    continue
                cond = a
                break
            if cond is not None:
                ok, val = const_eval(cond)
                if ok:
                    findings.append((self.path, node.lineno, "CONST-COND(%r)" % (val,),
                                     seg(self.src, node)))
                # len(x) >= 0  /  len(x) > -1
                self._bound(cond, node)
        self.generic_visit(node)

    def _bound(self, cond, node):
        if isinstance(cond, ast.Compare) and len(cond.ops) == 1:
            L, R = cond.left, cond.comparators[0]
            op = cond.ops[0]
            lname = getattr(L.func, "id", None) if isinstance(L, ast.Call) else None
            if lname == "len" and isinstance(R, ast.Constant):
                v = R.value
                if isinstance(op, ast.GtE) and isinstance(v, int) and v <= 0:
                    findings.append((self.path, node.lineno, "LEN-GE-ALWAYS", seg(self.src, node)))
                if isinstance(op, ast.Gt) and isinstance(v, int) and v < 0:
                    findings.append((self.path, node.lineno, "LEN-GT-ALWAYS", seg(self.src, node)))
            if lname in ("len", "sum") and isinstance(op, (ast.Lt, ast.LtE)) and isinstance(R, ast.Constant):
                if isinstance(R.value, int) and R.value > 0:
                    pass

    def visit_Assert(self, node):
        ok, val = const_eval(node.test)
        if ok:
            findings.append((self.path, node.lineno, "ASSERT-CONST(%r)" % (val,),
                             seg(self.src, node)))
        self.generic_visit(node)

    def visit_Compare(self, node):
        # float literal equality
        for c in node.comparators:
            if isinstance(c, ast.Constant) and isinstance(c.value, float):
                op = node.ops[0]
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    findings.append((self.path, node.lineno, "FLOAT-LITERAL-EQ",
                                     seg(self.src, node)))
        # string literal compared to itself
        self.generic_visit(node)


files = load_list()
for rel in files:
    full = os.path.join(ROOT, rel)
    if not os.path.exists(full):
        continue
    with io.open(full, encoding="utf-8", errors="replace") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    V(rel, src).visit(tree)

print("findings:", len(findings))
for p, ln, kind, s in sorted(findings, key=lambda t: (t[0], t[1])):
    print("%s:%d  %-22s %s" % (p.replace("\\", "/"), ln, kind, s))

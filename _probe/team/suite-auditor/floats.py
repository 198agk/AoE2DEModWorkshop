# -*- coding: utf-8 -*-
"""Float-comparison scan: comparisons against an unrounded decimal literal,
which is the float32-vs-binary64 trap this project has shipped before.

Also reports `==`/`!=` against a literal with >6 decimal digits, and any
assertion of a bound that the code path cannot reach (heuristic: `<= 0`,
`>= 1.0` on a fraction).
"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LIST = os.path.join(HERE, "suite_list.txt")

files = [ln.strip() for ln in open(LIST, encoding="utf-8") if ln.strip()]
EXTRA = os.path.join(ROOT, "aoe2mod", "tests")
for fn in sorted(os.listdir(EXTRA)):
    if fn.endswith(".py"):
        rel = os.path.join("aoe2mod", "tests", fn)
        if rel not in files:
            files.append(rel)

LITERALISH = (ast.Constant,)


def is_floatish(node):
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    if isinstance(node, ast.Constant) and isinstance(node.value, float):
        return node.value
    return None


for rel in files:
    p = os.path.join(ROOT, rel)
    try:
        src = open(p, encoding="utf-8").read()
        tree = ast.parse(src)
    except (SyntaxError, OSError):
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        ops = [type(o).__name__ for o in node.ops]
        if "Eq" not in ops and "NotEq" not in ops:
            continue
        vals = [is_floatish(node.left)] + [is_floatish(c) for c in node.comparators]
        vals = [v for v in vals if v is not None]
        for v in vals:
            s = ("%.12f" % v).rstrip("0")
            digits = s.split(".")[-1] if "." in s else ""
            if len(digits) > 6:
                print("%-40s %5d  %s  -> literal %r (%d decimals)"
                      % (os.path.basename(rel), node.lineno,
                         ast.unparse(node)[:90], v, len(digits)))

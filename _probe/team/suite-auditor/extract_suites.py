# -*- coding: utf-8 -*-
"""Extract the SUITES list from _probe/run_suites.py by AST (no regex fragility)."""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
p = os.path.join(ROOT, "_probe", "run_suites.py")
with open(p, encoding="utf-8") as f:
    tree = ast.parse(f.read())

names = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "SUITES":
                names = [e.value for e in node.value.elts]

out = os.path.join(HERE, "suite_list.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(names))
print("suites:", len(names))
missing = []
for n in names:
    fp = os.path.join(ROOT, n)
    if not os.path.exists(fp):
        missing.append(n)
print("missing files:", missing)

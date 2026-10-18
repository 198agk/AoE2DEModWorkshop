# -*- coding: utf-8 -*-
"""Every backticked callable name in the three SKILL.mds: does a def/class exist?"""
import sys, io, os, re, ast, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\Software\AI\帝国项目"
os.chdir(ROOT)

# index every def/class/assignment target in aoe2mod/**/*.py and _probe/**.py
index = {}
for base in ("aoe2mod", "_probe"):
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            try:
                tree = ast.parse(open(p, encoding="utf-8", errors="replace").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names = [node.name]
                elif isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            names = [t.id]
                for n in names:
                    index.setdefault(n, set()).add(p)

docs = [r".dsh/skills/aoe2-de-dat/SKILL.md",
        r".dsh/skills/aoe2-de-sprites/SKILL.md",
        r".dsh/skills/aoe2-de-ui-textures/SKILL.md"]

# name immediately followed by "(" inside backticks, and also bare ".attr(" style
pat = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)\(([^`)]*)\)?")
missing = []
checked = 0
seen = set()
for d in docs:
    for i, ln in enumerate(open(d, encoding="utf-8").read().splitlines(), 1):
        for m in pat.finditer(ln):
            full = m.group(1)
            base = full.split(".")[-1]
            if full in seen:
                continue
            seen.add(full)
            checked += 1
            if base not in index:
                missing.append((d, i, full, ln.strip()[:110]))

print("distinct callables cited:", checked)
print("NOT FOUND anywhere in aoe2mod/ or _probe/:", len(missing))
for d, i, full, ctx in missing:
    print("  %-46s:%-4d %-34s %s" % (d.split("/")[-1].replace("SKILL.md", "") + "SKILL.md", i, full, ctx))

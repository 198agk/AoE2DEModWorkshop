import sys, io, os, re, ast
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src = open("aoe2mod/api.py",encoding="utf-8").read()
print("api.py: 'not_proven' occurrences =", src.count("not_proven"))
for i,l in enumerate(src.splitlines(),1):
    if "not_proven" in l: print("  %d| %s" % (i, l.strip()[:230]))
print()
print("resolve_mod_name present:", "def resolve_mod_name" in src)
for i,l in enumerate(src.splitlines(),1):
    if "def resolve_mod_name" in l: print("  %d| %s" % (i, l.strip()))
print()
for name in ("def _split_by_strategy",):
    for i,l in enumerate(src.splitlines(),1):
        if name in l: print("  %d| %s" % (i, l.strip()[:200]))
# return statement of _split_by_strategy
i0 = next(i for i,l in enumerate(src.splitlines(),1) if "def _split_by_strategy" in l)
print("  body around:")
for i in range(i0, i0+26):
    print("  %d| %s" % (i, src.splitlines()[i-1].rstrip()[:200]))

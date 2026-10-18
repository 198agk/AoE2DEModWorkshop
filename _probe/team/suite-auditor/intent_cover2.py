"""For each declared intent, list REGISTERED suites that actually INVOKE it.

An invocation is a dict literal containing a key "intent" whose value is the
intent name (as written by the compiler: {"intent": "unit.stat", ...}), or a
call to plan/build with that string.  Bare string mentions in comments or in
comparison lists are counted separately, because a suite can *mention* an
intent and never run it.
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROBE = os.path.join(ROOT, "_probe")

SUITES = []
_src = open(os.path.join(PROBE, "run_suites.py"), encoding="utf-8").read()
for _node in ast.walk(ast.parse(_src)):
    if isinstance(_node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SUITES" for t in _node.targets):
        SUITES = [e.value for e in _node.value.elts]
TESTS = [os.path.join("aoe2mod", "tests", f) for f in
         sorted(os.listdir(os.path.join(ROOT, "aoe2mod", "tests")))
         if f.endswith(".py")]
FILES = sorted(set(SUITES) | set(TESTS))

with open(os.path.join(ROOT, "aoe2mod", "schema", "intents.json"), encoding="utf-8") as fh:
    SCHEMA = json.load(fh)
NAMES = list(SCHEMA["intents"].keys())


def invoked_in(src, name):
    """True when some dict literal in the file has {"intent": name}."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "intent":
                    if isinstance(v, ast.Constant) and v.value == name:
                        return True
    return False


rows = {n: {"invoke": [], "mention": []} for n in NAMES}
for rel in FILES:
    path = os.path.join(ROOT, rel)
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        continue
    for n in NAMES:
        if invoked_in(src, n):
            rows[n]["invoke"].append(rel)
        elif ('"%s"' % n) in src or ("'%s'" % n) in src:
            rows[n]["mention"].append(rel)

for n in NAMES:
    r = rows[n]
    print("== %s" % n)
    print("   INVOKED by %d: %s" % (len(r["invoke"]), ", ".join(r["invoke"]) or "-"))
    print("   mentioned-only in %d: %s" % (len(r["mention"]), ", ".join(r["mention"]) or "-"))

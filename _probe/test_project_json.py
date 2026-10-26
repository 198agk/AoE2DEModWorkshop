"""A generated description is only worth having if "out of date" is red.

`project.json` is derived from the live schema by `tools/describe.py`, so it
cannot disagree with the tree unless someone forgot to regenerate it.  That is
exactly the failure this file exists to catch: every hand-maintained description
in this repository has gone stale, and a stale description keeps parsing, which
is why nobody notices.  README's intent table was a row short for a day; the
verify command said 116 suites against a registry of 138.

Two independent things are checked here, on purpose:

  A. `tools/describe.py --check` exits 0 -- the file on disk is what the current
     tree generates.  This catches "schema changed, file did not".
  B. The claims inside the file are re-derived HERE, from a different route than
     the generator took (ast for the suite list, the reader's own sentence table
     for `by_sentence`, the two `def do_GET`/`def do_POST` bodies for routes).
     Without B, a generator bug that writes a wrong number would be blessed by A
     forever: the file would match the tree, and the tree would be described
     wrongly.  That is the same shape as a test that asks the code under test
     what to expect.

What this file does NOT do: run the tool, read the game, or import the schema
through the compiler.  It has to be cheap enough to sit in the fast suite.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PROJECT = os.path.join(ROOT, "project.json")
CHECKED = []
FAILED = []


def check(name, ok, detail=""):
    CHECKED.append(name)
    if ok:
        print("  ok   %s%s" % (name, (" :: %s" % detail) if detail else ""))
    else:
        print("  FAIL %s%s" % (name, (" :: %s" % detail) if detail else ""))
        FAILED.append(name)


def _load(path):
    with io.open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _suite_names():
    """The runner's list, read with ast (a `]` in a comment fools a regex)."""
    with io.open(os.path.join(HERE, "run_suites.py"), "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SUITES" for t in node.targets):
            return [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    return []


def _routes_from_server():
    src = io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
                  encoding="utf-8").read()
    cut = src.find("def do_POST")
    get_part = src if cut < 0 else src[:cut]
    post_part = "" if cut < 0 else src[cut:]
    end = post_part.find("\n        def ", 5)
    if end > 0:
        post_part = post_part[:end]
    pattern = r'if path == "(/api/[a-z0-9\-]+)"'
    return (sorted(set(re.findall(pattern, get_part))),
            sorted(set(re.findall(pattern, post_part))))


def main():
    if not os.path.isfile(PROJECT):
        print("PROJECT JSON: MISSING -- run tools/describe.py")
        return 1
    doc = _load(PROJECT)

    print("=== A. the file is what the tree generates right now")
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "describe.py"),
                           "--check"], capture_output=True, text=True)
    check("describe.py --check exits 0", proc.returncode == 0,
          (proc.stdout or proc.stderr).strip().splitlines()[-1:] or "")

    print("=== B. the claims inside it, re-derived from the tree")
    intents = _load(os.path.join(ROOT, "aoe2mod", "schema", "intents.json"))
    schema_ids = sorted(intents["intents"])
    check("the file lists every schema intent",
          sorted(i["id"] for i in doc["intents"]) == schema_ids,
          "%d in file, %d in schema" % (len(doc["intents"]), len(schema_ids)))
    check("and no intent it lists has been deleted",
          all(i["id"] in intents["intents"] for i in doc["intents"]), "")

    # by_sentence must be the reader's own answer, not a copied constant.
    from aoe2mod.ui import nl
    real_sayable = sorted(k for k, v in intents["intents"].items()
                          if nl.sentence_reachable(k, v))
    check("the sayable list is the reader's answer",
          doc["intents_by_sentence"] == real_sayable,
          "file %d, reader %d" % (len(doc["intents_by_sentence"]), len(real_sayable)))
    check("and the two lists partition the schema",
          sorted(doc["intents_by_sentence"] + doc["intents_api_only"]) == schema_ids, "")

    gets, posts = _routes_from_server()
    check("the GET routes are the dispatch's GET routes",
          doc["routes"]["get"] == gets,
          "file %d, server %d" % (len(doc["routes"]["get"]), len(gets)))
    check("the POST routes are the dispatch's POST routes",
          doc["routes"]["post"] == posts,
          "file %d, server %d" % (len(doc["routes"]["post"]), len(posts)))
    check("every documented route starts with /api/",
          all(r.startswith("/api/") for r in doc["routes"]["get"] + doc["routes"]["post"]), "")

    from aoe2mod.ui import locale as LO
    table = LO.load()
    check("the wording count is the table's count",
          doc["wording"]["keys"] == len(table),
          "file %s, table %d" % (doc["wording"]["keys"], len(table)))
    check("the wording file exists",
          os.path.isfile(os.path.join(ROOT, doc["wording"]["file"])),
          doc["wording"]["file"])

    names = _suite_names()
    check("the suite count is the runner's list length",
          doc["commands"]["suites"]["python"] == len(names),
          "file %s, runner %d" % (doc["commands"]["suites"]["python"], len(names)))
    check("and the runner's suites all exist on disk",
          all(os.path.isfile(os.path.join(ROOT, rel)) for rel in names), "")

    strategies = set((v.get("compile") or {}).get("strategy")
                     for v in intents["intents"].values())
    check("every strategy it names is a strategy the schema declares",
          all(i["strategy"] in strategies for i in doc["intents"]),
          sorted(strategies))

    print()
    if FAILED:
        print("PROJECT JSON: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("PROJECT JSON: %d CHECKS PASSED -- THE DESCRIPTION ON DISK IS WHAT THE "
          "TREE GENERATES, AND ITS NUMBERS ARE RE-DERIVED RATHER THAN TRUSTED"
          % len(CHECKED))
    return 0


if __name__ == "__main__":
    sys.exit(main())

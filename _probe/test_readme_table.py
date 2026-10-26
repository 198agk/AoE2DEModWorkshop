"""Nail the front page's intent TABLE, not just a mention of the id.

Why this exists separately from `_probe/test_doc_drift.py` section E: that
section asks "does the README name every intent the schema ships", and it passed
while the table was a row short -- because `unit.replace_on_map` was mentioned
lower down, in the "实机验证过" list.  A mention is what a search finds; a table
row is what a stranger reads.  Both questions are worth a check, and only one of
them had one.

The table is also where a number can go stale silently: it is headed
"能做什么（14 个意图）" and nothing compared that 14 to the number of rows.

Run:  python _probe\test_readme_table.py
"""

import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

README = os.path.join(ROOT, "README.md")
FAILS = []
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(name)
    if ok:
        print("  ok " + name)
    else:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def table_ids(text):
    """Unique intent ids named inside the 能做什么 table, in order.

    Read the ids, not the cells: one cell names two (`tech.research_time`、
    `tech.cost`), so counting cells gives 13 for a table of 14 intents.
    """
    out = []
    for ln in text.split("\n"):
        if not ln.startswith("| "):
            continue
        for m in re.finditer(r"`((?:unit|tech)\.[a-z_]+)`", ln):
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def schema_intents():
    """Ask a child process, so this nail never pays the 93 MB parse itself."""
    code = (
        "import json,sys;"
        "sys.path.insert(0, r'%s');"
        "from aoe2mod.intent import compiler as C;"
        "d,_=C.load_schema();"
        "print(json.dumps(sorted(d['intents'].keys())))" % ROOT
    )
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise RuntimeError("could not read the schema: %s" % (out.stderr or "")[-400:])
    return json.loads(out.stdout)


def main():
    text = read(README)
    ids = table_ids(text)
    schema = schema_intents()

    check("the table names at least ten intents", len(ids) >= 10, str(len(ids)))
    missing = [k for k in schema if k not in ids]
    check("the table has a row for every intent the schema ships",
          not missing, json.dumps(missing))

    # The heading's number is a claim about the table sitting under it.  It went
    # stale the moment a fourteenth intent landed, and nothing read it.
    m = re.search(r"能做什么（(\d+)\s*个意图）", text)
    check("the heading states a count at all", bool(m),
          "no 能做什么（N 个意图） in the README")
    if m:
        check("...and it equals the number of rows", int(m.group(1)) == len(ids),
              "heading says %s, table has %d" % (m.group(1), len(ids)))
        check("...and it equals what the schema ships",
              int(m.group(1)) == len(schema),
              "heading says %s, schema has %d" % (m.group(1), len(schema)))

    # The verification command is a live instruction; a stale number there sends
    # a reader to run something and expect the wrong wait.
    runs = re.findall(r"run_suites\.py'\s*#\s*(\d+)\s*条快套件", text)
    check("the verification command states a count", bool(runs),
          "no `run_suites.py # N 条快套件` line")
    if runs:
        reg = os.path.join(ROOT, "_probe", "run_suites.py")
        src = read(reg)
        import ast
        tree = ast.parse(src)
        n = 0
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "SUITES" for t in node.targets):
                n = len(node.value.elts)
        check("...and that count is what the runner registers",
              int(runs[0]) == n, "README says %s, runner has %d" % (runs[0], n))

    print()
    if FAILS:
        print("README TABLE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("README TABLE: %d CHECKS PASSED -- EVERY INTENT HAS A ROW, THE HEADING "
          "COUNT MATCHES THE ROWS AND THE SCHEMA, AND THE RUN COUNT MATCHES THE RUNNER"
          % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

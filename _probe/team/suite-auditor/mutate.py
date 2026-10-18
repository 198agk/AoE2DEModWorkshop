# -*- coding: utf-8 -*-
"""Mutation harness: run a suite against a patched COPY of aoe2mod.

Usage:  python mutate.py <label> <suite_rel_path> <target_file> <old> <new>

Each call:
  1. fresh copy scratch_tree -> run_<label>
  2. apply one exact string replacement in run_<label>/<target_file>
     (assert exactly one occurrence; refuse otherwise)
  3. run run_<label>/<suite_rel_path> with cwd=run_<label>
  4. report exit code and whether the final line still reads like success

The pristine tree `scratch` is never modified.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.join(HERE, "scratch")
PY = sys.executable
OUT = os.path.join(HERE, "mutations")

IGNORE = shutil.ignore_patterns("out", "__pycache__", "*.pyc")


def fresh(dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(SCRATCH, dest, ignore=IGNORE)
    os.makedirs(os.path.join(dest, "aoe2mod", "tests", "out"), exist_ok=True)
    return dest


def patch(root, rel, old, new):
    p = os.path.join(root, rel)
    with open(p, encoding="utf-8") as f:
        src = f.read()
    n = src.count(old)
    if n != 1:
        raise SystemExit("PATCH ANCHOR %r occurs %d times in %s" % (old, n, rel))
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(src.replace(old, new, 1))
    return p


def run(root, suite, timeout=900):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.pop("PYTHONPATH", None)
    r = subprocess.run([PY, "-X", "utf8", suite], cwd=root, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def main():
    label, suite, target, old, new = sys.argv[1:6]
    os.makedirs(OUT, exist_ok=True)
    root = fresh(os.path.join(OUT, "run_" + label))
    if target != "-":
        patch(root, target, old, new)
    code, out = run(root, suite)
    log = os.path.join(OUT, label + ".log")
    with open(log, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    lines = [x.rstrip() for x in out.strip().splitlines() if x.strip()]
    print(json.dumps({
        "label": label,
        "suite": suite,
        "mutation": [target, old, new],
        "exit": code,
        "tail": lines[-3:],
        "log": os.path.relpath(log, HERE),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

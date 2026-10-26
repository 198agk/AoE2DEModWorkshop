# -*- coding: utf-8 -*-
"""Prove the acceptance checker still catches the defects it was written for.

The checker was edited three times in one round (excuse `:root`, resolve `var()`
before counting, ignore `@container` overrides).  Every one of those edits makes
it MORE permissive, and a permissive checker that goes green is exactly the
failure mode this repository has spent days removing.  So each relaxation is
tested by re-introducing the defect it is supposed to tolerate only in the
legitimate place.

Each case patches a copy of the page in a temp dir, runs the real checker
against it, and requires the named failure.  Nothing in the repo is modified.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
CHECKER = os.path.join(HERE, "design_acceptance.py")
PY = sys.executable

FAILS = []


def check(name, ok, detail=""):
    if ok:
        print("ok   %s" % name)
    else:
        print("FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


def run_checker(page_text):
    """Write `page_text` into a throwaway tree and run the real checker."""
    tmp = tempfile.mkdtemp(prefix="dsh_accept_")
    try:
        os.makedirs(os.path.join(tmp, "aoe2mod", "ui", "static"))
        os.makedirs(os.path.join(tmp, "aoe2mod", "schema", "locales"))
        os.makedirs(os.path.join(tmp, "_probe"))
        with io.open(os.path.join(tmp, "aoe2mod", "ui", "static", "index.html"),
                     "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page_text)
        for name in os.listdir(os.path.join(ROOT, "aoe2mod", "schema", "locales")):
            if name.endswith(".json"):
                shutil.copy(os.path.join(ROOT, "aoe2mod", "schema", "locales", name),
                            os.path.join(tmp, "aoe2mod", "schema", "locales", name))
        report = os.path.join(ROOT, "_probe", "width_report.json")
        if os.path.isfile(report):
            shutil.copy(report, os.path.join(tmp, "_probe", "width_report.json"))
        shutil.copy(CHECKER, os.path.join(tmp, "_probe", "design_acceptance.py"))
        got = subprocess.run([PY, "-X", "utf8", os.path.join(tmp, "_probe",
                                                             "design_acceptance.py")],
                             capture_output=True, timeout=120)
        return got.returncode, got.stdout.decode("utf-8", "replace")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def page():
    return io.open(PAGE, encoding="utf-8").read()


def main():
    base = page()
    code, out = run_checker(base)
    check("the real page passes", code == 0, out.strip().split("\n")[-1])

    # 1. A hex literal outside the token table must still red item 1.
    broken = base.replace("  body {",
                          "  body { border-color: #ff0000;", 1)
    code, out = run_checker(broken)
    check("a hex literal outside :root is caught",
          code == 1 and "no hex literals outside :root" in out and "FAIL 1" in out,
          out.strip().split("\n")[-1])

    # 2. The contract allows at most five sizes; the page uses four, so ONE more
    # is legal.  Two more is not.  The first version of this case added a single
    # size and expected a red -- it would have "proved" a detector that cannot
    # fire, which is the same class of mistake as the checker that counts zero.
    broken = base.replace("  .empty {",
                          "  .empty { font-size: 23px; }\n  .empty2 { font-size: 24px;", 1)
    code, out = run_checker(broken)
    check("a sixth font size is caught", code == 1 and "FAIL 2" in out,
          out.strip().split("\n")[-1])

    # ...and five is still allowed, so the allowance is not silently a ban.
    five = base.replace("  .empty {",
                        "  .empty { font-size: 23px;", 1)
    code, out = run_checker(five)
    check("a fifth font size is allowed", code == 0,
          out.strip().split("\n")[-1])

    # 3. A half-pixel size must red item 3.
    broken = base.replace("  .empty {",
                          "  .empty { font-size: 12.5px;", 1)
    code, out = run_checker(broken)
    check("a half-pixel font size is caught", code == 1 and "FAIL 3" in out,
          out.strip().split("\n")[-1])

    # 4. A fourth radius must red item 4.
    broken = base.replace("  .empty {",
                          "  .empty { border-radius: 20px;", 1)
    code, out = run_checker(broken)
    check("a fourth radius is caught", code == 1 and "FAIL 4" in out,
          out.strip().split("\n")[-1])

    # 5. A spacing value off the scale (and not 48) must red item 5.
    broken = base.replace("  .empty {", "  .empty { padding: 18px;", 1)
    code, out = run_checker(broken)
    check("an off-scale spacing value is caught", code == 1 and "FAIL 5" in out,
          out.strip().split("\n")[-1])

    # 6. An inline style must red item 6.
    broken = base.replace('<div class="box">', '<div class="box" style="color:red">', 1)
    code, out = run_checker(broken)
    check("an inline style is caught", code == 1 and "FAIL 6" in out,
          out.strip().split("\n")[-1])

    # 7. A var() with no definition must red item 7.
    broken = base.replace("  .empty {", "  .empty { color: var(--nope);", 1)
    code, out = run_checker(broken)
    check("an undefined var() is caught", code == 1 and "FAIL 7" in out,
          out.strip().split("\n")[-1])

    # 8. An empty top-level rule must red item 8.
    broken = base.replace("  .empty {",
                          "  .nothing-here { }\n  .empty {", 1)
    code, out = run_checker(broken)
    check("an empty rule block is caught", code == 1 and "FAIL 8" in out,
          out.strip().split("\n")[-1])

    # 9. A label without for= must red item 9.
    broken = base.replace('for="title" ', "", 1)
    code, out = run_checker(broken)
    check("a label without for= is caught", code == 1 and "FAIL 9" in out,
          out.strip().split("\n")[-1])

    # 10. A second .primary must red item 10.
    broken = base.replace('<button id="btn-form" class="chip"',
                          '<button id="btn-form" class="chip primary"', 1)
    code, out = run_checker(broken)
    check("a second .primary is caught", code == 1 and "FAIL 10" in out,
          out.strip().split("\n")[-1])

    # 11. An em dash in the string table must red item 12 (the page copies that
    # table over its own text, so a clean markup file is not enough).
    tmp = tempfile.mkdtemp(prefix="dsh_locale_")
    try:
        os.makedirs(os.path.join(tmp, "aoe2mod", "ui", "static"))
        os.makedirs(os.path.join(tmp, "aoe2mod", "schema", "locales"))
        os.makedirs(os.path.join(tmp, "_probe"))
        io.open(os.path.join(tmp, "aoe2mod", "ui", "static", "index.html"),
                "w", encoding="utf-8", newline="\n").write(base)
        src = os.path.join(ROOT, "aoe2mod", "schema", "locales", "zh.json")
        body = io.open(src, encoding="utf-8").read()
        io.open(os.path.join(tmp, "aoe2mod", "schema", "locales", "zh.json"),
                "w", encoding="utf-8", newline="\n").write(
            body.replace("预览，还没动任何文件", "预览 \u2014 还没动任何文件", 1))
        report = os.path.join(ROOT, "_probe", "width_report.json")
        if os.path.isfile(report):
            shutil.copy(report, os.path.join(tmp, "_probe", "width_report.json"))
        shutil.copy(CHECKER, os.path.join(tmp, "_probe", "design_acceptance.py"))
        got = subprocess.run([PY, "-X", "utf8", os.path.join(tmp, "_probe",
                                                             "design_acceptance.py")],
                             capture_output=True, timeout=120)
        out = got.stdout.decode("utf-8", "replace")
        check("an em dash in the locale table is caught",
              got.returncode == 1 and "FAIL 12" in out,
              out.strip().split("\n")[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 12. A genuine `@container` override must NOT be reported as a duplicate.
    check("a @container override is not a duplicate",
          "FAIL 8" not in run_checker(base)[1],
          "the real page has #editor .edlist twice, once inside @container")

    if FAILS:
        print("\nACCEPTANCE SELF-TEST: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("\nACCEPTANCE SELF-TEST: EVERY DETECTOR STILL FIRES, AND THE TWO "
          "RELAXATIONS DO NOT HIDE A DEFECT")
    return 0


if __name__ == "__main__":
    sys.exit(main())

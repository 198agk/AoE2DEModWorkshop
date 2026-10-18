# -*- coding: utf-8 -*-
"""Regenerate the name tables and the semantics layer, then verify.

The generators now write LF.  Re-running them proves two things at once: the
tables still contain the same DATA (the code that reads the game's string files
has not changed), and the line endings no longer fight git.

`extract_ids.py` needs `_raw_ids.json` (17 MB, gitignored, produced from the
shipped .dat), so the semantic rebuild is the slow half.
"""
import io
import os
import subprocess
import sys

ROOT = r"D:\Software\AI\帝国项目"
PY = (r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime"
      r"\dependencies\python\python.exe")

STEPS = (
    (_probe := "_probe/schema/build_attribute_labels.py", "attribute labels"),
    ("_probe/schema/build_resource_labels.py", "resource labels"),
    ("_probe/schema/build_labels_zh.py", "zh label tables"),
    ("_probe/semantic/extract_ids.py", "semantic ids (17 MB intermediate)"),
    ("_probe/semantic/build_semantic.py", "semantic names"),
)


def run(rel, label):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("  SKIP %-42s (missing)" % label)
        return True
    print("  RUN  %-42s" % label)
    r = subprocess.run([PY, "-X", "utf8", p], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    tail = (r.stdout or "").strip().splitlines()[-2:]
    for line in tail:
        print("        " + line[:100])
    if r.returncode != 0:
        print("        FAILED: %s" % (r.stderr or "")[-300:])
        return False
    return True


def crlf_report():
    import glob
    bad = []
    for pat in ("aoe2mod/**/*.json", "aoe2mod/**/*.py", "_probe/schema/*.json",
                "_probe/semantic/*.json", "tools/*.py"):
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            b = io.open(p, "rb").read()
            if b.count(b"\r\n"):
                bad.append((os.path.relpath(p, ROOT), b.count(b"\r\n")))
    print()
    if bad:
        print("files still carrying CRLF: %d" % len(bad))
        for rel, n in bad[:10]:
            print("    %-52s %d" % (rel, n))
    else:
        print("no file in the product or the generated sources carries CRLF.")
    return not bad


def main():
    ok = all([run(rel, label) for rel, label in STEPS])
    if not ok:
        print("\nA generator failed; not reporting a verdict.")
        return 1
    print()
    crlf_report()
    print()
    print("Now run: python tools/sync_engine.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

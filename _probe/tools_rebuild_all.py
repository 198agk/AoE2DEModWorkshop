# -*- coding: utf-8 -*-
"""Full rebuild, in dependency order, with idempotency evidence at every step.

Why order matters: `sync_engine.py` copies whatever the generators produced.
Running it before the generators simply re-vendors today's disk state, which
would make "we rebuilt" an unfalsifiable claim.  So: generate, prove idempotent,
then vendor.

Why idempotency matters: a generator that is not deterministic means the
artifact depends on when you ran it.  Every step is therefore run twice and the
output bytes compared; a difference is reported as a defect, not smoothed over.

Usage:
    python -X utf8 _probe/tools_rebuild_all.py [--skip-semantic]
"""
import hashlib
import io
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = (r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime"
      r"\dependencies\python\python.exe")
P = lambda *a: os.path.join(ROOT, *a)

# (script, human label, files it owns)
STEPS = [
    ("_probe/schema/build_schema.py", "schema tables from AGE Lists.cpp",
     ["_probe/schema/effect_command_types.json",
      "_probe/schema/effect_attributes.json",
      "_probe/schema/armor_classes.json",
      "_probe/schema/AGE3NamesV0007.json"]),
    ("_probe/schema/build_attribute_labels.py", "attribute names (game's 12200 block)",
     ["_probe/schema/attribute_labels.json",
      "_probe/schema/attribute_labels_zh.json"]),
    ("_probe/schema/build_resource_labels.py", "resource names (game's 15000 block)",
     ["_probe/schema/resource_labels.json",
      "_probe/schema/resource_labels_zh.json"]),
    ("_probe/schema/build_labels_zh.py", "chinese labels for commands/attributes/classes",
     ["_probe/schema/effect_labels_zh.json"]),
    ("_probe/semantic/extract_ids.py", "raw name-string ids from the .dat",
     ["_probe/semantic/_raw_ids.json"]),
    ("_probe/semantic/build_semantic.py", "unit/tech names resolved through the strings",
     ["_probe/semantic/unit_names.json",
      "_probe/semantic/tech_names.json"]),
    ("tools/sync_engine.py", "vendor research sources into the shipped package",
     ["aoe2mod/dat/parser.py", "aoe2mod/dat/writer.py", "aoe2mod/dat/locate.py",
      "aoe2mod/game/sld.py", "aoe2mod/game/sldencode.py"]),
]


def sha(rel):
    p = P(rel)
    if not os.path.isfile(p):
        return None
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def run(rel):
    r = subprocess.run([PY, "-X", "utf8", P(rel)], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def snapshot(files):
    return {f: sha(f) for f in files}


def main():
    skip_semantic = "--skip-semantic" in sys.argv
    print("=" * 78)
    print("FULL REBUILD  (each step is run twice to prove determinism)")
    print("=" * 78)
    problems = []
    t_all = time.time()

    for rel, label, owned in STEPS:
        if skip_semantic and "semantic" in rel:
            print("  SKIP  %s (--skip-semantic)" % label)
            continue
        print()
        print("-- %s" % label)
        print("   %s" % rel)
        before = snapshot(owned)
        t0 = time.time()
        rc, out, err = run(rel)
        dt = time.time() - t0
        if rc != 0:
            problems.append("%s exited %d" % (rel, rc))
            print("   FAILED rc=%d in %.1fs" % (rc, dt))
            for line in (err or out).strip().splitlines()[-6:]:
                print("      " + line[:110])
            continue
        after1 = snapshot(owned)
        rc2, out2, err2 = run(rel)
        after2 = snapshot(owned)
        if rc2 != 0:
            problems.append("%s exited %d on the second run" % (rel, rc2))
            print("   SECOND RUN FAILED rc=%d" % rc2)
            continue
        stable = after1 == after2
        if not stable:
            problems.append("%s is not deterministic" % rel)
        changed = [f for f in owned if before[f] != after1[f]]
        print("   ok  %.1fs   deterministic=%s   files changed vs before=%d"
              % (dt, stable, len(changed)))
        for f in changed:
            print("        %-46s %s -> %s" % (f, (before[f] or "-")[:12],
                                              (after1[f] or "-")[:12]))
        for line in out.strip().splitlines()[-3:]:
            print("        | " + line[:104])

    print()
    print("=" * 78)
    print("POST-REBUILD CHECKS")
    print("=" * 78)

    # 1. no CRLF anywhere in the shipped package or the generated sources
    import glob
    bad = []
    for pat in ("aoe2mod/**/*.py", "aoe2mod/**/*.json",
                "_probe/schema/*.json", "_probe/semantic/*.json",
                "tools/*.py"):
        for p in glob.glob(P(pat), recursive=True):
            b = io.open(p, "rb").read()
            if b"\r\n" in b:
                bad.append((os.path.relpath(p, ROOT), b.count(b"\r\n")))
    print("  CRLF-free: %s" % ("yes" if not bad else "NO -- %d files" % len(bad)))
    for rel, n in bad[:10]:
        print("      %-52s %d" % (rel, n))
    if bad:
        problems.append("%d file(s) carry CRLF" % len(bad))

    # 2. every product module imports
    sys.path.insert(0, ROOT)
    import importlib
    import traceback
    fails = []
    n = 0
    for p in sorted(glob.glob(P("aoe2mod/**/*.py"), recursive=True)):
        rel = os.path.relpath(p, ROOT)[:-3].replace(os.sep, ".")
        if rel.endswith(".__init__"):
            rel = rel[:-9]
        n += 1
        try:
            importlib.import_module(rel)
        except Exception as exc:
            fails.append((rel, type(exc).__name__, str(exc)[:100]))
    print("  product modules imported: %d / %d" % (n - len(fails), n))
    for f in fails:
        print("      FAIL %s: %s %s" % f)
    if fails:
        problems.append("%d product module(s) fail to import" % len(fails))

    # 3. provenance still describes the files on disk
    import json
    prov_p = P("aoe2mod/ENGINE_PROVENANCE.json")
    if os.path.isfile(prov_p):
        prov = json.load(io.open(prov_p, encoding="utf-8"))
        mism = []
        no_sha = []
        checked = 0

        def _walk(node, key=""):
            """Every dict that names a path is checked, however deeply nested.

            The first version of this loop only looked at top-level dicts, which
            silently skipped the `data` and `effect_tables` arrays -- 10 of the
            20 files the manifest names.  A verification loop that skips half its
            subject is the same defect shape as the assertions this script exists
            to catch, so it recurses.
            """
            out = []
            if isinstance(node, dict):
                if "path" in node:
                    out.append(node)
                else:
                    for k, v in node.items():
                        out.extend(_walk(v, k))
            elif isinstance(node, list):
                for v in node:
                    out.extend(_walk(v, key))
            return out

        for entry in _walk(prov):
            checked += 1
            want = entry.get("sha256")
            actual = sha(entry["path"])
            if not want:
                no_sha.append(entry["path"])
                continue
            if actual != want:
                mism.append((entry["path"], want[:12], (actual or "-")[:12]))
        print("  provenance entries with a path: %d, checksummed %d, no sha %d"
              % (checked, checked - len(no_sha), len(no_sha)))
        print("  provenance sha mismatches: %d" % len(mism))
        for m in mism:
            print("      %s claimed %s actual %s" % m)
        if mism:
            problems.append("%d provenance sha mismatch(es)" % len(mism))
        if no_sha:
            # Not a failure -- the name tables have no sha by design -- but the
            # count must be printed, because "0 mismatches" over 13 of 20 files
            # reads like "all 20 verified".
            print("      (no sha, so unverified: %s)" % ", ".join(no_sha))

    total = time.time() - t_all
    print()
    if problems:
        print("REBUILD INCOMPLETE (%d problem(s), %.0fs):" % (len(problems), total))
        for p in problems:
            print("   - " + p)
        return 1
    print("REBUILD COMPLETE in %.0fs.  Every step ran twice with identical output."
          % total)
    print("Next: python -X utf8 _probe/run_suites.py  and  _probe/run_long.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

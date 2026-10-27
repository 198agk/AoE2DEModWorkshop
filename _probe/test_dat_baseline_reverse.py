# -*- coding: utf-8 -*-
"""Prove the baseline checker can fail.

A guard that passes is worth nothing until it has been seen to fail for the
right reason.  This project has caught itself three times writing a check that
enumerated nothing (an empty `units` list reported "ok (0)"), so every new
assertion here gets broken on purpose and must produce a NAMED failure.

Each case edits ONE value in a copy of the baseline, re-runs the checker, and
requires the checker to exit non-zero AND print the check's name.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKER = os.path.join(HERE, "test_dat_baseline.py")
BASELINE = os.path.join(ROOT, "_golden", "dat_baseline.json")

CASES = [
    ("raw bytes", lambda b: b.__setitem__("raw_bytes", b["raw_bytes"] + 1)),
    ("raw sha", lambda b: b.__setitem__("raw_sha256", "0" * 64)),
    ("units_gaia ids", lambda b: b["id_sequences"]["units_gaia"].pop()),
    ("units_gaia sha", lambda b: b.__setitem__("gaia_units_sha256", "0" * 64)),
    ("britons sha", lambda b: b.__setitem__("britons_units_sha256", "0" * 64)),
    ("techs ids", lambda b: b["id_sequences"]["techs"].pop()),
    ("graphics ids", lambda b: b["id_sequences"]["graphics"].pop()),
    ("civ names", lambda b: b["civ_names"].pop()),
    ("unit counts", lambda b: b["unit_counts"][0].__setitem__("units", 1)),
    ("structure sha", lambda b: b.__setitem__("structure_sha256", "0" * 64)),
    ("serialized sha", lambda b: b.__setitem__("serialized_sha256", "0" * 64)),
]


def main():
    base = json.loads(io.open(BASELINE, encoding="utf-8").read())
    tmpdir = tempfile.mkdtemp(prefix="datbase_")
    # the checker reads _golden/dat_baseline.json relative to the repo, so give
    # it a whole throwaway tree that mirrors the layout it expects
    fake = os.path.join(tmpdir, "repo")
    os.makedirs(os.path.join(fake, "_golden"))
    os.makedirs(os.path.join(fake, "_probe"))
    shutil.copy2(CHECKER, os.path.join(fake, "_probe", "test_dat_baseline.py"))
    # symlink-free copy of the engine so the checker imports the same code
    src_pkg = os.path.join(ROOT, "aoe2mod")
    dst_pkg = os.path.join(fake, "aoe2mod")
    shutil.copytree(src_pkg, dst_pkg,
                    ignore=shutil.ignore_patterns("__pycache__"))

    dst = os.path.join(fake, "_golden", "dat_baseline.json")
    print("throwaway tree:", fake)
    print()
    bad = []
    for name, mutate in CASES:
        b = json.loads(json.dumps(base))       # deep copy
        mutate(b)
        with io.open(dst, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(b, fh, ensure_ascii=False)
        r = subprocess.run([sys.executable, "-X", "utf8",
                            os.path.join(fake, "_probe", "test_dat_baseline.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800)
        out = (r.stdout or "") + (r.stderr or "")
        red = r.returncode != 0
        # the failure must NAME the check, not just exit non-zero
        named = any(tok in out for tok in
                    ("FAIL", "differs at", "FAILED"))
        status = "RED" if red else "STILL GREEN <-- guard does not bite"
        if not red:
            bad.append(name)
        print("%-22s exit=%d  %s  named=%s" % (name, r.returncode, status, named))

    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    if bad:
        print("REVERSE NOT PROVEN for: %s" % bad)
        return 1
    print("REVERSE OK: every case turned the checker red")
    return 0


if __name__ == "__main__":
    sys.exit(main())

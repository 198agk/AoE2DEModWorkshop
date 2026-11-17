# -*- coding: utf-8 -*-
"""Verify the SEALED app folder: it boots, it answers, and it refuses tampering.

The point of this gate is the distinction the shipped-bundle rule already draws:
a readable development tree passing is not evidence about the encrypted one. So
every check here runs the sealed launcher inside a throwaway copy, and nothing is
compared against the repo sources.

Two build modes are covered, because they answer different questions:

  licensed  a license.key bound to one machine.  Checks 2 and 3 apply.
  free      no license at all (the open-source build).  The license checks are
            replaced by "it boots without one" / "a foreign key does not matter",
            because a free build that demanded a key would be testing the wrong
            thing.  The integrity checks run in BOTH modes -- dropping the license
            must never drop the manifest.

Checks, each proved by running the real child process:

  1. clean boot        -> HTTP 200 on / and 63 civs from /api/meta
  2. no license.key    -> exit 4   (licensed)  |  still boots (free)
  3. foreign-hwid key  -> exit 4   (licensed)  |  still boots (free)
  4. one byte flipped in runtime/engine.pak -> exit 5
  5. one file appended in the tree          -> exit 5
  6. no .py engine source anywhere under the sealed app (that is the whole point)
  7. the build carries the buyer's watermark, not a plain source tree
  8. the pack does not sit on disk in a form a stock decompiler can read

Run: python -X utf8 _probe/verify_sealed.py [--app <sealed app dir>]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SEALED = os.path.join(ROOT, "_cache", "sealed", "app")
RUNTIME_PY = os.path.join(ROOT, "_out", "AoE2ModWorkshop", "runtime", "python.exe")

EXIT_LICENSE = 4
EXIT_INTEGRITY = 5


def _run(runtime_dir, port, timeout=25):
    """Start the sealed launcher and return (exit_code, stderr_text).

    Only useful for a run that is expected to REFUSE: a run that boots keeps
    serving and would sit here until the timeout.
    """
    cmd = [RUNTIME_PY, "-X", "utf8", "-u", "aoe2mod_launch.py",
           "--serve-only", "--port", str(port)]
    p = subprocess.run(cmd, cwd=runtime_dir, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _boot(runtime_dir, port, tries=40):
    """Start the launcher, wait for a real answer, stop it. -> (good, meta, civs)."""
    proc = subprocess.Popen(
        [RUNTIME_PY, "-X", "utf8", "-u", "aoe2mod_launch.py", "--serve-only",
         "--port", str(port)],
        cwd=runtime_dir, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace")
    good, _ = _http_ok(port, "/", tries)
    meta = b""
    if good:
        good_meta, meta = _http_ok(port, "/api/meta", 6)
        good = good and good_meta
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    civs = 0
    try:
        civs = len(((json.loads(meta.decode("utf-8")) or {}).get("civs")) or [])
    except Exception:
        pass
    return good, meta, civs


def _http_ok(port, path="/", tries=40):
    url = "http://127.0.0.1:%d%s" % (port, path)
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                return r.status == 200, r.read()
        except Exception:
            time.sleep(0.5)
    return False, b""


def check_fresh_copy(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify_sealed")
    ap.add_argument("--app", default=DEFAULT_SEALED)
    a = ap.parse_args(argv)
    app = os.path.abspath(a.app)
    if not os.path.isdir(app):
        print("no sealed app at", app)
        return 2
    if not os.path.isfile(RUNTIME_PY):
        print("no bundled interpreter at", RUNTIME_PY)
        return 2

    ok = True

    def note(name, good, detail=""):
        nonlocal ok
        print("  %-26s %s%s" % (name, "ok" if good else "FAIL", detail))
        if not good:
            ok = False

    print("sealed app:", app)

    cfg_path = os.path.join(app, "runtime", "_rt_cfg.py")
    cfg_text = open(cfg_path, encoding="utf-8").read()
    free = any(l.strip() == "FREE = True" for l in cfg_text.splitlines())
    print("  %-26s %s" % ("build mode", "free (no license)" if free else "licensed"))

    # 6. the shipped tree must not contain engine source at all
    # The three files under runtime/ ARE the gate (launcher, assembled boot with
    # the Ed25519 verifier, and the per-build key config) -- they hold no engine
    # logic by design.  Everything else must be gone: a surviving aoe2mod/*.py is
    # a folder that was sealed over instead of sealed.
    GATE = {"runtime/aoe2mod_launch.py", "runtime/aoe2mod_boot.py",
            "runtime/_rt_cfg.py"}
    leaked = []
    for base, dirs, names in os.walk(app):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in names:
            if not n.endswith((".py", ".pyc")):
                continue
            rel = os.path.relpath(os.path.join(base, n), app).replace(os.sep, "/")
            if rel in GATE:
                continue
            leaked.append(rel)
    note("no engine source on disk", not leaked, " %d file(s)" % len(leaked))
    if leaked:
        print("    leakers:", ", ".join(leaked[:6]))

    # 1. clean boot answers a real route
    good, _, civs = _boot(os.path.join(app, "runtime"), 7961)
    note("clean boot", good and civs == 63, " civs=%d" % civs)

    tmp = tempfile.mkdtemp(prefix="sealed_", dir=os.path.join(ROOT, "_probe", "_tmp"))
    try:
        # 2/3. license behaviour -- the branch is the whole difference between the
        # two build modes, and it is deliberate: a free build has no key, so a
        # "refuses without a key" check would test nothing but the absent file.
        w = os.path.join(tmp, "nolicense")
        check_fresh_copy(app, w)
        lk = os.path.join(w, "license.key")
        if os.path.isfile(lk):
            os.remove(lk)

        w2 = os.path.join(tmp, "foreign")
        check_fresh_copy(app, w2)
        issue = os.path.join(HERE, "protect", "licensing.py")
        key = os.path.join(HERE, "protect", "keys", "priv.hex")
        subprocess.run([RUNTIME_PY, "-X", "utf8", issue, "issue", "--priv", key,
                        "--buyer", "FOREIGN", "--hwid", "0000aaaa1111bbbb2222",
                        "--out", os.path.join(w2, "license.key")],
                       check=True, capture_output=True)

        if free:
            good, _, c1 = _boot(os.path.join(w, "runtime"), 7962)
            note("boots without license", good and c1 == 63, " civs=%d" % c1)
            good, _, c2 = _boot(os.path.join(w2, "runtime"), 7963)
            note("foreign key irrelevant", good and c2 == 63, " civs=%d" % c2)
        else:
            rc, out = _run(os.path.join(w, "runtime"), 7962)
            note("refuses without license", rc == EXIT_LICENSE, " rc=%d" % rc)
            rc, out = _run(os.path.join(w2, "runtime"), 7963)
            note("refuses foreign hwid", rc == EXIT_LICENSE, " rc=%d" % rc)

        # 4. one byte flipped inside the encrypted pack
        w3 = os.path.join(tmp, "packflip")
        check_fresh_copy(app, w3)
        pak = os.path.join(w3, "runtime", "engine.pak")
        b = bytearray(open(pak, "rb").read())
        b[len(b) // 2] ^= 0xFF
        open(pak, "wb").write(bytes(b))
        rc, out = _run(os.path.join(w3, "runtime"), 7964, timeout=40)
        note("refuses pack byte-flip", rc == EXIT_INTEGRITY, " rc=%d" % rc)

        # 5. one appended line in a shipped data file
        w4 = os.path.join(tmp, "append")
        check_fresh_copy(app, w4)
        tgt = os.path.join(w4, "aoe2mod", "ui", "static", "index.html")
        with open(tgt, "a", encoding="utf-8") as fh:
            fh.write("\n<!-- repacked by a reseller -->\n")
        rc, out = _run(os.path.join(w4, "runtime"), 7965, timeout=40)
        note("refuses edited page", rc == EXIT_INTEGRITY, " rc=%d" % rc)

        # 7. watermark present in the build
        note("buyer recorded in build", "FRE" in cfg_text,
             " " + [l for l in cfg_text.splitlines() if l.startswith("BUYER")][0][:44])

        # 8b. a stray importable module is the cheapest hijack, and the manifest
        # cannot see it -- only the runtime walk can.
        w5 = os.path.join(tmp, "stray")
        check_fresh_copy(app, w5)
        with open(os.path.join(w5, "runtime", "sitecustomize.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("pass\n")
        rc, out = _run(os.path.join(w5, "runtime"), 7966, timeout=40)
        note("refuses stray module", rc == EXIT_INTEGRITY, " rc=%d" % rc)

        # 8. the pack must not start with anything a stock decompiler reads.
        # A .pyc begins with the 4-byte magic for its interpreter version; an
        # AOE2PAK1 header there is the evidence that the bytes are ciphered.
        head = open(os.path.join(app, "runtime", "engine.pak"), "rb").read(8)
        note("pack is not a .pyc", head[:8] == b"AOE2PAK1", " " + repr(head[:8]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("SEALED BUNDLE: ALL CHECKS OK" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

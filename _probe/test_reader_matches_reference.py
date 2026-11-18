"""Compare the shipped reader against the Python reference, sentence by sentence.

The parse/build gate only asks "does the build accept what the reader said".  It
cannot see the two failure modes this probe exists for:

* the reader agrees with ITSELF and both are wrong (the ordinal was decremented
  on both sides, so 「第2条」 wrote the third command and every internal check
  passed), and
* a class id that is silently replaced by the schema's default, so a refusal
  becomes a wrong edit.

So each sentence is asked of both readers and the ANSWERS are compared, not the
verdicts.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import _paths as P

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, "AoE2 DE Mod Workshop.exe")
PORT = 7841

CASES = [
    "织布机第1条效果改成100",
    "织布机第2条效果加5",
    "织布机第0条效果加5",
    "织布机效果加5",
    "民兵对平民攻击加2",
    "民兵对建筑攻击加2",
    "民兵对家畜攻击加2",
    "城堡对建筑攻击加5",
    "民兵对骑兵攻击加2",
    "民兵对弓箭手护甲加3",
    "织布机研究时间改成5",
    "织布机黄金成本改成5",
    "把织布机和铸币术做成只能选一个",
]


def post(path, body, timeout=900):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (PORT, path),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(proc):
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("the bundle exited: %s" % proc.returncode)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/progress" % PORT, timeout=3) as r:
                p = json.loads(r.read().decode("utf-8")).get("progress") or {}
            if p.get("ready"):
                return
            if p.get("error"):
                raise SystemExit("the bundle failed: %s" % p["error"])
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("the bundle never became ready")


def rust(summary):
    """(intent, the fields that decide which bytes move) or (None, why)."""
    clause = (summary.get("clauses") or [{}])[0]
    intents = summary.get("intents") or []
    if not intents:
        return None, clause.get("why") or "no intent"
    it = intents[0]
    return it, None


def shape(it):
    """The part of an intent that decides WHICH bytes are written."""
    if it is None:
        return None
    k = it.get("intent")
    if k == "tech.effect":
        return (k, it.get("tech"), it.get("command"))
    if k == "unit.attack_class":
        return (k, it.get("unit"), it.get("class_id"), it.get("kind"))
    if k in ("tech.research_time", "tech.cost"):
        return (k, it.get("tech"), it.get("resource"), it.get("value"), it.get("delta"),
                tuple(it.get("civs") or ()))
    if k == "tech.toggle_group":
        return (k, tuple(it.get("techs") or ()))
    return (k, it.get("unit"), it.get("stat"), it.get("value"), it.get("delta"))


def py_shape(it):
    if not it:
        return None
    k = it.get("intent")
    if k == "tech.effect":
        return (k, it.get("tech"), it.get("command"))
    if k == "unit.attack_class":
        return (k, it.get("unit"), it.get("class_id"), it.get("kind"))
    if k in ("tech.research_time", "tech.cost"):
        return (k, it.get("tech"), it.get("resource"), it.get("value"), it.get("delta"),
                tuple(it.get("civs") or ()))
    if k == "tech.toggle_group":
        return (k, tuple(it.get("techs") or ()))
    return (k, it.get("unit"), it.get("stat"), it.get("value"), it.get("delta"))


def main():
    from aoe2mod.ui.server import App

    app = App()
    proc = subprocess.Popen(
        [EXE, "--port", str(PORT)],
        cwd=BUNDLE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bad = 0
    try:
        wait_ready(proc)
        print("%-24s %-30s %s" % ("sentence", "rust", "python"))
        for s in CASES:
            got = post("/api/parse", {"text": s, "pins": {}})
            it, why = rust(got)
            want = app.parse(s)
            pyint = (want.get("intents") or [None])[0]
            a, b = shape(it), py_shape(pyint)
            same = a == b
            if not same:
                bad += 1
            print("%-24s %-30s %s%s" % (
                s[:22], str(a)[:28], str(b)[:30], "" if same else "   MISMATCH"))
            if not same:
                print("    rust why : %s" % (why or ""))
                print("    py why   : %s" % (((want.get("clauses") or [{}])[0]).get("why") or ""))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    print("\nVERDICT")
    print("  sentences         = %d" % len(CASES))
    print("  disagreements     = %d (must be 0)" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

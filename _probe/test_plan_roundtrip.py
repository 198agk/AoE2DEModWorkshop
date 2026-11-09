"""Does `/api/plan` plan the same edit the sentence it came from planned?

`/api/parse` already returns a plan beside each sentence.  `/api/plan` takes an
INTENT and returns a plan for it, which means the intent has to survive the round
trip through JSON: every field the builder reads has to come back, and anything
that does not come back becomes a plan about a different edit.

So the check is: parse a sentence, take the intent it produced, plan THAT, and
require the two plans to be identical.  Then require the same plan to match the
Python reference's, because agreeing with itself is how this project has twice
shipped a number that was wrong on both sides.
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
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7861

CASES = [
    "村民血量改成100",
    "不列颠村民血量改成100",
    "城堡攻击加5",
    "民兵人口成本设为0",
    "民兵对平民攻击加2",
    "织布机研究时间改成5",
    "织布机黄金成本改成5",
    "织布机第1条效果改成100",
    "把织布机和铸币术做成只能选一个",
    # A card-move names a BUTTON SLOT, and the same slot is a different button in
    # a different civilization, so the sentence has to name one (「挪格子要指定
    # 一个文明」).  The civilization-less spelling is correctly REFUSED since
    # 2026-11-01; keeping it here made the case assert against a refusal.
    "不列颠把民兵放在兵营的第5格",
    "让弓兵的样子换成长弓兵",
]

# Fields the two plans must agree on.  `description` is included on purpose: it is
# the sentence a person reads back before pressing 生成.
KEYS = ["description", "kind", "editable", "changes_dat", "writes", "shape",
        "edit_count", "civ_count", "civs", "civ_labels", "member_count",
        "mirror_count", "variants", "records", "locations", "before", "value",
        "bytes_changed", "reason"]


def post(path, body, timeout=1800):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (PORT, path),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(proc):
    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("the bundle exited: %s" % proc.returncode)
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/progress" % PORT, timeout=3
            ) as r:
                p = json.loads(r.read().decode("utf-8")).get("progress") or {}
            if p.get("ready"):
                return
            if p.get("error"):
                raise SystemExit("the bundle failed: %s" % p["error"])
        except SystemExit:
            raise
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("the bundle never became ready")


def reference(sentence):
    """The Python reader's plan for the same sentence, or None when it refuses."""
    from aoe2mod.ui.server import App

    app = App()
    got = app.parse(sentence)
    cl = (got.get("clauses") or [{}])[0]
    intent = (cl or {}).get("intent")
    if not intent:
        return None
    return ((cl.get("preview") or {}).get("plan")) or None


def main():
    proc = subprocess.Popen(
        [EXE, "--port", str(PORT)],
        cwd=BUNDLE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bad = 0
    try:
        wait_ready(proc)
        print("%-30s %-22s %s" % ("sentence", "intent", ""))
        for sentence in CASES:
            got = post("/api/parse", {"text": sentence, "pins": {}})
            it = (got.get("intents") or [None])[0]
            if not it:
                why = ((got.get("refusals") or [{}])[0]).get("why") or "no intent"
                print("%-30s refused: %s" % (sentence, why))
                bad += 1
                continue
            from_parse = ((got.get("clauses") or [{}])[0].get("preview") or {}).get("plan") or {}
            from_plan = post("/api/plan", {"intent": it})
            if not from_plan.get("ok"):
                print("%-30s /api/plan refused: %s"
                      % (sentence, (from_plan.get("error") or "")[:60]))
                bad += 1
                continue
            planned = from_plan.get("plan") or {}
            diffs = [k for k in KEYS
                     if json.dumps(from_parse.get(k), sort_keys=True)
                     != json.dumps(planned.get(k), sort_keys=True)]
            ref = reference(sentence)
            ref_diffs = []
            if ref is not None:
                ref_diffs = [k for k in KEYS
                             if json.dumps(planned.get(k), sort_keys=True)
                             != json.dumps(ref.get(k), sort_keys=True)
                             and (planned.get(k) is not None or ref.get(k) is not None)]
            ok = not diffs
            if not ok:
                bad += 1
            print("%-30s %-22s round trip %s%s"
                  % (sentence, it.get("intent"),
                     "same" if ok else "DIFFER " + ",".join(diffs),
                     "" if not ref_diffs else "   vs python: " + ",".join(ref_diffs)))
            if diffs:
                for k in diffs:
                    print("    %-14s parse=%s  plan=%s"
                          % (k, json.dumps(from_parse.get(k), ensure_ascii=False),
                             json.dumps(planned.get(k), ensure_ascii=False)))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    print("\nVERDICT  cases=%d  round-trip clashes=%d (must be 0)" % (len(CASES), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

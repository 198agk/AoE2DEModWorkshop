"""Does the number the preview promises equal the number the build reports?

`edit_count` was filled from whichever field each builder happened to emit, and
three of the seven shapes emitted none at all -- so `织布机研究时间改成5`
previewed "0 edits" for an edit that writes one, and `把织布机和铸币术做成只能选
一个` previewed 0 while the build said 1.  A zero that means "this shape does not
report" is indistinguishable from a zero that means "nothing will happen", which
is the one reading a person must never be given.

The check is deliberately narrow: both numbers come from the same builder, so a
disagreement means the DRY path reports differently from the real one.  Two
paths that drift are how a preview becomes a second implementation.
"""
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import _paths as P

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7859

# One sentence per intent: the seven builders plus the stat path with and
# without a civilization scope, because the family expansion is what makes the
# two numbers large enough for an off-by-one to hide in.
CASES = [
    ("unit.stat", "村民血量改成100"),
    ("unit.stat (scoped)", "不列颠村民血量改成100"),
    ("unit.stat (mirror)", "城堡攻击加5"),
    ("unit.cost", "民兵人口成本设为0"),
    ("unit.attack_class", "民兵对平民攻击加2"),
    ("tech.research_time", "织布机研究时间改成5"),
    ("tech.cost", "织布机黄金成本改成5"),
    ("tech.effect", "织布机第1条效果改成100"),
    ("tech.toggle_group", "把织布机和铸币术做成只能选一个"),
    # A card-move names a BUTTON SLOT, and the same slot is a different button in
    # a different civilization, so the sentence has to name one (「挪格子要指定
    # 一个文明」).  The civilization-less spelling is correctly REFUSED since
    # 2026-11-01; keeping it here made the case assert against a refusal.
    ("unit.card_move", "不列颠把民兵放在兵营的第5格"),
    ("unit.sprite", "让弓兵的样子换成长弓兵"),
]


# A reset connection is not slow, it is gone: no timeout helps.  The build runs
# in a second process and is the slow request, so under a full-suite run (209
# suites, same disk) one of the eleven can be answered by a closed socket.  That
# produced `ConnectionResetError: [WinError 10054]` on 2026-11-07 and the suite
# exited 1 -- reporting "the preview and the build disagree", the one claim it
# exists to make, from a request that never got an answer.
WIRE_ERRORS = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError,
               http.client.RemoteDisconnected, http.client.BadStatusLine)


def post(path, body, timeout=1800, tries=4):
    """POST and re-send if the socket died before answering.

    A retry must not look like a second edit: `/api/build` writes a mod folder
    named after `title`, so each attempt gets a fresh title and cannot land in
    the folder the previous attempt was writing.  The caller compares counts, and
    a count does not depend on the title.
    """
    last = None
    for attempt in range(1, tries + 1):
        attempt_body = dict(body)
        if "title" in attempt_body:
            attempt_body["title"] = "%s a%d" % (body["title"], attempt)
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (PORT, path),
            data=json.dumps(attempt_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except WIRE_ERRORS as exc:
            last = exc
            print("  %s  %s (attempt %d/%d): %s: %s"
                  % (path, (body.get("title") or ""), attempt, tries,
                     type(exc).__name__, exc))
            if attempt < tries:
                time.sleep(2.0 * attempt)
    raise SystemExit("the bundle never answered %s: %s: %s"
                     % (path, type(last).__name__, last))


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
        print("%-22s %-30s %8s %8s  %s" % ("intent", "sentence", "preview", "build", ""))
        for want, sentence in CASES:
            got = post("/api/parse", {"text": sentence, "pins": {}})
            it = (got.get("intents") or [None])[0]
            if not it:
                why = ((got.get("refusals") or [{}])[0]).get("why") or "no intent"
                print("%-22s %-30s  refused: %s" % (want, sentence, why))
                bad += 1
                continue
            plan = ((got.get("clauses") or [{}])[0].get("preview") or {}).get("plan") or {}
            built = post("/api/build", {
                "intents": [it],
                "title": "counts %d" % int(time.time()),
                "install": False,
            })
            if not built.get("ok"):
                print("%-22s %-30s  build refused: %s"
                      % (want, sentence, (built.get("error") or "")[:60]))
                bad += 1
                continue
            pv = plan.get("edit_count")
            be = built.get("edit_count")
            same = pv == be
            if not same:
                bad += 1
            print("%-22s %-30s %8s %8s  %s"
                  % (want, sentence, pv, be, "same" if same else "DIFFER"))
            # The description is the other half of the promise: an empty one
            # tells the player nothing about what is about to be written.
            if not (plan.get("description") or "").strip():
                bad += 1
                print("    the preview has no description")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    print("\nVERDICT  cases=%d  preview/build count clashes=%d (must be 0)"
          % (len(CASES), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

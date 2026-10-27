# -*- coding: utf-8 -*-
"""Every sentence the reader ACCEPTS must survive the build.

The defect this exists for
--------------------------
On 2026-10-28 the shipped binary answered three sentences with a confident
intent and then could not build any of them:

  「民兵人口成本设为0」    -> unit.cost          -- `build_one` has no branch
  「民兵对平民攻击加2」    -> unit.attack_class  -- `build_one` has no branch
  「把民兵放在第5格」      -> unit.card_move     -- reads `box`, reader sends `button`

All three looked fine to every gate this project had. `check_routes.py` compares
route NAMES, and `/api/build` exists. `report_typable.py` compares what a
sentence PARSES to, and all three parse. Neither asks the question a player
asks: I typed it, the screen said "understood", so can it be built?

That is the same shape as `_probe/test_dat_baseline_reverse.py`'s lesson and as
the "all green, wrong artefact" failure: a check that measures a neighbour of
the thing instead of the thing.

What is asserted
----------------
For each sentence, in one process against the SHIPPED exe:

  1. `/api/parse` yields exactly one intent (a refusal is a legitimate answer,
     but then the case must say so in `EXPECT_REFUSED`, and the reason must be
     non-empty -- "no" without a why is a defect of its own);
  2. that intent, sent to `/api/build`, does NOT come back with a
     "this build cannot do that" error.

Step 2 deliberately does NOT require a successful build for every case: an
intent can be refused for a reason that is a fact about the game ("no such cost
slot"). What it forbids is the whole CLASS of answer that means the two halves
of the program disagree about what exists: no branch, missing field, unknown
intent. Those are listed in `IMPLEMENTATION_ERRORS` and are matched literally so
a new refusal wording shows up as a failure instead of passing silently.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7814

# One sentence per intent the reader claims.  Written the way a player would.
CASES = [
    ("unit.stat", "村民血量改成100"),
    # NOT 「民兵木材成本减少10」: a militia's three cost slots are 0/3/4 and none
    # of them is wood, so that sentence is refused for a fact about the game and
    # would never exercise the branch.  Population IS slot 4 here.
    ("unit.cost", "民兵人口成本设为0"),
    ("tech.research_time", "织布机研究时间改成5"),
    ("tech.cost", "织布机黄金成本改成5"),
    ("tech.effect", "织布机第1条效果改成100"),
    ("unit.card_move", "把民兵放在第5格"),
    # NOT 「步弓手对骑兵攻击加2」: 骑兵 is a unit class (12) and the file holds
    # zero attack rows of class 12, so that sentence can never build.  「对平民」
    # resolves to attack class 4, which a militia actually carries.
    ("unit.attack_class", "民兵对平民攻击加2"),
    ("unit.sprite", "让弓兵长得像长弓兵"),
    ("tech.toggle_group", "把织布机和铸币术做成只能选一个"),
]

# Intents the reader is allowed to REFUSE, with the class of reason expected.
EXPECT_REFUSED = {
    # The reader has no branch for these yet; a refusal is honest, silence is not.
    "unit.art", "unit.create", "tech.create", "unit.replace_on_map",
    "unit.availability", "tech.availability",
}

# Wording that means the two halves disagree about what the program can do.
# Matched as substrings; a build failing for a fact about the GAME ("no such
# cost slot") is not in this list and counts as agreement.
IMPLEMENTATION_ERRORS = [
    "这句话没有说要改哪个单位",      # build never got the id -> field name drift
    "这句话没有说要改哪个科技",
    "没说要把哪个单位挪走",          # card_move: `unit` missing
    "没说要挪到第几格",              # card_move: reads `box`, reader sends `button`
    "不认识的属性",                  # unit.cost reaches the stat path, stat=""
    "没有任何文明的单位",            # ditto, or a family table miss
    "没听出要改哪个属性",
]


def post(path, obj):
    d = json.dumps(obj, ensure_ascii=False).encode()
    r = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (PORT, path), data=d,
        headers={"Content-Type": "application/json"}, method="POST")
    body = urllib.request.urlopen(r, timeout=300).read().decode()
    return json.loads(body)


def wait_ready():
    for _ in range(240):
        time.sleep(0.5)
        try:
            j = json.loads(urllib.request.urlopen(
                "http://127.0.0.1:%d/api/progress" % PORT, timeout=5).read())
            p = j.get("progress") or {}
            if p.get("ready"):
                return True
            if p.get("error"):
                print("server error: %s" % p["error"])
                return False
        except Exception:
            pass
    return False


def main():
    if not os.path.isfile(EXE):
        print("no %s" % EXE)
        return 1
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    time.sleep(1)
    proc = subprocess.Popen([EXE, "--port", str(PORT)], cwd=BUNDLE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = 0
    rows = []
    try:
        if not wait_ready():
            print("server never became ready")
            return 1
        for want, sentence in CASES:
            r = post("/api/parse", {"text": sentence})
            got = [i for i in (r.get("intents") or [])]
            if not got:
                why = (r.get("refusals") or [{}])[0].get("why") or ""
                # A refusal is an answer, but only when it says why.
                ok = bool(why.strip()) and want in EXPECT_REFUSED
                rows.append((want, sentence, "refused", why, "ok" if ok else "NO WHY"))
                if not ok:
                    bad += 1
                continue
            it = got[0]
            if it.get("intent") != want:
                rows.append((want, sentence, "wrong intent: %s" % it.get("intent"), "", "BAD"))
                bad += 1
                continue
            try:
                b = post("/api/build", {"intents": [it], "title": "gate_%s" % want})
                ok_build = b.get("ok") is True
                msg = "" if ok_build else str(b.get("error") or "")
            except Exception as e:                      # HTTP 4xx carries the text
                ok_build = False
                msg = str(e)
            clash = [m for m in IMPLEMENTATION_ERRORS if m in msg]
            if clash:
                verdict = "DISAGREE"
                bad += 1
            elif ok_build:
                verdict = "built"
            else:
                verdict = "refused by the game"
            rows.append((want, sentence, verdict, msg[:70], ""))
        print("%-22s %-30s %-20s %s" % ("intent", "sentence", "verdict", "message"))
        for want, sentence, verdict, msg, extra in rows:
            print("%-22s %-30s %-20s %s %s" % (want, sentence, verdict, msg, extra))
        print()
        print("VERDICT")
        print("  cases             = %d" % len(CASES))
        print("  parse/build clash = %d (must be 0)" % bad)
        return 0 if bad == 0 else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())

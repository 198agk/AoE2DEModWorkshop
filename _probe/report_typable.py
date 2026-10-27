# -*- coding: utf-8 -*-
"""What can actually be TYPED, measured rather than claimed.

The screen lists 14 intents and marks the ones a sentence cannot reach. That mark
comes from `intent_is_reachable`, which is a list I maintain by hand -- so it can
drift from reality in both directions. This probes every intent with a real
sentence through the SHIPPED binary and reports what came back.

Two outcomes matter and they are different:
  * the sentence produced the intent  -> a player can type it;
  * the sentence was refused           -> it cannot, and the refusal says why.

An intent marked reachable that refuses is the defect this project keeps fixing
(a screen promising what the reader cannot deliver).
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7813

# One sentence per intent, written the way a player would.
CASES = [
    ("unit.stat", "村民血量改成1000"),
    ("unit.cost", "民兵木材成本减少10"),
    ("tech.research_time", "织布机研究时间改成5"),
    ("tech.cost", "织布机黄金成本改成5"),
    ("tech.effect", "织布机第1条效果改成100"),
    ("unit.card_move", "把民兵放在第5格"),
    ("unit.attack_class", "步弓手对骑兵攻击加2"),
    # The ones expected to refuse -- listed so a change is visible.
    ("unit.sprite", "让弓兵长得像长弓兵"),
    ("unit.art", "把村民的图换成 new.png"),
    ("unit.create", "照着民兵做一个新单位叫铁匠学徒"),
    ("tech.create", "照织布机做一项新科技叫铁匠手艺"),
    ("tech.toggle_group", "把织布机和铸币术做成只能选一个"),
    ("unit.availability", "让不列颠能造蔷琵侦察兵"),
    ("tech.availability", "让不列颠能研究火枪手"),
    ("unit.replace_on_map", "开局把村民换成斥候骑兵"),
]


def post(path, obj):
    d = json.dumps(obj, ensure_ascii=False).encode()
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=d,
                               headers={"Content-Type": "application/json"},
                               method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())


def main():
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    time.sleep(1)
    p = subprocess.Popen([EXE, "--port", str(PORT)], cwd=BUNDLE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = []
    try:
        for _ in range(120):
            time.sleep(0.5)
            try:
                j = json.loads(urllib.request.urlopen(
                    "http://127.0.0.1:%d/api/progress" % PORT, timeout=5).read())
                if (j.get("progress") or {}).get("ready"):
                    break
            except Exception:
                pass

        meta = json.loads(urllib.request.urlopen(
            "http://127.0.0.1:%d/api/meta" % PORT, timeout=30).read())
        claimed = {i["id"]: i["by_sentence"] for i in (meta.get("intents") or [])}

        for intent_id, sentence in CASES:
            r = post("/api/parse", {"text": sentence})
            got = [i.get("intent") for i in (r.get("intents") or [])]
            refused = [x.get("why") for x in (r.get("refusals") or [])]
            typed = intent_id in got
            rows.append({
                "intent": intent_id,
                "sentence": sentence,
                "typed": typed,
                "claimed": claimed.get(intent_id),
                "got": got,
                "why": (refused[0] if refused else "")[:70],
            })
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

    print("%-22s %-7s %-8s %s" % ("intent", "typed", "claimed", "note"))
    print("-" * 96)
    bad = []
    for r in rows:
        note = "" if r["typed"] else (r["why"] or "refused")
        print("%-22s %-7s %-8s %s"
              % (r["intent"], "YES" if r["typed"] else "no",
                 r["claimed"], note))
        # A claimed-reachable intent that refuses, or vice versa, is a lie on the
        # screen -- that is what this check exists for.
        if r["claimed"] is not None and r["claimed"] != r["typed"]:
            bad.append(r["intent"])

    print()
    yes = sum(1 for r in rows if r["typed"])
    print("TYPABLE: %d of %d" % (yes, len(rows)))
    if bad:
        print("DISAGREES WITH THE SCREEN: %s" % bad)
        return 1
    print("screen and reader agree on every intent")
    return 0


if __name__ == "__main__":
    sys.exit(main())

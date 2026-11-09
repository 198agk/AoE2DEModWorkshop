# -*- coding: utf-8 -*-
"""Measure how much real spoken Chinese the reader actually understands.

WHY THIS EXISTS
---------------
Every other suite in this folder asks "does this sentence do the right thing".
None of them asks "how many sentences does it understand at all", so progress on
the reader was invisible: the fixes went in one at a time and nobody could say
whether the tool was getting easier to use, which is the whole point of it.

This is a MEASUREMENT, not a pin.  It prints a percentage and exits 0 whatever
that percentage is; it is registered in `probe_suite_registry.py` as such, not
in `run_suites.py`, because a corpus of opinions cannot be a regression gate --
the day someone deliberately rejects a sentence, a percentage gate would call a
correct refusal a failure.

How to read the output:
  PASS     the reader produced a clause that is buildable (a real intent and a
           real entity).  That sentence can become a mod.
  ANSWER   it is a question and the reader answered it.  Also a success.
  REFUSED  it was understood as "not a thing I can do" and said why in words a
           player can act on.  Counted separately: some of these are the RIGHT
           answer (「所有科技研究时间减10%」 has no such concept -- a technology
           has no category to say "all of them") and some are a gap the reader
           should close.  The goal is not 100% PASS.
  SILENT   it produced nothing at all: no clause, no refusal, no answer.  This
           is the only line that is always a defect.

Usage
    python -X utf8 _probe/nl_corpus.py               # starts its own server
    python -X utf8 _probe/nl_corpus.py --url http://127.0.0.1:7811/
    python -X utf8 _probe/nl_corpus.py --show-pass
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Written the way a player talks in a group chat, not the way the schema reads:
# short, no punctuation, trade words mixed with slang, occasionally typo'd.
# Every line was typed by someone who wanted a thing done, so a line the reader
# cannot use is a line a player cannot use either.
CORPUS = [
    # --- the 15 intents, in the words people actually used --------------
    "村民血量改成1000",
    "村民血量改1000",
    "把村民的血量改成1000",
    "村民血亮改成1000",
    "不列颠村民血量改成1000",
    "所有文明村民血量改成1000",
    "剑士血量加到200",
    "长弓兵攻击加5",
    "弓箭手射程加1",
    "骑士移动速度改成2",
    "步弓手对骑兵攻击加2",
    "弓箭手木材成本加10",
    "所有步兵木材造价减10%",
    "长枪兵造价便宜点",
    "织布机研究时间减5",
    "所有科技研究时间减10%",
    "织布机木材成本加10",
    "织布机第1条效果加5",
    "不列颠不能造火枪兵",
    "不列颠不能研究织布机",
    "把村民的样子换成步弓手",
    "给村民换图片 我的图.png",
    "不列颠照村民做一个新单位，叫铁匠学徒，放在第5格",
    "把锻造和步兵鳞甲做成只能选一个",
    "不列颠照织布机做一项新科技，叫细麻布",
    "开局时把村民换成斥候骑兵",
    "不列颠把民兵放在第5格",
    # --- speech habits: measure words, degrees, comparisons ------------
    "骑兵血量翻倍",
    "骑兵血量减半",
    "弓箭手攻击力提高一倍",
    "村民血量加百分之二十",
    "村民血量加两成",
    "一千五的血量给村民",
    "投石车血量改成一千二",
    "让弓箭手更便宜",
    "弓箭手太贵了",
    "骑兵血太少了",
    "骑兵血量再高一点",
    "射程比弓箭手更远",
    "比剑士血量高",
    "攻速快一点",
    "造得快一点",
    # --- 繁体 ---------------------------------------------------------
    "火槍兵血量改成500",
    "遊俠攻擊力加3",
    # --- questions (a first-class feature, not a failure) --------------
    "村民血量是多少",
    "弓箭手攻击力是多少",
    "织布机研究时间是多少",
    "村民造价是多少",
    "谁能造手推炮",
    "谁不能造手推炮",
    "谁能造城堡",
    "谁有织布机",
    "哪些文明能造火枪兵",
    # --- refusals that SHOULD be refusals, and must say why ------------
    "所有单位血量加10",
    "砍树速度加10%",
    "谁能打过谁",
    "这是什么",
    "村民血量",
    # --- class-wide edits ----------------------------------------------
    "所有骑兵血量加10%",
    "所有步兵移动速度加10%",
    "所有建筑血量加500",
]


def free_port(start=7980):
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn_server():
    """Start the page's own engine so the number is about THIS tree.

    An ambient 7811 may be a build from an hour ago; a corpus that measures a
    stale reader is worse than no corpus, because it reads as progress.
    """
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u",
         os.path.join(ROOT, "tools", "run_ui.py"),
         "--serve-only", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d/" % port
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(url + "api/meta", timeout=3) as r:
                if b'"ok"' in r.read():
                    return proc, url
        except Exception:                                # noqa: BLE001
            pass
        time.sleep(0.5)
    try:
        proc.kill()
        proc.wait(timeout=20)
    except Exception:                                    # noqa: BLE001
        pass
    return None, url


def parse(url, sentence):
    body = json.dumps({"text": sentence}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url + "api/parse", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def classify(row):
    """One word per sentence, so the percentage means something specific.

    Not `ok` / `not ok`: the interesting difference is between "I cannot do
    that and here is why" (a refusal a player can act on, often the CORRECT
    answer) and "nothing happened" (always a defect).
    """
    clauses = row.get("clauses") or []
    if not clauses:
        return "SILENT", ""
    if any(c.get("question") for c in clauses):
        return "ANSWER", "question"
    if any(c.get("who") for c in clauses):
        return "ANSWER", "who"
    buildable = [c for c in clauses if c.get("intent")]
    if buildable:
        return "PASS", buildable[0]["intent"].get("intent", "")
    why = (clauses[0].get("why") or "").strip()
    if why:
        return "REFUSED", why
    return "SILENT", "no intent, no why"


def main(argv):
    url = None
    if "--url" in argv:
        url = argv[argv.index("--url") + 1]
    show_pass = "--show-pass" in argv

    server = None
    if url is None:
        server, url = spawn_server()
        if server is None:
            print("NO SERVER: `tools/run_ui.py` did not answer /api/meta at %s"
                  % url)
            return 1
    print("corpus: %d sentences   server %s\n" % (len(CORPUS), url))

    counts = {}
    silent, refused = [], []
    try:
        for s in CORPUS:
            try:
                row = parse(url, s)
            except Exception as exc:                     # noqa: BLE001
                print("  ERROR    %-42s %s" % (s, exc))
                counts["ERROR"] = counts.get("ERROR", 0) + 1
                continue
            kind, detail = classify(row)
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "SILENT":
                silent.append((s, detail))
                print("  SILENT   %-42s %s" % (s, detail))
            elif kind == "REFUSED":
                refused.append((s, detail))
                print("  refused  %-42s %s" % (s, detail[:70]))
            elif show_pass:
                print("  %-8s %-42s %s" % (kind.lower(), s, detail))
    finally:
        if server is not None:
            try:
                server.kill()
                server.wait(timeout=20)
            except Exception:                            # noqa: BLE001
                pass

    total = sum(counts.values())
    passed = counts.get("PASS", 0)
    answered = counts.get("ANSWER", 0)
    rate = 100.0 * (passed + answered) / total if total else 0.0
    print("\n" + "=" * 72)
    for k in ("PASS", "ANSWER", "REFUSED", "SILENT", "ERROR"):
        if counts.get(k):
            print("  %-8s %3d" % (k, counts[k]))
    print("  %-8s %3d" % ("TOTAL", total))
    print("\n  understood (PASS + ANSWER): %d/%d = %.1f%%"
          % (passed + answered, total, rate))
    print("  a refusal is not a failure: %d sentence(s) got a reason in words"
          % counts.get("REFUSED", 0))
    print("  SILENT is always a defect: %d" % counts.get("SILENT", 0))
    if refused:
        print("\n  the refusals, so a human can judge which are a gap:")
        for s, why in refused:
            print("    %-40s %s" % (s, why[:64]))
    print("=" * 72)

    # Exit 0 even with SILENT lines: this is a measurement.  A percentage that
    # can fail is a percentage somebody games by deleting the hard sentences.
    if silent:
        print("NOTE: %d silent sentence(s) -- see the lines above." % len(silent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

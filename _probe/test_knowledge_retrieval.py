# -*- coding: utf-8 -*-
"""The corpus index answers the six questions this tool exists to answer.

Each case below is a question a player actually typed, paired with the volume
that documents it.  They are here because the ranking is hand-written (no fts5
term matches a two-character Chinese query on this sqlite build, and the
project ships no third-party packages), so a change to the weights can silently
move `触发器怎么让单位走` onto a changelog -- and a confident wrong citation is
worse than no answer at all.

`今天天气怎么样` is the negative case: the corpus has nothing to say about it,
and the honest output is zero hits.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod import knowledge                      # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    if ok:
        print("  ok %s" % label)
    else:
        FAILS.append(label)
        print("FAIL %s :: %s" % (label, detail))


def top(question, n=3):
    return knowledge.search(question, limit=n)


def main():
    if not knowledge.available():
        print("knowledge.db missing; run tools/build_knowledge.py first")
        raise SystemExit(1)

    st = knowledge.stats()
    check("the index covers the whole corpus",
          st.get("chunks", 0) > 3000 and len(st.get("docs") or []) >= 30,
          (st.get("chunks"), len(st.get("docs") or [])))

    print("A  an effect question lands on the effect reference")
    for q, want in (("触发器怎么让单位走", "Task Object"),
                    ("怎么冻结单位", "Freeze Object"),
                    ("杀死一个单位", "Kill Object"),
                    ("怎么让单位巡逻", "Patrol"),
                    ("显示文字提示玩家", "Display Instructions")):
        hits = top(q, 1)
        got = hits[0]["section"] if hits else ""
        check("%s -> %s" % (q, want), want in got, got[-60:])

    print("B  a script question lands on the volume, not on a log")
    hits = top("随机地图怎么生成森林", 1)
    check("random map scripting -> 12-RMS",
          bool(hits) and "12-RMS" in hits[0]["doc"],
          hits[0]["doc"] if hits else "no hits")
    hits = top("怎么打包mod发布", 1)
    check("mod packaging -> 09-Mod",
          bool(hits) and "09-Mod" in hits[0]["doc"],
          hits[0]["doc"] if hits else "no hits")
    hits = top("cHitpoints 是什么", 1)
    check("a constant lands on 05-XS",
          bool(hits) and "05-XS" in hits[0]["doc"],
          hits[0]["doc"] if hits else "no hits")

    print("C  the index refuses instead of guessing")
    check("off-topic question returns nothing", top("今天天气怎么样") == [],
          [h["doc"] for h in top("今天天气怎么样")])
    check("empty question returns nothing", knowledge.search("") == [])

    print("D  every hit carries the line it came from")
    hits = top("触发器怎么让单位走", 3)
    check("hits name a file, a section and a line",
          all(h["doc"] and h["section"] and h["line"] > 0 for h in hits),
          hits[0] if hits else "no hits")

    print("E  the pack stays inside the prompt budget")
    text = knowledge.pack(hits, budget=1200)
    check("packing respects the budget", len(text) < 4000, len(text))
    check("packing names the volume", "06-场景" in text, text[:80])

    print()
    if FAILS:
        print("KNOWLEDGE RETRIEVAL: %d CHECK(S) FAILED" % len(FAILS))
        raise SystemExit(1)
    print("KNOWLEDGE RETRIEVAL: EVERY QUESTION LANDS ON THE VOLUME THAT ANSWERS IT")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Every sentence the two rule boxes OFFER must compile.

WHY THIS PIN EXISTS
-------------------
`_probe/test_field_search_hint.py` (2026-11-04) found the 找字段 box naming
fields three tables do not have.  The same question, asked of the AI/XS rule
boxes, found the same kind of lie in a worse place:

    #lang-xs-text  placeholder = 「例如：把 goal 0 设成 1」

That sentence produced NOTHING.  `aoe2mod/game/ainl.py`'s `ACTIONS` table had no
verb for writing a goal, so the reader answered 没有读出动作 and the box the
player was invited to type into returned an empty `code`.  It had been that way
since the box was built, and no suite watched it, because every existing pin
tested the sentences in `ainl.EXAMPLES` -- the chips -- and not the placeholder.

WHAT IT CHECKS
--------------
1. every sentence in `ainl.EXAMPLES[dept]` (the chips the page paints) compiles;
2. the placeholder sentence of `#lang-ai-text` and `#lang-xs-text`, read out of
   `index.html` as TEXT (so editing the copy re-runs the promise), compiles;
3. both departments can WRITE a goal: `xsSetGoal(N, M)` / `(set-goal N M)`.
   That is the one capability the placeholder was promising, and the read half
   (`xsGetGoal`) already existed -- a bridge with only one direction is a box
   that can look and not touch.

WHAT IT DOES NOT DO
-------------------
It does not require the emitted code to be *interesting*, and it does not pin
the wording of a refusal.  A refusal that rewords itself is not a regression.
A sentence that used to compile and now produces nothing is.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.game import ainl                        # noqa: E402
from aoe2mod.ui import server as S                   # noqa: E402

FAILS = []


def ck(what, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (("  ::  %r" % (detail,))
                                                    if not ok else ""))
    if not ok:
        FAILS.append((what, detail))


def placeholder_of(elem_id):
    """The placeholder text of one tag, read straight out of the page."""
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()
    m = re.search(r'<(?:textarea|input)[^>]*id="%s"[^>]*placeholder="((?:[^"\\]|\\.)*)"'
                  % re.escape(elem_id), page, re.S)
    return m.group(1).replace("&quot;", '"') if m else None


def main():
    app = S.App()
    voc = app.ailang_vocab()

    # --- 1. the chips ------------------------------------------------------
    print("-- chips (ainl.EXAMPLES)")
    for dept in ("ai", "xs"):
        for s in ainl.EXAMPLES[dept]:
            r = ainl.translate(s, dept, voc).as_dict()
            ck("%s chip %r compiles" % (dept, s), bool(r["code"]), r["why"])
            ck("%s chip %r passes the checker" % (dept, s),
               not r["diagnostics"], r["diagnostics"])

    # --- 2. the placeholders ----------------------------------------------
    print("-- placeholders (what the page tells the player to type)")
    for dept in ("ai", "xs"):
        raw = placeholder_of("lang-%s-text" % dept)
        ck("%s box still has a placeholder" % dept, bool(raw), raw)
        if not raw:
            continue
        # 「例如：X」 -- the offer is the part after the colon.
        sent = raw.split("：", 1)[-1].strip()
        ck("%s placeholder is a sentence, not a description" % dept,
           len(sent.split()) <= 12 and bool(sent), sent)
        r = ainl.translate(sent, dept, voc).as_dict()
        ck("%s placeholder %r compiles" % (dept, sent), bool(r["code"]), r["why"])
        ck("%s placeholder %r passes the checker" % (dept, sent),
           not r["diagnostics"], r["diagnostics"])

    # --- 3. the goal bridge has both directions ---------------------------
    print("-- the goal bridge (read half existed; write half is what the box promised)")
    for dept, want in (("xs", "xsSetGoal(0, 1);"), ("ai", "(set-goal 0 1)")):
        r = ainl.translate("把 goal 0 设成 1", dept, voc).as_dict()
        ck("%s can write goal 0 = 1" % dept, want in (r["code"] or ""), r["code"])
    r = ainl.translate("把 goal 0 设成 1", "xs", voc).as_dict()
    ck("the write uses two numbers, in order (goal id first)", "xsSetGoal(0, 1);"
       in (r["code"] or ""), r["code"])
    # The read half still works and still asks for ONE number.
    r = ainl.translate("村民不少于20个", "xs", voc).as_dict()
    ck("the read half still returns xsGetGoal", "xsGetGoal(20)" in (r["code"] or ""),
       r["code"])

    # --- 4. a named goal must not be refused as out of range --------------
    # `AGE-AI与XS-全面解析.md:153` gives 0-~4000 and lists 3001-3060 / 4001-4061
    # as hard-coded arrays; the old 0-511 bound refused the engine's own idioms.
    print("-- the range check must not refuse goals the engine itself uses")
    r = ainl.translate("goal 3004 设为 7", "xs", voc).as_dict()
    ck("goal 3004 (an ailib array pointer) is writable", "xsSetGoal(3004, 7)"
       in (r["code"] or ""), r["why"])
    r = ainl.translate("把 goal 5000 设成 1", "xs", voc).as_dict()
    ck("a goal beyond the array is still refused, in Chinese",
       not r["code"] and "goal 号" in r["why"], r["why"])

    # --- 5. and it must not swallow the sentence box's own vocabulary -----
    # `设成` / `设为` are the sentence box's assignment words.  Teaching the rule
    # reader to write goals is only safe because every keyword carries `goal`.
    print("-- the new verb must not steal 「把血量设成 1000」")
    for s in ("把村民血量设成 1000", "让掷矛手便宜 5 木材"):
        ck("the sentence box still reads %r" % s,
           bool((app.parse(s, []) or {}).get("clauses")), s)
    r = ainl.translate("把血量设成1000", "xs", voc).as_dict()
    ck("the rule reader refuses it instead of emitting a goal write",
       not r["code"], r["code"])

    print()
    if FAILS:
        print("RULE BOX EXAMPLES: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("RULE BOX EXAMPLES: EVERY SENTENCE THE TWO BOXES OFFER COMPILES, AND "
          "THE GOAL BRIDGE WRITES AS WELL AS READS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

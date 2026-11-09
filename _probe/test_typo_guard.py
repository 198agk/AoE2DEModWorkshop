# -*- coding: utf-8 -*-
"""A refusal that names a REAL mechanism must survive typo repair.

Measured 2026-11-01, found by the 61-sentence corpus:

    所有步兵砍树速度加10%   -> unit.stat unit_class=6 movement_speed +10%

The gather-rate refusal was correct and said which task row the number lives in.
But the sentence names no entity (the class word is the target), so
`_typo_worth_trying` took the "nothing was recognised" branch, and 树速度 was
repaired to 速度 -- turning a per-resource gather rate into a WALK SPEED edit of
all 217 infantry.  A wrong edit is worse than a refusal, and this one was built
out of the refusal itself.

The guard is a list of refusal sentences that are ANSWERS: each names a real
mechanism (a per-resource task row, one file per civilization, 188 records in a
category, no tech classes).  One slipped character cannot explain those away.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    import contextlib
    import io

    from aoe2mod.ui import nl as N
    from aoe2mod.ui import server as S

    with contextlib.redirect_stdout(io.StringIO()):
        a = S.App()
    vocab = a.vocab()

    def read(text):
        with contextlib.redirect_stdout(io.StringIO()):
            return N.read(text, vocab, civ_names=a.tk.civ_names,
                          civ_zh=N.CIV_ZH, unit_class=a.tk.unit_class,
                          producers=a.tk.unit_producers,
                          tech_cost=a.tk.tech_single_cost)

    print("\n=== 1. a truthful refusal is not 'repaired' into a wrong edit ===")
    # The exact sentence that regressed.  Asserting "no intent" is the whole
    # point: the failure mode was an intent WITH a plausible-looking field.
    intents, clauses = read("所有步兵砍树速度加10%")
    check("a class gather-rate sentence stays refused", not intents, intents)
    why = clauses[0].why if clauses else ""
    check("and the refusal still names the task row", "任务行" in why, why[:80])
    check("it does NOT become a walk-speed edit",
          not any(i.get("stat") == "movement_speed" for i in intents), intents)

    # Same shape, single entity: this one always refused correctly and still must.
    intents, clauses = read("村民砍树速度加10%")
    check("the single-unit spelling still refuses too", not intents, intents)

    print("\n=== 2. every terminal sentence is really terminal ===")
    # Each of these names a limit that no single-character slip can remove.
    for text, why_frag in (
            ("所有步兵砍树速度加10%", "不是一个数"),
            # This one says 「一个文明一份的文件，一句话改不了全部 63 个」 -- the
            # mechanism is "one file per civilization", which binds it to the
            # terminal list by 一句话改不了全部.
            ("所有文明都能造手推炮", "一句话改不了全部"),
            ("骑兵血量翻倍", "是一类单位"),
            ("所有科技研究时间减10%", "还不能一句话改")):
        intents, clauses = read(text)
        why = clauses[0].why if clauses else ""
        check("%s is refused with its mechanism named" % text,
              not intents and why_frag in why, why[:70])

    print("\n=== 3. a real slip is still repaired ===")
    # The guard must not close the door it was never meant to close: these have
    # NO explanation of their own, so one slipped character is the best guess.
    for text, entity, field in (
            ("剑土血量加20", 1974, "hit_points"),
            ("长弓冰射程加1", 8, "max_range"),
            ("村民血亮改成1000", 1810, "hit_points")):
        intents, clauses = read(text)
        check("%s is still repaired" % text,
              bool(intents) and intents[0].get("unit") == entity
              and intents[0].get("stat") == field, intents)

    print("\n=== 4. the terminal list is not dead text ===")
    check("the guard reads a table, not inline literals",
          isinstance(getattr(N, "_TERMINAL_WHY", None), tuple)
          and len(N._TERMINAL_WHY) >= 5, getattr(N, "_TERMINAL_WHY", None))

    print()
    if FAILS:
        print("TYPO GUARD: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("TYPO GUARD: A REFUSAL THAT NAMES A REAL LIMIT SURVIVES REPAIR, AND A "
          "REAL SLIP STILL GETS FIXED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

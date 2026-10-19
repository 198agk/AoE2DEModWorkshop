# -*- coding: utf-8 -*-
"""How much of what a Chinese player reads is still English?

The product builds its own sentences ("印加 不再能建造 蔷琵侦察兵") and the screen
prints them verbatim -- which is right, because a second layer of wording would
drift from the first.  But several are still English prose with Chinese nouns
spliced in, e.g.

    nothing would change: 村民 (男性) stays at its current 生命值

A player reads that as a half-translated program.  This probe MEASURES it on a
handful of REAL intents -- one legal edit, one refusal, per intent family -- and
classifies every user-visible string as chinese / mixed / english.

It is a probe, not a suite: the counts are the finding.  Re-run after touching
any message.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{2,}")

#: Prose a player reads.  `writes` is a path and `mode` an enum -- neither is
#: prose, and translating them would be wrong.
PROSE = ("description", "reason")

CASES = [
    # a legal edit, per family -- exercises the SUCCESS wording
    ("unit.stat ok", {"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                      "value": 1000}),
    ("unit.cost ok", {"intent": "unit.cost", "unit": 83, "resource": "wood",
                      "delta": 10}),
    ("tech.research_time ok", {"intent": "tech.research_time", "tech": 22,
                               "delta": 5}),
    ("tech.cost ok", {"intent": "tech.cost", "tech": 22, "resource": "food",
                      "delta": 10}),
    ("availability revoke ok", {"intent": "unit.availability", "unit": 2550,
                                "civ": "INCAS", "action": "revoke"}),
    # refusals -- exercises the wording a player sees when the edit cannot happen
    ("unit.stat no-op", {"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                         "delta": 0}),
    ("availability already has it", {"intent": "unit.availability", "unit": 83,
                                     "civ": "AZTECS", "action": "grant"}),
    ("tech.research_time no-op", {"intent": "tech.research_time", "tech": 22,
                                  "delta": 0}),
]


def classify(text):
    if not text:
        return "empty"
    has_zh = bool(CJK.search(text))
    has_en = bool(LATIN.search(text))
    if has_zh and has_en:
        return "mixed"
    return "chinese" if has_zh else "english"


def main():
    tk = A.open_toolkit(game_root=GAME)
    counts = {"english": 0, "mixed": 0, "chinese": 0, "empty": 0}
    rows = []
    for label, raw in CASES:
        try:
            plan = tk.plan(raw)
        except Exception as exc:                            # noqa: BLE001
            note = "%s: %s" % (type(exc).__name__, exc)
            counts[classify(note)] += 1
            rows.append((label, "raise", classify(note), note))
            continue
        found = False
        for field in PROSE:
            text = plan.get(field)
            if text:
                found = True
                kind = classify(str(text))
                counts[kind] += 1
                rows.append((label, field, kind, str(text)))
        if not found:
            counts["empty"] += 1
            rows.append((label, "-", "empty", "(no description)"))

    print("=" * 72)
    for label, field, kind, text in rows:
        mark = "  " if kind == "chinese" else "!!"
        print("%s %-30s %-12s %s" % (mark, label, field, text[:110]))
    print("=" * 72)
    print("counts: %s" % counts)
    bad = counts["english"] + counts["mixed"]
    print("%d of %d user-visible strings are not clean Chinese"
          % (bad, sum(counts.values())))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

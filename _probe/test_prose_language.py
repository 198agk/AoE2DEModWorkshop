# -*- coding: utf-8 -*-
"""Everything a player reads must be Chinese, and must name real things.

The screen prints the product's own sentences verbatim -- that is deliberate, so
a second layer of wording cannot drift from the first -- which means the wording
has to be right where it is produced, in `compiler.py` and `availability.py`.

Measured starting point, 2026-10-19:
    8 of 12 user-visible strings were mixed English/Chinese, e.g.
    "nothing would change: 村民 (男性) stays at its current 生命值"
    "AZTECS can already build 村民 (男性); nothing would change"
    "村民 (男性) has no 成本 wood field to change (its unit type does not store one)"

After the fix: 13 of 13 clean Chinese.  This file pins that, so the next message
someone adds in English fails a test instead of shipping to a player.

The second half of the file is the harder half: a Chinese sentence is not
automatically a GOOD sentence.  "成本木材" and "AZTECS" were both on screen at
some point while being "Chinese enough" for a naive check, so the assertions here
are about what a person would actually accept, not about character ranges.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                         # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAIL = []

CJK = re.compile(r"[\u4e00-\u9fff]")
#: Two or more Latin letters in a row.  A single stray letter is not worth
#: failing over (some unit names legitimately carry one, e.g. "X");
#: "nothing"/"can"/"ASZTECS" are.
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")

#: Raw keys that must never reach a player.  These are the ones reality surfaced;
#: the list is the assertion, so adding a leak means adding a line here.
LEAKED_KEYS = ("displayed_attack", "hit_points", "research_time", "cost_entry",
               "cost type", "attack cls", "locator", "unit_use_types")


def check(name, ok, detail=""):
    if ok:
        print("  ok %s" % name)
    else:
        FAIL.append(name)
        print("FAIL %s :: %s" % (name, detail))


def prose_of(plan):
    """The strings a screen would print, in the order it would print them."""
    out = []
    for field in ("description", "reason"):
        text = plan.get(field)
        if text:
            out.append((field, str(text)))
    return out


#: One case per kind of sentence the product produces.  Success wording AND
#: refusal wording, because a refusal is the sentence a stuck player reads most.
CASES = [
    ("unit stat, ok", {"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                       "value": 1000}),
    ("unit cost, refused", {"intent": "unit.cost", "unit": 83,
                            "resource": "wood", "delta": 10}),
    ("tech research time, ok", {"intent": "tech.research_time", "tech": 22,
                                "delta": 5}),
    ("tech cost, refused", {"intent": "tech.cost", "tech": 22,
                            "resource": "food", "delta": 10}),
    ("availability revoke, ok", {"intent": "unit.availability", "unit": 2550,
                                 "civ": "INCAS", "action": "revoke"}),
    ("unit stat, no-op", {"intent": "unit.stat", "unit": 83,
                          "stat": "hit_points", "delta": 0}),
    ("availability already has it", {"intent": "unit.availability", "unit": 83,
                                     "civ": "AZTECS", "action": "grant"}),
    ("tech research time, no-op", {"intent": "tech.research_time", "tech": 22,
                                   "delta": 0}),
]


def main():
    tk = A.open_toolkit(game_root=GAME)

    seen = []
    for label, raw in CASES:
        plan = tk.plan(raw)
        strings = prose_of(plan)
        check("%s: the plan says something" % label, bool(strings), str(plan)[:160])
        for field, text in strings:
            seen.append((label, field, text))
            check("%s.%s has Chinese in it" % (label, field),
                  bool(CJK.search(text)), text[:120])
            check("%s.%s has no English words" % (label, field),
                  not LATIN_WORD.search(text), text[:120])
            for key in LEAKED_KEYS:
                check("%s.%s does not leak %r" % (label, field, key),
                      key not in text, text[:120])

    # ---- a Chinese sentence is not automatically a good sentence ----------
    # Three shapes were on screen at some point while being "Chinese enough" for
    # a character-range check: "成本 wood木材" (the enum kept AND translated),
    # "AZTECS" (a raw tree stem), and doubled words from a bad substitution.
    for label, field, text in seen:
        check("%s.%s has no doubled CJK" % (label, field),
              not re.search(r"([\u4e00-\u9fff]{2})\1", text), text[:120])
        check("%s.%s does not shout a raw tree stem" % (label, field),
              not re.search(r"\b[A-Z]{4,}\b", text), text[:120])
        check("%s.%s has no empty brackets" % (label, field),
              "（）" not in text and "()" not in text, text[:120])
        for res_en in ("food", "wood", "gold", "stone"):
            check("%s.%s does not print the raw resource %r"
                  % (label, field, res_en),
                  not re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % res_en, text),
                  text[:120])

    # A civilization is named in Chinese wherever it appears.
    for label, field, text in seen:
        if "AZTECS" in text or "INCAS" in text:
            check("%s.%s names the civilization in Chinese" % (label, field),
                  False, text[:120])

    print()
    if FAIL:
        print("PLAYER-FACING TEXT FAILED (%d): %s" % (len(FAIL), FAIL))
        return 1
    print("EVERY PLAYER-FACING SENTENCE IS CHINESE AND NAMES REAL THINGS"
          " (%d strings)" % len(seen))
    return 0


if __name__ == "__main__":
    sys.exit(main())

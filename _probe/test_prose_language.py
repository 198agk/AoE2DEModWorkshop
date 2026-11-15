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

Four surfaces, because the screen prints four different things:
    1. `description`   -- what the edit will do
    2. `reason`        -- why it cannot be done
    3. `warnings`      -- what will look wrong after it is done
    4. `str(exc)`      -- the message from a RAISED refusal, which
                          `server._safe_plan` / `_guard` put on screen verbatim
Surface 4 was missing until 2026-10-20: this file read only the first three while
105 English `raise` literals sat behind them.

A fifth surface is not a new SHAPE of sentence but a second ROUTE to the same
one: `build` calls the same rule as `plan` from its own line of code.  Both were
readable while disagreeing about how to spell a civilization ("INCAS" from the
build, "印加" from the preview), which no character-range check can notice --
it takes running both and comparing.  See `BUILD_CASES`.
"""
import os
import re
import shutil
import sys
import tempfile

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

#: Exception class names.  `_safe_plan`/`_guard` used to prefix every refusal with
#: one, so the screen read "IntentError: 「生命值」会变成 99999…".  These are for
#: us, not for a player.
CLASS_NAMES = ("IntentError", "ModError", "ValueError", "RuntimeError",
               "TypeError", "KeyError", "OSError", "struct.error", "zlib.error")

#: A path is DATA, not wording.  "找不到这张图片：D:\nope\missing.png" is honest --
#: the file name is the useful half -- but the letters in it are not English
#: prose, so the no-English-words check must not see them.
_PATHISH = re.compile(r"[A-Za-z]:[\\/][^\s]*|[\w./\\-]+\.(?:png|bmp|dds|jpe?g)",
                      re.IGNORECASE)


def _drop_paths(text):
    return _PATHISH.sub(" ", text)


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
    # The class bonus used to print "基础攻击 class 12" -- the class id in
    # English, on a Chinese screen.  This case exists because that sentence was
    # "partly Chinese" and a character-range check would have passed it.
    ("attack class bonus, ok", {"intent": "unit.attack_class", "unit": 4,
                                "class_id": 12, "kind": "attack", "delta": 2}),
    ("armour class bonus, ok", {"intent": "unit.attack_class", "unit": 4,
                                "class_id": 3, "kind": "armour", "delta": 1}),
    ("tech effect, ok", {"intent": "tech.effect", "tech": 22, "command": 0,
                         "delta": 5}),
    # A sprite swap is the third producer of player-facing prose, and it was
    # English for its whole life: "%d file(s) copied from X to Y".  Plan only --
    # nothing is written, so this stays cheap.
    ("sprite swap, ok", {"intent": "unit.sprite", "unit": 83, "donor": 4}),
    ("sprite swap, rename model", {"intent": "unit.sprite", "unit": 83,
                                   "donor": 4, "mode": "rename"}),
    # The refusal that made `把村民的样子换成城堡` print English.  Its reason comes
    # from `sprites.plan_swap`, which can only name the engine's raw animation
    # tokens ("attack, death, decay, idle, idlec, walk"); the Chinese words for
    # those live in `intent.reskin.MOMENT_WORD`, so the layer that owns them
    # composes the sentence and every token without a word is COUNTED instead of
    # pasted.  A villager and a castle share no animation at all -- that is why
    # this pair, and not another, is the case.
    ("a swap with no animation in common", {"intent": "unit.sprite", "unit": 1810,
                                            "donor": 82}),
]

#: Intents that RAISE instead of returning a plan.  This is the fourth producer of
#: player-facing prose and it was invisible for the whole life of this file:
#: `server._safe_plan()` hands the page `"%s: %s" % (type(exc).__name__, exc)`
#: (server.py:331) and `_guard()` does the same for the build route, so the
#: message inside `raise IntentError(...)` IS what a player reads.  A census
#: (`probe_raised_prose.py`) counted 106 raised literals, 105 of them English;
#: these are the ones a plain sentence can reach.
#:
#: Each entry must RAISE -- a case that quietly returns a plan would leave this
#: whole section asserting nothing, which is the same failure as an empty
#: assertion.
RAISED_CASES = [
    # i16 overflow: 「村民血量改成99999」
    ("hit points past the field", {"intent": "unit.stat", "unit": 83,
                                   "stat": "hit_points", "value": 99999}),
    # non-negative cost driven below zero: 「村民木材成本减100」 on a 50-wood slot
    ("cost driven negative", {"intent": "unit.cost", "unit": 83,
                              "resource": "food", "delta": -100}),
    # packed attribute is an unsigned BYTE but a float32 on disk
    ("packed attribute below zero", {"intent": "tech.effect", "tech": 22,
                                     "command": 1, "value": -1}),
    ("packed attribute past 255", {"intent": "tech.effect", "tech": 22,
                                   "command": 1, "delta": 99999}),
    ("packed attribute fractional", {"intent": "tech.effect", "tech": 22,
                                     "command": 1, "delta": 0.5}),
    # non-negative floats too: range and reload time
    ("range driven negative", {"intent": "unit.stat", "unit": 4,
                               "stat": "max_range", "value": -1}),
    # A file path the player typed that is not there.  The path itself is the
    # useful half of the answer ("找不到这张图片：a.png"), which is why paths are
    # stripped before the no-English check rather than forbidden.
    ("a picture that is not on disk", {"intent": "unit.art", "unit": 83,
                                       "picture": "no_such_picture_here.png"}),
]

WARNING_CASES = [
    ("sprite swap onto a distant unit", {"intent": "unit.sprite", "unit": 4,
                                         "donor": 8}),
    ("renaming a family", {"intent": "unit.sprite", "unit": 83, "donor": 594,
                           "whole_family": True}),
    # The third producer: `civtechtrees.grant` copies a donor row and reports
    # what it copied.  1,497 of 14,687 unit grants carry the receiver warning,
    # so this is not a rare sentence -- and until 2026-10-20 it read
    # "inherited Building ID=104 from the donor row" on a Chinese screen.
    # ARMENIANS has no building 104 (its own Monk reads 1806), so the
    # receiver-aware sentence is guaranteed to appear.
    ("availability grant with an unreachable building",
     {"intent": "unit.availability", "unit": 775, "civ": "Armenians",
      "action": "grant"}),
    # The other reskin sentences are only reachable on particular pairs, and the
    # two below are the ones that name ANIMATIONS.  The animation keys are engine
    # words ("carry", "walkA", "litter"); the sentence has to say "while carrying
    # something" instead.  Measured 2026-10-21: of the six warning shapes reachable
    # from shipped art, these two are the ones that spell a moment, so they are
    # the ones that can leak ASCII.
    #
    # A villager reskinned alone: it owns 27 records / 18 stems, and a
    # single-record swap covers only some of them -- that is the one that says
    # which stem stays behind and which moments it is used for.
    ("one-record villager swap, most of its art left behind",
     {"intent": "unit.sprite", "unit": 1810, "donor": 594}),
    # ... and the other direction supplies the "this moment is stood in for"
    # sentence, where the animation is borrowed from a neighbouring one.
    ("villager art borrowed from a neighbour for a missing moment",
     {"intent": "unit.sprite", "unit": 124, "donor": 594}),
]

#: Sentences that must be refused by BOTH entry points with the SAME words.
#: These are refusals, so `build` raises before it writes anything -- the temp
#: folder stays empty and cheap.  The civilization is given as a `.dat` name on
#: purpose: that is the input a caller (and the HTTP route) really passes, and
#: it is exactly the shape that used to print "INCAS" on the build path.
BUILD_CASES = [
    ("revoking a unit the civ never had",
     {"intent": "unit.availability", "unit": 2550, "civ": "British",
      "action": "revoke"}),
    ("granting a tech the civ already has",
     {"intent": "tech.availability", "tech": 3, "civ": "British",
      "action": "grant"}),
]

#: The Chinese spelling each case must contain.  Written out rather than derived,
#: so a rename in `civnames.py` fails here instead of silently agreeing with
#: itself.
BUILD_ZH = ("不列颠",)


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

    # ---- the words that live outside description/reason --------------------
    # A reskin emits one sentence per thing the player will SEE go wrong, and an
    # empty warning list is the happy case.  Both halves matter: a warning that is
    # English fails here, and a reskin that produces no warning at all cannot be
    # checked -- so the case list must actually produce one.
    warned = 0
    for label, raw in WARNING_CASES:
        plan = tk.plan(raw)
        warns = [str(w) for w in (plan.get("warnings") or ())]
        if not warns:
            check("%s: produces at least one warning to check" % label, False,
                  "no warnings: this case cannot test anything")
            continue
        warned += len(warns)
        for i, text in enumerate(warns):
            check("%s.warn#%d has Chinese in it" % (label, i),
                  bool(CJK.search(text)), text[:140])
            check("%s.warn#%d has no English words" % (label, i),
                  not LATIN_WORD.search(text), text[:140])
            check("%s.warn#%d has no doubled CJK" % (label, i),
                  not re.search(r"([\u4e00-\u9fff]{2})\1", text), text[:140])
            check("%s.warn#%d does not print a raw file stem" % (label, i),
                  "_x1" not in text and "_x2" not in text, text[:140])

    # ---- the fourth surface: what a RAISED exception says -------------------
    # `_safe_plan` and `_guard` put `str(exc)` on screen, so these are sentences
    # a player reads verbatim.  The section asserts its own reachability first:
    # a case that stopped raising would otherwise silently test nothing.
    raised = 0
    for label, raw in RAISED_CASES:
        try:
            plan = tk.plan(raw)
        except Exception as exc:                       # noqa: BLE001
            text = str(exc)
        else:
            check("%s: refuses instead of planning" % label, False,
                  "returned a plan: %r" % (plan.get("description"),))
            continue
        if not text:
            check("%s: says why it refused" % label, False, "empty message")
            continue
        raised += 1
        prose = _drop_paths(text)
        check("%s: the message has Chinese in it" % label,
              bool(CJK.search(prose)), text[:140])
        check("%s: the message has no English words" % label,
              not LATIN_WORD.search(prose), text[:140])
        check("%s: the message carries no exception class name" % label,
              not any(n in text for n in CLASS_NAMES), text[:140])
        check("%s: the message has no doubled CJK" % label,
              not re.search(r"([\u4e00-\u9fff]{2})\1", prose), text[:140])
        for key in LEAKED_KEYS:
            check("%s: the message does not leak %r" % (label, key),
                  key not in text, text[:140])
        for res_en in ("food", "wood", "gold", "stone"):
            check("%s: the message does not print the raw resource %r"
                  % (label, res_en),
                  not re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % res_en, prose),
                  text[:140])

    # ---- a fifth route by which a sentence reaches the screen --------------
    # `describe` and `icon_for` are not intents: they are called straight from
    # the screen (every "游戏里怎么说的？" click and every grid cell), and their
    # refusals are player-facing text for the same reason a plan's is.  They were
    # the last English left: `no unit with id 999999` was reachable by clicking a
    # stale row, and nothing in this file looked at them, because everything here
    # goes through `tk.plan`.
    for kind, want in (("unit", "单位"), ("tech", "科技"),
                       ("building", "建筑")):
        try:
            tk.describe(999999, kind=kind)
        except Exception as exc:                       # noqa: BLE001
            text = str(exc)
        else:
            check("describe(%s) refuses an id that is not there" % kind,
                  False, "returned an entity")
            continue
        check("describe(%s): the refusal names the kind in Chinese" % kind,
              want in text, text[:140])
        check("describe(%s): the refusal has no English words" % kind,
              not LATIN_WORD.search(_drop_paths(text)), text[:140])
        check("describe(%s): the refusal carries no exception class name" % kind,
              not any(n in text for n in CLASS_NAMES), text[:140])

    # `icon_for` answers with a dict instead of raising, so the same rule has to
    # be checked on the value rather than on an exception.
    gone = tk.icon_for("unit", 999999)
    check("icon_for refuses an id that is not there", gone.get("ok") is False,
          gone)
    check("icon_for: the refusal has no English words",
          not LATIN_WORD.search(_drop_paths(gone.get("why") or "")), gone)
    # A building IS a unit record whose type is 80, so "building" is answered by
    # the same resolve rather than refused (2026-11-10: the picker had no way to
    # ask for buildings, so nothing could reach a building by looking).  What is
    # left to refuse is a word that names no list at all.
    built = tk.icon_for("building", 82)
    check("icon_for answers a building by its unit record",
          built.get("ok") is True, built)
    check("icon_for: the building answer names a picture",
          bool(built.get("material")), built)
    odd = tk.icon_for("tree", 1)
    check("icon_for refuses a kind it does not take", odd.get("ok") is False, odd)
    check("icon_for: that refusal has no English words",
          not LATIN_WORD.search(_drop_paths(odd.get("why") or "")), odd)
    # The technology branch answers through the same dict, and it was the last
    # one still saying "no tech with id N" -- missed because only the unit branch
    # had a case here.
    gone_tech = tk.icon_for("tech", 999999)
    check("icon_for refuses a tech id that is not there",
          gone_tech.get("ok") is False, gone_tech)
    check("icon_for: the tech refusal has no English words",
          not LATIN_WORD.search(_drop_paths(gone_tech.get("why") or "")),
          gone_tech)

    # ---- the same rule reached through `build` -----------------------------
    # `plan`, `build` and `build_bundle` each call `AV.plan` from their own line
    # of code, and the refusal they raise is the same sentence.  Until 2026-10-20
    # only the preview call site passed `civ_zh`, so the build read
    # "BRITONS本来就不能建造..." while the preview read "不列颠本来就不能...".  Two
    # spellings of one answer is a defect even when both are readable, and a
    # character-range check cannot see it -- it takes comparing the entry points.
    #
    # Both non-preview routes are here because they are separate call sites: a
    # fix applied to one says nothing about the other, which is exactly how this
    # survived (the preview was right for weeks while two build routes were not).
    #
    # Measured cost: 0.00 s per refusal once the `.dat` is warm -- the rule reads
    # the trees, not the records, and a refusal writes no file (verified: 0 files
    # left behind), so this belongs in the fast suite.
    agreed = 0
    for label, raw in BUILD_CASES:
        try:
            plan = tk.plan(raw)
            preview_text = str(plan.get("reason") or "")
        except Exception as exc:                       # noqa: BLE001
            preview_text = str(exc)
        for route in ("build", "bundle"):
            out = tempfile.mkdtemp(prefix="prosebuild_")
            try:
                if route == "build":
                    tk.build(raw, title="prose", author="dsh", out_dir=out)
                else:
                    # `build_bundle` takes the LIST form -- the same shape the
                    # HTTP route posts, so this is the route a player reaches by
                    # pressing 构建 on several clauses at once.
                    tk.build_bundle([raw], title="prose", author="dsh",
                                    out_dir=out)
                build_text = "(no refusal)"
            except Exception as exc:                   # noqa: BLE001
                build_text = str(exc)
            finally:
                leftover = sum(len(fs) for _r, _d, fs in os.walk(out))
                shutil.rmtree(out, ignore_errors=True)
            check("%s via %s: refuses instead of writing" % (label, route),
                  build_text != "(no refusal)", build_text[:140])
            check("%s via %s: leaves no half-written mod" % (label, route),
                  leftover == 0, "%d files" % leftover)
            check("%s via %s: says what the preview says" % (label, route),
                  build_text == preview_text,
                  "got=%r preview=%r" % (build_text[:60], preview_text[:60]))
            check("%s via %s: no raw civ stem" % (label, route),
                  not re.search(r"\b[A-Z]{4,}\b", build_text), build_text[:140])
            check("%s via %s: names the civ in Chinese" % (label, route),
                  any(zh in build_text for zh in BUILD_ZH), build_text[:140])
            agreed += 1

    print()
    if FAIL:
        print("PLAYER-FACING TEXT FAILED (%d): %s" % (len(FAIL), FAIL))
        return 1
    print("EVERY PLAYER-FACING SENTENCE IS CHINESE AND NAMES REAL THINGS"
          " (%d strings, %d warnings, %d refusals, %d build refusals)"
          % (len(seen), warned, raised, agreed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

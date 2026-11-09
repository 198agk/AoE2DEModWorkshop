# -*- coding: utf-8 -*-
"""Every field of 「整份 AI 脚本」 reaches the file only after it has been looked at.

WHY THIS PIN EXISTS
-------------------
`_probe/test_ai_plan_civ.py` fixed the 民族 field, which reached
``(civ-selected X)`` unexamined.  Asking the same question of the OTHER fields
on that form found three more of the same shape, all on 2026-11-04:

    name      "MyAI\\n(defrule ... (disable-self) )"  ->  a LIVE RULE nobody
              asked for, because the name is interpolated into the file's first
              comment line and the newline ended the comment.  problems: []
    villagers -5        -> (defconst desired-villagers -5)      problems: []
    villagers 100000    -> (defconst desired-villagers 100000)  problems: []
    age       space-age -> silently swapped for feudal-age,     problems: []

The shared cause is that a form field is a string, and a string interpolated
into a file is code unless something stops it.  The civ fix put the examination
at the boundary (``Plan.__init__``); this pin holds the rest of the boundary to
the same standard, and holds the *reporting* of a clamp, because a clamp the
player never sees is the same silence in a different shape:

    -5 villagers is not "close enough to 1".  It is a request the game cannot
    satisfy, and the player is the only one who knows what they meant.

WHAT IT CHECKS
--------------
1. a name cannot end the comment it is pasted into, in every way that matters
   (newline, CR, tab, vertical tab, form feed, NUL, lone DEL), and the label
   adds no rule to the file -- measured by comparing the rule count against the
   same plan built with a clean label, because the file legitimately has rules;
2. a name is still a name afterwards: the player's words survive and a blank
   name still becomes the default;
3. counts are clamped into a range the game can honour, each clamp is reported
   as a ``problems`` row that keeps what the player typed, and the emitted
   ``defconst`` is the clamped value;
4. an integer-looking string is a number (the form posts strings) and a
   non-integer is reported rather than crashing;
5. an age the engine does not have is reported instead of swapped, and every
   age it does have passes through untouched;
6. all of it at once through ``App.ai_script_build``, the route the button
   calls, and the composed file still passes the shipped checker.

WHAT IT DOES NOT DO
-------------------
It does not pin the wording of any message (a reworded sentence is not a
regression), and it does not decide whether 500 villagers is a *good* ceiling --
only that the ceiling exists, is applied, and is said out loud.  It also does
not require a complaint for a repaired label: collapsing ``"  我的  伐木  AI  "``
to one line loses nothing the player meant, so it is done silently.  A clamp or
a dropped unit changes what the script does, and those are the ones that must
come back as words.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.game import aigen, ailang                     # noqa: E402
from aoe2mod.ui import server as S                         # noqa: E402

FAILS = []

#: The plan the page posts when a player fills nothing in but the army.  Kept
#: explicit so a change to the form's defaults shows up as a diff here rather
#: than as a mystery in a `defconst`.
BASE = {"name": "MyAI", "civ": None, "army": "knight:15", "villagers": 30,
        "attack_at": 20, "age": "feudal-age", "wall": False}

#: Bytes that must never reach the file, wherever they came from.
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def ck(what, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (("  ::  %r" % (detail,))
                                                    if not ok else ""))
    if not ok:
        FAILS.append((what, detail))


def build(app, **over):
    plan = dict(BASE)
    plan.update(over)
    return app.ai_script_build({"plan": plan})


def rules(text):
    """How many rules the file declares.

    Counted per LINE STARTING with `(defrule`, not per occurrence of the word:
    a label that says "(defrule" ends up inside the first comment, and matching
    the substring would blame the label for text the comment is supposed to
    carry.
    """
    return sum(1 for ln in (text or "").splitlines() if ln.startswith("(defrule"))


def defconst(text, name):
    """The integer a `(defconst <name> N)` line carries, or None."""
    m = re.search(r"\(defconst %s (-?\d+)\)" % re.escape(name), text or "")
    return int(m.group(1)) if m else None


def main():
    app = S.App()
    vocab = app.ailang_vocab()
    clean = build(app, name="MyAI").get("text") or ""
    base_rules = rules(clean)

    # --- 1. a name cannot become script -----------------------------------
    print("-- a label cannot end the comment it is pasted into")
    injections = [
        ("newline + rule", "MyAI\n(defrule\n\t(true)\n=>\n\t(disable-self)\n)"),
        ("carriage return", "MyAI\r(defrule (true) => (disable-self))"),
        ("tab", "My\u0009AI\r\n(defrule)"),
        ("vertical tab", "My\u000bAI\u000c(defrule)"),
        ("NUL", "MyAI\u0000(defrule)"),
        ("DEL", "MyAI\u007f(defrule)"),
    ]
    for label, typed in injections:
        r = build(app, name=typed)
        text = r.get("text") or ""
        first = text.splitlines()[0]
        ck("%s: the first line is one comment line" % label,
           first.startswith("; ") and "\n" not in first, first)
        ck("%s: the label added no rule" % label, rules(text) == base_rules,
           (rules(text), base_rules))
        ck("%s: no control character survives into the file" % label,
           not CONTROL.search(text), repr(text[:80]))

    # --- 2. and it is still a name ----------------------------------------
    print("-- a name is still a name")
    r = build(app, name="  我的  伐木  AI  ")
    ck("whitespace runs collapse instead of being deleted",
       "我的 伐木 AI" in (r.get("text") or "").splitlines()[0],
       (r.get("text") or "").splitlines()[0])
    ck("the player's words survive", "我的" in r["plan"]["name"], r["plan"]["name"])
    r = build(app, name="")
    ck("a blank name still falls back to the default",
       r["plan"]["name"] == "MyAI", r["plan"]["name"])

    # --- 3. counts are clamped, and the clamp is said out loud ------------
    print("-- counts the game cannot honour are clamped and reported")
    for field, const, typed, want in (
            ("villagers", "desired-villagers", -5, 1),
            ("villagers", "desired-villagers", 0, 30),
            ("villagers", "desired-villagers", 100000, 500),
            # -3 clamps UP to the lower bound (1) rather than being replaced by
            # the default: the player asked for "attack early", and 1 is the
            # earliest the trigger can mean.
            ("attack_at", "attack-soldier-count", -3, 1),
            ("attack_at", "attack-soldier-count", 9000, 500)):
        r = build(app, **{field: typed})
        got = defconst(r.get("text"), const)
        # 0 is falsy and the route substitutes its own default before the plan
        # ever sees the value, so "0 -> default, no complaint" is the route's
        # behaviour rather than the bound's.
        if typed == 0:
            ck("%s %d: the route's own default stands in" % (field, typed),
               got == want, (got, want))
            continue
        rows = [p for p in (r.get("problems") or []) if p.get("field") == field]
        ck("%s %d: the emitted constant is the bounded value" % (field, typed),
           got == want, (got, want))
        ck("%s %d: the clamp is a problem row naming the field" % (field, typed),
           bool(rows), r.get("problems"))
        ck("%s %d: the row keeps what the player typed" % (field, typed),
           bool(rows) and str(typed) in str(rows[0].get("value")), rows[:1])
        ck("%s %d: and the script is still valid" % (field, typed),
           not ailang.validate_ai(r.get("text") or "", vocab),
           ailang.validate_ai(r.get("text") or "", vocab)[:2])

    # --- 4. the form posts strings ---------------------------------------
    print("-- what the form actually posts (strings)")
    r = build(app, villagers="45", attack_at="60")
    pair = (defconst(r.get("text"), "desired-villagers"),
            defconst(r.get("text"), "attack-soldier-count"))
    ck("an integer-looking string is a number", pair == (45, 60), pair)
    ck("and nothing is reported for it", not r.get("problems"), r.get("problems"))
    r = build(app, villagers="abc")
    ck("a non-integer is a problem, not a crash",
       [p for p in (r.get("problems") or []) if p.get("field") == "villagers"],
       r.get("problems"))
    ck("and the file still has a usable constant",
       defconst(r.get("text"), "desired-villagers") == 30,
       defconst(r.get("text"), "desired-villagers"))

    # --- 5. an age the engine does not have -------------------------------
    print("-- an age the engine does not have is reported, not swapped")
    r = build(app, age="space-age")
    ck("the plan falls back to a real phase", r["plan"]["age"] == "feudal-age",
       r["plan"]["age"])
    ck("the fallback is a problem row naming the field",
       [p for p in (r.get("problems") or []) if p.get("field") == "age"],
       r.get("problems"))
    for age in aigen.AGES:
        r = build(app, age=age)
        ck("%s passes through untouched" % age,
           r["plan"]["age"] == age and not r.get("problems"),
           (r["plan"]["age"], r.get("problems")))
    r = build(app, age="")
    ck("a blank age is the default and is not a complaint",
       r["plan"]["age"] == "feudal-age" and not r.get("problems"),
       (r["plan"]["age"], r.get("problems")))

    # --- 6. all of it at once, through the route --------------------------
    print("-- the route the button calls, with everything wrong at once")
    r = app.ai_script_build({"plan": {"name": "MyAI\n(defrule (true) => (disable-self))",
                                      "civ": "britons2", "army": "camel archer:10",
                                      "villagers": -5, "attack_at": 9000,
                                      "age": "space-age"}})
    text = r.get("text") or ""
    ck("the route still answers ok", r.get("ok") is True, list(r)[:5])
    fields = {p.get("field") for p in (r.get("problems") or [])}
    ck("every field whose meaning changed is named in one place",
       {"civ", "army", "villagers", "attack_at", "age"} <= fields, sorted(fields))
    ck("the file it returns still passes the shipped checker",
       not ailang.validate_ai(text, vocab),
       ailang.validate_ai(text, vocab)[:2])
    # The twin is the same broken plan with a clean label: comparing rule
    # counts against the all-defaults build would measure the OTHER failures
    # (an unresolved army removes rules) instead of the injection.
    twin = app.ai_script_build({"plan": {"name": "MyAI", "civ": "britons2",
                                        "army": "camel archer:10",
                                        "villagers": -5, "attack_at": 9000,
                                        "age": "space-age"}}).get("text") or ""
    ck("and the label still added no rule", rules(text) == rules(twin),
       (rules(text), rules(twin)))
    ck("while the rules that were asked for are still there",
       "(train villager)" in text,
       [ln for ln in text.splitlines() if "train" in ln][:2])
    r = build(app, army="knight:15")
    ck("and a resolved army still trains what was asked",
       "(train knight-line)" in (r.get("text") or ""),
       [ln for ln in (r.get("text") or "").splitlines() if "train" in ln][:4])

    # --- 7. the count inside an army pair is a count too ------------------
    print("-- the number after the colon is the same kind of number")
    r = build(app, army="knight:0")
    ck("`knight:0` cannot ship as a rule that never fires",
       defconst(r.get("text"), "desired-knight-line") == 1,
       defconst(r.get("text"), "desired-knight-line"))
    ck("and the row keeps the pair the player typed",
       [p for p in (r.get("problems") or [])
        if p.get("field") == "army" and "knight" in str(p.get("value"))],
       r.get("problems"))
    r = build(app, army="knight:99999")
    ck("`knight:99999` is bounded the same way",
       defconst(r.get("text"), "desired-knight-line") == 500,
       defconst(r.get("text"), "desired-knight-line"))
    r = build(app, army="knight:15, archer:0")
    ck("only the pair that was out of range is reported",
       (defconst(r.get("text"), "desired-knight-line"),
        defconst(r.get("text"), "desired-archer-line")) == (15, 1)
       and len([p for p in (r.get("problems") or [])
                if p.get("field") == "army"]) == 1,
       (defconst(r.get("text"), "desired-knight-line"),
        defconst(r.get("text"), "desired-archer-line"), r.get("problems")))
    r = build(app, army="knight")
    ck("a pair with no number keeps the documented default of 20",
       defconst(r.get("text"), "desired-knight-line") == 20
       and not r.get("problems"),
       (defconst(r.get("text"), "desired-knight-line"), r.get("problems")))

    # --- 8. a posted flag is read, not truthy-tested ----------------------
    print("-- the wall flag, posted as a string")
    for raw in ("0", "false", "", "no", 0, False):
        r = build(app, wall=raw)
        ck("%r means no wall" % (raw,), r["plan"]["wall"] is False,
           r["plan"]["wall"])
    for raw in ("1", "true", "yes", 1, True):
        r = build(app, wall=raw)
        ck("%r means wall" % (raw,), r["plan"]["wall"] is True, r["plan"]["wall"])
    r = build(app, wall="1")
    ck("and a wall plan actually contains the wall rule",
       "build-wall" in (r.get("text") or ""),
       [ln for ln in (r.get("text") or "").splitlines() if "wall" in ln][:2])
    r = build(app, wall="0")
    ck("while a no-wall plan does not",
       "build-wall" not in (r.get("text") or ""),
       [ln for ln in (r.get("text") or "").splitlines() if "wall" in ln][:2])

    # --- 9. the four gatherer percentages are counts too -------------------
    # The page has no split form, so the route cannot be the harness here: this
    # is `Plan` called the way `from_sentences` calls it.  The numbers land in
    # `(set-strategic-number sn-food-gatherer-percentage N)`, where -50 tells
    # the engine to un-gather and 300 is a share of a village that does not
    # exist; "abc" used to raise straight out of `aistrat` while composing.
    print("-- a gatherer split is four more counts")
    def split_plan(split):
        plan = aigen.Plan(split=split)
        text, _diags, problems = aigen.check(plan, vocab)
        return plan, text, problems

    def pct(text, res="food"):
        m = re.search(r"\(set-strategic-number sn-%s-gatherer-percentage (-?\d+)\)"
                      % res, text or "")
        return int(m.group(1)) if m else None

    plan, text, problems = split_plan({"food": -50})
    ck("a negative share cannot reach the engine",
       pct(text) == 0 and plan.split["food"] == 0, (pct(text), plan.split))
    ck("and the row keeps the share that was asked for",
       [(p.get("field"), p.get("value")) for p in problems] == [("split", "food:-50")],
       problems)
    plan, text, problems = split_plan({"food": 300})
    ck("a share above 100 is capped, not passed through",
       pct(text) == 100 and len(problems) == 1, (pct(text), problems))
    plan, text, problems = split_plan({"wood": 1000})
    ck("the same cap follows the resource, not the key order",
       pct(text, "wood") == 100 and pct(text, "food") == 50,
       (pct(text, "wood"), pct(text, "food")))
    plan, text, problems = split_plan({"food": "abc"})
    ck("a share that is not a number is reported, and composing still returns",
       pct(text) == 50 and len(problems) == 1 and problems[0]["field"] == "split",
       (pct(text), problems))
    plan, text, problems = split_plan({"hack": 5})
    ck("a key nobody reads is said out loud instead of ignored",
       [(p.get("field"), p.get("value")) for p in problems] == [("split", "hack")],
       problems)
    plan, text, problems = split_plan({"food": 60})
    ck("a share inside the range passes untouched and says nothing",
       pct(text) == 60 and not problems, (pct(text), problems))
    plan, text, problems = split_plan(None)
    ck("no split means the shipped defaults, unchanged",
       pct(text) == 50 and not problems, (pct(text), problems))
    # the preset dict out of `SPLITS` is shared module state; a clamp must not
    # write back into it, or every later plan in the same process inherits it.
    before = dict(aigen.SPLITS["feudal"])
    split_plan({"food": 900})
    ck("clamping does not edit the shared preset",
       aigen.SPLITS["feudal"] == before, (aigen.SPLITS["feudal"], before))

    print()
    if FAILS:
        print("AI PLAN FIELDS: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("AI PLAN FIELDS: EVERY FIELD OF THE PLAN FORM IS EXAMINED AT THE BOUNDARY, "
          "AND EVERY CLAMP IS SAID OUT LOUD")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Every 「能做的事」 card shows a sentence that actually works.

WHY THIS EXISTS
---------------
A card that says only "可以说出来" answers "can I?" and leaves "how?" to the
player -- who is exactly the person that screen exists for.  So each intent
declares one worked example next to its own definition (`example` in
`aoe2mod/schema/intents.json`), and the card offers it as a button.

The risk is not that the sentence looks wrong.  It is that the READER moves
under it: add a word to the vocabulary, tighten a guard, and 「织布机第1条效果加5」
stops being a `tech.effect` -- while the card still offers it, with a button
that pastes a broken request into the box.  That is a card that lies, and it
must fail a suite instead of waiting to be noticed.

Two deliberate non-assertions:
  * the example is NOT required to be buildable here -- `切图` and `新单位`
    need a file or a donor unit and are refused at plan time on purpose.  What
    is asserted is that the sentence is UNDERSTOOD and lands on its own intent.
  * the wording of a `why` is not asserted.  A refusal that rewords itself is
    not a regression; a sentence that resolves to the wrong intent is.

Run:  python -X utf8 _probe/test_intent_examples.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.ui.server import App                            # noqa: E402

SCHEMA = os.path.join(ROOT, "aoe2mod", "schema", "intents.json")
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def intent_ids(clause):
    """The intent id(s) a clause resolved to, whatever shape the reader used."""
    it = clause.get("intent")
    if it is None:
        return []
    if isinstance(it, dict):
        return [it.get("intent")] if it.get("intent") else []
    if isinstance(it, str):
        return [it]
    return [getattr(x, "get", lambda *_: None)("intent") for x in it]


def main():
    doc = json.load(io.open(SCHEMA, encoding="utf-8"))
    intents = doc.get("intents") or {}
    a = App()

    print("\n=== 1. every intent declares one worked example ===")
    eq("the schema ships 15 intents", len(intents), 15)
    missing = [k for k, v in intents.items() if not (v.get("example") or "").strip()]
    check("not one is without an example", not missing, str(missing))
    for k, v in intents.items():
        ex = (v.get("example") or "").strip()
        if not ex:
            continue
        check("%s: the example is Chinese, not a latin placeholder" % k,
              bool(re.search(u"[\u4e00-\u9fff]", ex)), ex)
        # A sentence that carries a latin word must be carrying a FILENAME or a
        # unit id the reader is meant to keep -- 「我的图.png」 is the point of
        # the art example, not an English sentence.
        check("%s: the example is not an English sentence" % k,
              not re.search(r"\b(the|a|unit|tech|value|change|make)\b", ex, re.I),
              ex)

    print("\n=== 2. each example is read back as ITS OWN intent ===")
    for k, v in intents.items():
        ex = (v.get("example") or "").strip()
        if not ex:
            continue
        r = a.parse(ex)
        clauses = r.get("clauses") or []
        ids = []
        for c in clauses:
            ids.extend(intent_ids(c))
        print("     %-20s %-28s -> %s" % (k, ex, ids))
        eq("%s: the example lands on itself" % k, ids[:1], [k])
        eq("%s: and produces exactly one clause" % k, len(clauses), 1)
        check("%s: it is understood, not refused" % k,
              not (clauses[0].get("why") or "").strip(),
              str(clauses[0].get("why")))
        # An example is only usable if the player can SEE what it will hit: the
        # clause has to carry a resolved subject (or a class word for the
        # class-wide ones), otherwise the card would be offering a sentence whose
        # meaning is still a question.  `unit.create`/`tech.create` name their
        # new record rather than resolving an existing one, and both carry the
        # donor, so an entity is what every one of the 15 has.
        check("%s: the example names what it acts on" % k,
              bool(clauses[0].get("entity") or clauses[0].get("class_word")),
              str({k2: clauses[0].get(k2)
                   for k2 in ("entity", "entity_id", "class_word")}))

    print("\n=== 3. the examples are distinguishable from each other ===")
    # Two intents sharing one sentence means one of the two cards lies about
    # what its own sentence does -- the exact defect that made this suite exist
    # (a plugin intent listed 「把村民血量设成40」 while the reader resolved it to
    # `unit.stat`).  Uniqueness is the cheap version of "the button does what the
    # card says".
    seen = {}
    dupes = []
    for k, v in intents.items():
        ex = (v.get("example") or "").strip()
        if not ex:
            continue
        if ex in seen:
            dupes.append("%s == %s :: %s" % (k, seen[ex], ex))
        seen[ex] = k
    check("no two intents share one example sentence", not dupes, str(dupes))

    print("\n=== 4. the page actually renders the example, as text not a button ===")
    page = io.open(PAGE, encoding="utf-8").read()
    check("the page reads `it.example`", "it.example" in page)
    check("and pastes it into the box, then parses",
          'value = it.example' in page and "doParse()" in page)
    # `button` carries `white-space:nowrap` from the base rule, so a long
    # sentence in a button overflows a 210px card.  The sentence is a div and
    # the button says 「用这句」.
    check("the sentence is a div, and the button that types it is short",
          u'\u7528\u8fd9\u53e5' in page, "missing the 用这句 chip")
    check("no example is put inside a button",
          not re.search(r'el\("button"[^)]*it\.example', page))

    print("\n=== 5. an intent with no sentence is marked, not silently blank ===")
    # `by_sentence === false` renders 「只能用接口（句子还认不出来）」.  That branch
    # must keep existing: a plugin intent genuinely may have no sentence, and an
    # empty card would read as a bug in the tool rather than a limit of the
    # parser.
    check("the page has a branch for an intent with no sentence",
          "by_sentence" in page)
    check("and it says the API can still do it",
          u"\u53ea\u80fd\u7528\u63a5\u53e3" in page)

    print()
    if FAILS:
        print("INTENT EXAMPLES: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("INTENT EXAMPLES: ALL 15 CARDS OFFER A SENTENCE THAT STILL PARSES TO "
          "THEIR OWN INTENT")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The reader's words must follow the schema while the tool runs, not after a restart.

This file exists because of a measured defect (2026-10-25): `load_schema()` was
already keyed on the set of schema directories -- so a plugin folder dropped in while
the workshop runs takes effect -- but the vocabulary built FROM that schema was cached
under the literal `"table"`.  With a plugin added at runtime the schema listed
`unit.sort_order`, the page offered it, `meta` said so, and **every Chinese sentence
for it was still refused until the process restarted**.

That is the same defect as the schema cache it sits on top of, one layer up, and it is
invisible from inside a process that started after the plugin was there: every test
that builds its world first and asks questions second passes.

So this file adds the plugin mid-run and asks again WITHOUT clearing any cache.
Clearing the cache would be the test telling the code what to do -- the player cannot
clear a cache.  There is one deliberate clear at the start (to establish the cold
state) and one in `finally` (so this file cannot poison the next suite in the run).
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.intent import compiler as C          # noqa: E402
from aoe2mod.ui import nl                        # noqa: E402

fails = 0
checks = 0


def check(name, ok, detail=""):
    global fails, checks
    checks += 1
    if ok:
        print("  ok %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        fails += 1


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# A field the shipped schema does not bind at all, so learning it can only come from
# the plugin.  `sort_number` is on every unit record, so the intent is buildable.
INTENT = {
    "applies_to": "unit",
    "title": "改排序号",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["sort_number"]},
        "value": {"type": "int", "label": "设为"},
    },
    "compile": {"strategy": "in_place_patch"},
}

BINDING = {"unit_fields": {"sort_number": {
    "source": "mark", "name": "sort_number", "bytes": 2, "kind": "int",
    "signed": True, "label": "排序号"}}}


def main():
    root = tempfile.mkdtemp(prefix="dsh_live_")
    saved = os.environ.get(C._PLUGINS_ENV)
    os.environ[C._PLUGINS_ENV] = root
    try:
        C._SCHEMA_CACHE.clear()
        nl._STAT_EXTRA_CACHE.clear()

        # A. cold: a reader that never saw a plugin knows exactly the shipped words.
        words = nl.stat_words()
        check("a cold reader does not know the plugin's word",
              "排序号" not in words.get("sort_number", ()),
              "sort_number -> %r" % (words.get("sort_number"),))
        check("and it still knows the shipped fourteen",
              all(f in words for f in ("hit_points", "displayed_attack",
                                       "movement_speed", "line_of_sight")),
              "missing: %r" % [f for f in ("hit_points", "displayed_attack",
                                           "movement_speed", "line_of_sight")
                               if f not in words])
        check("and the plugin intent is absent from the schema",
              "unit.sort_order" not in C.load_schema()[0]["intents"], "")
        check("and the screen does not claim it is sayable",
              nl.sentence_reachable("unit.sort_order") is False,
              "by_sentence said True for an intent the schema does not have")

        # B. the folder appears.  NOTHING IS CLEARED: this is the player's action.
        base = os.path.join(root, "示例", "schema")
        write_json(os.path.join(base, "intents.json"),
                   {"schema_version": 1, "intents": {"unit.sort_order": INTENT}})
        write_json(os.path.join(base, "dat_bindings.json"), BINDING)

        intents, _bindings = C.load_schema()
        check("the schema picks the plugin up without a restart",
              "unit.sort_order" in intents["intents"],
              "schema_key() = %r" % (C.schema_key(),))
        check("the reader learns the word without a restart",
              "排序号" in nl.stat_words().get("sort_number", ()),
              "the vocabulary is still cached under a constant, so it needs a restart")
        check("the screen agrees the sentence is sayable",
              nl.sentence_reachable("unit.sort_order") is True,
              "by_sentence said False for an intent the reader can now produce")

        # C. taking the folder away has to take the word away too, or a removed
        #    plugin leaves a sentence that parses and then fails inside plan().
        shutil.rmtree(os.path.join(root, "示例"), ignore_errors=True)
        check("removing the folder removes the intent",
              "unit.sort_order" not in C.load_schema()[0]["intents"], "")
        check("and removes the word",
              "排序号" not in nl.stat_words().get("sort_number", ()),
              "a stale word would parse and then fail inside plan()")
        check("and the shipped fourteen survived the round trip",
              all(f in nl.stat_words() for f in ("hit_points", "displayed_attack",
                                                 "movement_speed")),
              "the vocabulary lost a shipped field on the way back")
    finally:
        if saved is None:
            os.environ.pop(C._PLUGINS_ENV, None)
        else:
            os.environ[C._PLUGINS_ENV] = saved
        C._SCHEMA_CACHE.clear()
        nl._STAT_EXTRA_CACHE.clear()
        shutil.rmtree(root, ignore_errors=True)

    print()
    if fails:
        print("LIVE VOCAB: %d CHECK(S) FAILED" % fails)
        return 1
    print("LIVE VOCAB: %d CHECKS PASSED -- the reader's words follow the schema "
          "while the tool runs, in both directions" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())

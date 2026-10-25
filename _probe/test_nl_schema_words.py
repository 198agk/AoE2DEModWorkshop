"""The reader learns words from the schema -- and the screen tells the truth about it.

Why this file exists
--------------------
Until 2026-10-25 `aoe2mod/ui/nl.py` held its own hand-written `STAT_WORDS` table
and never consulted `dat_bindings.json`.  A plugin could add an intent and a
field binding (2026-10-23) and `plan()` would happily build it, but no Chinese
sentence could ever reach it: the reader did not know any word for the field.
The hole was invisible because the ONE table it did know happened to be the same
fourteen labels the schema ships -- 14/14, measured -- so every shipped sentence
worked and every plugin sentence did not.

There are now two ways a sentence can be wrong, and they fail in opposite
directions, which is why both halves are in one file:

  A. TOO NARROW.  Learning words from the schema must not lose a shipped one.
     The failure shape is a WRONG ANSWER, not a refusal: a plugin label that is a
     substring of a shipped word silently re-routes 「弓箭手攻击力加2」.  So the
     assertion is not "the plugin case works" but "all fifteen shipped sentences
     still land on the same intent, the same stat and the same amount" -- measured
     against values recorded before the change.

  B. TOO WIDE.  `sentence_reachable()` decides what the screen CLAIMS it can do,
     and a claim nobody can cash is the same defect as a missing feature.  Two
     shapes must answer no: an intent SHADOWED by another intent that claims its
     options first (`intent_for_stat()` is a lookup, not a disjunction), and a
     field bound without a label (no word can be learned, so no sentence exists).

Run: python -X utf8 _probe/test_nl_schema_words.py
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod import api as A                       # noqa: E402
from aoe2mod.intent import compiler as C          # noqa: E402
from aoe2mod.semantic import index as SI          # noqa: E402
from aoe2mod.ui import nl                         # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

#: sentence -> (intent, stat or None, key, amount) measured BEFORE the words were
#: derived from the schema.  Any drift is a re-route, i.e. a wrong answer.
SHIPPED = [
    ("村民血量改成1000", ("unit.stat", "hit_points", "value", 1000)),
    ("弓箭手攻击力加2", ("unit.stat", "displayed_attack", "delta", 2)),
    ("村民移速改成0", ("unit.stat", "movement_speed", "value", 0)),
    ("弓箭手近战护甲加1", ("unit.stat", "displayed_melee_armour", "delta", 1)),
    ("弓箭手远程护甲加1", ("unit.stat", "displayed_pierce_armour", "delta", 1)),
    ("弓箭手视野加2", ("unit.stat", "line_of_sight", "delta", 2)),
    ("弓箭手射程加1", ("unit.stat", "max_range", "delta", 1)),
    ("弓箭手命中率加5", ("unit.stat", "accuracy", "delta", 5)),
    ("城镇中心驻扎容量加5", ("unit.stat", "garrison_capacity", "delta", 5)),
    ("弓箭手训练时间减3", ("unit.stat", "creation_time", "delta", -3)),
    ("弓箭手装填时间减1", ("unit.stat", "reload_time", "delta", -1)),
    ("步弓手对骑兵攻击加2", ("unit.attack_class", None, "delta", 2)),
    ("织布机研究时间减5", ("tech.research_time", None, "delta", -5)),
    ("村民木材成本加10", ("unit.cost", None, "delta", 10)),
    ("所有步兵血量加10", ("unit.stat", "hit_points", "delta", 10)),
]

SORT_ORDER = {
    "applies_to": "unit",
    "title": "改排序号",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["sort_number"]},
        "value": {"type": "int", "label": "设为"},
        "civs": {"type": "civ_scope", "label": "文明"},
    },
    "compile": {"strategy": "in_place_patch"},
}

SHADOWED = {
    "applies_to": "unit",
    "title": "重复出厂属性",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["hit_points", "line_of_sight"]},
        "value": {"type": "int", "label": "设为"},
        "civs": {"type": "civ_scope", "label": "文明"},
    },
    "compile": {"strategy": "in_place_patch"},
}

NO_STAT = {
    "applies_to": "unit",
    "title": "没有属性字段",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "value": {"type": "int", "label": "设为"},
    },
    "compile": {"strategy": "in_place_patch"},
}

UNLABELLED = {
    "applies_to": "unit",
    "title": "绑定但没标签",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["blast_width"]},
        "value": {"type": "int", "label": "设为"},
        "civs": {"type": "civ_scope", "label": "文明"},
    },
    "compile": {"strategy": "in_place_patch"},
}

FAILS = []
OKS = [0]


def check(name, ok, detail=""):
    if ok:
        OKS[0] += 1
        print("  ok %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    io_ = __import__("io")
    io_.open(path, "wb").write(text.encode("utf-8"))


def install_plugin(root):
    base = os.path.join(root, "示例", "schema")
    write_json(os.path.join(base, "intents.json"),
               {"schema_version": 1,
                "intents": {"unit.sort_order": SORT_ORDER,
                            "unit.stat_probe": SHADOWED,
                            "unit.no_stat_at_all": NO_STAT,
                            "unit.unlabelled": UNLABELLED}})
    # Neither sort_number nor blast_width is bound by the shipped file (14 fields,
    # measured), so the plugin binds both.  The difference the two rows carry is
    # the LABEL: 排序号 becomes sayable, the bare one stays unsayable.
    write_json(os.path.join(base, "dat_bindings.json"),
               {"unit_fields": {
                   "sort_number": {"source": "mark", "name": "sort_number",
                                   "bytes": 2, "kind": "int", "signed": True,
                                   "label": "排序号"},
                   "blast_width": {"source": "mark", "name": "blast_width",
                                   "bytes": 2, "kind": "float",
                                   "signed": False}}})


def main():
    tk = A.open_toolkit(GAME)
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)

    def read(text):
        return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH,
                       effect_count=tk.effect_count, unit_class=tk.unit_class)

    # ---- A. shipped sentences do not move -------------------------------
    print("=== A. fifteen shipped sentences still land where they did")
    moved = []
    for text, want in SHIPPED:
        got, clauses = read(text)
        if not got:
            moved.append("%s refused: %s" % (text, clauses[0].why))
            print("  FAIL %-22s refused" % text)
            continue
        it = got[0]
        key = "value" if "value" in it else ("delta" if "delta" in it else None)
        ok = (it.get("intent") == want[0]
              and (want[1] is None or it.get("stat") == want[1])
              and key == want[2] and it.get(key) == want[3])
        print("  %-4s %-22s -> %s %s %s=%r"
              % ("ok" if ok else "FAIL", text, it.get("intent"),
                 it.get("stat"), key, it.get(key)))
        if not ok:
            moved.append(text)
    check("no shipped sentence changed intent, stat or amount", not moved,
          str(moved))
    check("all fifteen were parsed, none refused", len(moved) == 0,
          "%d of %d moved" % (len(moved), len(SHIPPED)))

    # ---- B. the reader learns a word from a plugin binding --------------
    print("=== B. a plugin binding teaches the reader a word")
    root = tempfile.mkdtemp(prefix="dsh_words_")
    saved = os.environ.get(C._PLUGINS_ENV)
    os.environ[C._PLUGINS_ENV] = root
    try:
        install_plugin(root)
        C._SCHEMA_CACHE.clear()
        # `stat_words()` caches its table, and `p.reload()`-style clearing of the
        # schema cache does NOT touch it -- forget this line and every assertion
        # below reads the shipped vocabulary and blames the plugin.
        nl._STAT_EXTRA_CACHE.clear()

        intents, bindings = C.load_schema()
        specs = intents["intents"]
        check("the plugin's binding merged", "sort_number" in
              (bindings.get("unit_fields") or {}), "")
        # `stat_words()` returns {field: (words...)}; a derived field is one the
        # hand-written table never had, and a derived WORD is one absent from the
        # tuple the table would have given for that field.
        learned_fields = [f for f in nl.stat_words() if f not in nl.STAT_WORDS]
        learned_words = [w for f in learned_fields
                         for w in nl.stat_words()[f]
                         if w not in nl.STAT_WORDS.get(f, ())]
        check("the reader learned a field it did not have", bool(learned_fields),
              "no new fields -- did the cache get cleared?")
        check("and the new word is the plugin's label",
              "排序号" in learned_words, str(learned_words))

        got, _ = read("村民排序号加5")
        check("a sentence in the plugin's vocabulary parses",
              bool(got) and got[0].get("stat") == "sort_number",
              str(got))
        check("and it goes to the intent that owns that field",
              bool(got) and got[0].get("intent") == nl.intent_for_stat("sort_number"),
              str(got))
        try:
            plan = tk.plan(got[0]) if got else {}
        except C.IntentError as exc:
            # A refusal here is the OUTCOME under test, not a broken probe: if
            # `intent_for_stat()` stops asking the schema, the reader keeps writing
            # `unit.stat` and `plan()` rejects the very stat the schema taught it.
            # Letting the exception escape would turn a named FAIL into a traceback,
            # and a traceback is indistinguishable from a broken suite.
            plan = {"editable": False, "error": str(exc)}
        check("the preview accepts it", plan.get("editable") is True,
              str(plan.get("editable") or plan.get("error")))

        # ---- C. claims nobody can cash ---------------------------------
        print("=== C. the screen does not advertise what no sentence reaches")
        check("a field nobody else claims is reachable",
              nl.sentence_reachable("unit.sort_order",
                                    specs.get("unit.sort_order")) is True, "")
        check("an intent shadowed by a shipped one is NOT advertised",
              nl.sentence_reachable("unit.stat_probe",
                                    specs.get("unit.stat_probe")) is False,
              "intent_for_stat hands its options to unit.stat, so no sentence "
              "can produce it")
        check("an intent with no stat field and no branch is NOT advertised",
              nl.sentence_reachable("unit.no_stat_at_all",
                                    specs.get("unit.no_stat_at_all")) is False,
              "")
        check("a bound field with no label is NOT advertised",
              nl.sentence_reachable("unit.unlabelled",
                                    specs.get("unit.unlabelled")) is False,
              "no word exists for blast_width")
        check("a shipped intent is still reachable",
              nl.sentence_reachable("unit.stat", specs.get("unit.stat")) is True,
              "")
        check("a hand-written branch needs no stat field",
              nl.sentence_reachable("unit.sprite",
                                    specs.get("unit.sprite")) is True, "")
        check("an unknown id is not reachable",
              nl.sentence_reachable("unit.does_not_exist") is False, "")

        # The screen's own answer has to be this same answer, or the fix stops at
        # the function nobody calls.
        from aoe2mod.ui import server as S
        rows = {r["id"]: r for r in S.App(game_root=GAME).meta()["intents"]}
        check("the screen agrees about the reachable one",
              rows.get("unit.sort_order", {}).get("by_sentence") is True,
              str(rows.get("unit.sort_order", {}).get("by_sentence")))
        check("and about the shadowed one",
              rows.get("unit.stat_probe", {}).get("by_sentence") is False,
              str(rows.get("unit.stat_probe", {}).get("by_sentence")))
    finally:
        if saved is None:
            os.environ.pop(C._PLUGINS_ENV, None)
        else:
            os.environ[C._PLUGINS_ENV] = saved
        C._SCHEMA_CACHE.clear()
        nl._STAT_EXTRA_CACHE.clear()
        shutil.rmtree(root, ignore_errors=True)

    print()
    if FAILS:
        print("NL SCHEMA WORDS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("NL SCHEMA WORDS: %d CHECKS PASSED -- the reader learns words from the "
          "schema without moving a shipped sentence, and the screen only claims "
          "sentences the reader can produce" % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

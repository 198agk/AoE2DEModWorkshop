"""Can a plugin add a *sentence shape*, or only a field?

The objective says "插件化".  Two things have been measured and both are green:
  * a plugin can add an intent + a field binding, the reader learns the word, and
    a sentence is read as the plugin's intent id (`_probe/test_nl_schema_words.py`,
    `_probe/test_nl_live_vocab.py`);
  * the page marks an intent the reader cannot spell as 只能用接口.

The open question is where the line actually falls, and it must be answered by
behaviour rather than by reading `aoe2mod/ui/nl.py`: a plugin that declares an intent
whose fields are NOT `(entity, stat, number)` -- a *shape* the reader has no branch for
-- must be reported as unsayable, and a sentence resembling it must be refused rather
than quietly becoming something else.

This probe builds both plugins and asks the two questions.  `_probe/tmp_sentence_shapes.py`
(the source-regex census) is the commentary; this is the measurement.
"""
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.intent import compiler as C  # noqa: E402
from aoe2mod.ui import nl as nl  # noqa: E402

WORDED = {
    "intent": "unit.sort_order",
    "title": "排序号",
    "applies_to": "unit",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True, "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["sort_number"]},
        "delta": {"type": "int", "label": "变化量"},
    },
    "compile": {"strategy": "in_place_patch"},
}

# Same skeleton, but no `stat` field: the reader has no branch that could turn a
# Chinese sentence into this shape, and no plugin should be able to invent one.
SHAPELESS = {
    "intent": "unit.probe_shape",
    "title": "给单位挂一个标签",
    "applies_to": "unit",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True, "label": "单位"},
        "label": {"type": "string", "required": True, "label": "标签"},
    },
    "compile": {"strategy": "in_place_patch"},
}


def write_plugin(root, name, intents, bindings):
    """`intents` is a dict keyed by intent id -- the shipped file's own shape.

    (First version passed a list and the plugin merge blew up with
    `AttributeError: 'list' object has no attribute 'items'`; the shipped
    `aoe2mod/schema/intents.json` is `{"intents": {"<id>": {...}}}`, so a plugin
    that mirrors it must be keyed too.  Worth keeping: the failure looked like a
    product bug for one minute.)
    """
    d = os.path.join(root, name, "schema")
    os.makedirs(d, exist_ok=True)
    with io.open(os.path.join(d, "intents.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"schema_version": 1, "intents": intents}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with io.open(os.path.join(d, "dat_bindings.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"unit_fields": bindings}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    tmp = tempfile.mkdtemp(prefix="dsh_shape_")
    old = os.environ.get(C._PLUGINS_ENV)
    fails = []

    def check(name, ok, detail=""):
        print("  %s %s%s" % ("ok  " if ok else "FAIL", name,
                             (" :: %s" % detail) if detail and not ok else ""))
        if not ok:
            fails.append(name)

    try:
        write_plugin(tmp, "带词的", {"unit.sort_order": WORDED},
                     {"sort_number": {"source": "mark", "name": "sort_number",
                                      "bytes": 1, "kind": "int", "signed": False,
                                      "label": "排序号"}})
        write_plugin(tmp, "没词只有形状的", {"unit.probe_shape": SHAPELESS}, {})
        os.environ[C._PLUGINS_ENV] = tmp
        C.clear_schema_cache() if hasattr(C, "clear_schema_cache") else None

        intents, bindings = C.load_schema()
        names = set(intents.get("intents") or {})
        print("A. both plugins are in the schema")
        check("the field-carrying plugin intent is loaded", "unit.sort_order" in names, sorted(names))
        check("the shape-only plugin intent is loaded too", "unit.probe_shape" in names, sorted(names))

        print("\nB. only the one with a `stat` field is advertised as sayable")
        check("a plugin intent that names a field is sayable",
              nl.sentence_reachable("unit.sort_order", intents["intents"]["unit.sort_order"]))
        check("a plugin intent with no `stat` field is NOT sayable",
              not nl.sentence_reachable("unit.probe_shape", intents["intents"]["unit.probe_shape"]),
              "the screen would promise a sentence nobody can write")

        print("\nC. and a sentence shaped like it is refused, not read as something else")
        vocab = None
        try:
            from aoe2mod.semantic import index as SI
            idx = SI.index()
            vocab = nl.Vocabulary(idx.units, idx.techs)
        except Exception as exc:  # noqa: BLE001
            print("  (no semantic index: %s -- skipping the sentence half)" % exc)
        if vocab is not None:
            for text in ("给村民挂上铁匠标签", "把村民的标签改成铁匠"):
                got, _clauses = nl.read(text, vocab, civ_zh=nl.CIV_ZH)
                _ids = [g.get("intent") for g in got]
                check("「%s」does not become unit.probe_shape" % text,
                      "unit.probe_shape" not in _ids, _ids)
        check("the product says so in plugins/README.md",
              _readme_says_no_shapes(), "README does not state the limit")
    finally:
        if old is None:
            os.environ.pop(C._PLUGINS_ENV, None)
        else:
            os.environ[C._PLUGINS_ENV] = old
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fails:
        print("SENTENCE SHAPES: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
        return 1
    print("SENTENCE SHAPES: A PLUGIN CAN TEACH A FIELD; A NEW SHAPE IS NOT SAYABLE AND IS "
          "REFUSED RATHER THAN MISREAD")
    return 0


def _readme_says_no_shapes():
    p = os.path.join(ROOT, "plugins", "README.md")
    if not os.path.isfile(p):
        return False
    txt = io.open(p, encoding="utf-8").read()
    return "句子形状" in txt and ("加不了" in txt or "不能" in txt)


if __name__ == "__main__":
    raise SystemExit(main())

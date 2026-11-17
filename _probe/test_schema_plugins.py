"""Pin the plugin schema layer: a folder can add an intent, a folder cannot lie.

Why this file exists
--------------------
"Plugins as folders" has been a stated design constraint since the first line of
`aoe2mod/ui/server.py`, and until 2026-10-23 it survived only as that sentence:
`load_schema()` opened two files out of one hardcoded directory.  A plugin could
not add anything, and -- worse -- nobody would have noticed, because every
caller funnels through `load_schema()` and gets whatever it returns.

The three failures this file guards are all SILENT, which is why the assertions
are about evidence rather than about the happy path:

  A. a plugin folder contributes its intent to `load_schema()` and to
     `/api/meta` -- i.e. the merge actually happened, not just "the directory
     list got longer";
  B. a plugin-named intent reaches `plan()` AND `build()` AND produces the same
     bytes the shipped copy of that capability produces.  A plugin intent is a
     re-labelling of a strategy that already exists; if it writes different
     bytes it is not the same capability, it is a second implementation;
  C. a plugin can never WIN a collision.  Duplicate intent id and duplicate
     field binding are both refused, in Chinese, naming the directory.  Last
     writer wins would let a folder silently redefine what a shipped intent
     writes into the player's `.dat`;
  D. the cache key follows the directory set.  The old key was the directory
     STRING, so the first plugin would have kept returning the base tuple --
     the plugin would look loaded and contribute nothing.  This is the one bug
     that cannot be seen by adding a plugin and checking the count, because the
     count is read from the same stale cache.

Run: python -X utf8 _probe/test_schema_plugins.py
"""
import io
import _gamepaths as GP
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                                  # noqa: E402
from aoe2mod.intent import compiler as C                      # noqa: E402
from aoe2mod.ui import server as S                            # noqa: E402

GAME = GP.GAME

FAILS = []
OKS = [0]


def check(name, ok, detail=""):
    if ok:
        OKS[0] += 1
        print("  ok %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))


PLUGIN_INTENT = {
    "applies_to": "unit",
    "title": "把一项属性设成某个值（插件示例）",
    "fields": {
        "unit": {"type": "entity_ref", "kind": "unit", "required": True,
                 "label": "单位"},
        "stat": {"type": "enum", "required": True, "label": "属性",
                 "options": ["hit_points", "line_of_sight", "movement_speed"]},
        "value": {"type": "int", "label": "设为", "min": -32768, "max": 32767},
        "civs": {"type": "civ_scope", "label": "文明"},
    },
    "compile": {"strategy": "in_place_patch"},
    "safety": {"field_width_bits": 16, "signed": True},
}


def write_json(path, doc, bom=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    io.open(path, "wb").write(data)


class Plugins(object):
    """A throwaway plugins root, so the assertions never touch the real one.

    Uses `AOE2MOD_PLUGINS` rather than the repo directory: a suite that writes
    into `plugins/` would depend on the checkout's contents, and the point of
    a plugin root is that it can be somewhere else.
    """

    def __init__(self, with_example=True):
        self.root = tempfile.mkdtemp(prefix="dsh_plugins_")
        self.saved_env = os.environ.get(C._PLUGINS_ENV)
        os.environ[C._PLUGINS_ENV] = self.root
        self.reload()
        if with_example:
            self.add("示例", {"intents": {"unit.stat_probe": PLUGIN_INTENT}})

    def add(self, name, intents_doc=None, bindings_doc=None, bom=False):
        base = os.path.join(self.root, name, "schema")
        if intents_doc is not None:
            doc = {"schema_version": 1}
            doc.update(intents_doc)
            write_json(os.path.join(base, "intents.json"), doc, bom=bom)
        if bindings_doc is not None:
            write_json(os.path.join(base, "dat_bindings.json"), bindings_doc,
                       bom=bom)
        self.reload()

    def try_load(self, name, intents_doc=None, bindings_doc=None, bom=False):
        """Add a plugin, load the schema, then take the plugin away again.

        Merging happens INSIDE ``load_schema()``, not inside ``add`` -- so a
        refusal has to be provoked by a load, and the offending folder has to go
        before the next assertion, or one deliberate collision would poison
        every check after it (that is exactly what happened on the first run of
        this file).
        """
        self.add(name, intents_doc, bindings_doc, bom=bom)
        try:
            return C.load_schema()
        finally:
            shutil.rmtree(os.path.join(self.root, name), ignore_errors=True)
            self.reload()

    def reload(self):
        C._SCHEMA_CACHE.clear()

    def close(self):
        if self.saved_env is None:
            os.environ.pop(C._PLUGINS_ENV, None)
        else:
            os.environ[C._PLUGINS_ENV] = self.saved_env
        C._SCHEMA_CACHE.clear()
        shutil.rmtree(self.root, ignore_errors=True)


def main():
    base_intents, base_bindings = C.load_schema()
    base_count = len(base_intents["intents"])

    # ---- A. the folder really contributes -------------------------------
    print("=== A. a plugin folder adds its intent")
    p = Plugins()
    try:
        got_intents, got_bindings = C.load_schema()
        check("the shipped intents are all still there",
              set(base_intents["intents"]).issubset(set(got_intents["intents"])),
              "lost: %s" % (set(base_intents["intents"])
                            - set(got_intents["intents"])))
        check("and the plugin's intent is in the merged schema",
              "unit.stat_probe" in got_intents["intents"],
              str(sorted(got_intents["intents"])))
        check("so the schema grew by exactly one",
              len(got_intents["intents"]) == base_count + 1,
              "%d -> %d" % (base_count, len(got_intents["intents"])))
        check("and the bindings came through untouched",
              got_bindings.get("unit_fields") == base_bindings.get("unit_fields"),
              "unit_fields changed")
        check("the plugin root is in the directory list",
              len(C.plugin_schema_dirs()) == 2,
              str(C.plugin_schema_dirs()))

        # BOM: hand-edited JSON on Windows very often carries one, and the
        # first real plugin file did.  A refusal here would be a "your perfectly
        # good file is broken" message about a byte nobody can see.
        p.add("示例", {"intents": {"unit.stat_probe": PLUGIN_INTENT}}, bom=True)
        check("a plugin file saved with a BOM still loads",
              "unit.stat_probe" in C.load_schema()[0]["intents"],
              "BOM was refused")

        # ---- B. it reaches the product, and writes the shipped bytes -----
        print("=== B. the plugin intent reaches plan, build and the screen")
        tk = A.open_toolkit(game_root=GAME)
        plug = {"intent": "unit.stat_probe", "unit": 83, "stat": "hit_points",
                "value": 40}
        built_in = {"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                    "value": 40}
        plan = tk.plan(plug)
        check("the plugin intent previews as an editable change",
              plan.get("editable") is True and plan.get("edit_count"),
              str(plan.get("editable")))
        shipped_plan = tk.plan(built_in)
        check("and previews the SAME edit count as the shipped intent it reuses",
              plan.get("edit_count") == shipped_plan.get("edit_count"),
              "%r vs %r" % (plan.get("edit_count"),
                            shipped_plan.get("edit_count")))

        out = tempfile.mkdtemp(prefix="dsh_plugin_a_")
        out2 = tempfile.mkdtemp(prefix="dsh_plugin_b_")
        try:
            man = tk.build(plug, out, title="dsh plugin probe", author="dsh",
                           overwrite=True)
            man2 = tk.build(built_in, out2, title="dsh built-in probe",
                            author="dsh", overwrite=True)
            check("the plugin intent builds a mod",
                  bool(man.get("mod_dir")), str(man)[:120])
            dat_a = os.path.join(man["mod_dir"], "resources", "_common", "dat",
                                 "empires2_x2_p1.dat")
            dat_b = os.path.join(man2["mod_dir"], "resources", "_common", "dat",
                                 "empires2_x2_p1.dat")
            a = io.open(dat_a, "rb").read()
            b = io.open(dat_b, "rb").read()
            check("and writes byte-identical data to the intent it reuses",
                  a == b, "%d vs %d bytes" % (len(a), len(b)))
        finally:
            shutil.rmtree(out, ignore_errors=True)
            shutil.rmtree(out2, ignore_errors=True)

        ids = [i["id"] for i in S.App(game_root=GAME).meta()["intents"]]
        check("the screen's intent list carries it",
              "unit.stat_probe" in ids, str(len(ids)))
        row = [i for i in S.App(game_root=GAME).meta()["intents"]
               if i["id"] == "unit.stat_probe"][0]
        check("and shows the plugin's own title, not a fallback",
              row["title"] == PLUGIN_INTENT["title"], str(row["title"]))
        check("and reports the strategy it reuses",
              row["strategy"] == "in_place_patch", str(row["strategy"]))

        # ---- C. a plugin can never win a collision -----------------------
        print("=== C. a plugin cannot silently redefine a shipped name")
        try:
            p.try_load("撞名", {"intents": {"unit.stat": PLUGIN_INTENT}})
            check("a duplicate intent id is refused", False,
                  "the plugin replaced a shipped intent")
        except C.IntentError as exc:
            check("a duplicate intent id is refused", True, str(exc))
            check("and the refusal names the directory and the id",
                  "撞名" in str(exc) and "unit.stat" in str(exc), str(exc))
        try:
            p.try_load("撞字段", {"intents": {"unit.stat_probe2":
                                             dict(PLUGIN_INTENT)}},
                       bindings_doc={"unit_fields":
                                     {"hit_points": {"label": "冒名顶替"}}})
            check("a duplicate field binding is refused", False,
                  "the plugin redefined hit_points")
        except C.IntentError as exc:
            check("a duplicate field binding is refused", True, str(exc))

        p.add("未知策略", {"intents": {"unit.bogus": dict(
            PLUGIN_INTENT, compile={"strategy": "not_a_real_strategy"})}})
        try:
            tk.plan({"intent": "unit.bogus", "unit": 83,
                     "stat": "hit_points", "value": 40})
            check("a plugin cannot introduce a compile strategy", False,
                  "plan accepted an unknown strategy from a plugin")
        except C.IntentError:
            check("a plugin cannot introduce a compile strategy", True)
        shutil.rmtree(os.path.join(p.root, "未知策略"), ignore_errors=True)
        p.reload()

        # ---- D. the cache follows the directory set ----------------------
        print("=== D. the cache key follows the directory set")
        # The stale-key bug has a precise shape: the schema was loaded once, a
        # plugin appears AFTERWARDS, and the next call is answered from cache.
        # Clearing the cache between the two (which `add()` does) hides it
        # entirely, so this check must NOT clear.
        C._SCHEMA_CACHE.clear()
        before = C.load_schema()
        check("a cold read does not know the third plugin yet",
              "unit.stat_probe_three" not in before[0]["intents"], "")
        base_dir = os.path.join(p.root, "后来加的", "schema")
        write_json(os.path.join(base_dir, "intents.json"),
                   {"schema_version": 1,
                    "intents": {"unit.stat_probe_three": dict(
                        PLUGIN_INTENT, title="第三个")}})
        after = C.load_schema()          # deliberately NO cache clear
        check("a plugin dropped in while the tool runs shows up immediately",
              "unit.stat_probe_three" in after[0]["intents"],
              "answered from a stale cache keyed on the base directory")
        check("and the key is no longer a bare directory string",
              C.schema_key() != C._SCHEMA,
              repr(C.schema_key())[:80])
    finally:
        p.close()

    print("=== E. with the plugin root gone, the schema is exactly the shipped one")
    C._SCHEMA_CACHE.clear()
    back_intents, back_bindings = C.load_schema()
    check("the count is back to the shipped count",
          len(back_intents["intents"]) == base_count,
          "%d vs %d" % (len(back_intents["intents"]), base_count))
    check("and nothing plugin-shaped survived",
          not any(i.startswith("unit.stat_probe")
                  or i == "unit.bogus" for i in back_intents["intents"]),
          str([i for i in back_intents["intents"] if "probe" in i]))
    check("the cache key is the single shipped directory again",
          C.schema_key() == C._SCHEMA, repr(C.schema_key()))

    print()
    if FAILS:
        print("SCHEMA PLUGINS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("SCHEMA PLUGINS: %d CHECKS PASSED -- a folder of JSON adds an intent, "
          "and no folder can take a shipped name" % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

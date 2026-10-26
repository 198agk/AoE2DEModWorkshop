"""Named recipes: the sentences are what is saved, and a sentence still has to read.

Why a nail and not a smoke test
-------------------------------
Saving a name and reading it back is trivial and always works.  The failure this
file is written against is the quiet one: a recipe whose sentences no longer parse
would sit in the list looking exactly like a working one, and the player would find
out by clicking it a month later.  So every assertion here is about what happens
when the READER looks at the stored text, not about the file.

The state directory is redirected (`_probe` has done this since
`provenance.py` landed) so the player's real recipe file is never written.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.ui import recipes as R  # noqa: E402
from aoe2mod.ui import nl  # noqa: E402
from aoe2mod import api as A  # noqa: E402
from aoe2mod.semantic import index as SI  # noqa: E402
from aoe2mod.game import locations as L  # noqa: E402

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name,
                         "" if ok or detail == "" else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="dsh_recipes_")
    os.environ[R._PV.STATE_DIR_ENV] = tmp
    file_path = R.path()
    try:
        # --- A: a name is required, and a bad name is refused in Chinese -------
        for bad, why in (("", "空"), ("   ", "全空格")):
            try:
                R.remember(bad, ["村民血量改成1000"])
                check("an empty name is refused (%s)" % why, False, "accepted")
            except R.RecipeError as exc:
                check("an empty name is refused (%s)" % why,
                      "名字" in str(exc), str(exc))
        try:
            R.remember("长" * (R.MAX_NAME + 1), ["村民血量改成1000"])
            check("a name past the limit is refused", False, "accepted")
        except R.RecipeError as exc:
            check("a name past the limit is refused",
                  str(R.MAX_NAME) in str(exc), str(exc))

        # --- B: nothing to save is refused, and a blank line is not a sentence -
        try:
            R.remember("空配方", ["  ", ""])
            check("a recipe with no sentence is refused", False, "accepted")
        except R.RecipeError as exc:
            check("a recipe with no sentence is refused",
                  "一句" in str(exc), str(exc))
        row = R.remember("去空行", ["村民血量改成1000", "  ", "村民血量改成1000"])
        check("blank lines and duplicates collapse",
              row["sentences"] == ["村民血量改成1000"], row["sentences"])

        # --- C: the saved sentences are the ones the reader accepts ------------
        tk = A.open_toolkit()
        idx = SI.index()
        vocab = nl.Vocabulary(idx.units, idx.techs)
        recipe = R.remember("我的常用", [
            "村民血量改成1000",
            "织布机研究时间减5",
            "不列颠不能造蔷琵侦察兵",
        ])
        check("the recipe stores exactly what was handed to it",
              recipe["sentences"] == ["村民血量改成1000", "织布机研究时间减5",
                                      "不列颠不能造蔷琵侦察兵"],
              recipe["sentences"])
        for sentence in recipe["sentences"]:
            intents, clauses = nl.read(sentence, vocab,
                                       civ_names=tk.civ_names, civ_zh=nl.CIV_ZH,
                                       effect_count=tk.effect_count)
            check("a stored sentence still reads: %s" % sentence,
                  len(intents) == 1 and not clauses[0].why,
                  "intents=%d why=%r" % (len(intents), clauses[0].why))

        # --- D: reading back survives a restart (a new process, same folder) ---
        saved = R.rows()
        check("the recipe is in the list under its name",
              [r["name"] for r in saved] == ["去空行", "我的常用"],
              [r["name"] for r in saved])
        check("the list carries the sentence count",
              [r["count"] for r in saved] == [1, 3], [r["count"] for r in saved])
        check("it remembers when it was saved",
              bool(saved[0]["saved_at"]), saved[0]["saved_at"])

        # --- E: a corrupt file reads as no recipes, not as a crash -------------
        import io
        io.open(file_path, "w", encoding="utf-8", newline="").write(
            '{"version": 1, "recipes": {"x": {"sentences": []}, "y": 5}')
        # Read inside a guard on purpose.  A `raise` here used to escape `main()`
        # and end the process, so the reverse-validation script saw `exit=1` with
        # no named line and reported "still green" -- a crash is not a proof, and
        # a reading that cannot tell them apart certifies nothing.
        try:
            loaded = R.rows()
            crashed = None
        except Exception as exc:                        # noqa: BLE001
            loaded, crashed = None, "%s: %s" % (type(exc).__name__, exc)
        check("a corrupt file reads as no recipes", loaded == [], crashed or loaded)
        check("...and it does not raise out of the reader", crashed is None, crashed)
        R.remember("重来", ["村民血量改成1000"])
        check("saving after a corrupt read works",
              [r["name"] for r in R.rows()] == ["重来"], R.rows())
        # Read the bytes HERE, while a recipe exists.  The first version of this
        # assertion ran after the two `forget` calls below, so it inspected a file
        # whose only recipe had just been deleted and reported an empty file as a
        # defect -- a check that was asking about the wrong moment.
        saved_bytes = io.open(file_path, "rb").read()
        check("the file holds sentences, not a .dat path",
              b".dat" not in saved_bytes
              and "村民血量改成1000".encode("utf-8") in saved_bytes,
              saved_bytes[:120])

        # --- F: forgetting says whether it removed anything -------------------
        check("forgetting a name that exists removes it", R.forget("重来") is True)
        check("forgetting it again says nothing was removed",
              R.forget("重来") is False)
        check("and the file no longer names it",
              "重来".encode("utf-8") not in io.open(file_path, "rb").read(),
              io.open(file_path, "rb").read()[:80])
    finally:
        os.environ.pop(R._PV.STATE_DIR_ENV, None)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("RECIPES: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("RECIPES: %d CHECKS PASSED -- A NAME IS REQUIRED, A CORRUPT FILE READS AS "
          "EMPTY, AND EVERY STORED SENTENCE STILL READS" % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""A civilisation name typed by a player must reach the file as a token the engine reads.

WHY THIS PIN EXISTS
-------------------
`_probe/test_rule_box_examples.py` fixed one box that promised a capability the
code did not have.  The same afternoon, asking the same question of the
「整份 AI 脚本」 form found a failure that is quieter than an empty box: the form
had a 民族 field, and its value went into `(civ-selected X)` with no check at all.

Instrumented, every spelling a player is likely to use was WRONG:

    「不列颠」  -> (civ-selected 不列颠)   Chinese inside a .per file
    "British"   -> (civ-selected british)  the .dat's spelling, not the engine's
    "britons2"  -> (civ-selected britons2) a name nobody has ever had

and all three returned `problems: []`, `diagnostics: []`.  So the player got a
file that loads, runs, and whose civilisation rule (`civ-unique`, the one that
trains the unique unit) never fires -- with nothing anywhere saying so.

The root cause was three separate name spaces and one bridge missing between
them: the .dat titles a civilisation "British", the tree files call its stem
"BRITONS", and the `.per` parser matches ONLY its own table, which spells the
classic civilisations as adjectives ("briton", "frankish", "gothic", "teutonic",
"turkish", "celtic", "incan", "slavic", "indian").  `aigen.CIVS` already held
exactly the right 54 values, with the corpus citation in its comment, and
`grep -rn CIVS aoe2mod/` returned the definition and nothing else: a correct
table that no code consulted, which is indistinguishable from no table at all.

WHAT IT CHECKS
--------------
1. every one of the 62 playable civilisations resolves, from its Chinese name,
   its .dat spelling, a tree stem, its engine token and its civ id -- and all
   five agree;
2. the resolved tokens are exactly the ones the two authorities agree on:
   `aigen.CIVS` (corpus) and `values_by_domain` of `commands["civ-selected"]`
   in `aoe2mod/data/ai_grammar.json` (the checker's own table);
3. every token the table emits is either a name in that corpus list or a civ id
   the corpus really passes as a number, and the three rows that rest on
   extrapolation alone are named out loud rather than hidden;
4. a resolved name reaches the composed file as `(civ-selected briton)`, and the
   file contains no Chinese at all;
5. an unresolvable name produces a `problems` entry naming the field, and the
   file then contains no `civ-selected` rule rather than a broken one;
6. the same through the real surface: `App.ai_script_build`, the route the
   page's 「生成整份脚本」 button calls.

WHAT IT DOES NOT DO
-------------------
It does not check that the generated AI is *good*, and it does not pin the
wording of the refusal.  A reworded refusal is not a regression; a name that
used to resolve and now produces nothing is.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.game import aigen, civnames                # noqa: E402
from aoe2mod.game import civtechtrees                   # noqa: E402
from aoe2mod.ui import server as S                      # noqa: E402

FAILS = []

#: Rows whose argument is a civ id rather than a name, and which the corpus does
#: NOT show as a number.  Named here so that "we extrapolated" stays a statement
#: in the open instead of a comment somebody deletes.
EXTRAPOLATED = {"Saxons": "60", "Varangians": "61", "Danes": "62"}


def ck(what, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (("  ::  %r" % (detail,))
                                                    if not ok else ""))
    if not ok:
        FAILS.append((what, detail))


def grammar_civ_values():
    """The checker's own `(civ-selected X)` domain, from the shipped table."""
    g = json.load(io.open(os.path.join(ROOT, "aoe2mod", "data", "ai_grammar.json"),
                          encoding="utf-8"))
    arg = g["commands"]["civ-selected"]["args"][0]
    words, nums = set(), set()
    for vals in (arg.get("values_by_domain") or {}).values():
        for v in vals:
            (nums if str(v).isdigit() else words).add(v)
    return words, nums


def civ_lines(text):
    return [ln.strip() for ln in text.splitlines() if "civ-selected" in ln]


def main():
    words, nums = grammar_civ_values()

    # --- 1. every spelling of every civilisation resolves, and they agree ---
    print("-- all 62 civilisations, from every spelling a caller may hand over")
    ck("the table covers every playable civilisation",
       len(civnames.CIV_ENGINE) == 62 and len(civnames.CIV_ZH) == 62,
       (len(civnames.CIV_ENGINE), len(civnames.CIV_ZH)))
    disagree = []
    for zh, en in civnames.CIV_ZH.items():
        want = civnames.CIV_ENGINE.get(en)
        # Real spellings only.  `civ_file_stem` is the tree's own spelling
        # ("British" -> "BRITONS"), so this asks about a name that exists
        # instead of one the test invented by appending an "S".
        stem = civtechtrees.civ_file_stem(en)
        for spelling in (zh, en, en.lower(), en.upper(), stem, stem.lower()):
            got = civnames.engine_name(spelling)
            if got != want:
                disagree.append((zh, en, spelling, got, want))
    ck("Chinese / .dat / lower / UPPER / tree stem all land on the same token",
       not disagree, disagree[:4])
    ck("a tree stem is resolved through the existing bridge, not a second copy",
       civnames.engine_name("BRITONS") == "briton"
       and civnames.engine_name("INCAS") == "incan",
       (civnames.engine_name("BRITONS"), civnames.engine_name("INCAS")))
    ck("a civ id is accepted as an id", civnames.engine_name("1") == "1",
       civnames.engine_name("1"))
    ck("a non-civilisation returns None rather than a guess",
       civnames.engine_name("台北") is None
       and civnames.engine_name("britons2") is None
       and civnames.engine_name("") is None,
       (civnames.engine_name("台北"), civnames.engine_name("britons2")))
    ck("Gaia is not offered as a playable civilisation",
       civnames.engine_name("Gaia") is None, civnames.engine_name("Gaia"))

    # --- 2. the tokens are the ones the two authorities agree on ----------
    print("-- the token table is the corpus list, not a list somebody typed")
    named = {t for t in civnames.ENGINE_TOKENS if not t.isdigit()}
    ck("aigen.CIVS is exactly the issued name tokens",
       named == set(aigen.CIVS), sorted(named ^ set(aigen.CIVS)))
    ck("and every one of them appears in the grammar's civ-selected domain",
       not (named - words), sorted(named - words))

    # --- 3. numeric rows are ids the corpus really passes -----------------
    print("-- numeric rows: observed ids, and the three that are extrapolated")
    ids = {t for t in civnames.ENGINE_TOKENS if t.isdigit()}
    observed = ids - set(EXTRAPOLATED.values())
    ck("every non-extrapolated id is one the corpus passes as a number",
       not (observed - nums), sorted(observed - nums))
    ck("the extrapolated rows are exactly the ones the corpus never passes",
       set(EXTRAPOLATED.values()).isdisjoint(nums),
       sorted(set(EXTRAPOLATED.values()) & nums))
    ck("and they are the ids matching the .dat's own 0..62 numbering",
       all(civnames.civ_id(en) == int(tok) for en, tok in EXTRAPOLATED.items()),
       {en: (civnames.civ_id(en), tok) for en, tok in EXTRAPOLATED.items()})
    ck("the .dat numbering is 0..62 with Gaia at 0",
       civnames.civ_id("Gaia") is None and civnames.civ_id("British") == 1
       and civnames.civ_id("Danes") == 62,
       (civnames.civ_id("British"), civnames.civ_id("Danes")))

    # --- 4. a resolved name reaches the file as a token -------------------
    print("-- resolved name -> the file")
    app = S.App()
    voc = app.ailang_vocab()
    for typed, want in (("不列颠", "briton"), ("British", "briton"),
                        ("印加", "incan"), ("达罗毗荼", "40"), ("Puru", "56")):
        plan = aigen.Plan(name="MyAI", civ=typed, army="knight:15")
        text, diags, problems = aigen.check(plan, voc)
        lines = civ_lines(text)
        ck("%r becomes (civ-selected %s)" % (typed, want),
           lines == ["(civ-selected %s)" % want], lines)
        ck("%r reports no problem" % typed, not problems, problems)
        ck("%r passes the checker" % typed, not diags, diags)
    text, _d, _p = aigen.check(
        aigen.Plan(name="MyAI", civ="不列颠", army="knight:15"), voc)
    ck("the composed file contains no Chinese at all",
       not re.search(r"[\u4e00-\u9fff]", text),
       re.findall(r".{0,20}[\u4e00-\u9fff].{0,20}", text)[:3])

    # --- 5. an unresolvable name is reported, and no broken rule is emitted -
    print("-- unresolvable name")
    for typed in ("britons2", "台北", "English"):
        text, diags, problems = aigen.check(
            aigen.Plan(name="MyAI", civ=typed, army="knight:15"), voc)
        ck("%r is reported as a problem" % typed,
           [p for p in problems if p.get("field") == "civ"], problems)
        ck("%r emits no civ-selected rule instead of a wrong one" % typed,
           not civ_lines(text), civ_lines(text))
        ck("%r still reports no checker noise" % typed, not diags, diags)

    # --- 6. the same through the surface the button calls ------------------
    print("-- App.ai_script_build (what 「生成整份脚本」 posts to)")
    r = app.ai_script_build({"plan": {"name": "MyAI", "civ": "不列颠",
                                      "army": "knight:15", "villagers": 30,
                                      "attack_at": 20, "age": "feudal-age",
                                      "wall": False}})
    ck("the route answers ok", r.get("ok") is True, list(r)[:5])
    ck("its text carries the resolved token",
       "(civ-selected briton)" in (r.get("text") or ""),
       civ_lines(r.get("text") or ""))
    ck("its plan reports what it resolved", r["plan"].get("civ") == "briton",
       r["plan"].get("civ"))
    ck("and it keeps no dangling unresolved word",
       r["plan"].get("civ_unresolved") is None, r["plan"].get("civ_unresolved"))
    r2 = app.ai_script_build({"plan": {"civ": "britons2", "army": "knight:15"}})
    ck("a made-up name comes back as a problem on this route too",
       [p for p in (r2.get("problems") or []) if p.get("field") == "civ"],
       r2.get("problems"))
    ck("and the route does not fail outright", r2.get("ok") is True, list(r2)[:5])

    # --- 7. the form still says what it means ----------------------------
    print("-- the field on the page")
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()
    ck("the 民族 field is still on the page", 'id="lang-plan-civ"' in page)
    m = re.search(r'id="lang-plan-civ"[^>]*placeholder="([^"]*)"', page)
    ck("its placeholder still says leaving it blank means any civilisation",
       bool(m) and "留空" in m.group(1), m.group(1) if m else None)

    # --- 8. the complaint reaches the player as words --------------------
    # `problems` are rows ({field, value, why}), and the page used to hand the
    # row itself to textContent: the panel said a requirement had not been
    # dropped, then printed "[object Object]" where the reason should be.  The
    # check is textual because the defect is exactly one expression in the
    # renderer; a browser run is in `_probe/_tmp/chk_plan_civ_page.py`.
    print("-- what the panel prints for a problem")
    ck("the renderer no longer prints the row itself",
       'langLines(host, p, "why")' not in page)
    ck("it prints a sentence made from the row instead",
       "langLines(host, problemText(p), \"why\")" in page)
    ck("and that helper handles a bare string too",
       "typeof p === \"string\"" in page and "p.value" in page and "p.why" in page)

    print()
    if FAILS:
        print("AI PLAN CIV: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("AI PLAN CIV: EVERY CIVILISATION A PLAYER CAN NAME REACHES THE FILE AS A "
          "TOKEN THE ENGINE READS, AND ONE IT CANNOT IS SAID OUT LOUD")
    return 0


if __name__ == "__main__":
    sys.exit(main())

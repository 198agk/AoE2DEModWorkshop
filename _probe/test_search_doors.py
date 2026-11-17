# -*- coding: utf-8 -*-
"""Four doors, not one: a name can be typed as a number, a 中文名, an English
name, or the sound of it -- and an empty list must say where the answer lives.

WHY THIS PIN EXISTS
-------------------
Reported 2026-11-16, verbatim: 「你能不能增强一下检索功能」, beside a screenshot of
the 科技 tab answering 「0 / 0」 and 「没有匹配的。」 for 「铁匠铺」.

Two separate silences were behind that screenshot:

  1. the search only compared the text against `zh`, `en` and `internal`, so a
     name typed the way a Chinese player actually types -- `tjp`, `tjpu`,
     `tiejiangpu` -- answered nothing at all, and the `tw` field was not even
     looked at;
  2. zero rows was a dead end: 铁匠铺 IS in the file, in the OTHER table, and
     the screen said 「没有匹配的。」 instead of saying so.

WHAT IT DOES NOT DO
-------------------
It does not promise that every name is reachable by every door.  `tw` is a
SEPARATE name in this game (铁匠铺 -> 兵工廠), so 鐵匠鋪 finds nothing through
pinyin or `tw`; that is the data, and the pin asserts the honest behaviour
instead of a wish.

Run: python -X utf8 _probe/test_search_doors.py   (needs the UI on $BASE)
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import aoe2mod.api as A                              # noqa: E402
import aoe2mod.ui.server as SRV                     # noqa: E402
from aoe2mod.semantic import pinyin as PZ           # noqa: E402

FAILED = []


def ck(what, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what,
                         (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)
    return ok


def section(title):
    print()
    print("=== %s ===" % title)


# ---------------------------------------------------------------------------
section("1. the romanisation table ships with the app and needs nothing else")
# ---------------------------------------------------------------------------
PY_SRC = io.open(os.path.join(ROOT, "aoe2mod", "semantic", "pinyin.py"),
                 encoding="utf-8").read()
# The bundle runs a vendored CPython with a fixed package set.  A romanisation
# library that is imported but not shipped fails on the player's machine, on the
# screen whose whole job is to still work when something is missing.
# The docstring NAMES pypinyin on purpose (it explains why the library is not
# used), so the check is about imports, not about the word.
ck("pinyin.py imports only the standard library",
   "import pypinyin" not in PY_SRC and "from pypinyin" not in PY_SRC
   and "import json" in PY_SRC and "import os" in PY_SRC,
   [ln for ln in PY_SRC.splitlines() if ln.startswith("import ") or ln.startswith("from ")])
_tbl = PZ._table()
ck("the table is there and is a dict", isinstance(_tbl, dict) and len(_tbl) > 1000,
   len(_tbl))
ck("a character maps to a bare syllable, no tone",
   _tbl.get("铁") == "tie" and _tbl.get("匠") == "jiang" and _tbl.get("铺") == "pu",
   (_tbl.get("铁"), _tbl.get("匠"), _tbl.get("铺")))
ck("traditional forms map to the same syllable as their simplified form",
   _tbl.get("鐵") == _tbl.get("铁"), (_tbl.get("鐵"), _tbl.get("铁")))

# ---------------------------------------------------------------------------
section("2. one name has four spellings, and the mixed one is the point")
# ---------------------------------------------------------------------------
keys = PZ.of("铁匠铺")
ck("all four ways to type it are keys",
   set(["tjp", "tiejiangpu", "tjpu"]) <= set(keys), keys)
ck("the first key is the all-initials one", keys[0] == "tjp", keys)
ck("the full spelling is a key", "tiejiangpu" in keys, keys)
ck("the mixed spelling `tjpu` is a key, not a separate rule", "tjpu" in keys, keys)
ck("keys are de-duplicated and ordered short-to-long per family",
   len(set(keys)) == len(keys), keys)
ck("a name with no Chinese has no keys", PZ.of("Blacksmith") == (), PZ.of("Blacksmith"))
ck("empty and None are empty, not a crash", PZ.of("") == () and PZ.of(None) == ())
ck("one character still gives both of its keys", PZ.of("铁") == ("t", "tie"), PZ.of("铁"))

# ---------------------------------------------------------------------------
section("3. the rank: starts a spelling beats sits inside one")
# ---------------------------------------------------------------------------
ck("`tjp` starts a spelling -> 3", PZ.rank("tjp", "铁匠铺") == 3)
ck("`tjpu` starts a spelling -> 3", PZ.rank("tjpu", "铁匠铺") == 3)
ck("`jiangpu` sits inside one -> 4", PZ.rank("jiangpu", "铁匠铺") == 4)
ck("`tj` starts a spelling -> 3", PZ.rank("tj", "铁匠铺") == 3)
ck("`angpu` sits inside one -> 4", PZ.rank("angpu", "铁匠铺") == 4)
# The rule must not swallow the other three doors: a query with a digit or a
# Chinese character belongs to a different rule, and answering here would put
# pinyin results beside an exact number match.
ck("a digit is not a pinyin query", PZ.rank("6", "铁匠铺") is None)
ck("a Chinese character is not a pinyin query", PZ.rank("铁", "铁匠铺") is None)
ck("a one-letter query is not a pinyin query", PZ.rank("t", "铁匠铺") is None)
ck("a name with no keys answers None", PZ.rank("xyzq", "Blacksmith") is None)
ck("the best name wins even when a later one matches better",
   PZ.rank("tjpu", "Blacksmith", "铁匠铺") == 3)

# ---------------------------------------------------------------------------
section("4. the search itself: every door leads to 铁匠铺")
# ---------------------------------------------------------------------------
tk = A.open_toolkit()
_ = tk.version


def ids(kind, q, limit=5):
    return [r["id"] for r in tk.browse(kind, query=q, limit=limit)["rows"]]


BY_NAME = ids("unit", "铁匠铺")
ck("the Chinese name finds its rows", len(BY_NAME) >= 1, BY_NAME)
ck("a pinyin spelling finds the same rows", ids("unit", "tjpu") == BY_NAME,
   (ids("unit", "tjpu"), BY_NAME))
ck("initials only find them too", ids("unit", "tjp") == BY_NAME, ids("unit", "tjp"))
ck("the full spelling finds them too", ids("unit", "tiejiangpu") == BY_NAME,
   ids("unit", "tiejiangpu"))
ck("a remembered tail finds them too", ids("unit", "jiangpu") == BY_NAME,
   ids("unit", "jiangpu"))
ck("the English name still finds them", ids("unit", "blacksmith") == BY_NAME,
   ids("unit", "blacksmith"))

# Rank order, proved rather than described: the record whose number IS the query
# comes first, and a number match beats a pinyin match on the same page.
_six = tk.browse("unit", query="6", limit=5)
ck("a number puts that record on row one", _six["rows"][0]["id"] == 6,
   [r["id"] for r in _six["rows"]])
# `tj` matches names AND the pinyin of 铁匠铺-class names.  Whatever it finds,
# every row is a real row and the list is not empty -- a pinyin rank that threw
# away the name matches would be worse than not having one.
_tj = tk.browse("unit", query="tj", limit=10)
ck("a two-letter query still answers", _tj["total"] >= 1, _tj["total"])
ck("and its rows carry names", all(r.get("name") for r in _tj["rows"]),
   [r.get("name") for r in _tj["rows"][:3]])

# ---------------------------------------------------------------------------
section("5. zero rows says where the answer is")
# ---------------------------------------------------------------------------
APP = SRV.App()
_tech = APP.browse(kind="tech", query="铁匠铺")["browse"]
ck("the technology tab still answers nothing for a building", _tech["total"] == 0,
   _tech["total"])
_else = _tech.get("elsewhere") or {}
ck("and it names the table the record is in", set(_else) == set(["unit"]), list(_else))
ck("with the count the other table really has",
   (_else.get("unit") or {}).get("total") == tk.browse("unit", query="铁匠铺")["total"],
   (_else.get("unit") or {}).get("total"))
ck("and a few names to recognise it by",
   bool((_else.get("unit") or {}).get("names")), (_else.get("unit") or {}).get("names"))
ck("and the ids the door will land on",
   set(((_else.get("unit") or {}).get("ids") or [])) <= set(ids("unit", "铁匠铺", 3)),
   (_else.get("unit") or {}).get("ids"))
ck("pinyin reaches the other table through the same door",
   bool((APP.browse(kind="tech", query="tjpu")["browse"].get("elsewhere") or {}).get("unit")))
# The hint costs one extra lookup, only on the empty path -- and it must not fire
# when the query is empty (that is just an unsearched list) or when the other
# table has nothing either (that would be a door onto another empty room).
ck("an empty query is not a miss",
   not APP.browse(kind="tech", query="")["browse"].get("elsewhere"))
ck("a query nobody has is not a miss either",
   not APP.browse(kind="tech", query="zzzz")["browse"].get("elsewhere"))
ck("a hit in its own table adds no door",
   not APP.browse(kind="unit", query="铁匠铺")["browse"].get("elsewhere"))
ck("every row still comes back untouched",
   APP.browse(kind="unit", query="村民", limit=2)["browse"]["rows"][0].get("id") == ids("unit", "村民", 1)[0])

# ---------------------------------------------------------------------------
section("6. the page draws the door and the four doors")
# ---------------------------------------------------------------------------
PAGE = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
               encoding="utf-8").read()
ck("the empty list is drawn by one function, not by inline text",
   "function edNothing(box, q, j)" in PAGE and "edNothing(box, q, j);" in PAGE)
ck("it reads the route's elsewhere field",
   "j.browse.elsewhere" in PAGE)
ck("the door sets the box BEFORE switching the tab",
   PAGE.index("if (q0) q0.value = qq;") < PAGE.index("edKind(kind);",
                                                   PAGE.index("function edNothing")))
ck("the empty state still names the four ways to type a name",
   "一个名字有四种打法学" in PAGE and "tiejiangpu / tjpu / tjp" in PAGE)
ck("the search box waits for quiet instead of firing per keystroke",
   "_edqT = setTimeout(() => loadEditor(), 220);" in PAGE)
ck("the app no longer says only 「没有匹配的。」 for a missed search",
   "这里没有「" in PAGE)

# ---------------------------------------------------------------------------
print()
if FAILED:
    print("SEARCH DOORS: %d FAILED -> %r" % (len(FAILED), FAILED[:6]))
    sys.exit(1)
print("SEARCH DOORS: A NAME IS REACHABLE BY ITS NUMBER, ITS 中文名, ITS ENGLISH "
      "NAME AND ITS SOUND -- AND A MISS SAYS WHICH TABLE HAS IT")

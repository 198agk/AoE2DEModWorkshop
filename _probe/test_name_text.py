# -*- coding: utf-8 -*-
"""A mod's own Chinese names must not be shown as `è´¸æ\x98\x93`.

Reported 2026-11-06 with a screenshot of the tech tab on the user's own mod
(文明联盟 test 9, 125 MB): every row read `æ®åä¸ää½¬`, and the panel beside it
said `读不到字段：_Stop: 没有说明`.  The red line had its own cause (a thread race
in `tablefields.stage_offsets`); the mojibake is this file's subject.

The cause is a rule that is correct where it lives and wrong where it was used:
`parser.Reader.debug_string` decodes latin-1, because the reader must round-trip
every byte it read and a guessing codec would corrupt a record on the way back
out.  The screens then printed that latin-1 text verbatim.

Measured that day: of the mod's 5,874 technology names, **230** are UTF-8 bytes
written into a byte string; of 136,861 unit names, **4,473** are.  The shipped
English data has none, so nothing there changed.

`game/nametext.py` puts the guess on the DISPLAY side only:
`readable()` re-encodes latin-1 and tries UTF-8, falling back to the text it was
given; `stored()` writes UTF-8 for a name a player typed.  Nothing on a write
path calls `readable`.

This pin is written to catch the three ways that can go wrong:

  1. being too eager -- `SPRMN`, `Milícia`, and genuinely-latin-1 bytes with no
     valid UTF-8 reading must all come back unchanged;
  2. being too shy -- the actual mod strings from the screenshot must decode;
  3. drifting to the write path -- `stored()` must be UTF-8, and a name written
     through it must read back through `readable()`, or a rename would start
     storing mojibake of its own.

Run: python -X utf8 _probe/test_name_text.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
from aoe2mod.game import nametext as NT
from aoe2mod.semantic import index as SEM

IDX_SRC = os.path.join(ROOT, "aoe2mod", "semantic", "index.py")

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
section("1. the exact strings from the screenshot decode")
# ---------------------------------------------------------------------------
# These are the byte strings taken out of the mod's .dat by `_probe/_tmp/
# t_mojibake.py` on 2026-11-06; the right-hand side is what the author typed.
CASES = [
    ("å¼\x80å±\x80bonusç§\x91æ\x8a\x80ç¦\x81ç\x94¨", "开局bonus科技禁用"),
    ("ç\xa0\x94ç©¶å\x8d\x95ä½\x8dæ\x95°é\x87\x8fé\x99\x90å\x88¶(make avail)",
     "研究单位数量限制(make avail)"),
    ("è´¸æ\x98\x93è\x8e·å\x8f\x96ç\x9f³å¤´", "贸易获取石头"),
]
for raw, want in CASES:
    got = NT.readable(raw)
    ck("decodes %r" % (want,), got == want, got)

# ---------------------------------------------------------------------------
section("2. everything that is not UTF-8 comes back untouched")
# ---------------------------------------------------------------------------
for same in ("SPRMN", "VMBAS", "Milícia", "Tarkan (make avail)", "弩手", ""):
    ck("%r is left as it was" % (same,), NT.readable(same) == same, NT.readable(same))
ck("None passes through", NT.readable(None) is None)
# 0xFF is never valid UTF-8, so these bytes must not be "helpfully" decoded.
latin_bad = b"\xff\xfe".decode("latin-1")
ck("invalid UTF-8 stays latin-1", NT.readable(latin_bad) == latin_bad, repr(NT.readable(latin_bad)))
# A string that is ALREADY real Unicode (from a JSON table) must not be re-mangled:
already = "贸易获取石头"
ck("already-decoded Unicode is untouched", NT.readable(already) == already, NT.readable(already))

# ---------------------------------------------------------------------------
section("3. a name written through `stored` reads back through `readable`")
# ---------------------------------------------------------------------------
for name in ("弩手甲", "Machinery 改", "æ®ç©º", "A"):
    body = NT.stored(name)
    back = NT.readable(body.decode("latin-1"))
    ck("%r round-trips through the file bytes" % (name,), back == name, back)
ck("`stored` is UTF-8, not latin-1", NT.stored("弩") == "弩".encode("utf-8"),
   NT.stored("弩"))
ck("`stored(None)` is empty", NT.stored(None) == b"")
ck("`stored` of bytes is those bytes", NT.stored(b"abc") == b"abc")

# ---------------------------------------------------------------------------
section("3b. the second family: GBK written into the same byte string")
# ---------------------------------------------------------------------------
# `2026 三国文明联盟整合11.06` names its units `°¢×ÈÌØ¿Ë`.  Reported 2026-11-07
# (「还有为什么总是有乱码」).  It is not UTF-8, so section 2's rule returned it
# unchanged and the command panel drew the raw bytes.  GBK is the other encoding
# these mods use, and it can be recognised without guessing.
GBK_CASES = [
    (b"\xb0\xa2\xd7\xc8\xcc\xd8\xbf\xcb", "阿兹特克"),
    (b"\xb0\xa3\xc8\xfb", "埃塞"),
    (b"\xb0\xd8\xb0\xd8\xb6\xfb", "柏柏尔"),
    (b"\xd5\xbd\xea\xaa", "战戟"),
]
for raw, want in GBK_CASES:
    got = NT.readable(raw.decode("latin-1"))
    ck("GBK %r reads as %r" % (raw, want), got == want, got)
# The one that made the rule strict: a French name with ONE high byte.  GBK
# turns 0xC9 into 蒫 and leaves six ASCII letters, so「有没有汉字」passes; an odd
# count of high bytes is the tell that it was never a GBK pair.
ck("a French name with one high byte is left alone",
   NT.readable(b"\xc9cossais".decode("latin-1")) == b"\xc9cossais".decode("latin-1"),
   NT.readable(b"\xc9cossais".decode("latin-1")))
# A plain English name must not be touched either -- and pure ASCII never even
# reaches the second decoder.
ck("an ASCII name is not re-read as GBK", NT.readable("SPRMN") == "SPRMN",
   NT.readable("SPRMN"))
# UTF-8 still wins: a GBK byte run is almost never valid UTF-8, and when two
# readings are both possible the earlier one keeps its place.
utf8_cn = "弩手甲".encode("utf-8").decode("latin-1")
ck("UTF-8 is still tried first", NT.readable(utf8_cn) == "弩手甲",
   NT.readable(utf8_cn))

# --- 3c. the third family: GBK, but padded with decoration -----------------
# `2026 三国文明联盟整合11.06` and `2026 Civilization A...` write names like
# `¡¤¡¤¡¤[ÖÐÌï]¡¤¡¤¡¤`, which is `·····[中田]·····`: GBK middle dots (0xA1 0xA4)
# around a Han name.  The strict rule「每个非 ASCII 字符都必须是 CJK」rejected
# exactly those 126 names and kept drawing the bytes, which is the same complaint
# one round later.  `_DECOR` is the punctuation a Chinese mod actually carries.
DECOR_CASES = [
    (b"\xa1\xa4" * 13 + b"[\xd6\xd0\xcc\xef]" + b"\xa1\xa4" * 22,
     "·" * 13 + "[中田]" + "·" * 22),
    (b"\xa1\xa4" * 17 + b"\xb4\xf3\xcc\xef" + b"\xa1\xa4" * 20,
     "·" * 17 + "大田" + "·" * 20),
]
for raw, want in DECOR_CASES:
    got = NT.readable(raw.decode("latin-1"))
    ck("a decorated GBK name reads through %r" % raw[:6], got == want, got[:40])
# The exception is a LIST, not a relaxation: a character outside it still vetoes.
# Without this line,「加点宽容」would silently become「什么都解」.
ck("decoration is a list, not a licence",
   hasattr(NT, "_DECOR") and "\u00b7" in NT._DECOR and len(NT._DECOR) < 20,
   sorted(NT._DECOR) if hasattr(NT, "_DECOR") else None)
ck("a kana in the middle still vetoes",
   NT.readable(b"\xa4\xa2\xa4\xa2\xa4\xa2".decode("latin-1"))
   == b"\xa4\xa2\xa4\xa2\xa4\xa2".decode("latin-1"),
   NT.readable(b"\xa4\xa2\xa4\xa2\xa4\xa2".decode("latin-1")))

# A patch that rebuilt this module's tail from `src[:index]` once deleted
# `stored()` outright (2026-11-07) and nothing noticed until a rename path ran:
# section 3 above would have caught it, but only if someone ran this file.  Five
# names are the module's whole contract with the rest of the tree, so say so once,
# cheaply, and let any import-time reader of this suite see it.
for fn in ("readable", "stored"):
    ck("nametext still exports `%s`" % fn, callable(getattr(NT, fn, None)),
       getattr(NT, fn, None))

# ---------------------------------------------------------------------------
section("4. the index is the only place the guess is made")
# ---------------------------------------------------------------------------
src = io.open(IDX_SRC, encoding="utf-8").read()
ck("Entity reads all four name fields through `readable`",
   src.count("NT.readable(") >= 4, src.count("NT.readable("))
ck("no field is assigned the raw value directly",
   re.search(r"self\.(internal|en|zh|tw) = raw\.get\(", src) is None)
ck("`display` still prefers the localised field",
   re.search(r"return self\.zh or self\.en or self\.internal", src) is not None)
# The write paths must NOT decode: a rename stores bytes, and a reader that
# guessed would corrupt them.  `records.py` is allowed to import `nametext` for
# `stored()` (it is the rename path), but it must never call `readable`.
for path in ("aoe2mod/dat/parser.py", "aoe2mod/dat/writer.py"):
    body = io.open(os.path.join(ROOT, *path.split("/")), encoding="utf-8").read()
    ck("%s never touches `nametext`" % path, "nametext" not in body)
_rec = io.open(os.path.join(ROOT, "aoe2mod", "dat", "records.py"), encoding="utf-8").read()
ck("records.py writes through `stored` and never decodes",
   "NTX.stored(" in _rec and "NTX.readable(" not in _rec,
   (_rec.count("NTX.stored("), _rec.count("NTX.readable(")))

# ---------------------------------------------------------------------------
section("5. a real mod row displays readably")
# ---------------------------------------------------------------------------
tk = A.open_toolkit()
_ = tk.version
e = SEM.Entity("tech", 5844, {"internal": CASES[0][0], "resolved": True})
ck("an Entity built from mod bytes displays the author's text",
   e.display == CASES[0][1], e.display)
ix = tk.index()
moji = [u for u in ix.units.values() if "\xc3\xa5" in (u.internal or "")]
ck("the shipped index has no mojibake left in it", not moji,
   [(u.id, u.internal) for u in moji[:3]])
shown = [u.display for u in list(ix.units.values())[:4000] if u.display]
bad = [s for s in shown if "\xc3\xa5" in s or "\xc3\xa6" in s]
ck("4000 displayed unit names contain no latin-1 mojibake", not bad, bad[:4])

section("6. the other reads of the same bytes decode too")
# The index is one of five ways a .dat name reaches the screen.  The other four
# live in `aio2mod/ui/server.py` and were latin-1 raw until 2026-11-06: the
# effect table's rows, one effect's fields, an effect record's name in the read
# result, and the en->zh pairing that names the effect attached to a technology.
# Measured before the fix: `table_rows("effect")` said `Magyarséå æç`.
import aoe2mod.ui.server as SRV

srv = io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
              encoding="utf-8").read()
ck("table_rows decodes the row label",
   'nm = NTX.readable(rec.get("name")) or ""' in srv)
ck("table_rows searches the decoded label, not the raw one",
   "if qs and qs not in nm.lower():" in srv)
ck("table_fields decodes the record name",
   '"name": NTX.readable(rec.get("name")) or ""' in srv)
ck("an effect's own name in the effect list decodes",
   '"effect_name": NTX.readable(got.get("effect_name"))' in srv)
ck("the effect reference decodes before pairing",
   'en = (NTX.readable(e.get("name")) or "").strip()' in srv)
ck("both sides of the en->zh pair decode",
   "by_en.setdefault(NTX.readable(t.en).strip().lower(), t.zh)" in srv)

_app2 = SRV.App()
rows = _app2.table_rows("effect", limit=400)
badrows = [r for r in (rows.get("rows") or [])
           if "\xc3\xa5" in (r.get("name") or "") or "\xc3\xa6" in (r.get("name") or "")]
ck("no effect row in the first 400 still carries latin-1 mojibake",
   not badrows, [(r.get("index"), r.get("name")) for r in badrows[:3]])
# And the search box must find an effect by the name the row shows -- a decoded
# label with a raw search is a row you can see and cannot find.
# Search the name a row SHOWS.  This install's 1,500 effect names are all ASCII
# ("New Effect", "Magyars Tech Tree"), so a Chinese one only exists on the user's
# mod -- and a nail that needs a file outside the repo fails on another machine.
# The property that matters can be checked here instead: the string the search
# compares against is the string the row displays.  Take a real name out of the
# listing and search it.
_all = _app2.table_rows("effect", limit=4000)
_pick = next((r for r in (_all.get("rows") or [])
              if (r.get("name") or "").strip() and len(r.get("name") or "") > 4), None)
ck("there is an effect name to search for", _pick is not None)
if _pick is not None:
    again = _app2.table_rows("effect", q=_pick["name"], limit=5)
    found = [h for h in (again.get("rows") or []) if h.get("index") == _pick["index"]]
    ck("搜显示出来的那个名字能搜到那一行", bool(found),
       (_pick["name"], [h.get("index") for h in (again.get("rows") or [])][:4]))
    ck("and the row it finds shows the same name",
       bool(found) and found[0].get("name") == _pick["name"],
       found[0].get("name") if found else None)

# ---------------------------------------------------------------------------
section("7. a number in the search box is an id")
# ---
# Two screens promise this and neither delivered it.  The command panel's box
# says 「打名字或编号，比如 村民、83」; the editor's said 「按名字过滤…」.  Until
# 2026-11-08 `Toolkit.browse` only compared the text against `zh`/`en`/`internal`,
# so `q=83` answered `total 0` -- you could see 「编号 5073」 written beside a
# record and had no way to reach it by that number.  Measured: `q=83` -> 0,
# `q=村民` -> 3.
_tk2 = A.open_toolkit()
_ = _tk2.version
# `Toolkit.browse` is the raw one; `App.browse` is what wraps it in `{ok, browse}`.
_all = _tk2.browse("unit", limit=1)["total"]
_by_id = _tk2.browse("unit", query="83", limit=5)
ck("a number finds the one record with that id",
   _by_id["total"] == 1 and _by_id["rows"][0]["id"] == 83,
   (_by_id["total"], [r["id"] for r in _by_id["rows"][:3]]))
ck("and nothing else came along with it", _by_id["total"] < _all, _all)
# An id is matched EXACTLY.  A prefix rule would put 5073 beside 50730 and read
# like a name search that happens to be wrong.  `8` also appears INSIDE four real
# names (碎石 8 x 8, 山脉 8), so the honest check is: the record numbered 8 comes
# first, and every other row earned its place from its name, not from its number.
_by_id2 = _tk2.browse("unit", query="8", limit=20)
_rest = _by_id2["rows"][1:]
ck("the record with that number comes first",
   _by_id2["rows"][0]["id"] == 8, [r["id"] for r in _by_id2["rows"][:4]])
# A prefix rule on the id would have dragged in 80..89 and 800..899.  What the
# rest of the page holds is instead names that contain the digit somewhere --
# 碎石 8 x 8, 山脉 8, and 空 (whose internal name has an 8 in it).
ck("a number is not a prefix search",
   all(not str(r["id"]).startswith("8") for r in _rest),
   [(r["id"], r.get("name")) for r in _rest[:4]])
ck("a number no record uses finds nothing",
   _tk2.browse("unit", query="31999", limit=5)["total"] == 0)
# A digit string that happens to be inside a name still has to find that name:
# the id test is an OR, not a replacement.
_by_name = _tk2.browse("unit", query="村民", limit=5)
ck("a name still finds its rows", _by_name["total"] >= 1,
   (_by_name["total"], [r["id"] for r in _by_name["rows"][:3]]))
# Read what the route actually does, because the search box lives in another file
# and a missing branch there is invisible from here.
_api_src = io.open(os.path.join(ROOT, "aoe2mod", "api.py"), encoding="utf-8").read()
ck("browse turns a digit string into an id",
   "qid = int(q) if q.isdigit() else None" in _api_src)
ck("and compares it with the id before the names",
   "if q and uid != qid " in _api_src)
_page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                encoding="utf-8").read()
ck("the editor's box says it takes a number",
   "按名字或编号过滤" in _page and "按名字过滤…" not in _page)

# ---------------------------------------------------------------------------
print()
if FAILED:
    print("NAME TEXT: %d FAILED -> %r" % (len(FAILED), FAILED[:6]))
    sys.exit(1)
print("NAME TEXT: A .DAT NAME IS A BYTE STRING AND A CHINESE MOD WRITES UTF-8 IN "
      "IT -- THE SCREEN DECODES, THE FILE DOES NOT, AND A NAME THAT WAS ALREADY "
      "RIGHT COMES BACK UNCHANGED")

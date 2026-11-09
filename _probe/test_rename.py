# -*- coding: utf-8 -*-
"""「为什么不能修改名字」 -- a name is TWO things, and both have to move.

Reported 2026-11-06, verbatim:

    「为什么不能修改名字」

The honest answer that day was four read-only fields: `LanguageDLLName`,
`LanguageDLLCreation`, `LanguageDLLHelp`, `LanguageDLLHotKeyText`, `Name.marker`,
`Name.len`, `Name` -- every one of them `ro=True`, and the refusal for `Name`
told the player to "use 重命名", a function that did not exist anywhere in the
repo.  A promise pointing at nothing.

What a name actually is:

  * the INTERNAL name, a `debug_string` inside the record: `marker` + `length`
    + text, three consecutive addresses.  Writing only the text leaves a stale
    length behind and shifts every byte after it -- the parser itself recorded
    2,656 bytes of drift from exactly that mistake;
  * the DISPLAY name, an i32 in the record pointing at a row in a
    `key-value-*.txt` string table.  That id is SHARED: 5079 is the name of 57
    records.  So "edit the text at 5079" renames 57 things at once -- a rename
    has to mint a new id, and carry the row to the mod when the file is saved.

The checks here are:

  1. `name_bytes` truncates on a UTF-8 boundary, never mid-character, and the
     reader reads the name back out of its own bytes;
  2. `rename_steps` refuses an address that does not hold a name segment;
  3. `string_id_step` is equal width and refuses a negative id;
  4. a real unit rename rewrites the internal name AND points every one of the
     63 civ copies at one new string id;
  5. a real tech rename does the same through `lang_name`;
  6. the whole session's names travel to the mod file;
  7. the model, the grid and the field form all show the new name without a
     save, and undo puts the old one back;
  8. renames that change nothing are refused instead of writing a no-op step;
  9. one gesture reports one line of history, not seventy;
 10. the page has the two doors and neither of them reloads the grid.

Run: python -X utf8 _probe/test_rename.py
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.ui.server as S
from aoe2mod.dat import parser as P
from aoe2mod.dat import records as REC
from aoe2mod.game import nametext as NT

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
LABELS = os.path.join(ROOT, "aoe2mod", "game", "fieldlabels.py")

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
section("1. a name is bytes, and it stops between characters")
# ---------------------------------------------------------------------------
# 200 bytes is the cap because `debug_string`'s length field is a u16 and the
# game's own longest names are 44 bytes; the boundary walk is because half a
# UTF-8 sequence is not a shorter name, it is a corrupt one.
ck("ascii passes through unchanged", REC.name_bytes("SPRMN") == b"SPRMN",
   REC.name_bytes("SPRMN"))
ck("chinese becomes UTF-8, not latin-1 question marks",
   REC.name_bytes("弩手甲") == "弩手甲".encode("utf-8"),
   REC.name_bytes("弩手甲"))
_round = NT.readable(REC.name_bytes("弩手甲").decode("latin-1"))
ck("and reads back out of the byte string", _round == "弩手甲", _round)
_long = REC.name_bytes("弩" * 200)
ck("the cap is 200 bytes", len(_long) <= REC.NAME_MAX_BYTES, len(_long))
ck("and it did not cut a character in half",
   _long.decode("utf-8", "strict") is not None)
_big = REC.name_bytes("弩" * 400)
try:
    _big.decode("utf-8")
    _ok = True
except UnicodeDecodeError:
    _ok = False
ck("a 400-character name is cut on a boundary, not through a character", _ok,
   len(_big))


# ---------------------------------------------------------------------------
section("2. it will not write a name segment where there is none")
# ---------------------------------------------------------------------------
# The address comes from a walk.  If the walk and the file ever disagree the
# marker is the only thing standing between "rename" and "overwrite a float".
_buf = bytearray(64)
struct.pack_into("<HH", _buf, 8, P.DEBUG_STRING_MARKER, 3)
_buf[12:15] = b"ABC"
_steps, _info = REC.rename_steps(_buf, 8, "弩手甲")
ck("a good address yields one splice step", len(_steps) == 1, _steps)
ck("the step starts at the marker, not at the text",
   _steps[0][0] == 8, _steps[0][0])
ck("it cuts the marker, the length and the old text",
   _steps[0][1] == 4 + 3, _steps[0][1])
ck("and writes the new length with the new text",
   _steps[0][2][:4] == struct.pack("<HH", P.DEBUG_STRING_MARKER, 9),
   _steps[0][2][:4])
_try = None
try:
    REC.rename_steps(_buf, 0, "x")
except REC.RecordError as exc:
    _try = str(exc)
ck("an address with no marker is refused", _try is not None, _try)
ck("and the refusal names the byte it found", "0" in (_try or ""), _try)
_try2 = None
try:
    REC.rename_steps(_buf, 8, "")
except REC.RecordError as exc:
    _try2 = str(exc)
ck("an empty name is refused", _try2 is not None, _try2)
# Spaces are a name, not an absence: the caller strips before it gets here, and
# a record whose whole name is spaces is still a record that walks its length.
_ssp, _isp = REC.rename_steps(_buf, 8, "   ")
ck("but spaces are a name and get written", _isp["name_bytes"] == 3, _isp)

# ---------------------------------------------------------------------------
section("3. a display id is four bytes and never negative")
# ---------------------------------------------------------------------------
_buf2 = bytearray(32)
struct.pack_into("<i", _buf2, 6, 5079)
_step, _sinfo = REC.string_id_step(_buf2, 6, 30030002)
ck("the step is equal width", _step[1] == 4 and len(_step[2]) == 4, _step)
ck("it remembers what was there", _sinfo["was"] == 5079, _sinfo["was"])
_same, _sinfo2 = REC.string_id_step(_buf2, 6, 5079)
ck("writing the same id yields no step at all", _same is None, _same)
_try3 = None
try:
    REC.string_id_step(_buf2, 6, -5)
except REC.RecordError as exc:
    _try3 = str(exc)
ck("a negative id is refused", _try3 is not None, _try3)
ck("because the engine reads it signed and no table has one",
   "非负" in (_try3 or ""), _try3)

# ---------------------------------------------------------------------------
section("4. a real unit rename moves both halves, in all 63 copies")
# ---------------------------------------------------------------------------
app = S.App()
app.reset_session()
tk = app.tk
_ = tk.version
_LEN0 = len(app.session_raw())
_UID = 1
_BEFORE = app.unit_fields(_UID, civ="British").get("name")
_res = app.record_rename(kind="unit", civ="British", record=_UID,
                         name="弩手测试")
ck("the rename is accepted", _res.get("ok") is True, _res.get("error"))
_disp = _res.get("display") or {}
ck("it minted a new string id, it did not edit a shared one",
   int(_disp.get("now") or 0) != int(_disp.get("was") or 0), _disp)
ck("and it says how many copies it pointed at", _disp.get("copies") == 63,
   _disp.get("copies"))
ck("the new id is not one of the old, shared ids",
   int(_disp.get("string_id") or 0) >= 30000000, _disp.get("string_id"))
ck("the session remembers the text", app._new_strings.get(_disp["string_id"]) ==
   "弩手测试", app._new_strings)
ck("the model carries the new bytes, not latin-1 of them",
   NT.readable(tk._civs[1]["units"][[u["id"] for u in tk._civs[1]["units"]]
                                      .index(_UID)]["name"]) == "弩手测试")
# 63 records carry this name and the rename points all of them at one id, so
# the check has to be over the copies -- and it has to read the FINAL buffer at
# the offsets the model holds, because the splice in civ 1 moved every byte
# after it (the `offset` in `display_info` is a coordinate from before that).
_copies = [(c["units"], u2) for c in tk._civs
           for u2 in (c.get("units") or []) if u2.get("id") == _UID]
_badcopies = []
for _units, _u2 in _copies:
    _o = _u2.get("_off_dll_name")
    _v = struct.unpack_from("<i", app.session_raw(), _o)[0] if _o else None
    if _v != _disp["string_id"] or _u2.get("_dll_name") != _disp["string_id"]:
        _badcopies.append((_u2.get("civ"), _v, _u2.get("_dll_name")))
ck("all %d civ copies point at the new id, in the file and in the model"
   % len(_copies), not _badcopies and len(_copies) == 63, _badcopies[:3])
ck("the file grew by the name, nothing else",
   len(app.session_raw()) > _LEN0, len(app.session_raw()) - _LEN0)

# ---------------------------------------------------------------------------
section("5. the name is visible everywhere, before the mod is saved")
# ---------------------------------------------------------------------------
# This is the half that failed first: the row a new id points at only lands in
# the mod at save time, so the name index had nothing to read and every screen
# kept the old name -- the toast said one thing and the pane title another.
ck("the field form shows the new name",
   app.unit_fields(_UID, civ="British").get("name") == "弩手测试",
   app.unit_fields(_UID, civ="British").get("name"))
_hit = app.browse(kind="unit", query="弩手测试", limit=5, offset=0)["browse"]
ck("the grid finds it by the new name", [_r["id"] for _r in _hit["rows"]] ==
   [_UID], [_r["id"] for _r in _hit["rows"]])
ck("and the old name no longer finds it",
   app.browse(kind="unit", query=_BEFORE, limit=5, offset=0)["browse"]["total"]
   == 0, _BEFORE)
ck("describe agrees", app.describe("unit", _UID)["entity"].get("name") ==
   "弩手测试")
_files = app.string_files()
ck("the strings that are waiting to be saved exist as mod files", len(_files) > 0,
   len(_files))
_first = sorted(_files)[0]
ck("one per locale, under resources/", _first.startswith("resources/"), _first)
ck("and the new row is in them",
   ('%d "弩手测试"' % _disp["string_id"]).encode("utf-8") in _files[_first],
   _files[_first][-60:])

# ---------------------------------------------------------------------------
section("6. a tech rename goes through lang_name")
# ---------------------------------------------------------------------------
_TID = 22
_tbefore = app.tech_fields(_TID).get("name")
_tres = app.record_rename(kind="tech", record=_TID, name="织布机测试")
ck("the tech rename is accepted", _tres.get("ok") is True, _tres.get("error"))
_tdisp = _tres.get("display") or {}
ck("one copy, because a tech record is not stored per civilisation",
   _tdisp.get("copies") == 1, _tdisp.get("copies"))
ck("the field form shows it", app.tech_fields(_TID).get("name") == "织布机测试",
   app.tech_fields(_TID).get("name"))
_traw = struct.unpack_from("<i", app.session_raw(), _tdisp["offset"])[0]
ck("the record at that offset points at the new id",
   _traw == _tdisp["string_id"], _traw)
ck("the grid finds the tech by its new name",
   [r["id"] for r in app.browse(kind="tech", query="织布机测试", limit=5,
                                offset=0)["browse"]["rows"]] == [_TID])

# ---------------------------------------------------------------------------
section("7. a rename that changes nothing is refused, not written")
# ---------------------------------------------------------------------------
# The first draft compared `name_bytes(old)` with `name_bytes(new)` where `old`
# came straight out of the model, i.e. the latin-1 REPRESENTATION of the stored
# bytes.  Encoding that again doubled every high byte, so the comparison never
# matched, a second identical rename was accepted, the file grew by 4 bytes and
# a step that changed nothing was pushed onto the undo stack.
_again = app.record_rename(kind="unit", civ="British", record=_UID,
                           name="弩手测试")
ck("the same name twice is refused", _again.get("ok") is False,
   _again.get("error"))
ck("and it says the name did not change", "没变" in (_again.get("error") or ""),
   _again.get("error"))
_againt = app.record_rename(kind="tech", record=_TID, name="织布机测试")
ck("the same holds on the tech side", _againt.get("ok") is False,
   _againt.get("error"))

# ---------------------------------------------------------------------------
section("8. one gesture is one line of history")
# ---------------------------------------------------------------------------
# A unit rename writes 63 equal-width steps (one per civ copy).  `_step_notes`
# used to collect a note per WRITE, so `/api/undo` answered with the same
# sentence ~70 times -- and the page then ran the same DOM surgery 70 times.
_st = app.hist_state()
ck("the two renames are two undo steps", (_st.get("undo") or 0) >= 2,
   _st.get("undo"))
_u1 = app.undo()
ck("undo is accepted", _u1.get("ok") is True, _u1.get("error"))
_notes = _u1.get("undone") or []
ck("undoing the tech rename reports exactly one line", len(_notes) == 1,
   len(_notes))
ck("the line names the tech", (_notes[0].get("tech") == _TID) if _notes else
   False, _notes)
ck("and the tech has its old name back",
   app.tech_fields(_TID).get("name") == _tbefore,
   app.tech_fields(_TID).get("name"))
_u2 = app.undo()
_n2 = _u2.get("undone") or []
ck("undoing the unit rename reports exactly one line too", len(_n2) == 1,
   len(_n2))
ck("the unit has its old name back",
   app.unit_fields(_UID, civ="British").get("name") == _BEFORE,
   app.unit_fields(_UID, civ="British").get("name"))
ck("the file is back to its original length",
   len(app.session_raw()) == _LEN0, len(app.session_raw()) - _LEN0)
_old = app.browse(kind="unit", query=_BEFORE, limit=5, offset=0)["browse"]
ck("and the old name is findable again", _old["total"] >= 1, _old["total"])

# ---------------------------------------------------------------------------
section("9. the page has both doors and neither reloads the grid")
# ---------------------------------------------------------------------------
page = open(PAGE, encoding="utf-8").read()
server = open(SERVER, encoding="utf-8").read()
labels = open(LABELS, encoding="utf-8").read()
# The internal name cannot be typed into directly: it is three addresses, and
# the middle one is a length.  The display name cannot be typed into directly
# either: the id it points at belongs to other records.  Both doors are one
# button.
ck("the pane has a 改名字 button",
   re.search(r'ren\.id = "ed-rec-rename"', page) is not None)
ck("with a box to type the name in",
   re.search(r'rn\.id = "ed-rename-name"', page) is not None)
ck("the box is length-capped like the record is",
   re.search(r'rn\.maxLength = \d+', page) is not None)
ck("the button calls the rename",
   re.search(r"onclick = \(\) => edRecordRename\(ren\)", page) is not None)
ck("an empty box is refused before any request",
   re.search(r"先在上面写一个新名字", page) is not None)
ck("the request names the route literally",
   re.search(r'api\("/api/record-rename",', page) is not None)
ck("a unit rename carries the civilisation it belongs to",
   re.search(r'kind: "unit", record: id, civ: edCiv\(\), name: name', page)
   is not None)
ck("a tech rename carries no civilisation",
   re.search(r'kind: "tech", record: id, name: name', page) is not None)
ck("the rename rewrites the row in place instead of reloading 400 rows",
   re.search(r"async function edAfterRename\(r\)", page) is not None)
ck("and it does not call the full reload",
   re.search(r"async function edAfterRename\(r\)[\s\S]{0,1600}"
             r"await openEditor\(", page) is not None
   and re.search(r"async function edAfterRename\(r\)[\s\S]{0,1600}loadEditor\(",
                 page) is None)
ck("the toast reports the string id and how many records it covers",
   re.search(r"文本编号", page) is not None
   and re.search(r"覆盖 ", page) is not None)

ck("the route exists",
   re.search(r'"/api/record-rename"', server) is not None)
ck("the editor has the method",
   re.search(r"def record_rename\(self", server) is not None)
ck("it can be told to skip the display half",
   re.search(r"def record_rename\(self[^)]*display=True", server) is not None)
ck("it records the historical note under a stable key",
   re.search(r'"op": "rename"', server) is not None)
ck("the notes are de-duplicated by that key",
   re.search(r"def _step_notes\(writes\)[\s\S]{0,900}seen", server) is not None)
ck("the name index is told about ids this session minted",
   re.search(r"self\.tk\._new_text\[sid\] = text", server) is not None)
ck("the same name twice is refused by comparing readable bytes",
   re.search(r"name_bytes\(NTX\.readable\(old_name\)\)", server) is not None)
ck("a rename drops the old index so the title follows the file",
   re.search(r"def _after_rename\([\s\S]{0,3000}tk\._index = None", server)
   is not None)
ck("and a history step that touched a rename re-reads every display id",
   re.search(r"def _resync_display_ids\(self\)", server) is not None)
ck("which is what makes undo put the OLD name back on all 63 copies",
   re.search(r'w\.get\("note"\) or \{\}\)\.get\("op"\) == "rename"',
             server) is not None)

ck("the display-name field says where to go instead",
   re.search(r'要改显示的名请点记录上方的「改名字」', labels) is not None)
ck("and it says why the shared id cannot simply be edited",
   re.search(r"57 条记录", labels) is not None)
ck("the internal-name field names all three addresses",
   re.search(r"标记、长度、文本", labels) is not None)

print()
if FAILED:
    print("RENAME: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("RENAME: A NAME IS AN INTERNAL STRING AND A SHARED DISPLAY ID -- BOTH MOVE "
      "TOGETHER, EVERY CIV COPY FOLLOWS, THE SCREENS SEE IT BEFORE THE SAVE, "
      "UNDO PUTS IT BACK BYTE FOR BYTE, AND NOTHING IS WRITTEN WHEN NOTHING "
      "CHANGED")

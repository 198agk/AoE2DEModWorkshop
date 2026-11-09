# -*- coding: utf-8 -*-
"""Nail: 改哪一个数据文件 -- the list asks two questions and answers both.

Reported 2026-11-07: 「还有你这个应该给我选择数据模组的功能」.  The route to
list the files had existed since 2026-11-03, but its only caller was the
editor's own `<select>`, so the answer to "which of these twenty builds am I
editing?" lived on a different screen from the question.

What could be false, and why each part is checked here:

1. **Two questions, not one.**  "Which file is open" and "which file does the
   game read" are different: five enabled data mods compete and the highest
   `Priority` wins.  A chooser that marks only the open file lets a player edit
   a file that is never loaded -- 93 MB of writes that change nothing in game.
2. **A row is not a path.**  `C:/Users/.../mods/subscribed/582581_...` is not
   something a player can read; the label is.  The switch must send the PATH
   though -- sending the label is the classic version of this bug, and it fails
   silently on Windows because the label is a valid-looking relative string.
3. **A format we cannot parse is not a format we can edit.**  `supported` is
   `format is not None`; a `VER 7.8` file (format 43) IS editable (the parser
   knows GV_C21), a file with no `VER x.y` head is not.  Calling a legacy file
   uneditable is the same lie in reverse.
4. **Switching drops unsaved work.**  `set_dat` resets the session: the buffers
   and indexes all belong to the old file.  It reports `dropped` so the screen
   can say so -- a silent loss is worse than a slow switch.
5. **The same file is not a switch.**  Picking the file already open answers
   `changed: false`; rebuilding a toolkit to arrive where you started costs
   seconds and throws away every cache for nothing.
6. **The picker is filled at boot.**  This one was reported twice.  A block that
   only fills when its view is entered is a block that is empty the first time
   somebody looks at it.

Run:  python -X utf8 _probe\\test_dat_picker.py
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
HARNESS = os.path.join(ROOT, "_probe", "ui_page_harness.js")

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))
    if not ok:
        BAD.append((name, detail))


def _read(path):
    return io.open(path, encoding="utf-8").read()


def main():
    import aoe2mod.dat.parser as P
    import aoe2mod.ui.server as S

    app = S.App()
    tk = app.tk
    tk._ensure()
    page = _read(PAGE)
    server = _read(SERVER)
    harness = _read(HARNESS)

    # --- 1. the two routes sit in the two handlers ------------------------
    get_at = server.index("        def do_GET(self):")
    post_at = server.index("        def do_POST(self):")
    src_at = server.find('if path == "/api/dat-sources":')
    set_at = server.find('if path == "/api/dat-set":')
    check("the list route is a GET", get_at < src_at < post_at,
          "get@%d route@%s post@%d" % (get_at, src_at, post_at))
    check("the switch route is a POST", set_at > post_at, "route@%s" % set_at)
    check("the same chain has both, so neither can be inserted into the wrong one",
          src_at > 0 and set_at > 0)

    # --- 2. what the route answers ---------------------------------------
    got = app.dat_sources()
    check("the list answers", got.get("ok") is True, got.get("error"))
    items = got.get("sources") or []
    check("...with at least the install's own file", len(items) >= 1, len(items))
    wanted = {"path", "scope", "label", "format", "supported", "current", "note"}
    check("every row carries the keys the screen draws from",
          all(wanted <= set(it) for it in items),
          sorted(set(items[0]) & wanted) if items else "no rows")
    check("scope is one of game / mode / mod",
          all(it["scope"] in ("game", "mode", "mod") for it in items),
          sorted({it["scope"] for it in items}))
    check("the install's row is labelled, not pathed",
          all(it["label"] == "游戏本体" for it in items if it["scope"] == "game"),
          [it["label"] for it in items if it["scope"] == "game"])
    check("exactly one row is the file being edited",
          sum(1 for it in items if it["current"]) == 1,
          sum(1 for it in items if it["current"]))
    cur = [it for it in items if it["current"]]
    check("...and it is the toolkit's own file",
          bool(cur) and os.path.normcase(cur[0]["path"]) ==
          os.path.normcase(os.path.abspath(tk.dat_path)),
          (cur[0]["path"] if cur else None, tk.dat_path))
    check("every row is an absolute path",
          all(os.path.isabs(it["path"]) for it in items))
    check("format is either a number or null -- never a guess",
          all(it["format"] is None or isinstance(it["format"], int)
              for it in items),
          sorted({str(it["format"]) for it in items}))
    check("supported means WE can read it: `format is not None`",
          all(it["supported"] == (it["format"] is not None) for it in items),
          [(it["scope"], it["format"], it["supported"]) for it in items
           if it["supported"] != (it["format"] is not None)])
    # A legacy file is the case that reads wrong in both directions: the parser
    # knows VER 7.8, so it must be editable; a headless file must not be called
    # "格式 54".
    legacy = [it for it in items if it["format"] is not None and it["format"] != 54]
    check("a legacy format is offered as editable, because the parser knows it",
          all(it["supported"] for it in legacy),
          [(it["label"], it["format"]) for it in legacy])
    check("VER 7.8 really is a format this parser handles",
          P.gv_from_version_string("VER 7.8") == 43,
          P.gv_from_version_string("VER 7.8"))
    notes = {it["scope"]: it.get("note") or "" for it in items}
    check("each scope explains when the game reads it",
          bool(notes.get("game")) and bool(notes.get("mode")) and bool(notes.get("mod")),
          notes)
    check("the mod row warns that disabling the mod un-writes the edit",
          "不启用" in (notes.get("mod") or ""), notes.get("mod"))

    # --- 3. the same file is not a switch --------------------------------
    same = app.set_dat(got.get("current"))
    check("picking the file already open is not a switch",
          same.get("ok") is True and same.get("changed") is False,
          {k: same.get(k) for k in ("ok", "changed")})
    check("...and reports nothing dropped", same.get("dropped") == 0,
          same.get("dropped"))

    # --- 4. a path that is not a .dat is refused in one sentence ---------
    blank = app.set_dat("")
    check("an empty path says what it wants",
          blank.get("ok") is False and "没有说要改哪一份" in (blank.get("error") or ""),
          blank.get("error"))
    gone = app.set_dat(os.path.join(ROOT, "no_such_dir", "no_such.dat"))
    check("a missing file says where it looked",
          gone.get("ok") is False and "找不到这份文件" in (gone.get("error") or ""),
          gone.get("error"))

    # --- 5. the screen asks its question above the list -------------------
    view_at = page.index('id="view-mods"')
    list_at = page.index('id="dp-list"')
    mods_at = page.index('id="mods"')
    check("the picker lives on the mods screen",
          view_at < list_at, "view@%d picker@%d" % (view_at, list_at))
    check("...above the mod list, where the question is asked",
          list_at < mods_at, "picker@%d mods@%d" % (list_at, mods_at))
    check("it has a place to say which file wins",
          'id="dp-note"' in page)
    # Between the two calls the page writes a two-line comment explaining why
    # the picker is filled here; a regex that demanded "next line" reported the
    # boot call missing while it was three lines down.  Look for the order and a
    # short gap instead, and refuse if a `function` starts in between (that would
    # mean the call sits inside some other function, not in the boot path).
    _boot_at = page.index("renderMods(META.mods);")
    _dp_at = page.find("loadDatPicker();", _boot_at)
    _gap = page[_boot_at:_dp_at] if _dp_at > 0 else "function"
    # A COUNT OF CHARACTERS IS NOT A COUNT OF STATEMENTS.  The distance grew
    # past 400 when a second boot call was added between these two, and the
    # check called the picker missing.  What matters: no function opens in the
    # gap (that would put the call inside some other function), and only a
    # couple of statements run between them.
    _stmts = [ln.strip() for ln in _gap.splitlines()
              if ln.strip() and not ln.strip().startswith("//")]
    check("it is filled when the page boots, not when the view is entered",
          _dp_at > _boot_at and "function" not in _gap and len(_stmts) <= 4,
          "gap %d chars, %d statements at %s" % (len(_gap), len(_stmts), _dp_at))
    check("a redraw clears the old rows first",
          re.search(r"box\.textContent = \"\";\s*\n\s*box\.appendChild\(el\(\"div\", \"empty\"",
                    page) is not None)

    # --- 6. one row, four states, and the switch sends the path ----------
    check("the rows are sorted install, mode, mod",
          "const order = {game: 0, mode: 1, mod: 2};" in page)
    check("the file being edited is marked, not offered",
          'row.appendChild(el("span", "dpnow", "正在改"));' in page
          and 'el("button", "chip", "改这一份")' in page)
    check("the switch sends the path, not the label",
          "go.onclick = () => setDat(it.path);" in page)
    # The row used to carry a「游戏现在读的是它」badge.  Asked to remove it
    # (2026-11-07,「这个不需要，去掉吧」): two labels on fifteen rows is more
    # reading than the answer is worth, and the header already says it in a
    # sentence.  The pin flips to forbidding it, so a later edit cannot quietly
    # put the badge back and leave the header saying the same thing twice.
    check("the row no longer carries a「游戏现在读的是它」badge",
          "dpwin" not in page and "游戏现在读的是它" not in page.split("// Nothing else")[0],
          page.count("dpwin"))
    check("and the header still answers it instead",
          "优先级最高的是" in page
          and "游戏读的就是它" in page
          and "改别的份游戏看不到" in page)
    check("a file with no readable version says so instead of a number",
          '"格式读不出来"' in page)
    # Four states, and the second one is the one that used to print an empty
    # string: editing the winning file is not the same as "nothing to say".
    for state in ("game", "mod", "other", "none"):
        check("the header answers the %r case" % state,
              ('loads.reads === "%s"' % state) in page)
    check("switching redraws the picker, the editor and the card panel",
          "await loadDatPicker(true);" in page
          and 'if (typeof drawCardFile === "function") drawCardFile();' in page)

    # --- 7. the browser stub answers both routes ------------------------
    check("the stub lists four files, in an order the page must not keep",
          "const DATS = [" in harness
          and harness.index('label: "mod-b"') < harness.index('label: "游戏本体"'),
          "mod-b listed before the install")
    check("the stub's winner is NOT the file being edited",
          re.search(r'DATS\[2\]\.path.*?winner: \{ ?name: "mod-b"', harness, re.S)
          is not None,
          "otherwise a page that confuses the two questions passes")
    check("the stub flips which file is open when the switch lands",
          re.search(r'"/api/dat-set".*?d\.current = \(d\.path === body\.path\)',
                    harness, re.S) is not None)

    # --- 8. a real switch, and back -------------------------------------
    # Last, because it rebuilds the toolkit: everything above reads the file
    # that is open now, and everything after would read a different one.
    other = next((it for it in items if not it["current"]), None)
    if other is None:
        check("this machine has a second .dat to switch to", False, "only one file")
    else:
        went = app.set_dat(other["path"])
        check("switching to another file says it changed",
              went.get("ok") is True and went.get("changed") is True,
              {k: went.get(k) for k in ("ok", "changed", "error")})
        check("...reports how many unsaved edits it dropped",
              isinstance(went.get("dropped"), int), went.get("dropped"))
        check("...and the toolkit now reads that file",
              os.path.normcase(app.tk.dat_path) == os.path.normcase(other["path"]),
              app.tk.dat_path)
        check("...and meta agrees about which file is open",
              os.path.normcase(((went.get("meta") or {}).get("dat") or {}).get("path") or "")
              == os.path.normcase(other["path"]),
              ((went.get("meta") or {}).get("dat") or {}).get("path"))
        after = app.dat_sources()
        marked = [it["label"] for it in (after.get("sources") or []) if it["current"]]
        check("...and the list marks the new file, exactly one",
              len(marked) == 1 and marked[0] == other["label"], marked)
        back = app.set_dat(cur[0]["path"] if cur else None)
        check("switching back works the same way",
              back.get("ok") is True and back.get("changed") is True,
              back.get("error"))

    print()
    if BAD:
        for name, detail in BAD:
            print("FAILED: %s :: %s" % (name, detail))
        print("DATA PICKER: %d CHECK(S) FAILED" % len(BAD))
        return 1
    print("DATA PICKER: THE LIST IS A LIST OF FILES THE GAME COULD LOAD -- IT SAYS "
          "WHICH ONE IS OPEN, SAYS WHICH ONE WINS, REFUSES TO CALL AN UNREADABLE "
          "HEAD A FORMAT, SWITCHES THE SESSION BY PATH, AND DROPS NOTHING QUIETLY")
    return 0


sys.exit(main())

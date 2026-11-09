# -*- coding: utf-8 -*-
"""The local UI server: plain HTTP + JSON over the Toolkit, one screen.

Why not Electron / Tauri
------------------------
The project's constraint is a single entry point, plugins as folders, and no
requirement to squeeze everything into one .exe.  An HTTP server over the
existing `Toolkit` keeps the product's only state (the .dat, the mod folder, the
profile) exactly where it already lives, and the screen is a static folder --
replaceable, themeable, and inspectable without a build step.

What this server is NOT
-----------------------
It is not a general-purpose API.  It binds 127.0.0.1, it has no auth, and it
exposes the calls one screen needs.  Anything that needs a decision (which of
three archers, is this edit safe) is answered by the CLIENT asking the user, not
by the server guessing -- the refusals carry reasons precisely so the screen can
show them.

Design notes that are load-bearing
----------------------------------
* The Toolkit is expensive to build (parses 93 MB of .dat) and cheap to reuse,
  so it is built once, lazily, behind a lock.  Two concurrent first requests must
  not both parse.
* `plan()` is the preview.  The server never writes on a GET-like call, and
  `build()`/`install()` are separate, explicit POSTs -- a screen that previews
  on every keystroke cannot be allowed to emit mods.
* Errors are returned as `{"error": "..."} ` with HTTP 200 so the static client
  can render the message without special-casing fetch failures; a 500 would look
  like a network problem, which is exactly what it is not.
"""
import contextlib
import glob
import io
import json
import os
import re
import threading
import time
import traceback
import webbrowser
import zlib

from aoe2mod import api as A
from aoe2mod import appversion as AV
from aoe2mod.dat import fieldwrite as FW
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.dat import pseudopage as PP
from aoe2mod.dat import records as REC
from aoe2mod.dat import relocate as REL
from aoe2mod.game import civnames as CN
from aoe2mod.game import civtechtrees as CT
from aoe2mod.game import nametext as NTX
from aoe2mod.game import version as GV
from aoe2mod.mod import emitter as E
from aoe2mod.mod import strings as S
from aoe2mod.ui import compose as CP
from aoe2mod.ui import locale as LO
from aoe2mod.ui.loading import LOADING_PAGE
from aoe2mod.ui import nl
from aoe2mod import oplog as OPLOG
from aoe2mod.ui import recipes as RC

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

#: The wording of this screen, loaded once.  Read at import rather than per call
#: because every sentence here is chrome -- a heading, a button, a hint -- and
#: none of it changes while the process runs.  A plugin that wants different
#: wording drops a file and restarts, which is the same deal the schema makes.
_LOCALE = LO.load()


def _LOCALE_TEXT(key, values=None):
    """One screen string, substituted, with the key itself as the fallback."""
    text = _LOCALE.get(key)
    if text is None:
        return key
    return LO.fill(text, values)

#: Exception class names that must NOT be printed in front of a player's
#: sentence.  `_safe_plan` and `_guard` used to send "%s: %s" % (type(exc), exc),
#: so the screen literally read "IntentError: 「生命值」会变成 99999…" -- an English
#: class name glued to the front of a Chinese refusal.  The class name is for us;
#: the message is for the player.
_QUIET_ERRORS = ("AIError", "IntentError", "ModError", "ValueError", "RuntimeError",
                 "TypeError", "KeyError", "OSError", "FileNotFoundError",
                 "NotADirectoryError", "PermissionError", "UnsupportedVersionError",
                 "struct.error", "zlib.error",
                 # A bad query parameter is the product speaking to the person
                 # who typed the URL, not a library failing: "units='abc' 里有
                 # 一个不是编号" is the whole message, and prefixing it with
                 # "_BadId:" would read as a crash.
                 "_BadId")


def _sentence(exc):
    """The text a player should read for this exception.

    A message the product wrote for a player is passed through unchanged.  A
    message Python or a library wrote is prefixed with the class name, because
    that half is diagnostic and the player can quote it to a bug report -- but
    the product's own refusals must not carry one.
    """
    text = str(exc) or "没有说明"
    name = type(exc).__name__
    if name in _QUIET_ERRORS:
        return text
    return "%s: %s" % (name, text)


class App(object):
    """Everything the routes touch, with the Toolkit built once."""

    def __init__(self, game_root=None):
        self.game_root = game_root
        self._tk = None
        self._vocab = None
        # `{unit id: 中文名}` for the task table's picker rows.  Built on first
        # use and dropped by `set_dat`, because a mod renumbers units.
        self._task_name_cache = {}
        self._ailang = None
        # `{(path, mtime_ns, size): {(space, node): {age: votes}}}` -- the build
        # panel's `RequiredAge` vote, the only source that answers 「这个单位是
        # 哪个时代的」 for the command panel.  Kept per file version instead of
        # per session because `_panel_availability` rewrites those files: a
        # cache that outlived a write would filter the grid by an age the file
        # no longer holds.
        self._panel_age_cache = {}
        self._card_age_last = {}
        self._lock = threading.Lock()
        # Icon bytes and their per-(kind,id,size) answers.  See `icon()` for the
        # measurement: the DDS decode + PNG encode is 8.56 ms, and the unit list
        # asks for 400 of them.  Cleared by `reset_session()`?  No -- the icon
        # files live in the installed game and do not change when the session's
        # .dat buffer changes; the icon ID does not move, and a mod that swaps a
        # picture ships its own files (handled by `iconart`, not this cache).
        self._icon_png = {}
        self._icon_at = {}
        # The Title of the mod this session last wrote.  Reported 2026-11-09,
        # verbatim: 「那我要继续接着改同一份呢，总不能我每改动一次，就另存为
        # 一份吧」.  The folder name comes from the Title and the emitter
        # replaces that folder wholesale, so saving repeatedly is already
        # "keep editing the same mod" -- but only when the Title repeats, and
        # an empty name box used to derive a NEW Title from the first edit of
        # each batch ("村民 最大生命值" then "弓箭手 攻击力"), so every save made
        # another folder.  Remembering the last Title is what makes 保存 mean
        # update-in-place instead of accumulate.
        self._last_title = ""
        # WHICH BYTES THE CACHED INDEXES DESCRIBE.  Every index below is a table
        # of absolute offsets into `session_raw()`, and a structural edit or a
        # 放弃 REPLACES that buffer and moves every offset after the change.  A
        # scan takes ~10 s, so one can still be walking the OLD bytes when the
        # new ones arrive; if it then stores its result, the index describes a
        # file that no longer exists and the next decode reads a field out of
        # the middle of another record.  Measured 2026-11-05: the page hit
        # `struct.error: bad char in struct format` on a record whose 1,001
        # bytes were fine, right after a duplicate followed by 放弃.
        #
        # Bumping this on every change and having each builder check it before
        # it caches is cheaper than a lock around a 10 s walk: a stale result is
        # thrown away instead of blocking the edit that invalidated it.
        self._gen = 0
        # {string id: text} for rows this session had to ADD to a string table.
        #
        # Renaming a record for the player means pointing its `LanguageDLLName`
        # at a row nobody else uses.  The shipped rows are SHARED -- measured
        # 2026-11-06: string id 5079 is the name of 57 different records -- so
        # writing a new text into 5079 would rename fifty-six other things at
        # the same time.  A new id above the highest shipped one is the only
        # safe answer, and it has to survive until 保存 writes the table out.
        self._new_strings = {}
        # {mod relative path: bytes} for pictures this session is shipping.
        #
        # WRITTEN ONCE AT 保存, NOT WHEN THE PICTURE IS CHOSEN.  An icon is not
        # one number in the .dat: it is a texture file, a material row, a
        # texture row and a key in the icon table, and only the last of those
        # lives in the record.  `iconart.emit_many` builds all four from one
        # deep copy of the two shipped tables, so choosing five pictures costs
        # one merge rather than five complete rewrites of a 2.5 MB table
        # (measured 2026-11-06: 0.026 s for two against 0.022 s for one).
        #
        # NOT CLEARED BY 撤回: undoing the `IconID` write leaves the files in
        # the mod, and they are unreachable -- nothing in the table points at
        # them.  Dropping them would mean rebuilding the merge on every undo
        # step, and a stray texture nobody can see is a cheaper mistake than a
        # picture that disappears from a record that still names it.
        self._icons = {}
        # `{(building, button): [tech ids]}` for the command panel's cyclers,
        # and the generation it was built at.  Walking every technology to find
        # them costs 0.002 s, but the panel asks on every card draw, and a card
        # is redrawn on every box click.
        self._pseudo_map = {}
        self._pseudo_gen = -1
        # {kind: {slot, ...}} for the slots THIS session handed out.  The shipped
        # tables do not know about them yet -- they are only written at 保存 --
        # so `plan` would hand out the same first free number twice and the
        # second picture would collide with the first in the merge.
        # Measured 2026-11-06: choosing two unit pictures in one session both
        # planned slot 1000 and the second one silently replaced the first
        # material row, leaving the first record pointing at a picture that no
        # longer existed.
        self._icon_slots = {}
        self._icon_owner = {}
        # The pictures themselves, one entry per slot.  `self._icons` is DERIVED
        # from this list -- see `set_icon` for why it cannot be accumulated.
        self._icon_items = []

    def _gen_bump(self):
        """Declare every offset-based index stale.  See `self._gen`."""
        self._gen += 1
        return self._gen

    @property
    def tk(self):
        if self._tk is None:
            with self._lock:
                if self._tk is None:
                    self._tk = A.open_toolkit(game_root=self.game_root)
        return self._tk

    def vocab(self):
        if self._vocab is None:
            # The reader's vocabulary must be the vocabulary of the file being
            # edited: a mod that renames 村民 or adds 2,000 units has names the
            # shipped table does not carry, and without them those units cannot
            # be typed at all.  `tk.index()` is that per-file index (see its
            # docstring); it degrades to the shipped one when there is nothing
            # better to use.
            idx = self.tk.index()
            self._vocab = nl.Vocabulary(idx.units, idx.techs)
        return self._vocab

    def ailang_vocab(self):
        """The AI/XS language table, built from the payload alone.

        Deliberately does NOT touch ``self.tk``: that property opens the game
        install (`AoE2DE_s.exe` plus the DAT), and this table was mined from the
        executable and the shipped scripts ahead of time, so the language editor
        answers with the game closed.  Opening a toolkit here would make every
        request pay a DAT parse and would fail on a machine without the game --
        for a feature whose whole input is a JSON payload shipped with the tool.
        """
        if self._ailang is None:
            with self._lock:
                if self._ailang is None:
                    from aoe2mod.game import ailang as _ailang
                    self._ailang = _ailang.Vocab(_ailang.load())
        return self._ailang

    # ---- routes ---------------------------------------------------------
    def home(self):
        return self.meta()

    def meta(self):
        """Cheap facts a screen needs once: civs, intents, mods, versions."""
        tk = self.tk
        intents, _bindings = _load_schema()
        # The .dat being edited, spelled out.  Reported 2026-11-02: 「我改的是哪个
        # dat」 -- and it is a fair question, because the tool edits the file the
        # GAME will load, which lives in the Steam install, not in this repo.  A
        # player who has two installs (Steam + Microsoft Store) or a beta branch
        # selected has no way to tell from the screen, and a silent wrong-file
        # edit is the worst failure this tool can have.
        _dat = getattr(tk, "dat_path", "") or ""
        _raw = None
        try:
            _raw = self.session_raw()
        except Exception:
            _raw = None
        # WHICH ONE OF THE EIGHTEEN.  Reported 2026-11-07: 「我用这个面板的，是
        # 改动哪个的 dat 这个也不清楚」 -- asked while looking at the command
        # panel, which draws a building's card and says nothing about the file
        # behind it.  The rail names the file, but the rail is the far corner of
        # the screen; a player editing a card needs the answer where the edit is.
        #
        # `datsources.find` costs one `VER x.y` head per candidate (0.06 s for
        # 18 files here) and yields the SCOPE, which is the part that decides
        # whether the game reads the edit at all: a mod's `.dat` is loaded only
        # while that mod is enabled, and an enabled data mod outranks the
        # install's own file entirely.
        _src = None
        try:
            from aoe2mod.game import datsources as _DSR
            _src = _DSR.find(_DSR.candidates(self.game_root), _dat)
        except Exception:                              # noqa: BLE001
            _src = None
        _mods = _mods_brief(tk)
        # The game loads exactly ONE data mod: the enabled one with the highest
        # Priority.  With none enabled it loads the install's own file.  So
        # "am I editing the file that will be read" has an answer, and it is not
        # always yes -- measured here: 16 installed mods ship a `.dat`, 5 are
        # enabled, and the winner is `tbl one field` (Priority 6).
        _live = [m for m in _mods if m.get("ships_dat") and m.get("enabled")
                 and m.get("exists")]
        _live.sort(key=lambda r: -(r.get("priority") or 0))
        _top = _live[0] if _live else None
        _mine_mod = (_src or {}).get("mod") if _src else None
        if _top is None:
            _reads = "game" if (_src or {}).get("scope") == "game" else "none"
        else:
            # A file that belongs to the winning mod is the file read; anything
            # else (the install's, another mod's, a mode's) is written but not
            # loaded.  Compared by mod FOLDER name, which is what
            # `datsources._entry` records, not by title.
            _reads = "mod" if (_mine_mod and _mine_mod == _top.get("name")) else "other"
        return {
            "ok": True,
            # The TOOL's version, not the file's.  A player asking 「版本」 on a
            # page about the workshop means this number; `version` below is the
            # .dat's FileVersion ordinal, which only answers "which field layout
            # do I parse".
            "app_version": AV.VERSION,
            "version": tk.version,
            "civs": tk.civ_names,
            # Same 63 names, translated.  The .dat stores `British`; a screen a
            # Chinese player reads must not.  Parallel list rather than a dict so
            # the order stays the .dat's own civ index -- every other table in
            # this product is keyed by that index.
            "civs_zh": [_civ_zh_of(tk, c) for c in tk.civ_names],
            "dat": {
                "path": _dat,
                # The size ON DISK.  Reported 2026-11-03: 「你这个大小不对啊」 --
                # the rail used to print len(self.session_raw()), which is the
                # stream AFTER the game's compression is undone: 89.0 MB for a
                # file Explorer right-clicks at 11.4 MB (93,272,287 vs
                # 11,963,833 bytes on this install, ratio 7.8).  Both numbers
                # are true, so both are reported and the screen says which is
                # which; printing only the bigger one beside a file the player
                # can inspect reads as a bug.
                "bytes": _disk_bytes(_dat),
                "expanded_bytes": len(_raw) if _raw is not None else 0,
                # The .dat's internal FileVersion ordinal -- `GV_C32`, aliased
                # `GV_LatestDE2` in `aoe2mod/dat/parser.py`.  It says which field
                # layout to parse, NOT which game release this is; the screen
                # must never present it as a version a player could check.
                "format": tk.version,
                # Which file the check compares against, so 「我改的是哪个 dat」
                # has one answer on screen and in the docs.
                "from_game": bool(_dat),
                # `game` / `mode` / `mod` -- what this file IS, which is the
                # half of "which dat" a path cannot answer.  `None` when the
                # file is outside every folder the game reads (an exported copy
                # someone opened by hand).
                "scope": (_src or {}).get("scope"),
                "label": (_src or {}).get("label"),
                "mod": _mine_mod,
                "head": (_src or {}).get("head"),
                "supported": (_src or {}).get("supported"),
            },
            # Whether the game will actually READ the file being edited, and
            # which mod wins if it will not.  Three states, because collapsing
            # them is how a player learns to distrust the warning:
            #   "game"  -- no data mod is enabled, the install's file is read
            #   "mod"   -- the file being edited belongs to the winning mod
            #   "other" -- something else wins; this edit is written but unseen
            "dat_loads": {
                "reads": _reads,
                "competing": len(_live),
                "winner": _top and {"name": _top.get("name"),
                                    "title": _top.get("title"),
                                    "priority": _top.get("priority")},
            },
            # The build the player actually has, straight off AoE2DE_s.exe:
            # 「101.103.57257.0 188329 Retail Steam release_13_1_0 - 20261014.01」.
            # `None` when the exe is not on this machine (a data-only copy), and
            # the screen then omits the line rather than showing a placeholder.
            "game": _game_version(self.tk),
            "intents": [{"id": k,
                         "title": v.get("title") or v.get("title_en") or k,
                         # A worked example, declared in the schema next to the
                         # intent it belongs to.  The screen list used to say
                         # only "可以说出来" -- a capability with no way in, for
                         # someone who has never read the templates.  Declared
                         # rather than computed here because a computed one
                         # costs a full parse per intent (430 ms each, 6.4 s)
                         # on a route the window waits for; `_probe/
                         # test_intent_examples.py` re-reads every one of them
                         # against the live reader instead, which is where a
                         # sentence that stops parsing must be caught.
                         "example": v.get("example"),
                         "fields": list((v.get("fields") or {})),
                         "strategy": (v.get("compile") or {}).get("strategy"),
                         # Whether a SENTENCE can ever produce this intent.
                         # A plugin adds intents to the schema, and this screen
                         # lists everything in the schema under "能做的事" --
                         # but the sentence layer is hand-written, so a plugin
                         # intent is only reachable through the API.  Measured
                         # 2026-10-23: a plugin intent `unit.set_stat` appeared
                         # in this list while `把村民血量设成40` kept parsing to
                         # `unit.stat`.  Advertising a capability no sentence can
                         # reach is the same defect as a build that does less
                         # than it says, one screen earlier.
                         "by_sentence": nl.sentence_reachable(k, v)}
                        for k, v in intents["intents"].items()],
            "mods": _mods,
        }

    def forms(self, intent=None):
        """The sentence templates a form can be built from.

        Why this is a route rather than a key baked into `meta`: a plugin dropped
        in while the tool runs changes the table, and `meta` is fetched once at
        page load.  Measured 2026-10-25: a vocabulary cache keyed on a constant
        made a live plugin's words appear everywhere except the reader; the same
        file-backed table is read fresh here for the same reason.

        The important invariant is not in this function but in
        `_probe/test_compose_roundtrip.py`: every form listed here composes a
        sentence the reader accepts.  A form this route offers and the reader
        refuses would be the worst shape a screen can take -- the click works and
        the sentence underneath is one the tool cannot read.
        """
        table = CP.load()
        return {"ok": True, "forms": CP.forms(intent, table),
                "op_choices": table.get("op_choices") or []}

    def note_diag(self, values):
        """Remember the last viewport the page reported.

        Kept on the app rather than written anywhere: it is a measurement of
        one running window, and it must not survive as state a later run reads
        as its own.  Merged instead of replaced because the page sends `vw`
        first and `cols` a moment later.
        """
        with self._lock:
            merged = getattr(self, "_diag", {}) or {}
            merged.update({str(k): str(v) for k, v in (values or {}).items()})
            self._diag = merged

    def diag(self):
        """The numbers the page last reported, plus what the server knows.

        `scale` is the piece the page cannot see: `devicePixelRatio` tells the
        page how many device pixels a CSS pixel covers, but the shell needs to
        know whether the window it asked for was interpreted as logical or
        physical pixels -- that is the difference between a 1280 px window and
        an 850 CSS px layout.
        """
        got = dict(getattr(self, "_diag", {}) or {})
        got["page"] = "/"
        return got

    def recipes(self):
        """The sentences this player saved under names.

        A recipe stores sentences, never a built mod: a saved ``.dat`` would be a
        snapshot of data the game can update underneath it, while a saved sentence
        is rebuilt against whatever the game holds today.  The reader decides what
        each sentence means either way, so a recipe is exactly as correct as the
        reader on the day it runs -- and if the reader gets stricter, the recipe
        fails at parse time instead of quietly building something else.
        """
        return {"ok": True, "recipes": RC.rows(), "file": RC.path()}

    def save_recipe(self, name, sentences, note=""):
        try:
            row = RC.remember(name, sentences, note=note)
        except RC.RecipeError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "recipe": {"name": (name or "").strip(),
                                       "sentences": list(row["sentences"]),
                                       "count": len(row["sentences"]),
                                       "saved_at": row["saved_at"],
                                       "note": row["note"]}}

    def forget_recipe(self, name):
        return {"ok": True, "removed": RC.forget(name)}

    def search(self, q, kind="unit", limit=25):
        return {"ok": True, "hits": self.tk.search(q, kind=kind, limit=limit)}

    def browse(self, kind="unit", query="", limit=60, offset=0, order="id"):
        """A paged grid of things a player can pick by LOOKING at them.

        Typing a name only works if you already know the name -- and the game's
        Chinese names are not the ones people use ("弓箭手" is not any unit's
        name at all; "城堡" is a building AND part of a technology's name).  This
        route exists so a player can point at a picture instead.

        The rows say whether a picture exists at all: many of the game's units
        ship no icon id, so a grid that silently rendered holes would look
        broken.  `has_icon` lets the page draw a labelled cell instead.

        These numbers must be counted over the rows this route RETURNS (named
        entities only), never over every record in the .dat: the grid is what the
        player counts, and an earlier version quoted a count over all 2,693 unit
        records beside a grid that lists 1,651 of them.
        """
        return {"ok": True,
                "browse": self.tk.browse(kind=kind, query=query,
                                         limit=int(limit or 60),
                                         offset=int(offset or 0),
                                         order=order)}

    def describe(self, kind, entity_id):
        return {"ok": True, "entity": self.tk.describe(int(entity_id), kind=kind)}

    def icon(self, kind, entity_id, section=None, max_side=0):
        """The picture for one entity, as PNG bytes plus what it is.

        Measured 2026-11-02: `icon_for` costs 0.27 ms (it is a dict lookup once
        `_unit_facts` has run), and `ddstex.to_png` costs **8.56 ms** -- decode
        the DDS, resize, re-encode.  The unit list asks for 400 of these, so the
        last row was painted **3.6 seconds** after the first: measured in a real
        browser at loaded=1 (0 ms) / 38 (500 ms) / 203 (2 s) / 346 (6 s), and the
        screenshot that prompted 「有些图标不正常」 was taken inside that window.
        The rows were not broken; they had no picture yet.

        Two caches, because the two costs are different:
        * `_icon_png` keyed on (path, max_side) -- the bytes depend on nothing
          else, and 400 rows at one size is 400 entries of ~1.2 KB (measured
          215,614 B for 132 distinct icons).
        * `_icon_at` keyed on (kind, id, max_side) -- so a repeated id (a unit id
          is the same icon in 63 civilizations) skips the resolve too.

        The old docstring argued the browser's own cache was enough.  It is not:
        WebView2 keeps the bytes, but the FIRST paint still costs one process-
        bound encode per request, and that is the three seconds a player sees as
        "the icons are wrong".

        `section` is an override for the one thing the caller may know better
        than the rule does: nothing, today -- it exists so a test can prove the
        two tables draw different pictures, and so a future "show me the button"
        view does not need a new route.
        """
        from aoe2mod.game import ddstex as D
        side = int(max_side or 0)
        at_key = (kind, int(entity_id), side, section or "")
        hit = self._icon_at.get(at_key)
        if hit is not None:
            return hit
        got = self.tk.icon_for(kind, int(entity_id))
        if section and got.get("icon_id"):
            got = self.tk.icons.picture(section, got["icon_id"])
            got["witness"] = "the caller asked for the %s table" % (section,)
        if not got.get("ok"):
            out = {"ok": False, "error": got.get("why") or "no picture"}
            self._icon_at[at_key] = out
            return out
        png_key = (got.get("path"), side)
        body = self._icon_png.get(png_key)
        if body is None:
            body = D.to_png(got["path"], max_side=side)
            self._icon_png[png_key] = body
        out = {"ok": True, "png": body, "icon": {k: got.get(k) for k in
                                                 ("section", "icon_id", "file",
                                                  "witness", "material")}}
        self._icon_at[at_key] = out
        return out

    def icons(self, kind, ids, max_side=26):
        """Many icons in one answer: `ids` is a comma-separated string or list.

        WHY A BATCH ROUTE: 400 rows used to mean 400 HTTP round trips.  Even with
        the per-icon cache warm, each round trip pays request parse, JSON wrap and
        a socket hop; measured 2026-11-02 the browser reached 346 of 346 loaded
        only at the 6 s mark and the list looked half-drawn the whole time.  One
        request returns the whole list as a map, so the list paints in one go.

        The reply is `{ok, icons: {"<kind>:<id>": "data:image/png;base64,..."}}`.
        A record with no picture is ABSENT from the map rather than carrying an
        empty string: "there is nothing to draw" and "the picture is blank" must
        not look the same to the caller (the same rule `/api/icon` follows when
        it answers ok:false).
        """
        import base64
        if isinstance(ids, str):
            items = [x for x in ids.split(",") if x.strip()]
        else:
            items = list(ids or ())
        out = {}
        side = int(max_side or 26)
        for raw in items[:800]:
            try:
                eid = int(str(raw).strip())
            except (TypeError, ValueError):
                continue
            got = self.icon(kind, eid, max_side=side)
            if not got.get("ok"):
                continue
            out["%s:%d" % (kind, eid)] = ("data:image/png;base64,"
                                          + base64.b64encode(got["png"]).decode("ascii"))
        return {"ok": True, "icons": out, "size": side}

    def art(self, civ, mode=""):
        """The civ's tech-tree shield, as PNG bytes.

        Separate from `emblem()` on purpose: that one returns the 450x280 drawn
        banner the history screen uses, and the 104x104 shield is a different
        picture in a different folder.  The tech-tree header wants the shield.
        """
        from aoe2mod.game import civtechtrees as CT
        from aoe2mod.game import techtree_layout as TL
        stem = CT.civ_file_stem(civ) if civ else ""
        want = (mode or TL.MODE_BASE).strip().lower()
        named = ""
        for r in TL.civ_rows(self.tk.game_root, want):
            if r["stem"] == stem:
                named = r.get("emblem") or ""
                break
        path = TL.civ_art(self.tk.game_root, want, stem, named)
        if not path:
            return {"ok": False, "error": "没有「%s」的科技树图标" % (civ,)}
        with open(path, "rb") as fh:
            return {"ok": True, "png": fh.read()}

    def emblem(self, civ, mode=""):
        """A civilization's emblem, as the PNG the game already ships.

        The three spellings the product deals in (`British` from the .dat,
        `BRITONS` from the tree stems, `britons` on disk) all have to land on the
        same file, which is what `civnames.chinese` plus the tree-stem table are
        for -- the first version looked the aliased name up in icons.json and
        found nothing for the two civs whose file is spelled differently.
        """
        from aoe2mod.game import civtechtrees as CT
        from aoe2mod.game import techtree_layout as TL
        stem = CT.civ_file_stem(civ) if civ else ""
        want = (mode or TL.MODE_BASE).strip().lower()
        if want != TL.MODE_BASE:
            # The mode's emblems are its own PNGs under its own tree; the base
            # book has no `egyptian` at all (measured 2026-11-08: the base
            # civ_emblems folder holds 65 files and none of the mode's 17).
            folder = TL.emblems_dir(self.tk.game_root, want)
            # The mode's own `civilizations.json` states the file name, and it
            # does NOT follow the tree stem: GREEKS' emblem is `greek.png`, not
            # `greeks.png` (measured 2026-11-08).  So the name comes from the
            # mode's data, not from lowercasing the stem.
            named = ""
            for r in TL.civ_rows(self.tk.game_root, want):
                if r["stem"] == stem:
                    named = r.get("emblem") or ""
                    break
            for cand in (named, "%s.png" % stem.lower(), "%s.png" % str(civ or "").lower()):
                if not cand:
                    continue
                p = os.path.join(folder, cand)
                if os.path.isfile(p):
                    with open(p, "rb") as fh:
                        return {"ok": True, "png": fh.read()}
            return {"ok": False, "error": "没有「%s」的徽章" % (civ,)}
        path = self.tk.icons.emblem_path(stem.lower())
        if not path:
            # Some callers hold the icons.json stem already ("inCas"), and some
            # the localised name; try the plain lowercase form before giving up.
            path = self.tk.icons.emblem_path(str(civ or "").lower())
        if not path:
            return {"ok": False, "error": "没有「%s」的徽章" % (civ,)}
        # Emblems are already PNG on disk -- no decode step, unlike unit icons.
        with open(path, "rb") as fh:
            return {"ok": True, "png": fh.read()}

    def card(self, building=12, civ=""):
        """One building's command card, as the page's 命令面板 view draws it.

        WHY THIS ROUTE EXISTS: the native backend answers `/api/card` and this
        one did not -- measured 2026-10-28, the page's `loadCard()` got a 404 on
        port 7799 while the same URL returned 200 on the native port, so the
        command-panel view was an empty box plus one console error.  The data was
        never missing (`aoe2mod/dat/card.py` reads it); only the join from `.dat`
        rows to displayed names and civilisations' trees was missing.

        `civ` is optional and means "narrow to this civilisation's tree".  A civ
        name the tree layer does not know is REFUSED rather than silently
        producing the unfiltered card, because an unfiltered answer reads as "this
        civ can build everything" -- the opposite of what was asked.
        """
        from aoe2mod.game import cardview as CV
        from aoe2mod.game import civtechtrees as CT
        tk = self.tk
        tk._ensure()          # the civ list is only populated by the parse
        civs = tk._civs
        civ_name = str(civ or "").strip()
        if civ_name:
            # Accept both spellings the product deals in: the `.dat` name
            # (`British`) and the tree stem (`BRITONS`).  _civ_index bridges
            # them, and it raises with the reason when the name is unknown.
            civ_index = tk._civ_index(civ_name)
        else:
            civ_index = 1 if len(civs) > 1 else 0
        names = {}
        for uid, e in self._semantic().units.items():
            names[uid] = e.zh or e.en or e.display or ""
        icons = {k: v.get("icon_id") for k, v in tk._unit_facts().items()}
        slots, from_file = CV.card_slots(tk.game_root)
        trees = narrow_tree = None
        status = None
        if civ_name:
            trees = tk._trees()
            stem = CT.civ_file_stem(civs[civ_index].get("name"))
            narrow_tree = trees.get(stem)
            if narrow_tree is None:
                return {"ok": False,
                        "error": "没有这个文明：%s" % (civ_name,),
                        "known": sorted(trees.keys())}
            status = lambda t, node: CT.node_status(t, node)  # noqa: E731
        # 「你这个应该按时代来分」, 2026-11-07.  The one field that answers it is
        # `RequiredAge`, which lives in `futuravailableunits.json` and not in the
        # `.dat` -- and it is written PER (civilization, building, unit), so the
        # same unit can carry two ages.  The card therefore joins one vote per
        # node (`buildpanel.required_age_vote`) and hands it to `cardview`, which
        # copies it onto each row and each box.
        ages, age_ties = self._card_ages()
        # The panel is the first source, the tree fills the gaps: 18 of the
        # Barracks' 49 entries have no `RequiredAge` row at all, and the Goths'
        # 759/761 showed no era because of it.  Never the other way round -- the
        # panel is what the engine consults, and it disagrees with the tree on 7
        # of 2,794 rows.
        if narrow_tree is not None:
            filled = self._card_tree_ages(narrow_tree)
            if filled:
                ages = dict(ages)
                for _uid, _aid in filled.items():
                    ages.setdefault(_uid, _aid)
        # 「单位里好像也能放科技」 / 「很多都没读出来…比如哨站里也能放的」,
        # 2026-11-09.  Research buttons hang on the TECHNOLOGY record
        # (`research_locations[].location_id` names the host) and were never
        # read, so every research card looked empty: Outpost, University,
        # Blacksmith, Mill, Lumber Camp, Mining Camp, Wonder and Settlement all
        # reported `has_data False`.  The host may be a building OR a unit
        # (Trading Ship 17 carries the three `Trade x% wood` buttons), so the
        # caller passes the raw records and lets cardview match on the id.
        tech_records = tk._tech_records()
        tech_names = {}
        tech_idx = tk.index().techs
        for tid in range(len(tech_records)):
            e = tech_idx.get(tid)
            if e is not None:
                got = (e.zh or e.en or e.display or "").strip()
                if got:
                    tech_names[tid] = got
        tech_icons = {tid: r.get("icon_id") for tid, r in enumerate(tech_records)}
        tech_status = None
        if narrow_tree is not None:
            tech_status = lambda tid: CT.node_status(narrow_tree, tid,
                                                     use_types=("Tech",))
        # A research button's era comes from the tech tree's `Age ID`, which
        # every one of the 5,244 tech rows carries.  Without it a box holding
        # only research buttons has no age, and the era filter then hid the
        # whole University and Blacksmith the moment 城堡时代 was picked.
        tech_ages = {}
        if narrow_tree is not None:
            for _r in narrow_tree.get(CT.UNITS_KEY) or ():
                if _r.get("Use Type") != "Tech":
                    continue
                _aid = _r.get("Age ID")
                if _aid:
                    tech_ages.setdefault(int(_r.get("Node ID")), int(_aid))
        # With no civilization picked there is no tree, hence no `Age ID`, and a
        # research button then keeps `age: None` -- which the page treats as
        # UNKNOWN and always draws.  That is the honest answer for the
        # everything-in-the-.dat view: the same tech id can sit in a different
        # era for a different civilization.
        body = CV.card(civs, civ_index, int(building or 12), slots=slots,
                       icons=icons, names=names, narrow_tree=narrow_tree,
                       narrow_status=status, builders=self._builders(),
                       ages=ages,
                       techs=CV.techs_from_records(tech_records, int(building or 12)),
                       tech_icons=tech_icons, tech_names=tech_names,
                       tech_status=tech_status,
                       tech_ages=(tech_ages or None),
                       upgrades=self._card_upgrades())
        body["slots_from_file"] = from_file
        # Every building that has a card, with its name -- the page used to offer
        # two arrows and a label, so the only way to reach building 109 was to
        # press 「下一个建筑」 forty times.  「能不能把这个改成列表选择」,
        # 2026-11-07.  Names come from the same table the card's rows use, so a
        # building renamed by a mod shows its new name here too.
        # Four sources, not one -- see `cardview.host_ids`.  The training
        # entries alone gave 18 hosts for the British and made the other 30
        # cards unreachable, including every research-only one.
        panel_ids = ()
        try:
            from aoe2mod.game import buildpanel as BP
            panels = BP.load_all(tk.game_root)
            # `load_all` returns `{civ name: {"text","obj","path",...}}` -- the
            # JSON itself is under "obj", so passing the record to
            # `BP.buildings` would read a key that is not there and answer 0 for
            # every civilization (measured 2026-11-09: 0 buildings for Britons
            # until this line was fixed).
            key = BP.civ_key_for(panels, civs[civ_index].get("name"))
            obj = (panels.get(key) or {}).get("obj") if key else None
            panel_ids = [int(b.get("ID")) for b in
                         (BP.buildings(obj, key) or ())
                         if b.get("ID") is not None]
        except Exception:
            panel_ids = ()
        hosts = CV.host_ids(civs, civ_index, trees=narrow_tree,
                            records=tech_records, panel_ids=panel_ids)
        # `name_string_id` answers a STRING TABLE id, not a name, so it is
        # resolved here -- the tree's `Name` field is stale on 44 rows (all
        # Chronicles) and the string table is right in all 44 disagreements.
        strings_all = self._strings("")
        body["building_ids"] = [h["id"] for h in hosts]
        body["buildings"] = [
            {"id": h["id"],
             "kind": h["kind"],
             # A research-only host has no training name in some mods' tables,
             # so it falls back to the tech-tree node name rather than "建筑 N".
             "name": (names.get(h["id"])
                      or (strings_all.get(
                          CT.name_string_id(narrow_tree, h["id"],
                                            use_types=("Building",)) or -1)
                          or "").strip()
                      or ("建筑 " + str(h["id"])))}
            for h in hosts]
        body["engine_first"] = CV.ENGINE_FIRST
        body["engine_last"] = CV.ENGINE_LAST
        body["dat_slots"] = None
        # How many nodes the vote disagreed on, so the page can say「有 14 个
        # 单位的时代在各国之间不一致」instead of presenting one number as fact.
        body["age_sources"] = self._card_age_sources(age_ties)
        if civ_name:
            body["civ"] = civs[civ_index].get("name")
            body["civ_stem"] = CT.civ_file_stem(civs[civ_index].get("name"))
        return body

    def _card_ages(self):
        """``({unit id: age}, {unit id: votes})`` from the build-panel files.

        Read from `futuravailableunits.json` (and the paphos file) rather than
        from the tech trees, because that is the file the GAME reads.

        Measured 2026-11-07, civilization against its OWN tree: 2,794 unit rows
        agree, 7 disagree, 1 has no age on one side.  Where they disagree the
        panel wins -- the Burgundians' Cavalier is `RequiredAge` 4 in the panel
        and `Age ID` 3 in their tree, and the panel is what the engine consults.

        The join is still a vote, because `RequiredAge` is written per
        (civilization, building, node): 320 unit nodes carry an age, 14 of them
        carry two (a line one nation starts earlier), and exactly one is a
        genuine 4-vs-4 tie (`Settlement`, 2552).  Averages are not used.

        Cached per file mtime, not per session: an availability edit rewrites
        `RequiredAge`, and a cache that outlived the file would filter the grid
        by an age the file no longer holds.
        """
        from aoe2mod.game import buildpanel as BP
        votes_all = {}
        ties = {}
        for path in BP.panel_paths(self.tk.game_root):
            if path is None:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            key = (path, st.st_mtime_ns, st.st_size)
            got = self._panel_age_cache.get(key)
            if got is None:
                try:
                    _text, obj = BP.load_panel(path)
                    got = BP.required_age_vote(obj, BP.UNITS_KEY)
                except (OSError, ValueError):
                    got = {}
                self._panel_age_cache[key] = got
            for (space, node), votes in got.items():
                if space != BP.UNITS_KEY:
                    continue
                merged = votes_all.setdefault(node, {})
                for a, n in votes.items():
                    merged[a] = merged.get(a, 0) + n
        ages = {}
        for node, votes in votes_all.items():
            age, tie = BP.age_of(votes)
            if age is not None:
                ages[node] = age
            if tie:
                ties[node] = dict(votes)
        self._card_age_last = ties
        return ages, ties

    def _card_upgrades(self):
        """``{unit id: [{tech, tech_name, to}, ...]}`` -- what replaces what.

        A command-panel box is ONE button whose picture changes as you research,
        not a row of alternatives: box 1 of the Barracks holds 74/75/77/473/567
        because five technologies swap the unit in place.  Reported 2026-11-09:
        「确实是要通过研究科技才会把升级后的单位放同一个格子来覆盖前面的」.  The
        panel could say "5 units" and nothing about why they share a byte.

        THE RECORD IS THE EFFECT, not the panel: command type 3 (升级单位) carries
        the pair in its first two slots -- ``raw = [3, from, to, -1, 0.0]``.
        Measured 2026-11-09 on the shipped file: 424 such commands, 0.380 s to
        walk every technology's effect list, so this is cached per generation
        rather than per request.

        `target` / `value` are None on these rows -- `compiler.effect_rows`
        refuses to name a number for a command that has no attribute slot (its
        `reason_code` is `no_attribute_slot`), so the two unit ids are read from
        `raw`.  Reading `target` here would silently produce an empty map that
        looks like "this file has no upgrades".
        """
        from aoe2mod.intent import compiler as C
        tk = self.tk
        tk._ensure()
        gen = self._gen
        cache = getattr(tk, "_unit_upgrades", None)
        if cache is not None and getattr(tk, "_unit_upgrades_gen", None) == gen:
            return cache
        recs = tk._effect_records()
        techs = tk._tech_records()
        ix = self._semantic()
        out = {}
        for ti, t in enumerate(techs):
            eid = t.get("effect_id")
            if eid is None or not (0 <= eid < len(recs)):
                continue
            hit = [c for c in (recs[eid].get("commands") or ())
                   if c.get("type") == 3]
            if not hit:
                continue
            te = ix.techs.get(ti)
            tname = ((te.zh or te.en) if te is not None else "") \
                or NTX.readable(t.get("name")) or ""
            for c in hit:
                a, b = c.get("a"), c.get("b")
                if a is None or b is None or a < 0 or b < 0:
                    continue
                out.setdefault(int(a), []).append(
                    {"tech": ti, "tech_name": tname, "to": int(b)})
        tk._unit_upgrades = out
        tk._unit_upgrades_gen = gen
        return out

    def _card_tree_ages(self, narrow_tree):
        """``{unit id: age}`` from one civilization's tree -- the FALLBACK.

        `RequiredAge` in `futuravailableunits.json` is the file the engine reads
        and it wins where it has a row, but it does not have a row for every
        unit: measured 2026-11-09, 18 of the Barracks' 49 entries carry no
        `RequiredAge` at all, including the Goths' 759 近卫军 / 761 精锐近卫军,
        which is exactly why that box showed no era while the trees put them in
        城堡时代 and 帝王时代.

        The tree is the second source, not the first: it disagrees with the
        panel on 7 of 2,794 rows (the Burgundians' Cavalier is 4 in the panel and
        3 in their tree) and the panel is what the game consults.  So this only
        fills gaps, it never overrides.
        """
        if narrow_tree is None:
            return {}
        from aoe2mod.game import civtechtrees as CT
        out = {}
        for r in (narrow_tree.get(CT.UNITS_KEY) or ()):
            if r.get("Use Type") not in CT.UNIT_USE_TYPES:
                continue
            nid, aid = r.get("Node ID"), r.get("Age ID")
            if nid is None or aid is None:
                continue
            try:
                out[int(nid)] = int(aid)
            except (TypeError, ValueError):
                continue
        return out

    def _card_age_sources(self, ties):
        """The part of the vote a screen may show: how many, and one example."""
        if not ties:
            return {"ties": 0, "sample": []}
        sample = sorted(ties.items())[:4]
        return {"ties": len(ties),
                "sample": [{"unit": n, "votes": v} for n, v in sample]}

    def _builders(self):
        """``{unit id: [civ stem, ...]}`` -- who can ever build each unit.

        Thin forward to :meth:`Toolkit._builders` because the command panel needs
        it on every card and the cache must be one table, not one per request.
        """
        return self.tk._builders()

    def _semantic(self):
        # NOT the process-wide `semantic.index()`: that one is built from the
        # names shipped with this product (the game's own .dat) and never
        # changes, so a mod's units stayed invisible however often the player
        # switched files -- 「选择指定的数据文件没起作用」, reported 2026-11-03.
        return self.tk.index()

    def card_move(self, unit, box, building=None, civ=None, dry=True,
                  title=None):
        """Move one unit to another box on a building's card.

        ONE BYTE in the engine: the `button_id` inside that unit's
        `train_locations` entry, and `aoe2mod/dat/card.py` already knows where it
        is.  What this method adds is the same three refusals the native build
        makes, because each of them is a way to lose an edit while reporting
        success:

          * a unit with no entry for that building is refused -- inventing one
            changes the record's LENGTH, which is `unit.create`'s job;
          * a target box at or past the game's grid is refused with the number
            the layout file holds;
          * whatever already sat in the target box is SWAPPED into the vacated
            one, never overwritten.
        """
        import struct
        from aoe2mod.dat import card as CARD
        tk = self.tk
        tk._ensure()
        civs = tk._civs
        gv = tk._parsed[3]
        civs_start = tk._parsed[2]
        civ_name = str(civ or "").strip()
        civ_index = tk._civ_index(civ_name) if civ_name else (
            1 if len(civs) > 1 else 0)
        builder = None if building in (None, "", 0) else int(building)
        if builder is None:
            # The sentence may omit the building ("把民兵放在第5格"), and that
            # means "move it within its own card" -- so read the card the unit is
            # already on rather than inventing one.
            for bid in self._buildings_with_cards(civs, civ_index):
                if any(r["unit"] == int(unit)
                       for r in CARD.card(civs, civ_index, bid)):
                    builder = bid
                    break
            if builder is None:
                return {"ok": False,
                        "error": "第 %s 号单位不在任何建筑的训练表里，所以它没有格子可挪"
                                 % (unit,)}
        slots, from_file = __import__(
            "aoe2mod.game.cardview", fromlist=["card_slots"]).card_slots(
                tk.game_root)
        if not (CARD.ENGINE_FIRST <= int(box) <= CARD.ENGINE_LAST):
            return {"ok": False,
                    "error": "格子号 %s 不能写：命令面板一页第 %d..%d 格、"
                             "一共 %d 页，所以最大能写到第 %d 格。"
                             "第 0 格在记录里存在（村民采集、城门形态），游戏从不画；"
                             "第 %d 格以后引擎读得到但永远不画。"
                             % (box, CARD.ENGINE_FIRST, CARD.PAGE_BOXES,
                                CARD.PAGE_COUNT, CARD.ENGINE_LAST,
                                CARD.ENGINE_LAST)}
        buf = self.session_raw(tk)
        try:
            writes, got = CARD.plan_move(buf, gv, civs_start, civ_index,
                                         int(unit), builder, int(box), civs=civs)
        except Exception as exc:                            # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        out = {"ok": True, "building": builder, "unit": int(unit),
               "box": int(box), "slots": slots, "slots_from_file": from_file,
               "moved": [{"unit": u, "from": f, "to": t}
                         for (u, f, t) in got.get("moved") or []],
               "swapped": [{"unit": u, "from": f, "to": t}
                           for (u, f, t) in got.get("swapped") or []],
               # A move that rearranged nothing is still one slot changed, but
               # reporting 0 would read as "nothing will happen" for a sentence
               # that does something.
               "edit_count": max(1, len(got.get("moved") or [])),
               "bytes_changed": len(writes),
               "changes_dat": True}
        if dry:
            out["dry"] = True
            return out
        # INTO THE SESSION, not into a new folder.  A card drag is one byte and
        # the offsets cannot move (the box byte is fixed width), so this is the
        # cheapest kind of edit there is -- and it belongs in the same buffer as
        # every other edit, or 撤回 cannot take it back and 保存 cannot ship it.
        # Measured 2026-11-07: the old branch built `_out/dev7811/命令面板 12`,
        # a folder the player never asked for and would never enable.
        disp = tk._unit_lines.get(int(unit)) if getattr(
            tk, "_unit_lines", None) else None
        label = "把第 %s 号单位挪到第 %s 格" % (unit, box)
        if writes:
            # ONE NOTE PER BYTE, NOT ONE NOTE FOR THE BATCH.  A swap writes TWO
            # entries: the unit already in the target box moves into the vacated
            # one, and the dragged unit moves into the target.  `plan_move` lists
            # them in that order, so the first write belongs to the OTHER unit.
            # Sharing one note across the batch patched the second unit's
            # `train_locations` entry with the value decoded from the FIRST
            # unit's byte: measured 2026-11-09, dropping 75 onto box 7 (which
            # held 74) wrote both bytes correctly, reported 「把第 75 号单位挪到
            # 第 7 格」, and the grid redrew unchanged -- because 75 was patched
            # back to box 1 and 74's entry still said box 7.  The .dat was right
            # and the page was wrong, which is the worst way to be wrong.
            self._hist_begin()
            for w in writes:
                wid = int(w.get("unit") or unit)
                if wid == int(unit):
                    wlabel = label
                else:
                    wlabel = ("把第 %s 号单位换到第 %s 格"
                              % (wid, w.get("after")))
                wnote = {"unit": wid, "civ": civ_name or None,
                         "field": "button", "op": "card",
                         "card_field": "button_id", "label": wlabel,
                         "was": w.get("before"), "now": int(w.get("after")),
                         "unit_name": disp if wid == int(unit) else None,
                         "building": builder, "card": builder}
                self._session_edit(w["off"], struct.pack("<B", w["after"]),
                                   note=wnote, hold=True)
            self._hist_commit()
            self._stamp_write(out)
            out["label"] = label
        return out

    def _buildings_with_cards(self, civs, civ_index):
        from aoe2mod.game import cardview as CV
        return CV.building_ids_from_rows(civs, civ_index)

    # --- putting a unit on a card, taking it off, changing its train time ---
    # Dragging could only ever move a unit BETWEEN boxes it already occupied,
    # because the box is one byte inside an entry that exists.  Everything a
    # player actually asks for -- "让民兵也能从兵营出来", "把长矛兵从城堡上拿掉",
    # "让这个话题快一点" -- changes the RECORD instead, and that is why the card
    # panel could be read but not used (reported 2026-11-07: 「还有这个也完全
    # 没用」).
    def _card_ctx(self, civ):
        """`(tk, civs, gv, civs_start, civ_index, civ_name)` for a card edit."""
        tk = self.tk
        tk._ensure()
        civs = tk._civs
        civ_name = str(civ or "").strip()
        civ_index = tk._civ_index(civ_name) if civ_name else (
            1 if len(civs) > 1 else 0)
        return tk, civs, tk._parsed[3], tk._parsed[2], civ_index, civ_name

    @staticmethod
    def _train_bytes():
        from aoe2mod.dat import newunit as NU
        return NU.TRAIN_ENTRY_BYTES

    def _card_slots(self):
        from aoe2mod.game import cardview as CV
        return CV.card_slots(self.tk.game_root)

    def _card_splice(self, buf, steps, expect):
        """Apply a card splice to the live session buffer and prove the length.

        `expect` is the net byte change the plan promised: +9 to put an entry on
        a card, -9 to take it off.  Checking it looks paranoid until the first
        version of this shipped: `apply_steps(..., inplace=True)` was handed a
        COPY of the buffer, the copy was discarded, and the model was relocated as
        if the bytes had landed.  Everything downstream agreed with itself and the
        file was broken.

        On failure the bytes are put back, so a refusal cannot leave half a
        splice behind.
        """
        from aoe2mod.dat import records as REC
        before_len = len(buf)
        keep = bytes(buf) if len(buf) < (1 << 31) else None
        writes = []
        try:
            work, writes = REC.apply_steps(buf, steps, inplace=True)
            if work is not buf:
                # `inplace=True` means "mutate what I gave you"; a returned
                # buffer means it did not, and callers that ignore it lose the
                # edit.
                buf[:] = work
            grew = len(buf) - before_len
            if grew != expect:
                raise ValueError(
                    "这次改动应该让文件长 %+d 字节，实际是 %+d" % (expect, grew))
        except Exception:
            if keep is not None:
                buf[:] = keep
            raise
        return writes

    def card_put(self, unit, building, box=None, seconds=None, civ=None,
                 dry=True, title=None):
        """Give a building a train button for a unit it does not produce yet.

        Nine bytes spliced into the unit's record plus a count, so this is a
        STRUCTURAL edit: every offset after it moves and the model is carried
        across by `_relocate`, the same road `record_add` takes.
        """
        import struct
        import contextlib
        import io
        from aoe2mod.dat import card as CARD
        tk, civs, gv, civs_start, civ_index, civ_name = self._card_ctx(civ)
        try:
            builder = int(building)
            uid = int(unit)
        except (TypeError, ValueError):
            return {"ok": False, "error": "单位编号和建筑编号都要是整数"}
        slots, from_file = self._card_slots()
        button = 0 if box in (None, "") else int(box)
        # Not `slots`: that is how many boxes ONE screen holds (15), while the
        # engine honours ids up to 30 across two screens. Using the screen size
        # as the write limit is how the second page stayed un-writable after the
        # grid learned to draw it.
        if not (CARD.ENGINE_FIRST <= button <= CARD.ENGINE_LAST):
            return {"ok": False,
                    "error": "格子号 %s 不能写：命令面板一页第 %d..%d 格、"
                             "一共 %d 页，所以最大能写到第 %d 格。"
                             "第 0 格在记录里存在（村民采集、城门形态），游戏从不画；"
                             "第 %d 格以后引擎读得到但永远不画。"
                             % (box, CARD.ENGINE_FIRST, CARD.PAGE_BOXES,
                                CARD.PAGE_COUNT, CARD.ENGINE_LAST,
                                CARD.ENGINE_LAST)}
        buf = self.session_raw(tk)
        try:
            steps, info = CARD.plan_put_on_card(
                buf, gv, civs_start, civ_index, uid, builder, button,
                train_time=(int(seconds) if seconds not in (None, "") else 0),
                civs=civs)
        except CARD.CardError as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, ValueError):
            return {"ok": False, "error": "训练时间要填整数秒"}
        out = {"ok": True, "kind": "card-put", "unit": uid, "building": builder,
               "box": button, "seconds": info["train_time"], "info": info,
               "slots": slots, "slots_from_file": from_file,
               "label": "把第 %s 号单位加进第 %s 号建筑的第 %s 格"
                        % (uid, builder, button)}
        if dry:
            out["dry"] = True
            return out
        # The LIVE buffer, and the length is checked afterwards.  Passing a copy
        # here is how the first version lost the nine bytes while the history and
        # the model both acted as if they had landed -- see this module's
        # `_card_grew`.
        writes = self._card_splice(buf, steps, expect=self._train_bytes())
        note = {"unit": uid, "civ": civ_name or None, "field": "card_put",
                "op": "card-put", "label": out["label"], "was": None,
                "now": button, "building": builder,
                "create": "card.entry"}
        for w in writes:
            w["struct"] = True
            w["note"] = dict(note)
        self._hist_push(writes)
        self._sess_dirty = True
        self._sess_struct = True
        self._restructure(writes)
        self._stamp_write(out)
        out["bytes"] = len(self._sess)
        out["undo_label"] = note["label"]
        return out

    def card_take(self, unit, building, civ=None, dry=True, title=None):
        """Take a unit off one building's card, leaving its other cards alone."""
        from aoe2mod.dat import card as CARD
        tk, civs, gv, civs_start, civ_index, civ_name = self._card_ctx(civ)
        try:
            builder = int(building)
            uid = int(unit)
        except (TypeError, ValueError):
            return {"ok": False, "error": "单位编号和建筑编号都要是整数"}
        buf = self.session_raw(tk)
        try:
            steps, info = CARD.plan_take_off_card(
                buf, gv, civs_start, civ_index, uid, builder, civs=civs)
        except CARD.CardError as exc:
            return {"ok": False, "error": str(exc)}
        out = {"ok": True, "kind": "card-take", "unit": uid, "building": builder,
               "box": info.get("button"), "info": info,
               "label": "把第 %s 号单位从第 %s 号建筑的卡上拿掉"
                        % (uid, builder)}
        if dry:
            out["dry"] = True
            return out
        writes = self._card_splice(buf, steps, expect=-self._train_bytes())
        note = {"unit": uid, "civ": civ_name or None, "field": "card_take",
                "op": "card-take", "label": out["label"], "was": None,
                "now": None, "building": builder, "create": None}
        for w in writes:
            w["struct"] = True
            w["note"] = dict(note)
        self._hist_push(writes)
        self._sess_dirty = True
        self._sess_struct = True
        self._restructure(writes)
        self._stamp_write(out)
        out["bytes"] = len(self._sess)
        out["undo_label"] = note["label"]
        return out

    def card_time(self, unit, building, seconds, civ=None, dry=True,
                  title=None):
        """How many seconds this unit takes to train, on this building's card.

        EQUAL WIDTH, one i16, so this is a field write: the offsets cannot move,
        `_session_edit` carries it, and the model is patched in place.
        """
        import struct
        from aoe2mod.dat import card as CARD
        tk, civs, gv, civs_start, civ_index, civ_name = self._card_ctx(civ)
        try:
            builder = int(building)
            uid = int(unit)
            secs = int(seconds)
        except (TypeError, ValueError):
            return {"ok": False, "error": "单位编号、建筑编号、秒数都要是整数"}
        buf = self.session_raw(tk)
        try:
            got = CARD.entry_at(buf, gv, civs_start, civ_index, uid, builder,
                                civs=civs)
        except CARD.CardError as exc:
            return {"ok": False, "error": str(exc)}
        if not (-32768 <= secs <= 32767):
            return {"ok": False, "error": "训练时间 %r 秒写不进 i16" % (seconds,)}
        out = {"ok": True, "kind": "card-time", "unit": uid, "building": builder,
               "box": got.get("button"), "before": got.get("train_time"),
               "after": secs, "offset": got["off_train_time"],
               "label": "把第 %s 号单位的建造时间改成 %s 秒" % (uid, secs)}
        if dry:
            out["dry"] = True
            out["bytes_changed"] = 2 if got.get("train_time") != secs else 0
            return out
        note = {"unit": uid, "civ": civ_name or None, "field": "train_time",
                "op": "card", "card_field": "train_time",
                "label": out["label"], "was": got.get("train_time"),
                "now": secs, "building": builder}
        self._session_edit(got["off_train_time"], struct.pack("<h", secs),
                           note=note)
        self._stamp_write(out)
        out["undo_label"] = note["label"]
        return out

    # ---- pseudo pages -----------------------------------------------------
    # A box in the command panel is a `button_id` 1..30, and the engine draws
    # EVERY technology whose `ResearchLocations` names that pair, one at a time.
    # So a box can cycle through an unlimited number of groups of units by
    # carrying a chain of repeatable, free technologies that turn one group's
    # train location off and the next one's on.  `aoe2mod/dat/pseudopage.py`
    # holds the mechanism and its hazards; this is the interface to it.
    #
    # 30 boxes per building is a hard ceiling (15 per screen, 2 screens, no pager
    # widget in `commandpanel.json`), which is why "more room" means "another
    # box" or "this box cycles" and never "a third screen".
    def _pseudo_cycles(self):
        """``{(building, button): [tech ids]}`` for the whole file, cached."""
        tk = self.tk
        gen = self._gen
        if self._pseudo_gen != gen:
            effects = tk._effect_records()
            techs = tk._tech_records()
            self._pseudo_map = PP.read_cycles(effects, techs)
            self._pseudo_gen = gen
        return self._pseudo_map

    def pseudo_pages(self, building=None, box=None, civ="", all_boxes=False):
        """Which boxes cycle, and what each page of one of them shows.

        Two questions in one route because they are the same walk: the map over
        every box costs 0.002 s and answering them separately would walk the
        technology list twice for one screen.
        """
        tk = self.tk
        tk._ensure()
        effects = tk._effect_records()
        techs = tk._tech_records()
        cycles = self._pseudo_cycles()
        out = {"ok": True, "kind": "pseudo-pages",
               "boxes": [{"building": b, "button": n, "pages": len(ids)}
                         for (b, n), ids in sorted(cycles.items())],
               "count": len(cycles)}
        if all_boxes:
            return out
        try:
            bld = int(building) if building not in (None, "") else 0
        except (TypeError, ValueError):
            return {"ok": False, "error": "建筑编号要是个整数"}
        if not bld:
            return out
        btn = None
        if box not in (None, ""):
            try:
                btn = int(box)
            except (TypeError, ValueError):
                return {"ok": False, "error": "格子号要是个整数"}
        if btn is None:
            # Every box of this building that cycles.
            rows = []
            for (b, n), ids in sorted(cycles.items()):
                if b != bld:
                    continue
                rows.append({"box": n, "pages": len(ids),
                             "page_list": PP.read_group(effects, techs, b, n)})
            out.update({"building": bld, "boxes_here": rows})
            return out
        group = PP.read_group(effects, techs, bld, btn)
        out.update({"building": bld, "box": btn, "pages": len(group),
                    "page_list": group,
                    "suggest_hide": PP.default_hide(group)})
        return out

    def add_pseudo_page(self, building, box, name=None, on=(), hide=None,
                        civ="", seconds=0, donor=None, dry=True, title=None):
        """Append one page to a box.  Three appends, one pointer, one undo step.

        Refuses the cases where the result would be a button that does something
        other than what was asked:
        * no units to show -- a page that turns nothing on is a page that turns
          the box blank;
        * units both shown and hidden -- the effect applies in order, so the
          answer would depend on where in the record each unit appeared;
        * a box outside 1..30 -- the engine reads it and never draws it;
        * the same units as the box already shows -- the press would look like
          nothing happened.

        `donor` defaults to the box's last existing page (which keeps the
        technology's era gate and other terms close to its neighbours) and falls
        back to the first technology in the file for a box that has no pages
        yet.  The clone's box, effect pointer, time and costs are rewritten
        either way, so a stranger donor still lands in the asked-for box.
        """
        tk = self.tk
        tk._ensure()
        from aoe2mod.dat import card as CARD
        try:
            bld = int(building)
            btn = int(box)
        except (TypeError, ValueError):
            return {"ok": False, "error": "建筑编号和格子号都要是整数"}
        if not (CARD.ENGINE_FIRST <= btn <= CARD.ENGINE_LAST):
            return {"ok": False,
                    "error": "格子号 %d 不能写：命令面板一页第 %d..%d 格、"
                             "一共 %d 页，所以最大能写到第 %d 格。"
                             % (btn, CARD.ENGINE_FIRST, CARD.PAGE_BOXES,
                                CARD.PAGE_COUNT, CARD.ENGINE_LAST)}
        try:
            secs = int(seconds or 0)
        except (TypeError, ValueError):
            return {"ok": False, "error": "研究时间要填整数秒"}
        if not (0 <= secs <= 32767):
            return {"ok": False, "error": "研究时间 %r 秒写不进 i16" % (seconds,)}
        on_ids = [int(u) for u in (on or ()) if str(u).strip() != ""]
        if not on_ids:
            return {"ok": False,
                    "error": "这一页要显示哪些单位？一个都没选的话，"
                             "翻过去这个格子就是空的"}
        effects = tk._effect_records()
        techs = tk._tech_records()
        group = PP.read_group(effects, techs, bld, btn)
        if hide:
            hide_ids = [int(u) for u in hide]
        else:
            # Computed, not asked for: drop this page's own units.  A cycle is
            # exactly "page N shows what page 1 showed", so the union of the
            # existing pages -- the right list for every OTHER unit -- contains
            # the units this page is about to turn on, and hiding those would
            # turn the page blank.
            hide_ids = [u for u in PP.default_hide(group) if u not in set(on_ids)]
        overlap = sorted(set(on_ids) & set(hide_ids))
        if overlap:
            # Only reachable when the caller passed `hide` themselves, and then
            # it is a real contradiction rather than an artefact of the default.
            return {"ok": False,
                    "error": "第 %s 号单位既要在这一页出现、又要在这一页藏起来；"
                             "一条效果里的命令是按顺序执行的，"
                             "同一批单位两头都写就是自相矛盾"
                             % "、".join(str(u) for u in overlap[:6])}
        if group and sorted(set(on_ids)) == sorted(set(group[-1]["on"] or ())):
            return {"ok": False,
                    "error": "这一页要显示的单位和第 %d 页完全一样，"
                             "按下去看起来什么也没发生" % len(group)}
        donor_id = None
        if donor not in (None, ""):
            try:
                donor_id = int(donor)
            except (TypeError, ValueError):
                return {"ok": False, "error": "参照科技编号要是个整数"}
        if donor_id is None and group:
            donor_id = group[-1]["tech"]
        if donor_id is None:
            donor_id = 0
        if not techs:
            return {"ok": False, "error": "这个文件里没有科技，没法做伪翻页"}
        if not (0 <= donor_id < len(techs)):
            return {"ok": False,
                    "error": "没有第 %s 号科技（这个文件里有 %d 条）"
                             % (donor_id, len(techs))}
        label = "在第 %s 号建筑的第 %s 格加第 %s 页（显示 %d 种单位）" % (
            bld, btn, len(group) + 1, len(set(on_ids)))
        eff_start, eff_end, eff_count = tk._effect_section()
        buf = self.session_raw(tk)
        try:
            steps, info = PP.plan_add_page(
                buf, tk._parsed[3], tk._parsed[4], eff_start, eff_end, eff_count,
                donor_id, (name or "").strip() or ("Page%d" % (len(group) + 1)),
                on_ids, hide_units=hide_ids, building=bld, seconds=secs,
                button=btn)
        except PP.PageError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:                     # noqa: BLE001
            return {"ok": False, "error": "这一页没能算出来：%s" % (exc,)}
        out = {"ok": True, "kind": "pseudo-page", "building": bld, "box": btn,
               "page": len(group) + 1, "pages_before": len(group),
               "on": info["on"], "hide": info["hide"], "seconds": secs,
               "donor": donor_id, "tech": info["tech"], "effect": info["effect"],
               "grew": info["total_bytes"], "label": label}
        if dry:
            out["dry"] = True
            out["bytes"] = len(buf)
            return out
        writes = self._card_splice(buf, steps, expect=info["total_bytes"])
        note = {"unit": None, "civ": str(civ or "").strip() or None,
                "field": "pseudo_page", "op": "pseudo-page", "label": label,
                "was": None, "now": btn, "building": bld,
                "tech": info["tech"], "effect": info["effect"],
                "create": "tech.create"}
        for w in writes:
            w["struct"] = True
            w["note"] = dict(note)
        self._hist_push(writes)
        self._sess_dirty = True
        self._sess_struct = True
        # The effect block GREW, so the one cache `_relocate` deliberately keeps
        # (`_effects`, because a civ splice cannot move that block) is now stale
        # -- and so is the `(start, end, count)` this function just read.
        tk._effects = None
        tk._effect_sec = None
        self._pseudo_gen = -1
        self._restructure(writes)
        self._stamp_write(out)
        out["bytes"] = len(self._sess)
        out["undo_label"] = label
        return out

    # --- the three routes the native backend had and this one did not -------
    # WHY THESE EXIST: measured 2026-10-30, `_probe/ship_and_verify.py` walked
    # the shipped package and hit `/api/civ` 404, which is what happens when the
    # page is served by THIS backend.  The three routes had only ever been
    # written on the Rust side (`desktop/aoe2mod-serve/src/server.rs`: `/api/civ`
    # at :789, `/api/sprite` at :687, `/api/toggle-group` at :670), so switching
    # the shell to "Python when the folder carries it" would have REMOVED them.
    # A page must not get a different set of answers depending on which engine
    # happens to be behind it, so the missing three are added here and the
    # Python backend becomes a strict superset.
    #
    # The response shapes below follow the Rust ones FIELD FOR FIELD, including
    # the field names, because `_probe/ship_and_verify.py` and the page were
    # written against those names (`records`, `entries`).  Where this side has a
    # better name (`edit_count`) both are sent; renaming a field the native
    # build already publishes would just move the divergence.
    def civ(self, civ, units=(), techs=(), buildings=()):
        """One civilisation's answer for a set of nodes, or its whole tree.

        `civ` accepts either spelling the product deals in -- the `.dat` name
        (`British`) and the tree stem (`BRITONS`).  An unknown name is REFUSED
        with the list of stems, never answered with someone else's tree: an
        empty answer reads as "this civ has nothing", which is a wrong fact
        rather than a missing one.
        """
        from aoe2mod.game import civtechtrees as CT
        tk = self.tk
        tk._ensure()
        want = str(civ or "").strip()
        trees = tk._trees()
        if not trees:
            return {"ok": False,
                    "error": "这台机器上没有找到 CivTechTrees/*.json，读不出文明科技树",
                    "known": []}
        stem = CT.civ_file_stem(want)
        if stem not in trees:
            # The caller may have passed an id-space spelling nobody bridges.
            return {"ok": False, "error": "没有这个文明：%s" % (want,),
                    "known": sorted(trees.keys())}
        tree = trees[stem]
        flat = CT.compact(tree)
        ids_unit = list(units)
        ids_tech = list(techs)
        ids_bld = list(buildings)
        asked_some = bool(ids_unit or ids_tech or ids_bld)
        if not asked_some:
            return {"ok": True, "civ": stem, "asked": "everything", "tree": flat,
                    "note": _CIV_STATUS_NOTE}

        names = self._semantic()
        answers = []

        def one(letter, node, kind):
            rows = flat.get(letter, {}).get(str(int(node))) or []
            status = "unknown"
            if rows:
                # Same precedence as the native build: one row that grants it
                # wins over any number of rows that do not.
                letters = [r[1] for r in rows]
                status = ("available" if "C" in letters
                          else "gated" if "R" in letters else "unavailable")
            bucket = names.techs if kind == "tech" else names.units
            e = bucket.get(int(node))
            answers.append({
                "kind": kind, "id": int(node),
                "name": (e.zh or e.en) if e is not None else "",
                "status": status,
                # Building rows are where the game offers it; a unit listed
                # under two buildings keeps both (MAPUCHE's Skirmisher).
                "rows": [{"building": r[0],
                          "status": {"C": "available", "R": "gated",
                                     "N": "unavailable"}.get(r[1], "unknown"),
                          "age": r[2]} for r in rows],
            })

        for i in ids_unit:
            one("u", i, "unit")
        for i in ids_tech:
            one("t", i, "tech")
        for i in ids_bld:
            one("b", i, "building")
        return {"ok": True, "civ": stem, "asked": "some", "answers": answers,
                "note": _CIV_STATUS_NOTE}

    def _strings(self, mode=""):
        """{string id: text} for the current install, read once per process.

        The tech tree needs a NAME for every node, and `Name String ID` is the
        authoritative source -- `civtechtrees.py:407`'s docstring records that
        the row's own `Name` field is stale on 44 Chronicles rows.  Measured
        2026-11-08: merging all 14 zh `key-value-*.txt` tables resolves
        **10,742 / 10,742** rows; the main table alone misses 513 of them (134
        distinct ids, all 405xxx, e.g. 405001 「长生军 (近战)」, which lives in
        `key-value-paphos-strings-utf8.txt`).  So this must be `tables_for`,
        never a hand-rolled read of `key-value-strings-utf8.txt`.
        """
        cache = getattr(self, "_strings_cache", None)
        if cache is None:
            cache = self._strings_cache = {}
        key = mode or "base"
        if cache.get(key) is None:
            from aoe2mod.semantic import fromdat as FD
            try:
                # `self.game_root` is the OVERRIDE the server was started with
                # and is usually None; the resolved install lives on the
                # toolkit.  Reading the wrong one returns {} and every name on
                # the tree comes back blank -- measured 2026-11-08, first run of
                # this route printed `name_zh: ''` for all 173 BRITONS nodes.
                got = FD.tables_for(self.tk.game_root,
                                    getattr(self.tk, "dat_path", None))
                if key != "base":
                    # A mode's own table OVERLAYS the base one rather than
                    # replacing it: Rome at War reuses 4201..4204 and
                    # 120150..120166 with different text, but its tree files
                    # still reference plenty of ids that only the base table
                    # has.  Merging in this order gives the mode the last word
                    # on the ids it redefines and the base text everywhere
                    # else.  Measured 2026-11-08: 1,836 of the mode's 2,142
                    # name ids are missing from the base table, and 0 are
                    # missing from the mode's.
                    from aoe2mod.game import techtree_layout as _TL
                    merged = dict(got)
                    extra = {}
                    folder = os.path.join(_TL.mode_root(self.tk.game_root, key),
                                          "resources")
                    for loc in ("zh", "tw", "en"):
                        pat = os.path.join(folder, loc, "strings", "key-value",
                                           "key-value-*.txt")
                        for path in sorted(glob.glob(pat)):
                            FD._read_table(path, extra)
                    merged.update(extra)
                    got = merged
                cache[key] = got
            except Exception:                          # noqa: BLE001
                # Naming is never worth failing a screen over.
                cache[key] = {}
        return cache[key]

    def techtree(self, civ="", mode=""):
        """One civilisation's tech tree, laid out -- the geometry the page draws.

        WHY THIS ROUTE EXISTS: `/api/civ` answers "can this civ have X" with
        `compact()`, which is `[[Building ID, letter, Age ID], ...]` and carries
        no row, no grid and no picture index.  A tree needs all three, so this
        route returns the raw item list the engine file holds, laid out by
        `techtree_layout.layout()` -- a line-for-line port of SiegeEngineers'
        `generateTechTreeJsons.py`, verified 2026-11-08 to reproduce the site's
        own `data/trees/BRITONS.json` with **0 field differences** and to run on
        all **62** shipped civ files without raising.

        EVERYTHING HERE COMES OFF THE INSTALL.  `CivTechTrees/*.json`,
        `civilizations.json` and the string tables are the game's own files, so
        a patch that adds a civilisation adds one file and one `civilization_list`
        row and this route answers for it with no code change.  Measured
        2026-11-08: this install has **62** tree files while aoe2techtree.net
        publishes **56** -- the site is the one that lags.

        `mode` picks which set of files is read:

            base      `CivTechTrees/*.json`                         62 civs
            pompeii   `modes/Pompeii/resources/_common/dat/...`      17 civs

        Rome at War is a MODE, and its civilizations do not exist in the base
        files at all -- not the trees, not the names, not the icons.  The mode's
        five ageless tech rows per file are dropped by `techtree_layout._aged`
        (measured: 85 rows, and the official site drops them too).
        """
        from aoe2mod.game import techtree_layout as TL
        tk = self.tk
        tk._ensure()
        want_mode = (mode or TL.MODE_BASE).strip().lower()
        if want_mode not in TL.MODE_REL:
            return {"ok": False, "error": "没有这个模式：%s" % (mode,),
                    "modes": [{"key": k, "label": TL.MODE_LABEL[k]}
                              for k in ("base", "pompeii")]}
        trees = TL.load_trees_for(tk.game_root, want_mode)
        strings = self._strings(want_mode)
        rows = TL.civ_rows(tk.game_root, want_mode)
        civs = []
        for r in rows:
            stem = r["stem"]
            if not stem or stem not in trees:
                # GAIA is civilization_list's first row and has NO tree file.
                # Listing it would put a name in the picker that answers
                # "没有这个文明" when picked.
                continue
            zh = strings.get(int(r["name_string_id"] or 0)) or ""
            desc = TL.clean_prose(strings.get(int(r["desc_id"] or 0)) or "")
            civs.append({"stem": stem, "name_zh": zh or stem,
                         "name_en": r["internal_name"], "era": r["era"],
                         "mode": r["mode"],
                         "desc": desc,
                         "emblem": bool(r["emblem"])})
        want = str(civ or "").strip()
        if not want:
            want = "BRITONS" if "BRITONS" in trees else (sorted(trees)[:1] or [""])[0]
        stem = CT.civ_file_stem(want)
        if stem not in trees:
            return {"ok": False,
                    "error": "没有这个文明：%s" % (want,),
                    "mode": want_mode, "civs": civs,
                    "known": sorted(trees.keys())}
        tree = trees[stem]
        era = "base"
        for r in rows:
            if r["stem"] == stem:
                era = r["era"]
                break
        try:
            body = TL.build(tree, strings)
        except RuntimeError as exc:
            # The official script raises here too.  Reported as a sentence
            # rather than a 500 so the page can say which civ and why.
            return {"ok": False, "error": "这个文明的科技树排不下：%s" % (exc,),
                    "civ": stem, "mode": want_mode, "civs": civs}
        zh = ""
        desc = ""
        for c in civs:
            if c["stem"] == stem:
                zh = c["name_zh"]
                desc = c.get("desc") or ""
                break
        return {"ok": True, "civ": stem, "civ_zh": zh, "era": era,
                "mode": want_mode,
                "mode_label": TL.MODE_LABEL.get(want_mode, want_mode),
                "desc": desc,
                "ages": TL.age_names(era, strings),
                "buildings": body["buildings"],
                "units_techs": body["units_techs"],
                "civs": civs,
                "modes": [{"key": k, "label": TL.MODE_LABEL[k]}
                          for k in ("base", "pompeii")],
                # Age ID -> the grid row pair the drawing code uses.  Published
                # so the page does not have to re-derive `(age-1)*2`.
                "rows_per_age": 2}

    def _icons_for(self, mode=""):
        """The IconBook for one mode, cached.

        Rome at War ships its own `widgetui/icons.json` (11 tables) and its own
        `morematerials.json`, and its picture indices are DIFFERENT numbers in a
        DIFFERENT table: `Use Type=Building`, index 48, is a Stable in the mode
        and something else entirely in the base game's 117-slot table.  Reading
        the base book for a mode's tree therefore draws the wrong pictures
        everywhere, silently.
        """
        from aoe2mod.game import icons as IC
        from aoe2mod.game import techtree_layout as TL
        key = (mode or TL.MODE_BASE).strip().lower()
        books = getattr(self, "_icon_books", None)
        if books is None:
            books = self._icon_books = {}
        if key not in books:
            root = self.tk.game_root if key == TL.MODE_BASE else TL.mode_root(
                self.tk.game_root, key)
            books[key] = IC.IconBook(root)
        return books[key]

    def age_icon(self, n):
        """One of the game's four age medallions, straight off the install.

        `resources/_common/wpfg/resources/Icons/age-{1..4}.png`, 80x80 RGBA,
        shipped as plain PNG -- the roman numerals the game prints in the tech
        tree's left gutter.  No decode step, so this route just reads the bytes.
        """
        from aoe2mod.game import techtree_layout as TL
        import io as _io
        try:
            want = int(n)
        except (TypeError, ValueError):
            want = 0
        path = TL.age_icons(self.tk.game_root).get(want)
        if not path:
            return {"ok": False, "error": "没有第 %s 个时代的图标" % (n,)}
        with _io.open(path, "rb") as fh:
            return {"ok": True, "png": fh.read(), "content_type": "image/png"}

    def techtree_icons(self, pairs, max_side=34, mode=""):
        """Pictures for a list of `Section:id` pairs, as base64 PNG.

        A SEPARATE REQUEST ON PURPOSE: the tree structure paints in one frame and
        the pictures stream in behind it.  Measured 2026-11-08 on BRITONS: 173
        nodes, 172 distinct (section, picture index) pairs, and `ddstex.to_png`
        costs **2.0 s** for the lot at 34px (2.3 s at 40px).  Folding that into
        `/api/techtree` would make the whole view a two-second blank box, which
        is the same failure `icon()` documents for the unit list.

        `section` must be stated by the caller, not inferred: the SAME integer
        draws two different pictures in the `Units` and `Techs` tables
        (`picture_index 17` is `UnitIcons01750730` vs `TechIconsT017Forging`).
        The tree knows which one applies from the row's `Use Type`.
        """
        import base64
        from aoe2mod.game import ddstex as D
        side = int(max_side or 0)
        out = {}
        book = self._icons_for(mode)
        for raw in (pairs or "").split(","):
            piece = raw.strip()
            if not piece or ":" not in piece:
                continue
            section, _, num = piece.partition(":")
            try:
                icon_id = int(num)
            except ValueError:
                continue
            key = "%s:%d" % (section, icon_id)
            if key in out:
                continue
            book_key = (mode or "base").strip().lower()
            hit = self._icon_at.get(("tt", book_key, section, icon_id, side))
            if hit is not None:
                if hit.get("ok"):
                    out[key] = hit["data"]
                continue
            got = book.picture(section, icon_id)
            if not got.get("ok"):
                # picture() refuses icon_id 0 on purpose ("this record has no
                # icon id").  Measured over all 62 civs: exactly two rows carry
                # index 0 -- `Archery Range` (62 civs) and `Crop Rotation` (62)
                # -- and BOTH resolve if asked directly, because the Buildings
                # and Techs tables DO have a slot 0.  So the tree asks the table
                # itself rather than treating 0 as "no picture".
                name = book.material_name(section, icon_id) if icon_id >= 0 else None
                got = book.resolve(name) if name else {"ok": False}
                if not got.get("ok"):
                    self._icon_at[("tt", book_key, section, icon_id, side)] = {"ok": False}
                    continue
            png_key = (got.get("path"), side)
            body = self._icon_png.get(png_key)
            if body is None:
                body = D.to_png(got["path"], max_side=side)
                self._icon_png[png_key] = body
            data = "data:image/png;base64," + base64.b64encode(body).decode("ascii")
            self._icon_at[("tt", book_key, section, icon_id, side)] = {"ok": True, "data": data}
            out[key] = data
        return {"ok": True, "icons": out, "size": side}

    def animations(self, unit, civ=""):
        """The animations one unit's art actually has -- `/api/animations`.

        WHY THIS ROUTE EXISTS: everything else in the editor edits numbers.  A
        modder's first question is "what does it look like now", and until this
        route the answer was AGE3's `ShowSLP` or nothing.  The list is small (1
        to 9 entries per unit, measured across all 2,279 loose-art units) so it is
        cheap enough to ask for on every pick.

        Each entry carries BOTH the grid the records claim and the grid read off
        the file, because 16 of the 7,618 shipped art files are claimed by
        records that disagree with each other -- naming the disagreement is more
        useful than picking one and being quietly wrong.
        """
        from aoe2mod.game import filmstrip as F
        tk = self.tk
        tk._ensure()
        rec = self._unit_record(unit, civ)
        if rec is None:
            return {"ok": False,
                    "error": "找不到第 %s 号单位在这份数据里的记录" % (unit,)}
        idx = tk._reskin_art()
        art = idx.art(rec)
        rows = F.animations(art or {})
        for row in rows:
            poses, angles = self._poses_hint(row["file"], row["claimed"])
            row["poses"], row["angles"] = poses, angles
            row["grid"], row["grid_source"] = [poses, angles], (
                "record" if row["claimed"] else "file")
        return {"ok": True,
                "unit": int(unit or 0),
                "kind": (art or {}).get("kind"),
                "stem": (art or {}).get("stem"),
                "name": (art or {}).get("name"),
                "reason": (art or {}).get("reason"),
                "count": len(rows),
                "animations": rows}

    def _unit_record(self, unit, civ=""):
        """One unit's own record, preferring the named civilization's copy.

        The same unit id exists up to 63 times (one copy per civilization) and
        the copies can point at different art, so "which copy" has to be a
        parameter rather than a guess.  Falls back to the first civilization that
        has the id when the named one does not.
        """
        tk = self.tk
        try:
            uid = int(unit)
        except (TypeError, ValueError):
            return None
        civs = tk._civs or []
        want = None
        if civ:
            try:
                want = tk._civ_index(str(civ).strip())
            except Exception:                          # noqa: BLE001
                want = None
        order = [want] if want is not None else []
        order += [i for i in range(len(civs)) if i != want]
        for ci in order:
            for u in (civs[ci] or {}).get("units", ()):
                if u.get("id") == uid:
                    return u
        return None

    def _poses_hint(self, file_name, claimed):
        """(poses, angles) for one art file, without rendering it.

        Reads only the SLD header's `num_frames`; the angle count comes from the
        records when a claim reproduces the file, and the file is read as one
        angle otherwise.  Same decision `filmstrip.strip` makes, asked here so the
        page can print "60 poses, 16 directions" before anyone renders a pixel.
        """
        import os
        import struct
        from aoe2mod.game import filmstrip as F
        from aoe2mod.game import sprites as SP
        path = os.path.join(SP.graphics_dir(self.tk.game_root), file_name + ".sld")
        n = 0
        try:
            with open(path, "rb") as fh:
                head = fh.read(16)
            if head[:4] == b"SLDX":
                n = struct.unpack_from("<H", head, 6)[0]
        except OSError:
            return (1, 1)
        for fc, ac in sorted(tuple(g) for g in (claimed or ())):
            if fc and ac and F.poses_of(n, ac) == fc:
                return (fc, ac)
        return (F.poses_of(n, 1) or n or 1, 1)

    def film(self, unit, civ="", anim="", frame=0, count=20, angle=0,
             with_shadow=False):
        """One animation as a single PNG row -- `/api/film`.

        Answers image/png through `_guard_icon`, not JSON, for the same reason
        `/api/icon` does: a 1.2 MB castle row wrapped in base64 is 1.6 MB of JSON
        and every encode failure would look like "the picture is missing".

        `count` is capped by `filmstrip.MAX_FRAMES` and by the strip's
        `max_width`, so a 150-frame castle destruction comes back as its first N
        poses and says so in `trimmed` rather than arriving 52,050 px wide.
        """
        from aoe2mod.game import filmstrip as F
        tk = self.tk
        tk._ensure()
        rec = self._unit_record(unit, civ)
        if rec is None:
            return {"ok": False,
                    "error": "找不到第 %s 号单位在这份数据里的记录" % (unit,)}
        idx = tk._reskin_art()
        art = idx.art(rec)
        rows = F.animations(art or {})
        if not rows:
            why = (art or {}).get("reason") or "这个单位没有散图，画不出动画"
            return {"ok": False, "error": why}
        key = (anim or "").strip().lower()
        pick = None
        for row in rows:
            if row["key"] == key:
                pick = row
                break
        if pick is None:
            return {"ok": False,
                    "error": "这个单位没有「%s」这个动作（有：%s）"
                             % (anim, "、".join(r["zh"] for r in rows))}
        poses, ac = self._poses_hint(pick["file"], pick["claimed"])
        got = F.strip(tk.game_root, pick["file"], frames=count, start=frame,
                      angles=ac, angle=angle, with_shadow=bool(with_shadow))
        got["ok"] = True
        got["unit"] = int(unit or 0)
        got["anim"] = pick["key"]
        got["anim_zh"] = pick["zh"]
        # The body is a PNG, so the numbers travel as headers: how many poses
        # the file has, how many were asked for, whether the row was cut to fit
        # the window, and how many poses in this angle draw nothing.  Without
        # them the page cannot say "第 61 到 80 个姿态" above the picture.
        got["headers"] = {
            "X-Film-Poses": got.get("poses") or 0,
            "X-Film-Frames": got.get("frames") or 0,
            "X-Film-Start": got.get("start") or 0,
            "X-Film-Angles": got.get("angles") or 1,
            "X-Film-Angle": got.get("angle") or 0,
            "X-Film-Truncated": 1 if got.get("capped") or got.get("trimmed") else 0,
            "X-Film-Blank": got.get("blank") or 0,
        }
        return got

    def sprite(self, unit, donor, civs=None, whole_family=False, fill=False,
               mode="rename", dry=True, title=None, install=False):
        """Swap one unit's animation for another's -- `/api/sprite`.

        Two refusals the native build makes are made here too, because each of
        them is a way to report success while nothing changed: no donor means
        "swap with what?", and a donor equal to the target is the one combination
        that always compiles to zero edits.
        """
        if unit in (None, "", 0):
            return {"ok": False, "error": "没说要换成哪个单位的图"}
        if donor in (None, "", 0):
            return {"ok": False, "error": "没说要换成哪个单位的图"}
        if int(unit) == int(donor):
            # Compiles to zero edits, and a zero-edit build still says "ok" --
            # the player then installs a mod that changes nothing and has no way
            # to tell it apart from a broken button.  The native build refuses
            # it for the same reason; the wording is its own.
            return {"ok": False,
                    "error": "目标单位和捐赠方是同一个，改了等于没改"}
        intent = {"intent": "unit.sprite", "unit": int(unit),
                  "donor": int(donor), "mode": mode or "rename"}
        if civs:
            intent["civs"] = list(civs)
        if whole_family:
            intent["whole_family"] = True
        if fill:
            intent["fill"] = True
        if dry and not install:
            plan = self._decorate(self.tk.plan(intent))
            # `records` is the native build's name for what this side calls
            # `edit_count`; both go out so neither caller has to know which
            # engine answered.
            out = dict(plan)
            out.update({"ok": True, "intent": "unit.sprite",
                        "mode": plan.get("sprite_mode") or intent["mode"],
                        "records": plan.get("edit_count"),
                        "file_count": (plan.get("copy_based_equivalent") or {})
                        .get("files"),
                        "dry": True})
            return out
        r = self.tk.build(intent, _out_root(), title=title or "sprite",
                          overwrite=True)
        man = dict(r)
        man.update({"ok": True, "intent": "unit.sprite",
                    "mode": man.get("sprite_mode") or intent["mode"],
                    "records": man.get("edit_count"),
                    "dry": False})
        if install and man.get("mod_dir"):
            man["installed"] = self.install(man["mod_dir"], name=title)
        return man

    def toggle_group(self, techs, kind=None, comment="", dry=True, title=None,
                     install=False):
        """Make research of these technologies mutually exclusive.

        `dry` defaults to TRUE here for the same reason `/api/field-set` does:
        the common mistake is naming a tech that cannot join a group, and echoing
        the numbers first costs nothing while building rewrites 93 MB.
        """
        ids = [int(x) for x in (techs or [])]
        if len(ids) < 2:
            return {"ok": False,
                    "error": "互斥至少要有两项科技，现在只有 %d 项" % len(ids)}
        intent = {"intent": "tech.toggle_group", "techs": ids}
        if kind:
            intent["type"] = kind
        if comment:
            intent["comment"] = comment
        if dry and not install:
            plan = self._decorate(self.tk.plan(intent))
            out = dict(plan)
            # `entries` is the count of groups the file holds AFTER this group
            # is added -- the number the native build reports and the one a
            # player can verify by opening linkedTechs.json.
            before = plan.get("shipped_groups")
            out.update({"ok": True, "intent": "tech.toggle_group",
                        "entry": {},
                        "entries": (before + 1) if isinstance(before, int)
                        and plan.get("editable") else None,
                        "groups_before": before, "dry": True,
                        "built": "", "installed": ""})
            return out
        r = self.tk.build(intent, _out_root(), title=title or "tech group",
                          overwrite=True)
        man = dict(r)
        before = man.get("groups_before")
        man.update({"ok": True, "intent": "tech.toggle_group",
                    "entries": (before + 1) if isinstance(before, int) else None,
                    "groups_before": before, "dry": False})
        if install and man.get("mod_dir"):
            man["installed"] = self.install(man["mod_dir"], name=title)
        return man

    # --- 全字段编辑 ------------------------------------------------------
    # ---- edit session -----------------------------------------------------
    # WHY A SESSION BUFFER EXISTS: the first version applied every write to
    # `tk._raw` (a copy of the game file) and then threw that copy away, so a
    # second edit started again from the game's original bytes.  Measured
    # 2026-10-29: change 民兵 hit points to 4321, then change its speed -- the
    # rebuilt mod had the new speed and the OLD hit points, and the pane showed
    # 40.  The data editor has to accumulate, exactly like AGE's own windows, or
    # every edit undoes the previous one.
    #
    # The buffer is a plain `bytearray`; `session_dirty` says whether it differs
    # from the game file.  `reset_session()` is the way back.
    def session_raw(self, tk=None):
        """The bytes every field lookup and write works against.

        Returns the LIVE `bytearray` on purpose: `bytearray(raw)` on a 93 MB file
        costs 93 MB and a full copy per request, and `set_unit_field` then copies
        it AGAIN to diff.  Measured 2026-10-29: opening one unit allocated
        ~280 MB.  Callers must not mutate it; `_session_edit` is the only writer.

        ``tk`` lets a caller that already read the ``tk`` property PIN this
        request to one file.  Without it the buffer and the offsets could come
        from different `.dat`s while `set_dat` swaps underneath: measured on a
        screenshot, `EOFError: read of 12 byte(s) at offset 124537926 would pass
        end of file (93272287)` -- offset from a 125 MB mod, bytes from the
        game's 93 MB file.
        """
        tk = tk if tk is not None else self.tk
        tk._ensure()
        buf = getattr(self, "_sess", None)
        owner = getattr(self, "_sess_owner", None)
        if buf is not None and owner != tk.dat_path:
            # A switch happened between two calls in this same request.  The
            # copy belongs to the file that is no longer open, so it is not
            # "some old bytes", it is bytes that do not describe this file.
            buf = None
        if buf is None:
            buf = bytearray(tk._raw)
            self._sess = buf
            self._sess_owner = tk.dat_path
            self._sess_dirty = False
        return buf

    @property
    def session_dirty(self):
        return bool(getattr(self, "_sess_dirty", False))

    def _session_edit(self, off, packed, note=None, hold=False):
        """Apply one little-endian field write to the session buffer.

        `note` is the human line kept in `self._edits` so the header can say
        "已改 3 项" and the final build can describe itself.

        `hold` groups this write with the ones that follow it, so 63 copies of
        one unit undo as ONE gesture instead of sixty-three.  The caller that
        loops over civilisations opens the group with `_hist_begin()` and closes
        it with `_hist_commit()`; every other write is a step of its own.

        The pending list is no longer maintained here.  It is REBUILT from the
        history (`_hist_rebuild_edits`), because 撤回 has to be able to take a
        row back off the list: a list that only ever grows would keep saying
        "已改 2 项" after the player undid both.
        """
        self.session_raw()
        before = bytes(self._sess[off:off + len(packed)])
        self._sess[off:off + len(packed)] = packed
        self._sess_dirty = True
        self._hist_record(off, before, packed, note, hold)
        self._after_write(off, packed, note)

    def _after_write(self, off, packed, note):
        """Put a written value into the caches, or drop what cannot be patched.

        Split out of `_session_edit` for 撤回: an undo writes the OLD bytes back,
        which is the same kind of write as the one being undone, so the caches
        have to be repaired the same way.  Passing the bytes now STORED (not the
        ones being replaced) is what lets one function serve both directions.

        Patch the cached VALUES in place instead of dropping the index.
        """
        # Every field write is the same byte width as the field it replaces, so
        # no offset can move -- the index is still a correct map of the file,
        # only one number inside it is stale.  Dropping it forced an 8-20 s
        # rescan on the very NEXT edit; measured 2026-10-30, six edits paid
        # ~23 s each almost entirely for this one line.
        note = note or {}
        idx = getattr(self.tk, "_field_index", None)
        if idx is not None and note.get("unit") is not None:
            civ_idx = None
            try:
                civ_idx = self.tk._civ_index(str(note.get("civ") or "").strip()) if str(
                    note.get("civ") or "").strip() else (1 if len(self.tk._civs) > 1 else 0)
            except Exception:                          # noqa: BLE001
                civ_idx = None
            rec = idx.get((civ_idx, int(note["unit"]))) if civ_idx is not None else None
            if rec is not None:
                # The index no longer caches decoded fields (12.3 GB, see
                # `_unit_index`); drop this record's on-demand decode so the
                # next `unit_fields()` reads the edited bytes.
                rec.pop("fields", None)
        # Technologies cache their decode the same way, under their own index.
        # `note["tech"]` is present only for `set_tech_field`, so a unit edit
        # never invalidates the tech panel and vice versa.
        tidx = getattr(self.tk, "_tech_field_index", None)
        if tidx is not None and note.get("tech") is not None:
            trec = tidx.get(int(note["tech"]))
            if trec is not None:
                trec.pop("fields", None)
        # An effect-list write patches a command INSIDE a cached effect record,
        # which is a third cache again.  Dropping it would cost a 5 s walk of the
        # Effects stage on the very next preview; the offsets cannot move (the
        # number is a fixed-width float32), so the one stale value is patched in
        # place -- the same reasoning as the two branches above.
        #
        # Measured 2026-11-01: without this, writing 织布机's +15 to 100 and then
        # re-reading the list showed 15 again, and a SECOND preview of the same
        # edit still claimed 15 as the old value.
        if note and note.get("effect") is not None:
            self._patch_effect_cache(int(note["effect"]), int(note["command"]),
                                     off, packed)
        # A card drag writes the `button_id` byte inside one `train_locations`
        # entry.  `CARD.card()` builds the page from `tk._civs`, which still said
        # box 1 after the byte said 5 -- the page would draw the unit where it
        # used to be until something re-walked the file.  Patch the one field:
        # the byte is fixed width, so the offset is still valid, and dropping
        # `_civs` would re-walk 63 civilisations per drag.
        if note and note.get("op") == "card" and note.get("unit") is not None:
            self._patch_card_entry(note, off, packed)

    def _patch_card_entry(self, note, off, packed):
        """Put one written card value into the located model, everywhere it lives.

        `CARD.card()` and `CARD.boxes()` build the page from `tk._civs`, not from
        the buffer, so a value written into the buffer is invisible to the page
        until something re-walks the file -- measured 2026-11-07: the byte said
        box 5, `pending` said 1, and the page still drew the unit in box 1.

        The value is decoded from `packed` (the bytes now stored), never from the
        note: 撤回 replays the same note with the previous bytes, and a
        note-driven patch put the unit back at box 5 while the buffer said 1.

        EVERY civ copy is patched, not just the one being edited, because the
        shipped file carries the same record 63 times and `card()` may be asked
        about any of them.  Only the entry naming THIS builder is touched: a unit
        can be trained by several buildings, and moving it on one card must not
        move it on the others.
        """
        import struct
        unit_id = int(note["unit"])
        builder_id = int(note.get("building") or 0)
        field = note.get("card_field") or "button_id"
        raw = bytes(packed)
        if field == "button_id":
            value = struct.unpack_from("<B", raw, 0)[0]
        elif field == "train_time":
            value = struct.unpack_from("<h", raw, 0)[0]
        else:
            return
        civs = getattr(self.tk, "_civs", None)
        if not civs:
            return
        for civ in civs:
            for u in civ.get("units") or ():
                if u.get("id") != unit_id:
                    continue
                for tl in u.get("train_locations") or ():
                    if tl.get("unit_id") == builder_id:
                        tl[field] = value

    # ---- 撤回 / 重做 ------------------------------------------------------
    # WHY A HISTORY AT ALL: "放弃" already threw the whole session away, which is
    # fine for "start over" and useless for "that last number was wrong".  AGE3
    # has Undo/Redo; this editor had neither, so a mistyped 生命值 meant finding
    # the unit again and retyping the old value from memory.
    #
    # A step stores the BYTES it replaced, not an offset plus a value: an edit is
    # one to four bytes and the same write serves units, technologies, effect
    # commands and the six table spaces.  Offsets inside one .dat never move
    # (every field write is the same width as the field it replaces), so a pair
    # of byte strings is a complete description of the change -- and it stays
    # true even if the wording of a note changes later.
    #
    # ONE GESTURE, ONE STEP.  Writing 生命值 across all 63 civilisations is 63
    # separate `_session_edit` calls; undoing them one at a time would be a
    # practical joke.  The caller wraps the loop in `_hist_begin()` and
    # `_hist_commit()` and the whole batch becomes a single step.

    HIST_MAX = 200

    def _hist_begin(self):
        """Start grouping writes into one undo step."""
        self._hist_group = []

    def _hist_record(self, off, before, packed, note, hold=False):
        """Remember one byte write.  Called by `_session_edit` for every write."""
        # `struct` marks a step that CHANGED THE LENGTH of the file.  Its
        # offsets are only valid for the exact buffer state around it, and every
        # index built from the old geometry is wrong afterwards, so undo/redo of
        # such a step has to re-read the buffer instead of patching one value.
        w = {"off": off, "before": before, "after": bytes(packed),
             "struct": bool((note or {}).get("struct")),
             "note": dict(note) if note else None}
        if hold and getattr(self, "_hist_group", None) is not None:
            self._hist_group.append(w)
            return
        self._hist_push([w])

    def _hist_commit(self):
        """Turn everything collected since `_hist_begin()` into one step."""
        group = getattr(self, "_hist_group", None)
        self._hist_group = None
        if group:
            self._hist_push(group)

    def _hist_push(self, writes):
        hist = getattr(self, "_hist", None)
        if hist is None:
            hist = self._hist = []
        at = getattr(self, "_hist_at", 0)
        # A new edit after 撤回 discards the redo tail: the player chose a
        # different future, so the old one is no longer reachable.
        if at < len(hist):
            del hist[at:]
        hist.append(writes)
        # Bounded: a player who edits five hundred numbers does not need five
        # hundred undos, and one step holds a handful of bytes per record.
        if len(hist) > self.HIST_MAX:
            del hist[:len(hist) - self.HIST_MAX]
        self._hist_at = len(hist)
        self._hist_rebuild_edits()

    def _hist_rebuild_edits(self):
        """Recompute the pending list from the steps that are still applied.

        The list cannot be appended to any more: 撤回 has to be able to take a
        row back off it, and a list that only ever grows would keep saying
        "已改 2 项" after the player undid both.

        The merge key has to include WHICH record.  Unit edits carry `civ` and
        `unit` so two civilisations' 村民 stay apart; a technology edit carries
        neither (a tech record is not per-civ), so without `tech` in the key
        every technology's ResearchTime would collapse into one row and the mod
        would ship a single edit for a batch of twelve.

        The FIRST `was` wins -- that is the game's original value.  Letting a
        later write overwrite it made a field edited three times report
        "3600 -> 3900" in the mod description, hiding that the player moved it
        from 40.
        """
        hist = getattr(self, "_hist", None) or []
        at = getattr(self, "_hist_at", 0)
        edits = []
        for writes in hist[:at]:
            for w in writes:
                note = w.get("note")
                if not note:
                    continue
                # `op` keeps a record add/remove out of the field-write rows:
                # they share (civ, unit) with the field edits of the same record
                # and merging them made 「复制单位 83」 vanish behind a row that
                # said `unit.field` with an empty field name.
                key = (note.get("civ"), note.get("unit"), note.get("tech"),
                       note.get("field"), note.get("op"))
                for e in edits:
                    if (e.get("civ"), e.get("unit"), e.get("tech"),
                            e.get("field"), e.get("op")) == key:
                        keep = e.get("was")
                        e.update(note)
                        e["was"] = keep
                        break
                else:
                    edits.append(dict(note))
        self._edits = edits
        return edits

    def hist_state(self):
        """What the 撤回/重做 buttons need: how many steps each way, and a label."""
        hist = getattr(self, "_hist", None) or []
        at = getattr(self, "_hist_at", 0)
        label = ""
        if at > 0:
            for w in reversed(hist[at - 1]):
                if w.get("note"):
                    label = str(w["note"].get("label") or w["note"].get("field") or "")
                    break
        redo_label = ""
        if at < len(hist):
            for w in reversed(hist[at]):
                if w.get("note"):
                    redo_label = str(w["note"].get("label") or w["note"].get("field") or "")
                    break
        return {"ok": True, "undo": at, "redo": len(hist) - at,
                "undo_label": label, "redo_label": redo_label}

    def undo(self):
        """Put the bytes of the last step back."""
        hist = getattr(self, "_hist", None) or []
        at = getattr(self, "_hist_at", 0)
        if at <= 0:
            return {"ok": False, "error": "没有可以撤回的改动了"}
        step = hist[at - 1]
        self._hist_apply(step, "before")
        self._hist_at = at - 1
        # With every step taken back the buffer IS the game file again, so the
        # "unsaved changes" warning must stop firing.  Anything left over means
        # the player built a mod from an earlier batch (see `save_session`).
        self._sess_dirty = bool(self._hist_at)
        self._hist_rebuild_edits()
        out = self.hist_state()
        out.update(self._session_counts())
        # The page patched the list in place when the records were made instead
        # of re-reading it (see `edAfterAdd`), so it also has to be told which
        # rows are gone -- otherwise 撤回 leaves the deleted rows on screen and
        # the counter keeps claiming a total the file no longer has.  Reported
        # 2026-11-05 as 「列表还会还原」; the same in-place fix needs both halves.
        out["undone"] = self._step_notes(step)
        return out

    def redo(self):
        """Apply the last undone step again."""
        hist = getattr(self, "_hist", None) or []
        at = getattr(self, "_hist_at", 0)
        if at >= len(hist):
            return {"ok": False, "error": "没有可以重做的改动了"}
        step = hist[at]
        self._hist_apply(step, "after")
        self._hist_at = at + 1
        self._sess_dirty = True
        self._hist_rebuild_edits()
        out = self.hist_state()
        out.update(self._session_counts())
        out["redone"] = self._step_notes(step)
        return out

    @staticmethod
    def _step_notes(writes):
        """The notes of one undo step, newest-last, minus write-internal keys.

        A step is a list of byte pairs; only the ones carrying a `note` describe
        what the player asked for.  `op` + `ids` is what the list needs to know
        which rows the step created or destroyed.
        """
        out = []
        seen = set()
        for w in (writes or ()):
            note = w.get("note")
            if not note:
                continue
            # ONE GESTURE, ONE LINE.  A rename writes its display string into
            # every copy of the record (74 exists in 63 civ records), and a
            # batch add tags each sliced byte pair with the same note -- either
            # way the step carries the same sentence dozens of times.  The page
            # then摘 the same row and re-inserts it once per copy: correct but
            # N times the work, and the /api/undo body grows by 70x.
            key = (note.get("civ"), note.get("unit"), note.get("tech"),
                   note.get("field"), note.get("op"))
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(note))
        return out

    def _hist_apply(self, writes, side):
        """Write one side of a step's byte pairs into the session buffer.

        The slice being replaced is not always as wide as the bytes being put
        there.  A field write is equal-width, but a step that ADDED a record has
        an empty `before`, and undoing it has to CUT the bytes it added, not
        overwrite zero of them -- which would leave the record behind and a
        history that says it was taken back.  So the width to replace is the
        width of the OTHER side.

        UNDO RUNS THE STEP BACKWARDS.  A plan that inserts a record lists its
        writes in the order they were applied, and several of those offsets only
        make sense in the buffer that existed between them: shrinking the flag
        array back before cutting the record that sits after it lands on the
        wrong bytes.  Equal-width field writes are independent of each other,
        which is why the order never mattered until a step could change the
        file's length -- measured 2026-11-05, undoing a duplicate in forward
        order produced a buffer the parser could not walk (`read_bird`,
        `struct.error: bad char in struct format`).
        """
        buf = self.session_raw()
        structural = False
        order = list(writes) if side == "after" else list(reversed(writes))
        for w in order:
            packed = w[side]
            cut = len(w["after"] if side == "before" else w["before"])
            buf[w["off"]:w["off"] + cut] = packed
            if w.get("struct"):
                structural = True
            else:
                self._after_write(w["off"], packed, w.get("note"))
        if structural:
            self._restructure(writes, undo=(side == "before"))
        if any((w.get("note") or {}).get("op") == "rename" for w in writes):
            self._resync_display_ids()


    def _session_counts(self):
        return {"dirty": self.session_dirty,
                "pending": len(self.pending_edits()),
                "bytes": len(self._sess) if self._sess is not None else 0}

    def _patch_effect_cache(self, effect_id, command, off, packed):
        """Put a written value into the cached effect record, or drop the cache.

        The cache is `tk._effects`, a list of `{name, commands:[{..., d}]}`.
        A miss (no such effect, no such command, or a different offset than the
        one recorded) drops the whole cache rather than half-fixing it: a cache
        that is right for 10,499 commands and wrong for one is worse than no
        cache, because the preview would invent a `before` value.
        """
        import struct
        try:
            stored = struct.unpack("<f", packed)[0]
        except Exception:                                  # noqa: BLE001
            self.tk._effects = None
            return
        effects = getattr(self.tk, "_effects", None)
        if not effects or not (0 <= effect_id < len(effects)):
            self.tk._effects = None
            return
        cmds = effects[effect_id].get("commands") or ()
        if not (0 <= command < len(cmds)):
            self.tk._effects = None
            return
        c = cmds[command]
        if c.get("_off_d") != off:
            # The record moved, which a fixed-width write cannot cause -- so the
            # cache is not the one this write belongs to.
            self.tk._effects = None
            return
        c["d"] = stored

    def _stamp_write(self, out):
        """Fill in the counters every accepted write reports back.

        The 撤回/重做 buttons are enabled from these, so a write that forgot them
        would leave a fresh change un-undoable until the next poll -- and the
        player would press 撤回 and be told there is nothing to take back.
        """
        out["session_dirty"] = True
        out["pending"] = len(self.pending_edits())
        hist = self.hist_state()
        out["undo"] = hist["undo"]
        out["redo"] = hist["redo"]
        out["undo_label"] = hist["undo_label"]
        out["redo_label"] = hist["redo_label"]
        out["saved_to_memory"] = True
        return out

    def _relocate(self, tk, writes, undo):
        """Carry the parsed model across one splice instead of re-parsing it.

        `relocate` moves every byte offset the model keeps by the same deltas
        the splice applied, then re-walks only the civ the splice landed in.
        Measured 2026-11-06 on the 93 MB file: unfold the writes + shift every
        offset + re-walk one civ + rebuild the field index is 0.43 s, against
        10.45 s for `Parser.parse` + `locate.locate` and another 10.4 s for the
        `unitfields.scan` that used to follow it.  That difference is the whole
        complaint -- "每次粘贴都会重新刷新加载，太慢了".

        Returns True when the model was moved AND verified, False when the
        caller has to fall back to the full re-parse.  A False is not an error:
        a model without `_start`/`_end` (a cache written before parsecache v2)
        and a chain that does not close both take that road, and the fallback is
        still correct.
        """
        parsed = getattr(tk, "_parsed", None)
        civs = getattr(tk, "_civs", None)
        if not parsed or not civs:
            return False
        if any(c.get("_start") is None or c.get("_end") is None for c in civs):
            return False
        rules = REL.splice_rules(writes, undo=undo)
        if not rules:
            # Every write in this edit kept its length, so no offset moved --
            # there is nothing to relocate and nothing to re-derive.
            return True
        # THIS IS AN OFFSET TOO.  It is the block's first byte, so a splice
        # anywhere before the civ block moves it exactly like the civs after it.
        # Left unshifted it disagrees with the (shifted) first civ and
        # `chain_ok` refuses a model that is perfectly good -- measured
        # 2026-11-09: the pseudo-page append fell back to a 15.65 s reparse
        # because of this one line.
        civs_start = REL.shift(rules, parsed[2])
        # A SPLICE BEFORE THE CIV BLOCK MOVES THE EFFECT BLOCK TOO, so the two
        # caches `_relocate` keeps for civ edits are wrong for this one.  They
        # were kept unconditionally and that cost a wrong answer rather than a
        # slow one: undo a pseudo-page (whose rule sits at the end of the effect
        # block), then add another, and `_effect_sec` still described the file
        # from before the undo -- the append landed 19 bytes past the block and
        # every later read died with `EOFError: read of 4 byte(s) at offset
        # 93272378 would pass end of file (93272379)`.  Measured 2026-11-09.
        if any(at < parsed[2] for at, _delta in rules):
            tk._effects = None
            tk._effect_sec = None
        gv = parsed[3]
        tail = parsed[4]
        # Which civ received the splice, in the coordinates of the buffer this
        # edit applies to.  The LAST civ that starts at or before the splice
        # owns it: civs are back to back, so bytes inserted exactly on a
        # boundary belong to the record ending there, not the one beginning.
        touched = []
        for at, _delta in rules:
            # `None` when the splice is before the first civ -- an insertion at
            # the end of the effect or technology block moves every civ without
            # editing any of them, and re-walking one of those would only
            # re-derive bytes that are already right.
            pick = None
            for ci, c in enumerate(civs):
                if c["_start"] <= at:
                    pick = ci
                else:
                    break
            if pick is not None and pick not in touched:
                touched.append(pick)
        buf = self.session_raw(tk)
        REL.shift_civs(civs, rules)
        new_tail = REL.shift(rules, tail)
        for ci in touched:
            REL.re_walk_civ(civs, buf, gv, ci)
        if not REL.chain_ok(civs, civs_start, new_tail):
            # The moved offsets no longer describe the new bytes as one unbroken
            # stream, so they cannot be trusted for writes.  Re-parse instead.
            return False
        raw = bytes(buf)
        tk._raw = raw
        tk._parsed = (raw, civs, civs_start, gv, new_tail, parsed[5])
        stats = tk._stats
        for ci in touched:
            REL.sync_stats_civ(stats, ci, civs[ci])
        # The technology block STARTS at the tail, so a unit splice moves all of
        # it.  `walk_tech` keeps no byte offset and `locate_techs` costs 8 ms, so
        # re-reading is both cheaper and safer than shifting a list of rows.
        try:
            techs = L.locate_techs(raw, new_tail, gv)
        except Exception:
            techs = None
        if techs is not None:
            stats["techs"] = techs
            stats["tech_count"] = len(techs)
        tk._techs = None
        # `_effects` is deliberately NOT dropped: the effect block sits before
        # the civ block, so no splice inside a civ can move it, and re-reading it
        # is the one expensive cache in the set (4.905 s measured 2026-11-06).
        for name in ("_field_index", "_tech_field_index", "_civ_spread",
                     "_tech_census", "_fam", "_index", "_unit_lines",
                     "_uifacts", "_fanout"):
            if hasattr(tk, name):
                setattr(tk, name, None)
        for name in [k for k in list(vars(tk)) if k.startswith("_table_index_")]:
            setattr(tk, name, None)
        self._vocab = None
        self._task_name_cache = {}
        return True

    def _restructure(self, writes=None, undo=False):
        """Re-read the session buffer after a record was added or removed.

        ONE INSERT MOVES EVERY OFFSET AFTER IT.  The parsed model, the unit
        field index, the technology index, every table index, the effect cache
        and the cross-civ histogram all describe the bytes as they were, so none
        of them can be patched -- they have to be thrown away and rebuilt from
        the new buffer.  Measured 2026-11-05: `Parser.parse` + `locate.locate`
        on 93 MB is ~10 s, which is why this runs once per structural edit and
        never on an ordinary field write.

        Re-reading from `self.dat_path` is NOT an option here: the file on disk
        is the one without this edit, so `_ensure()` would hand back a model of
        the wrong bytes while the buffer kept the right ones.
        """
        # Bump FIRST: a scan that is mid-walk right now is walking the bytes we
        # are about to replace, and it must lose the race even though it started
        # first.
        self._gen_bump()
        tk = self.tk
        if writes and self._relocate(tk, writes, undo):
            return tk
        raw = bytes(self.session_raw())
        p = P.Parser(raw)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
        civs, civs_start, gv, tail = L.locate(raw, parser=p)
        how = tk._parsed[5] if getattr(tk, "_parsed", None) else None
        tk._raw = raw
        tk._civs = civs
        tk._stats = p.stats
        tk._parsed = (raw, civs, civs_start, gv, tail, how)
        for name in ("_field_index", "_tech_field_index", "_effects",
                     # The technology rows live at the tail pointer, so a
                     # reparse is exactly the event that invalidates them.  It
                     # went unnoticed because `_relocate` clears `_techs`
                     # itself and every structural edit used to take that road;
                     # the first one that fell back to a full parse kept 5,874
                     # rows of a file that now has 5,875 -- and the panel said
                     # the page had not been added.
                     "_techs", "_effect_sec",
                     "_civ_spread", "_tech_census", "_fam", "_index",
                     "_unit_lines",
                     # `_uifacts` is the icon/class table `icon_for` reads: it
                     # is built from the unit records, so a cloned record is
                     # absent from it and the new row paints a blank `?`.
                     # Measured 2026-11-05: `/api/icon?id=30000` came back as a
                     # 57-byte placeholder while id 74 next to it was a 4,519-
                     # byte PNG.  `_fanout` folds the technology list into the
                     # effect cache, so a new technology stales it too.
                     "_uifacts", "_fanout"):
            if hasattr(tk, name):
                setattr(tk, name, None)
        for name in [k for k in list(vars(tk)) if k.startswith("_table_index_")]:
            setattr(tk, name, None)
        self._vocab = None
        self._task_name_cache = {}
        return tk

    def record_rename(self, kind="unit", civ="", record=None, name=None,
                      display=True):
        """Give one unit or technology a new internal name.

        Every name field in the editor is read-only and says so, which is
        correct: `Name` is three addresses (marker, length, text) and writing
        the text alone leaves the length stale -- `parser.Reader.debug_string`
        records a 2,656-byte drift from exactly that mistake.  That refusal,
        though, ended with 「要改请用「重命名」」 and no such command existed
        (reported 2026-11-06 as 「为什么不能修改名字」).  This is it.

        WHAT CHANGES: the `.dat` byte string only.  The name a player SEES comes
        from `LanguageDLLName` pointing into a string table, and that is a
        different road (which is why that field is read-only too).  Renaming
        here changes what later patches, the tech tree and this editor's own
        lists call the record.

        A rename can change the record's WIDTH, so this is a structural edit and
        goes through `_restructure`, which hands it to `relocate` and only
        re-walks the one civilisation the bytes moved inside.

        ``display`` also changes the name the GAME shows.  That name is a string
        id, and the shipped ids are shared -- string id 5079 is the name of 57
        records, so writing "弩手甲" into it would rename all fifty-seven.  So a
        fresh id is allocated above the highest shipped one, this record (and
        every other civilisation's copy of the same unit id) is pointed at it,
        and the row itself is carried in the mod by `save_session`.  The two
        halves have to travel together: an id with no row shows the number.
        """
        tk = self.tk
        kind = str(kind or "unit").strip().lower()
        if kind not in ("unit", "tech"):
            return {"ok": False,
                    "error": "只有单位或科技有名字，没有 %r 这种记录空间" % (kind,)}
        new_name = str(name or "").strip()
        if not new_name:
            return {"ok": False, "error": "名字不能是空的"}
        if tk._parsed is None:
            tk._ensure()
        buf = self.session_raw()
        gv = tk._parsed[3]
        civs_start = tk._parsed[2]
        tail = tk._parsed[4]
        civ_index = 0
        old_name = ""
        try:
            if kind == "tech":
                tid = int(record)
                old_name = next((t.get("name") or "" for i, t in
                                 enumerate(tk._stats.get("techs") or [])
                                 if i == tid), "")
                steps, info = REC.plan_rename_tech(buf, gv, tail, tid, new_name)
                label = "重命名科技 %s 为「%s」" % (tid, new_name)
                note = {"tech": tid, "field": "Name", "op": "rename",
                        "label": label, "was": NTX.readable(old_name),
                        "now": new_name, "tech_name": new_name,
                        "civ": None, "unit": None}
            else:
                want = str(civ or "").strip()
                if want in ("*", "all", "全部"):
                    want = ""
                civ_index = (tk._civ_index(want) if want
                             else (1 if len(tk._civs) > 1 else 0))
                uid = int(record)
                civ = tk._civs[civ_index]
                old_name = next((u.get("name") or "" for u in civ["units"]
                                 if u.get("id") == uid), "")
                if not old_name:
                    return {"ok": False,
                            "error": "这个文明里没有编号 %s 的单位" % (uid,)}
                # The model already holds this record's span; handing it in
                # instead of letting `records` re-walk the civilisation turns a
                # 4 s walk (measured on the last civ) into 0.02 s.
                span = next((u for u in civ["units"] if u.get("id") == uid), {})
                steps, info = REC.plan_rename_unit(
                    buf, gv, civs_start, civ_index, uid, new_name,
                    start=span.get("_start"), end=span.get("_end"))
                label = "重命名单位 %s 为「%s」" % (uid, new_name)
                note = {"unit": uid, "civ": civ.get("name"),
                        "civ_index": civ_index, "field": "Name",
                        "op": "rename", "label": label,
                        "was": NTX.readable(old_name), "now": new_name,
                        "unit_name": new_name}
        except REC.RecordError as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, ValueError):
            return {"ok": False, "error": "编号要填整数"}
        # A name that is already exactly this is not an edit.  Both sides go
        # through `readable` first: `stats` keeps the raw latin-1 view of the
        # bytes on disk, so a record renamed to 「织布机改」 reads back as
        # `ç»å¸æºæ¹`.  Feeding that straight into
        # `name_bytes` encodes it AGAIN (twice-encoded, 24 bytes for 12) and the
        # comparison says "changed" when nothing did -- measured 2026-11-06:
        # the second identical rename was accepted, grew the file by 4 bytes and
        # pushed an undo step that undid nothing.
        if REC.name_bytes(NTX.readable(old_name)) == REC.name_bytes(new_name):
            return {"ok": False,
                    "error": "名字没变，还是「%s」" % (NTX.readable(old_name),)}
        display_info = None
        if display:
            # EQUAL-WIDTH WRITES GO FIRST.  They move no byte, so the splice
            # offsets found above are still valid when the rename runs; the other
            # order would need every display offset re-shifted by hand.
            try:
                sid = self.new_string_id(new_name)
                spots = []
                if kind == "tech":
                    off = next((t.get("_off_lang_name") for i, t in
                                enumerate(tk._stats.get("techs") or [])
                                if i == int(record)), None)
                    if off is None:
                        off = REC._display_off(buf, gv, info["start"])
                    if off is not None:
                        spots.append((off, None))
                else:
                    uid = int(record)
                    for ci, cv in enumerate(tk._civs):
                        for u in cv.get("units") or ():
                            if u.get("id") == uid and u.get("_off_dll_name") is not None:
                                spots.append((u["_off_dll_name"], ci))
                extra = []
                for off, ci in spots:
                    step, sinfo = REC.string_id_step(buf, off, sid)
                    if step is not None:
                        extra.append(step)
                    display_info = dict(sinfo, string_id=sid, text=new_name,
                                        copies=len(spots))
                steps = extra + list(steps)
            except REC.RecordError as exc:
                return {"ok": False, "error": str(exc)}
            except Exception as exc:                       # noqa: BLE001
                return {"ok": False,
                        "error": "改显示名失败：%s: %s" % (type(exc).__name__, exc)}
        work, writes = REC.apply_steps(buf, steps, inplace=True)
        for w in writes:
            w["struct"] = True
            w["note"] = dict(note)
        self._hist_push(writes)
        self._sess_dirty = True
        self._sess_struct = True
        self._restructure(writes)
        self._after_rename(kind, info, civ_index)
        out = {"ok": True, "kind": kind, "info": info, "label": label,
               "was": NTX.readable(old_name), "now": new_name,
               "display": display_info, "record": int(record)}
        self._stamp_write(out)
        out["session_dirty"] = True
        out["bytes"] = len(self._sess)
        return out

    def _after_rename(self, kind, info, civ_index=0):
        """Make every cache agree with the new name.

        `_restructure` already re-walked the civ when the rename changed the
        record's width (a different length is a splice, and `relocate` re-walks
        the one civ the splice landed in).  When the new name has the SAME
        length there is no splice at all, `relocate` returns early, and the
        model would keep the old text -- so the walk and the cache drops happen
        here, unconditionally, and are idempotent when the fast path was taken.
        """
        tk = self.tk
        civs = getattr(tk, "_civs", None)
        if kind == "unit" and civs and 0 <= civ_index < len(civs):
            c = civs[civ_index]
            if c.get("_start") is not None and tk._parsed:
                REL.re_walk_civ(civs, tk._raw, tk._parsed[3], civ_index)
                REL.sync_stats_civ(tk._stats, civ_index, c)
        idx = getattr(tk, "_field_index", None)
        if kind == "unit" and idx:
            want = int(info.get("id"))
            for (ci, u), r in idx.items():
                if u == want:
                    r.pop("fields", None)
            sp = getattr(tk, "_civ_spread", None)
            if sp:
                sp.pop(want, None)
        # The same reason undo needs it: the display id was written into every
        # civ copy, and `relocate` re-walked only one of them.
        self._resync_display_ids()
        # The semantic index carries the display name and the families table is
        # built from the civ model -- both are pictures of the old text.
        tk._index = None
        tk._fam = None

    def _resync_display_ids(self):
        """Re-read every record's display-name id out of the buffer.

        A rename writes one id into each of the 63 civ copies; an undo writes
        all 63 back.  `relocate` re-walks only the civilisation the splice
        landed in, so the other copies would keep the id from before the undo
        and the name index -- which is built from this model -- would keep
        showing the name the file no longer contains.

        This is a flat pass over offsets the model already holds, not a walk:
        measured 2026-11-06, 136,861 records in 0.14 s.  It runs only when a
        history step actually touched a rename.
        """
        tk = self.tk
        civs = getattr(tk, "_civs", None)
        if not civs or not getattr(tk, "_parsed", None):
            return 0
        raw = self.session_raw(tk)
        n = len(raw)
        seen = 0
        for civ in civs:
            for u in civ.get("units") or ():
                off = u.get("_off_dll_name")
                if off is None or not (0 <= off <= n - 4):
                    continue
                sid = int.from_bytes(bytes(raw[off:off + 4]), "little",
                                    signed=True)
                if sid != u.get("_dll_name"):
                    u["_dll_name"] = sid
                    seen += 1
        for t in (getattr(tk, "_stats", None) or {}).get("techs") or ():
            off = t.get("_off_lang_name")
            if off is None or not (0 <= off <= n - 4):
                continue
            sid = int.from_bytes(bytes(raw[off:off + 4]), "little",
                                 signed=True)
            if sid != t.get("lang_name"):
                t["lang_name"] = sid
                seen += 1
        if seen:
            tk._index = None
            tk._fam = None
        return seen

    def record_edit(self, op, kind="unit", civ="", record=None, donor=None,
                    name=None, hp=None, force=False, count=None, ids=None,
                    donors=None, blank=False):
        """Add, duplicate or remove ONE record of the .dat.

        This is the write the editor never had: every other route edits a number
        inside a record that already exists, so the file's geometry never
        changed and the undo stack could be a list of equal-width byte swaps.
        Adding or removing a record moves everything after it, so the step is
        recorded with its own length and `_restructure()` rebuilds what the
        offsets were pointing at.

        `op` is "add" (empty donor -> the smallest free id), "dup" (donor is the
        record to copy) or "del".  `kind` is "unit" or "tech" -- two id spaces,
        and unit 22 and tech 22 are different records.

        `count` and `ids` are the bulk door: 1000 clones are ONE splice and ONE
        undo step.  Measured 2026-11-05 on the shipped file: a thousand records
        cost 0.037 s of byte work against 0.175 s for one, because the cost of a
        batch is the blob and not the count -- a thousand separate gestures would
        re-parse the whole 93 MB file a thousand times for the same bytes.
        """
        tk = self.tk
        op = str(op or "").strip().lower()
        kind = str(kind or "unit").strip().lower()
        if kind not in ("unit", "tech"):
            return {"ok": False, "error": "只能给单位或科技增删记录，没有 %r 这种记录空间" % (kind,)}
        if op not in ("add", "dup", "del"):
            return {"ok": False, "error": "记录操作只有 add / dup / del，收到的是 %r" % (op,)}
        if tk._parsed is None:
            tk._ensure()
        buf = self.session_raw()
        gv = tk._parsed[3]
        civs_start = tk._parsed[2]
        tail = tk._parsed[4]

        # Writes made BEFORE the shared `apply_steps` below (a multi-donor clone
        # has to plan against the buffer the previous clone produced).  None
        # means "nothing applied yet, run the plan at the bottom".
        wrote = None
        if kind == "tech":
            try:
                if op == "del":
                    steps, info = REC.plan_remove_tech(buf, gv, tail, int(record))
                    label = "删除科技 %s" % (info.get("id"),)
                    note = {"tech": info.get("id"), "field": None, "op": op,
                            "label": label, "was": None, "now": None,
                            "tech_name": info.get("name")}
                else:
                    donor_id = int(donor if donor is not None else record)
                    steps, info = REC.plan_add_tech(buf, gv, tail, donor_id,
                                                    lang_name=name)
                    label = "新增科技 %s" % (info.get("name"),)
                    note = {"tech": info.get("id"), "field": None, "op": op,
                            "label": label, "was": None, "now": info.get("id"),
                            "tech_name": info.get("name"),
                            "donor": donor_id, "name": name,
                            "create": "tech.create"}
            except REC.RecordError as exc:
                return {"ok": False, "error": str(exc)}
            refs = {"effects": 0, "civs": 0}
        else:
            # "*" is the FIELD-WRITE scope ("all 63 copies"), not an address: a
            # record is added to one civilisation's run, and cloning into all 63
            # is 63 records and 63 flag flips (schema says so for `unit.create`).
            # Reported 2026-11-05: the editor sends `edScopeCiv()`, so with
            # 全部文明 selected every duplicate failed with
            # 「科技树里的这个文明名（'*'）对不上 .dat 里的任何一条文明」.
            want = str(civ or "").strip()
            if want in ("*", "all", "全部"):
                want = ""
            civ_index = (tk._civ_index(want) if want
                         else (1 if len(tk._civs) > 1 else 0))
            civ_name = (tk._civs[civ_index].get("name") if civ_index < len(tk._civs)
                        else want)
            try:
                many = [int(i) for i in ids] if ids else None
                if op == "del":
                    if many:
                        # Delete every id the caller named, in one step.  The
                        # reference question is asked per id so the refusal can
                        # say WHICH one is still pointed at, not just "no".
                        hot = []
                        for uid in many:
                            refs = REC.unit_references(tk._stats, uid)
                            if refs["effects"] or refs["civs"] > 1:
                                hot.append((uid, refs))
                        if hot and not force:
                            uid, refs = hot[0]
                            return {"ok": False,
                                    "error": "%d 条里第 %d 号单位还被 %d 条效果命令和"
                                             "%d 份文明记录引用，删掉会让那些效果指向一个"
                                             "不存在的单位（确认要删就带上 force）"
                                             % (len(many), uid, refs["effects"],
                                                refs["civs"]),
                                    "references": refs, "blocked": [h[0] for h in hot]}
                        steps, info = REC.plan_remove_units(
                            buf, gv, civs_start, civ_index, many)
                        label = "删除单位 %s 等 %d 条" % (many[0], len(many))
                        note = {"unit": many[0], "civ": civ_name, "field": None,
                                "op": op, "label": label, "was": None,
                                "now": None, "unit_name": many[0],
                                "create": None, "ids": many}
                        refs = {"effects": 0, "civs": 1}
                    else:
                        uid = int(record)
                        refs = REC.unit_references(tk._stats, uid)
                        if (refs["effects"] or refs["civs"] > 1) and not force:
                            return {"ok": False,
                                    "error": "第 %d 号单位还被 %d 条效果命令和 %d 份文明记录引用，"
                                             "删掉会让那些效果指向一个不存在的单位"
                                             "（确认要删就带上 force）"
                                             % (uid, refs["effects"], refs["civs"]),
                                    "references": refs}
                        steps, info = REC.plan_remove_unit(buf, gv, civs_start,
                                                           civ_index, uid)
                        label = "删除单位 %s" % (uid,)
                        note = {"unit": uid, "civ": civ_name, "field": None,
                                "op": op, "label": label, "was": None, "now": None,
                                "unit_name": uid, "create": None}
                elif donors:
                    # One new record per donor, still ONE gesture: 粘贴 of a
                    # multi-row selection is the obvious way to ask for this, and
                    # the player expects the undo button to take back the paste
                    # rather than one row of it.
                    #
                    # Each clone plans against the buffer the previous one left,
                    # so the flag array grows once and every offset is real.  The
                    # writes come back in application order and 撤销 replays a
                    # structural step backwards, which is why accumulating them
                    # is enough to make the whole paste one step.
                    wrote = []
                    made = []
                    # Reserve the ids up front.  `plan_add_unit` derives a free
                    # id from `stats`, and `stats` is the file we started from —
                    # it never learns about the records this loop already made,
                    # so asking it four times in a row hands back the same id
                    # four times ("这个文明已经有编号 30000 的单位了").
                    want_ids = REC.free_unit_ids(tk._stats, len(donors))
                    # One gesture means one undo, which means a failure halfway
                    # through must not leave half a paste in the buffer: keep the
                    # bytes and put them back before the error travels up.
                    keep = bytes(buf)
                    try:
                        for i, did in enumerate([int(x) for x in donors]):
                            st, inf = REC.plan_add_unit(
                                buf, gv, civs_start, civ_index, did,
                                new_id=want_ids[i],
                                hp=(int(hp) if hp not in (None, "") else None),
                                stats=tk._stats)
                            _, w = REC.apply_steps(buf, st, inplace=True)
                            wrote.extend(w)
                            made.append(inf.get("id"))
                    except Exception:
                        buf[:] = keep
                        raise
                    info = {"ids": made, "count": len(made), "donor": made and
                            [int(x) for x in donors][0]}
                    label = "粘贴 %d 条记录" % (len(made),)
                    note = {"unit": made[0] if made else None, "civ": civ_name,
                            "field": None, "op": op, "label": label,
                            "was": None, "now": made[-1] if made else None,
                            "unit_name": None, "donor": None, "name": None,
                            "hp": None, "create": "unit.create", "ids": made}
                    refs = {"effects": 0, "civs": 1}
                elif blank:
                    # A record built from NOTHING.  Until now "add" only ever
                    # meant "copy": `plan_add_unit` refuses a donor that is not
                    # in this civ, and the route's own comment said so out loud
                    # ("a new record with no fields in it would be a hole the
                    # parser still has to walk").  It is not a hole: the reader
                    # decides which blocks a record has from its TYPE, so a type
                    # -70 record with every block written out at its minimum is
                    # a record the parser walks to the last byte -- which
                    # `newunit.blank_image` proves before it returns.
                    want = (int(count) if count not in (None, "") else None)
                    if many or (want is not None and want > 1):
                        steps, info = REC.plan_add_units(
                            buf, gv, civs_start, civ_index, None,
                            count=want, ids=many,
                            hp=(int(hp) if hp not in (None, "") else None),
                            stats=tk._stats, blank=True)
                        got = info.get("ids") or []
                        label = "新增空白单位 %d 条（%s..%s）" % (
                            len(got), got[0], got[-1])
                        note = {"unit": got[0] if got else None, "civ": civ_name,
                                "field": None, "op": op, "label": label,
                                "was": None, "now": got[-1] if got else None,
                                "unit_name": None, "donor": None,
                                "name": None, "hp": hp,
                                "create": "unit.create", "ids": got}
                        refs = {"effects": 0, "civs": 1}
                    else:
                        steps, info = REC.plan_add_unit(
                            buf, gv, civs_start, civ_index, None,
                            name=name,
                            hp=(int(hp) if hp not in (None, "") else None),
                            stats=tk._stats, blank=True)
                        label = "新增空白单位 %s" % (info.get("id"),)
                        note = {"unit": info.get("id"), "civ": civ_name,
                                "field": None, "op": op, "label": label,
                                "was": None, "now": info.get("id"),
                                "unit_name": name, "donor": None,
                                "name": name, "hp": hp,
                                "create": "unit.create"}
                        refs = {"effects": 0, "civs": 1}
                else:
                    donor_id = int(donor if donor is not None else record)
                    want = (int(count) if count not in (None, "") else None)
                    if many or (want is not None and want > 1):
                        # One splice for the whole batch: same flag write, one
                        # blob, one undo step.  10,000 clones measured 0.047 s.
                        steps, info = REC.plan_add_units(
                            buf, gv, civs_start, civ_index, donor_id,
                            count=want, ids=many,
                            hp=(int(hp) if hp not in (None, "") else None),
                            stats=tk._stats)
                        got = info.get("ids") or []
                        label = "复制单位 %s 成 %d 条（%s..%s）" % (
                            donor_id, len(got), got[0], got[-1])
                        note = {"unit": got[0] if got else None, "civ": civ_name,
                                "field": None, "op": op, "label": label,
                                "was": None, "now": got[-1] if got else None,
                                "unit_name": name, "donor": donor_id,
                                "name": name, "hp": hp,
                                "create": "unit.create", "ids": got}
                        refs = {"effects": 0, "civs": 1}
                    else:
                        steps, info = REC.plan_add_unit(
                            buf, gv, civs_start, civ_index, donor_id,
                            hp=(int(hp) if hp not in (None, "") else None),
                            stats=tk._stats)
                        label = "复制单位 %s 成 %s" % (donor_id, info.get("id"))
                        note = {"unit": info.get("id"), "civ": civ_name,
                                "field": None, "op": op, "label": label,
                                "was": None, "now": info.get("id"),
                                "unit_name": name, "donor": donor_id, "name": name,
                                "hp": hp, "create": "unit.create"}
                        refs = {"effects": 0, "civs": 1}
            except REC.RecordError as exc:
                return {"ok": False, "error": str(exc)}
            except (TypeError, ValueError):
                return {"ok": False, "error": "编号要填整数"}

        # One gesture, one step: the plan touches the flag array, its count and
        # the record run, and undoing half of that would leave a file the parser
        # cannot walk.
        if wrote is None:
            work, writes = REC.apply_steps(buf, steps, inplace=True)
        else:
            writes = wrote
        for w in writes:
            w["struct"] = True
            w["note"] = dict(note)
        self._hist_push(writes)
        self._sess_dirty = True
        self._sess_struct = True
        self._restructure(writes)
        out = {"ok": True, "op": op, "kind": kind, "info": info,
               "references": refs}
        self._stamp_write(out)
        out["session_dirty"] = True
        out["bytes"] = len(self._sess)
        return out

    def reset_session(self):
        # A structural step REPLACED `tk._raw` with the edited bytes (see
        # `_restructure`), so "start over" cannot just drop the buffer: the next
        # `session_raw()` would copy the edited file back and the player would
        # keep the record they just discarded.  Throwing the model away makes
        # `_ensure()` re-read the game's own file, which is the one true
        # baseline.
        self._gen_bump()
        if getattr(self, "_sess_struct", False):
            self._sess_struct = False
            tk0 = getattr(self, "tk", None)
            if tk0 is not None:
                tk0._parsed = None
                tk0._raw = None
                tk0._civs = None
                tk0._stats = None
                for name in ("_field_index", "_tech_field_index", "_effects",
                             "_civ_spread", "_tech_census", "_fam", "_index",
                             "_unit_lines"):
                    if hasattr(tk0, name):
                        setattr(tk0, name, None)
                for name in [k for k in list(vars(tk0)) if k.startswith("_table_index_")]:
                    setattr(tk0, name, None)
                self._vocab = None
                self._task_name_cache = {}
        self._sess = None
        self._sess_dirty = False
        self._edits = []
        # Forget which mod was last written.  The buffer has just been thrown
        # away, so the next 保存 starts from the ORIGINAL bytes: reusing the old
        # folder name would rebuild that mod out of a batch that no longer
        # contains the edits it was built from -- it would silently LOSE an
        # earlier edit rather than update it.  Same for a .dat switch, which
        # routes through here too.
        self._last_title = ""
        # 放弃 is the end of the road, not a step backwards: "start over" must
        # not leave a 撤回 button that walks back into the changes the player
        # just declared they did not want.
        self._hist = []
        self._hist_at = 0
        self._hist_group = None
        # KEEP THE INDEXES, DROP WHAT THEY CACHED.  Undo restores the original
        # bytes, which are the same 93 MB at the same offsets -- every record
        # start in `_field_index` is still correct, so throwing the index away
        # buys nothing and costs a full 11 s rescan on the very next 试算.
        # Measured 2026-10-30: after 撤销, the next dry run took 12.1 s; with
        # the index kept it takes 0.0 s.  Only the DECODED fields are stale,
        # because they hold the values the player just discarded.
        self._drop_decoded_fields(getattr(self.tk, "_field_index", None))
        # Same reasoning for the tech and the cross-civ census: offsets and
        # counts survive, the decoded numbers do not.
        self._drop_decoded_fields(getattr(self.tk, "_tech_field_index", None))
        self.tk._tech_census = None
        # The cross-civ histogram IS a picture of the bytes (value -> how many
        # copies store it), so every count in it is now wrong.  It costs 0.02 s
        # to rebuild, unlike the 11 s scan above.
        self.tk._civ_spread = None
        # The effect records are a THIRD cache of decoded numbers and they hold
        # the values a write just put there.  Unlike the two above they are not
        # indexed by record, so they are dropped rather than patched: 5 s is the
        # cost of the next preview, and 撤销 is a rare gesture compared to the
        # eight edits that lead up to it.  Measured 2026-11-01: without this,
        # 撤销 left 织布机 reading 100 and a probe reported the decoder broken.
        self.tk._effects = None
        # And the pictures: 放弃 means the whole session did not happen, so a
        # texture chosen two steps ago must not ride into the next build under
        # a table key nothing points at any more.
        self._icons = {}
        self._icon_slots = {}
        self._icon_owner = {}
        self._icon_items = []
        return {"ok": True, "dirty": False, "pending": 0}

    @staticmethod
    def _drop_decoded_fields(index):
        """Forget the decoded `fields` dict on every record of a kept index.

        Written out instead of `index = None` because a rescan is the expensive
        half of this route and none of it changes on undo.
        """
        if not index:
            return
        for rec in list(index.values()):
            if isinstance(rec, dict):
                rec.pop("fields", None)

    def pending_edits(self):
        return list(getattr(self, "_edits", None) or [])

    def session_intents(self):
        """The `intents` a build made from right now would record.

        WHY THIS IS A ROUTE AND NOT ONLY AN INTERNAL FOLD: it is the one thing a
        rebuild depends on and the one thing no screen showed.  Measured
        2026-10-31: eighteen recorded builds were unrebuildable because their
        `intents` were folded by a function nothing could inspect, and the fold
        had already drifted from the schema (it emitted `unit.field`, which the
        compiler refuses).  A probe can now compare it against the live schema
        without importing this file -- which matters because the shipped exe
        runs its OWN copy, so an importing probe would pass while the thing the
        player is running failed.
        """
        return {"ok": True, "pending": len(self.pending_edits()),
                "intents": [_intent_of(e) for e in self.pending_edits()]}

    def new_string_id(self, text):
        """Allocate (or reuse) a string id carrying ``text`` for this session.

        Reuse matters: renaming the same record twice in a row must not leave the
        first text as an orphan row and a second id pointing at the second --
        60 s of edits would ship 60 unused rows.  An id this session already
        created is reused and its text replaced in place.
        """
        text = str(text or "")
        for sid, have in self._new_strings.items():
            if have == text:
                return sid
        sid = S.first_free_id(self.tk.game_root)
        while sid in self._new_strings:
            sid += 1
        self._new_strings[sid] = text
        # The name index reads string TABLES, and this row is not in one yet --
        # it lands in the mod when the file is saved.  Tell the model, and drop
        # the index it built while the record still carried the old id, or the
        # pane keeps printing the old name over a file that no longer says it.
        self.tk._new_text[sid] = text
        self.tk._index = None
        return sid

    def string_files(self):
        """``{mod relative path: bytes}`` for the rows this session added."""
        if not self._new_strings:
            return {}
        entries = sorted(self._new_strings.items())
        return S.build_files(self.tk.game_root, entries)

    def save_session(self, title=None, keep=False, install=False):
        """Build ONE data mod carrying every pending edit.

        WHY THIS IS A SEPARATE ROUTE: the first draft rebuilt the whole 93 MB
        `.dat` on every accepted value -- measured 27-28 s each, so eight edits
        took four minutes and the player could not tell whether the tool had
        hung.  AGE edits in memory and writes once.  Here: `field-set` touches
        memory only, and this route writes the buffer once, re-parses the file
        it produced and records provenance for the whole batch.

        WHY IT INSTALLS BY DEFAULT: asked 2026-11-09, verbatim 「要不你都改成默认
        放入 local 里吧」.  Before this the only way into `mods/local` was the
        主页's 生成并安装 button, so a player editing in 编辑器 saved a folder
        into `_mods_out/` and then had to go find another button -- and the
        folder they had already built was invisible to the game.  Installing is
        the same `install_mod(..., overwrite=True)` the build route uses, so a
        repeat save replaces `mods/local/<title>` instead of piling up copies.
        The DEFAULT here is `install=False` even though the route passes
        `True`: every caller of this method today is a probe, and a probe that
        copies 11.5 MB into the player's real mod list is the exact mistake
        `find_profile_root` documents at length.  The route decides, the method
        obeys.
        """
        tk = self.tk
        tk._ensure()
        edits = self.pending_edits()
        if not edits:
            return {"ok": False, "error": "还没有任何改动，不用保存"}
        import os as _os
        import hashlib
        from aoe2mod.mod import emitter as E
        from aoe2mod.mod import provenance as PV
        from aoe2mod.dat import parser as _P
        if title:
            name = title
        elif self._last_title:
            # Same session, same mod: 保存 must overwrite what the last 保存
            # wrote, not invent a second folder from this batch's first edit.
            name = self._last_title
        elif len(edits) == 1:
            e = edits[0]
            name = "%s %s" % (_subject_of(e), e.get("label", e.get("field")))
        else:
            name = "%s %s 等 %d 项" % (_subject_of(edits[0]),
                                       edits[0].get("label", edits[0].get("field")),
                                       len(edits))
        desc = "；".join("%s %s：%s → %s" % (
            e.get("label", e.get("field")), _subject_of(e), e.get("was"),
            e.get("now"))
            for e in edits[:12])
        info = E.make_info(name, author="aoe2mod", description=desc)
        mod_dir = _os.path.join(_out_root(), _safe_dir(info["Title"]))
        # The string table rides along: a rename that only changed the .dat
        # would point LanguageDLLName at an id no table defines, and the game
        # would show the raw number where the name should be.
        string_files = self.string_files()
        # Pictures ride along with the strings, in ONE `json_files` map: the
        # emitter writes that map into the mod verbatim, so two calls would
        # mean one of the two layers silently winning.  Measured 2026-11-06:
        # a session with both a rename and a new icon needs four extra files
        # (17 locale tables plus the two merged icon tables and one texture).
        _extra = dict(string_files or {})
        _extra.update(self._icons or {})
        self._last_title = info["Title"]
        man = E.emit_data_mod(mod_dir, bytes(self._sess), info,
                              base_dir=tk.game_root, overwrite=True,
                              json_files=_extra or None)
        raw2, how2 = _P.load_dat(man["dat"])
        p2 = _P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            p2.parse()
        out = {"ok": True, "built": man["mod_dir"],
               "dat_bytes": man.get("dat_file_bytes"),
               "reloaded_with": how2,
               "reparse_ok": p2.r.pos == len(raw2),
               "applied": len(edits),
               # An icon build is TWO mod folders, not one: the engine ignores
               # `widgetui/` sitting next to a `.dat` (measured 2026-10-24,
               # eleven builds empty and one split build drawing), so the
               # emitter moves that layer into `<title>_ui`.  The page has to
               # say so, because enabling only the data half reproduces the
               # exact empty box this feature exists to fix.  Passing the
               # manifest's own keys through rather than rebuilding them keeps
               # one source of truth for what landed on disk.
               "info": man.get("info"),
               "ui_mod_dir": man.get("ui_mod_dir"),
               "ui_info": man.get("ui_info"),
               "ui_files": man.get("ui_files"),
               "warnings": man.get("warnings") or [],
               "notes": man.get("notes") or [],
               "edits": [{"unit": e.get("unit"), "tech": e.get("tech"),
                          "field": e.get("field"), "label": e.get("label"),
                          "was": e.get("was"), "now": e.get("now")}
                         for e in edits]}
        try:
            entry = PV.entry_from_manifest(
                man, tk.dat_path,
                base_raw_sha256=hashlib.sha256(tk._raw).hexdigest(),
                intents=[_intent_of(e) for e in edits],
                target_version=tk.version)
            PV.record(entry)
            out["provenance"] = {"title": entry["title"]}
        except Exception as exc:                        # noqa: BLE001
            out["provenance"] = {"why_not": "%s: %s" % (type(exc).__name__, exc)}
        # 保存 puts it where the game reads it.  Same call the 生成并安装 button
        # makes (`App.install` -> `install_mod(overwrite=True)`), so a second
        # 保存 with the same title REPLACES `mods/local/<title>` instead of
        # leaving the older copy behind at a lower priority.
        #
        # A failed install must not throw the build away: the folder in
        # `_mods_out/` is complete and re-installable, and a player who hit a
        # locked profile (game running, antivirus holding the folder) deserves
        # the path plus the reason rather than a red toast that hides a good
        # build.
        if install:
            try:
                got = self.install(man["mod_dir"],
                                   name=(man.get("info") or {}).get("Title")
                                   or info["Title"],
                                   enabled=True, position=0)
                out["installed"] = got.get("installed") or {}
                meta = out["installed"] or {}
                out["install_error"] = meta.get("error") if meta.get("ok") is False else ""
            except Exception as exc:                    # noqa: BLE001
                out["installed"] = {}
                out["install_error"] = "%s: %s" % (type(exc).__name__, exc)
        # The edits are on disk now; start a fresh session on the SAME buffer so
        # the pane keeps showing what the player just built (re-reading the game
        # file would silently revert every value on screen).
        #
        # WHY THE EDITS ARE CLEARED: a second press of the same button must not
        # rebuild the same mod over its own output (measured: it succeeded, and
        # the folder was replaced mid-install).  另存为 is a different promise --
        # the caller asked for a SECOND copy of the same batch under another
        # name, so it passes `keep` and the pending list survives.
        if not keep:
            self._edits = []
            # The batch is now a mod on disk.  Keeping the history would let a
            # later 撤回 edit bytes that the build has already written out, and
            # the header would disagree with the folder it just produced.
            self._hist = []
            self._hist_at = 0
        return out

    def session_info(self):
        """What the header needs: how many edits are pending, and what they are.

        NO HOOK DIAGNOSTICS HERE.  A first draft also echoed
        `parser.read_unit.__name__` to prove the record/parse hooks were
        restored.  It reported `rec_unit` on a cold start and I chased a
        phantom: `/api/session-info` was reading the name while ANOTHER thread
        sat inside `scan()`'s patch window, which is exactly the window the
        lock exists to keep other threads out of -- a sampling race, not a leak.
        The real proof that nothing leaked is that a batch of edits survives
        `save_session` and re-parses, which `POST /api/session-save` reports.
        """
        self.session_raw()
        hist = self.hist_state()
        return {"ok": True, "dirty": self.session_dirty,
                "bytes": len(self._sess),
                "pending": len(self.pending_edits()),
                # Which mod 保存 will write into.  Empty until the first save.
                # The page puts this in the name box so the player can see that
                # saving again updates that mod instead of making another one.
                "target": self._last_title,
                # How many steps each way, so the 撤回/重做 buttons can be
                # disabled instead of failing when pressed.
                "undo": hist["undo"], "redo": hist["redo"],
                "undo_label": hist["undo_label"],
                "redo_label": hist["redo_label"],
                # `civ_all` and `copies` are here because the header prints a
                # COUNT: "已改 1 项" is true for a one-civilization edit and for a
                # 63-record blanket edit, and the player cannot tell which of the
                # two they queued up.  Echoing the flag lets the header say so.
                "edits": [{"unit": e.get("unit"), "tech": e.get("tech"),
                           "subject": _subject_of(e),
                           "label": e.get("label"),
                           "was": e.get("was"), "now": e.get("now"),
                           "civ": e.get("civ"),
                           "civ_all": bool(e.get("civ_all")),
                           "copies": e.get("copies")}
                          for e in self.pending_edits()]}

    def _index_from_model(self, tk, raw):
        """`{...}` from `tk._civs`, or None when the model cannot vouch for it.

        Every entry carries the same five keys `unitfields.scan` produces:
        `start`, `end`, `type`, `civ_index` and `civ`, and `civ` is the civ's
        NAME (a string), because that is what `scan`'s `rec_civ` puts there and
        what the table views print.

        Returning None means "scan instead": the model predates the `_start`
        bookkeeping, belongs to different bytes, or does not close into one
        unbroken stream from `civs_start` to the tail.
        """
        from aoe2mod.dat import relocate as REL
        civs = getattr(tk, "_civs", None)
        parsed = getattr(tk, "_parsed", None)
        if not civs or not parsed:
            return None
        if len(raw) != len(getattr(tk, "_raw", b"") or b""):
            return None
        for c in civs:
            if c.get("_start") is None or c.get("_end") is None:
                return None
            for u in c["units"]:
                if u.get("_start") is None or u.get("_end") is None:
                    return None
        if not REL.chain_ok(civs, parsed[2], parsed[4]):
            return None
        idx = {}
        for ci, c in enumerate(civs):
            name = c.get("name")
            for u in c["units"]:
                idx[(ci, u["id"])] = {"start": u["_start"], "end": u["_end"],
                                      "type": u["type"], "civ_index": ci,
                                      "civ": name}
        return idx

    def _unit_index(self, _tries=0):
        """`{(civ_index, unit_id): record}` for every unit in the .dat.

        WHY NOT RE-SCAN PER REQUEST: `scan()` walks 93 MB and takes ~7 s.  The
        whole point of the field editor is that a player opens a unit, changes
        eight numbers and saves -- eight requests.  Paying 7 s each time makes
        the feature feel broken even though it is correct, so the index is
        built once per Toolkit and cached on it.
        """
        tk = self.tk
        cached = getattr(tk, "_field_index", None)
        if cached is not None:
            return cached
        from aoe2mod.dat import unitfields as UF
        tk._ensure()
        # Scan the EDITED buffer when one exists.  Every field offset is resolved
        # from the bytes being described, so describing the game's original file
        # after a write would show the old value and, worse, hand out offsets that
        # no longer match the buffer the next write is applied to.
        #
        # LIGHT MODE, AND THE RECORD IS NOT CACHED.  A first version kept the
        # decoded dict-of-dicts for all 136,861 records as this index: 434 field
        # dicts each, measured 12.3 GB resident on 2026-10-30 -- the process was
        # minutes from being killed by the OS.  The index now holds only where
        # each record starts; `unit_fields()` decodes one record on demand
        # (0.2 ms) and `set_unit_field()` does the same.
        units = None
        # Announce the job BEFORE the scan so a page that polls immediately sees
        # "running" instead of nothing.  Measured 2026-11-02: this scan is 14.52 s
        # cold (136,861 records) and 0.003 s warm, so only the cold path has a bar
        # worth drawing -- `begin()` here and `snapshot()` tells the page which.
        from aoe2mod import jobs as J
        # One `tk` for the scan and the bytes: see `session_raw`'s `tk` argument
        # for the EOFError this prevents.
        raw = self.session_raw(tk)
        gen = self._gen
        # FAST PATH FIRST.  The model already knows where every record starts;
        # walking the bytes a second time to learn the same thing costs 10.43 s
        # against 0.17 s (measured 2026-11-06).  `_index_from_model` returns
        # None unless `chain_ok` reproduces the guarantee `scan`'s zero leftover
        # used to provide, so the slow path stays as the fallback.
        fast = self._index_from_model(tk, raw)
        if fast is not None:
            if gen != self._gen:
                if _tries >= 3:
                    raise RuntimeError("单位索引在扫描期间被改动了 %d 次，没能赶上一份稳定的数据，"
                                       "请稍后再试" % (_tries,))
                return self._unit_index(_tries + 1)
            tk._field_index = fast
            return fast
        J.begin("unit", "建立单位字段索引", len(raw))
        try:
            units, _stats, leftover = UF.scan(raw, tk._parsed[3],
                                              light=True,
                                              on_progress=_scan_reporter("unit"))
        except Exception as exc:
            J.fail("unit", "%s: %s" % (type(exc).__name__, exc))
            raise
        J.finish("unit")
        if leftover:
            # A non-zero leftover means the recorded offsets are NOT the offsets
            # the parser would walk, so every write below would land in the wrong
            # field.  Refuse rather than offer a form that silently corrupts.
            raise RuntimeError(
                "字段扫描没有走完整个文件（还剩 %d 字节），说明记录的字段地址不可信，"
                "这时候让你编辑会写进隔壁字段。" % (leftover,))
        idx = {}
        for u in units:
            idx[(u["civ_index"], u["id"])] = {"start": u["start"], "end": u["end"],
                                             "type": u["type"],
                                             "civ_index": u["civ_index"],
                                             "civ": u["civ"]}
        if gen != self._gen:
            # The buffer moved while this scan was walking it: these offsets
            # belong to a file that is gone.  Scan again rather than cache them
            # -- but only a few times, because an edit loop is not a reason to
            # spin here forever.
            if _tries >= 3:
                raise RuntimeError("单位索引在扫描期间被改动了 %d 次，没能赶上一份稳定的数据，"
                                   "请稍后再试" % (_tries,))
            return self._unit_index(_tries + 1)
        tk._field_index = idx
        return idx

    def _fields_of(self, rec, tk=None):
        """Decode one record's named fields out of the live session buffer.

        ``tk`` pins the read to the toolkit that produced ``rec["start"]``: a
        record located in a mod's file must not be decoded out of the game's
        file, which is a shorter stream and raises `EOFError` from the reader.
        """
        from aoe2mod.dat import unitfields as UF
        tk = tk if tk is not None else self.tk
        raw = self.session_raw(tk)
        f = UF.fields_at(raw, tk._parsed[3], rec["start"])
        rec["fields"] = f
        return f

    def _civ_spread(self, uid):
        """`{field: {value: how many copies store it}}` for one unit id.

        WHY THIS IS WORTH 13 ms OF DECODING PER UNIT: the `.dat` stores one unit
        record per civilisation and a field write lands in exactly one of them.
        Measured on the retail file: unit 74 has 424 of its 434 fields byte-identical
        in all 63 copies, unit 8 has all 400, unit 83 has 1013 of 1077.  So for
        the overwhelming majority of fields there is no single "the villager's
        hit points" -- there are 63 copies that had better stay equal, and a tool
        that edits one of them reports success for a change 62 civilisations do
        not have.  AGE has the same hole; the sentence path here does not (「村民
        生命值改成1000」 compiles to 63 records), so the field editor agreeing with
        the sentence path is also a consistency fix, not a new idea.

        The 10-ish fields that DO vary are content, not gameplay: the six newest
        civilisations carry their own `LanguageDLLName`, `IconID`,
        `StandingGraphic.0`, `DyingGraphic`.  Overwriting those blind would make
        six civilisations share one civilisation's icon, so `set_unit_field` uses
        this histogram to refuse a blanket write that would flatten those.

        Keyed by VALUE, not by a precomputed "agrees?" flag: the pane shows the
        REFERENCE civilisation's numbers, so whether a field is shared has to be
        answered against that value, not against the most common one.
        """
        tk = self.tk
        cache = getattr(tk, "_civ_spread", None)
        if cache is None:
            cache = tk._civ_spread = {}
        got = cache.get(uid)
        if got is not None:
            return got
        from aoe2mod.dat import unitfields as UF
        tk._ensure()
        raw = self.session_raw()
        stage = tk._parsed[3]
        idx = self._unit_index()
        seen = {}
        copies = 0
        for (ci, u), rec in idx.items():
            if u != uid:
                continue
            copies += 1
            for name, d in UF.fields_at(raw, stage, rec["start"]).items():
                slot = seen.setdefault(name, {})
                slot[d["value"]] = slot.get(d["value"], 0) + 1
        # `copies` rides along under a private key so the caller does not have to
        # sum 434 histograms to answer "out of how many".
        seen["__copies__"] = copies
        cache[uid] = seen
        return seen

    def unit_fields(self, unit, civ="", group="", q=""):
        """Every field of one unit, labelled, grouped and ranged for a form.

        `unit` is the id; `civ` picks which civilisation's copy of the record
        (the .dat stores one per civ -- editing British's 村民 does not touch
        French's, which is why `unit.stat` has a civ argument at all).

        `group` filters to one of `fieldlabels.GROUPS`; `q` filters by label or
        technical name.  Both are server-side because the page only ships the
        rows it draws -- 190 rows x 63 civs is not something to hand the browser
        whole.
        """
        from aoe2mod.game import fieldlabels as FL
        tk = self.tk
        tk._ensure()
        civs = tk._civs
        # `civ="*"` means "every civilisation, changed together".  The pane still
        # has to show ONE set of numbers, so it reads the reference civilisation's
        # copy and marks the fields where the 63 copies disagree -- see
        # `_civ_spread`.  Without this the editor silently edited one of 63
        # records: measured, unit 74 carries 424 of its 434 fields identically in
        # all 63 copies, so writing "British's" HitPoints leaves a French player
        # with the old value while the tool reports success.
        want = str(civ or "").strip()
        civ_all = want == "*"
        civ_index = (1 if len(civs) > 1 else 0) if (civ_all or not want) else (
            tk._civ_index(want))
        try:
            uid = int(unit)
        except (TypeError, ValueError):
            return {"ok": False, "error": "单位编号要是数字，收到的是 %r" % (unit,)}
        rec = self._unit_index().get((civ_index, uid))
        if rec is None:
            return {"ok": False,
                    "error": "「%s」这个文明里没有第 %d 号单位" % (
                        civs[civ_index].get("name"), uid)}
        allf = rec.get("fields") or self._fields_of(rec)
        e = self._semantic().units.get(uid)
        name = (e.zh or e.en or e.display) if e is not None else ""
        rows = []
        for fname, f in allf.items():
            meta = FL.meta_for(fname)
            grp = meta.get("group", "misc")
            if group and grp != group:
                continue
            label = meta.get("zh") or fname
            if q and (q not in label and q.lower() not in fname.lower()):
                continue
            row = {"name": fname, "label": label, "group": grp,
                   "group_zh": FL.GROUP_ZH.get(grp, grp),
                   "kind": f["kind"], "value": f["value"],
                   "offset": f["offset"]}
            for k in ("lo", "hi", "step", "hint"):
                if k in meta:
                    row[k] = meta[k]
            if "enum" in meta:
                # Only send the mapping for the value actually stored plus the
                # whole table when it is small (classes are 59, bools are 2).
                row["enum"] = {str(k): v for k, v in meta["enum"].items()}
                row["enum_text"] = meta["enum"].get(f["value"])
            if meta.get("ro"):
                row["ro"] = True
            rows.append(row)
        # Sort by BYTE OFFSET, not by name.  The offsets already are the struct
        # order, so repeated members (`Attacks.0..N`) stay adjacent for free --
        # a name sort puts `Attacks.10` before `Attacks.2` and reads as random.
        # Grouping is done by `group` on the client, which keeps one screen per
        # concern without hiding the layout.
        rows.sort(key=lambda r: r["offset"])
        # How many of the 63 copies agree with the number just shown.  Computed
        # once per unit (13 ms) and only for the rows actually shipped, so a
        # group filter costs nothing extra.
        spread = self._civ_spread(uid) if len(civs) > 1 else None
        copies = (spread or {}).get("__copies__", 0)
        if spread:
            for r in rows:
                hist = spread.get(r["name"]) or {}
                mine = hist.get(r["value"], 0)
                if copies and len(hist) > 1:
                    r["copies"] = copies
                    r["agrees"] = mine
                    if mine < copies:
                        r["differs"] = copies - mine
        # The enum-ish task columns ship a range ("0..255") and a hint that
        # lists four of the values.  Ask the file which values exist and how
        # often, so the form can offer them instead of asking for a number.
        if any((r.get("group") == "task") for r in rows):
            census = self._field_census()
            for r in rows:
                tail = r["name"].rsplit(".", 1)[-1]
                c = census.get(tail)
                if c and r["name"].count(".") >= 2:
                    r["seen"] = {str(k): v for k, v in c.items()}
                    r["seen_names"] = {
                        str(k): FL.value_name(tail, k) or ("#%s" % k)
                        for k in c}
        groups = []
        for gid, gzh in FL.GROUPS:
            n = sum(1 for r in allf if FL.group_of(r) == gid)
            if n:
                groups.append({"id": gid, "zh": gzh, "count": n})
        return {"ok": True, "unit": uid, "name": name,
                "civ": civs[civ_index].get("name"),
                # The same civilization in Chinese.  `civ` stays the .dat
                # spelling because it is what every API call takes back; the
                # screen prints this one (measured 2026-11-02: the pane said
                # 「只改 British」 -- an English word in a Chinese tool).
                "civ_zh": _civ_zh_of(self.tk, civs[civ_index].get("name")),
                "civ_index": civ_index,
                "civ_all": civ_all, "civ_copies": copies,
                "type": rec["type"], "start": rec["start"], "end": rec["end"],
                "bytes": rec["end"] - rec["start"],
                "field_count": len(allf),
                "groups": groups, "fields": rows,
                "shown": len(rows)}

    def _field_census(self):
        """Which integers does the shipped data actually store, per field tail?

        WHY NOT A HAND-WRITTEN ENUM TABLE: `fieldlabels` can say "TaskType 0 无、
        1 移动、3 驻守" from reading genieutils, but it cannot say what the 63-civ
        retail file contains, and a player typing 42 into TaskType gets a silent
        no-op.  AGE has the same hole and answers it with a text box.

        The file is the authority, so the census reads it: every distinct value
        of every `*.Tasks.*` enum-ish column across every record, with a count.
        Scanned once per Toolkit and cached -- 136,861 records x 434 fields is
        30 s of decoding, and the answer never changes inside one session.

        `light=True` + `fields_at` per record start, exactly like `_unit_index`,
        because the dict-of-dicts form of this measured 12.3 GB.
        """
        tk = self.tk
        cached = getattr(tk, "_field_census", None)
        if cached is not None:
            return cached
        from aoe2mod.dat import unitfields as UF
        idx = self._unit_index()
        raw = self.session_raw()
        stage = tk._parsed[3]
        seen = {}
        for rec in list(idx.values())[:_CENSUS_CAP]:
            for name, f in UF.fields_at(raw, stage, rec["start"]).items():
                if ".Tasks." not in name or not name.endswith(_CENSUS_TAILS):
                    continue
                tail = name.rsplit(".", 1)[-1]
                seen.setdefault(tail, {})
                v = f["value"]
                if isinstance(v, float):
                    continue
                seen[tail][v] = seen[tail].get(v, 0) + 1
        out = {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0])))
               for k, v in seen.items()}
        tk._field_census = out
        return out

    def set_unit_field(self, unit, name, value, civ="", dry=True, title=None):
        """Write one field.  `dry` echoes the bytes that would change.

        THREE REFUSALS, each of which is a way to lose an edit while reporting
        success (the same class of failure the card-move route guards):

          * a name that is not in this record -- there is no "close enough"
            field, and a typo must not resolve to a neighbour;
          * a value outside the field's own byte width -- the struct layout is
            fixed, so an i16 of 70000 is not a clamp, it is two fields and a
            corrupted record;
          * a read-only field (a length prefix, a count that the list itself
            defines).  Writing those is how a 93 MB file becomes unloadable.

        `dry=False` rebuilds the mod through the same emitter every other edit
        path uses, so the shipping story is identical.
        """
        from aoe2mod.game import fieldlabels as FL
        tk = self.tk
        tk._ensure()
        civs = tk._civs
        # `civ="*"` = write every civilisation's copy of this unit.  See
        # `unit_fields` for why one copy is the wrong default.
        want = str(civ or "").strip()
        civ_all = want == "*"
        civ_index = (1 if len(civs) > 1 else 0) if (civ_all or not want) else (
            tk._civ_index(want))
        rec = self._unit_index().get((civ_index, int(unit))) if str(unit).lstrip(
            "-").isdigit() else None
        if rec is None:
            return {"ok": False, "error": "这个文明里没有第 %s 号单位" % (unit,)}
        _flds = self._fields_of(rec)
        f = _flds.get(name)
        if f is None:
            close = [k for k in _flds if name.lower() in k.lower()][:6]
            return {"ok": False,
                    "error": "这条记录里没有叫 %s 的字段" % (name,),
                    "did_you_mean": close}
        meta = FL.meta_for(name)
        if meta.get("ro"):
            return {"ok": False,
                    "error": "「%s」是只读的：%s" % (meta.get("zh", name),
                                                  meta.get("hint")
                                                  or "它的值由数据本身决定，改了会让整条记录读不下去。")}
        kind = f["kind"]
        old = f["value"]
        try:
            if kind == "f32":
                new = float(value)
            elif kind.startswith("u"):
                new = int(value)
            else:
                new = int(value)
        except (TypeError, ValueError):
            return {"ok": False, "error": "%s 要填%s，收到的是 %r" % (
                meta.get("zh", name),
                "小数" if kind == "f32" else "整数", value)}
        lo, hi = None, None
        # Byte width first: this is the hard wall the struct layout imposes.
        W = {"u8": (0, 255), "u16": (0, 65535), "i16": (-32768, 32767),
             "i32": (-2147483648, 2147483647), "u32": (0, 4294967295),
             "f32": (-3.4e38, 3.4e38)}.get(kind)
        if W and not (W[0] <= new <= W[1]):
            return {"ok": False,
                    "error": "「%s」在文件里只占 %s，装不下 %s（范围 %s..%s）" % (
                        meta.get("zh", name), kind, new, W[0], W[1])}
        # Then the sane range: advice, but checked, because a HitPoints of -3 is
        # a crash you can only diagnose by reading the file back.
        if "lo" in meta and new < meta["lo"]:
            return {"ok": False,
                    "error": "%s 不能小于 %s（%s）" % (
                        meta.get("zh", name), meta["lo"],
                        meta.get("hint") or "这是引擎里合理的下限")}
        if "hi" in meta and new > meta["hi"]:
            return {"ok": False,
                    "error": "%s 不能大于 %s（%s）" % (
                        meta.get("zh", name), meta["hi"],
                        meta.get("hint") or "这是引擎里合理的上限")}
        import struct
        fmt = {"u8": "<B", "u16": "<H", "i16": "<h", "i32": "<i", "u32": "<I",
               "f32": "<f"}[kind]
        packed = struct.pack(fmt, new)
        base = self.session_raw()
        # WHICH COPIES THIS WRITE TOUCHES.  Resolved by NAME per record, never by
        # reusing the reference copy's offset: two civilisations can lay the same
        # unit out differently (measured: British's 民兵 record is 2166 records'
        # worth of table, Gaia's is 2693), so an offset that is right in one copy
        # is a different field in another.
        if civ_all and len(civs) > 1:
            from aoe2mod.dat import unitfields as UF
            stage = tk._parsed[3]
            targets = []
            for (ci, u), r in self._unit_index().items():
                if u != int(unit):
                    continue
                fr = UF.fields_at(base, stage, r["start"]).get(name)
                if fr is None:
                    continue
                targets.append({"civ": civs[ci].get("name") if 0 <= ci < len(civs)
                                else str(ci),
                                "civ_index": ci, "offset": fr["offset"],
                                "old": fr["value"]})
            targets.sort(key=lambda t: t["civ_index"])
        else:
            targets = [{"civ": civs[civ_index].get("name"),
                        "civ_index": civ_index, "offset": f["offset"],
                        "old": old}]
        # "值没变" is answered against EVERY copy being written: with 63 copies,
        # one of them already holding the value is not a reason to refuse -- the
        # other 62 not holding it is the reason to go.
        stale = [t for t in targets if t["old"] != new]
        if not stale:
            return {"ok": False,
                    "error": ("全部 %d 个文明都已经是 %s 了" % (len(targets), new)
                              if len(targets) > 1 else "值没变，还是 %s" % (old,))}
        # Diff only the bytes each field occupies.  Comparing whole 93 MB buffers
        # per edit (the first draft did) took ~0.4 s and allocated two copies;
        # a field is 1..4 bytes, so this IS the diff.
        for t in targets:
            before = bytes(base[t["offset"]:t["offset"] + len(packed)])
            t["changed"] = sum(1 for a, b in zip(before, packed) if a != b)
            t["bytes_before"] = before.hex()
        changed = sum(1 for t in targets if t["changed"])
        out = {"ok": True, "unit": int(unit),
               "civ": (civs[civ_index].get("name") if not civ_all else
                       "全部 %d 个文明" % (len(targets),)),
               "civ_all": bool(civ_all), "copies": len(targets),
               "copies_changing": changed,
               "field": name, "label": meta.get("zh", name), "kind": kind,
               "offset": targets[0]["offset"], "before": old, "value": new,
               "bytes_before": targets[0]["bytes_before"],
               "bytes_after": packed.hex(),
               # `bytes_changed` stays the REFERENCE copy's byte diff so every
               # existing caller keeps one meaning; how many records move is
               # `copies_changing`, which is a different question and gets its
               # own key rather than overloading this one.
               "bytes_changed": targets[0]["changed"],
               "changes_dat": changed > 0}
        if len(targets) > 1:
            # What the player is actually doing, in one sentence: "63 copies, 57
            # of them move from 40 to 1000, 6 already had 1000".
            same = [t["civ"] for t in targets if t["old"] == new]
            out["already"] = same
            out["older"] = sorted({t["old"] for t in stale})
        if dry or not changed:
            out["dry"] = True
            out["session_dirty"] = self.session_dirty
            out["pending"] = len(self.pending_edits())
            return out
        # MEMORY ONLY.  The first draft rebuilt the whole 93 MB `.dat` here --
        # measured 27-28 s per accepted value, so eight edits took four minutes
        # and a batch of edits could not be made at all.  AGE edits in memory
        # and writes once; so does this: the value lands in the session buffer,
        # the header counts it, and `POST /api/session-save` builds one mod.
        _nm = _flds.get("Name")
        note = {"civ": (civs[civ_index].get("name") if not civ_all else "*"),
                "civ_all": bool(civ_all), "copies": len(targets),
                "unit": int(unit),
                "unit_name": (_nm or {}).get("value") or "",
                "field": name, "label": meta.get("zh", name),
                "was": old, "now": new,
                "kind": kind, "offset": targets[0]["offset"]}
        # ONE pending row for the whole group.  63 rows in the header for one
        # decision is noise, and `_intent_of` carries `civ_all` so the rebuild
        # replay re-expands it.
        # ONE undo step for the whole group, for the same reason: sixty-three
        # presses of 撤回 to take back one decision is not an undo.
        self._hist_begin()
        first = True
        for t in targets:
            if not t["changed"]:
                continue
            self._session_edit(t["offset"], packed,
                               note=note if first else None, hold=True)
            first = False
        self._hist_commit()
        # `_session_edit` only drops the decode cache for the civ it was told
        # about; a blanket write staled all of them, so clear the lot -- including
        # the cross-civ histogram, which is now a picture of the old file.
        idx = getattr(tk, "_field_index", None)
        if idx:
            for (ci, u), r in idx.items():
                if u == int(unit):
                    r.pop("fields", None)
        sp = getattr(tk, "_civ_spread", None)
        if sp:
            sp.pop(int(unit), None)
        self._stamp_write(out)
        out["hint"] = "已记在内存里，改完点「保存成 mod」一次写盘"
        return out

    # ---- technologies ----------------------------------------------------
    #
    # WHY A SECOND FIELD EDITOR INSTEAD OF ONE GENERIC TABLE
    # -----------------------------------------------------
    # A technology has 34 fields, a unit has up to 434, and 5 of the tech fields
    # mean something the unit ones never do: they point at ANOTHER object
    # (`EffectID` -> an effect, `Civ` -> a civilisation, `ResearchLocations.N.
    # LocationID` -> a building, `RequiredTechs.N` -> another technology).  AGE
    # prints all five as bare integers, so "make 织布机 researchable at the 兵营"
    # becomes "type 12 into ResearchLocations.0.LocationID and hope".
    #
    # The column census below is the other half: it reads the shipped file and
    # reports which values those columns actually hold, with their Chinese names
    # and how many records use each.  So the page can offer 兵营 (12) instead of
    # asking for a number, and it can also say "no record stores 7" before the
    # player writes a value that would silently do nothing.

    def _tech_index(self, _tries=0):
        """`{tech_index: {"start","end"}}`, cached on the Toolkit.

        Same shape and same reason as `_unit_index`: `techfields.scan()` walks
        93 MB (measured 6.5 s light) and the panel opens one technology at a
        time, so the walk happens once and each record is decoded on demand
        (0.03 ms).
        """
        tk = self.tk
        cached = getattr(tk, "_tech_field_index", None)
        if cached is not None:
            return cached
        from aoe2mod.dat import techfields as TF
        tk._ensure()
        # Same announcement as `_unit_index`: measured 12.32 s cold, 0.001 s warm.
        from aoe2mod import jobs as J
        raw = self.session_raw(tk)
        gen = self._gen
        J.begin("tech", "建立科技字段索引", len(raw))
        try:
            techs, _stats, leftover = TF.scan(raw, tk._parsed[3], light=True,
                                              on_progress=_scan_reporter("tech"))
        except Exception as exc:
            J.fail("tech", "%s: %s" % (type(exc).__name__, exc))
            raise
        J.finish("tech")
        if leftover:
            raise RuntimeError(
                "科技扫描没有走完整个文件（还剩 %d 字节），说明记录的字段地址不可信，"
                "这时候让你编辑会写进隔壁字段。" % (leftover,))
        idx = {t["index"]: {"start": t["start"], "end": t["end"],
                            "index": t["index"]} for t in techs}
        if gen != self._gen:
            if _tries >= 3:
                raise RuntimeError("科技索引在扫描期间被改动了 %d 次，没能赶上一份稳定的数据，"
                                   "请稍后再试" % (_tries,))
            return self._tech_index(_tries + 1)
        tk._tech_field_index = idx
        return idx

    def _tech_fields_of(self, rec, tk=None):
        from aoe2mod.dat import techfields as TF
        tk = tk if tk is not None else self.tk
        f = TF.fields_at(self.session_raw(tk), tk._parsed[3], rec["start"])
        rec["fields"] = f
        return f

    def _tech_census(self):
        """Which integers do the tech columns actually hold, and how often.

        Measured 0.03 s for all 1510 records (the light scan is already paid by
        `_tech_index`), so unlike the unit census there is no sampling cap: the
        numbers below are the whole file.
        """
        tk = self.tk
        cached = getattr(tk, "_tech_census", None)
        if cached is not None:
            return cached
        from aoe2mod.dat import techfields as TF
        raw = self.session_raw()
        stage = tk._parsed[3]
        seen = {}
        for rec in self._tech_index().values():
            for name, f in TF.fields_at(raw, stage, rec["start"]).items():
                v = f["value"]
                if isinstance(v, str):
                    continue
                seen.setdefault(name, {})
                seen[name][v] = seen[name].get(v, 0) + 1
        out = {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0])))
               for k, v in seen.items()}
        tk._tech_census = out
        return out

    def _tech_ref(self, name, value):
        """Name the object a pointer column points at, or None.

        Four columns carry a reference.  Everything else returns None and the
        page prints the number -- a miss must not look like a name (the same
        rule `techlabels.value_name` follows).
        """
        tk = self.tk
        try:
            v = int(value)
        except (TypeError, ValueError):
            return None
        tail = name.rsplit(".", 1)[-1]
        if tail == "Civ":
            if v < 0:
                return {"kind": "civ", "id": v, "name": "通用（所有文明）"}
            names = tk.civ_names
            if 0 <= v < len(names):
                en = names[v]
                zh = CN.chinese(en)
                return {"kind": "civ", "id": v, "en": en,
                        "name": zh or en}
            return None
        if tail == "EffectID":
            return self._effect_ref(v)
        if tail == "LocationID":
            if v < 0:
                return {"kind": "unit", "id": v, "name": "没有研究地点"}
            e = self._semantic().units.get(v)
            if e is None:
                return None
            return {"kind": "unit", "id": v, "en": e.en,
                    "name": e.zh or e.en or e.display}
        if name.startswith("RequiredTechs."):
            if v < 0:
                return {"kind": "tech", "id": v, "name": "空位"}
            e = self._semantic().techs.get(v)
            if e is None:
                return None
            return {"kind": "tech", "id": v, "en": e.en,
                    "name": e.zh or e.en or e.display}
        return None

    def _effect_ref(self, v):
        """`EffectID 22` -> `织布机`.  Falls back to the effect's own name.

        The effect table and the technology table are separate: effect 22 is
        called "Loom" and technology 22 is also Loom, which is why 373 of 1500
        effects match a technology by English name and can borrow its Chinese
        name.  The rest have no Chinese anywhere in the install (they are DE's
        internal effect labels, "Tarkan (make avail)"), so the English name is
        the honest answer rather than a translation invented here.
        """
        tk = self.tk
        if v < 0:
            return {"kind": "effect", "id": v, "name": "没有效果"}
        cache = getattr(tk, "_effect_zh", None)
        if cache is None:
            cache = {}
            by_en = {}
            for t in self._semantic().techs.values():
                if t.en and t.zh:
                    by_en.setdefault(NTX.readable(t.en).strip().lower(), t.zh)
            for e in tk._effect_records():
                # Decode BEFORE pairing: `got["en"]` is compared against tech
                # English names below, and a UTF-8-inside-latin-1 effect name
                # never matches anything while its decoded form does.
                en = (NTX.readable(e.get("name")) or "").strip()
                zh = by_en.get(en.lower()) if en else None
                cache[e["index"]] = {"zh": zh, "en": en}
            tk._effect_zh = cache
        got = cache.get(v)
        if got is None:
            return None
        if got["zh"]:
            return {"kind": "effect", "id": v, "name": got["zh"],
                    "en": got["en"]}
        if got["en"]:
            return {"kind": "effect", "id": v, "name": got["en"]}
        return {"kind": "effect", "id": v, "name": "（无名效果）"}

    def _tech_value_name(self, name, v):
        """Chinese name for one stored value of one column, or None."""
        ref = self._tech_ref(name, v)
        if ref is not None:
            return ref["name"]
        from aoe2mod.game import techlabels as TL
        return TL.value_name(name, v)

    def tech_fields(self, tech, group="", q=""):
        """Every field of one technology, labelled, grouped, referenced."""
        from aoe2mod.game import techlabels as TL
        tk = self.tk
        tk._ensure()
        try:
            tid = int(tech)
        except (TypeError, ValueError):
            return {"ok": False, "error": "科技编号要是数字，收到的是 %r" % (tech,)}
        rec = self._tech_index().get(tid)
        if rec is None:
            return {"ok": False, "error": "没有第 %d 号科技（共 %d 条）" % (
                tid, len(self._tech_index()))}
        allf = rec.get("fields") or self._tech_fields_of(rec)
        e = self._semantic().techs.get(tid)
        census = self._tech_census()
        rows = []
        for fname, f in allf.items():
            meta = TL.meta_for(fname)
            grp = meta.get("group", "misc")
            if group and grp != group:
                continue
            label = meta.get("zh") or fname
            if q and (q not in label and q.lower() not in fname.lower()):
                continue
            row = {"name": fname, "label": label, "group": grp,
                   "group_zh": TL.GROUP_ZH.get(grp, grp),
                   "kind": f["kind"], "value": f["value"],
                   "offset": f["offset"]}
            for k in ("lo", "hi", "step", "hint"):
                if k in meta:
                    row[k] = meta[k]
            if "enum" in meta and meta["enum"]:
                row["enum"] = {str(k): v for k, v in meta["enum"].items()}
                row["enum_text"] = meta["enum"].get(f["value"])
            ref = self._tech_ref(fname, f["value"])
            if ref is not None:
                # The pointer column: this is the shape AGE never sends.
                row["ref"] = ref
                row["ref_text"] = ref["name"]
            if meta.get("ro") or f["kind"] == "str":
                # A string is length-prefixed; `set_tech_field` refuses it.  Mark
                # it read-only HERE so the page draws no input box for it -- a
                # box that always fails on submit teaches the player nothing.
                row["ro"] = True
            c = census.get(fname)
            # Only offer the observed values when the list is short enough to
            # read.  `EffectID` has 1015 distinct values and `Name` 1226; a
            # dropdown of 1015 is worse than a text box, so those fall through
            # and keep the numeric input (with `ref` naming the current value).
            if c and not row.get("ro") and not row.get("enum") and len(c) <= 64:
                row["seen"] = {str(k): n for k, n in c.items()}
                names = {}
                for k in c:
                    nm = self._tech_value_name(fname, k)
                    names[str(k)] = nm if nm else ("#%s" % k)
                row["seen_names"] = names
            rows.append(row)
        rows.sort(key=lambda r: r["offset"])
        groups = []
        for gid, gzh in TL.GROUPS:
            n = sum(1 for r in allf if TL.group_of(r) == gid)
            if n:
                groups.append({"id": gid, "zh": gzh, "count": n})
        return {"ok": True, "tech": tid, "kind": "tech",
                "name": (e.zh or e.en or "") if e is not None else "",
                "en": (e.en or "") if e is not None else "",
                "start": rec["start"], "end": rec["end"],
                "bytes": rec["end"] - rec["start"],
                "field_count": len(allf),
                "groups": groups, "fields": rows, "shown": len(rows)}

    # ---- giving a record a picture of its own ---------------------------
    #
    # WHY THIS IS NOT JUST "write IconID".  An icon number is a LOOKUP KEY, not
    # the picture: the engine resolves it through `icons.json` into a material,
    # and the material through `materials.json` into a texture file.  Writing
    # `IconID` alone therefore points a record at a key nobody defines, and the
    # game draws nothing -- measured 2026-11-06: `IconID` 8 -> 1000 on unit 74
    # wrote its two bytes correctly and produced an empty button, because the
    # shipped table stops at 999.
    #
    # So a picture is FOUR things and they have to agree: the texture file, the
    # material row, the texture row, and the key in the icon table that the
    # record's `IconID` names.  Three of the four live in two JSON files that
    # the engine reads WHOLE from the mod in place of the shipped ones, so they
    # ship as complete merged tables rather than patches.
    def set_icon(self, kind="unit", record=None, civ="", path=None,
                 data_b64=None, filename=None, slot=None, dry=True,
                 title=None):
        """Point one record at a picture it does not share with anything.

        `path` is a picture on this machine; `data_b64` is the same picture
        posted by the page (a browser cannot read a local path, so the file
        picker sends its bytes).  `dry=True` answers what WOULD happen -- which
        slot, which material name, which four files -- and writes nothing.

        The picture is letterboxed onto a transparent square, never stretched
        and never cropped: a 200x100 logo squashed square looks wrong on a
        square button, and cropping hides most of it.
        """
        from aoe2mod.game import iconart as IA
        tk = self.tk
        tk._ensure()
        if record is None:
            return {"ok": False, "error": "要给出这要换图标的记录编号"}
        if kind not in ("unit", "tech"):
            return {"ok": False,
                    "error": "只有单位和科技有图标，收到的是 %r" % (kind,)}
        cleanup = []
        src_path = path
        if not src_path and data_b64:
            import base64
            import tempfile
            try:
                blob = base64.b64decode(
                    str(data_b64).split(",")[-1], validate=False)
            except Exception:
                return {"ok": False, "error": "这张图传过来的内容读不出来"}
            if len(blob) > 8 * 1024 * 1024:
                return {"ok": False,
                        "error": "这张图有 %d MB，太大了（上限 8 MB）"
                                 % (len(blob) // (1024 * 1024),)}
            # A temp file rather than a second decoder: `picture.read` already
            # handles PNG/BMP/DDS with standard library only, and the packaged
            # build ships no Pillow on purpose.  One code path means the
            # preview and the build can never disagree about what a picture is.
            ext = os.path.splitext(str(filename or ""))[1].lower() or ".png"
            if ext not in (".png", ".bmp", ".dds", ".jpg", ".jpeg"):
                ext = ".png"
            fd, tmp = tempfile.mkstemp(suffix=ext, prefix="aoe2icon_")
            with os.fdopen(fd, "wb") as fh:
                fh.write(blob)
            src_path = tmp
            cleanup.append(tmp)
        if not src_path:
            return {"ok": False, "error": "没有给出要用的图片"}
        try:
            wide, high = IA.check_picture(src_path)
        except IA.IconError as exc:
            return {"ok": False, "error": str(exc)}
        name = ""
        if kind == "unit":
            want = str(civ or "").strip()
            civ_all = want == "*"
            civ_index = (1 if len(tk._civs) > 1 else 0) if (
                civ_all or not want) else tk._civ_index(want)
            rec = self._unit_index().get((civ_index, int(record)))
            if rec is None:
                return {"ok": False,
                        "error": "这个文明里没有第 %s 号单位" % (record,)}
            name = (self._fields_of(rec).get("Name") or {}).get("value") or ""
        else:
            civ_all = False
            rec = self._tech_index().get(int(record))
            if rec is None:
                return {"ok": False, "error": "没有第 %s 号科技" % (record,)}
            name = (self._tech_fields_of(rec).get("Name") or {}).get(
                "value") or ""
        try:
            icons_doc, materials_doc = IA.shipped(tk.game_root)
            slot = int(slot) if slot not in (None, "") else None
            art = IA.plan(icons_doc, materials_doc, src_path,
                          stem=str(name) or None, slot=slot, kind=kind)
            # Skip over numbers this session already handed out, and reuse the
            # one a record already has: picking a second picture for the SAME
            # record replaces it, it does not take a second slot.
            mine = self._icon_owner.get((kind, int(record)))
            if slot is not None:
                pass
            elif mine is not None:
                art = IA.plan(icons_doc, materials_doc, src_path,
                              stem=str(name) or None, slot=mine, kind=kind)
            else:
                while art["slot"] in self._icon_slots.get(kind, ()):
                    art = IA.plan(icons_doc, materials_doc, src_path,
                                  stem=str(name) or None,
                                  slot=art["slot"] + 1, kind=kind)
        except IA.IconError as exc:
            for t in cleanup:
                try:
                    os.unlink(t)
                except OSError:
                    pass
            return {"ok": False, "error": str(exc)}
        # What the field says now, so the preview can print "8 -> 1000" rather
        # than only the destination.
        flds = (self._fields_of(rec) if kind == "unit"
                else self._tech_fields_of(rec))
        was = (flds.get("IconID") or {}).get("value")
        out = {"ok": True, "kind": kind, "record": int(record),
               "label": str(name), "civ": (str(civ or "")
                                           if kind == "unit" else ""),
               "wide": wide, "high": high, "side": art["side"],
               "slot": art["slot"], "key": art["key"],
               "material": art["material"], "file": art["file_rel"],
               "files": [art["file_rel"], art["icons_rel"],
                         art["materials_rel"]],
               "was": was, "becomes": art["slot"],
               "copies": (len(tk._civs) if (kind == "unit" and civ_all)
                          else 1)}
        if dry:
            for t in cleanup:
                try:
                    os.unlink(t)
                except OSError:
                    pass
            out["dry"] = True
            out["pending"] = len(self.pending_edits())
            return out
        # The record half.  Reusing the two field writers rather than packing
        # the bytes here keeps ONE refusal list, one history step and one
        # `_after_write` for the whole program.
        if kind == "unit":
            wrote = self.set_unit_field(int(record), "IconID", art["slot"],
                                        civ=civ, dry=False, title=title)
        else:
            wrote = self.set_tech_field(int(record), "IconID", art["slot"],
                                        dry=False, title=title)
        unchanged = False
        if not wrote.get("ok"):
            # The record already names this slot and the picture is the new
            # part.  `set_unit_field` refuses a same-value write correctly --
            # its question is "did the number change" -- so ask the other
            # question here: is the slot the picture's, and is the picture new?
            # Without this, picking a second picture for one record reported
            # failure AFTER the merge table had already swapped the image:
            # the screen said no, the mod said yes (measured 2026-11-06).
            if (str(wrote.get("error") or "").startswith("值没变")
                    or "已经是" in str(wrote.get("error") or "")):
                unchanged = True
            else:
                for t in cleanup:
                    try:
                        os.unlink(t)
                    except OSError:
                        pass
                return {"ok": False,
                        "error": "图标槽 %d 已经算好了，但记录没能改成它：%s"
                                 % (art["slot"], wrote.get("error")),
                        "slot": art["slot"], "planned": out}
        # The three file halves.  Built AFTER the record write so a refused
        # record cannot leave an orphan texture in the mod.
        grew = False
        try:
            _side, _side2, _rgba = IA._rgba_from_picture(src_path,
                                                        side=art["side"])
            item = {"label": art["key"], "rgba": _rgba, "side": art["side"],
                    "slot": art["slot"], "stem": art["material"],
                    "kind": kind}
            # ONE entry per slot: picking a second picture for the same record
            # replaces its entry rather than adding a second one, because a
            # duplicate key would make the merge refuse and the OLD picture
            # ship while the record already names the new slot.
            same = [i for i, it in enumerate(self._icon_items)
                    if it["kind"] == kind and it["slot"] == art["slot"]]
            if same:
                self._icon_items[same[0]] = item
            else:
                self._icon_items.append(item)
                grew = True
            files, metas = IA.emit_many(icons_doc, materials_doc,
                                        self._icon_items)
        except IA.IconError as exc:
            if grew:
                self._icon_items.pop()
            return {"ok": False, "error": str(exc), "record_written": wrote}
        finally:
            for t in cleanup:
                try:
                    os.unlink(t)
                except OSError:
                    pass
        # DERIVED, whole: `emit_many` returns the complete merged tables for
        # every item, so the map is replaced rather than merged into.  Keeping
        # the old keys is exactly the bug noted on `_icon_items`.
        self._icons = dict(files)
        self._icon_slots.setdefault(kind, set()).add(art["slot"])
        self._icon_owner[(kind, int(record))] = art["slot"]
        out["wrote"] = wrote
        if unchanged:
            # Say it out loud: the record did not move, only the bytes behind
            # the slot it already named.
            out["record_unchanged"] = True
        out["icon_files"] = sorted(files)
        out["texture_bytes"] = len(files.get(IA._mod_rel(art["file_rel"]))
                                    or b"")
        out["shipping"] = len(self._icons)
        out["pending"] = len(self.pending_edits())
        out["session_dirty"] = self.session_dirty
        return out

    def set_tech_field(self, tech, name, value, dry=True, title=None):
        """Write one technology field.  Same three refusals as `set_unit_field`.

        `dry=True` by default and echoes the bytes that would change, because
        the common mistake is a field name that means something else here than
        it does on a unit (`Type` is the struct discriminator there and "0 普通 /
        2 时代升级" here).
        """
        import struct
        from aoe2mod.game import techlabels as TL
        tk = self.tk
        tk._ensure()
        try:
            tid = int(tech)
        except (TypeError, ValueError):
            return {"ok": False, "error": "科技编号要是数字，收到的是 %r" % (tech,)}
        rec = self._tech_index().get(tid)
        if rec is None:
            return {"ok": False, "error": "没有第 %d 号科技" % (tid,)}
        _flds = self._tech_fields_of(rec)
        f = _flds.get(name)
        if f is None:
            close = [k for k in _flds if name.lower() in k.lower()][:6]
            return {"ok": False,
                    "error": "这条科技里没有叫 %s 的字段" % (name,),
                    "did_you_mean": close}
        meta = TL.meta_for(name)
        if meta.get("ro"):
            return {"ok": False,
                    "error": "「%s」是只读的：%s" % (
                        meta.get("zh", name),
                        meta.get("hint") or "它的值由数据本身决定，改了会让整条记录读不下去。")}
        kind = f["kind"]
        if kind == "str":
            # A string is length-prefixed, so a fixed-width write cannot express
            # it: shortening leaves stale bytes, lengthening overwrites the next
            # field.  Refusing here is the difference between "no" and a .dat
            # that parses but is wrong.
            return {"ok": False,
                    "error": "「%s」是字符串，不能用定宽方式改写：它的长度前缀写了字节数，"
                             "改短会留下残字、改长会覆盖下一个字段。" % (meta.get("zh", name),)}
        old = f["value"]
        try:
            new = float(value) if kind == "f32" else int(value)
        except (TypeError, ValueError):
            return {"ok": False, "error": "%s 要填%s，收到的是 %r" % (
                meta.get("zh", name),
                "小数" if kind == "f32" else "整数", value)}
        W = {"u8": (0, 255), "u16": (0, 65535), "i16": (-32768, 32767),
             "i32": (-2147483648, 2147483647), "u32": (0, 4294967295),
             "f32": (-3.4e38, 3.4e38)}.get(kind)
        if W and not (W[0] <= new <= W[1]):
            return {"ok": False,
                    "error": "「%s」在文件里只占 %s，装不下 %s（范围 %s..%s）" % (
                        meta.get("zh", name), kind, new, W[0], W[1])}
        if "lo" in meta and new < meta["lo"]:
            return {"ok": False,
                    "error": "%s 不能小于 %s（%s）" % (
                        meta.get("zh", name), meta["lo"],
                        meta.get("hint") or "这是引擎里合理的下限")}
        if "hi" in meta and new > meta["hi"]:
            return {"ok": False,
                    "error": "%s 不能大于 %s（%s）" % (
                        meta.get("zh", name), meta["hi"],
                        meta.get("hint") or "这是引擎里合理的上限")}
        if (new == old) if kind == "f32" else (int(new) == old):
            return {"ok": False, "error": "值没变，还是 %s" % (old,)}
        fmt = {"u8": "<B", "u16": "<H", "i16": "<h", "i32": "<i", "u32": "<I",
               "f32": "<f"}[kind]
        packed = struct.pack(fmt, new)
        off = f["offset"]
        base = self.session_raw()
        before = bytes(base[off:off + len(packed)])
        changed = sum(1 for a, b in zip(before, packed) if a != b)
        out = {"ok": True, "tech": tid, "field": name,
               "label": meta.get("zh", name), "kind": kind,
               "offset": off, "before": old, "value": new,
               "bytes_before": before.hex(), "bytes_after": packed.hex(),
               "bytes_changed": changed, "changes_dat": changed > 0,
               "ref_before": self._tech_ref(name, old),
               "ref_after": self._tech_ref(name, new)}
        if dry or not changed:
            out["dry"] = True
            out["session_dirty"] = self.session_dirty
            out["pending"] = len(self.pending_edits())
            return out
        _e = self._semantic().techs.get(tid)
        _nmzh = ((_e.zh or _e.en) if _e is not None else "") or ""
        self._session_edit(off, packed, note={
            "tech": tid,
            # The record's own `Name` is the internal English string ("Loom");
            # the mod description should say 织布机, which is what the player sees
            # in the game and what they clicked to get here.
            "tech_name": _nmzh or (_flds.get("Name") or {}).get("value") or "",
            "field": name, "label": meta.get("zh", name),
            "was": old, "now": new, "kind": kind, "offset": off})
        self._stamp_write(out)
        out["hint"] = "已记在内存里，改完点「保存成 mod」一次写盘"
        return out

    # ---- the effect list of one technology ------------------------------
    #
    # WHY THIS IS A SEPARATE PANE AND NOT 34 MORE FIELDS: a technology record
    # stores a POINTER (`EffectID`) at a record somewhere else in the file, and
    # that record holds a LIST of commands.  AGE shows the pointer and leaves the
    # list to a different screen; measured 2026-11-01, this tool showed neither,
    # so 6,420 shipped number-carrying commands -- everything a technology
    # actually DOES -- were unreachable.
    #
    # The list is where the interesting numbers live.  `织布机` reads as three
    # rows: 平民 生命值 +15 / 平民 近战护甲 +1 / 平民 远程护甲 +2.  AGE prints
    # the same three as `4 -1 4 0 15.0` and expects you to know that the third
    # number is an attribute id and the fourth is a delta.
    def effect_rows(self, tech):
        """Every command of this technology's effect record, said in Chinese."""
        from aoe2mod.game import effectlabels as EL
        from aoe2mod.intent import compiler as C
        tk = self.tk
        tk._ensure()
        try:
            tid = int(tech)
        except (TypeError, ValueError):
            return {"ok": False, "error": "科技编号要是数字，收到的是 %r" % (tech,)}
        if tid not in self._tech_index():
            return {"ok": False, "error": "没有第 %d 号科技" % (tid,)}
        got = tk.effects(tid)
        # The class-name table the row's packed high byte is named from.  Read
        # from the same JSON `compiler.effect_rows` already read, so a name this
        # module prints and a name that function prints can never disagree.
        _cls_zh = ((C.load_effect_tables().get("zh") or {}).get("classes") or {})
        rows = []
        for r in got.get("rows") or ():
            row = dict(r)
            row["title"] = EL.row_title(r, class_zh=_cls_zh)
            row["params_zh"] = EL.params_zh(r.get("type_params"))
            row["shared_note"] = EL.shared_note(r, tech_id=tid)
            # The raw slots stay on the row: the preview has to be able to say
            # which bytes move, and a row whose number cannot be rewritten still
            # renders with its name so the list is complete.
            rows.append(row)
        _e = self._semantic().techs.get(tid)
        return {"ok": True, "tech": tid,
                "name": ((_e.zh or _e.en) if _e is not None else "")
                        or got.get("name") or "",
                "en": (_e.en or "") if _e is not None else "",
                "effect_id": got.get("effect_id"),
                "effect_name": NTX.readable(got.get("effect_name")),
                "command_count": len(rows),
                "editable_count": sum(1 for r in rows if r.get("editable")),
                "rows": rows}

    def unit_effects(self, unit, civ=""):
        """Every effect command in the file whose target is this unit.

        THE REVERSE DIRECTION.  A .dat has no pointer from a unit to a
        technology: the technology's effect record names the unit in a command
        slot, so "what changes 民兵" can only be answered by reading every
        technology's list.  Measured 2026-11-06 on the shipped file: 1,510
        technologies, 8,005 rows, 0.09 s -- cheap enough to do per request and
        cache per generation (`tk._unit_effects`).

        Why this exists at all: reported 「单位绑定效果，科技绑定效果，啥的全都没法
        做」.  Binding an effect to a UNIT is not a file operation -- there is no
        such field, and pretending otherwise would be a button that does
        nothing.  What the player means is this list: the numbers that are about
        this unit, wherever they live, each with its current value and a box to
        change it.

        Every row carries the technology it belongs to (`tech`, `tech_name`) and
        the position inside that technology's list (`command`), which is exactly
        what `/api/effect-set` takes -- so the write path here is the same one
        the technology panel already uses, refusals included.
        """
        from aoe2mod.intent import compiler as C
        tk = self.tk
        tk._ensure()
        try:
            uid = int(unit)
        except (TypeError, ValueError):
            return {"ok": False, "error": "单位编号要是数字，收到的是 %r" % (unit,)}
        gen = self._gen
        cache = getattr(tk, "_unit_effects", None)
        if cache is None or getattr(tk, "_unit_effects_gen", None) != gen:
            effects = tk._effect_records()
            fanout = tk._effect_fanout()
            ix = self._semantic()
            cache = {}
            for ti, t in enumerate(tk._tech_records()):
                for r in C.effect_rows(effects, t, fanout=fanout, ix=ix,
                                       unit_class=tk.unit_class):
                    tgt = r.get("target")
                    if tgt is None:
                        continue
                    ids = tgt if isinstance(tgt, (list, tuple)) else [tgt]
                    for one in ids:
                        try:
                            one = int(one)
                        except (TypeError, ValueError):
                            continue
                        cache.setdefault(one, []).append((ti, t, r))
            tk._unit_effects = cache
            tk._unit_effects_gen = gen
        hits = cache.get(uid) or []
        e = self._semantic().units.get(uid)
        name = ((e.zh or e.en) if e is not None else "") or ""
        if not name:
            for civ_row in tk._civs:
                for u in civ_row.get("units") or ():
                    if u.get("id") == uid:
                        name = NTX.readable(u.get("name")) or ""
                        break
                if name:
                    break
        rows = []
        for ti, t, r in hits:
            te = self._semantic().techs.get(ti)
            rows.append({
                "tech": ti,
                "tech_name": ((te.zh or te.en) if te is not None else "")
                             or NTX.readable(t.get("name")) or "",
                "command": r.get("index"),
                "type_label": r.get("type_label"),
                "attribute_label": r.get("attribute_label"),
                "target_label": r.get("target_label"),
                "value": r.get("value"),
                "editable": bool(r.get("editable")),
                "reason": r.get("reason"),
            })
        rows.sort(key=lambda x: (not x["editable"], x["tech"] or 0,
                                 x["command"] or 0))
        return {"ok": True, "unit": uid, "name": name, "total": len(rows),
                "editable_count": sum(1 for r in rows if r["editable"]),
                "rows": rows}

    def set_effect_value(self, tech, command, value=None, delta=None, dry=True,
                         title=None):
        """Rewrite the number of ONE command in a technology's effect list.

        THE OFFSET IS THE ROW'S OWN `offset`, re-read from the live session
        buffer on every call.  A stored offset would be a length in a file that
        gets patched, and the rebuild replay resolves the command by
        (technology, position in the list) for exactly that reason.

        Refusals come from `compiler.plan_effect_edit`, which is the same
        function the build path calls, so a preview cannot promise an edit the
        build then refuses -- that divergence is a defect this project has paid
        for three times.
        """
        import struct
        from aoe2mod.intent import compiler as C
        from aoe2mod.game import effectlabels as EL
        tk = self.tk
        tk._ensure()
        try:
            tid = int(tech)
            idx = int(command)
        except (TypeError, ValueError):
            return {"ok": False,
                    "error": "科技编号和第几条效果都要是数字，收到的是 %r / %r"
                             % (tech, command)}
        got = tk.effects(tid)
        if not got.get("rows"):
            return {"ok": False,
                    "error": "「%s」没有可以改的效果（这条科技没有指向任何效果记录）"
                             % (got.get("name") or tid,)}
        _e = self._semantic().techs.get(tid)
        tech_label = ((_e.zh or _e.en) if _e is not None else "") or got.get("name")
        if value is not None:
            op, amount = "value", value
        elif delta is not None:
            op, amount = "delta", delta
        else:
            return {"ok": False, "error": "没说要把这个数改成多少（给 value 或 delta）"}
        try:
            row = C.plan_effect_edit(
                tk._effect_records(),
                {"effect_id": got.get("effect_id"), "name": got.get("effect_name")},
                idx, op, amount, ix=self._semantic(),
                fanout=tk._effect_fanout(), tech_label=tech_label,
                unit_class=tk.unit_class)
        except C.IntentError as exc:
            return {"ok": False, "error": str(exc)}
        off = row.get("offset")
        if off is None:
            return {"ok": False,
                    "error": "效果记录里没有标出第 %d 条命令要改的那个数字在哪"
                             % (idx + 1,)}
        pack = struct.pack("<f", row["stored"])
        base = self.session_raw()
        before = bytes(base[off:off + 4])
        changed = sum(1 for a, b in zip(before, pack) if a != b)
        out = {"ok": True, "tech": tid, "command": idx,
               "title": EL.row_title(
                   row,
                   class_zh=((C.load_effect_tables().get("zh") or {})
                             .get("classes") or {})),
               "attribute": row.get("attribute"),
               "attribute_label": row.get("attribute_label"),
               "target_label": row.get("target_label"),
               "before": row.get("before"), "after": row.get("after"),
               "stored": row.get("stored"),
               "offset": off, "bytes_before": before.hex(),
               "bytes_after": pack.hex(), "bytes_changed": changed,
               "changes_dat": changed > 0,
               "shared_note": EL.shared_note(row, tech_id=tid)}
        if dry or not changed:
            out["dry"] = True
            out["session_dirty"] = self.session_dirty
            out["pending"] = len(self.pending_edits())
            return out
        # The label is WHAT the command changes, without its number: the mod
        # description already prints `was → now` beside it, so a title carrying
        # the old value would read "平民 生命值 +15：15.0 → 100.0" -- the number
        # the player just replaced, printed twice, once of them wrong.
        self._session_edit(off, pack, note={
            "tech": tid, "effect": got.get("effect_id"), "command": idx,
            "tech_name": tech_label,
            "field": "effect[%d]" % (idx,),
            "label": EL.row_label(
                row, class_zh=((C.load_effect_tables().get("zh") or {})
                               .get("classes") or {})),
            "was": row.get("before"), "now": row.get("after"),
            "kind": "f32", "offset": off})
        self._stamp_write(out)
        out["hint"] = "已记在内存里，改完点「保存成 mod」一次写盘"
        return out

    # ---- graphics / sounds ------------------------------------------------
    #
    # WHY A THIRD FIELD EDITOR
    # -----------------------
    # AGE's remaining 150 fields live in 30 tables, and the two biggest --
    # Graphics (20,883 records) and Sounds (930) -- are what a player actually
    # touches after the unit is right: which .slp a unit draws, how fast the
    # animation plays, which sound fires.  None of them were reachable here, so
    # "unit 74's StandingGraphic.0" could be changed but the graphic it points at
    # could not be opened.  That gap is the literal reason the product is "still
    # not a replacement for AGE3".
    #
    # The walk is 0.35 s for graphics and 0.20 s for sounds (stages 1-3 are the
    # first 3.5 MB of the file), so unlike the unit index there is nothing to be
    # clever about: it runs once, is cached on the Toolkit, and `leftover` must
    # be 0 or every offset below is a lie.
    def _table_index(self, table, _tries=0):
        """`{index: {"start","end"}}` plus the record's own name, cached."""
        from aoe2mod.dat import tablefields as TF
        tk = self.tk
        tk._ensure()
        attr = "_table_index_%s" % (table,)
        cached = getattr(tk, attr, None)
        if cached is not None:
            return cached
        from aoe2mod import jobs as J
        raw = self.session_raw()
        gen = self._gen
        J.begin(table, "建立%s表索引" % (TF.TABLE_ZH.get(table, table),), len(raw))
        # A civ record cannot be found on its own: a record's bounds are the
        # previous record's last unit end, and the unit index that holds those
        # ends is the one the 单位 tab builds.  Measured 2026-11-04, deriving
        # them there agrees with an honest walk 62/62 and costs 0.0006 s
        # instead of 9.15 s -- but only because the unit scan itself is already
        # paid for.  So this table waits for that tab rather than re-reading
        # 136,861 unit records to learn what the app already knows.
        civ_kw = {}
        if table == "civ":
            civ_kw = self._civ_bounds()
        try:
            recs, leftover = TF.scan(raw, table, **civ_kw)
        except Exception as exc:
            J.fail(table, "%s: %s" % (type(exc).__name__, exc))
            raise
        J.finish(table)
        if leftover:
            if table == "civ" and leftover < 0:
                # A negative leftover names the civilization whose derived start
                # disagreed with its own pointer array.  That is a different bug
                # from "the table did not walk", and the number says which one.
                bad = -leftover - 1
                raise RuntimeError(
                    "第 %d 号文明的起点和它自己的单位指针数对不上"
                    "（推导出来的起点是错的，这时候编辑会写进别的文明），"
                    "请把这份 .dat 报给作者。" % (bad,))
            raise RuntimeError(
                "%s表没有走完整个文件（还剩 %d 字节），说明记录的字段地址不可信，"
                "这时候让你编辑会写进隔壁记录。"
                % (TF.TABLE_ZH.get(table, table), leftover))
        gv = tk._parsed[3]
        out = {}
        for rec in recs:
            row = {"index": rec["index"], "start": rec["start"],
                   "end": rec["end"],
                   "commands": rec.get("command_count", 0),
                   "name": TF.record_name(raw, gv, rec, table,
                                          names=self._task_names())}
            # A civ record's own unit counts are the check on its derived start,
            # and `_civ_fields` reports them.  Dropping them here is what made
            # the first version print `真实单位记录数 0` for all 63 records.
            for extra in ("civ_name", "pointer_count", "unit_count"):
                if extra in rec:
                    row[extra] = rec[extra]
            out[rec["index"]] = row
        if gen != self._gen:
            if _tries >= 3:
                raise RuntimeError("%s表的索引在扫描期间被改动了 %d 次，没能赶上一份稳定的数据，"
                                   "请稍后再试" % (TF.TABLE_ZH.get(table, table), _tries))
            return self._table_index(table, _tries + 1)
        setattr(tk, attr, out)
        return out

    def _civ_bounds(self):
        """`{civ_starts, civ_ends, civ_units}` derived from the unit index.

        A civ record is six scalars, 601 floats and 2,750 unit pointers, and the
        unit records it points at are the bulk of the file.  So the honest way to
        find record N+1 is to walk record N -- 9.15 s, re-reading 136,861 unit
        records the editor already indexed on its first tab.

        Measured 2026-11-04 on the shipped file: for every civilization, the
        largest `end` among its unit records IS the next record's first byte,
        and 62 of the 62 derivable starts agree exactly with a full walk.  The
        unit COUNT per civilization travels with the bounds because it is the
        check that makes a derived start safe: if it disagrees with the record's
        own non-zero pointer count, the start was wrong.
        """
        idx = self._unit_index()
        ends, counts = {}, {}
        for rec in idx.values():
            ci = rec["civ_index"]
            counts[ci] = counts.get(ci, 0) + 1
            if ci not in ends or rec["end"] > ends[ci]:
                ends[ci] = rec["end"]
        n = max(ends) + 1 if ends else 0
        if n < 2:
            raise RuntimeError("单位索引里只有 %d 个文明，读不出文明表" % (n,))
        from aoe2mod.dat import tablefields as TF
        offs, _stats = TF.stage_offsets(self.session_raw(), "7 ")
        block_start = offs["7 UnitHeaders"][1]
        starts = [block_start + 2]
        for i in range(n - 1):
            starts.append(ends[i])
        # The last record ends where the civ block ends, which is where the tech
        # block begins -- but that edge is 89 MB further on, so the honest end
        # for the last record is "the rest of the block", clipped to the file.
        last_end = len(self.session_raw())
        ends_list = [starts[i + 1] for i in range(n - 1)] + [last_end]
        return {"civ_starts": starts, "civ_ends": ends_list, "civ_units": counts}

    def _task_names(self):
        """`{unit id: 中文名}` for the task table's rows.

        A task row is named "村民 (男性) · 第 1 条 · 采集/放置".  The name half of
        that lives in the semantic index and the id half in the .dat, and this is
        the only layer that holds both, so the join happens here rather than in
        `tablefields` (which is deliberately game-data only, no name tables).
        """
        if not self._task_name_cache:
            try:
                ix = self.tk.index()
                self._task_name_cache = dict(
                    (uid, e.display) for uid, e in ix.units.items())
            except Exception:                          # noqa: BLE001
                self._task_name_cache = {}
        return self._task_name_cache

    def tables(self):
        """The tables this build can open, with what a screen needs up front."""
        from aoe2mod.dat import tablefields as TF
        out = []
        for key, spec in sorted(TF.TABLES.items()):
            try:
                n = len(self._table_index(key))
            except Exception as exc:                   # noqa: BLE001
                out.append({"id": key, "zh": spec["zh"], "count": 0,
                            "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            out.append({"id": key, "zh": spec["zh"], "count": n})
        return {"ok": True, "tables": out}

    def table_rows(self, table, q="", offset=0, limit=200, named_only=False):
        """One page of a table, as rows a picker can draw.

        `named_only` matters for graphics: 3,520 of the 20,883 records carry no
        name at all (they are the entries nothing points at).  A picker that
        lists them is 17% noise, so the screen asks for named rows and the count
        it prints is the count of THOSE -- two different totals over one list is
        how a screen ends up promising 20,883 and paging 17,363.

        The rule is 「the record says something」, not literally 「has a name」:
        measured 2026-11-03, the 184 unnamed effect records hold 0 commands
        between them -- they are empty slots, and listing one is a row the
        player can only stare at.  A record with commands but no name is NOT
        skipped (302 of the effects are exactly that: bonus payloads no
        technology points at, which is why this table exists).
        """
        from aoe2mod.dat import tablefields as TF
        if table not in TF.TABLES:
            return {"ok": False,
                    "error": "没有叫 %r 的表（只有 %s）"
                             % (table, "、".join(sorted(TF.TABLES)))}
        idx = self._table_index(table)
        qs = str(q or "").strip().lower()
        rows = []
        for i in sorted(idx):
            rec = idx[i]
            # `rec["name"]` is the raw byte string: a Chinese mod writes UTF-8
            # into it, so the picker printed `æ°ææ` for 新效果 (measured on the
            # user's 125 MB mod, 2026-11-06).  Decode once, here, so the search
            # box and the label below cannot disagree about what the row is.
            nm = NTX.readable(rec.get("name")) or ""
            if named_only and not nm and not rec.get("commands"):
                continue
            if qs and qs not in nm.lower():
                continue
            rows.append({"index": i, "name": nm})
        try:
            off = max(0, int(offset))
        except (TypeError, ValueError):
            off = 0
        try:
            lim = max(1, min(1000, int(limit)))
        except (TypeError, ValueError):
            lim = 200
        return {"ok": True, "table": table, "zh": TF.TABLE_ZH.get(table, table),
                "total": len(rows), "named_only": bool(named_only),
                "total_all": len(idx),
                "offset": off, "limit": lim, "rows": rows[off:off + lim]}

    def table_fields(self, table, index, q=""):
        """Every field of one graphic or sound record, labelled in Chinese."""
        from aoe2mod.dat import tablefields as TF
        if table not in TF.TABLES:
            return {"ok": False, "error": "没有叫 %r 的表" % (table,)}
        try:
            ix = int(index)
        except (TypeError, ValueError):
            return {"ok": False, "error": "记录编号要是数字，收到的是 %r" % (index,)}
        idx = self._table_index(table)
        rec = idx.get(ix)
        if rec is None:
            return {"ok": False, "error": "第 %d 号记录不存在（共 %d 条）"
                                          % (ix, len(idx))}
        raw = self.session_raw()
        flds = TF.fields_at(raw, self.tk._parsed[3], rec, table=table)
        qs = str(q or "").strip().lower()
        rows = []
        for name, f in flds.items():
            meta = TF.meta_for(table, name)
            # A per-command label wins over the generic slot name.  Measured
            # 2026-11-03: the slot meta says 「数值」 for every `#N.d`, so three
            # commands read as three identical 「数值」 rows and the player has no
            # way to tell which one is 生命值 and which is 护甲 -- the whole
            # point of naming the commands.  `_effect_fields` already built
            # 「第 1 条：平民 生命值」 for exactly this.
            label = f.get("label") or meta.get("zh") or name
            if qs and qs not in label.lower() and qs not in name.lower():
                continue
            row = {"name": name, "label": label, "kind": f["kind"],
                   "value": f["value"], "offset": f["offset"]}
            for k in ("lo", "hi", "hint"):
                if k in meta:
                    row[k] = meta[k]
            if meta.get("ro") or f["kind"] == "str":
                row["ro"] = True
            # A command the effect table cannot write (a target the writer does
            # not handle) must SAY so on its own row.  `plan` refuses it either
            # way, but an editable-looking box that rejects the number after the
            # fact reads as a bug in the tool, not as a fact about the record.
            if f.get("_reason"):
                row["ro"] = True
                row["hint"] = f["_reason"]
                row["reason"] = f["_reason"]
            if "rank" in f:
                # Civ resource slots carry a usefulness rank; the byte offset of
                # slot 189 is not what a player is looking for.
                row["rank"] = f["rank"]
            rows.append(row)
        if table == "civ":
            # rank 0/1/2/3 = differs between civs / has a value / only a name /
            # neither.  Within a rank the slot number IS the reading order, so
            # the sort key is (rank, offset) and nothing is lost.
            rows.sort(key=lambda r: (r.get("rank", 3), r["offset"]))
        else:
            rows.sort(key=lambda r: r["offset"])
        return {"ok": True, "table": table, "zh": TF.TABLE_ZH.get(table, table),
                "record": ix, "name": NTX.readable(rec.get("name")) or "",
                "start": rec["start"], "end": rec["end"],
                "bytes": rec["end"] - rec["start"],
                "field_count": len(flds), "fields": rows,
                "shown": len(rows)}

    def set_table_field(self, table, index, name, value, dry=True, title=None):
        """Write one field of a graphic or sound record.

        Same refusals as `set_unit_field`, decided by `tablefields.plan` so the
        preview and the write are the same code path: a field that is not here,
        a read-only count, a length-prefixed string, a value outside the byte
        width, a value that is already stored.
        """
        from aoe2mod.dat import tablefields as TF
        if table not in TF.TABLES:
            return {"ok": False, "error": "没有叫 %r 的表" % (table,)}
        try:
            ix = int(index)
        except (TypeError, ValueError):
            return {"ok": False, "error": "记录编号要是数字，收到的是 %r" % (index,)}
        idx = self._table_index(table)
        rec = idx.get(ix)
        if rec is None:
            return {"ok": False, "error": "第 %d 号记录不存在（共 %d 条）"
                                          % (ix, len(idx))}
        base = self.session_raw()
        got = TF.plan(table, bytes(base), self.tk._parsed[3], rec, name, value)
        if not got.get("ok"):
            out = {"ok": False, "error": got.get("error")}
            if got.get("did_you_mean"):
                out["did_you_mean"] = got["did_you_mean"]
            if got.get("unchanged"):
                out["unchanged"] = True
            return out
        before = bytes(base[got["offset"]:got["offset"] + len(got["packed"])])
        out = {"ok": True, "table": table, "zh": TF.TABLE_ZH.get(table, table),
               "record": ix, "record_name": NTX.readable(rec.get("name")) or "",
               "field": name, "label": got["label"], "kind": got["kind"],
               "offset": got["offset"], "before": got["before"],
               "value": got["value"], "bytes_before": before.hex(),
               "bytes_after": got["packed"].hex(),
               "bytes_changed": got["changed"],
               "changes_dat": got["changed"] > 0}
        if dry or not got["changed"]:
            out["dry"] = True
            out["session_dirty"] = self.session_dirty
            out["pending"] = len(self.pending_edits())
            return out
        self._session_edit(got["offset"], got["packed"], note={
            "table": table, "record": ix,
            "record_name": NTX.readable(rec.get("name")) or "",
            "field": name, "label": got["label"],
            "was": got["before"], "now": got["value"],
            "kind": got["kind"], "offset": got["offset"]})
        self._stamp_write(out)
        out["hint"] = "已记在内存里，改完点「保存全部改动」一次写盘"
        return out

    def parse(self, text, pins=None):
        """Sentence -> {intents, refusals}.  No bytes touched.

        `pins` are [{kind, id}] for the pictures the player clicked.  A name is
        not unique (城门 is 29 records, 城镇中心 20) and name-only resolution
        takes the smallest id, so the click has to travel with the sentence.
        """
        intents, clauses = nl.read(text, self.vocab(),
                                   civ_names=self.tk.civ_names,
                                   civ_zh=nl.CIV_ZH, pins=pins,
                                   effect_count=self.tk.effect_count,
                                   unit_class=self.tk.unit_class,
                                   producers=self.tk.unit_producers,
                                   tech_cost=self.tk.tech_single_cost)
        out = []
        for cl in clauses:
            row = {"text": cl.text, "kind": cl.kind,
                   "entity": (cl.entity.display if cl.entity is not None
                              and not isinstance(cl.entity, dict)
                              else (cl.entity.get("name") if isinstance(cl.entity, dict) else None)),
                   # The id is what the icon and detail routes need.  The page
                   # cannot get it from the display name: 弓箭手 is not any unit's
                   # name, and 城堡 is both a building and part of a technology's
                   # name -- the resolver already picked one, so carry the pick.
                   "entity_id": (getattr(cl.entity, "id", None)
                                 if not isinstance(cl.entity, dict)
                                 else (cl.entity or {}).get("id")),
                   "why": cl.why, "notes": cl.notes,
                   # The exact word the player used for a category ("骑兵"), so
                   # the page can swap a chosen candidate into the sentence
                   # instead of guessing which substring to replace.
                   "class_word": getattr(cl, "class_word", None),
                   "candidates": [{"id": c.id if not isinstance(c, dict) else c["id"],
                                   "name": c.display if not isinstance(c, dict) else c.get("name")}
                                  for c in (cl.candidates or [])],
                   "intent": cl.intent}
            # --- "who can build this" -----------------------------------
            # The reader answered with the record, not with a list: it names no
            # civilization, so the answer is data, and the data is one call away
            # (`_availability_of` reads all 62 trees).  Kept separate from
            # `question` below, which answers with a NUMBER on disk; printing a
            # civ list under 「现在是 X」 would be a different question answered.
            if getattr(cl, "who", None) is not None:
                _w = cl.who
                _ut = (CT.TECH_USE_TYPES if _w.get("kind") == "tech"
                       else CT.UNIT_USE_TYPES)
                _av = (self.tk.availability_of(_w.get("id"), _ut)
                       if _w.get("id") is not None else None)
                if _av is None and _w.get("kind") == "unit":
                    # A BUILDING is not a ``Unit`` row.  The tech-tree file keeps
                    # its 28 buildings in a separate ``civ_techs_buildings`` list
                    # whose ``Use Type`` is ``Building``, so 「谁能造城堡」 asked in
                    # the unit space matched nothing and the honest-sounding
                    # answer below ("not in any tech tree") was simply false --
                    # 62 of 62 civs have a Castle row.  Measured 2026-10-31:
                    # id 82/12/109/70 all read ``None`` in ``Unit`` and
                    # ``ResearchedCompleted`` in ``Unit+Building``, and no id
                    # appears in both lists under two different names (0
                    # collisions across 62 files), so widening the space cannot
                    # turn a unit answer into a building answer.
                    _av = self.tk.availability_of(
                        _w.get("id"), ("Unit",) + tuple(CT.BUILDINGS_USE_TYPES))
                if _av is None:
                    # Not in any tech tree at all -- 1,364 units are like this.
                    # The honest sentence is about THE DATA, not about the word:
                    # the record exists and has a name, it is simply not
                    # something any civilization builds.
                    row["why"] = ("「%s」不在任何文明的科技树里——它不是靠建造或研究"
                                  "拿到的（地图上的东西、装饰、占位记录都是这样）。"
                                  % (cl.entity.display if cl.entity is not None
                                     else "它"))
                else:
                    # What a player means by "who can build this" is the
                    # builders list, not the holders list: they differ on 14
                    # real nodes, and using holders would answer "0 civs can
                    # build War Galley" when 56 can.  Both counts are sent so
                    # the card can say which it is showing.
                    _yes = [_civ_zh_of(self.tk, x) for x in _av["builders"]]
                    # 「谁不能造」 asks for the OTHER side, and the other side is
                    # not "everything minus builders" by subtraction: the 36
                    # civs are split into two groups the tool would fix
                    # differently (a status change for `blocked`, a row insert
                    # for `absent`), so they are reported together but kept
                    # apart, and a negative answer that listed only `blocked`
                    # would silently drop every civ with no row at all.
                    _no = ([_civ_zh_of(self.tk, x) for x in _av["blocked_in"]]
                           + [_civ_zh_of(self.tk, x) for x in _av["absent_from"]])
                    row["who"] = {
                        "kind": _w.get("kind"),
                        "id": _w.get("id"),
                        "civs": _no if _w.get("negative") else _yes,
                        "count": len(_no) if _w.get("negative") else len(_yes),
                        "holders": [_civ_zh_of(self.tk, x) for x in _av["holders"]],
                        "holder_count": _av["holder_count"],
                        "total": len(_yes) + len(_no),
                        "blocked": [_civ_zh_of(self.tk, x)
                                    for x in _av["blocked_in"]],
                        # The civs with no row in this tree at all.  A `grant`
                        # ADDS a row for them while a `revoke` deletes one, so
                        # they belong on the "cannot" side of a negative
                        # question and must not be folded into `blocked`, which
                        # needs a status change instead of a row insert.
                        "absent": [_civ_zh_of(self.tk, x)
                                   for x in _av["absent_from"]],
                        "negative": bool(_w.get("negative")),
                    }
                    # 「玛雅能不能造长弓兵」 names ONE civilization, so the useful
                    # answer is yes/no plus WHICH of the four states that civ is
                    # in -- not a 62-name list the player must find 玛雅 in.  The
                    # four are the ones this data already distinguishes and the
                    # tool fixes differently: holds it, must research first, is
                    # blocked by a status row, or has no row at all.
                    _ask = _w.get("ask_civ")
                    if _ask:
                        # The two sides spell a civilization differently: the
                        # reader hands back the .dat spelling (`Mayan`) while the
                        # tech-tree files are keyed like the game's own files
                        # (`MAYANS`).  Comparing the strings directly made every
                        # verdict fall through, and the card then answered the
                        # 62-name question the player did not ask.  Compare the
                        # CHINESE name instead -- one spelling both sides reach.
                        _zh = _civ_zh_of(self.tk, _ask)

                        def _has(bucket):
                            return any(_civ_zh_of(self.tk, x) == _zh
                                       for x in (_av.get(bucket) or ()))

                        _nm = cl.entity.display if cl.entity is not None else "它"
                        if _has("holders"):
                            _verdict = ("能。%s 直接就有「%s」，不用先研究什么。"
                                        % (_zh, _nm))
                        elif _has("pending_in"):
                            _verdict = ("能，但要先研究前置：%s 的科技树里有这一行，"
                                        "状态是「待解锁」。" % _zh)
                        elif _has("blocked_in"):
                            _verdict = ("不能，但只差一步：%s 的科技树里有这一行，"
                                        "只是被禁用了。说「%s能造%s」就能打开。"
                                        % (_zh, _zh, _nm))
                        elif _has("absent_from"):
                            _verdict = ("不能，而且 %s 的科技树里根本没有这一行。"
                                        "说「%s能造%s」会新增一行。"
                                        % (_zh, _zh, _nm))
                        else:
                            _verdict = None
                        if _verdict:
                            row["who"]["verdict"] = _verdict
                            row["who"]["ask_civ"] = _zh
                            # One civilization was named, so "26 / 62 个文明" is
                            # not the answer to the question that was asked.
                            _builds = _has("builders")
                            row["who"]["civs"] = [_zh] if _builds else []
                            row["who"]["count"] = 1 if _builds else 0
                            row["who"]["total"] = 1

            # A question is answered from the same call that would perform the
            # edit: `_as_edit` turned 「村民血量是多少」 into 「村民血量加1」, so the
            # plan's `preview_values.before` IS the value on disk right now.  That
            # is the one number AGE3 makes the player dig out of a 620-column
            # tree, and there is no cheaper honest source for it.
            #
            # `intent` stays None and `buildable` stays False: a question is not
            # work, and the page must not offer a build button for it.
            if getattr(cl, "question", None) is not None:
                _q = self._safe_plan(cl.question)
                _pv = ((_q.get("plan") or {}).get("preview_values")
                       if _q.get("ok") else None) or {}
                # Two cleanup passes before this reaches the card, both measured
                # 2026-10-31 on the shipped data:
                #
                # 1. A mirror field ("基础攻击 (mirror)") carries the SAME number
                #    as the field it mirrors, so 「弓箭手攻击力是多少」 arrived as
                #    "2 种取值" when the honest answer is one value, 4.  Mirror
                #    rows are dropped when an ordinary row exists.
                # 2. What the player asked is how many VALUES there are, not how
                #    many field/row pairs.  「村民射程是多少」 really is 2 values
                #    (0 for 1,575 records, 3 for 126), and that is worth saying;
                #    the pair count would have said 4.
                _pairs = [x for x in (_pv.get("pairs") or [])
                          if "mirror" not in (x.get("field") or "")]
                if not _pairs:
                    _pairs = list(_pv.get("pairs") or [])
                _vals = []
                for _x in _pairs:
                    if _x.get("before") not in _vals:
                        _vals.append(_x.get("before"))
                if _vals:
                    row["question"] = {
                        "field": _pairs[0].get("field") or _pv.get("field"),
                        "value": _vals[0] if len(_vals) == 1 else None,
                        "distinct": len(_vals),
                        "pairs": _pairs,
                    }
                else:
                    # The reader understood the subject but the data has no such
                    # field: say so instead of claiming the tool cannot answer.
                    row["why"] = (_q.get("error")
                                  or "这个记录里没有这一项")
            # A bare 造价 question is answered by the four numbers, not by
            # naming the four slots.  「村民造价是多少」 was told "which of the
            # four did you mean" while the tool knew the answer was 50 food and
            # nothing else.  Measured 2026-11-02; four plan() calls, 1.39 s cold,
            # and only for a sentence that named no resource.
            if ("造价分食物、木材、黄金、石头四项" in (row.get("why") or "")
                    and row.get("kind") == "unit"
                    and row.get("entity_id") is not None):
                _u = row["entity_id"]
                _prices = []
                for _zh, _en in (("食物", "food"), ("木材", "wood"),
                                 ("黄金", "gold"), ("石头", "stone")):
                    _pv = self._safe_plan({"intent": "unit.cost", "unit": _u,
                                           "resource": _en, "delta": 1})
                    _pl = (_pv.get("plan") or {}) if _pv.get("ok") else {}
                    _n = (_pl.get("preview_values") or {}).get("before")
                    if _n is not None and _n != 0:
                        _prices.append("%s %s" % (_zh, _n))
                if _prices:
                    # The example must name a resource that actually HAS a
                    # price: 城堡 charges 650 stone and nothing else, so
                    # 「城堡食物造价减10%」 would point at an empty slot.
                    _first = _prices[0].split(" ")[0]
                    row["why"] = ("「%s」的造价分四项，现在是：%s。这里没说改多少——"
                                  "要改就补上数值，比如「%s%s造价减10%%」。"
                                  % (row.get("entity") or "它",
                                     "，".join(_prices),
                                     row.get("entity") or "它", _first))
            # An intent means the SENTENCE was understood, not that the edit is
            # possible -- the plan can still refuse it ("already has it",
            # "nothing would change", "no such field").  Deciding that here, not
            # in the page, keeps one answer to "may this be built?"; the page
            # used to ask only `c.intent`, so it offered a build button for
            # work that could not be done and sent the refusal into the bundle.
            row["buildable"] = False
            if cl.intent is not None:
                row["preview"] = self._safe_plan(cl.intent)
                if row["preview"].get("ok"):
                    row["buildable"] = \
                        (row["preview"].get("plan") or {}).get("editable") is not False
            out.append(row)
        return {"ok": True, "clauses": out, "intents": intents}

    def ai_meta(self):
        """Is an AI entry point configured, and what does it understand?

        The page must not draw an AI box that always fails.  `available` is the
        only thing it reads to decide, and the grammar shown here is what the
        endpoint is told, so a player can read what is being asked of it.
        """
        from aoe2mod import ai as _ai
        intents, _b = _load_schema()
        brief = [{"id": k,
                  "title": v.get("title") or v.get("title_en") or k,
                  "fields": list((v.get("fields") or {})),
                  "by_sentence": nl.sentence_reachable(k, v)}
                 for k, v in intents["intents"].items()]
        cfg = _ai.config()
        return {"ok": True,
                "available": cfg is not None,
                "model": (cfg or {}).get("model"),
                "base": (cfg or {}).get("base"),
                "grammar": _ai.grammar(brief),
                # Not a hint: this build NEVER turns a model's answer into an
                # edit.  It writes sentences and the reader judges them, so every
                # refusal and preview a human sees applies unchanged.
                "writes": "sentences"}

    def ai_sentences(self, text):
        """One wish -> candidate sentences.  Nothing is parsed or built here."""
        from aoe2mod import ai as _ai
        intents, _b = _load_schema()
        brief = [{"id": k,
                  "title": v.get("title") or v.get("title_en") or k,
                  "fields": list((v.get("fields") or {})),
                  "by_sentence": nl.sentence_reachable(k, v)}
                 for k, v in intents["intents"].items()]
        got = _ai.ask(text, brief)
        return {"ok": True, "ai": got}

    # ---- AI / XS scripting (offline, no model) ---------------------------
    #
    # Two separate departments on purpose.  The `.per` language and XS are two
    # different engines with two different name domains: `(train X)` and
    # `(build X)` in `.per` share exactly one name (transport-ship), and most of
    # what a `.per` script does -- strategic numbers, gather ratios, research --
    # has no XS entry point at all (the shipped XS corpus calls
    # `xsResearchTechnology` zero times).  A single "write my script" box would
    # have to guess which language was meant and would emit the wrong one half
    # the time, so the caller names the department explicitly.

    def ai_lang_meta(self):
        """What the two language departments can express, and on what evidence.

        The `evidence` split is the point of this endpoint.  A name is `corpus`
        when a shipped script actually calls it, and `engine` when it exists in
        the executable's name table but no shipped script ever uses it -- the
        call loads and does nothing.  Reporting one grade for both would be
        telling the player a rule works when it silently does not.
        """
        from aoe2mod.game import ainl as _ainl
        v = self.ailang_vocab()
        p = v.payload
        return {"ok": True,
                "departments": [
                    {"id": "ai", "title": "AI 脚本 (.per)",
                     "note": "引擎内建 AI 语言：defrule/defconst、事实、战略数字"},
                    {"id": "xs", "title": "XS 脚本 (.xs)",
                     "note": "C 风格解释语言；只三件事有官方语料见证：goal、"
                             "xsEffectAmount 生成单位、xsTask"},
                ],
                # Per department: EXAMPLES is keyed by dept, so a bare
                # `list()` here handed the page ["ai", "xs"] -- the two keys --
                # and the example chips rendered the department names.
                "examples": dict((k, list(v))
                                 for k, v in _ainl.EXAMPLES.items()),
                "counts": {
                    "ai_commands": len(p.get("ai_commands") or {}),
                    "ai_facts": len(p.get("ai_facts") or {}),
                    "ai_sn": len(p.get("ai_sn") or ()),
                    "ai_train_names": len(p.get("ai_train_names") or ()),
                    "ai_build_names": len(p.get("ai_build_names") or ()),
                    "xs_syscalls": len(p.get("xs_syscalls") or {}),
                },
                "evidence": {
                    "ai_build_witnessed": len(p.get("ai_build_pool_confirmed") or ()),
                    "ai_build_unwitnessed": sorted(
                        p.get("ai_build_pool_absent") or ()),
                    "ai_train_witnessed": len(p.get("ai_train_pool_confirmed") or ()),
                    "ai_train_unwitnessed": sorted(
                        p.get("ai_train_pool_absent") or ()),
                    "wall_witnessed": sorted(p.get("ai_wall_commands") or ()),
                }}

    def ai_script_edit(self, payload):
        """Chinese (or English) sentence -> one rule of `.per` or one XS block.

        `diagnostics` is the checker's verdict on the emitted code, so the page
        can show the same judgement the editor would: an empty list means every
        head is a known command with the right number of arguments.
        """
        from aoe2mod.game import ainl as _ainl
        dept = (payload.get("dept") or "ai").strip().lower()
        if dept not in ("ai", "xs"):
            return {"ok": False, "error": "dept must be ai or xs"}
        text = payload.get("text") or ""
        r = _ainl.translate(text, dept, self.ailang_vocab())
        return {"ok": True, "dept": dept, "result": r.as_dict()}

    def ai_script_build(self, payload):
        """A whole plan -> a complete `.per` file, plus what it could not express.

        `problems` is never folded into the text: if the player asked for camel
        archers and the engine has no such name, they are told, instead of
        receiving a file that looks complete and trains nothing.
        """
        from aoe2mod.game import aigen as _aigen
        spec = payload.get("plan") or payload
        try:
            plan = _aigen.Plan(
                name=spec.get("name") or "MyAI",
                civ=spec.get("civ") or None,
                army=spec.get("army") or None,
                villagers=spec.get("villagers") or 30,
                attack_at=spec.get("attack_at") or 20,
                age=spec.get("age") or "feudal-age",
                # Passed through raw: `bool("0")` is True, so the route used to
                # turn a posted "0" into "wall the town".  `Plan` reads it.
                wall=spec.get("wall"))
        except (TypeError, ValueError) as exc:
            return {"ok": False, "error": "plan: %s" % exc}
        text, diags, problems = _aigen.check(plan, self.ailang_vocab())
        return {"ok": True, "text": text, "plan": plan.as_dict(),
                "diagnostics": [list(d) for d in diags], "problems": problems}

    def ai_script_check(self, payload):
        """Validate hand-written `.per` or `.xs` text.  Read-only."""
        from aoe2mod.game import ailang as _ailang
        dept = (payload.get("dept") or "ai").strip().lower()
        text = payload.get("text") or ""
        v = self.ailang_vocab()
        fn = _ailang.validate_xs if dept == "xs" else _ailang.validate_ai
        return {"ok": True, "dept": dept,
                "diagnostics": [list(d) for d in fn(text, v)],
                "balanced": _ailang.balanced(_ailang.strip_comments(text))}

    def plan(self, intent):
        return {"ok": True, "plan": self._decorate(self.tk.plan(intent))}

    # ---- which .dat, which script ----------------------------------------
    def dat_sources(self):
        """Every `.dat` on this machine the game could load, for a chooser.

        Reported 2026-11-03: 「我要改指定的dat」.  Reading costs one ``VER x.y``
        head per file (64 bytes inflated), NOT a parse: measured here 18
        candidates answered in 0.06 s.  The file being edited is flagged so the
        screen can mark it without comparing strings itself.
        """
        from aoe2mod.game import datsources as DSR
        cur = os.path.normcase(os.path.abspath(
            getattr(self.tk, "dat_path", "") or ""))
        try:
            items = DSR.candidates(self.game_root)
        except Exception as exc:
            return {"ok": False, "error": _sentence(exc)}
        for it in items:
            it["current"] = os.path.normcase(it["path"]) == cur
            # Editing a mod's `.dat` is an edit the game only reads while that
            # mod is enabled; the screen must be able to say so.
            it["note"] = {
                "game": "游戏平时加载的就是这一份",
                "mode": "选中这个模式时游戏加载它",
                "mod": "这个模组启用时游戏加载它，不启用就白改",
            }.get(it.get("scope"), "")
        # `format N` is the .dat's own FileVersion ordinal, not a game version:
        # a mod built in 2021 and one built last week both read 54 today.  What
        # the player asked for (2026-11-07) -- 「我要显示这个数据模组是哪个版本
        # 的」-- is answered from the FileVersion HEAD plus the record counts, and
        # measuring that costs 0.17-0.35 s per file under the parser lock, so it
        # is answered from the cache here and measured on a worker.
        from aoe2mod.game import datversion as DV
        paths = [it["path"] for it in items]
        base = None
        for it in items:
            if it.get("scope") == "game":
                base = DV.cached(it["path"])
        DV.start_worker(paths)
        for it in items:
            facts = DV.cached(it["path"])
            it["version"] = facts
            it["age"] = DV.compare(facts, base) if facts else None
        return {"ok": True, "current": cur, "sources": items,
                "versions": DV.status(), "base": base}

    def set_dat(self, path):
        """Point the whole session at another `.dat`, dropping every cache.

        The buffers and indexes all belong to the old file -- a 93 MB raw copy,
        decoded field records, the effect table, the tech census -- and reusing
        any of them would show numbers from one file against offsets in
        another.  So this rebuilds the toolkit and clears the session rather
        than patching it, and it reports how many pending edits it dropped,
        because a silent loss of unsaved work is worse than a slow switch.
        """
        from aoe2mod.game import datsources as DSR
        real, err = DSR.check_path(path)
        if err:
            return {"ok": False, "error": err}
        old = os.path.abspath(getattr(self.tk, "dat_path", "") or "")
        if os.path.normcase(real) == os.path.normcase(old):
            return {"ok": True, "dat": real, "changed": False, "dropped": 0}
        # `_edits` is created by the first edit, not by __init__ -- asking for
        # it directly crashed the switch on a fresh session (measured).
        pending = len(self.pending_edits())
        # `progress` is the counter the startup screen draws its bar from, and
        # `Toolkit._ensure` is the only thing that advances it.  Once all six
        # stages sit in `done`, `begin()` returns early -- so without this
        # reset the file we are about to parse reports "100 %, ready" from the
        # first millisecond, which is a bar that lies.  Reset only on a real
        # switch: the `changed: False` return above has to leave the live state
        # alone, and the startup screen polls this same dict to decide when it
        # may hand over to the main page.
        from aoe2mod import progress as PG
        PG.reset()
        with self._lock:
            # Reset and swap under ONE lock.  Every request reads `self.tk` more
            # than once (`_unit_index` reads it for the scan, `session_raw` for
            # the bytes), so a swap visible between those two reads is exactly
            # the mixed-file read that put an EOFError on the player's screen.
            self.reset_session()
            self._tk = A.open_toolkit(game_root=self.game_root, dat_path=real)
        # `vocab` is built from the entity names of the OLD file; a mod that
        # adds 900 units would otherwise be unnameable in a sentence.  The task
        # name map is the same hazard one layer down: a mod renumbers units, and
        # a stale map would label 4X科技's ids with the shipped names.
        self._vocab = None
        self._task_name_cache = {}
        return {"ok": True, "changed": True, "dropped": pending,
                "dat": real, "meta": self.meta()}

    def script_files(self, dept=""):
        """Every `.per`/`.ai`/`.xs` a player could open, for a chooser."""
        from aoe2mod.game import aifiles as AF
        try:
            items = AF.entries(self.game_root, dept=dept or None)
        except Exception as exc:
            return {"ok": False, "error": _sentence(exc)}
        return {"ok": True, "files": items, "max_bytes": AF.MAX_BYTES}

    def script_read(self, path):
        from aoe2mod.game import aifiles as AF
        text, err = AF.read(path, self.game_root)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "path": os.path.abspath(path), "text": text,
                "bytes": len(text.encode("utf-8")), "dept": AF.dept_of(path)}

    def script_write(self, path, text):
        """Save one script.  Refuses anything outside the four script folders."""
        from aoe2mod.game import aifiles as AF
        written, err = AF.write(path, text, self.game_root)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "path": os.path.abspath(path), "bytes": written,
                "dept": AF.dept_of(path)}

    def build(self, intents, title=None, author="", description="", out_dir=None,
              title_auto=False, install=False, profile_root=None):
        """One mod from one or more intents.

        A bundle is the right shape for "these three related edits land together",
        not a convenience loop: two separate mods touching the same .dat is how
        the profile ends up with one silently overriding the other.

        `title_auto` says the page wrote this title from the sentences, rather
        than the player typing it.  Only then is it trimmed to the engine's
        100-byte limit: three Chinese characters cost nine bytes, so a handful
        of sentences passes the limit without anyone writing a long title, and
        the build used to fail with a refusal about bytes.  A title the player
        typed is untouched -- shortening text someone wrote by hand is a
        different act, and it is refused with a sentence that says why.
        """
        if not intents:
            return {"ok": False, "error": "没有可构建的改动"}
        # An empty Author is refused by `emitter.validate_info`, and rightly so:
        # the game will not list a mod whose Author is blank.  But requiring it
        # from the caller made this route stricter than the native engine it
        # replaced -- `desktop/aoe2mod-serve/src/stat_edit.rs:1753` writes
        # `"Author":"aoe2mod"` for every edit it emits, so a tool that posted an
        # intent with no author used to get a mod and now got
        # 「作者不能是空的」.  Measured 2026-10-30: `_probe/test_sprite_target.py`
        # and `_probe/test_bytes_match_reference.py` both broke that way the
        # moment the shipped exe started running this engine.  The page sends
        # "dsh" itself, so this only ever decides for callers that say nothing.
        author = author or "aoe2mod"
        if title_auto and title:
            title = E.fit_auto_title(title)
        if out_dir:
            out_dir = os.path.join(out_dir, _safe_dir(title or "mod"))
        else:
            # One folder per title, the way `rebuild` already does it
            # (`below, out_dir = os.path.join(_out_root(), _safe_dir(title))`).
            # Handing every build the SAME `_mods_out` made `built` name a
            # folder that the next build silently emptied: measured
            # 2026-10-31, a suite that builds eleven cases then reads the .dat
            # out of `built` was reading whichever one happened to run last.
            out_dir = os.path.join(_out_root(), _safe_dir(title or "mod"))
        if len(intents) == 1:
            r = self.tk.build(intents[0], out_dir, title=title, author=author,
                              description=description, overwrite=True)
        else:
            r = self.tk.build_bundle(intents, out_dir, title=title, author=author,
                                     description=description, overwrite=True)
        installed = ""
        if install:
            # The native engine installs as part of the build
            # (`desktop/aoe2mod-serve/src/stat_edit.rs:496`), so a caller that
            # sends `install: true` and then looks for the folder got nothing
            # before this existed.  The mod folder name is the title the build
            # actually used, which is not always the one passed in: a
            # `title_auto` title is trimmed to the engine's 100-byte limit.
            _name = title or (r.get("info") or {}).get("Title") or ""
            got = self.tk.install(r["mod_dir"], name=_name, title=_name,
                                  enabled=True, position=0, overwrite=True,
                                  profile_root=profile_root)
            installed = got.get("mod_dir") or ""
        return self._build_reply(r, installed=installed,
                                 intents=intents)

    def _build_reply(self, man, installed="", intents=None):
        """The build's answer, in the shape the native engine answers in.

        `{"ok": true, "manifest": {...}}` alone was a problem the moment the
        shipped exe started running this engine: every caller written against
        `desktop/aoe2mod-serve/src/stat_edit.rs:461` reads `built`, `civs`,
        `edit_count`, `value` straight off the top level, and got None.  The
        page reads `b.manifest` (`aoe2mod/ui/static/index.html:3744`), so both
        shapes ship: the nested one the page needs, and the flat one the native
        contract promised.  Measured 2026-10-31: seven of the thirteen failing
        suites died on a KeyError for one of these keys.

        `plan()` is called for the extra counts, and it is free here: `build()`
        already ends by calling it for the resolved sentence
        (`aoe2mod/api.py:4048`), so the parse and the locate are warm.
        """
        out = {"ok": True, "manifest": man}
        out["built"] = man.get("mod_dir") or ""
        out["installed"] = installed or ""
        out["edit_count"] = man.get("edit_count")
        # Distinct civilisations, not writes: the native engine calls this
        # `civs` and the write count `edit_count` (see the note in
        # `desktop/aoe2mod-serve/src/stat_edit.rs` above `civ_count`).
        out["civs"] = man.get("civs_edited")
        # `before`/`value` are the field's own endpoints.  A manifest built by
        # a loose-file strategy has no byte patch and therefore no single
        # before/after, so they stay absent rather than being invented.
        if "before" in man:
            out["before"] = man["before"]
        if "value" in man:
            out["value"] = man["value"]
        if len(intents or []) == 1:
            try:
                plan = self.tk.plan(intents[0])
            except Exception:                        # noqa: BLE001
                plan = None
            if plan:
                for key in ("kind", "stat", "op", "amount", "civ_count",
                            "entity_id", "entity_name", "locations",
                            "location_ids", "mirror_count", "description"):
                    if key in plan and out.get(key) is None:
                        out[key] = plan[key]
                # The native engine's `variants` is `family.len()` -- the size
                # of the whole record family, the named unit included
                # (`desktop/aoe2mod-serve/src/stat_edit.rs:452`).  `plan()`
                # carries that as `unit_ids` (the full family, 27 for the
                # villager) and `variants` holds the OTHERS (26).  Reading
                # `variants` here reported 26 for a build that wrote 27
                # records.
                family = plan.get("unit_ids")
                if isinstance(family, list) and family:
                    out["variants"] = len(family)
                elif isinstance(plan.get("variants"), list):
                    out["variants"] = len(plan["variants"]) + 1
        return out

    def stat_apply(self, stat, unit, value=None, delta=None, civs=None,
                   kind="unit", out_dir=None):
        """Write one field change into a throwaway .dat and report the diff.

        This is `/api/stat` from the native engine
        (`desktop/aoe2mod-serve/src/stat_edit.rs:119 pub fn apply`), which this
        server never had -- every caller that used it got a 404 the moment the
        shipped exe started running this engine.  It compiles the same intent
        the editor would, so `edit_count` and `bytes_changed` here are the very
        numbers a build would produce, measured rather than predicted.
        """
        if kind == "tech":
            intent = {"intent": "tech.research_time", "tech": unit,
                      "value": value}
        else:
            intent = {"intent": "unit.stat", "unit": unit, "stat": stat,
                      "value": value}
            if delta is not None:
                intent.pop("value", None)
                intent["delta"] = delta
        if civs:
            intent["civs"] = civs
        from aoe2mod.intent import compiler as C
        rep = C.compile_intent(self.tk.dat_path, intent,
                               parsed=self.tk._parsed, stats=self.tk._stats,
                               game_root=self.tk.game_root)
        patched = C.apply_edits(self.tk._raw, rep["edits"])
        ver = rep["verification"]
        edits = rep["edits"]
        # Where the patched stream landed.  A caller that wants the bytes gets
        # them from disk rather than through JSON: the .dat is 93 MB.
        out = _out_root()
        name = "stat_%s_%s.dat" % (stat or intent["intent"], unit)
        try:
            if not os.path.isdir(out):
                os.makedirs(out)
            path = os.path.join(out, name)
            comp = zlib.compressobj(6, zlib.DEFLATED, -15)
            blob = comp.compress(patched) + comp.flush()
            with open(path, "wb") as fh:
                fh.write(blob)
        except OSError:
            path = ""
        # `before`/`value` are the FIRST edit's own endpoints.  A mirror row is
        # a second Edit at a different offset carrying the same value, so
        # reading edit 0 and edit 1 would report two different "befores" for
        # one change -- the first one is the field the caller named.
        first = edits[0] if edits else None
        return {
            "ok": True,
            "stat": stat,
            "unit": unit,
            "civs": rep["civs_edited"],
            "variants": self._variant_count(intent),
            "edit_count": len(edits),
            # A mirror is a SECOND place the same number is stored (the panel
            # figure and the row the damage maths reads).  Counted from the
            # edits themselves, so a stat with no mirror reports 0 truthfully.
            "mirror_count": sum(1 for e in edits if "mirror" in (e.where or "")),
            "before": first.before if first is not None else None,
            "value": first.after if first is not None else None,
            "bytes_changed": ver["changed_bytes"],
            "out": path,
        }

    def _variant_count(self, intent):
        """How many unit records this intent's family spans, as the native
        engine's `variants` reports it.  One for anything that is not a family.

        `plan()["unit_ids"]` is the whole family; `plan()["variants"]` is the
        others beside the named unit, so reading it here reported 26 for the
        villager, whose scoped build writes 27 records.
        """
        try:
            plan = self.tk.plan(intent)
        except Exception:                            # noqa: BLE001
            return 1
        family = plan.get("unit_ids")
        if isinstance(family, list) and family:
            return len(family)
        others = plan.get("variants")
        if isinstance(others, list):
            return len(others) + 1
        if isinstance(others, int):
            return others or 1
        return 1

    def install(self, mod_dir, name=None, enabled=True, position=0,
                profile_root=None):
        """Copy a built mod into the profile.

        `profile_root` exists so the tests can point at a throwaway folder: the
        one thing a test must never do is edit the player's real mod list, which
        is the mistake that made `_probe/test_install.py` fail for reasons that
        had nothing to do with installing.
        """
        r = self.tk.install(mod_dir, name=name, title=name, enabled=enabled,
                            position=position, overwrite=True,
                            profile_root=profile_root)
        return {"ok": True, "installed": r}

    def mods(self):
        return {"ok": True, "mods": _mods_brief(self.tk)}

    def oplog(self, limit=60):
        r"""The last few operations, plus where the folder is.

        The folder path travels with the answer so the About page can print it:
        「日志在哪」 is the first question a record invites, and a player who has
        to guess between the repository and the exe's folder will guess wrong
        (reported 2026-11-09: 「要不在工具目录创建一个专门的 log 文件夹」).
        """
        try:
            want = int(limit or 60)
        except (TypeError, ValueError):
            want = 60
        rows = OPLOG.tail(want)
        return {"ok": True,
                "dir": OPLOG.log_dir(),
                "files": OPLOG.files()[:31],
                "count": len(rows),
                "rows": rows,
                "keep_days": OPLOG.KEEP_DAYS,
                "day_file": OPLOG.day_path()}

    def open_log_folder(self):
        """Open `log/` in Explorer, creating it first.

        No path from the page: this answers for exactly one folder, which is
        what makes it safe to expose without `/api/open-url`'s scheme guard.
        Windows-only in practice; elsewhere it answers with the path so the
        screen can print it.
        """
        d = OPLOG.log_dir()
        if not d:
            return {"ok": False, "error": "还不知道日志放在哪（这台机器没给出工具目录）"}
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as exc:                       # noqa: BLE001
            return {"ok": False, "error": "建不了日志文件夹：%s" % exc}
        opened = False
        try:
            if hasattr(os, "startfile"):
                os.startfile(d)                        # noqa: S606 - our own folder
                opened = True
            else:
                opened = bool(webbrowser.open("file://" + d))
        except Exception:                              # noqa: BLE001
            # NOT a failure: the folder exists and the page prints its path, so a
            # machine with no file manager still leaves the player holding the
            # record.  Measured 2026-11-09: returning ok=False here made the
            # screen shout 「打不开文件夹」 over a folder it had just created.
            opened = False
        return {"ok": True, "dir": d, "opened": opened}

    def open_url(self, url):
        """Hand one address to the machine's own browser.

        Reported 2026-11-08: 「链接给个可直接打开的功能」.  The About page could
        only copy an address, and the reason it could not simply link was real --
        this window is a WebView pointed at the local server, so `<a href>` would
        replace the workshop with somebody else's page and there is no Back
        button to come home with.  Opening it in the SYSTEM browser is the other
        way to make a link clickable: the workshop keeps its window, the browser
        gets a tab.

        The guard is the SCHEME, not a host list.  `webbrowser` on Windows goes
        through `os.startfile`, which honours `file:` and will launch a local
        executable -- so a route that opens whatever it is handed is a "run this"
        primitive with a friendly name.  http and https only; anything else is
        refused with a sentence the screen can print, which is cheaper than
        explaining a launched program.
        """
        want = str(url or "").strip()
        if not want:
            return {"ok": False, "error": "没有给出要打开的地址"}
        low = want.lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            return {"ok": False,
                    "error": "只能打开 http 或 https 的地址，收到的是「%s」" % want[:60]}
        try:
            opened = webbrowser.open(want, new=2)
        except Exception as exc:                       # noqa: BLE001
            return {"ok": False, "error": "打不开这个地址：%s" % exc}
        if not opened:
            return {"ok": False,
                    "error": "系统没有接住这个地址，可以点「复制链接」自己贴到浏览器里"}
        return {"ok": True, "url": want, "opened": True}

    def mod_thumbnail(self, name):
        """One installed mod's picture, as the bytes on disk.

        The route is fed a name from the page, so the name is resolved against
        `tk.mods()` first: the set of openable folders is exactly the set the
        engine's own status file lists, and a name that is not in it never
        reaches `os.path.join`.

        Answers `content_type` as well as the bytes because the shipped files are
        not all PNG (measured 2026-11-06: 12 `.png`, 5 `.jpg`).
        """
        want = str(name or "")
        row = None
        for m in self.tk.mods():
            if m.get("name") == want:
                row = m
                break
        if row is None:
            return {"ok": False, "error": "没有叫「%s」的模组" % want}
        info, thumb = _mod_card(row)
        if not thumb:
            return {"ok": False, "error": "这个模组没有缩略图"}
        path = os.path.join(row.get("path") or "", thumb)
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError as exc:
            return {"ok": False, "error": "缩略图读不出来：%s" % exc}
        ctype = "image/jpeg" if thumb.lower().endswith((".jpg", ".jpeg")) else "image/png"
        return {"ok": True, "png": body, "content_type": ctype,
                "bytes": len(body)}

    def set_mod(self, name, enabled, profile_root=None):
        """Turn an installed mod on or off.

        ``profile_root`` is for tests, exactly as in ``install()``: this route
        writes the player's mod list, so a test that cannot point it elsewhere
        cannot test it at all -- which is why it was the one route with no
        assertion behind it.
        """
        r = self.tk.set_mod_enabled(name, enabled, profile_root=profile_root)
        return {"ok": True, "mods": _mods_brief(self.tk),
                "running_warning": r.get("running_warning"),
                "game_running": r.get("game_running")}

    def move_mod(self, name, delta, profile_root=None):
        """Move an installed mod one step in load order.

        `delta=-1` is up (higher priority = wins a shared path), `+1` is down.
        The answer carries the redrawn list so the page never has to guess what
        the new order is.
        """
        got = self.tk.move_mod(name, int(delta), profile_root=profile_root)
        return {"ok": True, "move": got, "mods": _mods_brief(self.tk),
                "running_warning": got.get("running_warning")}

    def move_mod_to(self, name, position, profile_root=None):
        """Put an installed mod at one place in load order (a drag, not an arrow).

        The answer carries the redrawn list for the same reason `move_mod` does:
        the page must not have to guess where the row landed.
        """
        got = self.tk.move_mod_to(name, int(position), profile_root=profile_root)
        return {"ok": True, "move": got, "mods": _mods_brief(self.tk),
                "running_warning": got.get("running_warning")}

    def uninstall(self, name, profile_root=None):
        r = self.tk.uninstall(name, profile_root=profile_root)
        return {"ok": True, "mods": _mods_brief(self.tk),
                "running_warning": r.get("running_warning"),
                "game_running": r.get("game_running")}

    def update_check(self):
        """Has the game's data moved since the installed mods were built?

        Cheap on purpose: 0.009 s for one hash plus a 64-byte inflate of the
        version head, so the screen can call it on load.  The expensive
        confirmation (inflate + hash the raw stream) only runs for a mod whose
        base file hash actually changed -- see `mod/provenance.py`.
        """
        got = self.tk.update_check()
        for row in got.get("rows") or []:
            row["status_zh"] = status_zh(row.get("status"))
        got["banner"] = _banner(got)
        # The native engine answers flat -- `{"ok":true,"rows":[…],
        # "attention":…,"state":…}` (`desktop/aoe2mod-serve/src/updates.rs::
        # to_json`) -- and every caller written before the shipped exe started
        # running this engine reads `u["rows"]`.  The page reads the nested
        # `update` key, so both are served: measured 2026-10-31,
        # `_probe/test_e2e_shipped.py:141` found zero rows and reported that
        # update-check did not know about two mods it had just built.
        out = {"ok": True, "update": got}
        for key in ("rows", "attention", "state"):
            if key in got:
                out[key] = got[key]
        return out

    def repair_check(self, profile_root=None):
        """Which installed mods ship a `.dat` the game has since outgrown.

        Cost, measured 2026-10-23 on this machine: 16 mods, 3-12 s of parsing
        each, so this is a button press rather than a load-time call -- unlike
        `update_check`, which only hashes two files and can run on every page
        load.  The screen asks for it on demand and says it is slow.
        """
        return self.tk.repair_check(profile_root=profile_root)

    def repair_apply(self, name, profile_root=None, out_dir=None):
        """Rebuild one installed mod's `.dat` from today's data and reinstall it.

        Same cost as one `repair_check` row (3-12 s of parsing) plus a full
        rebuild and install, so it is a button press on a mod the player has
        chosen -- never something that runs because a page loaded.

        ``profile_root`` exists for the same reason as everywhere else: the tests
        must be able to point at a throwaway profile instead of the player's.
        """
        return self.tk.repair_apply(name, out_dir=out_dir,
                                    profile_root=profile_root)

    # ---- carrying a mod's edits onto a NEW official build ----------------
    #
    # `repair_*` answers with the intent vocabulary, which cannot express an
    # added record, a moved effect command or an icon slot -- so a mod that did
    # any of those comes back `manual` and the player is left to redo it by hand.
    # The two calls below ask the same question at the byte level instead, which
    # is what makes a mod that added a unit survive a patch.

    def upgrade_check(self, name=None, profile_root=None, limit=40,
                      base_dat=None, new_dat=None):
        """Can each installed data mod be carried onto today's official build?

        Read-only.  Before looking, it files the game's current `.dat` into the
        version archive: the build the mods were made from has to be captured
        while it still exists on disk, because the patch that creates the need
        for this call also deletes the evidence.
        """
        return self.tk.upgrade_check(name=name, profile_root=profile_root,
                                     limit=limit, base_dat=base_dat,
                                     new_dat=new_dat)

    def upgrade_apply(self, name=None, mod_dat=None, out_dir=None, title=None,
                      base_dat=None, new_dat=None, install=True,
                      profile_root=None, official_wins=False, force=False):
        """Carry one mod's edits onto today's official build and reinstall it.

        Cost: one analysis plus one rewrite, measured 22 s cold on this machine
        with the parse caches warm and 50 s on the first call of a process --
        hence a button per mod, never a page load.
        """
        return self.tk.upgrade_apply(
            name=name, mod_dat=mod_dat, out_dir=out_dir, title=title,
            base_dat=base_dat, new_dat=new_dat, install=install,
            profile_root=profile_root, official_wins=official_wins,
            force=force)

    def rebuild(self, title, profile_root=None):
        """Rebuild a stale mod from the intents its record kept, then reinstall.

        This is the whole point of storing the intents: after an official patch
        the user should not have to remember the sentence they wrote weeks ago.
        Anything missing is reported, never approximated -- a rebuild that
        guessed would ship a different mod under the same name.

        `profile_root` is for tests, exactly as in `install()`: the one thing a
        test must never do is edit the player's real mod list.
        """
        from aoe2mod.mod import provenance as PV
        doc = PV.load()
        entry = (doc.get("builds") or {}).get(title)
        if entry is None:
            return {"ok": False,
                    "error": "没有「%s」的构建记录，没法按原样重建" % title}
        intents = entry.get("intents")
        if not intents:
            return {"ok": False,
                    "error": "「%s」的记录里没有留下当初的改动，需要重新说一遍"
                             % title}
        fs, others = _split_field_intents(intents)
        out_dir = os.path.join(_out_root(), _safe_dir(title))
        if fs and not others:
            # The whole record is field edits, and those never went through the
            # intent compiler -- they were written straight into the session
            # buffer.  `self.build()` would hand `unit.field` to `C.resolve()`
            # and die with "unknown intent", which is what this branch exists to
            # stop: measured 2026-10-30, that message was the ONLY thing a player
            # saw for all nine of the field builds in `builds.json`.
            got = self._rebuild_fields(fs, title=title, author=entry.get("author"),
                                       description=entry.get("description"),
                                       out_dir=out_dir)
        elif fs:
            # Mixed: compile the sentences first, then lay the field writes on
            # the stream the compiler produced.  That order is forced -- the
            # compiler may APPEND records (a new unit, an effect), which moves
            # every byte after the append point, so field offsets resolved
            # against the game's file would land in the wrong place.
            got = self._rebuild_mixed(fs, others, title=title,
                                      author=entry.get("author"),
                                      description=entry.get("description"),
                                      out_dir=out_dir)
        else:
            built = self.build(others, title=title,
                               author=entry.get("author") or "dsh",
                               description=entry.get("description") or "",
                               out_dir=out_dir)
            if not built.get("ok"):
                return built
            got = {"ok": True, "manifest": built["manifest"]}
        if not got.get("ok"):
            return got
        man = got["manifest"]
        installed = self.tk.install(man["mod_dir"], name=title, title=title,
                                    enabled=True, position=0, overwrite=True,
                                    profile_root=profile_root)
        # Same flat shape a fresh build answers in.  A rebuild used to reply with
        # `manifest` only, so a caller that asked "how many edits, how many
        # civilisations" got None for both even though the record's intents were
        # in hand -- measured 2026-10-31 in `_probe/test_rebuild_installs.py`.
        out = self._build_reply(man, installed=(installed or {}).get("mod_dir") or "",
                                intents=intents)
        out["replayed"] = got.get("replayed")
        out["installed_detail"] = installed
        out["title"] = title
        out["author"] = entry.get("author") or ""
        # `rebuilt` is what the native engine nests the whole build answer
        # under (`desktop/aoe2mod-serve/src/rebuild.rs:148 "rebuilt": built`),
        # and it is the key callers read the counts from.  Both levels carry the
        # same numbers so neither shape has to be guessed at.
        out["rebuilt"] = {k: v for k, v in out.items() if k != "rebuilt"}
        return out

    # ---- replaying field edits after a patch ----------------------------
    def _replay_fields(self, edits, base):
        """Apply every field intent to `base` (raw bytes).  Never guesses.

        `base` is the stream the result has to live on: the game's own file for
        a pure field build, the compiler's output for a mixed one.  Offsets are
        resolved against THIS stream, not against whatever the record captured
        months ago -- a patch moves records, and a stored offset would write into
        a neighbouring field while reporting success.

        Returns ``{ok, buf, applied, refused}``.  One refusal does not abort the
        rest: the caller reports which sentences survived, because "eight of your
        nine edits came back" is useful and "unknown intent" is not.
        """
        from aoe2mod.dat import tablefields as TF
        buf = bytearray(base)
        civs, _cs, gv, _tail = L.locate(bytes(buf), parser=None)
        applied, refused = [], []
        # One scan per (kind) for the whole batch.  Each scan walks 93 MB and
        # takes ~7 s, so re-scanning per edit would turn nine edits into a
        # minute of waiting; and the scan must be redone after a write only if
        # the write changes a length, which a fixed-width field never does.
        idx = {}
        for e in edits:
            if e.get("intent") == "table.field":
                # A third id space, so a third scan space.  Re-resolved here for
                # the same reason the other two are: the record's position is
                # what the intent stores, and a patch can move it.
                tid = e.get("table")
                got = TF.plan(tid, bytes(buf), gv,
                              self._table_index(tid).get(e.get("record")) or {},
                              e.get("field"), e.get("value"))
                if not got.get("ok"):
                    refused.append({"intent": e, "error": got.get("error"),
                                    "unchanged": bool(got.get("unchanged"))})
                    continue
                res = TF.apply(buf, got["offset"], got["packed"])
                if not res["changed"]:
                    refused.append({"intent": e,
                                    "error": "写下去和原值字节一样，这次重建没有改动它",
                                    "unchanged": True})
                    continue
                applied.append({"intent": e, "field": got["field"],
                                "label": got["label"], "was": got["before"],
                                "now": got["value"], "offset": got["offset"]})
                continue
            kind = "tech" if e.get("intent") == "tech.field" else "unit"
            if kind not in idx:
                idx[kind] = FW.index(kind, bytes(buf), gv)
            if kind == "tech":
                tid = e.get("tech")
                rec = idx[kind].get(tid) if isinstance(tid, int) else None
                what = "科技 %s" % (tid,)
                civ_all = False
            else:
                civ_key = str(e.get("civ") or "").strip()
                civ_i = self.tk._civ_index(civ_key) if civ_key and civ_key != "*" else (
                    1 if len(civs) > 1 else 0)
                uid = e.get("unit")
                rec = idx[kind].get((civ_i, uid)) if isinstance(uid, int) else None
                what = "%s 的第 %s 号单位" % (
                    (civs[civ_i].get("name") if 0 <= civ_i < len(civs) else civ_i),
                    uid)
                # `civ_all` (or a literal `civ:"*"`) means the build wrote every
                # civilisation's copy.  A replay that quietly redid one of them
                # would produce a mod that looks right and behaves like the
                # single-civ editor this flag exists to stop being the default.
                civ_all = bool(e.get("civ_all")) or civ_key == "*"
            if rec is None:
                refused.append({"intent": e,
                                "error": "重建时的数据里找不到%s" % (what,)})
                continue
            if civ_all and isinstance(e.get("unit"), int):
                # One plan per copy, each against its OWN record, because the
                # copies need not share a layout.
                here = []
                for (ci, u), r in idx["unit"].items():
                    if u == e["unit"]:
                        here.append((ci, r))
                if not here:
                    refused.append({"intent": e,
                                    "error": "重建时的数据里找不到%s" % (what,)})
                    continue
                done, why = 0, []
                first = None   # one copy's label/before, reported for the whole
                for ci, r in sorted(here):
                    p = FW.plan("unit", bytes(buf), gv, r, e.get("field"),
                                e.get("value"))
                    if not p.get("ok"):
                        why.append(p.get("error"))
                        continue
                    if not FW.apply(buf, p["offset"], p["packed"])["changed"]:
                        continue
                    if first is None:
                        # `was` is only meaningful per copy (the variants differ),
                        # so the report carries the reference copy's old value and
                        # `copies` says how many were written.  A caller that needs
                        # every old value can re-read them; the panel shows one.
                        first = p
                    done += 1
                if not done:
                    refused.append({"intent": e,
                                    "error": why[0] if why else
                                    "写下去和原值字节一样，这次重建没有改动它",
                                    "unchanged": True})
                else:
                    applied.append({"intent": e, "field": e.get("field"),
                                    "label": (first or {}).get("label")
                                    or e.get("field"),
                                    "was": (first or {}).get("before"),
                                    "now": e.get("value"), "copies": done})
                continue
            p = FW.plan(kind, bytes(buf), gv, rec, e.get("field"), e.get("value"))
            if not p.get("ok"):
                # `unchanged` is not a failure worth alarming about, but it must
                # still be reported: the mod will not contain that edit.
                refused.append({"intent": e, "error": p.get("error"),
                                "unchanged": bool(p.get("unchanged"))})
                continue
            res = FW.apply(buf, p["offset"], p["packed"])
            if not res["changed"]:
                refused.append({"intent": e,
                                "error": "写下去和原值字节一样，这次重建没有改动它",
                                "unchanged": True})
                continue
            applied.append({"intent": e, "field": p["field"],
                            "label": p["label"], "was": p["before"],
                            "now": p["value"], "offset": p["offset"]})
        return {"ok": True, "buf": bytes(buf), "applied": applied,
                "refused": refused}

    def _emit_replay(self, buf, title, author, description, out_dir, applied,
                     refused):
        """Write the replayed stream as one installable data mod."""
        tk = self.tk
        info = E.make_info(title or "rebuild", author=author or "dsh",
                           description=description or "")
        man = E.emit_data_mod(out_dir, buf, info, base_dir=tk.game_root,
                              overwrite=True)
        # Read the file back.  A rebuild's whole promise is that the result opens
        # in the game, and the only cheap proof is that the engine's own parser
        # walks it to the last byte.
        raw2, how2 = P.load_dat(man["dat"])
        p2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            p2.parse()
        man["reparse_ok"] = (p2.r.pos == len(raw2))
        man["reloaded_with"] = how2
        man["replayed_fields"] = len(applied)
        return {"ok": True, "manifest": man,
                "replayed": {"applied": len(applied), "refused": refused,
                             "edits": [{k: a[k] for k in
                                        ("field", "label", "was", "now")}
                                       for a in applied]}}

    def _rebuild_fields(self, fs, title=None, author=None, description=None,
                        out_dir=None):
        """A build whose every intent is a field edit: patch the game file."""
        tk = self.tk
        tk._ensure()
        got = self._replay_fields(fs, tk._raw)
        return self._emit_replay(got["buf"], title, author, description, out_dir,
                                 got["applied"], got["refused"])

    def _rebuild_mixed(self, fs, others, title=None, author=None,
                       description=None, out_dir=None):
        """Sentences first, field writes on top of what they produced.

        The field edits go last because the compiler can APPEND records, and an
        append moves every byte after it: offsets resolved before the append
        would point at the wrong field afterwards.
        """
        built = self.build(others, title=title, author=author or "dsh",
                           description=description or "", out_dir=out_dir)
        if not built.get("ok"):
            return built
        man = built["manifest"]
        base = man.get("dat")
        if not base:
            # None of the sentences touched the `.dat`, so the field edits have
            # nothing to be laid on -- they are the whole mod.
            self.tk._ensure()
            got = self._replay_fields(fs, self.tk._raw)
        else:
            raw_c, _how = P.load_dat(base)
            got = self._replay_fields(fs, raw_c)
        return self._emit_replay(got["buf"], title, author, description, out_dir,
                                 got["applied"], got["refused"])

    # ---- helpers --------------------------------------------------------
    def _decorate(self, plan):
        """Turn the plan's civilization scope into names the screen can print.

        Two shapes arrive here, and that is a wart in the product rather than a
        choice made here: `unit.stat` reports `.dat` INDICES in `civs` while
        `unit.availability` reports NAMES.  The screen used to join whichever it
        got straight into "范围 ...", so a stat edit printed "范围 1、2、3".  Both
        shapes are accepted, the raw `civs` is left untouched for callers that
        want it, and a parallel `civ_labels` always carries printable Chinese.
        """
        if not isinstance(plan, dict):
            return plan
        scope = plan.get("civs")
        if not isinstance(scope, (list, tuple)) or not scope:
            return plan
        names = list(self.tk.civ_names or ())
        labels = []
        for item in scope:
            if isinstance(item, int):
                en = names[item] if 0 <= item < len(names) else str(item)
            else:
                en = item
            # `civnames.chinese` resolves all three spellings the game uses
            # (the .dat's `British`, the tree stem `BRITONS`, lower case) --
            # folding alone would leave `BRITONS` untranslated, which is what
            # the first version of this did.
            labels.append(CN.chinese(en))
        return dict(plan, civ_labels=labels)

    def _safe_plan(self, intent):
        """A preview that turns a refusal into data instead of a 500."""
        try:
            return {"ok": True, "plan": self._decorate(self.tk.plan(intent))}
        except Exception as exc:                       # noqa: BLE001
            return {"ok": False, "error": _sentence(exc)}


def _load_schema():
    from aoe2mod.intent import compiler as C
    return C.load_schema()


def _ships_dat(tk, m):
    """Does this installed mod carry a whole `empires2_x2_p1.dat`?

    A match loads exactly ONE data mod (measured 2026-10-18: `rename` is a data
    mod, one per match), so a player looking at a list of twenty needs to see
    which of them are competing for that single place.  Without this the screen
    says "installed" and the game quietly uses somebody else's data.

    The file itself is the only honest test: `info.json` carries no flag for it,
    and a mod can be a data mod by carrying a `.dat` without ever touching a
    unit.  One `os.path.isfile` per mod is cheap next to parsing 93 MB.
    """
    path = m.get("path")
    if not path or not m.get("exists"):
        return False
    rel = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
    try:
        return os.path.isfile(os.path.join(path, rel))
    except OSError:
        return False


#: The picture file names the game itself looks for, in the order it prefers
#: them.  Measured 2026-11-06 on 23 installed mods: 12 carry `thumbnail.png`, 5
#: carry `thumbnail.jpg`, 6 carry neither.  No other name appears anywhere.
THUMB_NAMES = ("thumbnail.png", "thumbnail.jpg")


def _mod_card(m):
    """-> (info dict, thumbnail file name or None) for one installed mod.

    Deliberately tolerant: a community mod's `info.json` is written by the
    Workshop uploader and this project has already hit one that carries bare CRs
    inside Description (`aoe2mod/mod/emitter.py` reads those with `strict=False`).
    A card that refuses to draw because the description will not parse would be
    worse than a card with no description, so every failure degrades to an empty
    dict rather than raising.

    `exists` is checked first: `mod-status.json` keeps entries for folders the
    player deleted, and joining a path under a missing folder is how a route ends
    up reporting a FileNotFoundError as "this mod is broken".
    """
    path = m.get("path")
    if not path or not m.get("exists"):
        return {}, None
    info = {}
    try:
        ip = os.path.join(path, "info.json")
        if os.path.isfile(ip):
            from aoe2mod.mod import emitter as E
            got = E.read_info_json(ip)
            if isinstance(got, dict):
                info = got
    except Exception:                                  # noqa: BLE001
        info = {}
    thumb = None
    for name in THUMB_NAMES:
        try:
            if os.path.isfile(os.path.join(path, name)):
                thumb = name
                break
        except OSError:
            continue
    return info, thumb


def _mods_brief(tk):
    """Mods, with the fields a screen shows and nothing that leaks a path.

    `ships_dat` and `dat_rank` exist because the one thing a player cannot see
    anywhere else is WHICH mod the next match will actually load.  The game
    hides that in a dropdown on the create-game screen, and the page used to
    point at the mods screen, which has no such dropdown.
    """
    rows = tk.mods()
    out = []
    for m in rows:
        info, thumb = _mod_card(m)
        out.append({"name": m.get("name"), "title": m.get("title") or m.get("name"),
                    "enabled": bool(m.get("enabled")), "kind": m.get("kind"),
                    "priority": m.get("priority"),
                    "ships_dat": _ships_dat(tk, m),
                    # The card view needs words and a picture flag; the list view
                    # ignores both.  `thumb` is the FILE NAME rather than a URL so
                    # the page never has to build a query string, and `None` means
                    # "draw the placeholder", not "not loaded yet".
                    "author": info.get("Author"),
                    "description": info.get("Description"),
                    "thumb": thumb,
                    "exists": bool(m.get("exists")),
                    "workshop_id": m.get("workshop_id")})
    # Among the ENABLED data mods, which one wins is decided by the game, not by
    # us: the highest priority.  Saying "13 compete" without saying which one is
    # in front would tell the player there is a problem and hide the answer.
    live = [r for r in out if r["ships_dat"] and r["enabled"]]
    live.sort(key=lambda r: -(r.get("priority") or 0))
    for i, r in enumerate(live):
        r["dat_rank"] = i + 1
    for r in out:
        r.setdefault("dat_rank", None)
        r["dat_competing"] = len(live)
    _pair_rows(out)
    return out


# The interface half of a split build is titled `<base>（界面）`.  That is the only
# thing on disk that ties the two folders together, so it is also what the screen
# has to read: the player made ONE decision ("use this build"), and a list that
# shows two unrelated switches invites turning off half of it -- a state measured
# to draw nothing on the icon layer while looking perfectly normal.
UI_HALF_WORD = "\uff08\u754c\u9762\uff09"


def _pair_rows(rows):
    """Mark the two folders of a split build so a screen can show them as one.

    Adds `role` ("data" / "ui") and `paired_with` (the sibling's title) to both
    halves.  Rows whose sibling is not installed keep `role: None` -- an interface
    mod installed on its own is a real state (an old build's leftovers), and
    pretending otherwise would hide it.
    """
    by_title = {}
    for r in rows:
        t = str(r.get("title") or "")
        if t:
            by_title[t] = r
    for r in rows:
        title = str(r.get("title") or "")
        if title.endswith(UI_HALF_WORD) and len(title) > len(UI_HALF_WORD):
            base = by_title.get(title[: -len(UI_HALF_WORD)])
            if base is not None and base is not r:
                r["role"] = "ui"
                r["paired_with"] = base.get("title")
                base["role"] = "data"
                base["paired_with"] = title
    for r in rows:
        r.setdefault("role", None)
        r.setdefault("paired_with", None)
    return rows


# Status words the update guard reports.  They now come from the locale table
# (`aoe2mod/schema/locales/zh.json`), so a heading and a status word live in the
# same place and one nail can read both.  A thin function rather than a dict
# because the fallback matters: a status this table has never heard of (a newer
# `provenance.py`) must print its machine value, not the key `status.xyz`.
def status_zh(status):
    if not status:
        return ""
    key = "status.%s" % status
    text = _LOCALE.get(key)
    return text if text is not None else str(status)


def _scan_reporter(key):
    """An `on_progress` callback that feeds `aoe2mod/jobs.py` for job `key`.

    WHY A FACTORY: the scanners report **bytes walked**, and the screen draws a
    percentage; this is the one place that knows both, so the conversion lives
    here rather than in two scanners.  Returning None when nothing would be
    learned keeps the call site readable.

    WHY NOT RAISE: this runs inside `parser._PARSE_LOCK` on a request thread.  An
    exception here would abort a 10 s scan and turn "opening the editor is slow"
    into "the editor is broken".  A dropped progress callback is the correct
    failure -- the bar simply stops one step short and the job's `finish()`
    lands it on 100 %.
    """
    from aoe2mod import jobs as J

    def report(pos):
        try:
            J.update(key, pos)
        except Exception:
            pass

    return report


def _disk_bytes(path):
    """The file's size as a file manager reports it, or 0.

    Deliberately not `len(raw)`: the .dat is stored compressed by the game and
    the parser works on the expanded stream, so the two numbers differ by 7.8x
    on this install (11,963,833 on disk vs 93,272,287 expanded).  Reported
    2026-11-03: 「你这个大小不对啊」 -- the rail was printing the expanded one.
    """
    try:
        return os.path.getsize(path or "")
    except OSError:
        return 0


def _game_version(tk):
    """Which release of the game this install is, or None."""
    try:
        return GV.banner(getattr(tk, "game_root", "") or "")
    except Exception:                  # a missing exe is normal, not an error
        return None


def _civ_zh_of(tk, stem):
    """The Chinese name of a civ-tree stem, or the stem itself.

    The tech trees are keyed like the game's own files (`BRITONS`, `DRAVIDIANS`),
    and a screen a Chinese player reads must not print that; `CN.chinese` already
    accepts all three spellings the data uses.  An unknown stem is returned
    unchanged rather than blanked: a new civilization in a future patch should
    read as its own file name, not disappear from the answer.
    """
    # Gaia is civ index 0 in every .dat and is NOT a playable civilization, so
    # `civnames.CIV_ZH` deliberately has no entry for it (that table is also the
    # sentence reader's vocabulary, and teaching it a word the game never offers
    # would let 「盖亚血量加10」 parse as a real edit).  It still shows up as the
    # first row of the civilization picker, where an English word is the one
    # thing this screen must not print -- so the display name lives here.
    _EXTRA = {"gaia": "盖亚"}
    _k = re.sub(r"[\s_\-]+", "", str(stem or "")).upper()
    if _k in ("GAIA",):
        return _EXTRA["gaia"]
    try:
        return CN.chinese(stem) or stem
    except Exception:
        return stem


def _banner(got):
    """The one sentence a screen shows at the top, or None when there is none.

    Only `stale` earns a banner.  `unknown` deliberately does not: it means "I
    cannot know", and a warning nobody can act on teaches people to ignore the
    ones they can.
    """
    stale = [r for r in got.get("rows") or [] if r.get("status") == "stale"]
    if stale:
        names = "、".join((r.get("name") or "?") for r in stale[:3])
        more = "" if len(stale) <= 3 else "等 %d 个" % len(stale)
        return _LOCALE_TEXT(
            "update.banner", {"names": names + more})
    return None


class _BadId(Exception):
    """A query parameter that should be a comma-separated id list is not one.

    Its own class so `/api/civ` can say WHICH parameter and WHICH token, instead
    of the `int()` ValueError a player would read as "the tool is broken".
    """


#: The sentence `/api/civ` sends with every answer.  Verbatim the native build's
#: (`desktop/aoe2mod-serve/src/civtree.rs`), because the page prints it and two
#: engines wording the same fact differently is a difference a player sees.
_CIV_STATUS_NOTE = (
    "状态来自游戏自己的 CivTechTrees/<CIV>.json；"
    "available 开局就有，gated 要先研究科技，"
    "unavailable 这个文明没有，unknown 这个文件不描述它")


def _tool_root():
    r"""The folder the player calls "the tool", i.e. where `log/` goes.

    Same three-levels-up walk as `_out_root`, with the same "do not write inside
    `app/`" rule and for the same measured reason (2026-11-02: the package grew
    from 50.9 MB to 1.7 GB because build output landed in `app/_mods_out/`).
    Kept as its own function rather than folded into `_out_root` because the
    two are allowed to diverge later -- the log is a record, the build folder is
    scratch, and a player who moves one will not necessarily move the other.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.basename(root).lower() == "app":
        bundle = os.path.dirname(root)
        if os.path.isdir(os.path.join(bundle, "runtime")):
            return bundle
    return root


def _op_detail(route, payload, result):
    """What the log should remember about one operation.

    Deliberately narrow: the payload's whitelisted keys plus the result's
    whitelisted keys, and the payload loses every long string first.  `/api/
    sprite` posts a whole sprite family and `/api/icon-set` can carry PNG bytes;
    neither belongs in a line a human reads.
    """
    detail = {}
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, (str, bytes, bytearray)) and len(v) > 200:
                continue
            detail[k] = v
    if isinstance(result, dict):
        for k, v in result.items():
            if k in ("tree", "boxes", "edits", "entity", "rows", "units",
                     "icon", "icons", "png", "text", "body"):
                continue
            detail.setdefault(k, v)
    return detail


def _out_root():
    r"""Where emitted mod folders go.

    `AOE2MOD_BUILD_OUT` overrides it.  `_mods_out/` is one fixed path in the
    workspace, so two runs at once -- two suites, or a suite beside the page --
    emit into the SAME folder per title and delete each other's output halfway
    through.  Measured 2026-10-30: `_probe/test_rebuild_fields.py` failed with
    `emitted mod folder not found: '...\_mods_out\rb blanket field'` while a
    second runner held the folder, and `_probe/test_rebuild.py` had already been
    setting this env var for a temp dir that nothing read.
    """
    override = os.environ.get("AOE2MOD_BUILD_OUT")
    if override:
        # A relative override must not mean two different folders.  `abspath`
        # here resolves against THIS process's cwd, which is not necessarily the
        # repo -- so it fixes the ambiguity only for a server started from the
        # repo.  `_probe/run_suites.py` therefore absolutises the value once,
        # before any child sees it; this line only keeps a hand-set relative
        # value honest for a server started in the repo.
        return os.path.abspath(override)
    # Three levels up is the REPO for a source checkout (`<repo>/aoe2mod/ui/
    # server.py`) and `<bundle>/app` for the shipped package.  Those are two
    # different promises: the first is a scratch folder, the second is part of
    # what gets zipped and handed to a player.  Measured 2026-11-02: the package
    # had grown from 50.9 MB to 1.7 GB with 77 mod folders inside
    # `app/_mods_out/`, written by suites that ran the exe without setting
    # `AOE2MOD_BUILD_OUT`.  Nothing broke -- the exe still starts -- which is
    # why it went unnoticed for days.
    #
    # So: if this file sits inside an `app/` folder that has a sibling exe, the
    # engine is the shipped copy and output goes BESIDE the bundle, not in it.
    here = os.path.dirname(os.path.abspath(__file__))       # .../aoe2mod/ui
    root = os.path.dirname(os.path.dirname(here))           # .../app  or the repo
    if os.path.basename(root).lower() == "app":
        bundle = os.path.dirname(root)
        if os.path.isdir(os.path.join(bundle, "runtime")):
            return os.path.join(bundle, "_mods_out")
    return os.path.join(root, "_mods_out")


def _safe_dir(title):
    """A folder name for a mod title that the filesystem will accept."""
    keep = "-_ ()（）[]【】·"
    out = "".join(c for c in str(title or "mod")
                  if c.isalnum() or c in keep).strip()
    return (out or "mod")[:60]


# ---- HTTP wiring --------------------------------------------------------
def _json_default(obj):
    """Last resort for values JSON has no idea about.

    A successful build used to answer `{"ok": false, "error": "Object of type
    bytes is not JSON serializable"}` because the writer's report carries two
    byte strings it compared, and that report rides inside the manifest.
    Measured 2026-11-01 on the sprite rename model.  The manifest is now cleaned
    where it is built (`api._json_safe`), and this is the belt to that
    braces: a route must never turn a finished mod into an error page because
    one leaf of its report is binary.  Hex for bytes (compared by eye in a
    log), and a type name for anything else rather than an exception.
    """
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).hex()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    return "%s(%s)" % (type(obj).__name__, obj)


def _json(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False,
                      default=_json_default).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _html(handler, text, code=200):
    """Write an HTML string with the same no-store header the page route uses."""
    body = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _file(handler, path, ctype):
    with open(path, "rb") as fh:
        body = fh.read()
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    if os.path.splitext(path)[1].lower() in _CACHEABLE:
        handler.send_header("Cache-Control", "max-age=86400")
    handler.send_header("Content-Length", str(len(body)))
    # No caching: these files are read off the local disk on every request, so a
    # cache buys nothing -- and it costs a real bug.  Measured 2026-10-26: the
    # window shell kept showing the page from before a fix (the CSS fix was in
    # the file on disk, and the window still drew the old layout), because
    # WebView2 heuristically caches a response that carries no cache header.
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


_CTYPES = {".html": "text/html; charset=utf-8",
           ".css": "text/css; charset=utf-8",
           ".js": "application/javascript; charset=utf-8",
           ".svg": "image/svg+xml",
           ".png": "image/png",
           # A font served as octet-stream is a font the browser refuses to use;
           # `@font-face` then silently keeps the fallback face.
           ".ttf": "font/ttf",
           ".woff2": "font/woff2",
           ".jpg": "image/jpeg",
           ".jpeg": "image/jpeg",
           ".json": "application/json; charset=utf-8"}

# Art never changes within an install, and the frame is 460 KB.  The page itself
# must stay `no-store` -- it is what a rebuild replaces.
_CACHEABLE = (".png", ".jpg", ".jpeg", ".ttf", ".woff2", ".svg")


def make_handler(app):
    """A `http.server.BaseHTTPRequestHandler` subclass bound to one App."""
    try:
        from http.server import BaseHTTPRequestHandler
    except ImportError:                                # pragma: no cover
        from BaseHTTPServer import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        server_version = "aoe2mod-ui"

        def log_message(self, fmt, *args):
            # The default writes every request to stderr; a screen that previews
            # on each keystroke would bury a real traceback in it.
            pass

        # ---- static ----
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return _file(self, os.path.join(STATIC_DIR, "index.html"),
                             _CTYPES[".html"])
            if path.startswith("/static/"):
                rel = path[len("/static/"):].replace("\\", "/")
                full = os.path.normpath(os.path.join(STATIC_DIR, rel))
                if not full.startswith(os.path.normpath(STATIC_DIR)):
                    return _json(self, {"ok": False, "error": "bad path"}, 400)
                if os.path.isfile(full):
                    ext = os.path.splitext(full)[1].lower()
                    return _file(self, full, _CTYPES.get(ext, "application/octet-stream"))
                return _json(self, {"ok": False, "error": "no such file"}, 404)
            if path == "/api/meta":
                return self._guard(lambda: app.meta())
            if path == "/api/locale":
                # The screen's own wording, so the page holds no Chinese prose of
                # its own.  Same reasoning as `/api/forms`: the table can change
                # between two page loads (a plugin can drop a locale file), and a
                # page that baked the old words in would be the one place that
                # cannot be corrected by editing data.
                loc = _query(self.path).get("locale", [LO.DEFAULT_LOCALE])[0]
                return self._guard(lambda: {
                    "ok": True, "locale": loc, "strings": LO.load(loc)})
            if path == "/loading":
                # The window opens HERE first, not at "/".  The socket is bound
                # before any parse (serve() builds App lazily), so this page is on
                # screen in ~1 s while the backend spends its measured 10.7 s
                # walking 93 MB.  Same origin as /api/progress, so no CORS and no
                # port baked into a page.
                return _html(self, LOADING_PAGE)
            if path == "/api/progress":
                # Must answer in milliseconds while `Parser.parse` is running: it
                # reads only a module-level dict, never the toolkit.  The window
                # polls this every 250 ms during startup and the bar is drawn from
                # what comes back.
                from aoe2mod import progress as PG
                return self._guard(lambda: {"ok": True, "progress": PG.snapshot()})
            if path == "/api/job":
                # Progress for a job a REQUEST starts (opening the field editor
                # the first time is 14.52 s measured 2026-11-02).  `/api/progress`
                # is the startup's own ten seconds; this is everything after.
                #
                # Same rule as `/api/progress`: read a module-level dict, never
                # touch the toolkit, so this answers in milliseconds while the
                # scanning thread holds the GIL.  A page that asks about a key
                # that never ran gets `known:False` and draws no bar -- that is
                # the warm path (0.003 s), which must not flash a 100 % bar.
                from aoe2mod import jobs as J
                q = _query(self.path)
                key = (q.get("key") or [""])[0]
                return self._guard(lambda: {"ok": True, "job": J.snapshot(key)})
            if path == "/api/log":
                # The About page draws the last few operations.  A GET on
                # purpose: it reads one text file and changes nothing, and the
                # whole point is that the player can see what the tool did
                # without opening Explorer.  `limit` is read from the query
                # because the contract guard requires every `?key=` the page
                # appends to be one this side actually uses -- a route that
                # ignores it answers 60 rows forever and looks like it worked.
                q = _query(self.path)
                try:
                    want = int(q.get("limit", ["60"])[0] or 60)
                except (TypeError, ValueError):
                    want = 60
                return self._guard(lambda: app.oplog(limit=want))
            if path == "/api/diag":
                # The page reports its own viewport here so a shell can read it
                # from outside.  A screenshot shows the symptom (the side panel
                # is missing); these numbers show the cause, and they are the
                # only way to tell "the layout got 850 CSS px" from "the layout
                # got 1700 and got clipped".  `document.title` was the first
                # channel and it cannot work: `WebviewWindow::title()` returns
                # the title the SHELL set, so the page can never write there.
                _d = _query(self.path)
                app.note_diag({k: v[0] for k, v in _d.items()})
                return self._guard(lambda: {"ok": True, "diag": app.diag()})
            if path == "/api/forms":
                return self._guard(lambda: app.forms(
                    _query(self.path).get("intent", [None])[0]))
            if path == "/api/mods":
                return self._guard(lambda: app.mods())
            if path == "/api/mod-thumb":
                # Image, not JSON -- a 1280x720 JPEG is up to 158 KB and
                # base64-ing seventeen of them into the list route is 1.6 MB of
                # text the page would then have to decode.
                q = _query(self.path)
                return self._guard_icon(lambda: app.mod_thumbnail(
                    q.get("name", [""])[0]))
            if path == "/api/recipes":
                return self._guard(lambda: app.recipes())
            if path == "/api/search":
                q = _query(self.path).get("q", [""])[0]
                kind = _query(self.path).get("kind", ["unit"])[0]
                return self._guard(lambda: app.search(q, kind=kind))
            if path == "/api/browse":
                q = _query(self.path)
                return self._guard(lambda: app.browse(
                    kind=q.get("kind", ["unit"])[0],
                    query=q.get("q", [""])[0],
                    limit=q.get("limit", [60])[0],
                    offset=q.get("offset", [0])[0],
                    order=q.get("order", ["id"])[0]))
            if path == "/api/describe":
                q = _query(self.path)
                return self._guard(lambda: app.describe(
                    q.get("kind", ["unit"])[0], q.get("id", ["0"])[0]))
            if path == "/api/pseudo-pages":
                # Which boxes cycle through several pages, and what each page of
                # one box shows.  `all_boxes=1` answers the first question alone.
                q = _query(self.path)
                return self._guard(lambda: app.pseudo_pages(
                    building=q.get("building", [""])[0],
                    box=q.get("box", [""])[0],
                    civ=q.get("civ", [""])[0],
                    all_boxes=q.get("all", ["0"])[0] in ("1", "true", "yes")))
            if path == "/api/card":
                # The command panel.  The native backend has answered this since
                # the page started calling it; this one returned 404, so the view
                # was an empty box plus one console error (measured 2026-10-28).
                q = _query(self.path)
                return self._guard(lambda: app.card(
                    building=q.get("building", ["12"])[0],
                    civ=q.get("civ", [""])[0]))
            if path == "/api/civ":
                # The civilisation tech-tree view.  Only the native backend
                # answered this before (measured 2026-10-30: 404 here, 200 on
                # port 7799), so the shell could not be switched to Python
                # without losing the view -- see the note above `def civ`.
                q = _query(self.path)

                def _ids(name):
                    """`units=5,4` -> [5, 4]; junk in the list is refused aloud.

                    Silently dropping a malformed id would answer a DIFFERENT
                    question than the one asked ("can this civ have 5" when the
                    caller also asked about "x"), and the missing row reads as
                    "this civ cannot have it".
                    """
                    out = []
                    for raw in (q.get(name) or []):
                        for piece in str(raw).split(","):
                            piece = piece.strip()
                            if not piece:
                                continue
                            try:
                                out.append(int(piece))
                            except ValueError:
                                raise _BadId("%s=%r 里有一个不是编号：%r"
                                             % (name, raw, piece))
                    return out

                return self._guard(lambda: app.civ(
                    q.get("civ", [""])[0],
                    units=_ids("units"), techs=_ids("techs"),
                    buildings=_ids("buildings")))
            if path == "/api/techtree":
                # The visual tech tree.  Separate from `/api/civ`, which answers
                # availability questions with a compact map that has no geometry.
                # `mode` picks the base install or Rome at War: their civs do not
                # overlap and their files do not live in the same folder.
                q = _query(self.path)
                return self._guard(lambda: app.techtree(
                    q.get("civ", [""])[0],
                    mode=q.get("mode", [""])[0]))
            if path == "/api/techtree-icons":
                q = _query(self.path)
                return self._guard(lambda: app.techtree_icons(
                    q.get("pairs", [""])[0],
                    max_side=int((q.get("size", ["34"])[0] or 34)),
                    mode=q.get("mode", [""])[0]))
            if path == "/api/age-icon":
                # The four age medallions, straight PNG off the install.
                q = _query(self.path)
                return self._guard_icon(lambda: app.age_icon(
                    q.get("n", ["1"])[0]))
            if path == "/api/session-info":
                # GET, because the header polls it while the player edits.
                return self._guard(app.session_info)
            if path == "/api/fields":
                # Every field of one unit -- what AGE shows as an 85-row wall,
                # here grouped and labelled in Chinese.
                q = _query(self.path)
                return self._guard(lambda: app.unit_fields(
                    q.get("unit", ["0"])[0], civ=q.get("civ", [""])[0],
                    group=q.get("group", [""])[0], q=q.get("q", [""])[0]))
            if path == "/api/tech-effects":
                # The LIST behind one technology's `EffectID` pointer.  Separate
                # from /api/tech-fields because it is a different record in a
                # different part of the file, and because the page draws it as a
                # list of sentences rather than a table of numbers.
                q = _query(self.path)
                return self._guard(lambda: app.effect_rows(
                    q.get("tech", q.get("id", ["0"]))[0]))
            if path == "/api/unit-effects":
                # The reverse of /api/tech-effects: every number in the file
                # that is about ONE unit, whichever technology carries it.
                q = _query(self.path)
                return self._guard(lambda: app.unit_effects(
                    q.get("unit", q.get("id", ["0"]))[0],
                    q.get("civ", [""])[0]))
            if path == "/api/tech-fields":
                # Same shape as /api/fields, one space of difference: the rows
                # carry `ref`/`ref_text` for the four pointer columns, which is
                # what the unit table has no equivalent of.
                q = _query(self.path)
                return self._guard(lambda: app.tech_fields(
                    q.get("tech", q.get("id", ["0"]))[0],
                    group=q.get("group", [""])[0], q=q.get("q", [""])[0]))
            if path == "/api/icons":
                # The whole list in one answer.  Measured 2026-11-02: 400 icons
                # at 26 px took the browser 3.6 s to finish as 400 requests, and
                # the screenshot of that window is what a player reported as
                # 「有些图标不正常」.  One request, one paint.
                q = _query(self.path)
                return self._guard(lambda: app.icons(
                    q.get("kind", ["unit"])[0], q.get("ids", [""])[0],
                    max_side=q.get("size", [26])[0]))
            if path == "/api/table-rows":
                # The picker behind 图形 / 音效.  20,883 rows is not something to
                # hand the browser whole (see `table_rows`), so this pages, and
                # `named_only` is what makes the count it prints the count it
                # pages.
                q = _query(self.path)
                return self._guard(lambda: app.table_rows(
                    q.get("table", ["graphic"])[0], q=q.get("q", [""])[0],
                    offset=q.get("offset", [0])[0],
                    limit=q.get("limit", [200])[0],
                    named_only=bool(int(q.get("named", ["1"])[0] or 1))))
            if path == "/api/table-fields":
                # One graphic or one sound record.  Same row shape as
                # /api/fields so the page reuses the same table widget.
                q = _query(self.path)
                return self._guard(lambda: app.table_fields(
                    q.get("table", ["graphic"])[0],
                    q.get("index", q.get("id", ["0"]))[0],
                    q=q.get("q", [""])[0]))
            if path == "/api/tables":
                return self._guard(app.tables)
            if path == "/api/dat-sources":
                # Which .dat the game could load, so the player can pick one.
                # 18 candidates answered in 0.06 s: each costs a 64-byte head
                # inflate, never a parse.  Reported 2026-11-03 「我要改指定的dat」.
                return self._guard(app.dat_sources)
            if path == "/api/script-files":
                # The game's ai/ + xs/ folders and the player's own copies.
                # Reading a directory listing, not a file, so a 53-file folder
                # costs one scandir per subdirectory.
                return self._guard(lambda: app.script_files(
                    _query(self.path).get("dept", [""])[0]))
            if path == "/api/script-read":
                return self._guard(lambda: app.script_read(
                    _query(self.path).get("path", [""])[0]))
            if path == "/api/animations":
                # The list of moments this unit's art actually has.  One small
                # JSON answer; the pictures come from /api/film, one per click.
                q = _query(self.path)
                return self._guard(lambda: app.animations(
                    q.get("unit", q.get("id", ["0"]))[0],
                    civ=q.get("civ", [""])[0]))
            if path == "/api/film":
                # Image, not JSON -- see App.film's docstring.
                q = _query(self.path)
                return self._guard_icon(lambda: app.film(
                    q.get("unit", q.get("id", ["0"]))[0],
                    civ=q.get("civ", [""])[0],
                    anim=q.get("anim", [""])[0],
                    frame=q.get("frame", [0])[0],
                    count=q.get("count", [20])[0],
                    angle=q.get("angle", [0])[0],
                    with_shadow=bool(int(q.get("shadow", ["0"])[0] or 0))))
            if path == "/api/icon":
                q = _query(self.path)
                return self._guard_icon(lambda: app.icon(
                    q.get("kind", ["unit"])[0], q.get("id", ["0"])[0],
                    section=(q.get("section", [None])[0]),
                    max_side=q.get("size", [0])[0]))
            if path == "/api/emblem":
                q = _query(self.path)
                return self._guard_icon(lambda: app.emblem(
                    q.get("civ", [""])[0],
                    mode=q.get("mode", [""])[0]))
            if path == "/api/art":
                q = _query(self.path)
                return self._guard_icon(lambda: app.art(
                    q.get("civ", [""])[0],
                    mode=q.get("mode", [""])[0]))
            if path == "/api/update-check":
                return self._guard(app.update_check)
            if path == "/api/ai-meta":
                # Cheap and keyless (no call is made): the page reads this on
                # load to decide whether to draw the AI box at all.  An AI box
                # that always fails is worse than none.
                return self._guard(app.ai_meta)
            if path == "/api/ai-lang-meta":
                # Keyless AND gameless: reads the shipped payload only, never the
                # install.  The language editor must work before a path is set.
                return self._guard(app.ai_lang_meta)
            if path == "/api/repair-check":
                # Deliberately NOT part of /api/mods: this parses about 12 MB
                # per mod, and the mod list is drawn on every page load.
                #
                # `q` used to be read here without being bound in this branch --
                # it is assigned in the sibling branches above, which makes it a
                # cell variable of the enclosing function, so the lambda raised
                # `NameError: cannot access free variable 'q'` on every call.
                # The repair button was therefore dead on arrival for everybody,
                # and no nail saw it: `test_page_route_contract` only checks the
                # KEY NAMES the page sends, and `test_ui_server` called
                # `App.repair_check` directly instead of going through the route.
                q = _query(self.path)
                return self._guard(lambda: app.repair_check(
                    profile_root=(q.get("profile_root", [None])[0] or None)))
            if path == "/api/upgrade-check":
                # Same reason as /api/repair-check: one parse of the official
                # stream plus one per mod that is not already current, so this
                # is asked for by a button and not by a page load.  `name`
                # narrows it to one mod, which is what the row's own button
                # does after an upgrade so the list is not re-walked.
                #
                # Bind `q` HERE, in this branch.  The sibling branch above does
                # the same for the same reason: a name read only inside a lambda
                # makes it a cell variable that is unbound on the other paths,
                # and the failure is `NameError: cannot access free variable`
                # at call time -- which reads like a broken button, not a bug.
                q = _query(self.path)
                return self._guard(lambda: app.upgrade_check(
                    name=(q.get("name", [None])[0] or None),
                    profile_root=(q.get("profile_root", [None])[0] or None),
                    limit=int(q.get("limit", ["40"])[0] or 40),
                    base_dat=(q.get("base_dat", [None])[0] or None),
                    new_dat=(q.get("new_dat", [None])[0] or None)))
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        # ---- actions ----
        def do_POST(self):
            path = self.path.split("?", 1)[0]
            # The log needs to know WHICH operation a sentence describes; `_guard`
            # reads these two attributes on success and on failure alike.
            self._op_route = path
            self._op_payload = {}
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8")
                                     if length else "{}")
            except ValueError as exc:
                return _json(self, {"ok": False, "error": "bad json: %s" % exc})
            self._op_payload = payload if isinstance(payload, dict) else {}
            if path == "/api/parse":
                return self._guard(lambda: app.parse(payload.get("text") or "",
                                                     payload.get("pins") or []))
            if path == "/api/plan":
                return self._guard(lambda: app.plan(payload["intent"]))
            if path == "/api/sprite":
                # Only the native backend answered this before (measured
                # 2026-10-30).  `dry` defaults to TRUE here, unlike the native
                # build: a sprite swap rewrites 93 MB and the common mistake is
                # picking the unit you are looking at as the donor, which
                # compiles to zero edits and would look like a broken button.
                return self._guard(lambda: app.sprite(
                    payload.get("unit"), payload.get("donor"),
                    civs=payload.get("civs") or None,
                    whole_family=bool(payload.get("whole_family")),
                    fill=bool(payload.get("fill")),
                    mode=payload.get("mode") or "rename",
                    dry=bool(payload.get("dry", True)),
                    install=bool(payload.get("install")),
                    title=payload.get("title")))
            if path == "/api/toggle-group":
                # The page posts `techs` as a list; a single number is accepted
                # too because that is what a hand-written curl sends.
                _techs = payload.get("techs")
                if _techs is None:
                    _techs = payload.get("tech")
                if not isinstance(_techs, (list, tuple)):
                    _techs = [] if _techs is None else [_techs]
                return self._guard(lambda: app.toggle_group(
                    _techs, kind=payload.get("type"),
                    comment=payload.get("comment") or "",
                    dry=bool(payload.get("dry", True)),
                    install=bool(payload.get("install")),
                    title=payload.get("title")))
            if path == "/api/card-put":
                return self._guard(lambda: app.card_put(
                    payload.get("unit"),
                    payload.get("building", payload.get("builder")),
                    box=payload.get("box", payload.get("button")),
                    seconds=payload.get("seconds"),
                    civ=payload.get("civ"),
                    dry=bool(payload.get("dry", False)),
                    title=payload.get("title")))
            if path == "/api/pseudo-pages":
                return self._guard(lambda: app.add_pseudo_page(
                    payload.get("building", payload.get("builder")),
                    payload.get("box", payload.get("button")),
                    name=payload.get("name"),
                    on=payload.get("on") or payload.get("units") or (),
                    hide=payload.get("hide"),
                    civ=payload.get("civ"),
                    seconds=payload.get("seconds") or 0,
                    donor=payload.get("donor"),
                    dry=bool(payload.get("dry", False)),
                    title=payload.get("title")))
            if path == "/api/card-take":
                return self._guard(lambda: app.card_take(
                    payload.get("unit"),
                    payload.get("building", payload.get("builder")),
                    civ=payload.get("civ"),
                    dry=bool(payload.get("dry", False)),
                    title=payload.get("title")))
            if path == "/api/card-time":
                return self._guard(lambda: app.card_time(
                    payload.get("unit"),
                    payload.get("building", payload.get("builder")),
                    payload.get("seconds"),
                    civ=payload.get("civ"),
                    dry=bool(payload.get("dry", False)),
                    title=payload.get("title")))
            if path == "/api/card-move":
                # The page's drag handler posts `box`; the sentence reader calls
                # the field `button`.  Both spellings are read here because the
                # two disagreeing about a field name is exactly the defect that
                # made every understood sentence come back "没说要挪到第几格"
                # on the native side.
                _box = payload.get("box", payload.get("button"))
                return self._guard(lambda: app.card_move(
                    payload.get("unit"), _box,
                    building=payload.get("building", payload.get("builder")),
                    civ=payload.get("civ"),
                    dry=bool(payload.get("dry", False)),
                    title=payload.get("title")))
            if path == "/api/session-reset":
                # "Discard my edits" -- drops the in-memory buffer so the pace
                # goes back to the game file.  Nothing on disk is touched.
                return self._guard(app.reset_session)
            if path == "/api/session-save":
                # Build ONE mod from every pending edit.  Separate from
                # `/api/field-set` on purpose: that route is fast because it
                # only touches memory, this one is slow (93 MB) and runs once.
                # `install` defaults to TRUE on the route and FALSE on the
                # method: the screen 保存 must put the mod where the game reads
                # it (asked 2026-11-09, 「要不你都改成默认放入 local 里吧」),
                # while a probe calling the method directly must not touch the
                # player's profile.
                return self._guard(lambda: app.save_session(
                    payload.get("title"), keep=bool(payload.get("keep")),
                    install=bool(payload.get("install", True))))
            if path == "/api/session-info":
                return self._guard(app.session_info)
            if path == "/api/session-intents":
                return self._guard(app.session_intents)
            if path == "/api/undo":
                # One step back.  The bytes are put back in the in-memory buffer
                # and the same caches `field-set` patched are patched again, so
                # the panel shows the restored value without a rescan.
                return self._guard(app.undo)
            if path == "/api/redo":
                return self._guard(app.redo)
            if path == "/api/effect-set":
                # One command of that list.  `dry` defaults to TRUE, exactly as
                # /api/field-set does: the common mistake is the wrong position in
                # the list, and echoing the bytes first is cheap.
                return self._guard(lambda: app.set_effect_value(
                    payload.get("tech"),
                    payload.get("command"),
                    value=payload.get("value"),
                    delta=payload.get("delta"),
                    dry=bool(payload.get("dry", True)),
                    title=payload.get("title")))
            if path == "/api/table-field-set":
                # One field of one graphic/sound record.  `dry` defaults to TRUE
                # for the same reason /api/field-set does: `SlpID` and `ID` are
                # one character apart and mean very different things, and echoing
                # the bytes first costs nothing.
                return self._guard(lambda: app.set_table_field(
                    payload.get("table") or "graphic",
                    payload.get("record", payload.get("index")),
                    payload.get("field") or payload.get("name"),
                    payload.get("value"),
                    dry=bool(payload.get("dry", True)),
                    title=payload.get("title")))
            if path == "/api/field-set":
                # One field, one value.  `dry` defaults to TRUE here (unlike
                # /api/card-move) because a mistyped field name is the common
                # case and echoing the bytes first is cheap.
                #
                # `kind` picks which record space the id lives in.  Defaulting
                # to "unit" keeps every existing caller working; a technology
                # edit must say so, because unit 22 and tech 22 are different
                # records and a silent default would edit the wrong one.
                _kind = str(payload.get("kind") or "unit").strip().lower()
                if _kind == "tech":
                    # `set_tech_field` takes no `civ`: a technology record is not
                    # per-civilisation the way a unit record is, it selects one
                    # with its own `Civ` field.
                    return self._guard(lambda: app.set_tech_field(
                        payload.get("tech", payload.get("unit")),
                        payload.get("field") or payload.get("name"),
                        payload.get("value"),
                        dry=bool(payload.get("dry", True)),
                        title=payload.get("title")))
                return self._guard(lambda: app.set_unit_field(
                    payload.get("unit"), payload.get("field") or payload.get("name"),
                    payload.get("value"),
                    civ=payload.get("civ"),
                    dry=bool(payload.get("dry", True)),
                    title=payload.get("title")))
            if path == "/api/record-add":
                # A record that was not in the file.  `kind` picks the space
                # (unit 30000 and tech 1510 are unrelated numbers).
                #
                # `donor` clones an existing record.  `blank: true` does not:
                # it asks for a record built from nothing, which is what a
                # player means by "新增" and what this route used to refuse
                # ("a new record with no fields in it would be a hole the
                # parser still has to walk" -- measured wrong on 2026-11-06:
                # the parser decides a record's blocks from its TYPE, and
                # `newunit.blank_image` walks its own output to the last byte
                # before returning it, so the record is not a hole).
                return self._guard(lambda: app.record_edit(
                    "add",
                    kind=payload.get("kind") or "unit",
                    civ=payload.get("civ"),
                    record=payload.get("record", payload.get("id")),
                    donor=payload.get("donor"),
                    name=payload.get("name"),
                    hp=payload.get("hp"),
                    count=payload.get("count"),
                    ids=payload.get("ids"),
                    # 粘贴 goes through THIS route: several donors, one gesture.
                    # Missing from the first cut, so Ctrl+V sent a request the
                    # server answered with "编号要填整数" (measured 2026-11-05).
                    donors=payload.get("donors"),
                    blank=bool(payload.get("blank"))))
            if path == "/api/record-dup":
                # Same clone, different sentence: "this one, again".  Kept as its
                # own route because the screen's two buttons mean different
                # things to the player even though the bytes are identical.
                return self._guard(lambda: app.record_edit(
                    "dup",
                    kind=payload.get("kind") or "unit",
                    civ=payload.get("civ"),
                    record=payload.get("record", payload.get("id")),
                    donor=payload.get("record", payload.get("id")),
                    name=payload.get("name"),
                    hp=payload.get("hp"),
                    count=payload.get("count"),
                    ids=payload.get("ids"),
                    donors=payload.get("donors")))
            if path == "/api/record-del":
                return self._guard(lambda: app.record_edit(
                    "del",
                    kind=payload.get("kind") or "unit",
                    civ=payload.get("civ"),
                    record=payload.get("record", payload.get("id")),
                    ids=payload.get("ids"),
                    force=bool(payload.get("force"))))
            if path == "/api/icon-set":
                # The picture arrives as base64 because that is what a browser
                # can read out of a file picker; `dry` decides preview or write,
                # and both go through `App.set_icon` so the slot the preview
                # names is the slot the record gets.
                return self._guard(lambda: app.set_icon(
                    kind=payload.get("kind") or "unit",
                    record=payload.get("record", payload.get("id")),
                    civ=payload.get("civ") or "",
                    data_b64=payload.get("data_b64"),
                    filename=payload.get("filename"),
                    slot=payload.get("slot"),
                    dry=bool(payload.get("dry", True))))
            if path == "/api/record-rename":
                # The door the field editor has been pointing at since the day
                # it made `Name` read-only: 「要改请用「重命名」」.
                return self._guard(lambda: app.record_rename(
                    kind=payload.get("kind") or "unit",
                    civ=payload.get("civ"),
                    record=payload.get("record", payload.get("id")),
                    name=payload.get("name")))
            if path == "/api/build":
                return self._guard(lambda: app.build(
                    (payload.get("intents") or _flat_intent(payload)),
                    title=payload.get("title"),
                    title_auto=bool(payload.get("title_auto")),
                    author=payload.get("author") or "",
                    description=payload.get("description") or "",
                    install=bool(payload.get("install"))))
            if path == "/api/stat":
                return self._guard(lambda: app.stat_apply(
                    payload.get("stat"),
                    payload.get("unit", payload.get("tech")),
                    value=payload.get("value"),
                    delta=payload.get("delta"),
                    civs=payload.get("civs"),
                    kind=str(payload.get("kind") or "unit").strip().lower()))
            if path == "/api/install":
                return self._guard(lambda: app.install(
                    payload["mod_dir"], name=payload.get("name"),
                    enabled=payload.get("enabled", True),
                    position=int(payload.get("position") or 0)))
            if path == "/api/mod-move-to":
                return self._guard(lambda: app.move_mod_to(
                    payload["name"], payload["position"],
                    profile_root=payload.get("profile_root")))
            if path == "/api/mod-move":
                # `payload` is already parsed at the top of do_POST.  This route
                # used to call `self._body()`, a method that does not exist, so
                # every move raised AttributeError, the handler died before
                # writing a response, and the browser reported the toast
                # 「移不动：Failed to fetch」.  Reported 2026-11-03.
                return self._guard(lambda: app.move_mod(
                    payload["name"], payload["delta"],
                    profile_root=payload.get("profile_root")))

            if path == "/api/mod":
                return self._guard(lambda: app.set_mod(
                    payload["name"], bool(payload.get("enabled"))))
            if path == "/api/uninstall":
                return self._guard(lambda: app.uninstall(payload["name"]))
            if path == "/api/rebuild":
                return self._guard(lambda: app.rebuild(payload["title"]))
            if path == "/api/upgrade-apply":
                # `install` defaults to TRUE for the UI path (a rebuilt folder
                # nobody installed is not what the button promises) but is read
                # from the payload so a caller can ask for the folder only.
                return self._guard(lambda: app.upgrade_apply(
                    name=payload.get("name"),
                    mod_dat=payload.get("mod_dat"),
                    out_dir=payload.get("out_dir"),
                    title=payload.get("title"),
                    base_dat=payload.get("base_dat"),
                    new_dat=payload.get("new_dat"),
                    install=bool(payload.get("install", True)),
                    profile_root=payload.get("profile_root"),
                    official_wins=bool(payload.get("official_wins")),
                    force=bool(payload.get("force"))))
            if path == "/api/repair-apply":
                return self._guard(lambda: app.repair_apply(payload["name"]))
            if path == "/api/ai-sentences":
                return self._guard(lambda: app.ai_sentences(payload.get("text") or ""))
            if path == "/api/ai-script-edit":
                return self._guard(lambda: app.ai_script_edit(payload))
            if path == "/api/ai-script-build":
                return self._guard(lambda: app.ai_script_build(payload))
            if path == "/api/ai-script-check":
                return self._guard(lambda: app.ai_script_check(payload))
            if path == "/api/open-url":
                # Scheme-checked in `App.open_url`: this is the only route that
                # reaches outside the process on the player's behalf.
                return self._guard(lambda: app.open_url(payload.get("url") or ""))
            if path == "/api/log-open":
                # Reported 2026-11-09: the log folder is only useful if it can
                # be opened.  Scheme-free, unlike `/api/open-url`: this opens
                # ONE folder this process owns, never a path from the page.
                return self._guard(lambda: app.open_log_folder())
            if path == "/api/dat-set":
                # Switching the file under the whole session: the toolkit is
                # rebuilt and every cache dropped, because a 93 MB buffer and
                # 400 decoded field records belong to ONE file.
                return self._guard(lambda: app.set_dat(payload.get("path") or ""))
            if path == "/api/script-write":
                # Guarded in `aifiles.check_save`: only the game's ai/ + xs/
                # folders and the player's own two copies of them.  A route that
                # writes wherever it is told is a file-write primitive.
                return self._guard(lambda: app.script_write(
                    payload.get("path") or "", payload.get("text") or ""))
            if path == "/api/recipe":
                return self._guard(lambda: app.save_recipe(
                    payload.get("name") or "", payload.get("sentences") or [],
                    note=payload.get("note") or ""))
            if path == "/api/recipe-forget":
                return self._guard(lambda: app.forget_recipe(payload.get("name") or ""))
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        def _guard(self, fn):
            """One place where an exception becomes a readable sentence.

            It is also the one place an OPERATION gets written down.  Every
            mutating route already funnels through here, so logging here means
            no route can be added and silently left out of the record -- which
            is the failure mode a per-route `OPLOG.record(...)` call invites
            (reported 2026-11-09: 「那怎么记录每一次的操作」).  `do_POST` stores
            the route and the parsed body on the handler before dispatching;
            a GET never has either, so reads stay out of the log by default.
            """
            route = getattr(self, "_op_route", "") or ""
            payload = getattr(self, "_op_payload", None) or {}
            started = time.time()
            try:
                got = fn()
            except Exception as exc:                   # noqa: BLE001
                tb = traceback.format_exc(limit=4)
                if route and OPLOG.logs(route):
                    OPLOG.record(route=route, ok=False,
                                 summary=OPLOG.summary_of(route, payload, {}),
                                 detail=payload,
                                 error="%s: %s" % (type(exc).__name__, exc),
                                 ms=(time.time() - started) * 1000)
                return _json(self, {"ok": False, "error": _sentence(exc),
                                    "where": tb})
            if route and OPLOG.logs(route):
                OPLOG.record(route=route,
                             ok=bool(got.get("ok", True)) if isinstance(got, dict) else True,
                             summary=OPLOG.summary_of(route, payload, got),
                             detail=_op_detail(route, payload, got),
                             error=(got.get("error") or "") if isinstance(got, dict) else "",
                             ms=(time.time() - started) * 1000)
            return _json(self, got)

        def _guard_icon(self, fn):
            """A route that answers with an IMAGE, not JSON.

            Kept separate from `_guard` on purpose: wrapping a 200 KB PNG in a
            JSON envelope would force the page to base64-decode it, and encoding
            failures would then look like "the icon is missing".  The failure
            path still answers JSON so the page can print a reason.
            """
            try:
                got = fn()
            except Exception as exc:                   # noqa: BLE001
                return _json(self, {"ok": False,
                                    "error": "%s: %s" % (type(exc).__name__, exc),
                                    "where": traceback.format_exc(limit=4)})
            if not got.get("ok"):
                return _json(self, {"ok": False,
                                    "error": got.get("error") or "no picture"})
            body = got["png"]
            self.send_response(200)
            # Default stays PNG: every route before this one answered with a
            # re-encoded atlas tile.  A route that passes a shipped file through
            # untouched has to say what it actually is, or five JPEG thumbnails
            # get served as PNG.
            self.send_header("Content-Type",
                             got.get("content_type") or "image/png")
            self.send_header("Content-Length", str(len(body)))
            # The files come off the installed game and do not change while it
            # is installed; a list view asks for the same sprite repeatedly.
            self.send_header("Cache-Control", "max-age=86400")
            # A route that answers with a picture can still have numbers to
            # report (how many poses came back, whether the row was trimmed to
            # fit a window).  Headers carry them so the body stays a plain PNG
            # rather than base64 inside JSON -- see `/api/film`.
            for k, v in (got.get("headers") or {}).items():
                self.send_header(k, str(v))
            self.end_headers()
            self.wfile.write(body)

    return Handler


# Columns whose value is a name the player picks from a list, not a number to
# type.  The census (below) learns which names actually occur.
_CENSUS_TAILS = ("TaskType", "ActionType", "GatherType", "TargetDiplomacy",
                 "CarryCheck", "ClassID", "TerrainID", "ResourceIn",
                 "ResourceOut", "WorkFlag2", "CombatLevelFlag")

# 136,861 records x 434 fields is 27 s of decoding for a table that does not
# change inside a session.  24,000 records is ~5 s and already covers every
# value that occurs (measured: ActionType saturates at 27 kinds by record 306).
_CENSUS_CAP = 24000


def _subject_of(edit):
    """What an edit is about, in words, for the mod description and title.

    The session buffer holds two kinds of record now (a unit and a technology),
    and they are numbered in different spaces -- technology 22 is 织布机 while
    unit 22 is a 民兵.  A description that says "单位 22" for a technology edit
    is worse than useless: it names the wrong object with full confidence.
    """
    if edit.get("tech") is not None:
        nm = edit.get("tech_name")
        return ("科技「%s」" % nm) if nm else ("科技 %s" % edit.get("tech"))
    if edit.get("table"):
        # A table edit is a THIRD id space.  Measured 2026-11-04: without this
        # branch a 伐木效率 write named its mod 「单位 None」, because the unit
        # branch is the fallback and a table record has no unit at all.
        tbl = edit.get("table")
        zh = TABLE_ZH_SAFE(tbl)
        nm = edit.get("record_name")
        return ("%s「%s」" % (zh, nm)) if nm else ("%s %s" % (zh, edit.get("record")))
    nm = edit.get("unit_name")
    return ("单位「%s」" % nm) if nm else ("单位 %s" % edit.get("unit"))


def TABLE_ZH_SAFE(table):
    """Chinese table name, without importing `tablefields` at module load."""
    try:
        from aoe2mod.dat import tablefields as TF
        return TF.TABLE_ZH.get(table, table)
    except Exception:                              # noqa: BLE001
        return str(table)


def _intent_of(edit):
    """One `intents` entry for provenance, keeping the two kinds apart.

    `civ_all` is recorded as a FLAG rather than expanded into 63 intents.  The
    rebuild replay has to re-locate every copy anyway (a patch moves records), and
    `civ:"*"` plus the flag is what tells it "all copies", which an expanded list
    would lose the meaning of the moment a civilisation is added.
    """
    if edit.get("create"):
        # A record that did not exist before this session.  It has no offset to
        # replay and no "was" value: replaying it means running the same clone
        # against the CURRENT file, which is what the create intents do.
        out = {"intent": edit["create"]}
        if edit["create"] == "unit.create":
            out.update({"donor": edit.get("donor"), "civ": edit.get("civ"),
                        "name": edit.get("name"), "hp": edit.get("hp")})
        else:
            out.update({"donor": edit.get("donor"), "name": edit.get("name")})
        return out
    if edit.get("op") == "del":
        # REMOVING a record has no compiler path yet -- the rebuild replay would
        # have to re-locate the record in the current file and cut it, which is
        # exactly what `records.plan_remove_*` does but no intent maps to it.
        # Recording the intent honestly beats folding it into `unit.field` with
        # an empty field name, which would make a rebuild edit a field called "".
        if edit.get("tech") is not None:
            return {"intent": "tech.delete", "tech": edit.get("tech")}
        return {"intent": "unit.delete", "unit": edit.get("unit"),
                "civ": edit.get("civ")}
    if edit.get("effect") is not None:
        # An effect-list write is NOT a `tech.field` edit: the number lives in a
        # different record, addressed by (technology, position in the list).  It
        # has a real schema intent -- `tech.effect` -- so the rebuild replay goes
        # through the ordinary compiler, which re-locates the command in the
        # CURRENT file.  A stored offset would point into whatever record now
        # sits at those bytes after a patch.
        return {"intent": "tech.effect", "tech": edit.get("tech"),
                "command": edit.get("command"), "value": edit.get("now")}
    if edit.get("table") is not None:
        # A graphic or a sound record is a THIRD id space: graphic 74 and unit 74
        # are unrelated records, and a stored byte offset would point into
        # whatever moved there after a patch.  So the record is addressed by
        # (table, position in that table) and re-resolved at replay time.
        return {"intent": "table.field", "table": edit.get("table"),
                "record": edit.get("record"), "field": edit.get("field"),
                "value": edit.get("now")}
    if edit.get("tech") is not None:
        return {"intent": "tech.field", "tech": edit.get("tech"),
                "field": edit.get("field"), "value": edit.get("now")}
    out = {"intent": "unit.field", "unit": edit.get("unit"),
           "field": edit.get("field"), "value": edit.get("now"),
           "civ": edit.get("civ")}
    if edit.get("civ_all"):
        out["civ_all"] = True
    return out


def _flat_intent(payload):
    """A single intent written flat into the body, as the native engine takes it.

    `desktop/aoe2mod-serve/src/stat_edit.rs:743 build_and_install` answers a body
    with no `intents` array by handing the WHOLE request to `build_one`, so
    every caller ever written against the native engine posts
    `{"intent": "unit.stat", "unit": 1810, "stat": ..., "value": ..., "title":
    ..., "install": true}` and nothing else.  `_probe/test_e2e_shipped.py:112`
    goes one step further and omits `intent` too, because the native stat path
    reads `stat`/`unit`/`value` directly and never looks at the name.

    This server read only the `intents` key of the body, so all of them arrived
    as an empty list and were refused with 「没有可构建的改动」.  Measured 2026-10-31:
    that refusal was the whole failure of seven suites once the shipped exe
    started running this engine.

    (The sentence above deliberately avoids writing that read as a bracketed
    subscript: `_probe/test_page_route_contract.py` scans this file for
    `payload["name"]` to decide what a route REQUIRES, and its last branch runs
    to the end of the file -- so the old wording made `/api/recipe-forget` look
    like it demanded an `intents` array.)
    """
    if not isinstance(payload, dict):
        return []
    body = {k: v for k, v in payload.items() if k != "intents"}
    name = body.get("intent")
    if not name:
        # No name at all: the native engine's default stat path, which is what
        # a flat `{"stat": ..., "unit": ..., "value": ...}` body means.
        if body.get("stat") and body.get("unit") is not None:
            name = "unit.stat"
        else:
            return []
        body["intent"] = name
    # Bundle-level fields belong to the build, not to the intent; leaving them
    # in would make `C.resolve()` reject the intent for unknown keys on the
    # older schema shapes.  `build()` reads them from its own arguments.
    for key in ("title", "title_auto", "author", "description", "install"):
        body.pop(key, None)
    return [body]


def _split_field_intents(intents):
    """`(field edits, everything else)`, order kept inside each list.

    Field edits are the two intents the editor writes straight into the session
    buffer.  They are absent from `schema/intents.json` on purpose -- they have
    no compiler recipe, because "set this named field of record N to V" is not a
    shape any sentence resolves to -- so the intent compiler rejects them, and
    `rebuild` has to route them somewhere else.
    """
    FIELD = ("unit.field", "tech.field", "table.field")
    fs, others = [], []
    for i in intents or ():
        (fs if isinstance(i, dict) and i.get("intent") in FIELD
         else others).append(i)
    return fs, others


def _query(path):
    try:
        from urllib.parse import parse_qs
    except ImportError:                                # pragma: no cover
        from urlparse import parse_qs
    return parse_qs(path.split("?", 1)[1] if "?" in path else "")


def _quiet_connection_errors():
    """A server class whose `handle_error` ignores a client that went away.

    Measured 2026-10-25 (first run of `tools/run_ui.py --window`): closing the
    window kills the in-flight requests, and the socket write then raises
    `ConnectionAbortedError: [WinError 10053]` inside the handler thread.  The
    stock `socketserver` prints a full traceback for it, so the last thing a
    player sees when they close the workshop is a stack trace -- which reads as
    "the program crashed on exit".  Nothing crashed: the reader is gone.

    Anything that is NOT the client leaving still prints, because that is the
    case where the traceback is the only clue.
    """
    try:
        from http.server import ThreadingHTTPServer as _Base
    except ImportError:                                # pragma: no cover
        from socketserver import ThreadingMixIn
        from http.server import HTTPServer as _Base

        class _Mix(ThreadingMixIn, _Base):
            daemon_threads = True

        _Base = _Mix

    class _Server(_Base):
        daemon_threads = True

        def handle_error(self, request, client_address):
            import sys as _sys
            exc = _sys.exc_info()[1]
            if isinstance(exc, (ConnectionError, BrokenPipeError)):
                return
            _Base.handle_error(self, request, client_address)

    return _Server


def serve(port=0, game_root=None, host="127.0.0.1", warm=False):
    """Start the server; returns (httpd, app, url).  Caller calls `serve_forever`.

    `warm=True` starts reading the game data on a background thread immediately.
    That is what makes the loading screen honest: the `.dat` is parsed lazily on
    the first request that needs it, and the splash page only asks `/api/progress`,
    which touches nothing -- so without this the bar sits at 0 % forever while the
    backend waits for a request the splash will not make until the bar is full.
    Measured 2026-10-26 on the first packaged run: exactly that deadlock.

    Tests leave it off: a background parse would run behind every test that builds
    a server, and `AOE2MOD_STATE_DIR` tests must not spend 10 s each on data they
    never read.
    """
    app = App(game_root=game_root)
    # Where `log/` lives: the tool directory, i.e. beside `_mods_out/`.
    # `AOE2MOD_LOG_DIR` still wins, which is what keeps a suite out of the
    # player's real record.
    OPLOG.configure(_tool_root())
    httpd = _quiet_connection_errors()((host, port), make_handler(app))
    url = "http://%s:%d" % (host, httpd.server_address[1])
    if warm:
        def _warm():
            try:
                # `app.tk` only CONSTRUCTS the toolkit -- it is lazy and parses
                # nothing.  Touching `version` is what enters `_ensure()`, so this
                # must ask for a fact, not for the object.  Measured 2026-10-26:
                # the first version of this thread held `app.tk` and the splash sat
                # at 0 % for the whole run because no parse had started.
                app.tk.version
            except BaseException as exc:              # noqa: BLE001
                from aoe2mod import progress as PG
                PG.fail("读取游戏数据失败：%s" % exc)
        threading.Thread(target=_warm, name="warm-dat", daemon=True).start()
    return httpd, app, url


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
import json
import os
import threading
import traceback

from aoe2mod import api as A
from aoe2mod.game import civnames as CN
from aoe2mod.mod import emitter as E
from aoe2mod.ui import compose as CP
from aoe2mod.ui import locale as LO
from aoe2mod.ui import nl
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
                 "struct.error", "zlib.error")


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
        self._lock = threading.Lock()

    @property
    def tk(self):
        if self._tk is None:
            with self._lock:
                if self._tk is None:
                    self._tk = A.open_toolkit(game_root=self.game_root)
        return self._tk

    def vocab(self):
        if self._vocab is None:
            ix = self.tk  # building the toolkit also builds the index
            from aoe2mod.semantic import index as SI
            idx = SI.index()
            self._vocab = nl.Vocabulary(idx.units, idx.techs)
        return self._vocab

    # ---- routes ---------------------------------------------------------
    def home(self):
        return self.meta()

    def meta(self):
        """Cheap facts a screen needs once: civs, intents, mods, versions."""
        tk = self.tk
        intents, _bindings = _load_schema()
        return {
            "ok": True,
            "version": tk.version,
            "civs": tk.civ_names,
            "intents": [{"id": k,
                         "title": v.get("title") or v.get("title_en") or k,
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
            "mods": _mods_brief(tk),
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

    def browse(self, kind="unit", query="", limit=60, offset=0):
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
                                         offset=int(offset or 0))}

    def describe(self, kind, entity_id):
        return {"ok": True, "entity": self.tk.describe(int(entity_id), kind=kind)}

    def icon(self, kind, entity_id, section=None, max_side=0):
        """The picture for one entity, as PNG bytes plus what it is.

        Decoding a DDS per request would be wasteful, but so is caching bytes in
        a process that may run for one sentence; the browser is told to keep the
        image, which is where the repetition actually happens (a list of 60 units
        asks for the same sprite once).

        `section` is an override for the one thing the caller may know better
        than the rule does: nothing, today -- it exists so a test can prove the
        two tables draw different pictures, and so a future "show me the button"
        view does not need a new route.
        """
        from aoe2mod.game import ddstex as D
        got = self.tk.icon_for(kind, int(entity_id))
        if section and got.get("icon_id"):
            got = self.tk.icons.picture(section, got["icon_id"])
            got["witness"] = "the caller asked for the %s table" % (section,)
        if not got.get("ok"):
            return {"ok": False, "error": got.get("why") or "no picture"}
        body = D.to_png(got["path"], max_side=int(max_side or 0))
        return {"ok": True, "png": body, "icon": {k: got.get(k) for k in
                                                  ("section", "icon_id", "file",
                                                   "witness", "material")}}

    def emblem(self, civ):
        """A civilization's emblem, as the PNG the game already ships.

        The three spellings the product deals in (`British` from the .dat,
        `BRITONS` from the tree stems, `britons` on disk) all have to land on the
        same file, which is what `civnames.chinese` plus the tree-stem table are
        for -- the first version looked the aliased name up in icons.json and
        found nothing for the two civs whose file is spelled differently.
        """
        from aoe2mod.game import civtechtrees as CT
        stem = CT.civ_file_stem(civ) if civ else ""
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
                                   unit_class=self.tk.unit_class)
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

    def plan(self, intent):
        return {"ok": True, "plan": self._decorate(self.tk.plan(intent))}

    def build(self, intents, title=None, author="", description="", out_dir=None,
              title_auto=False):
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
        if title_auto and title:
            title = E.fit_auto_title(title)
        out_dir = out_dir or _out_root()
        if len(intents) == 1:
            r = self.tk.build(intents[0], out_dir, title=title, author=author,
                              description=description, overwrite=True)
        else:
            r = self.tk.build_bundle(intents, out_dir, title=title, author=author,
                                     description=description, overwrite=True)
        return {"ok": True, "manifest": r}

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
        return {"ok": True, "update": got}

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
        built = self.build(intents, title=title,
                           author=entry.get("author") or "dsh",
                           description=entry.get("description") or "",
                           out_dir=os.path.join(_out_root(), _safe_dir(title)))
        if not built.get("ok"):
            return built
        man = built["manifest"]
        installed = self.tk.install(man["mod_dir"], name=title, title=title,
                                    enabled=True, position=0, overwrite=True,
                                    profile_root=profile_root)
        return {"ok": True, "manifest": man, "installed": installed}

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
        out.append({"name": m.get("name"), "title": m.get("title") or m.get("name"),
                    "enabled": bool(m.get("enabled")), "kind": m.get("kind"),
                    "priority": m.get("priority"),
                    "ships_dat": _ships_dat(tk, m)})
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


def _out_root():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "_mods_out")


def _safe_dir(title):
    """A folder name for a mod title that the filesystem will accept."""
    keep = "-_ ()（）[]【】·"
    out = "".join(c for c in str(title or "mod")
                  if c.isalnum() or c in keep).strip()
    return (out or "mod")[:60]


# ---- HTTP wiring --------------------------------------------------------
def _json(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _file(handler, path, ctype):
    with open(path, "rb") as fh:
        body = fh.read()
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


_CTYPES = {".html": "text/html; charset=utf-8",
           ".css": "text/css; charset=utf-8",
           ".js": "application/javascript; charset=utf-8",
           ".svg": "image/svg+xml",
           ".png": "image/png",
           ".json": "application/json; charset=utf-8"}


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
            if path == "/api/forms":
                return self._guard(lambda: app.forms(
                    _query(self.path).get("intent", [None])[0]))
            if path == "/api/mods":
                return self._guard(lambda: app.mods())
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
                    offset=q.get("offset", [0])[0]))
            if path == "/api/describe":
                q = _query(self.path)
                return self._guard(lambda: app.describe(
                    q.get("kind", ["unit"])[0], q.get("id", ["0"])[0]))
            if path == "/api/icon":
                q = _query(self.path)
                return self._guard_icon(lambda: app.icon(
                    q.get("kind", ["unit"])[0], q.get("id", ["0"])[0],
                    section=(q.get("section", [None])[0]),
                    max_side=q.get("size", [0])[0]))
            if path == "/api/emblem":
                q = _query(self.path)
                return self._guard_icon(lambda: app.emblem(
                    q.get("civ", [""])[0]))
            if path == "/api/update-check":
                return self._guard(app.update_check)
            if path == "/api/ai-meta":
                # Cheap and keyless (no call is made): the page reads this on
                # load to decide whether to draw the AI box at all.  An AI box
                # that always fails is worse than none.
                return self._guard(app.ai_meta)
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
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        # ---- actions ----
        def do_POST(self):
            path = self.path.split("?", 1)[0]
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8")
                                     if length else "{}")
            except ValueError as exc:
                return _json(self, {"ok": False, "error": "bad json: %s" % exc})
            if path == "/api/parse":
                return self._guard(lambda: app.parse(payload.get("text") or "",
                                                     payload.get("pins") or []))
            if path == "/api/plan":
                return self._guard(lambda: app.plan(payload["intent"]))
            if path == "/api/build":
                return self._guard(lambda: app.build(
                    payload.get("intents") or [],
                    title=payload.get("title"),
                    title_auto=bool(payload.get("title_auto")),
                    author=payload.get("author") or "",
                    description=payload.get("description") or ""))
            if path == "/api/install":
                return self._guard(lambda: app.install(
                    payload["mod_dir"], name=payload.get("name"),
                    enabled=payload.get("enabled", True),
                    position=int(payload.get("position") or 0)))
            if path == "/api/mod":
                return self._guard(lambda: app.set_mod(
                    payload["name"], bool(payload.get("enabled"))))
            if path == "/api/uninstall":
                return self._guard(lambda: app.uninstall(payload["name"]))
            if path == "/api/rebuild":
                return self._guard(lambda: app.rebuild(payload["title"]))
            if path == "/api/repair-apply":
                return self._guard(lambda: app.repair_apply(payload["name"]))
            if path == "/api/ai-sentences":
                return self._guard(lambda: app.ai_sentences(payload.get("text") or ""))
            if path == "/api/recipe":
                return self._guard(lambda: app.save_recipe(
                    payload.get("name") or "", payload.get("sentences") or [],
                    note=payload.get("note") or ""))
            if path == "/api/recipe-forget":
                return self._guard(lambda: app.forget_recipe(payload.get("name") or ""))
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        def _guard(self, fn):
            """One place where an exception becomes a readable sentence."""
            try:
                return _json(self, fn())
            except Exception as exc:                   # noqa: BLE001
                tb = traceback.format_exc(limit=4)
                return _json(self, {"ok": False, "error": _sentence(exc),
                                    "where": tb})

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
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            # The files come off the installed game and do not change while it
            # is installed; a list view asks for the same sprite repeatedly.
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(body)

    return Handler


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


def serve(port=0, game_root=None, host="127.0.0.1"):
    """Start the server; returns (httpd, app, url).  Caller calls `serve_forever`."""
    app = App(game_root=game_root)
    httpd = _quiet_connection_errors()((host, port), make_handler(app))
    url = "http://%s:%d" % (host, httpd.server_address[1])
    return httpd, app, url


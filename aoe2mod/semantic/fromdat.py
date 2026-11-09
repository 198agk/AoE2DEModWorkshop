# -*- coding: utf-8 -*-
"""Name a .dat by what THAT file says its objects are called.

Reported 2026-11-03, verbatim: 「选择指定的数据文件没起作用」.  The chooser did
switch files -- `App.set_dat` rebuilt the toolkit -- but the list on screen never
changed, because every name in it came from `semantic.index()`, a process-wide
singleton built from the JSON shipped with this product (i.e. the game's own
.dat).  Pick a mod that adds 6,000 units and the grid still showed the game's
1,651, so the mod's units were unreachable and the player's conclusion "the
choice did nothing" was correct from where they sat.

A mod .dat does not carry text either: a record names itself with a STRING ID
(unit ``LanguageDLLName``, tech ``LanguageDLLName``), and the text lives in
``resources/<locale>/strings/key-value/*.txt``.  The engine resolves that id
against the MOD's tables first and the install's tables second, so this module
does the same: mod root first, game root as the fallback, every ``key-value-*``
file in both.  Reading only ``key-value-strings-utf8.txt`` -- the obvious file --
loses 258 of the install's 1,649 named units, because the game splits names
across paphos / campaign / PDLC / tournament files (measured 2026-11-03).

What is deliberately NOT here: guessing a name from the record's internal code
(``SPRMN``, ``OLD-ACADEMY``).  Those are debug labels; the shipped semantic layer
already measured that only 310 of 1,651 satisfy internal == en.
"""
import glob
import io
import os
import time

#: Read in this order and let the earlier one win, so a Chinese player sees
#: Chinese and an install missing `tw` still gets a name.  `en` is the game's
#: documented global fallback.
LOCALES = ("zh", "tw", "en")

PREFIX = "key-value-"
SUFFIX = ".txt"


def _read_table(path, into):
    """Merge one ``<id> "text"`` table into ``into`` (first writer wins)."""
    try:
        with io.open(path, encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                head, _, rest = line.rstrip("\n").partition(" ")
                if not head.isdigit():
                    continue
                text = rest.strip()
                if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
                    text = text[1:-1]
                if text:
                    into.setdefault(int(head), text)
    except OSError:
        return


def mod_root_for(dat_path):
    """The folder whose ``resources/`` holds this .dat's own string tables.

    A mod's ``.dat`` lives at ``<mod>/resources/_common/dat/...``, so the mod
    root is the parent of its ``resources`` folder.
    """
    if not dat_path:
        return None
    parts = os.path.abspath(dat_path).split(os.sep)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].lower() == "resources":
            return os.sep.join(parts[:i]) or None
    return None


def tables_for(game_root, dat_path=None, locales=LOCALES):
    """``{string id: text}`` for the tables this .dat is named by.

    Measured 2026-11-03: 0.05 s for the install's 17 locales x 14 files, so this
    runs on every dat switch without a progress bar.
    """
    roots = []
    mr = mod_root_for(dat_path)
    if mr and game_root and os.path.normcase(mr) != os.path.normcase(
            os.path.abspath(game_root)):
        roots.append(mr)
    if game_root:
        roots.append(game_root)
    out = {}
    for base in roots:
        for loc in locales:
            folder = os.path.join(base, "resources", loc, "strings", "key-value")
            if not os.path.isdir(folder):
                continue
            for path in sorted(glob.glob(os.path.join(folder, PREFIX + "*" + SUFFIX))):
                _read_table(path, into=out)
    return out


def _names_by_id(tk, tables):
    """``({unit id: text}, {tech index: text})`` straight off the parsed records.

    The unit walk dedupes on id across all 63 civs (a unit has one name, however
    many civ copies it has) and keys TECH records by ARRAY INDEX, because that
    is what this product means by a tech id everywhere else (all 238 tech-tree
    node ids fall inside the 1,510-record array).
    """
    units, techs = {}, {}
    for civ in getattr(tk, "_civs", None) or ():
        for u in civ.get("units") or ():
            uid = u.get("id")
            if uid in units:
                continue
            sid = u.get("_dll_name") or 0
            text = tables.get(int(sid)) if sid else None
            if text:
                units[uid] = text
    records = tk._tech_records() if hasattr(tk, "_tech_records") else ()
    for i, t in enumerate(records):
        sid = t.get("lang_name") or 0
        text = tables.get(int(sid)) if sid else None
        if text:
            techs[i] = text
    return units, techs


def index_for(tk):
    """A `SemanticIndex` describing ``tk``'s own .dat, or None when unnecessary.

    Two sources, and the ORDER is the engine's own rule:

    1. the parsed records named through the string tables beside that .dat --
       this is what gives a mod's added units their names;
    2. the shipped JSON, for ids those tables do not name.  Load-bearing, not
       politeness: 196 of the install's 1,651 visible units are named by
       ``405xxx`` backup ids that no ``key-value`` file carries, and those are
       the six "Chronicles" civs' genuinely different units.

    Returns None when ``tk`` is the install's own file, so the ordinary player
    pays nothing for this and `semantic.index()` keeps serving.
    """
    from . import index as _idx_mod
    from .index import SemanticIndex

    root = getattr(tk, "game_root", None)
    dat = getattr(tk, "dat_path", None)
    if not root or not dat:
        return None
    if os.path.normcase(os.path.abspath(dat)) == os.path.normcase(
            os.path.abspath(os.path.join(root, "resources", "_common", "dat",
                                         "empires2_x2_p1.dat"))):
        return None

    t0 = time.time()
    tables = tables_for(root, dat)
    if not tables:
        return None
    extra_u, extra_t = _names_by_id(tk, tables)

    base = _idx_mod.index()

    # What this FILE actually contains wins over what the shipped JSON says, in
    # both directions:
    #   * an id the mod renamed or repurposed takes the mod's own text;
    #   * an id the mod deleted is dropped, so the grid stops offering rows that
    #     are not in the file the player chose.
    # The shipped text is used only where the tables have nothing to say -- 196
    # of the install's visible units are named by 405xxx backup ids that no
    # `key-value` file carries.
    here_u, here_t = set(), set()
    for civ in getattr(tk, "_civs", None) or ():
        for u in civ.get("units") or ():
            here_u.add(u.get("id"))
    for i in range(len(tk._tech_records() if hasattr(tk, "_tech_records") else ())):
        here_t.add(i)

    units_raw, techs_raw = {}, {}
    for uid, e in base.units.items():
        if uid not in here_u:
            continue
        raw = dict(getattr(e, "_extra", None) or {})
        text = extra_u.get(uid)
        if text:
            raw["en"] = raw["zh"] = raw["tw"] = text
            raw["resolved"] = True
        units_raw[uid] = raw
    for tid, e in base.techs.items():
        if tid not in here_t:
            continue
        raw = dict(getattr(e, "_extra", None) or {})
        text = extra_t.get(tid)
        if text:
            raw["en"] = raw["zh"] = raw["tw"] = text
            raw["resolved"] = True
        techs_raw[tid] = raw
    for uid, text in extra_u.items():
        if uid in units_raw:
            continue
        units_raw[uid] = {"internal": None, "en": text, "zh": text, "tw": text,
                          "name_string_id": 0, "resolved": True,
                          "civ_variants": None}
    for tid, text in extra_t.items():
        if tid in techs_raw:
            continue
        techs_raw[tid] = {"internal": None, "en": text, "zh": text, "tw": text,
                          "name_string_id": 0, "resolved": True}

    out = SemanticIndex(units=units_raw, techs=techs_raw)
    out.built_in = round(time.time() - t0, 2)
    out.dat_path = dat
    out.table_ids = len(tables)
    return out

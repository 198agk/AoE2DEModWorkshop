"""Give a unit the toolkit created a name the game will show.

A unit record names itself by a STRING ID (``LanguageDLLName``, an i32 at
``+3``), not by text.  So a new unit needs a new string id plus a line in a
string table -- and the shipped tables are inside the game folder, which the
mod may not touch.

The game already solves that: every locale ships
``resources/<locale>/strings/key-value/key-value-modded-strings-utf8.txt``,
605 bytes of instructions saying "place them in this file and when the mod is
enabled, these strings will also be added", and "The english string file is a
global fallback".  That is the supported way for a mod to add a string, so this
module writes that file instead of editing anything shipped.

Measured 2026-10-21 on the shipped install: zh, en and tw each hold 15,351
numeric ids and all three end at 30030001, so 30030002 is the first id no
locale uses.  The id must not collide with a number that a FUTURE game patch may
assign, and starting above the highest shipped id is the only rule available --
nothing in the game reserves a range.
"""
import io
import os


class StringError(Exception):
    """A name that cannot be shipped; the message is player-facing."""


# The numeric ids the shipped tables already use end here (measured, all three
# locales).  The first free id is the next one.
LAST_SHIPPED_ID = 30030001

TABLE_NAME = "key-value-strings-utf8.txt"
MODDED_TABLE_NAME = "key-value-modded-strings-utf8.txt"

# Locales worth writing when they exist.  `en` is the game's documented global
# fallback, so it is written even when the player's own locale is something else.
FALLBACK_LOCALES = ("en",)


def string_table_path(game_root, locale):
    return os.path.join(game_root, "resources", locale, "strings", "key-value",
                        TABLE_NAME)


def modded_table_rel(locale):
    """The mod-relative path of the file a mod adds strings through."""
    return "resources/%s/strings/key-value/%s" % (locale, MODDED_TABLE_NAME)


def available_locales(game_root):
    """Locales that actually ship a string table on this install."""
    root = os.path.join(game_root, "resources")
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        if os.path.isfile(string_table_path(game_root, name)):
            out.append(name)
    return out


def read_ids(path):
    """The numeric ids in one table, in file order.

    The files mix ``<number> "text"`` and ``NAME "text"`` lines (that mix is why
    three searches for a sentence by its number found nothing until the naming
    convention was understood), so only the purely numeric heads count here.
    """
    ids = []
    with io.open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            head = line.split(" ", 1)[0].strip()
            if head.isdigit():
                ids.append(int(head))
    return ids


def first_free_id(game_root, start=LAST_SHIPPED_ID + 1):
    """The lowest id no locale uses.

    Takes the maximum over every locale rather than trusting one: a locale whose
    table lags behind could otherwise hand out an id that another table already
    means something else by.
    """
    used = set()
    seen_any = False
    for locale in available_locales(game_root):
        ids = read_ids(string_table_path(game_root, locale))
        if ids:
            seen_any = True
            used.update(ids)
    if not seen_any:
        # No table readable: refuse rather than hand out an id that may collide.
        raise StringError("这个游戏目录里读不到任何字符串表，所以没法给新单位起名字")
    cand = max(start, LAST_SHIPPED_ID + 1)
    while cand in used:
        cand += 1
    return cand


def escape(text):
    """Escape a name for a string table line.

    The format is ``<id> "text"``; a quote would end the string early and a
    backslash may start an escape, so both are neutralised.  Newlines cannot
    appear inside one entry at all -- they would end the line and leave the rest
    as a second, broken table row.
    """
    out = str(text).replace("\\", "\\\\").replace('"', '\\"')
    return out.replace("\r", " ").replace("\n", " ").strip()


def string_line(string_id, text):
    return '%d "%s"\n' % (int(string_id), escape(text))


def build_files(game_root, entries, locales=None):
    """``{mod-relative path: bytes}`` carrying the given strings.

    ``entries`` is a list of ``(string_id, text)``.  One file per locale that
    ships a table, plus English as the documented global fallback.  The file body
    keeps the instructions the game ships in it -- deleting them changes nothing
    for the engine but removes the only explanation a player has for why the file
    is in their mod.
    """
    if not entries:
        return {}
    have = available_locales(game_root)
    if not have:
        raise StringError("这个游戏目录里读不到任何字符串表，所以没法给新单位起名字")
    wanted = list(locales) if locales else list(have)
    for loc in FALLBACK_LOCALES:
        if loc not in wanted and loc in have:
            wanted.append(loc)
    body_lines = [string_line(sid, text) for sid, text in entries]
    out = {}
    for loc in wanted:
        if loc not in have:
            continue
        header = [
            "//INSTRUCTIONS:\n",
            "//New unit names added by this mod.\n",
            "//Strings in this file are ADDED to the game's own table when the\n",
            "//mod is enabled; they are not a replacement for it.\n",
        ]
        payload = "".join(header + body_lines)
        out[modded_table_rel(loc)] = payload.encode("utf-8")
    return out

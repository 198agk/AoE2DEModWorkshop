# -*- coding: utf-8 -*-
"""What key a stored ``HotKeyID`` is bound to -- the key, and nothing else.

WHY THIS EXISTS: the editor prints a column's stored value next to its name
(`aoe2mod/game/valuenames.py`), but hotkeys were the one space with no table —
reported verbatim as 「这个热键编号全是数字，我怎么知道这些数字代表的是那个热键，
就是哪个键位」.  A player reads `16131` and has no way to learn it is the
Blacksmith build key, `S`.

WHY THE COMMAND NAME IS NOT SHOWN (asked for, 2026-11-16): the first cut printed
「铁匠铺  S」.  Reported back: 「你这个名字不需要，很多都是共用同一串编码的，我
只需要知道这些编码指的是什么热键」.  One id is reachable from several commands --
16101 carries 独特单位 for the castle, the dock and the siege workshop at once --
so the name is a guess about which caller asked, while the key is the fact the
player acts on.  The map is therefore id -> key letter only.

WHERE THE ANSWER LIVES (measured 2026-11-16 on the shipped install)

``resources/_common/dat/hotkeys.json`` (490,546 bytes) holds two lists --
``shared_hotkey_group_list`` (9 groups) and ``hotkey_group_list`` (27) -- whose
entries look like this::

    {"data_name": "BUILD_ECONOMIC", "name_string_id": 19214,
     "defaults_list": [{"name": "classic", "key": "B"},
                       {"name": "definitive", "key": "Q"},
                       {"name": "high definition", "key": "A"},
                       {"name": "left handed", "key": "Y"}],
     "button_action_list": [116]}

An entry names the command by ``name_string_id`` (a string id, resolved against
the locale table) and the key by ``defaults_list``.  The link to the `.dat` is
the OPTIONAL ``string_index_list``: it holds the ids the `.dat` stores in
``Creatable.TrainLocations.N.HotKeyID`` and ``ResearchLocations.N.HotKeyID``.
Flattening it gives 592 ids (6097..418131), and the mapping is exact --
16131 is the Blacksmith build key `S`; 16101 is the castle's unique unit key
`Q`; 16086 is `R`.  591 of those 592 entries carry a key; the one that does
not is dropped rather than shipped keyless.

WHY NOT THE FIRST-CHARACTER TRICK: the same id also indexes
``key-value-strings-utf8.txt`` directly, and there the TEXT is the key letter
(16079 -> "A").  That shortcut is documented by the community (Alian713's
hotkeys guide) and it does resolve some of the shipped values -- but it
disagrees with ``defaults_list`` wherever the game rebound the key: 16083 reads
"A" there while definitive is `Q`, 16101 reads "A" while it is `Q`.  A key
letter that is one patch out of date is worse than a number, because the player
presses it.  So the key comes from ``defaults_list.definitive``, the preset
this build actually ships.

WHAT STAYS A NUMBER: of the 100 distinct values the ``HotKeyID`` columns hold
across the whole install, 58 resolve here and 42 do not (155000, 139999, 16044,
16061, ...): they are in neither hotkeys.json nor any of the 222 ``*string*.txt``
files on this install, so there is nothing to say about them.  ``LanguageDLLHotKeyText``
is also left alone: it happens to equal ``HotKeyID + 139000`` for 207 of 400
sampled units but disagrees on 29 of the 198 that resolve, so the offset is a
habit and not a rule.  ``Creatable.ButtonHotkeyAction`` (values -1 / 153 / 154)
is a button action, not a hotkey id, and is deliberately absent from the table.

16000 is the "no hotkey" sentinel (`aoe2mod/mod/portgen.py:51-56`), carried by
360 shipped train slots, so it is spelled rather than left bare.  -1 means the
same thing and the page already prints 「没设」 for it.
"""
import json
import os

#: The value a creatable unit carries when the author never set a hotkey.
#: Same sentinel `aoe2mod/mod/portgen.py` documents; spelled here so a picker
#: does not offer 「16000」 as if it were a key.
NO_HOTKEY = 16000

#: The preset whose keys this build really uses.  The other three exist so a
#: player who switched presets in game still recognises the command.
PRESET = "definitive"

_REL = ("resources", "_common", "dat", "hotkeys.json")

#: Parsed files by absolute path.  A handful of entries at most -- one per
#: install and one per mod folder that ships its own hotkeys.json.
_CACHE = {}
_CACHE_MAX = 4


def json_path(game_root, dat_path=None):
    """Where this install's ``hotkeys.json`` is, or ``None``.

    ``game_root`` is tried first.  When it is missing (a mod ``.dat`` resolved
    to a folder, or a caller that only knows the .dat path) the .dat's own
    ancestors are walked, because a mod may ship its own hotkey table next to
    the data it accompanies.
    """
    cands = []
    if game_root:
        cands.append(os.path.join(game_root, *_REL))
    if dat_path:
        here = os.path.dirname(os.path.abspath(dat_path))
        for _ in range(6):
            cands.append(os.path.join(here, *_REL))
            nxt = os.path.dirname(here)
            if nxt == here:
                break
            here = nxt
    for path in cands:
        if os.path.isfile(path):
            return path
    return None


def _parse(path):
    """``{hotkey id: entry}`` for one hotkeys.json, cached by path.

    Entries WITHOUT ``string_index_list`` are dropped: 592 ids are addressable
    this way and the rest of the file's commands (camera, diplomacy, chat)
    never appear in a `.dat` column, so they cannot answer a value the editor
    is showing.
    """
    key = os.path.abspath(path)
    got = _CACHE.get(key)
    if got is not None:
        return got
    out = {}
    try:
        with open(path, "rb") as fh:
            blob = json.loads(fh.read().decode("utf-8-sig", "replace"))
    except (OSError, ValueError):
        # A corrupted file must not take the whole editor down with it: the
        # column then prints its number, which is what it did before this
        # module existed.
        blob = {}
    groups = []
    for k in ("shared_hotkey_group_list", "hotkey_group_list"):
        groups.extend(blob.get(k) or [])
    for grp in groups:
        gname = grp.get("data_name") or ""
        for e in grp.get("hotkey_list") or []:
            for sid in e.get("string_index_list") or []:
                if not isinstance(sid, int) or sid in out:
                    continue
                out[sid] = {
                    "group": gname,
                    "entry": e.get("data_name") or "",
                    "name_id": e.get("name_string_id"),
                    "keys": {d.get("name") or "": d.get("key") or ""
                             for d in (e.get("defaults_list") or [])
                             if isinstance(d, dict)},
                }
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def entries(game_root, dat_path=None):
    """``{hotkey id: {group, entry, name_id, keys}}``; ``{}`` when unreadable."""
    path = json_path(game_root, dat_path)
    if not path:
        return {}
    return _parse(path)


def key_of(sid, game_root, dat_path=None):
    """The key this build puts on that command (``""`` when unknown)."""
    e = entries(game_root, dat_path).get(sid)
    if not e:
        return ""
    keys = e["keys"]
    return keys.get(PRESET) or keys.get("classic") or ""


def labels(game_root, strings=None, dat_path=None):
    """``{hotkey id: "S"}`` for every id the `.dat` can store.

    The value is the key letter from ``defaults_list.definitive`` and nothing
    else, per 「很多都是共用同一串编码的，我只需要知道这些编码指的是什么热键」.
    ``strings`` is accepted and ignored: the locale table was only ever needed
    for the command name, and keeping the parameter means callers that already
    pass it (`ui/server.py`) do not have to change shape.

    An entry with no key at all is dropped: a bare number is what the column
    printed before this module existed, and inventing a placeholder would put a
    made-up key in front of a player.  Measured on this install: 591 of the 592
    addressable entries carry a key, and every one of the 58 census values that
    resolves at all resolves here too -- dropping the name costs no coverage.
    """
    out = {}
    for sid, e in entries(game_root, dat_path).items():
        k = e["keys"].get(PRESET) or e["keys"].get("classic") or ""
        if k:
            out[sid] = k
    if NO_HOTKEY not in out:
        out[NO_HOTKEY] = "没设热键"
    return out


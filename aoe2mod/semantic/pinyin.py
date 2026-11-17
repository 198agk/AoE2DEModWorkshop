# -*- coding: utf-8 -*-
"""Romanised search: 「tjpu」 finds 铁匠铺.

WHY A TABLE AND NOT A LIBRARY
------------------------------
`pypinyin` answers this in one call, and it is not shipped.  The bundle runs a
vendored CPython with a fixed set of packages (`make_bundle.py`), and adding a
dependency to answer "does this name sound like what the player typed" would put
a second thing that can be missing at run time on a screen whose whole job is to
still work when something is.  So the mapping is generated ONCE from the shipped
name tables (`_probe/_tmp/gen_pinyin.py`) and stored beside them as
`data/pinyin.json`: 1,620 distinct characters, 1,616 of them mapped, 24 KB.

WHY FOUR SPELLINGS PER NAME, NOT ONE
------------------------------------
Players do not type a name; they type what they can reach.  For 铁匠铺 that is
any of:

| typed | which spelling |
|---|---|
| `tiejiangpu` | every syllable in full |
| `tjp` | initials of every character |
| `tjpu` | initials, then the last syllable in full |
| `jiangpu` | the tail, having forgotten the first character |

`tjpu` is the one that decides whether this feels like a search: it is how pinyin
input methods work, mixing initials with a full syllable.  So `of()` hands back a
set of keys -- full, all-initials, and every "first k as initials, the rest in
full" split -- and a query matching the START of any key is a strong hit, while
a query sitting inside one is a weak hit.

WHAT IT DOES NOT DO, HONESTLY
- Tone is dropped.  The player types a keyboard, not a dictionary.
- Polyphones get the reading `lazy_pinyin` picks in isolation: 长 is `chang`, so
  「长城」 reads `changcheng`, not `zhangcheng`.  A context-dependent reading can
  therefore miss by pinyin and still be found by its characters, its English
  name and its number -- pinyin is the loosest of the four doors, so it ranks
  last.
- Traditional characters map to the same syllable as their simplified form
  (鐵 and 铁 both `tie`), but this game keeps a SEPARATE Taiwanese name in `tw`
  rather than a transliteration: 铁匠铺's `tw` field is 兵工廠, so nobody typing
  鐵匠鋪 will find it through pinyin or through `tw`.  That is the data, not the
  romanisation.
- Symbols and punctuation in a name are skipped, so a name with a dot in it
  still reads as one run of letters.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")

_CHAR = None      # char -> bare syllable, loaded on first use
_CACHE = {}       # name -> tuple of spellings, or () when it has no Chinese


def _table():
    global _CHAR
    if _CHAR is None:
        path = os.path.join(_DATA, "pinyin.json")
        try:
            with open(path, encoding="utf-8") as fh:
                _CHAR = json.load(fh)
        except (OSError, ValueError):
            _CHAR = {}      # no table: pinyin simply finds nothing
    return _CHAR


def of(text):
    """Every way to spell `text` on a keyboard; `()` when it has no Chinese.

    Ordered from the spelling a player is most likely to type to the least, so a
    caller that wants to show "you could have typed this" has something to show.
    All keys are lowercase a-z.
    """
    if not isinstance(text, str) or not text:
        return ()
    hit = _CACHE.get(text)
    if hit is not None:
        return hit
    table = _table()
    syl = [table[ch] for ch in text if table.get(ch)]
    if not syl:
        value = ()
    else:
        initials = "".join(s[0] for s in syl)
        keys = [initials, "".join(syl)]
        # "first k as initials, the rest in full" -- `tjpu` lives here.
        for k in range(1, len(syl)):
            keys.append(initials[:k] + "".join(syl[k:]))
        # Ordered short-to-long within each family, and de-duplicated, so a name
        # like 一一 does not offer the same key three times.
        seen = set()
        value = tuple(k for k in keys if k and not (k in seen or seen.add(k)))
    # Bounded so a session that opens a 5,874-name mod cannot grow this without
    # limit.  The shipped tables hold at most a few thousand distinct names, so
    # the cap is above the working set and below "unbounded".
    if len(_CACHE) < 40000:
        _CACHE[text] = value
    return value


def rank(query, *names):
    """How well `query` matches the romanisation of any of `names`.

    3 = the query starts one of the spellings (`tjp`, `tjpu`, `tiejiangpu`).
    4 = the query sits inside one (`jiangpu`, `angpu`).
    None = not a pinyin query at all.  That is the common answer: a query holding
    a digit, a space or a Chinese character belongs to somebody else's rule.

    Ranked BELOW both name ranks (2) and both number ranks (0 and 1): a query
    that also spells a name is asking for that name, and pinyin is a guess about
    what the player meant.
    """
    if not query or len(query) < 2 or not query.isascii() or not query.isalpha():
        return None
    best = None
    for name in names:
        for key in of(name):
            if key.startswith(query):
                return 3
            if best is None and query in key:
                best = 4
    return best
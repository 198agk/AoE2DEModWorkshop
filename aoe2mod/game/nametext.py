# -*- coding: utf-8 -*-
"""Names inside a `.dat` are BYTE strings, and Chinese mods store UTF-8 in them.

`parser.Reader.debug_string` decodes latin-1, deliberately: the reader must
round-trip every byte it read, and a codec that guesses would corrupt a record
on the way back out.  That is the right rule for the reader and the wrong one
for the screen.

Measured 2026-11-06 on the user's own mod (文明联盟 test 9, 125 MB): 230 of
5,874 technology names and **4,473 of 136,861 unit names** are UTF-8 written
into a byte string.  Shown through latin-1 they read `è´¸æ\x98\x93è\x8e·å\x8f\x96`,
which is what the screenshot showed.  `readable()` below is the display-side
translation: try UTF-8, and if the bytes are not valid UTF-8 (the shipped
English names, the `SPRMN` style internals) return the latin-1 text unchanged.

It never runs on a write path.  A rename writes UTF-8 back through
`parser`/`writer` byte-for-byte; only the label on screen is decoded.

2026-11-07, a second family: 中文 mods that store **GBK** in the same byte
string.  `2026 三国文明联盟整合11.06` names its units `°¢×ÈÌØ¿Ë`, which is
GBK for 阿兹特克 -- valid UTF-8 it is not, so `readable` returned it unchanged
and the command panel drew the bytes.  The order is UTF-8 first (a GBK byte run
can rarely be valid UTF-8, and when it is the text is longer and round-trips),
then GBK, and each answer has to earn its place: it must re-encode to exactly
the same bytes and must contain a Han character.  Anything else stays latin-1,
because「解不开」must look like「解不开」and not like a guess.
"""

import re


def readable(text):
    """The text a player should read for a `.dat` byte string.

    ``None`` and the empty string pass through.  A byte string that is valid
    UTF-8 with non-ASCII in it is decoded as UTF-8; anything else (pure ASCII,
    or bytes that are not UTF-8 at all) comes back exactly as given.
    """
    if not text or not isinstance(text, str):
        return text
    try:
        raw = text.encode("latin-1")
    except (UnicodeEncodeError, ValueError):
        # Already real Unicode (a JSON name table, a Chinese literal); nothing
        # was mangled on the way in.
        return text
    if not any(b >= 0x80 for b in raw):
        return text
    try:
        back = raw.decode("utf-8")
    except UnicodeDecodeError:
        back = None
    if back is not None:
        return back if back != text else text
    gbk = _as_gbk(raw)
    return gbk if gbk is not None else text


#: What a GBK name is made of: Han characters and the CJK punctuation that goes
#: with them.  Nothing else -- a GBK mis-read of a French name turns up kana or
#: a stray accented letter, and that is the tell.
_CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

#: Punctuation a Chinese mod uses AROUND a name.  `·` is the one that mattered:
#: `\xa1\xa4` is GBK's middle dot, and two mods pad their unit names with it.
#: Kept deliberately small -- a character not listed here still vetoes a decode,
#: because「解不开」must look like「解不开」.
_DECOR = frozenset("·•‧・—–―…°×÷±§")


def _as_gbk(raw):
    """``raw`` read as GBK, or None when it is not demonstrably GBK.

    Three conditions, each measured against a real name on this machine:

    * the bytes must encode back to themselves (no invented half pair);
    * there must be a Han character (``°¢×ÈÌØ¿Ë`` is 阿兹特克; ``Hello`` is not);
    * **every** non-ASCII byte must be consumed as part of a two-byte CJK
      character, and there must be at least two of them.

    The last one is what ``Écossais`` taught: one 0xC9 followed by an ASCII
    letter decodes to 蒫 plus six letters, and a rule that only asked「有汉字吗」
    would print that.  A GBK character is exactly two bytes, so counting them
    settles it without a heuristic -- an odd count is not GBK.

    **Except decoration.**  Two mods pad a name with GBK middle dots:
    ``¡¤¡¤¡¤[ÖÐÌï]¡¤¡¤¡¤`` is ``·····[中田]·····``.  Requiring every non-ASCII
    character to be CJK rejected those 126 names and kept drawing the bytes,
    which is the same complaint one round later.  `_DECOR` is the punctuation
    GBK actually carries around a name; anything outside it still vetoes.
    """
    hi = sum(1 for b in raw if b >= 0x80)
    if hi < 4 or hi % 2:
        return None
    try:
        got = raw.decode("gbk")
    except (UnicodeDecodeError, ValueError):
        return None
    if got.encode("gbk", "ignore") != raw:
        return None
    cjk = sum(1 for ch in got if ord(ch) >= 0x80)
    if cjk * 2 != hi:
        return None
    if any((ord(ch) >= 0x80) and not _CJK.match(ch) and ch not in _DECOR
           for ch in got):
        return None
    if not _HAN.search(got):
        return None
    return got


def stored(text):
    """The bytes a name becomes on the way INTO the `.dat`.

    UTF-8, always, and never `readable`'s guessing: this is the write path.  A
    name a player typed is real Unicode, and UTF-8 is the one encoding every
    shipped string table and every 中文 mod already agrees on.  `None` becomes
    empty bytes; bytes pass through untouched, because a caller that already has
    bytes (a round-trip, a copy) must not get them re-encoded.
    """
    if text is None:
        return b""
    if isinstance(text, (bytes, bytearray)):
        return bytes(text)
    return str(text).encode("utf-8")

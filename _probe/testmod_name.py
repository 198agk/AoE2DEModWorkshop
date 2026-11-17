# -*- coding: utf-8 -*-
r"""Rename the current test mod to the `dsh test` scheme, and define the scheme.

The user's instruction (m25178): 「你把你的测试模组的名字也改成dsh test，以后都用这个命名，
版本号改动内容测试内容你自己写」 -- so from now on every test mod is named `dsh test ...`,
with a version, what was changed and what is being tested.

The scheme implemented here:

    folder = Title = "dsh test v<N> - <changed> + <tested>"

    v<N>        monotonically increasing; never reused, so a stale copy on disk is
                always recognisable as stale
    <changed>   what the artifact actually edits, in player words
    <tested>    what the in-game observation is supposed to answer

and the `Description` carries the three lines a reader needs:
    the version, the change list, and the exact in-game reading.

This module is the single place the scheme lives, so future experiments import it
rather than inventing a new name each time.
"""
import os
import _gamepaths as GP
import re
import sys

PREFIX = "dsh test"

# ★★★ The game TRUNCATES the Title to 100 UTF-8 BYTES.  Measured 2026-10-16:
# v6's title was 58 chars / 103 bytes and the game wrote
#
#     local//dsh test v6 村民血量1000 + 不列颠可造蔷琵侦察兵（黑暗时代·去掉EnablingResearch
#
# into `mod-status.json` -- the final `）` (3 bytes) cut off at 100 bytes -- and
# the folder it then looked for did not exist, so the mod was enabled in the log
# and yet had NO EFFECT.  v5 was 43 chars / 89 bytes and worked.  100 bytes is
# 33 Chinese characters, so a Chinese title that merely LOOKS short is over.
#
# The mod list shows the folder name, so the limit applies to the name, not to
# the Description (which may be long -- a shipped mod has 554 bytes of it).
TITLE_MAX_BYTES = 100


def utf8_len(s):
    """Length of `s` in UTF-8 bytes -- which is the unit the game limits on."""
    return len((s or "").encode("utf-8"))


def fit_title(s, limit=TITLE_MAX_BYTES):
    """Cut `s` so its UTF-8 length is <= `limit`, never splitting a character.

    NEVER truncate in the middle of a multi-byte character: the game truncates on
    the byte boundary and would then hold an invalid fragment.  Prefer cutting at
    a character boundary and, when one is available, at a separator so the result
    still reads as a phrase.
    """
    if utf8_len(s) <= limit:
        return s
    out = ""
    for ch in s:
        if utf8_len(out + ch) > limit:
            break
        out += ch
    # try to end on a natural break instead of mid-word
    for sep in ("（", "(", " ", "·", "｜", "+"):
        i = out.rfind(sep)
        if i > limit // 4:
            out = out[:i].rstrip()
            break
    return out



def name_for(version, changed, tested=None):
    """The folder name and Title for a test mod, in CHINESE.

    The user asked for Chinese (m25601: 「你模组名字和备注就不能写中文描述吗」) -- the
    game's mod list is the only place these strings are ever read, and it is read by
    the user, so they belong in the user's language.

    ``version`` is an int or a string like "v1".  ``changed`` is a SHORT player-facing
    phrase naming what the artifact edits; the game shows the folder name in its mod
    list, so the detailed record (what was changed, what is being tested, and the
    controls) belongs in the `info.json` Description, not here.
    """
    v = version if str(version).startswith("v") else "v%s" % version
    base = "%s %s %s" % (PREFIX, v, changed.strip())
    if tested:
        base += "（测：%s）" % tested.strip()
    # The game stores the Title as the folder path and cuts it at 100 UTF-8 bytes;
    # an over-long Chinese title silently loses its tail and the mod stops loading.
    if utf8_len(base) > TITLE_MAX_BYTES:
        base = fit_title(base)
    return base


def description_for(version, changed, tested, extra_lines=()):
    """The `info.json` Description, in Chinese: version, change list, in-game reading."""
    v = version if str(version).startswith("v") else "v%s" % version
    lines = [
        "%s %s" % (PREFIX, v),
        "改动：%s" % changed.strip(),
        "验证：%s" % tested.strip(),
    ]
    lines.extend(extra_lines)
    return "｜".join(lines)


VERSION_RE = re.compile(r"^%s\s+v(\d+)\b" % re.escape(PREFIX))


def version_of(folder_name):
    """The version number in a `dsh test vN ...` folder name, or None."""
    m = VERSION_RE.match(folder_name or "")
    return int(m.group(1)) if m else None


def existing_versions(local_dir):
    """Every `dsh test vN ...` folder currently installed, newest first."""
    if not os.path.isdir(local_dir):
        return []
    out = []
    for d in os.listdir(local_dir):
        v = version_of(d)
        if v is not None and os.path.isdir(os.path.join(local_dir, d)):
            out.append((v, d))
    return sorted(out, reverse=True)


if __name__ == "__main__":
    # self-check: the scheme round-trips, a non-scheme name is rejected, and the
    # strings are CHINESE (the user asked; the mod list is user-facing).
    n = name_for(1, "村民血量 + 不列颠加蔷琵侦察兵")
    assert n == "dsh test v1 村民血量 + 不列颠加蔷琵侦察兵", n
    assert version_of(n) == 1
    assert version_of("aoe2mod Smoke9 Dat Grant") is None
    assert name_for("v3", "甲") == "dsh test v3 甲"
    assert name_for(2, "甲", "乙") == "dsh test v2 甲（测：乙）"
    d = description_for(1, "甲", "乙", extra_lines=["对照A：丙"])
    assert d.startswith("dsh test v1｜改动：甲｜验证：乙"), d
    assert "｜" in d and "对照A" in d
    # the description must not leak the old English scaffolding
    assert "changed:" not in d and "tested:" not in d
    # ★★★ the 100-byte title ceiling (the v6 failure, 2026-10-16)
    _long = name_for(6, "村民血量1000 + 不列颠可造蔷琵侦察兵",
                     "黑暗时代·去掉EnablingResearch")
    # the separator-aware cut leaves the phrase "-- not the whole tail"; what must
    # hold is only that the result FITS.  Over-cutting is allowed and preferred to
    # a mid-word break, so do not assert a lower bound here.
    assert utf8_len(_long) <= TITLE_MAX_BYTES, (utf8_len(_long), _long)
    assert _long.encode("utf-8").decode("utf-8") == _long  # never split a character
    _n = name_for(6, "村民血量1000 + 不列颠可造蔷琵侦察兵（黑暗时代·去掉EnablingResearch）")
    assert utf8_len(_n) <= TITLE_MAX_BYTES, (utf8_len(_n), _n)
    assert _n.encode("utf-8").decode("utf-8") == _n
    # a short name must pass through untouched
    assert name_for(1, "村民血量") == "dsh test v1 村民血量"
    print("testmod_name: OK")
    print("  例:", n)
    print("  备注:", d)
    print("  长名截断:", name_for(6, "村民血量1000 + 不列颠可造蔷琵侦察兵",
                                  "黑暗时代·去掉EnablingResearch"))
    print("  上限:", TITLE_MAX_BYTES, "UTF-8 字节 =", TITLE_MAX_BYTES // 3, "个汉字")
    local = GP.LOCAL
    print("  已装的 dsh test 模组:", existing_versions(local) or "无")

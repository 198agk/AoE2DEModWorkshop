# -*- coding: utf-8 -*-
r"""The engine truncates a mod Title at 100 UTF-8 BYTES, and loads the folder by
the TRUNCATED name -- so an over-long title makes a mod that logs as enabled and
silently does nothing.

Found 2026-10-16 by reading `mod-status.json` after the user said the game could
not read the mod ("游戏依旧无法正常读取你的数据模组").  The record was:

    Path = 'local//dsh test v6 村民血量1000 + 不列颠可造蔷琵侦察兵（黑暗时代·去掉EnablingResearch'
    Title = the same string

and `os.path.isdir()` on that folder was False, because the real folder still had
its closing `）`.  Proof it is a BYTE cut, not a character cut:

    real.encode("utf-8")[:100] == applied_path.encode("utf-8")   ->  True
    real folder 103 bytes / applied 100 bytes / the lost tail is "）" (3 bytes)

v5 was 89 bytes and loaded; v6 was 103 and did not.  The limit therefore belongs
in `validate_info`, where an over-long Title is REFUSED rather than shipped.

This pin asserts the boundary itself, the truncation arithmetic, and that the
shipped mods respect it.
"""
import json
import _gamepaths as GP
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_probe"))

from aoe2mod.mod import emitter as E          # noqa: E402
import testmod_name as TN                     # noqa: E402

MODS = GP.MODS

FAILS = []


def check(name, cond, detail=""):
    print("  %-66s %s%s" % (name, "PASS" if cond else "FAIL",
                            "" if cond else "   " + str(detail)))
    if not cond:
        FAILS.append(name)


print("TITLE BYTE LIMIT: the engine cuts a Title at 100 UTF-8 bytes and then")
print("looks for a folder of that cut name, so an over-long title is a mod that")
print("is 'enabled' and silently does nothing.")
print()

print("A  the constant and the byte arithmetic")
check("the limit is 100 UTF-8 bytes", E.TITLE_MAX_BYTES == 100, E.TITLE_MAX_BYTES)
check("title_bytes counts UTF-8 bytes, not characters",
      E.title_bytes("ab") == 2 and E.title_bytes("中") == 3,
      "%d %d" % (E.title_bytes("ab"), E.title_bytes("中")))
check("so 100 bytes is 33 Chinese characters and one spare byte",
      E.title_bytes("中" * 33) == 99 and E.title_bytes("中" * 34) == 102)

print()
print("B  validate_info REFUSES an over-long Title instead of shipping it")
_ok = E.make_info("short", author="a", description="d")
check("a short Title is publishable", E.validate_info(_ok) == [], E.validate_info(_ok))
_long_title = "中" * 40                     # 120 bytes
_bad = E.make_info(_long_title, author="a", description="d")
_problems = E.validate_info(_bad)
check("a 120-byte Title is NOT publishable", len(_problems) == 1, _problems)
# This refusal is READ BY THE PLAYER: the screen joins the sentences they typed
# into the title, so a run of Chinese can pass 100 bytes nobody typed a long
# title.  2026-10-20 the sentence was still English ("... so this mod would be
# enabled and silently do nothing ..."), i.e. an internal note shown to a player.
check("and the message is a Chinese sentence naming the byte counts",
      _problems and "120" in _problems[0] and "100" in _problems[0]
      and "字节" in _problems[0]
      and not __import__("re").search(r"[A-Za-z]{2,}", _problems[0]),
      _problems)

print()
print("C  _fit_title cuts to the limit without splitting a character")
_fit = E._fit_title("中" * 40)
check("the fitted title fits", E.title_bytes(_fit) <= E.TITLE_MAX_BYTES,
      E.title_bytes(_fit))
check("it is valid UTF-8 (never a half character)",
      _fit.encode("utf-8").decode("utf-8") == _fit)
check("a title already within the limit is returned unchanged",
      E._fit_title("abc") == "abc")
_mixed = E._fit_title("dsh test v6 村民血量1000 + 不列颠可造蔷琵侦察兵（黑暗时代·去掉EnablingResearch）")
check("the real v6 name fits after fitting",
      E.title_bytes(_mixed) <= E.TITLE_MAX_BYTES, _mixed)
check("and the name_for() helper applies the same limit",
      E.title_bytes(TN.name_for(
          6, "村民血量1000 + 不列颠可造蔷琵侦察兵",
          "黑暗时代·去掉EnablingResearch")) <= E.TITLE_MAX_BYTES)

print()
print("C2 the AUTO title the page writes is fitted, the TYPED one is refused")
# The page builds its title by joining the sentences, then slices it to 60
# CHARACTERS.  Chinese costs 3 bytes per character, so 60 characters is up to
# 180 bytes: a player who types six ordinary sentences presses 做成 mod and the
# build fails on a byte count they never wrote.  The user chose (2026-10-20):
# trim what the PAGE wrote, refuse what the PLAYER typed, and say why.
_names = ["把不列颠的村民血量改成1000"] * 6
_page = ("dsh " + " + ".join(_names))[:60]
check("the page's own 60-character title is over the byte limit",
      E.title_bytes(_page) > E.TITLE_MAX_BYTES, E.title_bytes(_page))
_fit_auto = E.fit_auto_title(_page)
check("fit_auto_title brings it under the limit",
      E.title_bytes(_fit_auto) <= E.TITLE_MAX_BYTES,
      "%d bytes: %r" % (E.title_bytes(_fit_auto), _fit_auto))
check("and it is still a real title, not an empty one", bool(_fit_auto.strip()),
      _fit_auto)
check("a title within the limit survives fitting unchanged",
      E.fit_auto_title("dsh 村民血量改成1000") == "dsh 村民血量改成1000")
# A sentence can carry a picture path ("给村民换张图 D:\pics\a.png"), and the
# page joins the sentence text into the title, so the colon and backslash land
# in a folder name the publisher rejects.
_ok["Title"] = "dsh 村民 给村民换张图 D:\\pics\\a.png"
check("a path in the title is refused rather than shipped",
      any("字符" in p for p in E.validate_info(_ok)), E.validate_info(_ok))
_path_fit = E.fit_auto_title("dsh 村民 给村民换张图 D:\\pics\\a.png")
check("the auto fitter drops the path instead of picking it clean",
      "Dpics" not in _path_fit and "换张图" in _path_fit, _path_fit)
check("and what it leaves is publishable",
      not any("字符" in p for p in E.validate_info(E.make_info(
          _path_fit, author="a", description="d"))), _path_fit)

print()
print("D  every installed mod's Title actually names an existing folder")
# This is the invariant the v6 failure broke: `mod-status.json` records a Path
# derived from the Title, and the engine loads that Path.  If a Title was cut,
# the Path points nowhere.
using = []
_sp = os.path.join(MODS, "mod-status.json")
if os.path.exists(_sp):
    _o = json.loads(open(_sp, "rb").read().decode("utf-8"), strict=False)
    for _m in _o.get("Mods", []):
        _p = _m.get("Path", "")
        _k, _f = _p.split("//", 1) if "//" in _p else ("", _p)
        _t = _m.get("Title", "")
        using.append((_k, _t, _f,
                      os.path.isdir(os.path.join(MODS, _k, _f)),
                      E.title_bytes(_t)))
    check("the census read mod-status.json", len(using) > 0, len(using))
    check("every recorded Title is within the byte limit for its folder",
          all(u[4] <= E.TITLE_MAX_BYTES or not u[3] for u in using),
          [(u[1][:30], u[4]) for u in using if u[4] > E.TITLE_MAX_BYTES])
    # The invariant this pin owns is TRUNCATION, not tidiness.  A stale entry --
    # a record whose folder was deleted after the record was written -- is a
    # normal consequence of uninstalling while the game is closed (the game
    # rewrites this file on its next launch), and this project is not allowed to
    # write mod-status.json at all.  Asserting "every entry resolves" would fail
    # for a reason that has nothing to do with the 100-byte cut, and the failure
    # would look like the very bug this file exists to catch.
    #
    # The discriminating question is: did the TRUNCATION put the folder out of
    # reach?  A title over the limit must never point anywhere, because the
    # engine is looking for its cut prefix; a title within the limit pointing at
    # a missing folder is a stale record.
    _over = [u for u in using if u[4] > E.TITLE_MAX_BYTES]
    check("no over-long Title points at a folder that does not exist",
          not [u[1] for u in _over if not u[3]],
          [u[1] for u in _over if not u[3]])
    _stale = [u[1] for u in using if not u[3]]
    if _stale:
        print("     note: %d stale record(s) whose folder is gone (not a title"
              " failure): %s" % (len(_stale), [t[:36] for t in _stale]))
    for _k, _t, _f, _ok2, _nb in using:
        print("     %-6s %4d bytes  exists=%-5s %s"
              % (_k, _nb, _ok2, _t[:44]))
else:
    print("     (no mod-status.json on this machine -- skipping D)")

print()
if FAILS:
    print("TITLE BYTE LIMIT: FAILED -> %s" % FAILS)
    sys.exit(1)
print("TITLE BYTE LIMIT: a mod Title is capped at %d UTF-8 bytes (= %d Chinese"
      % (E.TITLE_MAX_BYTES, E.TITLE_MAX_BYTES // 3))
print("  characters); past that the engine loads a folder named after the CUT")
print("  title, so the mod is enabled in the log and has no effect.  The refusal")
print("  lives in validate_info, so this cannot be shipped by accident again.")

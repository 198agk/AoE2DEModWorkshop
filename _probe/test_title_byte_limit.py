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
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_probe"))

from aoe2mod.mod import emitter as E          # noqa: E402
import testmod_name as TN                     # noqa: E402

MODS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
        r"\76561198406248391\mods")

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
check("and the message names the byte counts and the consequence",
      _problems and "120" in _problems[0] and "100" in _problems[0]
      and "silently" in _problems[0], _problems)

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

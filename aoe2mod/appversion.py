# -*- coding: utf-8 -*-
"""The workshop's own version number — one place, so no screen can invent another.

Why this exists
---------------
Reported 2026-11-08, while looking at the 版本 card on the 关于 page:

> 版本应该是指模组工坊的版本，写个 ver1.0

The card was printing one sentence and that sentence was about the `.dat`:
「模组工坊 by RemonBo。这次读到的数据格式是 54，文明 63 个。」 The player asked
for a version and got a format ordinal.  He is right that the word 版本 on a page
about the tool should mean the tool.

Two different numbers live here, and confusing them is the whole bug:

* **this file** carries the workshop's version — what a bug report says when the
  question is "which build of the tool did this".
* `aoe2mod/game/version.py` carries the *game's* build (`101.103.57257.0`) read
  out of `AoE2DE_s.exe`, and `Parser.version` carries the `.dat`'s FileVersion
  ordinal (`54`), which only answers "which field layout do I parse".

The page prints all three, and each is labelled with the thing it belongs to.
Nothing here is derived from the others: a patch to the game must not move the
tool's version, and a release of the tool must not touch the game's.

Why not read it from `desktop/src-tauri/tauri.conf.json`
-------------------------------------------------------
Because the page would then have a second copy of the number anyway (the bundle
manifest is read by the Rust build, not by the Python server), and the two would
drift the first time one of them is bumped.  The bundle manifest is a *consumer*
of this constant, not its home: `_probe/test_about_page.py` asserts that its
version agrees with this one on major.minor, so a bump that forgets the bundle
turns a nail red instead of shipping two answers.
"""

#: What the player sees, and what a bug report quotes.
#:
#: The scheme the player asked for on 2026-11-18 (「我每产生新改动，版本号就增加
#: 0.0001」): every round of changes moves the LAST decimal place, so 1.0 ->
#: 1.0001 -> 1.0002 and so on.  A four-decimal number is not decoration: the
#: comparison in `aoe2mod/updates.py` reads the dot part as a decimal fraction,
#: which keeps 1.0001 sorted below 1.1 and above 1.0.
VERSION = "1.0001"

#: What this build changed, newest first, in one short line each.  Printed on
#: the 关于 page under the version and published into the gist next to the same
#: number, so 「检查更新」 can say what is new instead of only that something is:
#: a version number alone asks the player to download 286 MB blind.
CHANGES = (
    "选中的记录可以直接拖到另一个工坊窗口：数值、图形、造价整份照搬，落点不对会说为什么",
    "拖动期间光标旁有一个提示，告诉你要落在哪个窗口、带了几条",
    "另一个窗口改了数据文件，这一边的列表会自己重画，不用手动刷新",
    "版本号从这一版起每次改动加 0.0001，并在这里写清改了什么",
)

#: The same number with the word in front, so screens do not each spell it.
LABEL = "ver " + VERSION


def _semver(text=None):
    """``1.0001`` -> ``1.0.1``: the same build, spelled for a manifest.

    Three-part versions are a different grammar from the player's decimal one:
    a Rust manifest, an installer header and a PyPI-style string cannot say
    four decimals.  The dot part is therefore read as a fraction scaled to four
    places and becomes the patch number, so every bump the player asked for is
    also a bump here -- 1.0 -> 1.0.0, 1.0001 -> 1.0.1, 1.0002 -> 1.0.2 -- and
    a bigger move still sorts above the small ones (1.1 -> 1.0.1000).
    """
    raw = str(text if text is not None else VERSION)
    head, _, tail = raw.partition(".")
    digits = "".join(ch for ch in tail if ch.isdigit()) or "0"
    return "%s.0.%d" % (head, int(digits.ljust(4, "0")[:4]))


#: What `tauri.conf.json`, `Cargo.toml` and the installer header must say.
#: Derived rather than typed twice: `_probe/test_about_page.py` compares the
#: manifest against this, so a bump that forgets a manifest turns a nail red.
SEMVER = _semver()

#: The product's name as it appears on screens and in `info.json` titles.
TITLE = "模组工坊"

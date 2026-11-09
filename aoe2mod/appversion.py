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

#: What the player sees, and what a bug report quotes.  Bump the minor for a
#: feature release, the major for a break in the saved-mod format.
VERSION = "1.0"

#: The same number with the word in front, so screens do not each spell it.
LABEL = "ver " + VERSION

#: The product's name as it appears on screens and in `info.json` titles.
TITLE = "模组工坊"

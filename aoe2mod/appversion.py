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
version agrees with this one, so a bump that forgets the bundle turns a nail red
instead of shipping two answers.

The numbering scheme, third time
--------------------------------
2026-11-21 the player asked for "two decimals after the point, publish every
0.10".  2026-11-23 he asked for "+0.01 per build, do not publish every time".
2026-11-26 he changed the grammar itself:

> 你发布1.7.0版本吧，以后都这样0.0.0写
> 更新内容写：更新了更换模型功能和文联ai最优解教程

So the number is now plain `major.minor.patch` — three parts, the same shape a
semver manifest wants, and the same shape the player will type in the next
request.  1.7.0 is the first build in this grammar; every earlier number
(1.60, 1.69) keeps its old two-decimal reading in the changelog and in the
already-published releases.

Publishing is still a decision and not a side effect of saving a file: the patch
slot is the build counter, and a build whose patch is 0 (1.7.0, 1.8.0) is the one
the player may be handed.  `_probe/publish_release.py` refuses anything else
unless it is named with `--force`.
"""

#: What the player sees, and what a bug report quotes.  Three parts, always.
VERSION = "1.7.1"

#: What this build changed，一行一件，用玩家看得懂的话写。 印在 关于 页的版本
#: 下面，也发进 gist 的同号旁边，让「检查更新」能说出新在哪儿，而不是只报一个号码。
#: 只写改了什么都别写怎么改的：玩家要知道值不值得装，不需要读实现。
#:
#: 1.7.0 ships exactly the two lines the player dictated on 2026-11-26
#: (「更新内容写：更新了更换模型功能和文联ai最优解教程」).  The long per-round notes
#: are still in the git history and in docs/CHANGELOG.md; what a player reads on
#: the 关于 page is this.
CHANGES = (
    "加入了文本编辑功能",
)

#: The same number with the word in front, so screens do not each spell it.
LABEL = "ver " + VERSION

#: What a mod this tool builds names as its author when the player leaves the
#: 作者 field blank.  The player asked for this on 2026-11-22: builds were landing
#: in the mod list with the development handle ("dsh" in one place, "aoe2mod" in
#: another) where the tool's own name belongs, and a shot through the mod-manager
#: panel is not the place to explain what "dsh" is.
#:
#: One spelling, read by every fallback -- `upgrade._author_text`,
#: `api.repair_apply`, the three build routes in `ui.server`, and
#: `locations.set_mod_info` -- because the previous two spellings were exactly
#: the bug: the same blank field produced a different author depending on which
#: route happened to fill it in.
AUTHOR = "AoE2 DE Mod Workshop"


def _parts(text=None):
    """``"1.7.3"`` -> ``(1, 7, 3)``.  The number the player reads, split in three.

    Every other function here goes through this one, so "three parts" is decided
    in a single place.  Missing pieces read as zero (`"1.7"` -> `(1, 7, 0)`,
    `"2"` -> `(2, 0, 0)`), which is what lets an old two-decimal number from the
    changelog still be compared against a new one.
    """
    raw = str(text if text is not None else VERSION)
    bits = []
    for piece in raw.split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        bits.append(int(digits or 0))
    while len(bits) < 3:
        bits.append(0)
    return bits[0], bits[1], bits[2]


def spell(major, minor, patch=0):
    """``(1, 7, 0)`` -> ``"1.7.0"``: three parts, no padding, no surprises.

    The player asked for `0.0.0` on 2026-11-26, so nothing is padded and nothing
    is dropped: 1.7.0 stays 1.7.0, and 1.10.3 keeps its ten.
    """
    return "%d.%d.%d" % (int(major), int(minor), int(patch))


def _semver(text=None):
    """The same build, spelled for a manifest.  Now identical to `VERSION`.

    Before 2026-11-26 this had to translate "1.10" (one point one zero) into
    "1.10.0" because a Rust manifest would read the 10 as a patch number.  The
    player's own number is three-parted now, so there is nothing left to
    translate -- the function stays because the manifest readers call it, and
    because a two-decimal legacy string still has to come out three-parted.
    """
    major, minor, patch = _parts(text)
    return spell(major, minor, patch)


#: The patch value a number must carry to be publishable.  Zero means `x.y.0`;
#: anything else is a build sitting between two releases.  Kept as a constant
#: because `is_release_boundary` reads it and `_probe/test_release_cadence.py`
#: pins it, so "let us publish every build" cannot be done by quietly editing one
#: number in one screen.
STEP = 0

#: The step between two BUILDS, in the patch slot.  Every round of work moves the
#: patch by one (1.7.0 -> 1.7.1) so two screenshots can be told apart, while
#: publishing stays on a patch of `STEP` (zero).
BUILD_STEP = 1


def is_release_boundary(text=None):
    """Is this a number the player is meant to be handed, or one we are still on?

    A release is three hundred megabytes of uploads (an installer, a full zip and
    a 30 MB update zip), so "publish" is a decision, not a side effect of saving a
    file.  Only a whole `x.y.0` is a decision: 1.7.0 yes, 1.8.0 yes, 1.7.1 no.

    A number that is not a boundary is not an error -- it is a build sitting
    between two releases, and it is allowed to exist locally and in a bundle.  It
    is only `_probe/publish_release.py` that refuses it.
    """
    _, _, patch = _parts(text)
    return patch == STEP


def next_release(text=None):
    """The next number that may be published, starting from this one.

    ``1.7.0`` -> ``1.8.0``, ``1.7.3`` -> ``1.8.0``, ``1.9.0`` -> ``1.10.0``.
    Used by the 关于 page to tell the player when the next one is coming, and by
    the cadence test to prove a build number never silently becomes a release.
    """
    major, minor, _patch = _parts(text)
    minor += 1
    return spell(major, minor, STEP)


#: What `tauri.conf.json`, `Cargo.toml` and the installer header must say.
#: Derived rather than typed twice: `_probe/test_about_page.py` compares the
#: manifest against this, so a bump that forgets a manifest turns a nail red.
SEMVER = _semver()

#: The product's name as it appears on screens and in `info.json` titles.
TITLE = "模组工坊"

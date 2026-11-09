"""Which of the several ``empires2_x2_p1.dat`` files on this machine to edit.

Reported 2026-11-03, verbatim: 「我要改指定的dat或者ai/xs，你这完全没有给我
选择」.  The complaint is exact, and the reason there is more than one file is
not an accident of this tool:

* every install has ``<game>/resources/_common/dat/empires2_x2_p1.dat``;
* a **mode** (``<game>/modes/Pompeii/...``) ships its own, and the game swaps
  to it when that mode is selected;
* every installed mod that changes game data ships one too, and while that mod
  is enabled **the game loads the mod's file, not the install's**.

Measured 2026-11-03 on this machine: 23 installed mods, **16 of them ship a
``.dat``** (11.5 MB each), plus the install's own and one under ``modes/``.
Editing the install's file while a data mod is enabled is therefore an edit the
game never reads -- a silent no-op, which is the worst failure this tool has.

This module only *finds* them.  Choosing one is `App.set_dat`; reading the
``VER x.y`` head off each is `aoe2mod.mod.provenance.head_version`, which
inflates 64 bytes rather than parsing 93 MB.
"""

import os

from . import locations as LOC
from ..dat import parser as P


#: What the game's own file is called, relative to a game root or a mod folder.
DAT_REL = LOC.DAT_REL

MODES_DIR = "modes"


def _entry(path, scope, label, mod=None):
    """One candidate, with the facts a chooser needs and no parse cost.

    ``format`` is the GameVersion ordinal the ``VER x.y`` head maps onto, i.e.
    which field layout this file needs.  It is deliberately NOT called
    ``version``: the screen already had to be taught (2026-11-03) that 54 is a
    format number and the game's release is a different string entirely.
    """
    from ..mod import provenance as PV
    head = None
    fmt = None
    try:
        head = PV.head_version(path)
        if head:
            fmt = P.gv_from_version_string(head)
    except Exception:
        # A file we cannot even inflate a head out of is still listed: the
        # player may have pointed at a partially written mod, and hiding it
        # would make the chooser disagree with Explorer.
        head, fmt = head, None
    try:
        size = os.path.getsize(path)
        when = os.path.getmtime(path)
    except OSError:
        size, when = 0, 0
    return {
        "path": os.path.abspath(path),
        "scope": scope,          # game | mode | mod
        "label": label,          # what the screen prints
        "mod": mod,              # mod folder name, when scope == "mod"
        "bytes": size,
        "mtime": int(when),
        "head": head,            # "VER 8.9"
        "format": fmt,           # 54
        # Whether OUR parser can interpret it at all.  A legacy third-party
        # `VER 7.8` file parses with a different field set; saying so up front
        # is better than a screen that silently shows the wrong 400 fields.
        "supported": fmt is not None,
    }


def candidates(game_root=None, profile_root=None):
    """Every ``.dat`` a player could reasonably mean, newest install first.

    Order is deliberate: the install's own file first (that is what the game
    loads with no data mod enabled), then modes, then installed mods in the
    engine's priority order.  Duplicates by real path are collapsed, because a
    mod folder can be reachable through more than one account glob.
    """
    game_root = game_root or LOC.find_game_root()
    out = []
    seen = set()

    def add(path, scope, label, mod=None):
        if not path or not os.path.isfile(path):
            return
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            return
        seen.add(key)
        out.append(_entry(path, scope, label, mod))

    add(LOC.dat_path(game_root), "game", "游戏本体")

    # Modes.  `<game>/modes/<Name>/resources/_common/dat/...` -- the folder name
    # is the mode's name as the game shows it.
    modes = os.path.join(game_root, MODES_DIR)
    try:
        for name in sorted(os.listdir(modes)):
            add(os.path.join(modes, name, DAT_REL), "mode", name)
    except OSError:
        pass

    # Installed mods that carry game data.  `list_mods` already sorts by the
    # engine's Priority, which is the order the game layers them in.
    try:
        root = profile_root or LOC.find_profile_root()
        for m in LOC.list_mods(root):
            path = os.path.join(m.get("path") or "", DAT_REL)
            if m.get("exists") and os.path.isfile(path):
                add(path, "mod", m.get("title") or m.get("name") or "",
                    mod=m.get("name"))
    except Exception:
        pass

    return out


def default_path(game_root=None):
    """The install's own file: what the game reads with no data mod enabled."""
    return LOC.dat_path(game_root or LOC.find_game_root())


def find(candidates_list, path):
    """The candidate whose real path matches ``path``, or ``None``."""
    if not path:
        return None
    want = os.path.normcase(os.path.abspath(path))
    for c in candidates_list:
        if os.path.normcase(c["path"]) == want:
            return c
    return None


def check_path(path):
    """Validate a ``.dat`` a caller named directly (not chosen from the list).

    Returns ``(abs_path, error)``.  A path is acceptable when it exists, is a
    file, and its ``VER x.y`` head maps onto a layout our parser knows -- the
    same rule `Parser.parse` enforces, applied before 93 MB are inflated so the
    screen can refuse in one sentence instead of failing five seconds later.
    """
    if not path or not str(path).strip():
        return "", "没有说要改哪一份 .dat"
    p = os.path.abspath(str(path).strip())
    if not os.path.isfile(p):
        return p, "找不到这份文件：%s" % p
    try:
        head = __import__("aoe2mod.mod.provenance", fromlist=["x"]).head_version(p)
    except Exception as exc:
        return p, "读不出这份文件的版本头：%s" % exc
    if not head:
        return p, ("%s 开头没有 VER x.y，它不像一份 AoE2 DE 的 .dat（可能下坏了）"
                   % os.path.basename(p))
    try:
        P.gv_from_version_string(head)
    except P.UnsupportedVersionError:
        return p, ("%s 的版本是 %s，这一版解析器只认 VER 7.1 到 VER 8.9。"
                   "强行按已知布局读会得到错位的数据，所以这里先停下。"
                   % (os.path.basename(p), head))
    return p, None

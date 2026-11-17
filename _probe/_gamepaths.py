# -*- coding: utf-8 -*-
"""Where the game and the player's profile are, resolved instead of typed into
every probe by hand.

WHY
---
Every probe used to spell the author's own paths out in full -- the Steam library
on one drive, the player folder under a user name, the 17-digit SteamID64.  That
worked on exactly one machine, and it also meant the repository published a
stranger's directory layout in ninety-odd files.

aoe2mod.game.locations already knows how to find both of them (registry, the
library .vdf, AOE2MOD_GAME_ROOT / AOE2MOD_PROFILE).  This module just asks it
once, so a probe says GP.DAT instead of a path.

NOTHING HERE THROWS.  A clone with no game installed gets empty strings, and the
probe that needed them fails on its own terms -- open('') -- instead of at import
time.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from aoe2mod.game import locations as _L
except Exception:                                    # a bare copy of _probe/
    _L = None


def _call(name, *a):
    if _L is None:
        return None
    try:
        return getattr(_L, name)(*a)
    except Exception:
        return None


GAME = _call("find_game_root") or ""
PROFILE = _call("find_profile_root") or ""
ACCOUNT = (_call("pick_account", PROFILE) or "") if PROFILE else ""
STEAMID = os.path.basename(ACCOUNT.rstrip("\\/")) if ACCOUNT else "0"
MODS = os.path.join(ACCOUNT, "mods") if ACCOUNT else ""
SUBSCRIBED = os.path.join(MODS, "subscribed") if MODS else ""
LOCAL = os.path.join(MODS, "local") if MODS else ""
LOGS = os.path.join(PROFILE, "logs") if PROFILE else ""
DAT_DIR = os.path.join(GAME, "resources", "_common", "dat") if GAME else ""
DAT = os.path.join(DAT_DIR, "empires2_x2_p1.dat") if DAT_DIR else ""
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics") if GAME else ""
REPO = _ROOT


if __name__ == "__main__":
    for k in ("GAME", "PROFILE", "ACCOUNT", "STEAMID", "MODS", "SUBSCRIBED",
              "DAT", "REPO"):
        print("%-11s %s" % (k, globals()[k]))

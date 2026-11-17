# -*- coding: utf-8 -*-
"""Throwaway game profiles, so a suite can install without touching the player's.

WHY THIS EXISTS
---------------
`install_mod` writes into `mods/local/<title>` AND registers a row in
`mods/mod-status.json`.  `Toolkit.install(profile_root=None)` and
`App.rebuild(profile_root=None)` both mean "the REAL profile", so any suite that
saves with install, or rebuilds anything, edits the list a player sees in the
game's mod manager.  Measured 2026-11-12: one full-suite run left five test mods
at the top of the player's list -- `rb one field`, `rb mixed`, `rb all civs`,
`fx one number`, plus `gate rebuild` installed from the shipped exe.

`aoe2mod/game/locations.py:314 find_profile_root` accepts any directory holding
`mods/mod-status.json` as a complete profile, so an empty one is enough: no
2.5 GB copy of the player's subscribed mods, and the entry dies with the temp
dir.  `AOE2MOD_STATE_DIR` / `AOE2MOD_BUILD_OUT` are a SEPARATE axis (the build
record and the output folder) and are not set here.
"""
import io
import os

PROFILE_ENV = "AOE2MOD_PROFILE"


def temp_profile(parent, label=""):
    """Make `parent/app` an empty profile and point the process at it.

    Returns the profile path.  `parent` is normally the suite's own temp dir, so
    the caller's cleanup removes the profile too.
    """
    app = os.path.join(parent, "app")
    os.makedirs(os.path.join(app, "mods"))
    with io.open(os.path.join(app, "mods", "mod-status.json"), "w",
                 encoding="utf-8") as f:
        f.write(u'{"Mods":[],"Unsub":[]}')
    os.environ[PROFILE_ENV] = app
    return app


def enabled_local(path=None):
    """The local mods this process would have installed into, for an assertion."""
    import json
    prof = path or os.environ.get(PROFILE_ENV) or ""
    doc_path = os.path.join(prof, "mods", "mod-status.json")
    if not os.path.isfile(doc_path):
        return []
    with io.open(doc_path, encoding="utf-8", errors="replace") as f:
        doc = json.loads(f.read())
    return [m.get("Path") for m in (doc.get("Mods") or [])
            if m.get("Enabled") and str(m.get("Path") or "").startswith("local//")]

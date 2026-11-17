# -*- coding: utf-8 -*-
r"""PIN: `uninstall`/`set_mod_enabled` must accept a mod's Title, not just its folder.

## The bug, found by accident

`uninstall_mod(name)` and `set_mod_enabled(name)` built the status key as
``"%s//%s" % (kind, name)`` and compared it to the entry's `Path`.  That works only
if `name` IS the folder name.  But a UI lists mods by **Title**, and on this machine
the two genuinely differ for every subscribed mod:

    Path  = subscribed//182654_Age of Anime (Chibi Edition)
    Title =             Age of Anime (Chibi Edition)

The publisher prefixes the FOLDER with the workshop id; the Title does not have it.
So ``uninstall("Age of Anime (Chibi Edition)")`` removed **nothing**, and the caller
read ``entries_removed: 0`` as "that mod was never installed".

It surfaced because a test installed a mod under ``title="aoe2mod restart-note
check"`` while the FOLDER was ``aoe2mod Smoke6 Champi Scout``: uninstalling by title
left a stale entry whose folder had also been replaced.

## The fix

``resolve_mod_name(profile_root, name, kind, account) -> (folder, how)`` tries the
folder name first, then the Title, and reports which matched (``"path"`` /
``"title"`` / ``"bare"``).  Both `uninstall_mod` and `set_mod_enabled` go through it
and report ``requested`` alongside the resolved ``name``.

Also pinned: `install_mod`'s manifest carries ``requires_game_restart``,
``restart_note`` and ``storage_points``.  That flag is NOT a blanket True any
more.  It was, and the claim behind it -- "the game reads
``resources/_common/dat/`` once, at startup, so a mod copied in while the game
runs has its JSON half silently do nothing" -- was wrong.  The user reported in
game (2026-10-16) that a data mod dropped into the mods folder while the game is
running IS read by that running session, graphics excepted.

The measurement I had read as support actually says the opposite of what I took
from it: `_probe/test_mod_load_timing.py` shows the engine enabling these mods in
a later mod-manager pass (line 860-996, after "Opening resource packages" at
254-267).  Being enabled late is not being ignored; that pass is when a newly
added folder is noticed at all.  Nor was the failure it "explained" ever one
clean experiment -- the single tree-only attempt (2026-10-14) could not have
moved the menu anyway, because the menu reads the shipped panel file.

Run:  python _probe\test_mod_name_resolution.py
"""
import json
import _gamepaths as GP
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = GP.GAME
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  the two spellings really do differ on this machine")
prof = G.find_profile_root()
tk = A.open_toolkit(game_root=GAME)
mods = tk.mods()
differing = [(m["name"], m["title"], m["kind"]) for m in mods
             if m.get("title") and m["title"] != m["name"]]
print("     installed mods whose Title != folder name: %d of %d"
      % (len(differing), len(mods)))
for n, t, k in differing[:4]:
    print("        [%s] folder %-46s" % (k, n[:46]))
    print("        [%s] title  %-46s" % (" " * len(k), t[:46]))
check("at least one installed mod has a Title different from its folder name",
      bool(differing))

print()
print("B  resolve_mod_name finds the folder from either spelling")
if differing:
    n0, t0, k0 = differing[0]
    got, how = G.resolve_mod_name(prof, n0, kind=k0)
    check("a folder name resolves to itself", got == n0 and how == "path",
          "got %r (%s)" % (got, how))
    got, how = G.resolve_mod_name(prof, t0, kind=k0)
    check("a Title resolves to the folder", got == n0 and how == "title",
          "got %r (%s)" % (got, how))
got, how = G.resolve_mod_name(prof, "definitely-not-a-mod-xyz", kind="local")
check("an unknown name is returned unchanged with how='bare'",
      got == "definitely-not-a-mod-xyz" and how == "bare",
      "got %r (%s)" % (got, how))

def fake_profile(tmp):
    """A minimal profile whose account dir can be discovered and written.

    `pick_account` needs `<profile>/<account>/mods` to exist, so the fixture has to
    create it -- the first version of this test patched `find_profile_root` but left
    the directory structure missing, and the install died with
    `FileNotFoundError: no <profile>/<account>/mods folder`.
    """
    acc = os.path.join(tmp, "9999")
    os.makedirs(os.path.join(acc, "mods", "local"), exist_ok=True)
    os.makedirs(os.path.join(acc, "mods", "subscribed"), exist_ok=True)
    return acc


print()
print("C  install's folder name follows info.json's Title, so uninstall-by-Title is")
print("   the SAME string -- and title resolution only matters for Steam's mods")
tmp = tempfile.mkdtemp(prefix="aoe2mod_name_")
try:
    acc = fake_profile(tmp)
    src = os.path.join(tmp, "folder name")
    E.emit_json_mod(
        src, {os.path.join("widgetui", "probe.json"): b'{"a":1}'},
        E.make_info("Title that differs", author="aoe2mod probe"))
    G.install_mod(src, tmp, title="Title that differs", kind="local",
                  enabled=True, position=0, account=acc)
    inst = [m for m in G.list_mods(tmp) if m["kind"] == "local"]
    check("the mod installed", len(inst) == 1, "mods=%s" % inst)
    # `install_mod` defaults `name` to the Title read from info.json, NOT to the
    # source folder's basename.  That is deliberate: the folder name IS the mod
    # name the engine reports, so it must match the Title.  (An earlier version of
    # this test asserted the basename and was wrong.)
    check("the folder is named after the Title, not the source basename",
          bool(inst) and inst[0]["name"] == "Title that differs",
          "name=%r" % (inst[0]["name"] if inst else None))
    check("and the Title matches it",
          bool(inst) and inst[0]["title"] == "Title that differs")
    rep = G.uninstall_mod(tmp, "Title that differs", kind="local", account=acc)
    check("uninstall by that name removed the entry",
          rep["entries_removed"] == 1, "report=%s" % rep)
    check("and the folder is gone",
          rep["folder_removed"] and
          not os.path.isdir(os.path.join(acc, "mods", "local",
                                         "Title that differs")))
    left = [m for m in G.list_mods(tmp) if m["kind"] == "local"]
    check("no stale entry is left behind", not left, "left=%s" % left)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("C2 the diverging case: a Steam-style entry whose folder has a workshop-id")
print("   prefix while the Title does not -- exactly what 8 of 8 installed mods")
print("   on this machine look like")
tmp = tempfile.mkdtemp(prefix="aoe2mod_steam_")
try:
    acc = fake_profile(tmp)
    # build the folder and the status entry the way Steam's publisher does
    folder = os.path.join(acc, "mods", "subscribed",
                          "182654_Age of Anime (Chibi Edition)")
    os.makedirs(folder, exist_ok=True)
    E.emit_json_mod(folder, {os.path.join("widgetui", "probe.json"): b'{"a":1}'},
                    E.make_info("Age of Anime (Chibi Edition)",
                                author="RauFrosch"))
    doc, _a, _b = G.read_status_doc(tmp, account=acc)
    G.upsert_mod_entry(doc, "182654_Age of Anime (Chibi Edition)",
                       kind="subscribed", title="Age of Anime (Chibi Edition)",
                       enabled=True, position=0)
    G.write_status_doc(acc, doc)
    got, how = G.resolve_mod_name(tmp, "Age of Anime (Chibi Edition)",
                                  kind="subscribed", account=acc)
    check("a Title resolves to the prefixed folder",
          got == "182654_Age of Anime (Chibi Edition)" and how == "title",
          "got %r (%s)" % (got, how))
    rep = G.uninstall_mod(tmp, "Age of Anime (Chibi Edition)",
                          kind="subscribed", account=acc)
    check("and uninstalling BY TITLE removes the right entry",
          rep["entries_removed"] == 1 and
          rep["name"] == "182654_Age of Anime (Chibi Edition)",
          "report=%s" % rep)
    check("reporting that it resolved via the Title",
          rep.get("resolved_by") == "title", "report=%s" % rep)
    check("and the prefixed folder is gone",
          not os.path.isdir(folder))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("D  set_mod_enabled also accepts a Title")
tmp = tempfile.mkdtemp(prefix="aoe2mod_enable_")
try:
    acc = fake_profile(tmp)
    src = os.path.join(tmp, "folder name")
    E.emit_json_mod(src, {os.path.join("widgetui", "probe.json"): b'{"a":1}'},
                    E.make_info("Another Title", author="aoe2mod probe"))
    G.install_mod(src, tmp, title="Another Title", kind="local",
                  enabled=True, position=0, account=acc)
    G.set_mod_enabled(tmp, "Another Title", False, kind="local", account=acc)
    e = [m for m in G.list_mods(tmp) if m["kind"] == "local"][0]
    check("disabling by Title worked", e["enabled"] is False,
          "enabled=%r" % e["enabled"])
    G.set_mod_enabled(tmp, "Another Title", True, kind="local", account=acc)
    e = [m for m in G.list_mods(tmp) if m["kind"] == "local"][0]
    check("re-enabling by Title worked", e["enabled"] is True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("E  install reports the restart requirement -- and it is NOT always True")
tmp = tempfile.mkdtemp(prefix="aoe2mod_restart_")
try:
    acc = fake_profile(tmp)
    src = os.path.join(tmp, "m")
    # A data mod: `.dat` plus the JSON files beside it.  The user reported in game
    # (2026-10-16) that dropping one in while the game runs DOES take effect, so
    # this must NOT ask for a restart.  The old manifest said True for everything.
    E.emit_json_mod(src, {os.path.join("resources", "_common", "dat",
                                       "CivTechTrees", "BRITONS.json"): b"{}"},
                    E.make_info("Restart Test", author="aoe2mod probe"),
                    base_dir=GAME)
    man = G.install_mod(src, tmp, title="Restart Test", kind="local", account=acc)
    check("a data mod does NOT ask for a restart",
          man.get("requires_game_restart") is False,
          "man=%s" % {k: man.get(k) for k in ("requires_game_restart",
                                              "storage_points")})
    check("and it names no graphics storage point",
          man.get("storage_points") == [], repr(man.get("storage_points")))
    check("and it DOES carry the .dat the game needs to start",
          bool(man.get("dat")), repr(man.get("dat")))
    note = man.get("restart_note") or ""
    # NOT `"restart needed" not in note` -- the note opens with "no restart
    # needed", which CONTAINS that substring, so that assertion would fail on
    # correct text.  Ask for the positive claim instead.
    check("and the note says so positively (picked up while running)",
          note.startswith("no restart needed") and "running" in note,
          "note=%r" % note[:90])

    # A graphics mod is the other case: a running session has already bound its
    # atlases, so this one DOES ask.
    src2 = os.path.join(tmp, "g")
    E.emit_json_mod(src2, {os.path.join("widgetui", "textures", "x.png"): b"PNG"},
                    E.make_info("Graphics Test", author="aoe2mod probe"))
    man2 = G.install_mod(src2, tmp, title="Graphics Test", kind="local",
                         account=acc)
    check("a graphics mod asks for a restart",
          man2.get("requires_game_restart") is True,
          "man2=%s" % {k: man2.get(k) for k in ("requires_game_restart",
                                                "storage_points")})
    check("and the note explains WHY (something was already bound)",
          "bound" in (man2.get("restart_note") or ""),
          "note=%r" % (man2.get("restart_note") or "")[:90])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("MOD NAME RESOLUTION: a mod can be addressed by folder OR Title, and an")
print("  install asks for a restart only when a running game could not see it.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

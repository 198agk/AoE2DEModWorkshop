# -*- coding: utf-8 -*-
"""A build that ships a .dat must reach the profile as TWO mods.

The failure this guards against is quiet: `emit_data_mod` moves `widgetui` into a
sibling folder, `install` only installs the folder it was given, and the result is a
mod that loads (canary reads 4000) with no icon -- exactly the shape that cost five
runs in v74..v82.  So the assertions here are about the profile, not about the build
output: two folders, both enabled, the UI half carrying the three files.

It also pins the width of the rule.  Only `widgetui` moves: locale string tables and
`.sld` sprites stay beside the `.dat`, because published mods prove those work there
(Chow ships a 12 MB dat next to two 19,677 B string tables; WAIFor 662 `.sld` in the
same folder).  A rule that quietly widened would still pass every positive check
above and start breaking mods that used to be fine.
"""
import os
import _gamepaths as GP
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = GP.GAME
FAILS = []


def check(ok, label, detail=""):
    if ok:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s :: %s" % (label, detail))
        FAILS.append(label)


def seed_png(folder):
    """A picture that cannot be confused with any shipped icon."""
    sys.path.insert(0, HERE)
    from aoe2mod.game import ddstex as DD
    w = h = 256
    rgba = bytearray()
    for y in range(h):
        for x in range(w):
            on = ((x // 32) + (y // 32)) % 2 == 0
            rgba += bytes((255, 0, 255, 255)) if on else bytes((0, 255, 255, 255))
    path = os.path.join(folder, "split_checker.png")
    open(path, "wb").write(DD.encode_png(w, h, bytes(rgba)))
    return path


def fake_profile(root):
    """A profile with one account, so install never guesses a real one.

    Layout is `<profile_root>/<account>/mods` -- `find_accounts` lists the profile
    root and keeps any child that owns a `mods` folder.  I first wrote
    `<root>/profile/<steamid>/mods`, one level too deep, and `pick_account` raised
    "找不到任何带 mods 目录的账号" -- the product was right, the fixture was wrong.
    """
    acc = os.path.join(root, "76561198000000001")
    os.makedirs(os.path.join(acc, "mods", "local"))
    open(os.path.join(acc, "mods", "mod-status.json"), "wb").write(
        b'{"Mods": []}')
    return root


def main():
    pic_dir = tempfile.mkdtemp(prefix="split_pic_")
    out = os.path.join(tempfile.mkdtemp(prefix="split_out_"), "mod")
    prof = fake_profile(tempfile.mkdtemp(prefix="split_prof_"))
    pic = seed_png(pic_dir)

    tk = A.open_toolkit(game_root=GAME)
    intent = {
        "intent": "unit.stat", "unit": 109, "stat": "hit_points",
        "value": 4000, "civs": ["British"],
    }
    create = {
        "intent": "unit.create", "donor": 83, "civ": "British",
        "name": "图标学徒", "button": 6, "builder": 109, "icon": pic,
    }
    man = tk.build_bundle([intent, create], out, title="dsh test split 分开投递",
                          author="dsh", overwrite=True)

    print("=== A. the build split the two halves")
    check(man.get("verification", {}).get("ok") is True,
          "the build verified",
          man.get("verification"))
    ui_dir = man.get("ui_mod_dir")
    check(bool(ui_dir) and os.path.isdir(ui_dir),
          "the build reports a second folder for the interface layer",
          ui_dir)
    data_mod = man.get("mod_dir")
    data_files = [f.get("rel") if isinstance(f, dict) else f
                  for f in (man.get("files") or [])]
    check(not any(str(f).replace("\\", "/").startswith("widgetui/")
                  for f in data_files),
          "and the data folder no longer carries any widgetui file",
          [f for f in data_files if "widgetui" in str(f)])
    check(bool(data_files) and any(str(f).endswith(".dat") for f in data_files),
          "while it still carries the .dat", len(data_files))
    ui_files = man.get("ui_files") or []
    # Walking `ui_dir` unguarded turns "the emitter stopped splitting" into a
    # TypeError, and a crash is not a red assertion: the reader learns nothing about
    # which claim failed.  Keep every later check runnable.
    ui_rels = []
    if ui_dir and os.path.isdir(ui_dir):
        ui_rels = sorted(os.path.relpath(os.path.join(dp, n), ui_dir).replace("\\", "/")
                         for dp, _dn, fn in os.walk(ui_dir) for n in fn)
    check(any(r.endswith("widgetui/icons.json") for r in ui_rels),
          "the interface folder carries icons.json", ui_rels)
    check(any(r.endswith("widgetui/materials.json") for r in ui_rels),
          "and materials.json", ui_rels)
    check(any(r.endswith(".dds") for r in ui_rels),
          "and the picture itself", ui_rels)
    print("  data folder: %s (%d files)" % (data_mod, len(data_files)))
    print("  ui folder  : %s (%d files) %s" % (ui_dir, len(ui_files), ui_rels))

    print("=== B. install puts BOTH in the profile")
    inst = tk.install(data_mod, name="dsh test split 分开投递", title="dsh test split 分开投递",
                      enabled=True, position=3, profile_root=prof, overwrite=True)
    check(inst.get("installed") is True or inst.get("name"),
          "the data half installed",
          {k: inst.get(k) for k in ("name", "enabled", "priority")})
    ui_inst = (inst.get("ui_install") or {})
    # `"why_not" not in {}` is true, so an assertion written that way stays green when
    # install never tries the second half at all -- reverse validation caught exactly
    # that on 2026-10-24.  The claim is positive: a folder path came back.
    check(bool(ui_inst.get("mod_dir")) and "why_not" not in ui_inst,
          "the interface half installed as well", ui_inst)

    rows = G.list_mods(prof)
    names = [r.get("title") or r.get("name") for r in rows]
    mine = [r for r in rows if str(r.get("title") or "").startswith("dsh test split")]
    check(len(mine) == 2,
          "the profile lists two mods from this one build",
          [(r.get("title"), r.get("enabled"), r.get("priority")) for r in rows])
    check(all(r.get("enabled") is True for r in mine),
          "and both are enabled, so neither half is silently off",
          [(r.get("title"), r.get("enabled")) for r in mine])

    ui_row = [r for r in mine if "界面" in str(r.get("title"))]
    check(len(ui_row) == 1, "one of them is the interface half",
          [(r.get("title")) for r in mine])
    if ui_row:
        ui_path = ui_row[0].get("path")
        found = []
        for dp, _dn, fn in os.walk(ui_path):
            for n in fn:
                found.append(os.path.relpath(os.path.join(dp, n),
                                             ui_path).replace("\\", "/"))
        check(any(f.endswith("widgetui/icons.json") for f in found),
              "and it really sits in the profile with its icon tables", found[:6])
        check(any(f.endswith(".dds") for f in found),
              "including the picture the game has to draw", found[:6])

    data_row = [r for r in mine if "界面" not in str(r.get("title"))]
    if data_row:
        dpath = data_row[0].get("path")
        dats = [os.path.join(dp, n) for dp, _dn, fn in os.walk(dpath) for n in fn
                if n.endswith(".dat")]
        check(len(dats) == 1, "the data half carries exactly one .dat", dats)
        stray = [os.path.join(dp, n) for dp, _dn, fn in os.walk(dpath) for n in fn
                 if "widgetui" in dp.replace("\\", "/")]
        check(not stray,
              "and no widgetui file travelled with the data, which is the whole point",
              stray[:4])

    print("=== C. a build that ships no .dat is not split")
    try:
        _icons_only = E.split_ui_layer  # present
        print("  split_ui_layer present: True")
    except AttributeError:
        pass
    plain = os.path.join(tempfile.mkdtemp(prefix="v84_plain_"), "mod")
    os.makedirs(plain)
    open(os.path.join(plain, "info.json"), "wb").write(
        b'{"Author":"dsh","CacheStatus":0,"Description":"only ui","Title":"plain"}')
    os.makedirs(os.path.join(plain, "widgetui"))
    open(os.path.join(plain, "widgetui", "icons.json"), "wb").write(b"{}")
    info = E.read_info_json(os.path.join(plain, "info.json"))
    got = E.split_ui_layer(plain, info)
    check(got is None, "a folder with no .dat is left alone", got)
    check(os.path.isdir(os.path.join(plain, "widgetui")),
          "and its widgetui folder stays where it is")

    print("=== D. the split is widener-narrow: only widgetui")
    check(E.ui_only_path("widgetui\\icons.json") is True,
          "widgetui is a UI-layer path")
    check(E.ui_only_path(os.path.join("resources", "zh", "strings",
                                      "key-value", "k.txt")) is False,
          "a locale string table is NOT, because a shipped mod proves it works beside a .dat")
    check(E.ui_only_path(os.path.join("resources", "_common", "drs", "graphics",
                                      "x.sld")) is False,
          "nor are sprite files, for the same reason")
    check(E.ui_only_path(os.path.join("resources", "_common", "wpfg", "x.xaml")) is False,
          "nor wpfg, where no measurement exists either way")

    print("=== D2. the （界面） suffix survives the 100-byte title cap")
    # The failure is silent and reproduces the exact confusion the suffix exists
    # to prevent: `_fit_title` cuts from the RIGHT, so a title that already sits
    # near the cap loses the （界面） and both halves carry the SAME name in the
    # mod list.  Measured 2026-11-12 on an auto title of 90 bytes: the UI half
    # came back byte-identical to the data half.
    long_title = "单位 882 把第 882 号单位从第 12 号建筑的卡上拿掉（全部 63 个文明）"
    fitted = E._fit_title_stem(long_title, "（界面）")
    check(fitted.endswith("（界面）"),
          "a long title still ends in the interface marker", fitted)
    check(fitted != long_title,
          "so the two halves cannot carry the same name", fitted)
    check(E.title_bytes(fitted) <= E.TITLE_MAX_BYTES,
          "and the result still fits the engine caps it in bytes",
          E.title_bytes(fitted))
    check(E._fit_title_stem("单位「SPRMN」 生命值", "（界面）") == "单位「SPRMN」 生命值（界面）",
          "a short title is left untouched apart from the marker")

    print("=== E. uninstalling one half removes the other")
    # The build output folder is `<name>_ui`, but the INSTALLED folder is named after
    # the title, and `install()` names the interface half `<base title>（界面）`.  Both
    # spellings exist in the wild, so the pairing must not assume one.
    gone = tk.uninstall("dsh test split 分开投递", profile_root=prof)
    left = [r for r in G.list_mods(prof)
            if str(r.get("title") or "").startswith("dsh test split")]
    check(bool((gone.get("paired") or {}).get("mod_dir")),
          "uninstalling the data half also removed the interface half",
          gone.get("paired"))
    check(not left,
          "and nothing from this build is left installed",
          [(r.get("title"), r.get("enabled")) for r in left])

    # Reinstall and try the other direction: uninstall the interface half by name.
    inst2 = tk.install(data_mod, name="dsh test split 分开投递",
                       title="dsh test split 分开投递", enabled=True, position=3,
                       profile_root=prof, overwrite=True)
    check(bool((inst2.get("ui_install") or {}).get("mod_dir")),
          "the pair installs again for the reverse direction",
          inst2.get("ui_install"))
    gone2 = tk.uninstall("dsh test split 分开投递（界面）", profile_root=prof)
    left2 = [r for r in G.list_mods(prof)
             if str(r.get("title") or "").startswith("dsh test split")]
    check(bool((gone2.get("paired") or {}).get("mod_dir")),
          "uninstalling the interface half also removed the data half",
          gone2.get("paired"))
    check(not left2,
          "so a half is never left overriding tables on its own",
          [(r.get("title"), r.get("enabled")) for r in left2])

    # A mod with no sibling at all must not invent one: `resolve_mod_name` returns the
    # name unchanged when nothing matches, so `entries_removed`/`folder_removed` are the
    # honest signal.
    lonely = os.path.join(tempfile.mkdtemp(prefix="v86_lonely_"), "mod")
    os.makedirs(os.path.join(lonely, "widgetui"))
    open(os.path.join(lonely, "info.json"), "wb").write(
        b'{"Author":"dsh","CacheStatus":0,"Description":"x","Title":"dsh test lonely"}')
    tk.install(lonely, name="dsh test lonely", title="dsh test lonely",
               profile_root=prof, overwrite=True)
    gone3 = tk.uninstall("dsh test lonely", profile_root=prof)
    check(gone3.get("paired") is None,
          "a mod with no other half reports no pair instead of inventing one",
          gone3.get("paired"))
    shutil.rmtree(os.path.dirname(lonely), ignore_errors=True)

    print("=== F. a rebuild does not inherit the previous interface half")
    rebuild_out = os.path.join(tempfile.mkdtemp(prefix="v87_rebuild_"), "mod")
    first = tk.build_bundle([
        {"intent": "unit.stat", "unit": 109, "stat": "hit_points", "value": 4000},
        {"intent": "unit.create", "donor": 83, "civ": "British",
         "name": "旧图标", "icon": pic},
    ], rebuild_out, title="dsh test rebuild", author="dsh", overwrite=True)
    check(bool(first.get("ui_mod_dir")),
          "the first build splits and names an interface folder", first.get("ui_mod_dir"))
    sibling = rebuild_out.rstrip("\\/") + "_ui"
    check(os.path.isdir(sibling), "and that folder really came into being", sibling)

    # Same output folder, no icon at all.  A correct rebuild must not ship the old tables.
    second = tk.build_bundle([
        {"intent": "unit.stat", "unit": 109, "stat": "hit_points", "value": 4100},
    ], rebuild_out, title="dsh test rebuild", author="dsh", overwrite=True)
    check(second.get("ui_mod_dir") is None,
          "the second build does not split, because it has no icon layer",
          second.get("ui_mod_dir"))
    check(not os.path.isdir(sibling),
          "and the first build's interface folder was removed, not left on disk",
          sibling)
    shutil.rmtree(os.path.dirname(rebuild_out), ignore_errors=True)

    print("=== G. switching one half off switches the other off")
    inst3 = tk.install(data_mod, name="dsh test split 分开投递",
                       title="dsh test split 分开投递", enabled=True, position=3,
                       profile_root=prof, overwrite=True)
    check(bool((inst3.get("ui_install") or {}).get("mod_dir")),
          "the pair installs again for the switch", inst3.get("ui_install"))
    got = tk.set_mod_enabled("dsh test split 分开投递", False, profile_root=prof)
    rows3 = [(r.get("title"), r.get("enabled")) for r in G.list_mods(prof)
             if str(r.get("title") or "").startswith("dsh test split")]
    check(got.get("enabled") is False, "the data half reports off", got)
    check(bool(got.get("paired")), "and a second half was switched with it",
          got.get("paired"))
    check(all(e is False for _t, e in rows3) and len(rows3) == 2,
          "no half is left on while the screen says off", rows3)

    # ...and turning it back on brings both back.
    back = tk.set_mod_enabled("dsh test split 分开投递", True, profile_root=prof)
    rows4 = [(r.get("title"), r.get("enabled")) for r in G.list_mods(prof)
             if str(r.get("title") or "").startswith("dsh test split")]
    check(back.get("enabled") is True, "switching back on works", back)
    check(all(e is True for _t, e in rows4) and len(rows4) == 2,
          "and both halves come back on together", rows4)

    # A mod with no sibling must not raise: `set_mod_enabled` refuses unknown
    # names instead of creating them, and the pairing probe has to treat that as
    # "no other half" rather than as a failure of the switch itself.
    lonely_dir = os.path.join(tempfile.mkdtemp(prefix="v88_lonely_"), "mod")
    os.makedirs(os.path.join(lonely_dir, "widgetui"))
    open(os.path.join(lonely_dir, "info.json"), "wb").write(
        b'{"Author":"dsh","CacheStatus":0,"Description":"x","Title":"dsh test lonely2"}')
    tk.install(lonely_dir, name="dsh test lonely2", title="dsh test lonely2",
               profile_root=prof, overwrite=True)
    solo = tk.set_mod_enabled("dsh test lonely2", False, profile_root=prof)
    check(solo.get("enabled") is False and solo.get("paired") is None,
          "a mod with no other half switches fine and reports no pair", solo)
    tk.uninstall("dsh test lonely2", profile_root=prof)
    shutil.rmtree(os.path.dirname(lonely_dir), ignore_errors=True)

    for d in (pic_dir, prof):
        shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(os.path.dirname(out), ignore_errors=True)

    print()
    if FAILS:
        print("SPLIT DELIVERY: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("SPLIT DELIVERY: ONE BUILD BECOMES TWO ENABLED MODS, AND THE ICON TABLES "
          "TRAVEL WITH THE INTERFACE HALF")
    return 0


if __name__ == "__main__":
    sys.exit(main())

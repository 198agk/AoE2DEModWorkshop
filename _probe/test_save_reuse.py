# -*- coding: utf-8 -*-
"""保存 twice = ONE folder; only 另存为 makes a second.

Reported 2026-11-09, verbatim: 「那我要继续接着改同一份呢，总不能我每改动一次，
就另存为一份吧」.

What the player was seeing: the folder is named from the mod's Title, and an
empty name box had the SERVER derive a Title from the batch's first edit -- so
each save after a different edit produced "单位SPRMN 生命值", then "单位SPRMN
攻击力", and `_mods_out/` grew one folder per save.  The emitter was never the
problem: `emit_data_mod(..., overwrite=True)` already replaces the folder
wholesale, and `install_mod(..., overwrite=True)` already replaces
`mods/local/<name>`.

The fix is that `save_session` remembers the Title it last wrote and reuses it
when the box is empty, which is what makes an empty box mean "same mod" instead
of "work out a new name".  Both halves are pinned here:

1. save twice with an empty box -> one folder, second save UPDATES it (and the
   first edit is still in the file, so the update did not drop it);
2. 另存为 (`keep=True, title=...`) -> a second folder;
3. install the same title twice -> one folder in `mods/local`, contents replaced.

Run: python -X utf8 _probe/test_save_reuse.py
Exit code 0 = all green.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("  (" + str(detail) + ")") if detail else ""))
    if not ok:
        BAD.append(name)


def mod_folders(root):
    """The mod folders a save produced, ignoring the copied runtime dlls."""
    return sorted(
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d))
        and not d.lower().startswith(("python", "runtime"))
    )


def main():
    # Never write into the checkout's `_mods_out/`: that is the folder the
    # packed build shows the player, and a test that appends to it is how the
    # package once grew to 1.7 GB.
    out = tempfile.mkdtemp(prefix="aoe2mod_savesame_")
    os.environ["AOE2MOD_BUILD_OUT"] = out

    from aoe2mod.ui.server import App
    from aoe2mod.dat import parser as P

    app = App()
    app.tk._ensure()
    print("dat:", os.path.basename(app.tk.dat_path))
    print("out:", out)
    check("nothing is there before the first save", mod_folders(out) == [],
          mod_folders(out))

    # --- 1. two saves, empty name box --------------------------------------
    r = app.set_unit_field(74, "HitPoints", 99, dry=False)
    check("first edit is accepted", r.get("ok"), r.get("error"))
    s1 = app.save_session()
    check("first save builds a folder", s1.get("ok"), s1.get("error"))
    first_dir = os.path.basename(s1.get("built") or "")
    check("and it is the only one", mod_folders(out) == [first_dir],
          mod_folders(out))
    check("session-info names it as the save target",
          app.session_info().get("target") == "单位「SPRMN」 生命值",
          app.session_info().get("target"))

    # A DIFFERENT edit: with the old naming this alone produced a second folder.
    r = app.set_unit_field(75, "HitPoints", 88, dry=False)
    check("second edit is accepted", r.get("ok"), r.get("error"))
    s2 = app.save_session()
    check("second save succeeds", s2.get("ok"), s2.get("error"))
    check("and writes the SAME folder",
          os.path.basename(s2.get("built") or "") == first_dir,
          os.path.basename(s2.get("built") or ""))
    check("still exactly one folder", len(mod_folders(out)) == 1,
          mod_folders(out))

    # Replacing a folder wholesale is only safe if the earlier edit survived:
    # the new bytes are built from the session buffer, and the buffer still
    # holds edit 1.  Read the produced file back rather than trusting it.
    dat = s2["built"] + os.sep + os.path.join(
        "resources", "_common", "dat", "empires2_x2_p1.dat")
    from aoe2mod import api as A
    tk2 = A.open_toolkit(dat_path=dat)
    tk2._ensure()
    hp = {}
    srv = __import__("aoe2mod.ui.server", fromlist=["App"]).App()
    srv._tk = tk2
    for u in (74, 75):
        f = srv.unit_fields(u)
        got = [x for x in f["fields"] if x["name"] == "HitPoints"]
        hp[u] = got[0]["value"] if got else None
    check("the updated folder still carries the first edit", hp[74] == 99, hp)
    check("and carries the second", hp[75] == 88, hp)

    # --- 2. 另存为 ---------------------------------------------------------
    r = app.set_unit_field(76, "HitPoints", 77, dry=False)
    s3 = app.save_session(title="另存的那一份", keep=True)
    check("另存为 succeeds", s3.get("ok"), s3.get("error"))
    check("另存为 makes a second folder", len(mod_folders(out)) == 2,
          mod_folders(out))
    check("and the pending list survives it", app.session_info().get("pending") == 1,
          app.session_info().get("pending"))

    # --- 3. 保存 also installs into mods/local ----------------------------
    # Asked 2026-11-09, verbatim: 「要不你都改成默认放入 local 里吧」.  The route
    # is what defaults to install=True; the method defaults to False so that a
    # probe calling it cannot write into the player's real mod list.  This block
    # proves the mechanism with a throwaway profile.
    prof = tempfile.mkdtemp(prefix="aoe2mod_profile_reuse_")
    os.makedirs(os.path.join(prof, "mods", "local"), exist_ok=True)
    with open(os.path.join(prof, "mods", "mod-status.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"Mods": [], "Unsub": []}, fh)
    os.environ["AOE2MOD_PROFILE"] = prof
    before = set(os.listdir(os.path.join(prof, "mods", "local")))
    r = app.set_unit_field(74, "HitPoints", 55, dry=False)
    s4 = app.save_session(install=True)
    check("保存 with install=True succeeds", s4.get("ok"), s4.get("error"))
    check("it answers with what it installed", bool(s4.get("installed")),
          list((s4.get("installed") or {}).keys())[:6])
    local = os.path.join(prof, "mods", "local")
    check("mods/local gained exactly one folder",
          len(set(os.listdir(local)) - before) == 1,
          sorted(os.listdir(local)))
    # The installed folder is named after the TITLE the save used, and after the
    # 另存为 above that title is 另存的那一份 -- not the auto-derived one.  Read
    # the name off the reply instead of guessing it: `_safe_dir` strips 「」 for
    # the build folder, so the two names legitimately differ.
    want = ((s4.get("installed") or {}).get("name")) or ""
    dat = os.path.join(local, want, "resources", "_common", "dat",
                       "empires2_x2_p1.dat")
    check("and it carries the saved .dat", bool(want) and os.path.isfile(dat),
          (want, dat))
    s5 = app.save_session(install=True)
    check("a second 保存 does not add a second install",
          len(set(os.listdir(local)) - before) == 1, sorted(os.listdir(local)))
    check("and reports no install error", not s5.get("install_error"),
          s5.get("install_error"))
    os.environ.pop("AOE2MOD_PROFILE", None)
    shutil.rmtree(prof, ignore_errors=True)

    # --- 4. 放弃 forgets the target ---------------------------------------
    app.reset_session()
    check("放弃 forgets which mod was being written",
          app.session_info().get("target") == "",
          app.session_info().get("target"))

    shutil.rmtree(out, ignore_errors=True)


def install_half():
    """`mods/local/<name>` is replaced, not appended to, for a repeated title."""
    from aoe2mod.game import locations as G

    prof = tempfile.mkdtemp(prefix="aoe2mod_profile_")
    os.makedirs(os.path.join(prof, "mods", "local"), exist_ok=True)

    def fake_mod(tag):
        d = tempfile.mkdtemp(prefix="aoe2mod_src_")
        root = os.path.join(d, "resources", "_common", "dat")
        os.makedirs(root)
        with open(os.path.join(root, "empires2_x2_p1.dat"), "wb") as f:
            f.write(b"VER 8.9\n" + tag.encode())
        with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as f:
            json.dump({"Author": "probe", "CacheStatus": -1,
                       "Description": tag, "Title": "同一个模组"}, f)
        return d

    a, b = fake_mod("first"), fake_mod("second")
    G.install_mod(a, prof, name="同一个模组", title="同一个模组", overwrite=True)
    G.install_mod(b, prof, name="同一个模组", title="同一个模组", overwrite=True)
    local = os.path.join(prof, "mods", "local")
    dirs = os.listdir(local)
    dat = os.path.join(local, "同一个模组", "resources", "_common", "dat",
                       "empires2_x2_p1.dat")
    body = open(dat, "rb").read() if os.path.isfile(dat) else b""
    check("installing the same title twice keeps ONE folder", len(dirs) == 1, dirs)
    check("and the second install replaced its contents", body.endswith(b"second"),
          body.split(b"\n")[-1:])
    shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
    install_half()
    print()
    if BAD:
        for name in BAD:
            print("FAILED:", name)
        sys.exit(1)
    print("SAVE REUSE: 保存 UPDATES THE MOD IT LAST WROTE AND INSTALLS IT; ONLY 另存为 MAKES A SECOND")

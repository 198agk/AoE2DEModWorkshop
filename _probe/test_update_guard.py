# -*- coding: utf-8 -*-
"""Does the update guard tell the truth in each of the five situations?

The failure this must prevent is quiet and expensive: a mod ships a whole 12 MB
`.dat`, the game patches its own, and the installed mod keeps handing the engine
the old one.  Nothing anywhere says so.  The guard exists to say so -- but a guard
that cries wolf costs a user a pointless 20-second rebuild, and after the second
false alarm they stop reading it.  So each status has to be reachable and provable:

  current  built from the data the game has now
  stale    the game's data changed under this mod
  edited   the mod's own .dat is not what we emitted
  unknown  no record (not ours, or the record was deleted)
  no_dat   the mod ships no .dat, so a patch cannot stale it

Plus the two "must not" cases measured in the same run:

  * a re-compressed but byte-identical raw stream is CURRENT, not stale
    (the file hash differs, so only the deep comparison can answer this);
  * an unknown row is NOT counted as needing attention -- a banner nobody can act
    on teaches people to ignore the ones they can.

Everything here runs against a throwaway state file and a throwaway profile, via
`AOE2MOD_STATE_DIR`.  The player's real records are never touched.
"""
import io
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zlib
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
except Exception:
    pass

from aoe2mod import api as A                              # noqa: E402
from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.mod import provenance as PV                   # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("OK   %s" % name)
    else:
        print("FAIL %s%s" % (name, ("  :: %s" % detail) if detail else ""))
        FAILED.append(name)


def write_dat(path, raw, level=6):
    """Write a .dat the way the game does: raw deflate, window_bits=-15."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = zlib.compressobj(level, zlib.DEFLATED, -15)
    with open(path, "wb") as fh:
        fh.write(c.compress(raw))
        fh.write(c.flush())


def main():
    tmp = tempfile.mkdtemp(prefix="aoe2mod guard ")
    state = os.path.join(tmp, "state")
    os.environ[PV.STATE_DIR_ENV] = state
    state_file = os.path.join(state, PV.STATE_FILE)

    tk = A.open_toolkit()
    tk._ensure()                     # the raw stream is what the record hashes
    game_dat = tk.dat_path
    raw = tk._raw
    base_file_sha = PV.file_sha256(game_dat)
    base_raw_sha = hashlib.sha256(raw).hexdigest()

    # ---- the record a build leaves behind ------------------------------
    print("--- what a build records ---")
    man = {"info": {"Title": "guard probe", "Author": "dsh", "Description": ""},
           "mod_dir": os.path.join(tmp, "emitted"),
           "dat": None, "dat_sha256": base_raw_sha, "changes_dat": True,
           "dat_is_carrier": False, "edit_count": 3, "resolved": "probe"}
    os.makedirs(man["mod_dir"])
    # the emitted .dat is a REAL deflate stream, since the check hashes it
    man["dat"] = os.path.join(man["mod_dir"], "resources", "_common", "dat",
                              "empires2_x2_p1.dat")
    write_dat(man["dat"], raw)
    entry = PV.entry_from_manifest(man, game_dat, base_raw_sha256=base_raw_sha,
                                   intents=[{"intent": "unit.stat", "unit": 83,
                                             "stat": "hit_points", "value": 1000}],
                                   target_version=tk.version)
    check("the record knows the game file it was built from",
          entry["base_file_sha256"] == base_file_sha)
    check("the record knows the raw stream it was built from",
          entry["base_raw_sha256"] == base_raw_sha)
    check("the record knows the version string", entry["base_version"] == "VER 8.9",
          entry["base_version"])
    check("the record keeps the intents, so a rebuild needs no retyping",
          entry["intents"] and entry["intents"][0]["unit"] == 83)
    check("the record knows its own emitted file",
          entry["dat_file_sha256"] == PV.file_sha256(man["dat"]))
    PV.record(entry, path=state_file)
    check("the state file is where the module says",
          os.path.isfile(state_file) and PV.state_path() == state_file)
    check("the state file is valid json and holds the build",
          entry["title"] in (PV.load(state_file).get("builds") or {}))

    # ---- 1. current ----------------------------------------------------
    print()
    print("--- current: nothing moved ---")
    got = PV.check(profile_root=_fake_profile(tmp, install=man["dat"]),
                   game_dat=game_dat, path=state_file)
    row = [r for r in got["rows"] if r["name"] == "guard probe"]
    check("our mod is listed", len(row) == 1, got["rows"])
    check("it reads as current", row and row[0]["status"] == PV.CURRENT,
          row and row[0])
    check("nothing asks for attention", got["needs_attention"] == 0,
          got["needs_attention"])

    # ---- 2. stale: the game shipped new data ---------------------------
    print()
    print("--- stale: the game's data changed ---")
    other = bytearray(raw)
    other[-1] = (other[-1] + 1) % 256          # one byte, same size
    game2 = os.path.join(tmp, "game2", "resources", "_common", "dat",
                         "empires2_x2_p1.dat")
    write_dat(game2, bytes(other))
    got2 = PV.check(profile_root=_fake_profile(tmp, install=man["dat"]),
                    game_dat=game2, path=state_file)
    row2 = [r for r in got2["rows"] if r["name"] == "guard probe"][0]
    check("it reads as stale", row2["status"] == PV.STALE, row2["status"])
    check("stale is what the banner counts", got2["needs_attention"] == 1,
          got2["needs_attention"])
    check("the reason names the version it was built on",
          "VER 8.9" in (row2["detail"] or ""), row2["detail"])
    check("a stale row is fixable", row2["fixable"] is True)

    # ---- 3. same content, re-compressed --------------------------------
    print()
    print("--- re-compressed, same content: NOT stale ---")
    game3 = os.path.join(tmp, "game3", "resources", "_common", "dat",
                         "empires2_x2_p1.dat")
    write_dat(game3, raw, level=9)
    check("the file really is different",
          PV.file_sha256(game3) != base_file_sha)
    got3 = PV.check(profile_root=_fake_profile(tmp, install=man["dat"]),
                    game_dat=game3, path=state_file)
    row3 = [r for r in got3["rows"] if r["name"] == "guard probe"][0]
    check("it reads as current, not stale", row3["status"] == PV.CURRENT,
          row3["status"])
    check("and it says why", "重新打包" in (row3["detail"] or ""), row3["detail"])
    check("no attention asked for", got3["needs_attention"] == 0)

    # ---- 4. edited: the installed file is not ours ---------------------
    print()
    print("--- edited: the installed .dat is not the one we emitted ---")
    med = os.path.join(tmp, "med", "resources", "_common", "dat",
                       "empires2_x2_p1.dat")
    write_dat(med, bytes(other))
    got4 = PV.check(profile_root=_fake_profile(tmp, install=med),
                    game_dat=game_dat, path=state_file)
    row4 = [r for r in got4["rows"] if r["name"] == "guard probe"][0]
    check("it reads as edited", row4["status"] == PV.EDITED, row4["status"])
    check("an edited mod says so instead of blaming the game",
          "覆盖" in (row4["detail"] or ""), row4["detail"])

    # ---- 5. unknown: a mod we have no record for -----------------------
    print()
    print("--- unknown: a mod the guard has never heard of ---")
    prof5 = _fake_profile(tmp, install=None, extra="someone else's mod")
    got5 = PV.check(profile_root=prof5, game_dat=game_dat, path=state_file)
    names5 = [r["name"] for r in got5["rows"]]
    check("the stranger is listed", "someone else's mod" in names5, names5)
    stranger = [r for r in got5["rows"] if r["name"] == "someone else's mod"][0]
    check("it reads as unknown", stranger["status"] == PV.UNKNOWN,
          stranger["status"])
    check("unknown is NOT counted as attention", got5["needs_attention"] == 0,
          got5["needs_attention"])
    check("unknown is not offered as fixable", stranger["fixable"] is False)

    # ---- 6. no_dat: a graphics-only mod --------------------------------
    print()
    print("--- no_dat: a mod that ships no .dat ---")
    man6 = dict(man)
    man6["info"] = {"Title": "textures only", "Author": "dsh"}
    man6["dat"] = None
    man6["changes_dat"] = False
    man6["dat_is_carrier"] = False
    e6 = PV.entry_from_manifest(man6, game_dat, base_raw_sha256=base_raw_sha,
                                intents=[{"intent": "unit.sprite", "unit": 4,
                                          "donor": 8}])
    PV.record(e6, path=state_file)
    prof6 = _fake_profile(tmp, install=None, extra="textures only")
    got6 = PV.check(profile_root=prof6, game_dat=game2, path=state_file)
    row6 = [r for r in got6["rows"] if r["name"] == "textures only"][0]
    check("a graphics-only mod reads as no_dat", row6["status"] == PV.NO_DAT,
          row6["status"])
    check("no_dat is not attention", got6["needs_attention"] == 0)

    # ---- 7. a broken state file must not take the screen down ----------
    print()
    print("--- a corrupt record file is not a crash ---")
    with open(state_file, "wb") as fh:
        fh.write(b"{\"builds\": {oops")
    got7 = PV.check(profile_root=prof6, game_dat=game_dat, path=state_file)
    check("a corrupt record reads as empty, not as an exception",
          got7["ok"] is True and isinstance(got7["rows"], list))
    check("everything becomes unknown, which is what 'no record' means",
          all(r["status"] == PV.UNKNOWN for r in got7["rows"]),
          [r["status"] for r in got7["rows"]])

    # ---- 8. the wiring: a real build leaves a real record ---------------
    # Everything above exercises `provenance` directly.  None of it would notice
    # if `Toolkit.build` stopped calling `_remember` -- and then every mod this
    # tool ships would read as "unknown", which is the guard quietly switching
    # itself off.  So build one real mod through the public API and follow it all
    # the way to a status.
    print()
    print("--- a real build, through the public API ---")
    from aoe2mod.game import locations as L
    out = os.path.join(tmp, "emitted")
    state2 = os.path.join(tmp, "state2", PV.STATE_FILE)
    os.environ[PV.STATE_DIR_ENV] = os.path.dirname(state2)
    built = tk.build({"intent": "unit.stat", "unit": 83, "stat": "hit_points",
                      "value": 1000}, out, title="wired probe", author="dsh",
                     overwrite=True)
    recorded = (PV.load(state2).get("builds") or {}).get("wired probe")
    check("building through the public API writes a record",
          recorded is not None, list((PV.load(state2).get("builds") or {})))
    check("the record carries the intents, so a rebuild needs no retyping",
          bool(recorded) and recorded.get("intents")
          and recorded["intents"][0].get("value") == 1000,
          str(recorded and recorded.get("intents"))[:160])
    check("the build's own manifest points at the record",
          bool((built.get("provenance") or {}).get("title")), str(
              built.get("provenance")))
    prof9 = _fake_profile(tmp)
    tk.install(built["mod_dir"], name="wired probe", title="wired probe",
               enabled=True, overwrite=True, profile_root=prof9)
    wired = [r for r in PV.check(profile_root=prof9, game_dat=game_dat,
                                 path=state2)["rows"] if r["name"] == "wired probe"]
    check("a real installed build reads as current, not unknown",
          len(wired) == 1 and wired[0]["status"] == PV.CURRENT,
          wired and wired[0])
    check("installing into a profile is itself remembered",
          bool(recorded and (PV.load(state2).get("builds") or {})
               .get("wired probe", {}).get("installed_dat_file_sha256")),
          "an install that is not remembered cannot tell a patch from a replacement")
    later = [r for r in PV.check(profile_root=prof9, game_dat=game2,
                                 path=state2)["rows"] if r["name"] == "wired probe"]
    check("and the same real mod goes stale when the game's data moves",
          later and later[0]["status"] == PV.STALE, later and later[0]["status"])

    # ---- 9. the cheap path really is cheap -----------------------------
    print()
    print("--- the guard is cheap enough to run on every screen load ---")
    PV.record(e6, path=state_file)
    t = time.time()
    PV.check(profile_root=prof6, game_dat=game_dat, path=state_file)
    dt = time.time() - t
    check("a full check takes well under a second", dt < 0.6, "%.3f s" % dt)
    check("the version comes from the head, not a 4.5 s parse",
          PV.head_version(game_dat) == "VER 8.9")

    shutil.rmtree(tmp, ignore_errors=True)
    del os.environ[PV.STATE_DIR_ENV]

    print()
    if FAILED:
        print("UPDATE GUARD: %d CHECK(S) FAILED -> %s"
              % (len(FAILED), json.dumps(FAILED, ensure_ascii=False)))
        return 1
    print("UPDATE GUARD: EVERY STATUS IS REACHABLE AND NAMED -- NO FALSE ALARMS")
    return 0


def _fake_profile(root, install=None, extra=None):
    """A throwaway profile with one local mod (optionally carrying a .dat)."""
    prof = os.path.join(root, "profile")
    acc = os.path.join(prof, "12345678901234567")
    local = os.path.join(acc, "mods", "local")
    os.makedirs(local, exist_ok=True)
    mods = []
    if install:
        d = os.path.join(local, "guard probe")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
            json.dump({"Title": "guard probe", "Author": "dsh",
                       "Description": "", "CacheStatus": 0}, fh)
        target = os.path.join(d, "resources", "_common", "dat",
                              "empires2_x2_p1.dat")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(install, target)
        mods.append({"Name": "guard probe", "Title": "guard probe"})
    if extra:
        d = os.path.join(local, extra)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
            json.dump({"Title": extra, "Author": "x", "Description": "",
                       "CacheStatus": 0}, fh)
        mods.append({"Name": extra, "Title": extra})
    # The status document is what makes a mod visible to the game AND to
    # `list_mods`; a folder alone is not enough.  `Path` is "kind//name"
    # relative to the mods root (forward slashes, measured on the live file) --
    # writing a filesystem path there makes list_mods report an empty name.
    doc = {"Mods": [{"Name": m["Name"], "Title": m["Title"], "Enabled": True,
                     "Priority": i + 1, "Kind": "local",
                     "Path": "local//%s" % m["Name"]}
                    for i, m in enumerate(mods)]}
    with open(os.path.join(acc, "mods", "mod-status.json"), "w",
              encoding="utf-8") as fh:
        json.dump(doc, fh)
    return prof


if __name__ == "__main__":
    sys.exit(main())

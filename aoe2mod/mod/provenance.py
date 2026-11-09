# -*- coding: utf-8 -*-
"""Remember which game data a built mod came from, so an official update is visible.

WHY THIS EXISTS

Every data mod this project emits carries a WHOLE `.dat` (about 12 MB compressed,
93 MB inflated).  That is not a detail -- it is how a data mod works.  It also
means the mod is a snapshot: when the game patches its own `.dat`, the installed
mod keeps handing the engine the OLD one, so the patch's data changes silently
disappear (or the game refuses to start if the format moved).  The only correct
action after a patch is rebuild + reinstall, and until this module existed nothing
in the product knew a patch had happened.

The same is true of the "carrier" case: a JSON-layer mod (per-civ availability)
ships `empires2_x2_p1.dat` UNMODIFIED because the game will not start when a mod
overrides the DAT storage point without it.  Such a mod changes no byte, yet after
a patch it pins the old 93 MB stream in place.  Carriers are the QUIETEST way to
lose a patch, so they are tracked like any other build.

WHERE THE RECORD LIVES

The user chose (2026-10-20) a LOCAL state file over a file inside the mod folder,
because 13 of 13 third-party mods on this machine have exactly
`info.json` + `thumbnail.*` at the root and nothing else -- adding a file of our
own would be a shape no published mod has ever had, and there is no evidence the
publisher's validation accepts it.  The cost of that choice is honest and is
reported to the user: the record does not travel with the mod, so on another
machine (or after deleting the state file) this module can only say "unknown",
never a guess.

The state file is `builds.json` under `%LOCALAPPDATA%\\aoe2de-mod-workshop\\`
(override with ``AOE2MOD_STATE_DIR``, which the tests use so they never touch the
player's real records -- the same lesson `test_install.py` taught twice).

WHAT IS COMPARED, AND WHY IN THIS ORDER

A cheap check must not answer a different question than the expensive one.  So:

  * the routine check hashes the COMPRESSED `.dat` file (~0.009 s) and compares it
    against the fingerprint taken at build time;
  * only when that differs does it inflate the stream (~0.12 s) and compare the
    RAW sha256, because a re-shipped file might be the same content re-compressed
    (a false "your mod is stale" costs the user a pointless rebuild, and a guard
    that cries wolf gets ignored);
  * the version string (``VER 8.9``) is read by streaming the FIRST few dozen
    bytes of the raw stream (~0.000 s) -- a full parse costs 4.5 s, which is far
    too slow to run when a screen loads.

Measured on this machine, 2026-10-20, in `_probe/probe_update_guard.py` and
`_probe/probe_update_head.py`:
    sha256 of the compressed file            0.009 s
    load_dat (inflate to the raw stream)     0.118 s
    sha256 of the raw stream                 0.036 s
    Parser().parse() (for the version enum)  4.564 s
    streaming 64 bytes of the raw stream     0.0000 s
"""
import hashlib
import io
import json
import os
import time
import zlib

STATE_VERSION = 1
STATE_DIR_ENV = "AOE2MOD_STATE_DIR"
#: The native engine's spelling of the same override
#: (`desktop/aoe2mod-serve/src/recipes.rs:40 fn state_dir`).  Both are honoured
#: because the shipped exe now runs THIS engine, and every suite written against
#: the native one sets this name -- measured 2026-10-31,
#: `_probe/test_e2e_shipped.py:74` isolated its build records with
#: `AOE2MOD_STATE` and this side wrote into the player's real `builds.json`
#: anyway, so its own update-check could not find the mods it had just built.
STATE_DIR_ENV_NATIVE = "AOE2MOD_STATE"
STATE_FILE = "builds.json"

# Status values a caller may print.  Kept as words rather than booleans so the
# screen can say what it knows instead of colouring a dot.
CURRENT = "current"        # built from the data the game has now
STALE = "stale"            # the game's data changed after this mod was built
EDITED = "edited"          # the mod's own .dat no longer matches what we emitted
UNKNOWN = "unknown"        # no record: not ours, or the state file was deleted
NO_DAT = "no_dat"          # the mod ships no .dat, so a patch cannot stale it


def state_dir():
    """Where build records live.

    ``AOE2MOD_STATE_DIR`` overrides for tests, and the native engine's own name
    ``AOE2MOD_STATE`` is accepted as the same thing: both are sandbox
    declarations, and a deployment that sets only the native name must not end
    up writing into the player's real records.
    """
    override = (os.environ.get(STATE_DIR_ENV)
                or os.environ.get(STATE_DIR_ENV_NATIVE))
    if override:
        return os.path.abspath(override)
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "aoe2de-mod-workshop")


def state_path():
    return os.path.join(state_dir(), STATE_FILE)


def load(path=None):
    """Read the record file; a missing or corrupt file reads as empty.

    A corrupt record must not take the screen down: the worst it can cost is that
    an installed mod becomes "unknown", which is exactly what the absence of a
    record already means.
    """
    path = path or state_path()
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8-sig"))
    except (IOError, OSError, ValueError):
        return {"version": STATE_VERSION, "builds": {}}
    if not isinstance(doc, dict):
        return {"version": STATE_VERSION, "builds": {}}
    doc.setdefault("version", STATE_VERSION)
    if not isinstance(doc.get("builds"), dict):
        doc["builds"] = {}
    return doc


def save(doc, path=None):
    """Write atomically -- a half-written record file is worse than none."""
    path = path or state_path()
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def record(entry, path=None):
    """Store one build record, keyed by its Title (the name the game indexes by)."""
    doc = load(path)
    doc["builds"][entry["title"]] = entry
    save(doc, path)
    return entry


def forget(title, path=None):
    doc = load(path)
    if title in doc["builds"]:
        del doc["builds"][title]
        save(doc, path)
        return True
    return False


# ---------------------------------------------------------------------------
# fingerprints
# ---------------------------------------------------------------------------

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def head_version(path):
    """The ``VER x.y`` string, by inflating only the first few bytes.

    This is the cheap half of a version check and it must agree with the full
    parse -- `_probe/probe_update_head.py` confirmed it does on 8 `.dat` files,
    including one that is still `VER 7.8` (a third-party mod built on an older
    game).  A cheaper check that answers a different question would be worse than
    no check at all.
    """
    d = zlib.decompressobj(-15)
    out = b""
    try:
        with open(path, "rb") as fh:
            while len(out) < 64:
                chunk = fh.read(1 << 14)
                if not chunk:
                    break
                out += d.decompress(chunk, 64 - len(out))
                if d.eof:
                    break
    except (IOError, OSError, zlib.error):
        return None
    return out.split(b"\x00")[0].decode("ascii", "replace") if out else None


def fingerprint(path, deep=False):
    """Cheap by default: one hash of the compressed file plus the version head.

    ``deep=True`` also inflates and hashes the raw stream, which is what the
    build side stores and what a "different file, same content" case is settled
    with.
    """
    out = {"file_sha256": file_sha256(path), "version": head_version(path)}
    if deep:
        from ..dat import parser as P
        raw, how = P.load_dat(path)
        out["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        out["raw_bytes"] = len(raw)
        out["stored_as"] = how
    return out


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def entry_from_manifest(man, game_dat, base_raw_sha256=None, title=None,
                        intents=None, target_version=None):
    """Turn a build manifest into the record this module stores.

    ``base_raw_sha256`` is the sha256 of the game's raw stream at build time.  A
    caller that already parsed the `.dat` has it in memory, so it costs nothing
    there -- and it is what lets a later check tell "the game re-compressed the
    same content" from "the game shipped new content".  Without it the check falls
    back to the file hash only, which is still correct, just noisier after a patch
    that only changes packaging.

    ``intents`` is stored so that a stale mod can be REBUILT without the user
    retyping the sentence.  That is the whole point of the one-click path: a
    guard that only says "this is stale" leaves the user to remember what they
    asked for three weeks ago.
    """
    info = man.get("info") or {}
    dat_file = man.get("dat")
    out = {
        "title": title or info.get("Title") or os.path.basename(
            man.get("mod_dir") or ""),
        "built_at": now_iso(),
        "target_version": target_version,
        "changes_dat": bool(man.get("changes_dat")),
        "dat_is_carrier": bool(man.get("dat_is_carrier")),
        "dat_raw_sha256": man.get("dat_sha256"),
        "base_file_sha256": None,
        "base_raw_sha256": base_raw_sha256,
        "base_version": None,
        "dat_file_sha256": None,
        "dat_file_bytes": None,
        "edit_count": man.get("edit_count"),
        "resolved": man.get("resolved"),
        "author": info.get("Author") or "",
        "description": info.get("Description") or "",
        "intents": json.loads(json.dumps(intents)) if intents else None,
    }
    if os.path.isfile(game_dat):
        out["base_file_sha256"] = file_sha256(game_dat)
        out["base_version"] = head_version(game_dat)
    if dat_file and os.path.isfile(dat_file):
        out["dat_file_sha256"] = file_sha256(dat_file)
        out["dat_file_bytes"] = os.path.getsize(dat_file)
    return out


def note_installed(man, path=None):
    """Attach "what actually landed in the profile" to an existing record.

    The build record knows the game data it was made from; only the install step
    knows the bytes the game will read.  Keeping the two apart is what lets
    ``check()`` tell "the game was patched" from "something replaced MY mod".
    """
    doc = load(path)
    builds = doc.get("builds") or {}
    key = man.get("name") or man.get("title")
    entry = builds.get(key) or builds.get(man.get("title"))
    if entry is None:
        return None
    dat = man.get("dat")
    if dat and os.path.isfile(dat):
        entry["installed_dat_file_sha256"] = file_sha256(dat)
        entry["installed_at"] = now_iso()
        entry["installed_name"] = key
        entry["installed_kind"] = man.get("kind")
        save(doc, path)
    return entry


# ---------------------------------------------------------------------------
# the check itself
# ---------------------------------------------------------------------------

def _installed_dat(mod):
    from ..game import locations as L
    path = os.path.join(mod.get("path") or "", L.DAT_REL)
    return path if os.path.isfile(path) else None


def check(profile_root=None, game_dat=None, path=None, deep_when_needed=True):
    """Compare every installed mod we built against the game's data right now.

    Returns::

        {"ok": True,
         "state_dir": "...",
         "dat": {"path":..., "file_sha256":..., "version":...},
         "rows": [{"name":..., "title":..., "kind":..., "enabled":...,
                   "status": "current"|"stale"|"edited"|"unknown"|"no_dat",
                   "detail": "...", "fixable": bool,
                   "built_at":..., "built_version":...}],
         "needs_attention": N}

    ``needs_attention`` counts the rows a user has to act on -- that is what the
    screen shows a banner for.  An unknown row is NOT attention: it is honestly
    unknowable, and shouting about it would train the user to ignore the banner.
    """
    from ..game import locations as L
    prof = profile_root or L.find_profile_root()
    dat = game_dat or L.dat_path(L.find_game_root())
    current = fingerprint(dat)
    doc = load(path)
    builds = doc.get("builds") or {}

    rows = []
    for mod in L.list_mods(prof):
        name = mod.get("name") or ""
        title = mod.get("title") or name
        entry = builds.get(name) or builds.get(title) or None
        row = {"name": name, "title": title, "kind": mod.get("kind"),
               "enabled": bool(mod.get("enabled")), "status": UNKNOWN,
               "detail": "", "fixable": False, "built_at": None,
               "built_version": None, "installed_dat": None}
        installed = _installed_dat(mod)
        row["installed_dat"] = installed

        if entry is None:
            row["detail"] = ("没有任何构建记录：这份模组不是本工具建的，"
                             "或者记录文件被删了")
            rows.append(row)
            continue

        row["built_at"] = entry.get("built_at")
        row["built_version"] = entry.get("base_version")
        row["fixable"] = True

        ships_dat = bool(entry.get("changes_dat")) or bool(entry.get("dat_is_carrier"))
        if not ships_dat or installed is None:
            row["status"] = NO_DAT
            row["detail"] = ("这份模组不带 .dat（只发贴图/科技树 JSON 之外的松散文件），"
                             "官方更新不会让它失效")
            row["fixable"] = False
            rows.append(row)
            continue

        # Did the mod's own copy change since we emitted it?
        try:
            have = file_sha256(installed)
        except (IOError, OSError):
            have = None
        want_file = entry.get("dat_file_sha256")
        if want_file and have and have != want_file:
            row["status"] = EDITED
            row["detail"] = ("装着的这份 .dat 和本工具发出去的不是同一个文件"
                             "（可能被别的模组或手工覆盖过）；重建会覆盖它")
            rows.append(row)
            continue

        if current["file_sha256"] == entry.get("base_file_sha256"):
            row["status"] = CURRENT
            row["detail"] = "按游戏现在这份数据建的"
            rows.append(row)
            continue

        # The file changed.  Is it the same content re-compressed, or new data?
        same_content = False
        if deep_when_needed:
            now = fingerprint(dat, deep=True)
            same_content = (now.get("raw_sha256") == entry.get("base_raw_sha256"))
        if same_content:
            row["status"] = CURRENT
            row["detail"] = "游戏重新打包过 .dat，内容没变，不用重建"
            rows.append(row)
            continue

        row["status"] = STALE
        now_s = current.get("version") or "?"
        then_s = entry.get("base_version") or "?"
        if now_s != then_s:
            row["detail"] = ("游戏数据从 %s 更新到了 %s；这份模组带着旧的一整份 .dat，"
                             "会把更新盖掉" % (then_s, now_s))
        else:
            row["detail"] = ("游戏数据更新过（版本号还是 %s，但内容变了）；"
                             "这份模组带着旧的一整份 .dat，会把更新盖掉" % now_s)
        rows.append(row)

    return {
        "ok": True,
        "state_dir": os.path.dirname(path or state_path()),
        "dat": {"path": dat, "file_sha256": current["file_sha256"],
                "version": current["version"]},
        "rows": rows,
        "needs_attention": sum(1 for r in rows if r["status"] == STALE),
    }

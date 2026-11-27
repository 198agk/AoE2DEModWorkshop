# -*- coding: utf-8 -*-
"""Where is the game, and where do its mods live?

Nothing here parses game data; it only answers "which folder".  The rules come
from inspecting this machine and from the engine's own strings:

* The mods root lives under the USER profile, not the game install, and is
  per-Steam-account: ``<profile>/<steamid64>/mods``.
* A mod is a folder that contains an ``info.json``.  Its name is
  ``<WorkshopID>_<Title>`` for subscribed mods and ``<name>`` for local ones.
* Load ORDER is not directory order: it comes from ``mod-status.json``, whose
  entries carry a ``Priority``.  Any tool that shows mods must read that file,
  and must tolerate a ``Path`` that no longer exists (users rename folders).
"""
import json
import os
import time

from .. import appversion as AV

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

#: Override for the profile root; see :func:`find_profile_root`.  Points at ONE
#: account folder (the one holding ``mods/``), and is how every suite keeps its
#: writes out of the player's real mod list.
PROFILE_ENV = "AOE2MOD_PROFILE"

#: Override for the game install; see :func:`find_game_root`.  The native
#: engine has always honoured it (``desktop/aoe2mod-serve/src/lib.rs:167``), and
#: this side ignored it -- which turned a sandbox into a silent lie: measured
#: 2026-10-31, `_probe/probe_startup_failure.py` pointed it at an empty folder to
#: prove the splash explains a missing ``.dat``, and the shipped exe -- by then
#: running THIS engine -- found the real game instead and started normally, so
#: the failure path was never exercised at all.
GAME_ENV = "AOE2MOD_GAME_ROOT"

# Steam's own app id for Age of Empires II: Definitive Edition.  The manifest
# named ``appmanifest_<APP_ID>.acf`` is the only authoritative answer to "where
# did this user install it", so it is the first thing we look for.
APP_ID = "813780"

# Candidate game roots, most specific first.  A Steam library can be anywhere,
# so the app id manifest is the reliable marker, not a guessed path.
#
# BOTH markers are required, and the executable is the one that matters for
# `game_root_of_dat`.  A marker list containing only the .dat is CIRCULAR: the
# function derives a candidate root FROM a .dat path and then proves it by
# looking for that same .dat, so any directory shaped like an install -- a test
# fixture, a mod's staging folder -- passes trivially.  The executable is the
# marker a bare copy of the data file cannot fake.
_GAME_MARKERS = (
    os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat"),
    "AoE2DE_s.exe",
)

# Storage points whose contents a RUNNING game will not re-resolve.  Everything
# else -- the `.dat`, the dat-adjacent JSON, strings, AI, scenarios, sounds -- is
# picked up while the game is running.
#
# This list exists because the product used to tell every user to quit and
# relaunch, and that was wrong.  The user reported in game (2026-10-16) that a
# data mod dropped into the mods folder IS read by the running game, with
# graphics being the exception.  The measurement agreed and I had misread it:
# ``_probe/test_mod_load_timing.py`` finds the engine enabling these mods in a
# later mod-manager pass (log line 860-996, long after "Opening resource
# packages" at 254-267).  Enabling a mod mid-session is not the same as ignoring
# it, which is what the old note claimed.
_GRAPHICS_POINTS = (
    os.path.join("resources", "_common", "drs"),       # .sld sprites, sounds
    os.path.join("resources", "_common", "wpfg"),      # menu XAML + PNG
    os.path.join("resources", "_common", "palettes"),
    os.path.join("widgetui", "textures"),
)
# A bare texture anywhere is enough, even outside the points above: the running
# session has already bound the atlas or image those bytes came from.
_GRAPHICS_EXTS = (".sld", ".dds", ".png", ".jpg", ".jpeg", ".pal", ".palx",
                  ".xaml", ".ttf")


def storage_points_touched(mod_dir):
    """Which storage points a built mod writes into, by path prefix.

    Cheap and deliberately conservative: a path counts as graphics when it lives
    under one of `_GRAPHICS_POINTS` or ends in `_GRAPHICS_EXTS`.  Nothing here
    decides whether the mod WORKS -- only whether a running game is expected to
    notice it without a relaunch.
    """
    points = set()
    for dirpath, _dirs, files in os.walk(mod_dir):
        rel_dir = os.path.relpath(dirpath, mod_dir)
        if rel_dir == ".":
            rel_dir = ""
        for fn in files:
            if fn in ("info.json", "thumbnail.png", "thumbnail.jpg"):
                continue
            rel = os.path.join(rel_dir, fn) if rel_dir else fn
            low = rel.lower().replace("/", os.sep)
            for p in _GRAPHICS_POINTS:
                if low.startswith(p.lower() + os.sep) or low == p.lower():
                    points.add(p)
            if low.endswith(_GRAPHICS_EXTS):
                points.add("textures")
    return sorted(points)


def looks_like_game_root(path):
    return all(os.path.exists(os.path.join(path, m)) for m in _GAME_MARKERS)


def find_game_root(explicit=None, search=()):
    """Return a game root, or raise with the paths that were tried.

    Discovery is done in order of reliability, never by guessing:

      1. ``appmanifest_813780.acf`` -- the engine's own app id for AoE2 DE.
         Its ``installdir`` names the folder inside ``<library>/steamapps/
         common``, so a library that moved is still found.
      2. ``<library>/steamapps/common/AoE2DE`` for every library Steam knows
         about, per ``libraryfolders.vdf``.
      3. A blind sweep of the usual Steam layouts, last resort only.

    Steps 1-2 are genuine discovery; step 3 CANNOT be complete, and this
    machine proves it: the game sits one ``Games`` folder deeper than any
    drive-relative layout a fixed list would guess.  Measured here: with steps
    1-2 disabled the sweep raises FileNotFoundError even though the game is
    installed.  That is why the registry and the manifest are consulted first.
    """
    tried = []
    for cand in (explicit,) + tuple(search):
        if not cand:
            continue
        tried.append(cand)
        if looks_like_game_root(cand):
            return cand

    # A declared game root wins over discovery, and a declared one that does not
    # look like an install is an ERROR rather than a fall-through -- same rule as
    # `find_profile_root` and for the same measured reason: a sandbox that
    # silently resolves somewhere else is worse than no sandbox.
    override = os.environ.get(GAME_ENV)
    if override is not None:
        tried.append(override)
        if override and looks_like_game_root(override):
            return override
        raise FileNotFoundError(
            "找不到游戏目录：%s=%s 不是一个能用的游戏安装目录。"
            "它要指到装着 %s 的那一层。因为已经指定了游戏目录，"
            "就不再退回别的安装。" % (GAME_ENV, override or "(空)",
                                    _GAME_MARKERS[1]))

    # 1 + 2: every library Steam admits to, via the manifest then by name.
    for lib in steam_libraries():
        man = os.path.join(lib, "steamapps", "appmanifest_%s.acf" % APP_ID)
        installdir = _read_acf_value(man, "installdir")
        if installdir:
            cand = os.path.join(lib, "steamapps", "common", installdir)
            tried.append(cand)
            if looks_like_game_root(cand):
                return cand
        cand = os.path.join(lib, "steamapps", "common", "AoE2DE")
        tried.append(cand)
        if looks_like_game_root(cand):
            return cand

    # 3: blind sweep, only for machines with no readable Steam metadata.
    seen = {os.path.normcase(os.path.normpath(t)) for t in tried}
    for drive in ("C:", "D:", "E:", "F:", "G:", "H:"):
        for lib in ("steamapps",
                    os.path.join("Steam", "steamapps"),
                    os.path.join("SteamLibrary", "steamapps"),
                    os.path.join("Program Files (x86)", "Steam", "steamapps"),
                    os.path.join("Program Files", "Steam", "steamapps")):
            cand = os.path.join(drive + os.sep, lib, "common", "AoE2DE")
            key = os.path.normcase(os.path.normpath(cand))
            if key in seen:
                continue
            seen.add(key)
            tried.append(cand)
            if looks_like_game_root(cand):
                return cand
    raise FileNotFoundError(
        "找不到《帝国时代 2 决定版》的安装目录。找过这些地方：\n  "
        + "\n  ".join(tried)
        + "\n如果装在别的地方，启动时加 --game-root <路径> 指给它。")


def steam_root():
    """The Steam install folder, from the registry.  None if unreadable."""
    try:
        import winreg
    except ImportError:
        return None
    for hive, key, value in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
        try:
            with winreg.OpenKey(hive, key) as k:
                p = winreg.QueryValueEx(k, value)[0]
        except OSError:
            continue
        if p and os.path.isdir(p):
            # The registry stores forward slashes on this machine.
            return os.path.normpath(p)
    return None


def _vdf_paths(text):
    """Every ``"path"`` value in a libraryfolders.vdf, unescaped."""
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s.lower().startswith('"path"'):
            continue
        val = s.partition("path")[2].strip()
        parts = [p for p in val.split('"') if p.strip()]
        if not parts:
            continue
        p = parts[-1].replace("\\\\", "\\")
        if p and os.path.isdir(p):
            out.append(os.path.normpath(p))
    return out


def steam_libraries():
    """Every Steam library folder, deduped, most likely first.

    ``libraryfolders.vdf`` is where Steam records extra libraries; the one next
    to the install is listed too.  A missing or unparsable file is not an
    error -- it just means fewer candidates.

    Dedup is case-insensitive on purpose: the registry reports this machine's
    root in lower case while the vdf keeps the on-disk capitalisation, and
    without normcase both survive and we probe the same tree twice.
    """
    roots = []
    seen = set()

    def add(p):
        if not p:
            return
        key = os.path.normcase(os.path.normpath(p))
        if key in seen:
            return
        seen.add(key)
        roots.append(os.path.normpath(p))

    root = steam_root()
    if root:
        add(root)
    # A library's own vdf lists the siblings, so one pass finds the rest.
    for base in list(roots):
        vdf = os.path.join(base, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(vdf):
            continue
        try:
            with open(vdf, encoding="utf-8-sig") as fh:
                text = fh.read()
        except OSError:
            continue
        for p in _vdf_paths(text):
            add(p)
    return roots


def _read_acf_value(path, key):
    """One ``"key" "value"`` pair out of a Steam ``.acf``, or None."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return None
    for raw in text.splitlines():
        s = raw.strip()
        if not s.lower().startswith('"%s"' % key.lower()):
            continue
        val = s.partition(key)[2].strip()
        parts = [p for p in val.split('"') if p.strip()]
        if parts:
            return parts[0].replace("\\\\", "\\")
    return None


def dat_path(game_root):
    return os.path.join(game_root, DAT_REL)


def game_root_of_dat(dat_path):
    """The game root a ``.dat`` path sits under, or ``None``.

    The inverse of :func:`dat_path`.  The path is
    ``<root>/resources/_common/dat/<file>``, which is FOUR components below the
    root -- the filename itself plus three directories.  Stripping three leaves
    ``<root>/resources``, which fails validation and returns ``None``; that is
    what silently dropped the declared objreplacement edges from every caller
    that only knew the .dat path, so ``build()`` wrote 882 villager records
    while ``plan()`` promised 1701.

    It is VALIDATED with :func:`looks_like_game_root` rather than computed
    blindly, because a .dat that has been copied elsewhere (a test fixture, a
    mod's staging folder) must not make its grandparent directory look like an
    install -- the caller then reads ``objreplacement.json`` from the wrong tree,
    or, worse, from a tree that merely happens to have the same shape.
    """
    if not dat_path:
        return None
    cand = os.path.abspath(dat_path)
    for _ in range(4):
        cand = os.path.dirname(cand)
    return cand if looks_like_game_root(cand) else None


def find_profile_root(explicit=None):
    """The user profile root that holds mods, logs and scenarios.

    ``AOE2MOD_PROFILE`` overrides it and points at ONE ACCOUNT folder (the one
    holding ``mods/``), which is what the native engine's ``mods::profile_root``
    has always honoured (`desktop/aoe2mod-serve/src/mods.rs:45`).  This side
    ignored the variable, and that was not a cosmetic gap: measured 2026-10-31,
    `_probe/test_e2e_shipped.py` copied the profile to a temp folder, set
    `AOE2MOD_PROFILE` to it, and the shipped exe -- which by then was running
    THIS engine -- installed two mods into the player's real mod list instead.
    A sandbox that silently resolves elsewhere is worse than no sandbox.

    A set-but-unusable override is an error, never a fall-through: falling
    through is exactly how the test above wrote where it did not mean to.
    """
    if explicit:
        return explicit
    override = os.environ.get(PROFILE_ENV)
    if override is not None:
        if not override:
            raise FileNotFoundError(
                "%s 是空的。要么把它删掉，要么指到存账号文件夹那一层"
                "（本该有 mods\\ 的那一级）。" % PROFILE_ENV)
        if not os.path.isfile(os.path.join(override, "mods",
                                           MOD_STATUS_NAME)):
            raise FileNotFoundError(
                "%s=%s 里面没有 mods\\%s。它要指到存账号文件夹那一层"
                "（本该有 mods\\ 的那一级），不是它的上一层。"
                "因为已经指定了档案目录，就不再退回真实档案。"
                % (PROFILE_ENV, override, MOD_STATUS_NAME))
        return override
    home = os.path.expanduser("~")
    cand = os.path.join(home, "Games", "Age of Empires 2 DE")
    if os.path.isdir(cand):
        return cand
    # Reached on a machine where the game is installed but has never been
    # started.  This sentence is the FIRST thing such a player reads on the
    # screen, so it says what to do next rather than naming a path in English.
    raise FileNotFoundError(
        "还没有游戏存档目录（%r）。先启动一次《帝国时代 2 决定版》，"
        "让它建好存档，再回来。" % cand)


def mods_root(profile_root, kind="subscribed"):
    return os.path.join(profile_root, "*", "mods", kind)


def read_mod_status(profile_root):
    """Read every mod-status.json under the profile, tolerating bare CR/LF.

    Returns ``{path: entry}``.  The ``Path`` field is stored with forward
    slashes relative to the mods root, e.g. ``subscribed//550412_Name``.

    ``profile_root`` may be the parent of the account folders (the usual case)
    OR an account folder itself.  The second shape is what ``AOE2MOD_PROFILE``
    means and what :func:`read_status_doc` already accepts -- but this reader
    only ever looked one level down, so with a sandbox declared the WRITE landed
    in the sandbox and the LIST came back empty: measured 2026-10-31,
    `_probe/test_e2e_shipped.py` installed two mods into its own temp profile and
    then could not find either one.
    """
    out = {}
    if os.path.isfile(os.path.join(profile_root, "mods", MOD_STATUS_NAME)):
        accounts = [profile_root]
    else:
        try:
            accounts = [os.path.join(profile_root, d)
                        for d in os.listdir(profile_root)]
        except OSError:
            return out
    for acc in accounts:
        p = os.path.join(acc, "mods", MOD_STATUS_NAME)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8-sig") as fh:
            text = fh.read()
        try:
            data = json.loads(text)
        except ValueError:
            data = json.loads(text, strict=False)
        for entry in data.get("Mods", []):
            out[entry.get("Path")] = entry
    return out


def list_mods(profile_root, check_exists=True):
    """Every installed mod, ordered by engine Priority (1 = highest).

    ``exists`` is reported rather than assumed, because a user may rename or
    delete a mod folder and the status file then points at nothing.
    """
    status = read_mod_status(profile_root)
    mods = []
    import glob
    # `profile_root` may be an account folder itself (what `AOE2MOD_PROFILE`
    # means and what `read_mod_status` now accepts).  The glob below is built as
    # "<profile>\<account>\mods\...", so an account folder has to collapse to its
    # parent or the pattern matches nothing: measured 2026-10-31, a sandbox
    # profile installed two mods and `list_mods` returned both with a literal
    # `*` in `path` and `exists=False`.
    accounts_root = profile_root
    if os.path.isfile(os.path.join(profile_root, "mods", MOD_STATUS_NAME)):
        accounts_root = os.path.dirname(profile_root.rstrip("\\/")) or profile_root
    for rel, entry in status.items():
        kind, _, name = (rel or "").partition("//")
        # The name is a FOLDER NAME, not a pattern.  Three of the 18 mods on this
        # machine carry glob metacharacters in their name ([UI], [Map]), and
        # passing the name straight to glob.glob made those entries report
        # exists=False and leave a literal '*' inside `path` -- a path that
        # cannot be opened by anything downstream.  glob.escape is the fix.
        pattern = os.path.join(accounts_root, "*", "mods", kind,
                               glob.escape(name))
        hits = sorted(glob.glob(pattern))
        path = (hits[0] if hits
                else os.path.join(accounts_root, "*", "mods", kind, name))
        mods.append({
            "name": name,
            "kind": kind,
            "title": entry.get("Title"),
            "enabled": bool(entry.get("Enabled")),
            "priority": entry.get("Priority"),
            "workshop_id": entry.get("WorkshopID"),
            "path": path,
            "exists": os.path.isdir(path) if check_exists else None,
        })
    mods.sort(key=lambda m: (m["priority"] is None, m["priority"]))
    return mods


# --------------------------------------------------------------------------
# Writing side: where an installed mod goes, and the exact shape of the file
# the engine reads back.  Every rule below was measured, not assumed.
# --------------------------------------------------------------------------

MOD_STATUS_NAME = "mod-status.json"

# Key order inside one entry, exactly as the engine writes it (measured on a
# live 1705-byte file).  JSON objects are unordered, but re-writing in the
# engine's own order keeps diffs readable and avoids surprising other tools.
MOD_ENTRY_KEYS = ("CheckSum", "Enabled", "LastUpdate", "Path", "Priority",
                  "PublishID", "Title", "WorkshopID")


def _now_ms():
    """Milliseconds since the epoch -- the unit `LastUpdate` actually uses.

    Measured values are 13 digits (e.g. 1791051076997), which is ms, not s.
    """
    return int(time.time() * 1000)


def account_mods_dir(account_dir, kind="local"):
    return os.path.join(account_dir, "mods", kind)


def find_accounts(profile_root):
    """Every account folder under the profile that owns a ``mods/`` directory."""
    out = []
    try:
        names = os.listdir(profile_root)
    except OSError:
        return out
    for name in sorted(names):
        p = os.path.join(profile_root, name)
        if os.path.isdir(os.path.join(p, "mods")):
            out.append(p)
    return out


def status_path(account_dir):
    return os.path.join(account_dir, "mods", MOD_STATUS_NAME)


def pick_account(profile_root, explicit=None):
    """The account folder a tool should install into.

    Two accounts coexist on this machine: ``0`` and a SteamID64.  The SteamID
    one is the live profile -- it owns ``mod-status.json`` and every subscribed
    mod -- while ``0`` holds a leftover local mod and no status file at all.
    Scoring by "has a status file, else most mods" follows the data rather than
    hardcoding a SteamID, which is different on every machine.
    """
    if explicit:
        return explicit
    candidates = find_accounts(profile_root)
    if not candidates:
        # Reached when the game has been started but the mod manager never
        # opened: the account folder exists, the `mods` folder under it does not.
        raise FileNotFoundError(
            "在 %r 下面找不到任何带 mods 目录的账号。先在游戏里打开一次"
            "「模组」界面（订阅或安装任意一个模组都行），它会把目录建好。" % profile_root)

    def score(acc):
        has_status = os.path.exists(status_path(acc))
        n = 0
        for kind in ("subscribed", "local"):
            try:
                n += len(os.listdir(account_mods_dir(acc, kind)))
            except OSError:
                pass
        return (1 if has_status else 0, n)

    return max(candidates, key=score)


def read_status_doc(profile_root, account=None):
    """The raw ``mod-status.json`` document, the account, and its original bytes.

    Order is preserved on purpose and must stay that way: the engine's mod list
    has NO sort of its own (``screeninstalledmods.xaml`` binds a plain listbox
    with no ``SortDescription``/``CollectionViewSource``), so the on-screen
    order -- and therefore which mod wins a file conflict -- is exactly the
    array order in this file.
    """
    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)
    p = status_path(acc)
    if not os.path.exists(p):
        return {"Mods": [], "Unsub": []}, acc, None
    with open(p, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig")
    try:
        doc = json.loads(text)
    except ValueError:
        # Shipped files contain bare control characters inside Description.
        doc = json.loads(text, strict=False)
    return doc, acc, raw


def write_status_doc(account_dir, doc, backup=True):
    """Rewrite ``mod-status.json`` byte-compatibly; return the backup path.

    The engine's own writer emits compact JSON, UTF-8, no BOM and no trailing
    newline (measured: 1705 bytes, first byte ``{``, last byte ``}``).  Matching
    that exactly matters because this file is read on every launch, and handing
    the engine a pretty-printed shape it never wrote is an unnecessary risk.

    A backup is taken first: this file is the user's entire mod setup, and a
    bad write makes every mod vanish from the list.
    """
    p = status_path(account_dir)
    bak = None
    if backup and os.path.exists(p):
        bak = p + ".bak"
        with open(p, "rb") as src, open(bak, "wb") as dst:
            dst.write(src.read())
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    return bak


def renumber_priorities(entries):
    """Make ``Priority`` contiguous and equal to list position.

    The file and the UI agree on one thing: array order IS load order.  A new
    mod therefore has to be INSERTED, and every other entry's number shifts.
    Renumbering preserves relative order under both readings -- whether the
    engine sorts by the number or simply walks the array -- which is what makes
    "insert my mod at the top" safe for the mods the user already had.
    """
    for i, e in enumerate(entries, 1):
        e["Priority"] = i
    return entries


def make_status_entry(name, kind="local", title=None, enabled=True,
                      priority=1, workshop_id=0, checksum="0",
                      last_update=None):
    """One ``Mods[]`` entry with the engine's exact key set and order."""
    return {
        "CheckSum": str(checksum),
        "Enabled": bool(enabled),
        "LastUpdate": str(last_update if last_update is not None else _now_ms()),
        "Path": "%s//%s" % (kind, name),
        "Priority": int(priority),
        "PublishID": 0,
        "Title": title or name,
        "WorkshopID": int(workshop_id),
    }


def upsert_mod_entry(doc, name, kind="local", title=None, enabled=True,
                     position=0, workshop_id=0, checksum="0",
                     last_update=None, move=False):
    """Insert or update one entry without reordering anyone else.

    ``position`` is 0-based and only applies to a NEW entry (``0`` = top of the
    list = highest priority = wins file conflicts).

    ``move=True`` also relocates an entry that ALREADY exists.  Installing needs
    that: the game itself registers a local mod folder it finds on disk, so a
    mod we are installing for the first time can already be in the list -- at
    the bottom, disabled.  Treating that as "an entry the user positioned by
    hand" left a fresh install at the end of the list (measured 2026-10-19,
    `dsh test v15`: entry present, `Enabled` written, `Priority` 11 of 11, so
    the game loaded it last).  A hand-positioned mod is only at risk when the
    caller is updating in place, which is why this defaults to ``False``.
    """
    rel = "%s//%s" % (kind, name)
    entries = doc.setdefault("Mods", [])
    found = None
    for e in entries:
        if e.get("Path") == rel:
            found = e
            break
    if found is None:
        found = make_status_entry(
            name, kind=kind, title=title, enabled=enabled,
            priority=len(entries) + 1, workshop_id=workshop_id,
            checksum=checksum, last_update=last_update)
        at = max(0, min(int(position), len(entries)))
        entries.insert(at, found)
    else:
        found["Enabled"] = bool(enabled)
        if title:
            found["Title"] = title
        if move:
            # `install` asked for a position and this entry is not the one the
            # user hand-placed: lift it out and re-insert at `position`.
            entries.remove(found)
            at = max(0, min(int(position), len(entries)))
            entries.insert(at, found)
        # Otherwise leave it exactly where it already sits: an update must never
        # move a mod the user positioned by hand.
    renumber_priorities(entries)
    return found


def move_mod_entry(doc, name, delta, kind="local"):
    """Move one entry up or down in load order; returns its new 1-based Priority.

    Array order is load order, and ``Priority`` is kept equal to position (see
    :func:`renumber_priorities`), so "move up" is a swap of two neighbours
    followed by a renumber -- not a rewrite of every number the user set.

    Out-of-range moves clamp instead of raising: a player pressing 上移 on the
    first row wants "it stayed first", not an error dialog.  The returned number
    is the position it actually ended at, which is what the screen redraws from.
    """
    rel = "%s//%s" % (kind, name)
    entries = doc.setdefault("Mods", [])
    at = None
    for i, e in enumerate(entries):
        if e.get("Path") == rel:
            at = i
            break
    if at is None:
        raise KeyError(name)
    want = at + (1 if int(delta) > 0 else -1)
    if 0 <= want < len(entries):
        entries[at], entries[want] = entries[want], entries[at]
    renumber_priorities(entries)
    for i, e in enumerate(entries):
        if e.get("Path") == rel:
            return i + 1
    return at + 1


def move_mod_to_entry(doc, name, position, kind="local"):
    """Put one entry at ``position`` in load order; returns its new 1-based Priority.

    The two arrows move a row one place, which is all a list of three rows needs
    and not what a drag is: the player picks a row up and drops it somewhere
    else, possibly ten places away.  Sending ten ``delta`` calls would rewrite
    ``mod-status.json`` eleven times and could half-apply if one failed.

    ``position`` is the index in the array AFTER the row has been lifted out, so
    "drop before row N" is ``position = N`` and "drop at the end" is the list
    length.  It is clamped rather than raising: a drop that lands past the end
    means "last", not an error dialog.  Measured with the 18 mods on this
    machine: 0.0004 s for the reorder plus renumber.
    """
    rel = "%s//%s" % (kind, name)
    entries = doc.setdefault("Mods", [])
    at = None
    for i, e in enumerate(entries):
        if e.get("Path") == rel:
            at = i
            break
    if at is None:
        raise KeyError(name)
    item = entries.pop(at)
    want = max(0, min(int(position), len(entries)))
    entries.insert(want, item)
    renumber_priorities(entries)
    return want + 1


def remove_mod_entry(doc, name, kind="local"):
    """Drop one entry; returns how many were removed (0 or 1)."""
    rel = "%s//%s" % (kind, name)
    entries = doc.setdefault("Mods", [])
    kept = [e for e in entries if e.get("Path") != rel]
    removed = len(entries) - len(kept)
    doc["Mods"] = renumber_priorities(kept)
    return removed


GAME_PROCESS = "AoE2DE_s.exe"


def game_running(process=GAME_PROCESS):
    """Is the game running right now?  ``True`` / ``False`` / ``None``.

    Three-valued on purpose: a false "no" is an alarm that teaches the user to
    ignore alarms, so a process table we could not read must answer ``None``,
    not ``False``.

    A Toolhelp snapshot rather than ``tasklist``: measured 4 ms for 267
    processes and it spawns nothing.  The probe scripts used
    ``subprocess.run(["tasklist", ...])``, which is a process spawn whose
    failure mode (no permission, no PATH) is indistinguishable from "not
    running" -- exactly the wrong way for this question to fail.

    Why ask at all: the engine holds the mod list in memory and rewrites
    ``mod-status.json`` when it exits.  An entry written while the game is
    running can therefore be replaced by the older list at exit -- the files
    stay, the entry disappears.  The user chose (2026-10-20) to WARN and still
    install, not to refuse: dropping a data mod folder in while playing is a
    real thing people do.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _PE32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * 260),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        snap = k32.CreateToolhelp32Snapshot(0x2, 0)   # TH32CS_SNAPPROCESS
        if not snap or snap == wintypes.HANDLE(-1).value:
            return None
        try:
            e = _PE32()
            e.dwSize = ctypes.sizeof(_PE32)
            if not k32.Process32FirstW(snap, ctypes.byref(e)):
                return None
            want = process.lower()
            while True:
                if e.szExeFile.lower() == want:
                    return True
                if not k32.Process32NextW(snap, ctypes.byref(e)):
                    return False
        finally:
            k32.CloseHandle(snap)
    except Exception:                                  # noqa: BLE001
        return None


def running_note(process=GAME_PROCESS):
    """The two manifest fields that carry the "is the game open" answer.

    Merged into every result that writes ``mod-status.json`` -- install,
    uninstall and enable/disable all have the same hazard, so they all say the
    same thing instead of one of them looking safe by silence.
    """
    running = game_running(process)
    note = None
    if running:
        note = ("游戏正开着。它退出时会用自己记得的模组列表覆盖 "
                "mod-status.json，所以这次写进去的改动可能被盖掉（文件还在，"
                "列表里没有）。装完回游戏里看一眼，或者关掉游戏再写一次。")
    return {"game_running": running, "running_warning": note}


def install_mod(mod_dir, profile_root, name=None, title=None, kind="local",
                enabled=True, position=0, account=None, overwrite=False,
                backup=True, checksum=None):
    """Copy an emitted mod folder into the profile and register it.

    Two separate things must happen, and only the first is a file copy:

      1. The folder lands in ``<account>/mods/<kind>/<name>``.  Its name IS the
         mod name, and the engine derives the storage path from the folder, so
         the name must not be changed afterwards.
      2. ``mod-status.json`` gains an entry, because a mod with files on disk
         and no entry is not loaded.  (Belt and braces: ``local/`` mods do seem
         to be discovered without the file -- this machine has a local mod under
         the ``0`` account and no status file there -- but the entry is what
         makes enabling, ordering and the in-game list work, so we always write
         it.)

    Returns a manifest.  ``dat_sha256`` lets a caller prove the installed bytes
    are the bytes that were built.
    """
    import shutil

    src = os.path.abspath(mod_dir)
    if not os.path.isdir(src):
        raise FileNotFoundError("emitted mod folder not found: %r" % mod_dir)
    if not os.path.exists(os.path.join(src, "info.json")):
        raise ValueError("not a mod folder (no info.json): %r" % mod_dir)

    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)

    if name is None:
        read_info = json.loads(
            open(os.path.join(src, "info.json"), encoding="utf-8-sig").read())
        name = read_info.get("Title") or os.path.basename(src)
    if title is None:
        title = name

    target = os.path.join(account_mods_dir(acc, kind), name)
    if os.path.exists(target):
        if not overwrite:
            raise FileExistsError(
                "这个位置已经装着一个叫「%s」的模组了：%s。"
                "要换掉它的话，调用时带上 overwrite=True。"
                % (name, target))
        shutil.rmtree(target)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copytree(src, target)

    doc, acc, _ = read_status_doc(profile_root, account=acc)
    entry = upsert_mod_entry(doc, name, kind=kind, title=title,
                             enabled=enabled, position=position, move=True,
                             checksum=(checksum if checksum is not None else "0"))
    # The engine keeps a FOLDER CHECKSUM in this entry and verifies the selected
    # dataset against it.  Writing "0" left the number unusable for the two
    # things that read it: `dataset.write_selection` refuses a zero checksum, and
    # `dataset.audit` cannot tie a `Player.nfp` record to a folder whose status
    # entry says zero -- so the tool's own freshly installed data mod looked like
    # "nothing is picked" the moment it was installed.  Measured 2026-11-21: the
    # only entries on this disk carrying a real CheckSum are the ones the GAME
    # wrote, and the game writes it right after it discovers the folder.
    #
    # Computed here, once, from the bytes that just landed -- the same rule the
    # engine uses (`zlib.crc32` over the folder, `info.json`/`thumbnail*` aside).
    # An explicit `checksum=` still wins, so a caller that already knows the
    # number does not pay for a second walk over 12 MB.
    crc = checksum
    if crc is None:
        dat_probe = os.path.join(target, DAT_REL)
        if os.path.isfile(dat_probe):
            from . import dataset as _DS
            crc = _DS._folder_checksum(target)
    if crc is not None:
        entry["CheckSum"] = str(crc)
    bak = write_status_doc(acc, doc, backup=backup)

    dat = os.path.join(target, DAT_REL)
    man = {
        "account": acc,
        "kind": kind,
        "name": name,
        "title": title,
        "mod_dir": target,
        "enabled": bool(entry["Enabled"]),
        "priority": entry["Priority"],
        "path_field": entry["Path"],
        "status_file": status_path(acc),
        "status_backup": bak,
        "status_entries": len(doc.get("Mods", [])),
        "dat": dat if os.path.exists(dat) else None,
        "installed": True,
        # The game does NOT have to be restarted for a data mod.  A mod folder
        # dropped in while the session is running is picked up by a later
        # mod-manager pass, and the user confirmed this in game (2026-10-16):
        # "我开着游戏不影响数据模组的编辑，直接放进文件夹，开着的游戏也是能读取到的，
        # 除了图形那种和某些特殊的启用方式".
        #
        # Earlier this manifest said the opposite, and the evidence was
        # misread.  `_probe/test_mod_load_timing.py` shows the engine enabling
        # these mods at log line 860-996 while "Opening resource packages" is at
        # 254-267 -- but being ENABLED late is not being IGNORED; the later pass
        # is when the mod manager picks up a newly added folder at all.  The
        # claim that the JSON half silently does nothing was never one clean
        # experiment: the one tree-only attempt (2026-10-14) also failed to move
        # the menu because the menu reads the shipped panel file, and every test
        # before it never had the mod loaded in the first place.
        #
        # Graphics are different: a running session has already bound its
        # atlases, XAML and sprite sheets.  `storage_points_touched` names what
        # this mod actually touches, so a caller can say "restart for the
        # textures" instead of "restart" as a blanket rule.
        "storage_points": storage_points_touched(target),
    }
    _pts = man["storage_points"]
    man["requires_game_restart"] = bool(_pts)
    if _pts:
        man["restart_note"] = (
            "this mod writes %s, which a running game has already bound, so the "
            "change may only appear after a relaunch. Data mods do not need "
            "this: a mod folder dropped in while the game runs is picked up by "
            "a later mod-manager pass." % ", ".join(_pts))
    else:
        man["restart_note"] = (
            "no restart needed. The game picks up a mod folder while it is "
            "running, so a data mod (`.dat` and the JSON files beside it) "
            "takes effect without relaunching.")
    if man["dat"]:
        man["dat_sha256"] = sha256_file(man["dat"])
        man["dat_file_bytes"] = os.path.getsize(man["dat"])
    # "Do I need to close the game" is a different question from "do I need to
    # relaunch it", and this manifest used to answer only the second one.  Both
    # are now answered, because a user who is told "no restart needed" will
    # reasonably leave the game open -- and that is when the entry gets lost.
    man.update(running_note())
    return man


def resolve_mod_any(profile_root, name, kind="local", account=None):
    """Resolve a mod name to ``(folder, kind, how)``, searching BOTH kinds.

    Every write route passes ``kind`` through with the default ``"local"``, but a
    Steam library lives in ``subscribed``.  Measured 2026-11-07 on the machine
    this was built on: all 18 installed mods are ``subscribed``, so the arrows,
    the drag and the on/off switches all failed -- 「移不动：'582581_文明联盟 test 9'」
    for a move (the entry is ``subscribed//...``, not ``local//...``) and
    「没找到叫「…」的模组」 for a toggle -- while every one of them was drawn from
    the list that had just been read out of the subscribed folder.

    The requested ``kind`` wins when the name exists in both, because that is the
    caller's own statement about which one it means.  Only when it matches nothing
    is the other kind tried, which is the case that used to be a dead end.
    """
    folder, how = resolve_mod_name(profile_root, name, kind=kind, account=account)
    if how != "bare":
        return folder, kind, how
    other = "subscribed" if kind == "local" else "local"
    folder2, how2 = resolve_mod_name(profile_root, name, kind=other,
                                     account=account)
    if how2 != "bare":
        return folder2, other, how2
    # Neither status entry matched.  A folder dropped into the mods tree by hand
    # still counts -- the game registers those itself -- so look on disk too.
    try:
        acc = account or (profile_root
                          if os.path.isdir(os.path.join(profile_root, "mods"))
                          else pick_account(profile_root))
        for k in (kind, other):
            if os.path.isdir(os.path.join(account_mods_dir(acc, k), name)):
                return name, k, "folder"
    except Exception:
        pass
    return folder, kind, how


def resolve_mod_name(profile_root, name, kind="local", account=None):
    """Turn a mod's folder name OR its Title into the folder name.

    Both spellings are in use, and they genuinely differ on this machine: the
    subscribed mod at ``subscribed//182654_Age of Anime (Chibi Edition)`` has the
    Title ``Age of Anime (Chibi Edition)`` -- the publisher prefixes the folder
    with the workshop id.  A UI lists mods by Title, so calling
    ``uninstall(title)`` would silently remove nothing, and the caller would read
    ``entries_removed: 0`` as "it was not installed".

    Returns ``(folder_name, how)`` where ``how`` says which spelling matched:
    ``"path"`` (already a folder name), ``"title"`` (resolved via the status
    file), or ``"bare"`` (nothing matched, returned unchanged so the caller's own
    "not installed" error still reads naturally).
    """
    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        try:
            acc = pick_account(profile_root)
        except Exception:
            return name, "bare"

    doc, _acc, _ = read_status_doc(profile_root, account=acc)
    for e in doc.get("Mods", []):
        rel = e.get("Path") or ""
        k, _, folder = rel.partition("//")
        if k != kind:
            continue
        if folder == name:
            return folder, "path"
    for e in doc.get("Mods", []):
        rel = e.get("Path") or ""
        k, _, folder = rel.partition("//")
        if k != kind:
            continue
        if (e.get("Title") or "") == name:
            return folder, "title"
    return name, "bare"


def recycle_path(path):
    """Move a file or folder to the Recycle Bin.  Returns ``True`` on success.

    The player asked for this directly (2026-10-26): "还有移除是什么意思，放入
    回收站吗".  Up to today `uninstall_mod` called `shutil.rmtree`, so "移除" was
    permanent -- and the thing it deletes is a folder the player may have spent
    an evening tuning.  Nothing here is about tidiness: an editor that can only
    destroy is an editor people stop using on anything they care about.

    Uses the shell's own recycle verb (``SHFileOperationW`` with ``FOF_ALLOWUNDO``)
    because that is the only route that lands in the bin rather than in a
    folder this program invented.  It refuses a path that does not exist, and on
    a machine where the call fails it returns ``False`` so the caller can say so
    instead of reporting a deletion that did not happen.
    """
    import ctypes
    from ctypes import wintypes

    path = os.path.abspath(path)
    if not os.path.exists(path):
        return False
    if os.name != "nt":
        return False

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_uint16),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE = 3
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040
    FOF_NOERRORUI = 0x0400
    # pFrom is a double-NUL-terminated list; one path means two terminators.
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0\0"
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI
    try:
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    except Exception:
        return False
    if rc != 0 or op.fAnyOperationsAborted:
        return False
    return not os.path.exists(path)


def uninstall_mod(profile_root, name, kind="local", remove_files=True,
                  account=None, backup=True):
    """Remove a mod's status entry, and its folder unless told otherwise.

    ``name`` may be the mod's FOLDER name or its Title -- see
    :func:`resolve_mod_name` for why both are needed.
    """
    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)

    folder, kind, how = resolve_mod_any(profile_root, name, kind=kind,
                                       account=acc)
    _running = running_note()

    doc, acc, _ = read_status_doc(profile_root, account=acc)
    removed = remove_mod_entry(doc, folder, kind=kind)
    if removed:
        write_status_doc(acc, doc, backup=backup)

    target = os.path.join(account_mods_dir(acc, kind), folder)
    files_gone = False
    recycled = False
    if remove_files and os.path.isdir(target):
        # Recycle, never destroy: the player asked (2026-10-26).  Measured before
        # this change, "移除" called `shutil.rmtree` -- an evening's tuning gone
        # with one click and no way back.
        recycled = recycle_path(target)
        files_gone = recycled
        if not files_gone:
            raise OSError(
                "\u300c%s\u300d的文件夹没能放进回收站，所以什么也没删：%s。"
                "（退出占用它的程序再试）" % (folder, target))
    return {"account": acc, "name": folder, "requested": name,
            "resolved_by": how, "kind": kind,
            "entries_removed": removed, "folder_removed": files_gone,
            "recycled": recycled,
            "mod_dir": target, "status_entries": len(doc.get("Mods", [])),
            "game_running": _running["game_running"],
            "running_warning": _running["running_warning"]}


def set_mod_enabled(profile_root, name, enabled, kind="local", account=None,
                    backup=True):
    """Turn an installed mod on or off without moving it in the list.

    Disabling is not deleting: the entry stays (the engine keeps a disabled mod
    in the list, greyed out) and its position is preserved, so re-enabling later
    restores exactly the conflict order the user had.

    ``name`` may be the folder name or the Title (see :func:`resolve_mod_name`).

    A name that matches NOTHING is refused instead of created.  ``upsert``
    creates an entry when it finds none, which is what ``install_mod`` wants and
    the opposite of what this function means: measured 2026-10-20, toggling a
    name that did not exist inserted ``__no_such_mod__`` at Priority 1 of the
    player's real list -- a phantom entry pointing at a folder that is not
    there, reported to the caller as ``ok``.  A folder the player dropped into
    ``mods/local`` by hand still works: the game itself registers those, so the
    folder on disk is the second half of "does this mod exist".
    """
    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)
    folder, kind, _how = resolve_mod_any(profile_root, name, kind=kind,
                                       account=acc)
    doc, acc, _ = read_status_doc(profile_root, account=acc)
    if _how == "bare" and not os.path.isdir(
            os.path.join(account_mods_dir(acc, kind), folder)):
        raise FileNotFoundError(
            "没找到叫「%s」的模组：模组列表里没有它，模组文件夹里也没有这个文件夹。"
            "它可能已经被删掉或者改名了，刷新一下列表再试。" % (name,))
    _running = running_note()
    entry = upsert_mod_entry(doc, folder, kind=kind, enabled=enabled)
    write_status_doc(acc, doc, backup=backup)
    return {"account": acc, "name": name, "kind": kind,
            "enabled": bool(entry["Enabled"]), "priority": entry["Priority"],
            "path_field": entry["Path"],
            "game_running": _running["game_running"],
            "running_warning": _running["running_warning"]}


def set_mod_info(profile_root, name, title=None, author=None,
                 description=None, kind="local", account=None, backup=True):
    """Rewrite the parts of an installed mod's `info.json` the player can type.

    What the engine reads, and what this does NOT touch:

    * `Title` is the name the mod manager shows.  It is NOT the folder name --
      the folder is found from `mod-status.json`'s `Path`, so renaming a mod
      never moves a directory and never breaks an installed save.  The status
      entry's own `Title` is updated to match, because that is what the list
      renders.
    * `Description` / `Author` are shown in the mod manager and nowhere else.
      `Description` may be empty and may be any length; `Author` may not be
      empty (see `emitter.validate_info`), so an old file with no author falls
      back instead of refusing the edit.

    Every other key the file already had is carried over verbatim -- community
    mods ship `Unpublished`, `thumbnail`, `previewIcon` and friends, and a
    rename that quietly dropped them would unpublish the mod.

    A `<folder>_ui` sibling keeps its pairing: its Title is rewritten to
    `<new title>（界面）` so `ui/server._pair_rows` still matches the two halves.
    Its folder name stays put, exactly like the data half's.
    """
    from ..mod import emitter as E

    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)
    # The third value says HOW the name was found (path / title / folder / bare).
    # This caller does not care: a mod it cannot find on disk raises below either
    # way, and the message names the folder it looked for.  Discarding it keeps
    # `_how` in this file to the one place that branches on it.
    folder, kind, _ = resolve_mod_any(profile_root, name, kind=kind,
                                     account=acc)
    target = os.path.join(account_mods_dir(acc, kind), folder)
    if not os.path.isdir(target):
        raise FileNotFoundError(
            "没找到叫「%s」的模组：模组列表里没有它，模组文件夹里也没有这个文件夹。"
            "它可能已经被删掉或者改名了，刷新一下列表再试。" % (name,))

    def _merged(path, want_title):
        old = E.read_info_soft(os.path.join(path, "info.json"))
        info = dict((k, v) for k, v in old.items() if isinstance(k, str))
        info["Title"] = want_title or str(old.get("Title") or
                                          os.path.basename(path))
        info["Author"] = str(old.get("Author") or AV.AUTHOR)
        info["Description"] = str(old.get("Description") or "")
        if "CacheStatus" not in info:
            info["CacheStatus"] = 0
        return info

    want = (title or "").strip()
    info = _merged(target, want)
    if author is not None:
        info["Author"] = author.strip() or info["Author"]
    if description is not None:
        info["Description"] = description
    problems = E.validate_info(info)
    if problems:
        raise ValueError(" ".join(problems))

    ui_dir = target.rstrip("\\/") + "_ui"
    ui_title = None
    if os.path.isdir(ui_dir):
        ui_title = E._fit_title_stem(info["Title"], "\uff08\u754c\u9762\uff09")

    doc, acc, _ = read_status_doc(profile_root, account=acc)
    rel = "%s//%s" % (kind, folder)
    found = None
    for e in doc.get("Mods", []):
        if e.get("Path") == rel:
            found = e
            break
    status_updated = False
    if found is not None:
        found["Title"] = info["Title"]
        status_updated = True
        if ui_title:
            ui_rel = "%s//%s" % (kind, os.path.basename(ui_dir))
            for e in doc.get("Mods", []):
                if e.get("Path") == ui_rel:
                    e["Title"] = ui_title
                    break

    info_path = E.write_info_json(target, info)
    if ui_title:
        E.write_info_json(ui_dir, _merged(ui_dir, ui_title))
    if status_updated:
        write_status_doc(acc, doc, backup=backup)
    _running = running_note()
    return {"account": acc, "name": name, "folder": folder, "kind": kind,
            "title": info["Title"], "author": info["Author"],
            "description_length": len(info["Description"]),
            "info_path": info_path, "path_field": rel,
            "status_updated": status_updated,
            "ui_title": ui_title,
            "game_running": _running["game_running"],
            "running_warning": _running["running_warning"]}


def copy_mod(profile_root, name, new_name=None, title=None, author=None,
             description=None, kind="local", account=None, enabled=True,
             position=0, backup=True):
    """Duplicate an installed mod into a SECOND folder, leaving the first alone.

    「改模组名字和简介没有另存为」 -- the panel could only rewrite the one
    `info.json` it found, so a player who liked a shipped mod's data but wanted
    their own name on it had no way to keep both: typing a new name overwrote
    the original.  This is the missing half, and it is a COPY, not a rename:

    * the source folder is read, never written -- not one byte of it changes,
      so the original stays in the list exactly as it was;
    * the copy gets its own folder in the same `mods/<kind>/` tree, and the
      folder name IS the new Title, because the engine derives the storage path
      from the folder and lists the mod by it;
    * `mod-status.json` gains an entry for the copy at ``position`` (0 = top of
      the list = highest priority), enabled like the original, so the game
      actually loads it;
    * a `<folder>_ui` sibling is copied beside it and retitled `<title>（界面）`,
      because `ui/server._pair_rows` matches the two halves by Title and a
      renamed data half would otherwise unpair from its interface half.

    The `.dat` comes along with the copy: duplicating a 30 MB data folder is the
    point of the feature, and a "copy" that pointed at the original's bytes
    would make editing one silently edit both.
    """
    import shutil
    from ..mod import emitter as E

    if account:
        acc = account
    elif os.path.isdir(os.path.join(profile_root, "mods")):
        acc = profile_root
    else:
        acc = pick_account(profile_root)
    folder, kind, _ = resolve_mod_any(profile_root, name, kind=kind,
                                      account=acc)
    src = os.path.join(account_mods_dir(acc, kind), folder)
    if not os.path.isdir(src):
        raise FileNotFoundError(
            "没找到叫「%s」的模组：模组列表里没有它，模组文件夹里也没有这个文件夹。"
            "它可能已经被删掉或者改名了，刷新一下列表再试。" % (name,))

    old = E.read_info_soft(os.path.join(src, "info.json"))
    want_title = (title or "").strip() or (new_name or "").strip()
    if not want_title:
        # 「副本」 rather than a timestamp: the player is going to rename this
        # anyway, and a name carrying a clock reads like a backup file.
        want_title = str(old.get("Title") or folder) + " 副本"
    bad = sorted(set(E.BANNED_TITLE_CHARS) & set(want_title))
    if bad:
        raise ValueError(
            "新名字里有引擎不允许的字符：%s。这个名字会被当作文件夹名，所以这些"
            "字符不能出现。把「%s」里去掉它们就行。"
            % (" ".join(bad), want_title))
    want_title = E._fit_title(want_title)
    target_name = want_title
    if target_name == folder:
        raise ValueError(
            "新名字和原来一样（%s），这样只是原地改名，用「存进 info.json」就行；"
            "另存为要的是一个不一样的名字，原来那份才不会被动。" % (folder,))
    target = os.path.join(account_mods_dir(acc, kind), target_name)
    if os.path.exists(target):
        raise FileExistsError(
            "这个位置已经有一个叫「%s」的模组了：%s。换一个名字再存，或者先在"
            "列表里把它删掉。" % (target_name, target))

    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copytree(src, target)

    info = dict((k, v) for k, v in old.items() if isinstance(k, str))
    info["Title"] = want_title
    info["Author"] = (str(old.get("Author") or AV.AUTHOR)
                      if author is None else (author.strip() or
                                              str(old.get("Author") or AV.AUTHOR)))
    info["Description"] = (str(old.get("Description") or "")
                           if description is None else description)
    if "CacheStatus" not in info:
        info["CacheStatus"] = 0
    problems = E.validate_info(info)
    if problems:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(" ".join(problems))
    info_path = E.write_info_json(target, info)

    # A split build is two folders and ONE decision.  Copying only the data half
    # would leave the player with a new mod drawing the old icons -- and the pair
    # would be gone, because pairing reads the Title suffix.
    ui_src = src.rstrip("\\/") + E.UI_FOLDER_SUFFIX
    ui_name = None
    ui_target = None
    if os.path.isdir(ui_src):
        ui_title = E._fit_title_stem(want_title, "\uff08\u754c\u9762\uff09")
        ui_target = os.path.join(account_mods_dir(acc, kind), ui_title)
        if os.path.exists(ui_target):
            shutil.rmtree(target, ignore_errors=True)
            raise FileExistsError(
                "这个位置已经有一个叫「%s」的模组了：%s。换一个名字再存。"
                % (ui_title, ui_target))
        shutil.copytree(ui_src, ui_target)
        ui_old = E.read_info_soft(os.path.join(ui_src, "info.json"))
        ui_info = dict((k, v) for k, v in ui_old.items() if isinstance(k, str))
        ui_info["Title"] = ui_title
        ui_info["Author"] = info["Author"]
        if "CacheStatus" not in ui_info:
            ui_info["CacheStatus"] = 0
        E.write_info_json(ui_target, ui_info)
        ui_name = ui_title

    doc, acc, _ = read_status_doc(profile_root, account=acc)
    entry = upsert_mod_entry(doc, target_name, kind=kind, title=want_title,
                             enabled=enabled, position=position, move=True)
    if ui_name:
        upsert_mod_entry(doc, ui_name, kind=kind, title=ui_name,
                         enabled=enabled, position=position + 1, move=True)
    bak = write_status_doc(acc, doc, backup=backup)

    dat = os.path.join(target, DAT_REL)
    _running = running_note()
    return {"account": acc, "name": name, "folder": folder, "kind": kind,
            "new_name": target_name, "title": want_title,
            "mod_dir": target, "info_path": info_path,
            "path_field": entry["Path"], "priority": entry["Priority"],
            "status_file": status_path(acc), "status_backup": bak,
            "status_entries": len(doc.get("Mods", [])),
            "dat": dat if os.path.exists(dat) else None,
            "ui_name": ui_name, "ui_dir": ui_target,
            "copied": True,
            "game_running": _running["game_running"],
            "running_warning": _running["running_warning"]}


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

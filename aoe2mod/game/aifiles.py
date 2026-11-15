"""Which ``.per`` / ``.xs`` file to open, and writing it back.

Reported 2026-11-03, same sentence as :mod:`aoe2mod.game.datsources`: 「我要改
指定的dat或者ai/xs，你这完全没有给我选择」.  The language editor could write a
rule, a whole script, and validate text, but the only thing the player could do
with the result was copy it into a text box -- there was no way to name a file,
so "write this to my AI" was not possible.

Where the files actually are, measured 2026-11-03 on this machine:

* ``<game>/resources/_common/ai/`` -- **53 ``.per``** plus 3 ``.ai``.  These are
  the game's own scripts; editing one changes the game for every campaign and
  every random map that loads it, so a caller that means "my AI" must not land
  here by accident.  Listed anyway, because a mod author genuinely does edit
  ``AiBuilder.per``, and hiding it only pushes them into Explorer.
* ``<game>/resources/_common/xs/`` -- **7 ``.xs``** (``Constants.xs``,
  ``Effects.xs``, ``x256tech.xs``, ``x9tech.xs`` and three under ``ailib/``).
* ``<profile>/<account>/resources/_common/ai/`` -- **empty** on this machine.
* ``<profile>/<account>/resources/_common/xs/`` -- **only ``default0.xs``**.

The two profile folders are where a player's OWN scripts belong, and they are
nearly empty: that is the gap this module fills.  Files are written as plain
UTF-8 with no BOM and ``\\n`` endings, because the game's own files are ASCII
and a BOM in front of ``(defrule`` stops the parser dead.
"""

import os

#: Where the game keeps its own scripts, per department.
GAME_SUBDIR = {
    "ai": os.path.join("resources", "_common", "ai"),
    "xs": os.path.join("resources", "_common", "xs"),
}

EXT = {"ai": ".per", "xs": ".xs"}

#: ``.ai`` files are the tiny "load these .per files" manifests.  Editable, and
#: listed separately so nobody mistakes one for a rule file.
MANIFEST_EXT = ".ai"

#: A script larger than this is not something this screen should open: the box
#: is a textarea, and measured here the biggest game script is 78 KB.  A file
#: past the cap is still LISTED (so the list does not lie about the folder), and
#: opening it is refused with a sentence rather than silently truncated.
# One script can be read into the editor at a time.  Measured on this install:
# the biggest `.per` is `AI (HD version).per` at 1,170,991 bytes and the next
# four are 350-465 KB, so a 512 KB cap refused the one file a player is most
# likely to want to read.  4 MB covers every script shipped with the game and
# still refuses a file that would make the textbox unusable.
MAX_BYTES = 4 * 1024 * 1024


#: Which scope wins when two folders hold a file of the same name.  A local mod
#: is where a script actually gets LOADED (the profile's own `ai/` folder is only
#: read when the player starts a scenario), so it sorts first; the game's shipped
#: folder sorts last because overwriting it changes every campaign and every
#: random map at once.
SCOPE_RANK = {"mod": 0, "profile": 1, "game": 2}


def local_mod_dirs(account_dir):
    """``[(name, path)]`` for every folder under ``<account>/mods/local``."""
    base = os.path.join(account_dir, "mods", "local")
    out = []
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if os.path.isdir(d):
            out.append((name, d))
    return out


def _roots(game_root=None, profile_root=None, account=None):
    """``[(scope, dept, dir, label)]`` for every folder a script may live in.

    Three scopes now, not two.  Reported 2026-11-10: 「这个生成的东西应该放local
    去」 -- what this screen generates has to end up somewhere the engine loads,
    and that is ``mods/local/<name>/resources/_common/<ai|xs>/``, not the game's
    own folder and not the nearly-empty profile copy.  Local mods are listed too
    so a script written there can be read back and edited in the same box.
    """
    from . import locations as LOC
    out = []
    game_root = game_root or LOC.find_game_root()
    for dept, rel in (("ai", GAME_SUBDIR["ai"]), ("xs", GAME_SUBDIR["xs"])):
        out.append(("game", dept, os.path.join(game_root, rel), "游戏本体"))
    try:
        root = profile_root or LOC.find_profile_root()
        # Three shapes reach this point.  An account folder passed directly (its
        # own `mods` next to it) is the shape AOE2MOD_PROFILE declares and the
        # one `read_status_doc` already accepts; `pick_account` looks only one
        # level DOWN for accounts, so handing it an account folder found none and
        # this function quietly listed the game's folders only -- which is
        # exactly what made a freshly written local mod invisible in the chooser
        # (measured 2026-11-10).
        if account:
            prof = account
        elif os.path.isdir(os.path.join(root, "mods")):
            prof = root
        else:
            prof = LOC.pick_account(root)
    except Exception:
        return out
    for dept, rel in (("ai", GAME_SUBDIR["ai"]), ("xs", GAME_SUBDIR["xs"])):
        out.append(("profile", dept, os.path.join(prof, rel), "我的档案"))
    for name, mod_dir in local_mod_dirs(prof):
        for dept, rel in (("ai", GAME_SUBDIR["ai"]), ("xs", GAME_SUBDIR["xs"])):
            d = os.path.join(mod_dir, rel)
            # Only folders that exist: a mod that ships no script must not add
            # an empty line to the chooser per department.
            if os.path.isdir(d):
                out.append(("mod", dept, d, "本地模组「%s」" % name))
    return out


def _walk(directory, exts):
    """Every matching file below ``directory``, as paths relative to it."""
    found = []
    if not os.path.isdir(directory):
        return found
    for base, dirs, files in os.walk(directory):
        dirs.sort()
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in exts:
                full = os.path.join(base, name)
                found.append((os.path.relpath(full, directory), full))
    return found


def dept_of(path):
    """``"ai"`` or ``"xs"`` from the extension, or ``""`` when neither."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext in (".per", ".ai"):
        return "ai"
    if ext == ".xs":
        return "xs"
    return ""


def entries(game_root=None, profile_root=None, account=None, dept=None):
    """Every script file a player could mean, with the facts a chooser needs.

    ``editable`` is False for the game's own files under a **read-only** install
    (a Store install, or a Steam library the user cannot write to).  Probed by
    attempting an append of zero bytes -- the only reliable, side-effect-free
    test on Windows, where ``os.access(W_OK)`` answers from the ACL of the
    parent directory rather than the file's own.
    """
    out = []
    for scope, d, directory, label in _roots(game_root, profile_root, account):
        if dept and d != dept:
            continue
        exts = {EXT[d], MANIFEST_EXT} if d == "ai" else {EXT[d]}
        for rel, full in _walk(directory, exts):
            try:
                size = os.path.getsize(full)
                when = int(os.path.getmtime(full))
            except OSError:
                size, when = 0, 0
            out.append({
                "path": os.path.abspath(full),
                "scope": scope,          # game | profile
                "scope_label": label,
                "dept": d,               # ai | xs
                "rel": rel.replace(os.sep, "/"),
                "name": os.path.basename(full),
                "ext": os.path.splitext(full)[1].lower(),
                "manifest": os.path.splitext(full)[1].lower() == MANIFEST_EXT,
                "bytes": size,
                "mtime": when,
                "too_big": size > MAX_BYTES,
                "writable": _writable(full),
            })
    # Local mods first: that is where the engine actually loads a script from,
    # and the reason this screen writes there.  Then the player's own folder,
    # which is nearly empty.  The game's own files last, because they are the
    # ones that collide with every campaign.
    out.sort(key=lambda e: (SCOPE_RANK.get(e["scope"], 9), e["dept"],
                            e["rel"].lower()))
    return out


#: Default folder name for the local mod this screen writes into.  A mod folder
#: is identified by its name (the engine derives the storage path from it), so
#: this string is a real identity, not a label: changing it later leaves the old
#: folder behind as a second mod.
DEFAULT_MOD = "模组工坊脚本"

#: Script name used when the player did not type one.
DEFAULT_SCRIPT = {"ai": "我的AI", "xs": "我的XS"}

#: The engine cuts a mod Title at 100 UTF-8 bytes and then looks for a folder of
#: that cut name, so a folder name longer than 33 Chinese characters would
#: produce a mod that is "enabled" and does nothing.
MOD_NAME_MAX = 30


def _safe_name(name, fallback, limit):
    """A folder-safe name, or ``fallback`` when nothing usable is left.

    Same character set as the rest of this package (``_safe_dir`` in
    ``ui/server.py``): alphanumerics plus a few brackets, because the name becomes
    a Windows directory inside the player's profile.
    """
    keep = "-_ ()（）[]【】·"
    out = "".join(ch for ch in str(name or "") if ch.isalnum() or ch in keep)
    out = out.strip(" .")
    return out[:limit] or fallback


def local_target_of(path):
    """``(mod_name, stem)`` when ``path`` is a script inside a local mod.

    The reverse of :func:`local_mod_dir`, for the screen's "update the file I am
    looking at" case: it only ever yields two NAME pieces, never a directory to
    write into, so a path the player cannot write still cannot steer a save --
    the write itself always goes back through ``local_mod_dir``.
    """
    if not path:
        return None
    parts = os.path.normpath(os.path.abspath(str(path))).split(os.sep)
    low = [p.lower() for p in parts]
    try:
        i = len(low) - 1 - low[::-1].index("local")
    except ValueError:
        return None
    # <account>/mods/local/<mod>/resources/_common/<ai|xs>/<name>
    if i < 1 or low[i - 1] != "mods":
        return None
    if len(parts) < i + 6 or parts[i + 2].lower() != "resources" \
            or parts[i + 3].lower() != "_common":
        return None
    dept = parts[i + 4].lower()
    if dept not in EXT:
        return None
    mod = parts[i + 1]
    name = parts[i + 5]
    if os.path.splitext(name)[1].lower() != EXT[dept]:
        return None
    return mod, os.path.splitext(name)[0]


def local_mod_dir(profile_root=None, account=None, mod_name=None):
    """``(mod_dir, account_dir)`` for the local mod these scripts go into."""
    from . import locations as LOC
    root = profile_root or LOC.find_profile_root()
    if account:
        acc = account
    elif os.path.isdir(os.path.join(root, "mods")):
        # The caller handed us an account folder, not a profile: same fallback
        # ``read_status_doc`` and ``install_mod`` use.
        acc = root
    else:
        acc = LOC.pick_account(root)
    mod = _safe_name(mod_name, DEFAULT_MOD, MOD_NAME_MAX)
    return os.path.join(LOC.account_mods_dir(acc, "local"), mod), acc


def _local_info(mod):
    return {"Author": "模组工坊", "CacheStatus": 0,
            "Description": "模组工坊生成的 AI 脚本。改这里的内容，游戏里直接生效。",
            "Title": mod}


def save_local(dept, text, script_name="", mod_name="", profile_root=None,
               account=None):
    """Write one generated script into a local mod, and register the mod.

    Reported 2026-11-10: 「这个生成的东西应该放local去」.  The three boxes on
    the script screen produced text and offered to overwrite a file the game
    ships; what a player wants instead is that the thing they just generated
    lands somewhere the engine loads it, without touching the game's own 53
    ``.per`` files.  That place is ``mods/local/<mod>/resources/_common/ai/``.

    Two writes, and both are needed: the script file (which is the point), and
    ``info.json`` plus a ``mod-status.json`` entry (without which the mod is
    invisible in the in-game list, and cannot be enabled or ordered).

    One file, one name.  Asked 2026-11-10: 「就像编辑器那些存的一样，默认放 local/mods
    里自建一个，后续改动也按原文件名一样就覆盖」 -- the same promise the editor's
    保存 makes with its remembered title.  The name is decided by the caller (and
    repeated by ``App.script_local_save`` when the box is empty), so a second
    press lands on the file the first one wrote; ``replaced`` in the reply says
    so.

    Raises ``ValueError`` carrying a sentence the screen can show.
    """
    from . import locations as LOC
    dept = (dept or "ai").strip().lower()
    if dept not in EXT:
        raise ValueError("生成的脚本只能放 .per 或 .xs，这个是 %r"
                         % (dept or "空"))
    body = text or ""
    if body.startswith("\ufeff"):
        body = body[1:]
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    data = body.encode("utf-8")
    if not data.strip():
        raise ValueError("正文是空的，没有东西可以放。先在框里生成，或者粘一段"
                         "脚本进来。")
    if len(data) > MAX_BYTES:
        raise ValueError("这份脚本有 %.1f MB，超过能写的 %.1f MB。"
                         % (len(data) / 1048576.0, MAX_BYTES / 1048576.0))

    stem = str(script_name or "").strip()
    if stem and os.path.splitext(stem)[1].lower() == EXT[dept]:
        stem = os.path.splitext(stem)[0]
    stem = _safe_name(stem, DEFAULT_SCRIPT[dept], 40)

    mod_dir, acc = local_mod_dir(profile_root, account, mod_name)
    mod = os.path.basename(mod_dir)
    sub = os.path.join(mod_dir, GAME_SUBDIR[dept])
    path = os.path.join(sub, stem + EXT[dept])

    os.makedirs(sub, exist_ok=True)
    # Same name, same file: pressing the button again updates the script that is
    # already there instead of stacking `我的AI.per`, `我的AI (2).per` and so on.
    # The reply says which of the two happened, because "saved" and "replaced"
    # are the same toast and the player cannot tell whether a target file was
    # overwritten (asked 2026-11-10: 「后续改动也按原文件名一样就覆盖」).
    replaced = os.path.isfile(path)
    tmp = path + ".tmp~"
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise ValueError("放不进 %s：%s" % (path, exc))

    # info.json: only ever created, never rewritten -- a folder the player (or
    # AGE) already set up keeps its own Title and Author.
    info_path = os.path.join(mod_dir, "info.json")
    created = not os.path.exists(info_path)
    if created:
        import json
        with open(info_path, "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(_local_info(mod), fh, ensure_ascii=False,
                      separators=(",", ":"))

    # The folder on disk is not enough for the in-game list: a local mod with no
    # entry is loaded by a later mod-manager pass but never appears in the list,
    # so it cannot be switched or ordered.  Appended, not inserted at 0, because
    # pushing every other mod's Priority down is a change the player did not ask
    # for.
    root = profile_root or LOC.find_profile_root()
    doc, acc, _raw = LOC.read_status_doc(root, account=acc)
    before = len(doc.get("Mods") or [])
    entry = LOC.upsert_mod_entry(doc, mod, kind="local", title=mod,
                                 enabled=True, position=before, move=False)
    bak = LOC.write_status_doc(acc, doc, backup=True)

    out = {
        "ok": True,
        "path": os.path.abspath(path),
        "rel": os.path.relpath(path, mod_dir).replace(os.sep, "/"),
        "dept": dept,
        "bytes": len(data),
        "name": stem + EXT[dept],
        "mod": mod,
        "mod_dir": os.path.abspath(mod_dir),
        "info_created": created,
        "replaced": replaced,
        "account": acc,
        "status_file": LOC.status_path(acc),
        "status_backup": bak,
        "priority": entry.get("Priority"),
        "enabled": bool(entry.get("Enabled")),
        "installed": True,
    }
    out.update(LOC.running_note())
    return out


def _writable(path):
    """True when this file can be written, tested without changing it."""
    try:
        with open(path, "ab"):
            pass
        return True
    except OSError:
        return False


def allowed_roots(game_root=None, profile_root=None, account=None):
    """The directories a save is permitted to touch, realpath'd.

    A save route that accepts any path is a file-write primitive; this list is
    the whole reason it does not become one.

    Local mods used to be deliberately absent here, on the reading that a mod is
    installed output.  Reported 2026-11-10: 「这个生成的东西应该放local去」 --
    a mod folder is not merely output, it is the one place a script the engine
    actually loads can live without colliding with the game's 53 shipped .per
    files, so refusing it meant the generated rule had nowhere to go.  Every
    mods/local/<name>/resources/_common/{ai,xs} folder is a save target now.
    What is still absent is every OTHER mod: a subscribed workshop mod is
    fetched again on every update, so editing one is editing a file that the
    next sync deletes.
    """
    out = []
    for _scope, _d, directory, _label in _roots(game_root, profile_root,
                                                account):
        out.append(os.path.normcase(os.path.realpath(directory)))
    return out


def check_save(path, game_root=None, profile_root=None, account=None,
               verb="写"):
    """``(abs_path, error)`` for a read or a save of one script file.

    Refuses, in this order: no path; not a ``.per``/``.ai``/``.xs``; outside the
    script folders (the game's two, the profile's two, and every local mod's
    two); a folder that does not exist yet is created (the profile's ``ai``
    folder is empty on this machine, so "save my first AI" would otherwise fail
    for a reason that reads like a bug).
    """
    if not path or not str(path).strip():
        return "", "没有说要写到哪个文件"
    p = os.path.abspath(str(path).strip())
    if dept_of(p) == "":
        return p, "只能%s .per、.ai 或 .xs 文件，这个不是：%s" % (
            verb, os.path.basename(p))
    real = os.path.normcase(os.path.realpath(p))
    dirs = allowed_roots(game_root, profile_root, account)
    inside = any(real.startswith(d + os.sep) for d in dirs)
    if not inside:
        return p, ("只能%s到游戏本体的 ai/ 、xs/ 目录、你档案里的同两个目录，"
                   "或者自己装的本地模组（mods/local/模组名/resources/_common/"
                   "ai 或 xs）里。%s 不在这些目录里——想放在别处，先在文件管理器"
                   "里把文件建好。" % (verb, p))
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        try:
            os.makedirs(d)
        except OSError as exc:
            return p, "建不了目录 %s：%s" % (d, exc)
    return p, None


def read(path, game_root=None, profile_root=None, account=None):
    """``(text, error)``.  Decodes UTF-8, then cp1252, then latin-1."""
    p, err = check_save(path, game_root, profile_root, account, verb="读")
    if err:
        return "", err
    if not os.path.isfile(p):
        return "", "这个文件还不存在：%s" % p
    size = os.path.getsize(p)
    if size > MAX_BYTES:
        return "", ("%s 有 %.1f MB，超过这个界面能打开的 %.1f MB。"
                    "用别的编辑器改它，或者先把它拆小。"
                    % (os.path.basename(p), size / 1048576.0,
                       MAX_BYTES / 1048576.0))
    with open(p, "rb") as fh:
        blob = fh.read()
    if blob[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = blob.decode("utf-16", "replace")
    else:
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                text = blob.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = blob.decode("latin-1", "replace")
    return text, None


def write(path, text, game_root=None, profile_root=None, account=None):
    """Write ``text`` as UTF-8, ``\\n`` endings, no BOM.  Returns ``(bytes, err)``.

    A BOM is stripped if the caller pasted one in, because the game's own parser
    rejects ``\\ufeff(defrule``.  ``\\r\\n`` is normalised to ``\\n`` for the same
    class of reason: the shipped scripts all end lines with a single ``\\n``, and
    a mixed file makes every later diff unreadable.
    """
    p, err = check_save(path, game_root, profile_root, account)
    if err:
        return 0, err
    body = (text or "")
    if body.startswith("\ufeff"):
        body = body[1:]
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    data = body.encode("utf-8")
    if len(data) > MAX_BYTES:
        return 0, ("这份脚本有 %.1f MB，超过能写的 %.1f MB。"
                   % (len(data) / 1048576.0, MAX_BYTES / 1048576.0))
    tmp = p + ".tmp~"
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        if os.path.exists(p):
            os.replace(tmp, p)
        else:
            os.rename(tmp, p)
    except OSError as exc:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return 0, "写不进 %s：%s" % (p, exc)
    return len(data), None

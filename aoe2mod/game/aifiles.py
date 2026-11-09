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


def _roots(game_root=None, profile_root=None, account=None):
    """``[(scope, dir, label)]`` for every folder a script may live in."""
    from . import locations as LOC
    out = []
    game_root = game_root or LOC.find_game_root()
    for dept, rel in (("ai", GAME_SUBDIR["ai"]), ("xs", GAME_SUBDIR["xs"])):
        out.append(("game", dept, os.path.join(game_root, rel), "游戏本体"))
    try:
        root = profile_root or LOC.find_profile_root()
        prof = LOC.pick_account(root, account)
        for dept, rel in (("ai", GAME_SUBDIR["ai"]), ("xs", GAME_SUBDIR["xs"])):
            out.append(("profile", dept, os.path.join(prof, rel), "我的档案"))
    except Exception:
        pass
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
    # The player's own files first: that is the folder that is nearly empty, and
    # the reason they asked.  Then the game's, which are usually read-only.
    out.sort(key=lambda e: (0 if e["scope"] == "profile" else 1, e["dept"],
                            e["rel"].lower()))
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
    the whole reason it does not become one.  Mods are deliberately absent: a
    mod's scripts are installed output, and a player editing them is editing
    something that the next install overwrites.
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
    four script folders; a folder that does not exist yet is created (the
    profile's ``ai`` folder is empty on this machine, so "save my first AI"
    would otherwise fail for a reason that reads like a bug).
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
        return p, ("只能%s到游戏的 ai/ 、xs/ 目录，或者你自己档案里的同两个目录。"
                   "%s 不在这些目录里——想放在别处，先在文件管理器里把文件建好。"
                   % (verb, p))
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

# -*- coding: utf-8 -*-
"""Emit an installable mod folder from a compiled .dat.

A mod is not a zip or an archive: it is a FOLDER whose name is the mod name and
which mirrors the game root directly.  Everything learned about that shape comes
from the shipped mods on this machine, and each rule below exists because a real
mod would break without it:

* The `info.json` sits at the mod ROOT, with `resources/` as a sibling -- there
  is no extra `resources/` wrapper.  A nested wrapper makes the mod fail
  silently.
* `info.json` is parsed with ``strict=False``.  Real published mods contain bare
  CR/LF control characters inside `Description`, which strict JSON rejects.
* Only `Author`, `CacheStatus`, `Description`, `Title` are required; the
  publisher adds the rest.
* Data and UI/texture content may live in ONE folder.  This docstring used to
  say they "must ship as SEPARATE mods", citing
  `IDS_MODMGR_DATAMOD_SCENARIO_WARNING` -- and that reading of the string was
  wrong.  Read on 2026-10-23 out of
  `resources/zh/strings/key-value/key-value-strings-utf8.txt`, it says
  「警告。您将加载一个带有非官方数据集的场景。」: it is about a SCENARIO that
  carries its own data set, not about a mod folder holding two kinds of file.
  Measured the same day: two shipped third-party mods
  (`310130_1233 For Stephen Chow`, `445153_4X科技 …`) each put a `.dat` and
  text tables in one folder, and this project's own `dsh test v49` -- a `.dat`
  plus 17 locale string tables in a single folder -- was verified in game.
  So the manifest now reports which layers a folder carries instead of
  asserting a policy nothing follows.
* There is no central manifest: a mod wins by providing the same relative path
  as the base game, ordered by `Priority` in `mod-status.json`.
"""
import hashlib
import json
import os
import shutil
import zlib

from ..dat import parser as P

# The storage point a data mod writes, relative to the mod root.  This is the
# path INSIDE the mod folder, not inside the game.
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

# The DAT storage point as a PREFIX.  A mod that writes ANY file under here may
# have to carry the `.dat` itself -- see `annotate_dat_storage_point` below, which
# records the evidence and the reasoning.
DAT_STORAGE_REL = os.path.join("resources", "_common", "dat")

INFO_REQUIRED = ("Author", "CacheStatus", "Description", "Title")

# ★★★ The engine truncates a mod Title at 100 UTF-8 BYTES, and derives the
# folder `Path` recorded in `mod-status.json` from that TRUNCATED title.
# Measured 2026-10-16: a shipped mod title of 103 bytes came back as
#
#     local//dsh test v6 ...去掉EnablingResearch      <- final `）` (3 bytes) cut
#
# and the folder the engine then looked for did not exist, so the mod appeared
# in `MainLog.txt` as "Enabling mod #0 (...)" and yet had NO effect.  A title of
# 89 bytes worked.  The mod list shows the folder name, so the limit applies to
# the Title, not to the Description (a shipped mod carries 554 bytes of that).
TITLE_MAX_BYTES = 100


def title_bytes(title):
    """The length the engine measures a Title in -- UTF-8 bytes, not characters."""
    return len((title or "").encode("utf-8"))


def _fit_title(title, limit=TITLE_MAX_BYTES):
    """Cut a Title to `limit` UTF-8 bytes without splitting a character.

    Cutting mid-character would leave an invalid fragment, which is worse than a
    short title, so this walks characters and then prefers a phrase boundary.
    """
    if title_bytes(title) <= limit:
        return title
    out = ""
    for ch in title:
        if title_bytes(out + ch) > limit:
            break
        out += ch
    for sep in ("（", "(", " ", "·", "｜", "+"):
        i = out.rfind(sep)
        if i > limit // 4:
            out = out[:i].rstrip()
            break
    return out
INFO_OPTIONAL = ("Unpublished", "thumbnail", "previewIcon", "mainmenu_bg.dds")


#: Characters the publisher forbids in a Title, because the Title becomes a
#: folder name.  A sentence can carry a path ("给村民换张图 D:\pics\a.png"),
#: and the page joins sentences into the title, so an auto title can contain
#: `:` and `\` without the player ever typing a title.
BANNED_TITLE_CHARS = '<>:"/\\|?*'


def fit_auto_title(title, limit=TITLE_MAX_BYTES):
    """Make the page's auto-written title legal: drop forbidden characters, fit.

    Only for a title the PAGE wrote.  A title the player typed goes through
    `validate_info` instead and is refused with a sentence -- silently
    shortening text someone wrote by hand is a different act, and a wrapper
    that quietly did it to both would blur the two.

    Two rules apply here and they are not the same rule: banned characters
    (the Title becomes a folder name) and the byte cap (`_fit_title`).

    A path is dropped whole rather than picked clean: "给村民换张图
    D:\\pics\\a.png" would otherwise become "给村民换张图 Dpicsa.png", which is
    not a title anyone can read.
    """
    words = []
    for tok in (title or "").split():
        if any(ch in BANNED_TITLE_CHARS for ch in tok) or "\\" in tok or "/" in tok:
            continue                      # a path, not a word the player typed
        words.append(tok)
    t = " ".join(words)
    t = "".join(ch for ch in t if ch not in BANNED_TITLE_CHARS)
    return _fit_title(t.strip(), limit)


def _rel_is_under_dat_storage(rel):
    """Is this mod-relative path inside the DAT storage point?"""
    n = rel.replace("\\", "/").lower()
    prefix = DAT_STORAGE_REL.replace("\\", "/").lower()
    return n == prefix or n.startswith(prefix + "/")


def dat_storage_point_files(json_files):
    """The JSON overrides that live INSIDE the DAT storage point.

    Paths are returned with forward slashes, matching ``json_overrides`` -- the
    caller may hand these in either separator, and a manifest that reported the
    same file two different ways would invite a string comparison bug downstream.
    """
    return sorted(r.replace(os.sep, "/").replace("\\", "/")
                  for r in (json_files or {}) if _rel_is_under_dat_storage(r))


def emit_json_mod(mod_dir, json_files, info, thumbnail=None, base_dir=None,
                  overwrite=False):
    """Write a mod that changes ONLY the dat-adjacent JSON layer.

    A per-civ availability change ("let the Britons build Huskars") touches no
    `.dat` byte at all: the authority is
    `resources/_common/dat/CivTechTrees/<CIV>.json` (see `game/civtechtrees.py`).
    Shipping the `.dat` anyway would be actively harmful -- the emitted `.dat`
    would be byte-identical to the base game, so the mod would carry 12 MB of
    nothing, and the game's own publisher warns about data mods that change
    nothing.

    ``json_files`` is ``{relative_path: bytes}``; the bytes must come from
    ``civtechtrees.serialize`` because the engine escapes an apostrophe as
    ``\\u0027`` and a naive ``json.dump`` does not.

    This is a thin wrapper over :func:`emit_data_mod`: one emitter, two entry
    points, so the path-traversal, overwrite, redundancy and manifest rules can
    never drift apart.
    """
    if not json_files:
        raise ModError("没有任何文件要写进模组：一个什么都不改的模组没有意义")
    return emit_data_mod(mod_dir, None, info, thumbnail=thumbnail,
                         base_dir=base_dir, overwrite=overwrite,
                         json_files=json_files)


def deflate_raw(raw, level=6):
    """Compress exactly the way the shipped .dat is compressed.

    The game stores `empires2_x2_p1.dat` as a bare deflate stream (no zlib
    header), so a mod's replacement must be compressed too -- writing the raw
    stream would produce a file the engine cannot open.  Note that compression
    is NOT byte-reproducible, so the emitted file is always verified by
    re-inflating and re-parsing, never by re-compressing and comparing.
    """
    comp = zlib.compressobj(level, zlib.DEFLATED, -15)
    return comp.compress(raw) + comp.flush()


class ModError(Exception):
    """The mod cannot be emitted.  The message is user-facing."""


#: How `validate_info` says an info.json field to a player.  The raw key is an
#: internal name: the screen renders these sentences next to 做成 mod, so
#: "Title must be a non-empty string" would be an internal note shown to a
#: player.  Every other refusal in this project already speaks Chinese; this
#: table is what keeps the info.json ones from being the exception.
_INFO_KEY_ZH = {
    "Title": "标题",
    "Author": "作者",
    "CacheStatus": "缓存标记",
    "Description": "说明文字",
}


def read_info_json(path):
    """Read a shipped info.json the way the game does."""
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig")
    try:
        return json.loads(text)
    except ValueError:
        # Shipped mods carry bare control characters in Description.
        return json.loads(text, strict=False)


def validate_info(info):
    """Return a list of human-readable problems; empty means publishable."""
    problems = []
    if not isinstance(info, dict):
        return ["info.json 里应该是一个 JSON 对象。"]
    for key in INFO_REQUIRED:
        if key not in info:
            problems.append("info.json 少了必须的「%s」。"
                            % _INFO_KEY_ZH.get(key, key))
    for key in ("Title", "Author"):
        v = info.get(key)
        if key in info and (not isinstance(v, str) or not v.strip()):
            # `_INFO_KEY_ZH` rather than the raw key: this sentence is rendered
            # on the screen next to the build button.
            problems.append("%s不能是空的。" % _INFO_KEY_ZH.get(key, key))
    title = info.get("Title")
    if isinstance(title, str):
        banned = set('<>:"/\\|?*')
        bad = sorted(banned & set(title))
        if bad:
            # Reaches the player on the screen: a sentence that carries a file
            # path ("给村民换张图 D:\pics\a.png") lands in the auto-title as a
            # colon and a backslash.  Say which characters, in Chinese, and say
            # that the title is the one thing that cannot hold them.
            problems.append(
                "标题里有引擎不允许的字符：%s。标题会被当作文件夹名，所以这些字符"
                "不能出现；说明文字可以随便写。把标题里的这些字符去掉就行。"
                % " ".join(bad))
        # ★★★ The engine cuts the Title at 100 UTF-8 bytes and then looks for a
        # folder of that cut name -- so an over-long title produces a mod that is
        # "enabled" in the log and silently does nothing.  Refuse rather than ship
        # a mod that cannot load; `_fit_title` is the fix.
        #
        # This sentence reaches the player: the screen builds the title by
        # joining the sentences they typed, so a run of Chinese can push it past
        # 100 bytes (3 bytes per character), and the refusal is rendered next to
        # the button they just pressed.  So it says what to do, in Chinese, and
        # names the number the engine uses.  The page's own titles are fitted
        # before they get here (`/api/build` -> `fit_auto_title`), which is why
        # this one only fires on a title the player typed.
        if title_bytes(title) > TITLE_MAX_BYTES:
            problems.append(
                "标题太长：现在是 %d 字节，而引擎在 %d 字节处截断标题、再拿截断后"
                "的名字去找文件夹，所以这样的模组会显示为已启用却什么都不改。"
                "把这个标题改短一点（大约 %d 个汉字以内；说明文字可以任意长）。"
                % (title_bytes(title), TITLE_MAX_BYTES, TITLE_MAX_BYTES // 3))
    return problems


def make_info(title, author="", description="", cache_status=0, **extra):
    """Build an info.json payload with the four required keys."""
    info = {
        "Author": author,
        "CacheStatus": cache_status,
        "Description": description,
        "Title": title,
    }
    for k, v in extra.items():
        if v is not None:
            info[k] = v
    return info


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def emit_data_mod(mod_dir, dat_bytes, info, thumbnail=None, base_dir=None,
                  overwrite=False, json_files=None):
    """Write a complete, installable data mod folder.

    ``dat_bytes`` is the RAW (uncompressed) .dat stream.  It is deflated on the
    way out, because that is how the game stores and expects it.

    ``json_files`` is an optional ``{relative_path: bytes}`` mapping for the
    dat-adjacent JSON layer -- most importantly
    ``resources/_common/dat/CivTechTrees/<CIV>.json``, which is the ONLY place
    per-civ availability can be changed (see ``game/civtechtrees.py``).  The bytes
    must come from ``civtechtrees.serialize``; this function does not serialise
    JSON itself, because the engine's escaping rule (``'`` written as ``\\u0027``)
    is not what a naive ``json.dump`` produces and a near-match would show up as a
    diff nobody asked for.

    ``dat_bytes`` may be ``None`` when the intent changes no `.dat` byte.  That is
    the natural shape for a JSON-layer change, BUT it is unsafe for files written
    inside the DAT storage point: a mod that puts `CivTechTrees/<CIV>.json` or
    `futuravailableunits.json` under `resources/_common/dat/` without also carrying
    `empires2_x2_p1.dat` makes the GAME FAIL TO START.  Evidence:

      * the user reported exactly that, twice and in game -- first as a popup with
        an empty file name, then as the same intent succeeding once the `.dat` was
        added;
      * every third-party mod on this machine that writes under
        `resources/_common/dat/` also carries the `.dat` (5 of 5), and the only
        copy without one is this project's own JSON-only test
        (`_probe/probe_dat_only_defect.py`);
      * the DAT storage point is the ONLY one flagged
        `use_modes_path_for_mods: true` in `modes/Pompeii/Pompeii.json`, so the
        engine may resolve that directory as a unit rather than per file.

    So when ``json_files`` reaches into the DAT storage point and ``dat_bytes`` is
    ``None``, the base `.dat` is copied in as a CARRIER (unmodified) and the
    manifest says so.  Passing ``base_dir`` is what makes that possible; without it
    the call is refused rather than silently producing an unstartable mod.

    Returns a manifest dict describing exactly what landed on disk.
    """
    problems = validate_info(info)
    if problems:
        # Player-facing: `/api/build` puts this message on the screen.  Prefix
        # says what to do; the problems themselves already speak Chinese.
        raise ModError("这个 mod 的信息填得不对，游戏不会认："
                       + " ".join(problems))
    if dat_bytes is None and not json_files:
        # Reachable from the screen only if the caller could not name WHY nothing
        # was produced (the bundle path now names the refused sentences before it
        # gets here).  Kept Chinese anyway: a fallback that speaks English is the
        # same defect one branch later.
        raise ModError("没有东西可以做成模组：既没有一个 .dat，也没有任何要覆盖的文件，"
                       "这样做出来的模组什么都不会改")

    # --- the DAT-storage-point carrier rule ------------------------------
    dat_carrier = False
    _into_dat = dat_storage_point_files(json_files)
    if _into_dat and dat_bytes is None:
        if not base_dir:
            raise ModError(
                "这个模组要往 %s 里写文件，却没有带上 empires2_x2_p1.dat；"
                "游戏会直接开不了局。调用时传 base_dir，让它把本机那份 .dat "
                "原样带过去。" % "、".join(_into_dat))
        _base_dat = os.path.join(base_dir, DAT_REL)
        if not os.path.exists(_base_dat):
            raise ModError(
                "这个模组要往 %s 里写文件，却没有带上 empires2_x2_p1.dat；"
                "而且在 %s 也找不到可以原样带过去的那份 .dat。"
                % ("、".join(_into_dat), _base_dat))
        dat_bytes, _how = P.load_dat(_base_dat)
        dat_carrier = True

    if os.path.exists(mod_dir):
        if not overwrite:
            # Refuse rather than merge: silently adding to an existing folder is
            # how a user ends up shipping someone else's files.
            if os.listdir(mod_dir):
                # The page always passes overwrite=True, so this is not the route
                # a player takes -- but it is one API call away, and a refusal
                # that speaks English is the same defect however it is reached.
                raise ModError("这个模组文件夹已经存在，里面还有别的东西：%s。"
                               "要整个换掉的话，调用时带上 overwrite=True。" % mod_dir)
        else:
            # ★ A rebuild must be a REPLACEMENT, not a merge.  Measured
            # 2026-10-23: a build that put a texture at the wrong relative path
            # was fixed and rebuilt into the same folder with overwrite=True, and
            # the stale copy at the old path was still there afterwards -- a mod
            # that ships two copies of the same picture in two places, one of
            # them unreachable, and nothing in the manifest says so.  The old
            # files are also the only thing that can make "which build is
            # installed" ambiguous.
            shutil.rmtree(mod_dir, ignore_errors=True)

    dat_abs = None
    blob = None
    if dat_bytes is not None:
        dat_abs = os.path.join(mod_dir, DAT_REL)
        os.makedirs(os.path.dirname(dat_abs), exist_ok=True)
        blob = deflate_raw(dat_bytes)
        with open(dat_abs, "wb") as fh:
            fh.write(blob)
    else:
        # A JSON-only mod never touches the .dat path, so nothing above created
        # the folder -- and `open(info.json)` then failed with FileNotFoundError.
        # The mod root must exist regardless of which layer is being changed.
        os.makedirs(mod_dir, exist_ok=True)

    written = []

    info_abs = os.path.join(mod_dir, "info.json")
    # COMPACT, exactly like every mod the game ships and accepts.  Measured: all 8
    # third-party mods on this machine write `{"Author":"x","CacheStatus":0,...}` with
    # NO space after the colon, while an `indent=2` file is the only one the mod
    # manager's validation pass fails to read -- it then shows `作者: Unpublished` and
    # `No Description` in the detail panel (`Unpublished` / `No Description` are the
    # engine's own fallbacks, found adjacent to `info.json` and `Validating '%s'` in
    # the exe's string pool).  Note it is NOT about newlines: an accepted mod
    # (`423821_…`, 748 B) contains seven CRs, all inside the Description VALUE.
    with open(info_abs, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(info, fh, ensure_ascii=False, separators=(",", ":"))
    written.append(("info.json", info_abs))

    thumb_abs = None
    if thumbnail:
        if not os.path.exists(thumbnail):
            raise ModError("找不到缩略图：%r" % thumbnail)
        # The publisher only accepts PNG for images.
        if os.path.splitext(thumbnail)[1].lower() not in (".png", ".jpg", ".jpeg"):
            raise ModError("缩略图只能是 PNG 或 JPEG，收到的是 %r"
                           % os.path.basename(thumbnail))
        ext = os.path.splitext(thumbnail)[1].lower()
        target = os.path.join(mod_dir, "thumbnail" + (".jpg" if ext in (".jpg", ".jpeg") else ".png"))
        with open(thumbnail, "rb") as src, open(target, "wb") as dst:
            dst.write(src.read())
        thumb_abs = target
        written.append(("thumbnail", target))

    manifest = {
        "mod_dir": mod_dir,
        "info": info,
        "dat": dat_abs,
        "dat_raw_bytes": len(dat_bytes) if dat_bytes is not None else 0,
        "dat_file_bytes": len(blob) if blob is not None else 0,
        "dat_sha256": (hashlib.sha256(dat_bytes).hexdigest()
                       if dat_bytes is not None else None),
        # True when the `.dat` is present only so that a JSON file may live under
        # the DAT storage point.  The game refuses to start when a mod overrides
        # that folder without it, so the copy is mandatory even though it is
        # byte-identical to the base game -- and the redundancy warning below must
        # not read as "this mod changes nothing".
        "dat_is_carrier": dat_carrier,
        "dat_storage_point_json": (dat_storage_point_files(json_files) or None),
        "thumbnail": thumb_abs,
        "files": [{"rel": "info.json", "bytes": os.path.getsize(info_abs)}],
    }
    if dat_abs is not None:
        manifest["files"].append({
            "rel": DAT_REL.replace(os.sep, "/"),
            "bytes": os.path.getsize(dat_abs),
        })
    # Say it explicitly, in BOTH cases: a caller comparing manifests must be able
    # to tell "no .dat byte was changed" from "a .dat was written and I forgot to
    # report it".  A carrier `.dat` is on disk but changes nothing, so this stays
    # False -- that is the distinction the tests and the UI need.
    manifest["changes_dat"] = False if dat_carrier else (dat_bytes is not None)
    if thumb_abs:
        manifest["files"].append({
            "rel": os.path.basename(thumb_abs),
            "bytes": os.path.getsize(thumb_abs),
        })

    # The dat-adjacent JSON layer.  Which files a mod may override is settled by
    # measurement, not assumption: `resources/_common/dat/` is overriding-able by
    # real published mods (550749 and 551103 both ship `linkedTechs.json`), and
    # overrides resolve at nested paths inside a storage point (550 of the
    # installed mod files sit 2-4 levels under `widgetui/`).  `CivTechTrees/` is
    # therefore reachable by the same lookup -- though no mod on this machine has
    # ever been observed shipping it, so treat that last step as evidenced
    # inference rather than an in-game observation.
    if json_files:
        for rel, data in sorted(json_files.items()):
            rel_n = rel.replace("/", os.sep)
            abs_path = os.path.join(mod_dir, rel_n)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if isinstance(data, str):
                data = data.encode("utf-8")
            with open(abs_path, "wb") as fh:
                fh.write(data)
            written.append((rel_n, abs_path))
            manifest["files"].append({
                "rel": rel_n.replace(os.sep, "/"),
                "bytes": os.path.getsize(abs_path),
            })
        manifest["json_overrides"] = sorted(
            r.replace(os.sep, "/") for r in json_files)

    # Which layers this ONE folder actually carries.  Computed from the files on
    # disk rather than declared, because the old field here asserted a policy
    # (`deliver_data_and_ui_as_separate_mods: True`) that the emitter itself did
    # not follow: a bundle with a `.dat` edit and a `unit.sprite` sentence ships
    # 93 MB of `.dat` next to 20 `.sld` files in one folder, measured 2026-10-23.
    # A manifest field nobody reads AND that describes the opposite of what
    # happened is worse than no field: the next reader trusts it.
    _rels = [f["rel"] for f in manifest["files"]]
    _layers = []
    if any(r.endswith(".dat") for r in _rels):
        _layers.append("dat")
    if any(r.endswith(".sld") for r in _rels):
        _layers.append("sld")
    if any("/strings/key-value/" in r for r in _rels):
        _layers.append("strings")
    if any(r.startswith("resources/_common/wpfg/") for r in _rels):
        _layers.append("wpfg")
    # JSON is judged from the FILES, not from `json_overrides`: that dict is the
    # generic loose-file bin, so a reskin's 20 `.sld` paths land in it and the
    # folder would be reported as carrying a "json" layer it does not have
    # (measured 2026-10-23: `layers` came back `['dat', 'sld', 'json']` for a
    # build whose only non-dat files were `.sld`).
    # `info.json` is the manifest of the folder itself, not an override of a game
    # file, so it never counts -- otherwise EVERY build carries a "json" layer.
    if any(r.endswith(".json") and r != "info.json" for r in _rels):
        _layers.append("json")
    if thumb_abs:
        _layers.append("thumbnail")
    manifest["layers"] = _layers
    # More than one data-ish layer means this folder mixes them, which the game
    # allows but which makes "which mod is the data mod" ambiguous at selection
    # time.  Say it; do not refuse it (measured: shipped mods do it too).
    #
    # A CARRIER `.dat` does not count here: it is there because the JSON needs the
    # folder, it changes no byte, and it already has its own warning.  Counting it
    # would tell every JSON-only build that its folder "carries several layers",
    # which is noise on top of a true sentence.
    _mixing = [l for l in _layers
               if l in ("strings", "wpfg", "sld", "json")
               or (l == "dat" and not dat_carrier)]
    if len(_mixing) > 1:
        manifest.setdefault("warnings", []).append(
            "这一个模组文件夹同时带了 %s 这几层。游戏允许这样做（本机就有第三方"
            "模组这么发货），但在「数据模组：」下拉框里它只算一个数据模组，"
            "所以要和别的数据模组一起用时只能选它一个。" % "、".join(_mixing))

    # A redundant copy is a real defect: the shipped mods contain files that are
    # byte-identical to the base game, which wastes space and hides the change.
    # The base .dat on disk is compressed, so compare RAW streams -- hashing the
    # two files directly would never match.
    if base_dir:
        base_dat = os.path.join(base_dir, DAT_REL)
        if dat_bytes is not None and os.path.exists(base_dat):
            try:
                base_raw, _ = P.load_dat(base_dat)
            except Exception:
                base_raw = None
            if base_raw is not None:
                same = base_raw == dat_bytes
                manifest["dat_identical_to_base"] = same
                if same and dat_carrier:
                    # The `.dat` is here on purpose: the JSON files that need it
                    # live inside the DAT storage point, and the game will not
                    # start if that folder is overridden without its .dat.  Report
                    # it as a carrier, NOT as "this mod changes nothing" -- the
                    # mod DOES change the JSON files listed alongside it.
                    # APPEND, do not assign: the layer warning above was written
                    # by this same call, and an assignment silently replaced it
                    # (measured: `layers` said the folder carried two layers while
                    # `warnings` said nothing about it).
                    manifest.setdefault("warnings", []).append(
                        "这个 mod 要往 %s 里写文件，所以 .dat 被原样带了一份"
                        "（没改）：游戏不允许只覆盖那个文件夹而不带 .dat，"
                        "否则开局就失败。真正的改动在旁边的 JSON 里。"
                        % "、".join(dat_storage_point_files(json_files)
                                    or ["(none)"]))
                elif same:
                    manifest["warnings"] = [
                        "这份 .dat 和出厂那份逐字节相同，所以这个 mod 什么都没改"]
                    # `changes_dat` was set above from "a .dat was handed in", but
                    # the whole point of that field is whether a byte changed.  An
                    # audit measured the two disagreeing: a build whose .dat is
                    # byte-identical to the base ended up carrying
                    # `changes_dat: True` next to this warning.  Correct it here,
                    # where the base comparison actually happened.
                    manifest["changes_dat"] = False

        # Same redundancy check for the JSON layer.  A JSON override that is
        # byte-identical to the shipped file is not harmless: it pins that file
        # to today's content, so a later game patch that updates it would be
        # silently reverted by this mod.  That is a real, reported class of mod
        # breakage, and it is only detectable at emit time.
        if json_files:
            redundant = []
            for rel in sorted(json_files):
                data = json_files[rel]
                if isinstance(data, str):
                    data = data.encode("utf-8")
                base_file = os.path.join(base_dir, rel.replace("/", os.sep))
                if not os.path.exists(base_file):
                    continue
                with open(base_file, "rb") as fh:
                    if fh.read() == data:
                        redundant.append(rel.replace(os.sep, "/"))
            if redundant:
                manifest["json_identical_to_base"] = redundant
                manifest.setdefault("warnings", []).append(
                    "有 %d 个 JSON 覆盖文件和本机那份逐字节相同，这等于把这个文件"
                    "钉在今天的内容上：以后游戏更新它时，这个模组会把它悄悄改回去。"
                    "要改就改出真实差异，不改就别把它放进模组：%s"
                    % (len(redundant), "、".join(redundant)))
    return manifest

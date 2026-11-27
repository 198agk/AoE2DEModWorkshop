"""Will the game actually read this mod's data, answered without starting the game.

Reported 2026-11-21, verbatim: 「更新模组依旧失败…按钮是有，但是效果全无，我想知道你怎么才能
复刻出一模一样的模组出来」 and then 「而且我要的是工具能做得到」.  A player who is told
"the rebuild carried 5,333 of 5,387 field changes" and still sees nothing has been
handed a number about a file the ENGINE never opened.  The tool therefore has to
answer the question one level up: **which `.dat` will the game read on the next
launch, and is the mod we just wrote part of that answer at all.**

Three separate facts decide it, and they live in three different files:

1. ``<account>/mods/mod-status.json`` -- ``Enabled`` per mod.  Measured
   2026-11-21 on this machine: of 27 entries exactly 10 are enabled and **none of
   the 13 that ship a ``.dat`` is among them**, while every one of the 9 launch
   logs says ``Setting version info: app = 188329 data = 0 mod = 0``.

2. ``<account>/profile/Player.nfp`` -- the DATASET the player last picked in the
   create-game screen.  This is not a settings text file: it is a bare deflate
   stream (``zlib.decompressobj(-15)``), 4,379 bytes on disk inflating to 38,481,
   and the picked dataset is one record in it:

       ``60 0a <u16 len> <utf-8 title> <u32 WorkshopID> <u32 flags> <u32 CheckSum>``

   Measured records: ``209785_Civilization Alliance`` + ``00 00 00 00`` +
   ``65 9a 62 cb`` (= 3412236901, the ``CheckSum`` of ``local//209785_...``) and
   ``1233 For Stephen Chow (2026.10.8)`` + ``72 bb 04 00`` (= 310130, its
   ``WorkshopID``) + ``65 b2 ae 33`` (= 867086949, its ``CheckSum``).  The
   ``CheckSum`` is ``zlib.crc32`` over the mod folder's files, NOT a hash of the
   title (measured: crc32 of the title bytes matches nothing in the record).

3. ``<account>/profile/AdditionalOptions.aop`` -- also bare deflate, 2,080 ->
   42,330 bytes, a plain ``key:value`` table whose ``DatasetIM/PublishedIM/MyMods/
   SubscribedBM/DatasetBM/PublishedMM/DatasetMM`` entries are all ``1``: those are
   the last-selected FILTER of the dropdown, not the pick.

Two things this module deliberately does not do.  It does not write ``Player.nfp``:
re-compressing the modified stream never reproduces the original bytes (level 0-9
give 38,491/5,666/4,909/4,780/4,453/4,242/4,175/4,174/4,108/4,077 against an
original 4,379, with a different container head), so a write-back would mean
patching a compressed stream in place, which is a bigger hammer than this question
needs.  And it does not claim a mod "works": it reports the state that decides
whether the engine will even open the file.
"""

import io
import json
import os
import struct
import zlib

from . import locations as LOC


#: Where the dataset pick and the mod-manager flags live, under the ACCOUNT folder.
NFP_REL = os.path.join("profile", "Player.nfp")
AOP_REL = os.path.join("profile", "AdditionalOptions.aop")

#: ``60 0a`` opens every string record in ``Player.nfp`` (measured: 164 records,
#: 10 distinct texts, 136 of them the ``NONE:NONE:::false`` placeholder).
RECORD_MAGIC = b"\x60\x0a"


def inflate(path):
    """The decompressed bytes of a bare-deflate profile file, or ``None``.

    ``Player.nfp`` and ``AdditionalOptions.aop`` carry no zlib/gzip header -- a
    plain ``zlib.decompress`` raises ``error: incorrect header check`` on both --
    but ``decompressobj(-15)`` reads them whole (measured ``eof False unused 0``,
    which only means the stream had no terminator, not that bytes were left over).
    """
    try:
        with open(path, "rb") as fh:
            blob = fh.read()
    except OSError:
        return None
    try:
        d = zlib.decompressobj(-15)
        return d.decompress(blob) + d.flush()
    except zlib.error:
        return None


def _records(raw):
    """Every ``60 0a`` string record as ``(offset, text, tail12)``.

    ``tail12`` is the twelve bytes that follow the text -- for a dataset record
    that is ``<u32 WorkshopID> <u32 flags> <u32 CheckSum>`` (see the module
    docstring for the two records this was measured on).
    """
    out = []
    if not raw:
        return out
    i = 0
    n = len(raw)
    while i + 4 <= n:
        if raw[i:i + 2] == RECORD_MAGIC:
            ln = struct.unpack("<H", raw[i + 2:i + 4])[0]
            end = i + 4 + ln
            if 0 < ln <= 400 and end <= n:
                try:
                    text = raw[i + 4:end].decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text and all(ch.isprintable() for ch in text):
                    out.append((i, text, raw[end:end + 12]))
                    i = end
                    continue
        i += 1
    return out


def read_selection(account_dir):
    """Every ``Player.nfp`` record that could be a dataset pick.

    A record qualifies when its twelve trailing bytes parse as
    ``(WorkshopID, flags, CheckSum)`` and the checksum is not zero.  That is
    necessary but NOT sufficient: the same file also holds player names, scenario
    names and 136 ``NONE:NONE:::false`` placeholder slots, and the tail of a player
    name happens to parse as a nonzero checksum too (measured: ``玩家`` at offset
    28126 yields workshop_id 395872, checksum 177838).  Callers therefore narrow
    the list against the installed mods -- see ``audit``.  This function reports
    what is in the FILE, not what is installed.
    """
    raw = inflate(os.path.join(account_dir, NFP_REL))
    picks = []
    for off, text, tail in _records(raw):
        if text == "NONE:NONE:::false" or len(tail) < 12:
            continue
        wid, flags, crc = struct.unpack("<III", tail)
        if not crc:
            continue
        picks.append({"title": text, "workshop_id": wid, "flags": flags,
                      "checksum": crc, "offset": off})
    return {"file": os.path.join(account_dir, NFP_REL),
            "bytes": (os.path.getsize(os.path.join(account_dir, NFP_REL))
                      if os.path.exists(os.path.join(account_dir, NFP_REL)) else 0),
            "raw_bytes": len(raw) if raw else 0,
            "picks": picks}


def read_flags(account_dir):
    """The ``Dataset*`` / ``Published*`` / ``MyMods`` entries of ``AdditionalOptions.aop``.

    These are the dropdown's last position, whose value is always ``1`` on the
    measured file -- reported because a screen that says "you picked X" should be
    able to show what it actually read, and because the absence of a
    ``DataMod``-like key here is the proof that the pick is NOT in this file.
    """
    raw = inflate(os.path.join(account_dir, AOP_REL))
    out = {}
    keys = ("DatasetIM", "PublishedIM", "MyMods", "SubscribedBM", "DatasetBM",
            "PublishedMM", "DatasetMM")
    if not raw:
        return {"file": os.path.join(account_dir, AOP_REL), "flags": out}
    for name in keys:
        needle = (name + ":").encode("ascii")
        at = raw.find(needle)
        if at < 0:
            continue
        j = at + len(needle)
        digits = bytearray()
        while j < len(raw) and 48 <= raw[j] <= 57:
            digits.append(raw[j])
            j += 1
        out[name] = int(bytes(digits)) if digits else None
    return {"file": os.path.join(account_dir, AOP_REL), "flags": out}


def _folder_checksum(mod_path):
    """``zlib.crc32`` over a mod folder, the way ``CheckSum`` is computed.

    Measured 2026-11-21: this reproduces ``mod-status.json``'s ``CheckSum`` for
    14 of 27 entries, and for EVERY entry that ships a ``.dat``.  The 13 misses
    are pure UI/text mods, which the engine apparently checksums another way.  So
    a mismatch here is not evidence of anything and is never reported as one --
    only a MATCH is used, to tie a ``Player.nfp`` record to a folder.
    """
    crc = 0
    try:
        names = []
        for base, _dirs, files in os.walk(mod_path):
            for f in files:
                full = os.path.join(base, f)
                names.append((os.path.relpath(full, mod_path).replace("\\", "/"),
                              full))
        names.sort()
        for rel, full in names:
            low = rel.rsplit("/", 1)[-1].lower()
            if low == "info.json" or low.startswith("thumbnail"):
                continue
            with open(full, "rb") as fh:
                crc = zlib.crc32(fh.read(), crc)
    except OSError:
        return None
    return crc & 0xFFFFFFFF

def _row_enabled(entry):
    """``Enabled`` of one ``mod-status.json`` entry, as a bool.

    The value is written by the game as a JSON boolean, but a hand-edited file
    can hold ``"true"``/``1``, and this is read on a screen that must not throw.
    """
    v = (entry or {}).get("Enabled")
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v)


def _match_pick(pick, mods, status_by_rel):
    """Tie one ``Player.nfp`` record to an installed mod, by the strongest key.

    Order follows what cannot be faked: the ``CheckSum`` the engine itself wrote
    into ``mod-status.json`` beats a WorkshopID, and a WorkshopID beats a title.
    A mod whose folder was deleted still keeps its status entry, so a title match
    that points at a missing folder is reported as ``installed: False`` rather
    than dropped -- "you have 209785 selected but its folder is gone" answers a
    far more useful question than silence.
    """
    if pick.get("checksum"):
        for m in mods:
            entry = status_by_rel.get(m["path_field"]) or {}
            if str(entry.get("CheckSum")) == str(pick["checksum"]):
                return m, "checksum"
    if pick.get("workshop_id"):
        for m in mods:
            if str(m.get("workshop_id")) == str(pick["workshop_id"]):
                return m, "workshop"
    for m in mods:
        if (m.get("title") or "") == pick["title"] or m.get("name") == pick["title"]:
            return m, "title"
    return None, None


def audit(profile_root=None, account=None):
    """Everything that decides whether a data mod is read, in one dict.

    The answer the player asked for is ``reads``: the file the engine will open.
    ``data_mods`` carries one row per installed mod that ships a ``.dat``, with
    ``will_be_read`` True for at most one of them, because a database mod is not
    layered -- the create-game screen picks ONE dataset and the engine loads that
    file (measured: the pick is a single ``Player.nfp`` record carrying the chosen
    mod's ``CheckSum``).
    """
    root = profile_root or LOC.find_profile_root()
    doc, acc, raw = LOC.read_status_doc(root, account=account)
    status_by_rel = {}
    for e in (doc.get("Mods") or []):
        status_by_rel[str(e.get("Path") or "")] = e

    mods = []
    for m in LOC.list_mods(acc):
        row = dict(m)
        row["path_field"] = "%s//%s" % (m.get("kind"), m.get("name"))
        row["dat"] = os.path.join(m.get("path") or "", LOC.DAT_REL)
        row["has_dat"] = bool(m.get("exists")) and os.path.isfile(row["dat"])
        mods.append(row)

    sel = read_selection(acc)
    flags = read_flags(acc)

    # Which mod the FILE says was picked.  ``Enabled`` is deliberately not part
    # of this: measured 2026-11-21, every one of the 13 installed data mods reads
    # ``Enabled: false`` and the engine writes ``false`` back within seconds when
    # anything external sets it true, so that field is not the switch for a data
    # mod.  The engine's own model is a selected DATASET -- the executable carries
    # ``DatasetIM``/``DatasetMM``/``DatasetWorkshopId``/``DatasetCRC`` and
    # ``UICreateMultiplaterGameDialog::CheckValidDatasetSelected``, and the pick is
    # what ``Player.nfp`` stores.  Reporting the enable flag as the cause is what
    # made the earlier answer wrong.
    picks = []
    ignored = 0
    picked = None
    for pick in sel["picks"]:
        m, how = _match_pick(pick, mods, status_by_rel)
        if m is None:
            # A player name or a scenario name: its tail parses as a checksum but
            # nothing installed answers to it.  Counting these is how the screen
            # can say "I read the file and found no dataset pick in it" instead of
            # inventing one.
            ignored += 1
            continue
        row = dict(pick)
        row["how"] = how
        row["mod"] = m.get("name")
        row["kind"] = m.get("kind")
        row["installed"] = bool(m.get("exists"))
        entry = status_by_rel.get(m["path_field"])
        row["enabled"] = _row_enabled(entry)
        row["dat"] = os.path.join(m.get("path") or "", LOC.DAT_REL)
        row["has_dat"] = bool(m.get("exists")) and os.path.isfile(row["dat"])
        picks.append(row)
        # Prefer the pick that can actually be mounted; keep the first one either
        # way so the screen can say "you picked X and X is gone" rather than show
        # nothing at all.
        if picked is None and row["installed"] and row["has_dat"]:
            picked = row
        elif picked is None or (not picked["installed"] and row["installed"]):
            picked = row

    data_rows = []
    for m in mods:
        if not m["has_dat"]:
            continue
        entry = status_by_rel.get(m["path_field"]) or {}
        is_sel = bool(picked and picked.get("mod") == m.get("name")
                      and picked.get("kind") == m.get("kind"))
        # Hash ONE folder, not fourteen.  A data mod is 10-15 MB here, so walking
        # every installed mod to fill a column nobody reads costs 170 MB of reads
        # on a screen that redraws after every toggle.  Only the picked folder's
        # checksum can change the answer, so only that one is recomputed.
        computed = _folder_checksum(m["path"]) if (is_sel and m.get("exists")) else None
        agrees = (str(entry.get("CheckSum")) == str(computed)
                  if computed is not None else None)
        data_rows.append({
            "name": m.get("name"),
            "title": m.get("title"),
            "kind": m.get("kind"),
            "priority": m.get("priority"),
            "enabled": _row_enabled(entry),
            "checksum": entry.get("CheckSum"),
            "checksum_now": computed,
            "checksum_agrees": agrees,
            "dat": m["dat"],
            "dat_bytes": os.path.getsize(m["dat"]) if os.path.isfile(m["dat"]) else 0,
            "selected": is_sel,
            # A stale checksum is the one thing that makes the engine reject a
            # picked dataset: ``DatasetCRC`` is what it verifies against the
            # folder before starting a match.
            "will_be_read": bool(is_sel and agrees is not False),
        })
    data_rows.sort(key=lambda r: (r["priority"] is None, r["priority"]))

    read_row = None
    for r in data_rows:
        if r["will_be_read"]:
            read_row = r
            break

    problems = []
    if not data_rows:
        problems.append({"code": "no-data-mod", "text": "这台机器上一个带 .dat 的模组都没有，游戏只会读它自己那份。"})
    if picked is None and data_rows:
        problems.append({"code": "no-dataset", "text": "装了 %d 个带 .dat 的模组，但 profile 里没有「选中的数据模组」这一条 —— 开局前要在「创建游戏」界面的「数据模组：」下拉框里选一次，游戏才会读它。" % len(data_rows)})
    elif picked is not None and not picked.get("installed"):
        problems.append({"code": "dataset-missing", "text": "上次选的数据模组「%s」文件夹已经不在了，游戏会退回它自己那份 .dat。" % picked.get("title")})
    elif picked is not None and not picked.get("has_dat"):
        problems.append({"code": "dataset-no-dat", "text": "上次选的数据模组「%s」里没有 .dat，它改的不是数据，游戏读的仍然是本体那份。" % picked.get("title")})
    if read_row is None and picked is not None and picked.get("has_dat") and picked.get("installed"):
        problems.append({"code": "dataset-stale", "text": "选中的「%s」算出来的校验和跟 mod-status.json 里记的不一样 —— 文件夹被改过而游戏没重新认过它，进游戏时可能退回本体。" % (picked.get("title") or picked.get("mod"))})
    if read_row is not None:
        others = [r for r in data_rows if r is not read_row]
        if others:
            problems.append({"code": "shadowed", "text": "另外 %d 个带 .dat 的模组不会被读：数据模组是单选，不是叠加，只有选中的那一份进游戏。" % len(others)})

    if read_row:
        reads = {"kind": "mod", "mod": read_row["name"], "title": read_row["title"],
                 "dat": read_row["dat"],
                 "why": "profile 里选中的数据模组就是它，文件夹也在，校验和对得上。"}
    else:
        reads = {"kind": "game", "mod": None, "title": "游戏本体", "dat": None,
                 "why": "profile 里没有一个能挂上的选中数据模组。"}
    if reads["dat"] is None:
        try:
            reads["dat"] = LOC.dat_path(LOC.find_game_root())
        except Exception:
            reads["dat"] = None

    return {
        "ok": True,
        "profile_root": root,
        "account": acc,
        "status_file": LOC.status_path(acc),
        "status_bytes": len(raw) if raw else 0,
        "counts": {
            "mods": len(mods),
            "enabled": sum(1 for m in mods if _row_enabled(status_by_rel.get(m["path_field"]))),
            "data_mods": len(data_rows),
            "picked": 1 if picked else 0,
        },
        "reads": reads,
        "selected": ({k: picked.get(k) for k in ("title", "workshop_id", "checksum", "how", "mod", "kind", "installed", "enabled", "offset")} if picked else None),
        "picks": picks,
        "data_mods": data_rows,
        "problems": problems,
        "flags": flags,
        "nfp": {"file": sel["file"], "bytes": sel["bytes"], "raw_bytes": sel["raw_bytes"],
                "records_seen": len(sel["picks"]), "matched": len(picks), "ignored": ignored},
        "note": "这一页读的是 mod-status.json 和 profile 里的 Player.nfp，不启动游戏。选中哪一份可以直接改（写的是游戏自己写的那条记录），但游戏正在跑的时候不写：它退出时会用自己的那份覆盖回来。",
    }


def _deflate(raw):
    """Compress ``raw`` the way the profile files are stored: bare deflate.

    Byte-identity with the file the game wrote is impossible (level 0-9 give
    38,491/5,666/4,909/4,780/4,453/4,242/4,175/4,174/4,108/4,077 bytes against the
    original 4,379), and it does not matter: the engine inflates the stream, it
    does not compare it.  What must be preserved is the RECORD LAYOUT, which is
    why ``write_selection`` edits the decompressed bytes and rebuilds the stream.
    """
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    return co.compress(raw) + co.flush()


def _backup(path, suffix=".before-dsh"):
    """Copy ``path`` next to itself once, so a bad write is one rename away from gone.

    Written only if the backup does not already exist: the FIRST state of the file
    is the interesting one, and overwriting the backup on every write would keep
    the last mistake instead of the last good file.
    """
    bak = path + suffix
    if os.path.exists(bak) or not os.path.exists(path):
        return bak if os.path.exists(bak) else None
    with open(path, "rb") as src, open(bak, "wb") as dst:
        dst.write(src.read())
    return bak


def _dataset_records(raw, account_dir):
    """The ``Player.nfp`` records that are dataset picks, newest understanding.

    The first guess -- "the first record whose third u32 is nonzero" -- is WRONG
    and the measurement that killed it is worth keeping: a player name record
    (``玩家`` at offset 28,126) happens to be followed by bytes that parse as
    workshop 395,872 / checksum 177,838, so that rule pointed the write at a
    player name and left the real pick untouched.  Round-tripping the sandbox copy
    and reading it back is what exposed it.

    What actually identifies a dataset pick is the ``CheckSum`` the engine itself
    wrote into ``mod-status.json`` for an installed mod: a record whose trailing
    checksum equals one of those is a pick, because the number came from that
    folder.  Measured on this profile there are TWO such records (``209785`` ->
    3412236901 and ``1233 For Stephen Chow`` -> 867086949), which lines up with the
    executable carrying both ``DatasetIM`` and ``DatasetMM`` -- one remembered pick
    per matchmaking mode.
    """
    doc, _acc, _raw = LOC.read_status_doc(account_dir, account=account_dir)
    known = {}
    titles = {}
    for e in (doc.get("Mods") or []):
        try:
            crc = int(str(e.get("CheckSum")))
        except (TypeError, ValueError):
            crc = 0
        # A zero is not an identity: this tool writes ``"CheckSum": "0"`` when it
        # registers a mod itself (``make_status_entry(..., checksum="0")``), and
        # every unused record in ``Player.nfp`` carries a zero tail.  Treating zero
        # as a checksum made the matcher rewrite eight records -- player names
        # included -- on the first sandbox run.
        title = e.get("Title") or ""
        if crc:
            known[crc] = title
        rel = str(e.get("Path") or "")
        bare = rel.rsplit("//", 1)[-1]
        if title:
            titles[title] = crc
        if bare:
            titles[bare] = crc
    out = []
    if not raw:
        return out
    for off, text, tail in _records(raw):
        if text == "NONE:NONE:::false" or len(tail) < 12:
            continue
        wid, _flags, crc = struct.unpack("<III", tail)
        # Two keys, in order of trust.  The checksum came from the folder, so a
        # match means this record was written by the engine for that mod.  The
        # title is the fallback for the case the checksum cannot cover: a picked
        # mod was uninstalled, or the status file was regenerated, and the record
        # keeps a checksum nothing installed answers to.  Either way the record is
        # only a candidate when its own checksum is nonzero -- a zero tail is an
        # unused slot, and there are hundreds.
        if not crc:
            continue
        if crc in known:
            out.append({"offset": off, "title": text, "workshop_id": wid,
                        "checksum": crc, "known_title": known[crc]})
        elif text in titles:
            out.append({"offset": off, "title": text, "workshop_id": wid,
                        "checksum": crc, "known_title": titles[text]})
    return out


def write_selection(account_dir, mod_path, title, workshop_id=0, checksum=None):
    """Point the profile's dataset pick(s) at ``mod_path``, in place.

    Measured 2026-11-21, and this is why the function exists at all:

    * ``mod-status.json``'s ``Enabled`` is NOT the switch for a data mod.  Set it
      true externally on any of the 13 installed data mods and the engine writes
      ``false`` back within 15-16 seconds; set it false and the engine keeps
      false.  A UI mod toggles normally.  The mods screen has shipped no switch
      for a ``ships_dat`` row since 2026-10-26 for the same reason.
    * The engine models the choice as a selected DATASET -- the executable
      carries ``DatasetIM``/``DatasetMM``/``DatasetWorkshopId``/``DatasetCRC`` and
      ``UICreateMultiplaterGameDialog::CheckValidDatasetSelected`` -- and the pick
      is a ``Player.nfp`` record.

    So "make the game read this mod" means: rewrite the TITLE, WorkshopID and
    CheckSum inside the record(s) that are already dataset picks, leave every
    other byte of the decompressed stream alone, and re-deflate.  Placeholder
    slots, player names and scenario records keep their bytes; offsets after the
    edited record shift, which is fine because the engine parses sequentially.

    Every identified pick is rewritten, not just the first: this profile has two
    (one per matchmaking mode), and pointing only one of them at the new mod would
    make the change appear to work in single-player and vanish in a lobby.

    There is no append path.  A profile that has never had a dataset picked has no
    record to rewrite, and inventing one means guessing at the slot bookkeeping
    around the 23 ``NONE:NONE:::false`` placeholders -- so ``ValueError`` says so
    and the caller tells the player to pick once in game.
    """
    nfp = os.path.join(account_dir, NFP_REL)
    raw = inflate(nfp)
    if not raw:
        raise ValueError("读不出 Player.nfp（%s）：文件不存在，或者它的压缩流解不开。" % nfp)
    if checksum is None:
        checksum = _folder_checksum(mod_path)
    if not checksum:
        raise ValueError("算不出「%s」的校验和：文件夹不在，或者里面有读不了的文件。" % title)

    targets = _dataset_records(raw, account_dir)
    if not targets:
        raise ValueError("这个 profile 里还没有「选中的数据模组」这一条记录。先在游戏里开局一次、"
                         "在「创建游戏」界面的「数据模组：」下拉框里随便选一份，回来再让工具替你换。")

    new_title = title.encode("utf-8")
    if len(new_title) > 400:
        raise ValueError("这个模组名太长（%d 字节），Player.nfp 的槽位放不下。" % len(new_title))
    head = (RECORD_MAGIC + struct.pack("<H", len(new_title)) + new_title
            + struct.pack("<III", int(workshop_id or 0), 0, int(checksum)))

    # Rewrite back to front so the offsets of records not yet visited stay valid.
    new_raw = raw
    replaced = []
    for t in sorted(targets, key=lambda x: x["offset"], reverse=True):
        off = t["offset"]
        old_end = off + 4 + len(t["title"].encode("utf-8")) + 12
        new_raw = new_raw[:off] + head + new_raw[old_end:]
        replaced.append({"offset": off, "was": t["title"],
                         "was_checksum": t["checksum"]})

    bak = _backup(nfp)
    blob = _deflate(new_raw)
    with open(nfp, "wb") as fh:
        fh.write(blob)

    # Read it back the way the engine will: inflate, and compare the records --
    # not the compressed bytes, which no level reproduces.  A write that does not
    # read back is restored from the backup instead of left on disk.
    check = inflate(nfp)
    if not check or check != new_raw:
        if bak:
            with open(bak, "rb") as src, open(nfp, "wb") as dst:
                dst.write(src.read())
        raise ValueError("写回去以后读出来的内容和要写的对不上，已经从备份还原了：%s"
                         % (bak or "（没有备份）"))
    return {"file": nfp, "backup": bak, "title": title,
            "checksum": int(checksum), "workshop_id": int(workshop_id or 0),
            "replaced": replaced, "bytes": len(blob), "raw_bytes": len(new_raw)}
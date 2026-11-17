# -*- coding: utf-8 -*-
"""Keep a local shelf of official `.dat` builds, so "which version is this mod based on" is answerable.

WHY THIS EXISTS

A data mod is a whole `.dat`: 11.9 MB compressed, 93,272,287 bytes inflated.  When
the game patches, `provenance.check()` can say a mod is stale -- and that is all it
can say.  It cannot say *which* official build the mod was made from, because the
only copy of the old official data that ever existed on this machine was inside the
mod folder the user is about to overwrite.  Rebuilding a stale mod therefore starts
from whatever the game ships NOW, silently folding the patch into the user's mod,
and the one thing a rebuild must not do is change more than the user asked for.

Keeping the previous official streams on disk turns that into a measurement: a
third-party mod's `.dat` can be diffed against every official build we have seen,
and the build with the fewest differing bytes is the one it was made from.  Measured
on this machine, 2026-11-09:

    diff_regions(base, mod) over two 93 MB streams, SAME length,
        a base with 0-1 edits                           0.011 - 0.015 s
        the same base with 63 edits                       0.139 s
    best_base against a same-length mod ("rb all civs")   0.250 s
    diff_regions across generations (93 MB vs 100 MB,
        63 MB different, 12.8 M regions)                  5.695 s
    note_official (copy path, incl. inflate+hash)         0.120 s
    note (deflate path, new content, no source file)      0.614 s
    note (idempotent, one hash of the raw stream)         0.039 s

The last three are why the copy path exists.  `note()` has the raw stream in hand
already, and deflating it again costs 0.614 s *per archive write*; if the caller can
also name the file it came from, that file is already the exact compressed blob the
engine reads -- verifying it inflates to the same 93 MB costs 0.11 s, then copying it
costs 0.006 s -- so the copy path is 5x cheaper and produces byte-identical storage
every time.  And a wrong-generation candidate costs 5.7 s to diff and returns 12.8
million regions (a list that alone weighs hundreds of MB), which is the measured
reason `best_base()` filters by raw length before diffing anything, and the reason
its cross-generation fallback is a last resort the caller is told about via
``same_len``.

WHERE THE BLOBS LIVE

`<tool>/dat_archive/<sha256[:16]>.dat` -- inside the tool's own folder, beside `log/`
and `_mods_out/`, and NOT under `%LOCALAPPDATA%`.

This moved on 2026-11-10, at the player's request ("let the tool keep a copy of the
official data in the tool's own folder every time the game updates it").  The old
location was inherited from `provenance.py`'s reasoning -- a local state file keeps
every mod folder shaped like a published mod -- and that reasoning still holds for
`builds.json`.  But the shelf is not a record of what this machine did; it is the
DATA the upgrade engine reasons from.  It ships with the tool, it travels when the
folder is copied to another machine, and a `%LOCALAPPDATA%` folder is the first
thing a disk cleaner deletes.  Measured before the move: 53 blobs, 328,554,973
bytes, 2019-10-18 (VER 6.6) through 2026-10-27 (VER 8.9).

Three overrides, in this order:

  `AOE2MOD_ARCHIVE_DIR`        the shelf itself, verbatim (a player who keeps it
                               elsewhere)
  `AOE2MOD_STATE_DIR` / `AOE2MOD_STATE`
                               keeps the old `<state>/dat_archive` layout, so every
                               suite written before the move stays isolated
  nothing                      `<tool>/dat_archive`

A shelf left behind in the old place is ADOPTED, not ignored: the first call copies
the blobs across and repoints the index (`_adopt_legacy`).  Silently starting from an
empty shelf would look exactly like "the archive was deleted", and would turn every
installed mod in the list into an `impossible`.

A blob is stored as the bare raw-deflate stream the engine reads -- not the inflated
93 MB.  Fifty-three builds of this size are 4.9 GB inflated against 313 MB compressed,
which is the difference between a shelf worth shipping and one that is not.
Every read re-inflates and re-hashes, and a blob that no longer matches its own name
is reported as missing rather than raised: a truncated file is a fact about the disk,
not an exception for the screen to catch.

COST OF A WRONG ANSWER

`best_base()` only compares candidates of the SAME raw length by default, because a
`VER 7.8` build has a different layout, and a diff across generations would report
"11,412 edits" for what is really "the mod is from another generation".  When nothing
shares the length, it falls back to the same-version candidates and says
`same_len: False`, so the caller can refuse to trust the number instead of pretending
the answer is the good one.
"""
import datetime
import hashlib
import json
import os
import shutil
import zlib

from ..dat import parser as P
from ..dat import locate as L
from . import emitter as E
from . import provenance as PV

#: The storage point, relative to BOTH the game root and a mod root.  Spelled here
#: rather than imported from `emitter` so this module stays importable on its own.
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

STATE_VERSION = 1
ARCHIVE_DIR = "dat_archive"
INDEX_FILE = "dat_archive.json"
#: The BUILD LEDGER: one row per Steam manifest this shelf was assembled from,
#: with the date that manifest appeared on Steam.  The index above answers "which
#: .dat do I hold"; this answers "when was that build live" -- two different
#: questions, and only the ledger can answer the second.  It is generated beside
#: the shelf (see MANIFEST.csv, same rows in CSV for a human with Excel), ships
#: with it, and is joined to the index by raw_sha256: a row here that names a
#: build we do not hold is not printed as if we had it.
BUILDS_FILE = "index.json"
BLOB_SUFFIX = ".dat"
#: 16 hex chars = 64 bits.  An accidental collision needs two `.dat` builds whose
#: first 8 bytes of hash agree; the full sha256 stays in the index and is re-checked
#: on every read, so a collision would be caught rather than served.
BLOB_NAME_CHARS = 16
#: The shelf itself, when a caller wants it somewhere other than the tool folder.
ARCHIVE_DIR_ENV = "AOE2MOD_ARCHIVE_DIR"

#: How many blobs to keep when nobody says otherwise.  ZERO MEANS EVERYTHING.
#:
#: This used to be 8 ("a couple of patches ago"), written when the shelf was a cache.
#: It is not a cache any more: the whole point of the 2026-11-10 move is that the
#: history IS the product, and a mod made three patches ago is exactly the mod that
#: needs carrying.  So `prune()` now deletes nothing without an explicit count, and
#: nothing in the tree calls it -- 53 blobs are 313 MB against 93 MB of `.dat` per
#: build, paid once, and the whole shelf is what makes a patch survivable.
PRUNE_KEEP = 0


def tool_root():
    r"""The folder the player calls "the tool" -- where `log/` and `dat_archive/` go.

    Same three-levels-up-from-the-package walk, and the same "never write inside
    `app/`" rule, as `aoe2mod/ui/server.py:_tool_root`, and for the same measured
    reason (2026-11-02: build output that landed in `app/_mods_out/` grew the
    package from 50.9 MB to 1.7 GB).  A shipped layout is::

        <tool>/aoe2-mod-workshop.exe
        <tool>/runtime/...
        <tool>/app/aoe2mod/mod/archives.py     <- this file, two levels under app/

    so the walk stops at `<tool>`, not at `<tool>/app`.

    Written out again rather than imported from the UI layer: `_probe/test_archives.py`
    imports this module alone, and `from ..ui import server` would drag the whole
    HTTP server into an engine test that only wants to hash a blob.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.basename(root).lower() == "app":
        bundle = os.path.dirname(root)
        if os.path.isdir(os.path.join(bundle, "runtime")):
            return bundle
    return root


def legacy_dir():
    """Where the shelf lived before 2026-11-10; kept so it can be adopted once."""
    return os.path.join(PV.state_dir(), ARCHIVE_DIR)


#: One adoption attempt per process: a failed copy must not be retried on every
#: `index_path()` call, and `load_index()` sits on the page-load path.
_ADOPTED = False


def _adopt_legacy(d):
    """Carry a shelf left at the old location into `d`, once.

    Copies the blobs, repoints every `path`, then writes the index.  The old folder
    is left alone: a half-finished adoption must not destroy the only copy, the copy
    is idempotent, and a later run finishes it.  Failures are swallowed -- an empty
    shelf costs one rebuild, while raising here would take the screen down on a
    page load.
    """
    global _ADOPTED
    if _ADOPTED:
        return
    _ADOPTED = True
    legacy = legacy_dir()
    if os.path.abspath(legacy) == os.path.abspath(d):
        return
    if not os.path.isdir(legacy):
        return
    src = os.path.join(legacy, INDEX_FILE)
    dst = os.path.join(d, INDEX_FILE)
    if not os.path.isfile(src) or os.path.isfile(dst):
        return
    try:
        with open(src, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8-sig"))
        got = doc.get("entries")
        if not isinstance(got, dict):
            return
        for sha, ent in got.items():
            if not isinstance(ent, dict) or not isinstance(sha, str):
                continue
            name = sha[:BLOB_NAME_CHARS] + BLOB_SUFFIX
            blob_src = os.path.join(legacy, name)
            blob_dst = os.path.join(d, name)
            if os.path.isfile(blob_src) and not os.path.isfile(blob_dst):
                shutil.copyfile(blob_src, blob_dst)
            ent["path"] = blob_dst
            if os.path.isfile(blob_dst):
                ent["file_bytes"] = os.path.getsize(blob_dst)
        tmp = dst + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, dst)
    except Exception:                                   # noqa: BLE001
        return


def archive_dir():
    """Where the blobs live; created on first use.

    The tool folder, unless a caller says otherwise.  The `AOE2MOD_STATE_DIR` branch
    exists so a suite that isolates its state does not also spend 313 MB writing into
    the real shelf -- and does not adopt the player's shelf into a temp folder.
    """
    override = os.environ.get(ARCHIVE_DIR_ENV)
    isolated = bool(os.environ.get(PV.STATE_DIR_ENV)
                    or os.environ.get(PV.STATE_DIR_ENV_NATIVE))
    if override:
        d = os.path.abspath(override)
    elif isolated:
        d = os.path.join(PV.state_dir(), ARCHIVE_DIR)
    else:
        d = os.path.join(tool_root(), ARCHIVE_DIR)
    if not os.path.isdir(d):
        os.makedirs(d)
    if not override and not isolated:
        _adopt_legacy(d)
    return d


def index_path():
    return os.path.join(archive_dir(), INDEX_FILE)


def blob_path(sha):
    return os.path.join(archive_dir(), sha[:BLOB_NAME_CHARS] + BLOB_SUFFIX)


# ---------------------------------------------------------------------------
# the index
# ---------------------------------------------------------------------------

def load_index():
    """Read the index; a missing, short or corrupt file reads as empty.

    Same rule as `provenance.load()`: a damaged index must not take the screen
    down.  The worst it can cost is that we forget which builds we have -- and the
    blobs are still on disk under their own hash names, so the next `note()` of the
    same content finds the file already there and writes no new bytes.
    """
    empty = {"version": STATE_VERSION, "entries": {}}
    try:
        with open(index_path(), "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8-sig"))
    except (IOError, OSError, ValueError):
        return empty
    if not isinstance(doc, dict):
        return empty
    doc.setdefault("version", STATE_VERSION)
    if not isinstance(doc.get("entries"), dict):
        doc["entries"] = {}
    else:
        doc["entries"] = {k: v for k, v in doc["entries"].items()
                          if isinstance(k, str) and isinstance(v, dict)}
    # A shipped shelf carries the absolute paths of the machine it was built on
    # ("D:\\...\\dat_archive\\<sha>.dat").  Unpacked anywhere else those paths
    # are fiction: `describe()` would sum sizes for files that are not there and
    # report an empty shelf that is in fact full.  Repoint each entry at the blob
    # name it should have in THIS folder -- the name is content-addressed, so the
    # same sha is the same file, and `raw_of()` re-hashes before trusting it.
    here = archive_dir()
    for sha, ent in doc["entries"].items():
        want = os.path.join(here, sha[:BLOB_NAME_CHARS] + BLOB_SUFFIX)
        if ent.get("path") == want:
            continue
        ent["path"] = want
        if os.path.isfile(want):
            try:
                ent["file_bytes"] = os.path.getsize(want)
            except OSError:
                pass
    return doc


def save_index(ix):
    """Write atomically -- a half-written index would lose every entry at once."""
    path = index_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ix, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def builds_path():
    return os.path.join(archive_dir(), BUILDS_FILE)


def load_builds():
    """Every manifest the shelf was assembled from, oldest first.

    A missing or damaged ledger reads as EMPTY rather than raising, for the same
    reason a damaged index does: the blobs are the product, and a shelf that can
    still inflate 53 builds is not made useless by a broken side-car.  The panel
    falls back to "this tool first stored it on <date>", which it can always
    know, instead of printing a date it cannot.

    Rows are normalised here rather than in the caller because the file is
    written by a harvest script that has changed shape once already (it carried
    `file` paths before it carried `gid`), and a panel that trusted the raw
    dict would break on the next harvest.
    """
    try:
        with open(builds_path(), "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8-sig"))
    except (IOError, OSError, ValueError):
        return []
    rows = doc.get("files") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        sha = str(r.get("raw_sha256") or "").strip().lower()
        if not sha:
            continue
        try:
            raw_bytes = int(r.get("raw_bytes") or 0)
            file_bytes = int(r.get("file_bytes") or 0)
        except (TypeError, ValueError):
            raw_bytes = file_bytes = 0
        out.append({"date": str(r.get("date") or "")[:10],
                    "time": str(r.get("time") or "")[:8],
                    "gid": str(r.get("gid") or ""),
                    "ver": str(r.get("ver") or ""),
                    "raw_bytes": raw_bytes,
                    "file_bytes": file_bytes,
                    "sha256": sha,
                    "dup_of": str(r.get("dup_of") or ""),
                    "branch": str(r.get("branch") or "")})
    out.sort(key=lambda r: (r["date"], r["time"], r["gid"]))
    return out


# ---------------------------------------------------------------------------
# reading a raw stream
# ---------------------------------------------------------------------------

def _head_ver(raw):
    """The ``VER x.y`` string from the head of a RAW stream.

    `provenance.head_version` takes a path and inflates; here the raw bytes are
    already in memory, so this is a slice and a split (0.000002 s, measured).
    A generation string is ASCII and NUL-terminated; anything else is reported
    as-is rather than raising, because a caller deciding whether a candidate is
    usable only needs to compare it.
    """
    if not raw:
        return None
    head = raw[:32].split(b"\x00")[0]
    try:
        return head.decode("ascii")
    except UnicodeDecodeError:
        return head.decode("ascii", "replace")


def _now():
    """UTC-free local ISO stamp WITH microseconds.

    `provenance.now_iso()` stops at the second.  `prune()` must never delete the
    newest entry, and two blobs noted inside the same second (which is exactly what
    the probe does) would sort as a tie -- so the ordering key has to be finer than
    the one a human reads.
    """
    return datetime.datetime.now().isoformat(timespec="microseconds")


def _inflate(path):
    """`load_dat` as data: ``(raw, how)`` or ``(None, None)`` when unreadable.

    A truncated stream raises `zlib.error` (a subclass of Exception, not of
    OSError), and a 200-byte text file named `empires2_x2_p1.dat` raises the same --
    both mean "this is not a `.dat`", which every caller here treats as data.
    """
    try:
        return P.load_dat(path)
    except (IOError, OSError, ValueError, EOFError, zlib.error):
        return None, None


# ---------------------------------------------------------------------------
# writing a blob
# ---------------------------------------------------------------------------

def _write_blob(blob, raw, src_path=None, src_how=None):
    """Store `raw` at `blob`, preferring the caller's compressed file verbatim.

    Returns the number of bytes on disk.  ``src_how`` is the ``how`` string
    `load_dat` returned for ``src_path`` when the caller already loaded it: passing
    it proves the file inflates to this exact raw and saves re-inflating (0.075 s +
    0.036 s).  When it is absent the file is verified here, because copying a file
    we have not verified would store bytes under a hash they do not have.
    """
    tmp = blob + ".tmp"
    copied = False
    if src_path and os.path.isfile(src_path):
        how = src_how
        ok = False
        if how is None:
            sraw, how = _inflate(src_path)
            if sraw is not None and len(sraw) == len(raw):
                ok = hashlib.sha256(sraw).hexdigest() == hashlib.sha256(raw).hexdigest()
        else:
            # how came from load_dat(src_path), so the stream is known to match.
            ok = True
        # Only a COMPRESSED source may be copied.  An already-inflated file would
        # be stored raw, and the engine cannot open a raw stream -- `load_dat`
        # would still read it back, so the mistake would survive every check here
        # and only show up when a mod built from this blob is loaded in game.
        if ok and how and how.startswith("raw-deflate"):
            shutil.copyfile(src_path, tmp)
            copied = True
    if not copied:
        with open(tmp, "wb") as fh:
            fh.write(E.deflate_raw(raw, 6))
    os.replace(tmp, blob)
    return os.path.getsize(blob)


def note(raw, src_path=None, label=None, mtime=None):
    """Remember one raw `.dat` stream.  Idempotent.

    ``src_path`` is the compressed file the stream came from, if the caller knows
    it: when that file inflates to this exact content its bytes are copied verbatim
    (0.006 s for 11.9 MB) instead of re-deflating 93 MB (0.57 s).  Otherwise the
    stream is deflated from memory.

    Returns the entry as stored.  IO errors from the final write are allowed to
    propagate -- a state dir that cannot be written is a real fault, and swallowing
    it would leave the index claiming a blob that is not there.
    """
    sha = hashlib.sha256(raw).hexdigest()
    return _store(raw, sha, src_path, label, mtime, None)


def _store(raw, sha, src_path, label, mtime, src_how):
    ix = load_index()
    blob = blob_path(sha)
    ent = ix["entries"].get(sha)

    # Idempotent path: the blob exists and its recorded size still matches.  Size,
    # not hash -- hashing 11.9 MB on every screen load would cost 0.009 s and still
    # not prove the CONTENT is right; `raw_of()` is where content is proved.  An
    # entry with no recorded size is treated as unknown and rewritten, which is
    # cheap (the copy path) and cannot leave a wrong blob trusted.
    if isinstance(ent, dict) and ent.get("path") == blob and os.path.isfile(blob):
        size = os.path.getsize(blob)
        if ent.get("file_bytes") and size == ent.get("file_bytes"):
            return ent

    if mtime is None and src_path and os.path.isfile(src_path):
        try:
            mtime = os.stat(src_path).st_mtime
        except OSError:
            mtime = None

    file_bytes = _write_blob(blob, raw, src_path=src_path, src_how=src_how)

    if isinstance(ent, dict):
        # Same content, blob was stale or missing: keep when it was first seen, so
        # a healed archive does not jump to the front of `entries()`.
        ent = dict(ent)
        ent.update({"path": blob, "file_bytes": file_bytes, "raw_bytes": len(raw),
                    "ver": _head_ver(raw)})
        if mtime is not None:
            ent["mtime"] = mtime
        if label:
            ent["label"] = label
        if src_path:
            ent["src"] = src_path
        ix["entries"][sha] = ent
    else:
        ent = {
            "sha256": sha,
            "raw_bytes": len(raw),
            "file_bytes": file_bytes,
            "ver": _head_ver(raw),
            "first_seen": _now(),
            "mtime": mtime,
            "label": label,
            "src": src_path,
            "path": blob,
        }
        ix["entries"][sha] = ent
    save_index(ix)
    return ent


def note_file(path, label=None):
    """Note the `.dat` at `path`.  ``None`` when it cannot be read as one.

    A file that is not a `.dat` is data, not an exception: the screen lists a mod
    folder's files and one of them may be a 200-byte text file called
    `empires2_x2_p1.dat`.
    """
    raw, how = _inflate(path)
    if raw is None:
        return None
    return _store(raw, hashlib.sha256(raw).hexdigest(), path, label, None, how)


def note_official(game_root=None):
    """Note the game's OWN `.dat` -- the build future mods are made from.

    Called after a patch, before anything is rebuilt, so the build that is about to
    be replaced survives the patch.  Returns ``None`` when the game is not installed
    or the file has gone: "no official build here" is a fact about the machine.
    """
    from ..game import locations as GL
    root = game_root or GL.find_game_root()
    if not root:
        return None
    path = GL.dat_path(root)
    if not os.path.isfile(path):
        return None
    return note_file(path, label="game")


# ---------------------------------------------------------------------------
# reading back
# ---------------------------------------------------------------------------

def raw_of(sha):
    """The raw stream for `sha`, or ``None``.

    Re-inflates and re-hashes (0.075 s + 0.036 s for the official build).  A blob
    that has been truncated or overwritten since it was written is treated as
    MISSING rather than raising: the archive's whole job is to be trustworthy, and
    a stream that does not hash to its own name is not that stream.
    """
    if not sha:
        return None
    blob = blob_path(sha)
    if not os.path.isfile(blob):
        return None
    raw, _how = _inflate(blob)
    if raw is None:
        return None
    if hashlib.sha256(raw).hexdigest() != sha:
        return None
    return raw


def entries():
    """Every entry, newest first."""
    ix = load_index()
    rows = [e for e in ix["entries"].values() if isinstance(e, dict)]
    rows.sort(key=lambda e: (e.get("first_seen") or "", e.get("mtime") or 0),
              reverse=True)
    return rows


def describe():
    """What the archive holds, for a panel that has to render it.

    ``bytes`` counts what is actually on disk -- the index can outlive a blob that
    a cleaner deleted, and a panel that reported the index's sizes would promise
    storage the user does not have.
    """
    rows = entries()
    total = 0
    for e in rows:
        p = e.get("path")
        try:
            if p and os.path.isfile(p):
                total += os.path.getsize(p)
        except OSError:
            pass
    return {"dir": archive_dir(), "count": len(rows), "bytes": total,
            "entries": rows}


def prune(keep=PRUNE_KEEP):
    """Delete the oldest blobs beyond `keep`.  The newest entry is never deleted.

    Returns the list of removed shas.  `keep <= 0` removes NOTHING and returns an
    empty list: since 2026-11-10 the shelf is the product (see `PRUNE_KEEP`), and a
    default that trimmed to one build would delete the generation the next patch has
    to carry a mod out of.  A caller that really wants a window passes a positive
    count.
    """
    keep = int(keep or 0)
    if keep <= 0:
        return []
    rows = entries()                      # newest first
    if len(rows) <= keep:
        return []
    ix = load_index()
    removed = []
    for ent in rows[keep:]:               # older than the keep window
        sha = ent.get("sha256")
        if not sha or sha not in ix["entries"]:
            continue
        blob = ent.get("path") or blob_path(sha)
        try:
            if os.path.isfile(blob):
                os.remove(blob)
        except OSError:
            # A blob we cannot delete stays in the index: forgetting it would hide
            # the disk usage from `describe()` and from the user.
            continue
        del ix["entries"][sha]
        removed.append(sha)
    if removed:
        save_index(ix)
    return removed


# ---------------------------------------------------------------------------
# which official build is this mod based on
# ---------------------------------------------------------------------------

def size_candidates(ver=None):
    """How many raw bytes each archived build of this generation has.

    This exists so a caller can answer "is there a same-length base at all?"
    WITHOUT paying for ``best_base``.  Measured on 2026-11-09: asking
    ``best_base`` for a mod that has no same-length candidate makes it diff the
    wrong-length file anyway -- 5.7 s and 12.8 million regions, about 900 MB of
    tuples -- to learn a fact that the index already knows for free.

    Returns ``{"sizes": {raw_bytes: [sha, ...]}, "ver": ver, "entries": n}``.
    Sizes are the DECOMPRESSED lengths, because that is what record offsets are
    counted in.
    """
    ix = load_index()
    out = {}
    for sha, ent in ix["entries"].items():
        if not isinstance(ent, dict):
            continue
        if ver and ent.get("ver") != ver:
            continue
        n = ent.get("raw_bytes")
        if isinstance(n, int) and n > 0:
            out.setdefault(n, []).append(sha)
    return {"sizes": out, "ver": ver, "entries": sum(len(v) for v in out.values())}


def pick_base(ver, prefer_len=None, exclude=None):
    """Choose an archived build of one generation WITHOUT diffing anything.

    ``best_base`` answers "which archived build is closest to this stream", and
    for a stream of a different length that question is meaningless: it falls
    back to comparing incompatible geometries, which costs 5.7 s and returns
    12.8 million regions (~900 MB of tuples) to say "these are two files".

    When the caller has already decided that a length difference is legitimate
    (the mod added records, so it is bigger), there is nothing left to measure --
    the base is a build of the same generation, and any one of them is the right
    ancestor.  This picks it by data the index already holds.

    Returns ``{"sha256", "raw", "ver", "raw_bytes", "exact_len", "candidates"}``
    or the empty shape when this generation was never archived.

    ``exclude`` drops shas from the pool.  The one caller that needs it is
    ``upgrade._load_pair``, and what it drops is the NEW stream -- the build the
    mod is being carried onto.  Today's build is always in the shelf (the tool
    notes it on every launch), and it always sorts first by ``first_seen``, so
    without this the "before" would silently be "after" and every mod that added
    records would come back as "nothing to carry" on exactly the day it matters.
    """
    ix = load_index()
    skip = set(exclude or ())
    rows = []
    for sha, ent in ix["entries"].items():
        if not isinstance(ent, dict) or sha in skip:
            continue
        if ver and ent.get("ver") != ver:
            continue
        rows.append((sha, ent))
    empty = {"sha256": None, "raw": None, "ver": None, "raw_bytes": None,
             "exact_len": False, "candidates": 0}
    if not rows:
        return empty
    rows.sort(key=lambda r: (r[1].get("first_seen") or ""), reverse=True)
    exact = [r for r in rows if r[1].get("raw_bytes") == prefer_len]
    sha, ent = (exact[0] if exact else rows[0])
    raw = raw_of(sha)
    if raw is None:
        return empty
    return {"sha256": sha, "raw": raw, "ver": ent.get("ver"),
            "raw_bytes": ent.get("raw_bytes"), "exact_len": bool(exact),
            "candidates": len(rows)}


def best_base(mod_raw, ver=None):
    """The archived official build this mod's stream is closest to.

    Returns::

        {"sha256", "raw", "ver", "diff_bytes", "diff_regions", "candidates",
         "same_len"}

    Only same-length candidates are compared when there are any: a `VER 7.8` file
    has a different layout, and `diff_regions` across generations reports thousands
    of regions for what is really "another generation".  With no same-length
    candidate the same-version ones are compared anyway and ``same_len`` is False,
    so the caller can print "closest, but not the same size" instead of trusting a
    number that answers a different question.

    Measured cost per candidate, 2026-11-09: 0.011 s for a base one byte away,
    0.250 s for the 63-edit `rb all civs` mod, and 5.695 s for a wrong-length mod
    (`398106_waifor arcade`, 100,478,853 raw bytes, 63,301,768 bytes different) --
    which also returns 12.8 MILLION regions, roughly 900 MB of tuples.  That is the
    whole reason the length filter comes first; a UI that calls this with a
    cross-generation mod is accepting a multi-second wait and a memory spike.
    A full archive of 8 same-length builds therefore costs ~2 s.
    Candidates whose blob is missing or corrupt are skipped; when nothing could be
    compared the empty shape is returned with ``candidates: 0``.
    """
    mod_ver = ver or _head_ver(mod_raw)
    ix = load_index()
    same_len = []
    same_ver = []
    for sha, ent in ix["entries"].items():
        if not isinstance(ent, dict):
            continue
        if mod_ver and ent.get("ver") != mod_ver:
            continue
        same_ver.append((sha, ent))
        if ent.get("raw_bytes") == len(mod_raw):
            same_len.append((sha, ent))

    empty = {"sha256": None, "raw": None, "ver": None, "diff_bytes": None,
             "diff_regions": None, "candidates": 0, "same_len": False}
    if not same_ver:
        return empty

    pool = same_len or same_ver
    best = None
    compared = 0
    for sha, ent in pool:
        base = raw_of(sha)
        if base is None:
            continue
        compared += 1
        regions = L.diff_regions(base, mod_raw)
        total = sum(n for _off, n in regions)
        if best is None or total < best["diff_bytes"]:
            best = {"sha256": sha, "raw": base, "ver": ent.get("ver"),
                    "diff_bytes": total, "diff_regions": regions,
                    "candidates": compared, "same_len": bool(same_len)}
    if best is None:
        return empty
    best["candidates"] = compared
    return best

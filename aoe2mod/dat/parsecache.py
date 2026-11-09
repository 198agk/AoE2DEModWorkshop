# -*- coding: utf-8 -*-
"""Keep the parse of the game data on disk, so the second start is not 9 seconds.

WHY THIS EXISTS

Measured 2026-10-31 on this machine, from `Toolkit._ensure()` (see
`aoe2mod/progress.py` for the same numbers):

    inflate        0.07 s
    parse          4.37 s      P.Parser(...).parse() over 93,272,287 bytes
    locate         4.08 s      walking every civ's unit record
    ---------------------------------
    total          8.56 s

The player's words were 「为什么这个加载这么慢」.  Nothing in that work depends
on the REQUEST -- it depends only on the bytes of the `.dat` -- so it is the one
thing in this program that can be computed once and reused across restarts.

WHAT IS CACHED, AND WHAT IS NOT

Only the three values the parse produces:

    stats   tuple of 33 tables   (p.stats)
    civs    the 63 civilisations with every unit record   (locate's first result)
    ...plus the four scalars that travel with them: civs_start, gv, tail, how.

The raw stream itself (93 MB) is NOT stored: it comes back from `load_dat` in
0.07 s and would triple the file on disk.

MEASURED COST (2026-10-31, `_probe/tmp_cache_bench.py`)

    pickle.dumps(payload, protocol=5)   0.68 s   112 MB
    zlib.compress(..., 1)               0.22 s    33 MB
    zlib.decompress                     0.13 s
    pickle.loads                        0.81 s
    read 33 MB from disk                0.01 s
    sha256 of the 93 MB raw stream      0.04 s
    ---------------------------------
    cache hit                           1.6 s   (versus 8.6 s of work)

So the cache is worth 5x and never makes the common path slower: a MISS costs
one extra 0.22 s of compressing, which is noise next to 8.6 s.

WHY THE KEY IS THE RAW SHA256

`aoe2mod/dat/datstamp.py` exists because Steam replaced the `.dat` on 2026-10-28
and both engines kept writing through offsets measured from the old file.  A
stale cache would be the same class of bug -- every offset off by thousands of
bytes while `/api/stat` answered `ok:true` -- so the key is the hash of the RAW
(inflated) stream, not of the file: a re-shipped file with identical content is
the same data, and a genuinely changed file must never hit the old parse.

`datstamp.check()` still runs BEFORE the cache is consulted.  If the installed
stamp disagrees with the game data, the load fails loudly; it does not fall back
to a cache.

WHERE IT LIVES

`aoe2mod/mod/provenance.state_dir()` -- the same directory as `builds.json`, so
`AOE2MOD_STATE_DIR` isolation works for probes without a second knob.  The file
name carries the interpreter's magic number and Python version: `pickle` is only
guaranteed to load what the same interpreter wrote, and the shipped exe runs
3.12 while the development checkout runs 3.14.  A different interpreter simply
misses the cache and re-parses; it never reads a foreign pickle.
"""
import hashlib
import os
import pickle
import sys
import threading
import time
import zlib

#: Bumped when the SHAPE of the cached tuple changes.  A reader that finds an
#: older number deletes the file instead of guessing what the fields mean.
#
#: v2 (2026-11-06): every civ and every unit record now carries `_start`/`_end`
#: -- the byte range it occupies.  A v1 file has the same three tables but the
#: records inside them have no spans, and the editor's incremental restructure
#: (`aoe2mod/ui/server.py:_restructure`) reads them.  Loading a v1 file would
#: therefore hand the editor a model that cannot be shifted: `KeyError: _start`
#: on the first added record.  The version guard turns that into a re-parse.
#:
#: v3 (2026-11-06): records also carry `_off_dll_name` (units) and
#: `_off_lang_name` / `_off_lang_description` (techs) -- the addresses of the
#: display-string ids.  Renaming a record for the PLAYER (not just for the
#: editor's lists) rewrites those ids, and a v2 model has no address to rewrite,
#: so the rename would silently change only the internal name.
CACHE_VERSION = 3

#: `pickle` files are not portable across CPython versions, so the name says
#: which interpreter wrote it.  Proton/Wine users can run the game from either.
_PY_TAG = "py%d%d" % (sys.version_info[0], sys.version_info[1])

NAME = "parse_cache_%s_v%d.bin" % (_PY_TAG, CACHE_VERSION)

#: Set to "0" to disable.  Probes use it to measure the uncached path.
CACHE_ENV = "AOE2MOD_PARSE_CACHE"

_LOCK = threading.Lock()


def cache_dir():
    """Where the cache file goes.  Same directory as the build records."""
    from aoe2mod.mod import provenance as PV
    return PV.state_dir()


def cache_path():
    return os.path.join(cache_dir(), NAME)


def enabled():
    return os.environ.get(CACHE_ENV, "1") != "0"


def key(raw):
    """The identity of a parse: hash of the inflated stream plus the version tag."""
    h = hashlib.sha256(raw).hexdigest()
    return {"raw_sha256": h, "raw_bytes": len(raw), "version": CACHE_VERSION,
            "python": _PY_TAG}


def raw_digest(raw):
    """Just the hash, for callers that already know the key shape."""
    return hashlib.sha256(raw).hexdigest()


def save(raw, stats, civs, civs_start, gv, tail, how):
    """Write the parse of `raw` to disk.  Returns the path, or None if it failed.

    A cache is an optimisation: every failure here is swallowed and the caller
    simply parses.  The one thing this must never do is leave a HALF-WRITTEN file
    that a later run would trust, so the bytes go to a temporary name first and
    are renamed into place.
    """
    if not enabled():
        return None
    payload = {
        "key": key(raw),
        "stats": stats,
        "civs": civs,
        "civs_start": civs_start,
        "gv": gv,
        "tail": tail,
        "how": how,
    }
    try:
        blob = pickle.dumps(payload, protocol=5)
        packed = zlib.compress(blob, 1)
    except Exception:
        return None
    path = cache_path()
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "wb") as fh:
            fh.write(packed)
        os.replace(tmp, path)
        return path
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None


def load(raw):
    """The cached parse of `raw`, or None.

    Returns ``(stats, civs, civs_start, gv, tail, how)`` exactly as
    `Toolkit._ensure()` would have computed them.  Anything unexpected --
    missing file, truncated pickle, a key that names different bytes, a shape
    this version does not know -- is a miss, never an error.
    """
    if not enabled():
        return None
    path = cache_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            packed = fh.read()
        payload = pickle.loads(zlib.decompress(packed))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    want = key(raw)
    got = payload.get("key") or {}
    for name in ("raw_sha256", "raw_bytes", "version", "python"):
        if got.get(name) != want[name]:
            return None
    try:
        stats = payload["stats"]
        civs = payload["civs"]
        civs_start = payload["civs_start"]
        gv = payload["gv"]
        tail = payload["tail"]
        how = payload["how"]
    except KeyError:
        return None
    # The shape checks below catch a file written by a build whose parser
    # produced different tables.  `CACHE_VERSION` is the primary guard; these
    # cost nothing and turn a corrupt file into a re-parse instead of a
    # `KeyError` five screens later.
    if not isinstance(stats, dict) or not isinstance(civs, list) or not civs:
        return None
    if not isinstance(civs_start, int) or not isinstance(gv, int):
        return None
    if not isinstance(tail, int) or not isinstance(how, str):
        return None
    return stats, civs, civs_start, gv, tail, how


def clear():
    """Delete the cache file.  Returns True when something was removed."""
    try:
        os.remove(cache_path())
        return True
    except OSError:
        return False


def describe():
    """`{path, exists, bytes, age}` for the diagnostics endpoint."""
    path = cache_path()
    try:
        st = os.stat(path)
        return {"path": path, "exists": True, "bytes": st.st_size,
                "age": round(time.time() - st.st_mtime, 1)}
    except OSError:
        return {"path": path, "exists": False, "bytes": 0, "age": None}

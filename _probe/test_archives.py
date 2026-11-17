"""`aoe2mod/mod/archives.py` keeps official `.dat` builds, and every promise it makes holds.

The module exists so a stale mod can be traced back to the official build it was
made from.  That is only useful if the shelf is trustworthy, so this suite attacks
the four ways a local store lies: it re-does work when it should be idempotent, it
serves a blob that is no longer the thing its name says, it dies on a damaged index
instead of starting over, and it deletes the one build that must be kept.

Nothing here touches the player's real records: `AOE2MOD_STATE_DIR` is pointed at a
temp dir BEFORE `aoe2mod` is imported, because that env var is read at call time by
`provenance.state_dir()` but the import order is the thing that has actually bitten
this project before (see `provenance.py`'s note on `AOE2MOD_STATE`).

Measured on this machine, 2026-11-09, 11.9 MB / 93,272,287 bytes inflated:

    note_official, first call  (copy path)      ~0.11 s
    note_official, second call (idempotent)     ~0.01 s
"""
import hashlib
import _gamepaths as GP
import os
import shutil
import sys
import tempfile
import time

# The state dir must be redirected before anything resolves it.
_TMP = tempfile.mkdtemp(prefix="archives_suite_")
os.environ["AOE2MOD_STATE_DIR"] = _TMP
os.environ.pop("AOE2MOD_STATE", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.mod import archives as AR          # noqa: E402
from aoe2mod.mod import provenance as PV        # noqa: E402

GAME = GP.GAME
SHIPPED = os.path.join(GAME, AR.DAT_REL)
RAW_BYTES = 93272287
HEAD32 = b"VER 8.9\x00"

FAILS = []


def check(ok, label, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def _blob_mtime(sha):
    p = AR.blob_path(sha)
    return os.stat(p).st_mtime_ns if os.path.isfile(p) else None


def main():
    try:
        print("=== 0. the state dir is the temp one, not the player's")
        check(os.path.abspath(PV.state_dir()) == os.path.abspath(_TMP),
              "state_dir() follows AOE2MOD_STATE_DIR", PV.state_dir())
        check(os.path.dirname(AR.archive_dir()) == os.path.abspath(_TMP),
              "the archive lives under it", AR.archive_dir())

        print()
        print("=== 1. the game's own .dat is archived, once")
        t0 = time.time()
        ent = AR.note_official(GAME)
        first_ms = (time.time() - t0) * 1000.0
        check(isinstance(ent, dict), "note_official returned an entry", type(ent).__name__)
        if not isinstance(ent, dict):
            raise SystemExit("no entry; nothing below can be tested")
        sha = ent["sha256"]
        ix = AR.load_index()
        check(len(ix["entries"]) == 1, "exactly one entry", sorted(ix["entries"]))
        check(ent.get("raw_bytes") == RAW_BYTES, "raw_bytes is 93,272,287", ent.get("raw_bytes"))
        check(ent.get("ver") == "VER 8.9", "ver is VER 8.9", ent.get("ver"))
        check(os.path.isfile(AR.blob_path(sha)), "the blob exists", AR.blob_path(sha))
        check(ent.get("path") == AR.blob_path(sha), "entry.path is the blob", ent.get("path"))
        check(ent.get("src") == SHIPPED, "src names the game file", ent.get("src"))
        # The blob must be the compressed stream the engine reads, not the 93 MB
        # raw one: `raw_of` would happily inflate an already-raw file too, so the
        # only place this shows up is disk size.  And it must be the game's file
        # BYTE FOR BYTE -- that equality is the only mechanical proof that `note()`
        # took the copy path instead of re-deflating (a re-deflate yields a
        # different length: 11,539,019 measured against the shipped 11,963,833).
        blob_bytes = os.path.getsize(AR.blob_path(sha))
        check(blob_bytes == ent.get("file_bytes") and blob_bytes < 20000000,
              "and the blob is compressed, not the raw stream", blob_bytes)
        check(blob_bytes == os.path.getsize(SHIPPED),
              "and it is the game's own compressed file, copied verbatim",
              (blob_bytes, os.path.getsize(SHIPPED)))
        check(first_ms < 300.0,
              "so the first call did not spend 573 ms deflating", "%.1f ms" % first_ms)

        print()
        print("=== 2. noting it again does no work and changes no byte")
        mtime_before = _blob_mtime(sha)
        t0 = time.time()
        ent2 = AR.note_official(GAME)
        second_ms = (time.time() - t0) * 1000.0
        check(len(AR.load_index()["entries"]) == 1, "the index did not grow",
              len(AR.load_index()["entries"]))
        check(ent2.get("first_seen") == ent.get("first_seen"),
              "first_seen is untouched", ent2.get("first_seen"))
        check(_blob_mtime(sha) == mtime_before, "the blob was not rewritten",
              (_blob_mtime(sha), mtime_before))
        print("    first call %.1f ms (copy path), second call %.1f ms (idempotent)"
              % (first_ms, second_ms))

        print()
        print("=== 3. raw_of round-trips the exact stream")
        raw = AR.raw_of(sha)
        check(raw is not None, "raw_of returned bytes", type(raw).__name__)
        if raw is None:
            raise SystemExit("no raw stream; the rest cannot be tested")
        check(hashlib.sha256(raw).hexdigest() == sha, "it hashes to its own name")
        check(raw[:8] == HEAD32[:8], "and starts with the real header", raw[:8])
        check(len(raw) == RAW_BYTES, "and is the full 93 MB", len(raw))

        print()
        print("=== 4. a truncated blob reads as missing, and the next note heals it")
        blob = AR.blob_path(sha)
        with open(blob, "wb") as fh:
            fh.write(b"x" * 100)
        check(AR.raw_of(sha) is None, "raw_of refuses a 100-byte blob")
        healed = AR.note_official(GAME)
        check(isinstance(healed, dict) and healed.get("sha256") == sha,
              "note_official still returns the same entry")
        check(os.path.getsize(blob) == ent.get("file_bytes"),
              "and the blob is whole again", os.path.getsize(blob))
        check(AR.raw_of(sha) is not None, "so raw_of works again")
        check(len(AR.load_index()["entries"]) == 1, "and no second entry appeared",
              len(AR.load_index()["entries"]))

        print()
        print("=== 5. garbage in the index is not fatal")
        with open(AR.index_path(), "wb") as fh:
            fh.write(b"\x00\xff this is not json \x00" * 40)
        ix = AR.load_index()
        check(ix == {"version": 1, "entries": {}}, "load_index returns the empty shape", ix)
        again = AR.note_official(GAME)
        check(isinstance(again, dict) and again.get("sha256") == sha,
              "note_official reindexes it", (again or {}).get("sha256"))
        check(len(AR.load_index()["entries"]) == 1, "and the index holds it again",
              len(AR.load_index()["entries"]))
        # The blob was already correct on disk, so the heal must have been the
        # idempotent-size path plus a fresh index write -- not a 93 MB deflate.
        check(os.path.getsize(blob) == ent.get("file_bytes"), "the blob was not touched",
              os.path.getsize(blob))

        print()
        print("=== 6. best_base finds the identical build")
        t0 = time.time()
        best = AR.best_base(raw, "VER 8.9")
        best_ms = (time.time() - t0) * 1000.0
        check(best.get("sha256") == sha, "it picks the official build", best.get("sha256"))
        check(best.get("diff_bytes") == 0, "with zero differing bytes", best.get("diff_bytes"))
        check(best.get("same_len") is True, "and same_len is True")
        check(best.get("candidates") == 1, "one candidate compared", best.get("candidates"))
        print("    best_base over %d blob(s): %.1f ms" % (best.get("candidates") or 0, best_ms))

        print()
        print("=== 7. prune deletes the oldest and keeps the newest")
        twice = raw[:4000000] + bytes([raw[4000000] ^ 0xFF]) + raw[4000001:]
        other = AR.note(twice, label="probe: one flipped byte")
        check(other["sha256"] != sha, "a flipped byte makes a distinct sha",
              other["sha256"][:16])
        check(other.get("raw_bytes") == RAW_BYTES, "and it is the same raw length",
              other.get("raw_bytes"))
        check(len(AR.load_index()["entries"]) == 2, "two entries now",
              len(AR.load_index()["entries"]))
        # `keep=1` keeps the NEWEST `first_seen`, which is the blob just noted --
        # so the official build is the one that goes.  That is the documented rule,
        # not an accident: a caller that wants the official build protected passes
        # a bigger `keep`, and `note_official` is what puts it back.
        removed = AR.prune(keep=1)
        left = AR.load_index()["entries"]
        check(len(left) == 1, "prune left one entry", sorted(left))
        check(len(removed) == 1, "and reported one removal", removed)
        check(removed[0] == sha, "the pruned sha is the OLDER entry", removed)
        check(removed[0] not in left, "it is gone from the index", sorted(left))
        check(not os.path.isfile(AR.blob_path(removed[0])), "and its blob is deleted",
              AR.blob_path(removed[0]))
        check(other["sha256"] in left, "the newest entry survived", sorted(left))
        check(os.path.isfile(AR.blob_path(other["sha256"])), "with its blob intact")
        check(AR.prune(keep=1) == [], "pruning again removes nothing")
        # `keep=0` must behave like 1 rather than emptying the shelf: deleting the
        # build the game currently ships is never what a caller means.
        check(AR.prune(keep=0) == [], "and keep=0 does not empty the archive",
              sorted(AR.load_index()["entries"]))

        print()
        if FAILS:
            print("FAIL: %s" % FAILS)
            return 1
        print("PASS")
        return 0
    except SystemExit:
        raise
    except Exception as exc:                       # noqa: BLE001
        # A raised exception exits non-zero with no FAIL line, which reads like a
        # broken harness rather than a broken product -- the same lesson
        # `_probe/test_repair.py` records in its section F.
        import traceback
        traceback.print_exc()
        print("FAIL: %s: %s" % (type(exc).__name__, exc))
        return 1
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

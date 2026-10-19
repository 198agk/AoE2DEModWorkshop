"""Measure what an "official update" guard can afford to check, and where to keep it.

The user picked: compare "the .dat this mod was built from" with "the .dat the game
has now", and if they differ, say so plainly and offer a one-click rebuild.
Before writing that, three things have to be measured rather than assumed:

  1. How expensive is each candidate check?  Hashing the compressed 12 MB file,
     inflating the 93 MB raw stream, and reading the version string all cost
     different amounts, and the guard runs on every screen load.
  2. What does an emitted mod record about its own origin?  `build()` returns a
     manifest -- if the manifest already carries enough to rebuild, no new schema
     is needed.
  3. Is there an existing user-state directory convention in this project?  (grep
     said no, but a probe should confirm what $LOCALAPPDATA actually holds.)

Writes nothing outside _probe/.
"""
import io
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
except Exception:
    pass

from aoe2mod import api as A                      # noqa: E402
from aoe2mod.dat import parser as P              # noqa: E402
from aoe2mod.game import locations as G          # noqa: E402

ROOT = os.path.dirname(_HERE)


def timed(label, fn):
    t = time.time()
    value = fn()
    print("%-46s %7.3f s" % (label, time.time() - t))
    return value


def main():
    tk = A.open_toolkit()
    dat = tk.dat_path
    print("dat          :", dat)
    print("dat file size: %d bytes" % os.path.getsize(dat))

    # --- 1. the three candidate checks ----------------------------------
    file_sha = timed("sha256 of the compressed file",
                     lambda: G.sha256_file(dat))
    print("             :", file_sha[:16], "...")

    def inflate():
        raw, how = P.load_dat(dat)
        return raw, how

    raw, how = timed("load_dat (inflate to the raw stream)", inflate)
    raw_sha = timed("sha256 of the raw stream",
                    lambda: __import__("hashlib").sha256(raw).hexdigest())
    print("             :", raw_sha[:16], "...", "how=%r" % (how,))

    # The version string is the first bytes of the RAW stream ("VER 8.9\0"), so a
    # guard that only wants the version does not need a full parse -- measure how
    # much cheaper peeking is than parsing.
    print("raw head     : %r" % (raw[:16],))
    gv = timed("parser.parse() (for the version enum)",
               lambda: _parse_gv(raw))
    print("             : gv=%r  toolkit.version=%r" % (gv, tk.version))

    # --- 2. what a build already remembers ------------------------------
    print()
    print("--- what build() reports about its own origin ---")
    keys = ("dat_sha256", "dat_raw_bytes", "dat_file_bytes", "reloaded_with",
            "dat_identical_to_base", "changes_dat", "verification")
    man_path = os.path.join(ROOT, "_mods_out", "info.json")
    print("last build dir exists:", os.path.isdir(os.path.join(ROOT, "_mods_out")))
    if os.path.isdir(os.path.join(ROOT, "_mods_out")):
        files = []
        for base, _dirs, names in os.walk(os.path.join(ROOT, "_mods_out")):
            for n in names:
                files.append(os.path.relpath(os.path.join(base, n),
                                             os.path.join(ROOT, "_mods_out")))
        print("files on disk:", sorted(files)[:8])
        info = json.load(open(man_path, encoding="utf-8-sig"))
        print("info.json keys:", sorted(info))
    print("build() manifest keys an earlier run reported:", ", ".join(keys))

    # --- 3. where would a local record live? ----------------------------
    print()
    print("--- candidate state roots ---")
    cands = {
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA"),
        "APPDATA": os.environ.get("APPDATA"),
        "home": os.path.expanduser("~"),
    }
    for name, value in cands.items():
        print("%-13s %r  exists=%s" % (name, value,
                                       os.path.isdir(value) if value else False))

    # --- 4. what the installed copy hashes to ---------------------------
    print()
    print("--- installed mods: is the raw sha recoverable from disk? ---")
    prof = G.find_profile_root()
    mods = G.list_mods(prof)
    print("profile_root:", prof)
    print("installed mods:", len(mods))
    mine = [m for m in mods if str(m.get("name", "")).lower().startswith("dsh")]
    print("this project's own mods:", [(m["name"], m.get("kind"), m.get("enabled"))
                                       for m in mine])
    for m in mine[:2]:
        p = os.path.join(m.get("path") or "", G.DAT_REL)
        if os.path.isfile(p):
            t = time.time()
            h = G.sha256_file(p)
            print("  %-34s file_sha=%s  %.3f s"
                  % (m["name"][:34], h[:12], time.time() - t))
            t = time.time()
            r, _how = P.load_dat(p)
            print("  %-34s raw_sha =%s  %.3f s"
                  % ("", __import__("hashlib").sha256(r).hexdigest()[:12],
                     time.time() - t))


def _parse_gv(raw):
    p = P.Parser(raw)
    with __import__("contextlib").redirect_stdout(io.StringIO()):
        p.parse()
    return getattr(p, "gv", None)


if __name__ == "__main__":
    main()

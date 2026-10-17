"""v2: raw-byte diff of the two inflated .dat streams + TEXT diff of the JSON pair.

Pure stdlib. No aoe2mod import. Reads the raw/ files written by v1.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import difflib
import hashlib
import json
import os

OUT = _HERE_PATH("_probe", "team", "verifier")
RAW = os.path.join(OUT, "raw")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

REL_TREE = os.path.join("resources", "_common", "dat", "CivTechTrees", "BRITONS.json")
REL_PANEL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")

def load_raw(name):
    with open(os.path.join(RAW, name), "rb") as f:
        return f.read()

def runs_of_difference(a, b):
    """Contiguous [start,end) runs where a != b. Inputs must be equal length."""
    assert len(a) == len(b), "lengths differ: %d vs %d" % (len(a), len(b))
    runs = []
    i = 0
    n = len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs

def main():
    gm = load_raw("dat_game.raw")
    md = load_raw("dat_mod.raw")
    print("== raw .dat positional diff ==")
    print("game raw len =", len(gm), " mod raw len =", len(md))

    runs = runs_of_difference(gm, md)
    total_bytes = sum(e - s for s, e in runs)
    print("differing runs      :", len(runs))
    print("differing byte count:", total_bytes)

    # group runs by (dx = changed-length, value pattern)
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 8:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    print("runs merged with <=8B gap:", len(merged))

    print()
    print("-- every differing run, with game->mod byte values --")
    for s, e in runs:
        g = gm[s:e]
        m = md[s:e]
        print("  off %10d..%-10d len=%2d  %s -> %s" % (s, e, e - s, g.hex(), m.hex()))

    strides = [runs[i + 1][0] - runs[i][0] for i in range(len(runs) - 1)]
    print()
    print("strides between consecutive changed runs:",
          sorted(set(strides)), "| distinct:", len(set(strides)))

    # Interpreting each 2-byte changed run as a little-endian int16:
    print()
    print("-- interpreted as LE int16 --")
    for s, e in runs:
        if e - s == 2:
            gv = int.from_bytes(gm[s:e], "little", signed=True)
            mv = int.from_bytes(md[s:e], "little", signed=True)
            print("  off %10d : %d -> %d" % (s, gv, mv))
        else:
            print("  off %10d : len != 2 (%d) -- not a bare int16" % (s, e - s))

    # 32-bit int16 pairs straddling: also test whether 25->1000 is the only change
    pats = {}
    for s, e in runs:
        pats[(gm[s:e], md[s:e])] = pats.get((gm[s:e], md[s:e]), 0) + 1
    print()
    print("-- distinct (game_bytes -> mod_bytes) patterns --")
    for k, v in sorted(pats.items(), key=lambda kv: -kv[1]):
        print("  %-14s -> %-14s  x%d" % (k[0].hex(), k[1].hex(), v))

    result = {
        "game_raw_len": len(gm), "mod_raw_len": len(md),
        "run_count": len(runs), "differing_bytes": total_bytes,
        "runs": [{"start": s, "end": e,
                  "game_hex": gm[s:e].hex(), "mod_hex": md[s:e].hex()} for s, e in runs],
        "strides": strides,
    }
    with open(os.path.join(OUT, "v2_dat_rawdiff.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    # ---------------- JSON TEXT DIFF ----------------
    print()
    print("== JSON TEXT diffs (mod vs game) ==")
    for rel, tag in ((REL_TREE, "tree"), (REL_PANEL, "panel")):
        mg = os.path.join(MOD, rel)
        gg = os.path.join(GAME, rel)
        with open(mg, "rb") as f:
            mb = f.read()
        with open(gg, "rb") as f:
            gb = f.read()
        print()
        print("--- %s : mod=%d B  game=%d B  %s" %
              (tag, len(mb), len(gb), "IDENTICAL" if mb == gb else "DIFFER"))
        print("    mod  sha256 =", hashlib.sha256(mb).hexdigest())
        print("    game sha256 =", hashlib.sha256(gb).hexdigest())
        if mb == gb:
            continue

        # first divergence
        first = next(i for i in range(min(len(mb), len(gb))) if mb[i] != gb[i])
        print("    first differing byte offset:", first)
        print("      context game:", gb[max(0, first - 40):first + 40])
        print("      context mod :", mb[max(0, first - 40):first + 40])

        # byte-level diff size via difflib on bytes-as-lines? use line diff instead
        mtxt = mb.decode("utf-8")
        gtxt = gb.decode("utf-8")
        mlines = mtxt.splitlines(keepends=True)
        glines = gtxt.splitlines(keepends=True)
        print("    line counts: mod=%d game=%d" % (len(mlines), len(glines)))

        sm = difflib.SequenceMatcher(None, glines, mlines, autojunk=False)
        opcodes = sm.get_opcodes()
        changed = [op for op in opcodes if op[0] != "equal"]
        print("    changed line-blocks:", len(changed))
        dbytes = 0
        for tag2, i1, i2, j1, j2 in changed:
            dbytes += len("".join(glines[i1:i2]).encode()) + len("".join(mlines[j1:j2]).encode())
        print("    bytes appearing in changed blocks (game-side + mod-side):", dbytes)

        diff_text = "".join(difflib.unified_diff(glines, mlines,
                                                 fromfile="GAME/" + tag, tofile="MOD/" + tag))
        dest = os.path.join(OUT, "diff_%s.txt" % tag)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(diff_text)
        print("    unified diff lines:", diff_text.count("\n"), "-> wrote", dest)

        # char-level count of differing bytes ignoring alignment, for the record
        if len(mb) == len(gb):
            same_len_diff = sum(1 for x, y in zip(mb, gb) if x != y)
            print("    same-length positional differing bytes:", same_len_diff)

    print("\ndone")

if __name__ == "__main__":
    main()

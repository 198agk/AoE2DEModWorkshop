"""Measure the three ways to shrink a reskin mod, and say what each costs.

The v12 villager mod is 438 MB across 466 files, but only EIGHT of those files
have distinct contents -- `fill` writes the same sheep animation under many
target names, and `resource_variants` adds eight more copies of the same pair of
pictures.  So the question "must it be this big" has three different answers
depending on what "big" means:

  1. bytes on the player's disk  -> hardlinks make it 6.7 MB
  2. bytes in the upload        -> a deflate zip collapses the duplicates
  3. bytes the engine must read -> unchanged; the engine still wants 466 names

Option 4, NOT shipping any picture at all by rewriting the `.dat`'s graphics
`file` strings to point at the shipped sheep files, would be the smallest of all
-- but it changes the LENGTH of a string inside a section that is addressed by a
POINTER ARRAY, so this probe measures whether the writer can even do it before
anything is promised to the user.

Run:
  python _probe\probe_size_options.py
"""

import collections
import hashlib
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_dshtest_v12")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    files = []
    for root, _dirs, names in os.walk(MOD):
        for n in names:
            p = os.path.join(root, n)
            files.append((os.path.relpath(p, MOD).replace("\\", "/"),
                          os.path.getsize(p)))
    files.sort()
    total = sum(s for _r, s in files)
    print("mod: %s" % MOD)
    print("files %d / %.1f MB" % (len(files), total / 1e6))

    # ---- 1. how much of it is the same bytes over and over ----------------
    by_sha = collections.defaultdict(list)
    for rel, size in files:
        if not rel.endswith(".sld"):
            continue
        h = hashlib.sha256()
        with open(os.path.join(MOD, rel), "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        by_sha[h.hexdigest()].append((rel, size))
    uniq = sum(v[0][1] for v in by_sha.values())
    print()
    print("1  DISTINCT CONTENTS")
    print("   distinct .sld contents: %d of %d files" % (len(by_sha), len(files) - 1))
    print("   bytes actually unique : %.1f MB" % (uniq / 1e6))
    print("   bytes that are copies : %.1f MB" % ((total - uniq) / 1e6))
    for sha, group in sorted(by_sha.items(), key=lambda kv: -len(kv[1]))[:3]:
        print("     %dx %8.0f KB  %s" % (len(group), group[0][1] / 1024.0,
                                          group[0][0]))

    # ---- 2. what a deflate zip would weigh ------------------------------
    zpath = os.path.join(os.path.dirname(MOD), "_probe_v12.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, _size in files:
            z.write(os.path.join(MOD, rel), rel)
    zsize = os.path.getsize(zpath)
    print()
    print("2  A DEFLATE ZIP OF THE SAME FOLDER")
    print("   zip (deflate 6): %.1f MB  (%.1fx smaller)" % (
        zsize / 1e6, total / float(zsize)))
    print("   path: %s" % zpath)

    # ---- 3. hardlinks: same bytes, one inode ---------------------------
    print()
    print("3  HARDLINKS (local install only)")
    print("   %d files would become %d inodes; folder shrinks to %.1f MB"
          % (len(files), len(by_sha) + 1, uniq / 1e6))
    print("   a zip still carries every path, so this helps disk, not upload")

    # ---- 4. can the .dat retarget a graphics record's file string? ------
    print()
    print("4  RETARGETING INSTEAD OF COPYING (would ship no picture at all)")
    import aoe2mod.api as A
    tk = A.open_toolkit(GAME)
    tk._ensure()
    gfx = tk._stats["graphics"]
    by_id = dict((g["id"], g) for g in gfx)
    # A record a villager uses, and the sheep record we would point it at.
    recs = [g for g in gfx if (g.get("file") or "").startswith("u_vil_male_villager_")]
    print("   villager graphics records with a modern file name: %d" % len(recs))
    for g in recs[:6]:
        print("     gfx %-5d %-34s -> %s" % (g["id"], g.get("name"), g.get("file")))
    sheep = [g for g in gfx if (g.get("file") or "").startswith("a_herd_sheep_")]
    print("   sheep graphics records: %d" % len(sheep))
    lens = sorted(set(len(g["file"]) for g in recs))
    print("   villager file-name lengths: %s" % lens)
    _l = sorted(set(len(g["file"]) for g in sheep))
    print("   sheep file-name lengths   : %s" % _l)
    print("   -> a retarget changes a u16-length-prefixed string, so the record")
    print("      changes LENGTH, and the graphics section is addressed by a")
    print("      pointer array: every later body would have to move.")

    # Is that pointer array rewritten by our writer?
    import aoe2mod.dat.writer as W
    src = open(W.__file__, "r", encoding="utf-8").read()
    for needle in ("def write_graphics", "graphics_offsets", "pointer",
                   "def serialize_dat"):
        print("   writer mentions %-22s %s" % (needle, needle in src))
    print()
    print("MEASURED: the 438 MB is %d distinct pictures written under %d names."
          % (len(by_sha), len(files) - 1))


if __name__ == "__main__":
    main()

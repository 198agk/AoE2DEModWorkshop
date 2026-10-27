# -*- coding: utf-8 -*-
"""Check the release zips against the inputs they were built from.

Why this exists
---------------
`make_publish_pack.py` rewrites `info.json` on purpose -- Title, Author and
Description become the ones a player sees, not "dsh test v12 ...".  So a plain
"are the zips identical to out_dshtest_v12 / v13" answer is meaningless: the
only honest check is *which fields differ, and is that the intended list*.

Everything else must match byte for byte.  The `.dat` in the light pack is the
one case where that matters a lot: it is a raw-deflate stream, so a single
wrong byte would still unzip and only fail inside the game.

Reads only.  Prints one line per pack and exits non-zero on any surprise.
"""
import hashlib
import json
import os
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# The publish script's own intent: rebuild these three fields, leave the rest.
RESTYLED = {"Title", "Author", "Description"}

# Retail `.dat` is 93,268,152 B.  A full-graphics mod carries a compressed copy
# (93,265,638 B inflated); a light mod carries the same bytes renamed.
FULL_DAT_INFLATED = None      # the full pack has no .dat at all
LIGHT_DAT_INFLATED = 93265638

PACKS = [
    {"zip": "村民变成绵羊.zip", "src": "_probe/out_dshtest_v12",
     "expect_sld": 466, "expect_dat": 0, "dat_inflated": FULL_DAT_INFLATED},
    {"zip": "村民变成绵羊-轻量版.zip", "src": "_probe/out_dshtest_v13",
     "expect_sld": 0, "expect_dat": 1, "dat_inflated": LIGHT_DAT_INFLATED},
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check(pack):
    zpath = os.path.join(REPO, "发布包", pack["zip"])
    src = os.path.join(REPO, pack["src"].replace("/", os.sep))
    ok = True
    print("=" * 72)
    print(pack["zip"])

    if not os.path.isfile(zpath):
        print("  MISSING %s" % zpath)
        return False
    z = zipfile.ZipFile(zpath)
    names = [n for n in z.namelist() if not n.endswith("/")]

    # 1. every entry that is not info.json must be byte-identical to the source
    diff = []
    missing = []
    for n in names:
        if n == "info.json":
            continue
        p = os.path.join(src, n.replace("/", os.sep))
        if not os.path.isfile(p):
            missing.append(n)
            continue
        if sha(z.read(n)) != sha(open(p, "rb").read()):
            diff.append(n)
    print("  entries          : %d" % len(names))
    print("  not in source    : %d" % len(missing))
    print("  bytes differ     : %d" % len(diff))
    for n in (missing + diff)[:4]:
        print("     %s" % n)
    ok = ok and not missing and not diff

    # 2. info.json must differ ONLY in the restyled fields
    a = json.loads(z.read("info.json").decode("utf-8-sig"))
    b = json.loads(open(os.path.join(src, "info.json"), "rb")
                   .read().decode("utf-8-sig"))
    changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    print("  info.json fields : %s" % sorted(a))
    print("  restyled         : %s" % sorted(changed))
    if changed != RESTYLED:
        print("     expected exactly %s" % sorted(RESTYLED))
        ok = False
    if a.get("CacheStatus") != 0:
        # Every one of the 21 mods already on this machine has 0.  A subscriber
        # seeing 1 gets a silently stale copy, and nothing in the game says so.
        print("     CacheStatus     : %r  (must be 0)" % a.get("CacheStatus"))
        ok = False
    tb = len(a["Title"].encode("utf-8"))
    print("  Title            : %r  (%d UTF-8 bytes, limit 100)" % (a["Title"], tb))
    if tb > 100:
        ok = False
    if "\r\n" not in a.get("Description", ""):
        print("     Description has no CRLF -- the in-game box collapses to one line")
        ok = False

    # 3. the thumbnail must be the size the workshop page wants
    if "thumbnail.png" in names:
        b2 = z.read("thumbnail.png")
        w = int.from_bytes(b2[16:20], "big")
        h2 = int.from_bytes(b2[20:24], "big")
        print("  thumbnail        : %dx%d" % (w, h2))
        if (w, h2) != (1280, 720):
            ok = False

    # 4. counts, and the .dat must inflate to the expected size
    sld = [n for n in names if n.lower().endswith(".sld")]
    dat = [n for n in names if n.lower().endswith(".dat")]
    print("  sld / dat / png  : %d / %d / %d"
          % (len(sld), len(dat), len([n for n in names if n.lower().endswith(".png")])))
    if len(sld) != pack["expect_sld"] or len(dat) != pack["expect_dat"]:
        print("     expected %d sld / %d dat" % (pack["expect_sld"], pack["expect_dat"]))
        ok = False
    for n in dat:
        raw = z.read(n)
        try:
            inflated = zlib.decompress(raw, -15)
        except zlib.error as e:
            print("     %s is not a raw-deflate stream: %s" % (n, e))
            ok = False
            continue
        print("  dat              : %d B on disk -> %d B inflated" % (len(raw), len(inflated)))
        if pack["dat_inflated"] is not None and len(inflated) != pack["dat_inflated"]:
            print("     expected %d B" % pack["dat_inflated"])
            ok = False
        if inflated[:4] != b"VER ":
            print("     header is not 'VER ' -- %r" % inflated[:8])
            ok = False
        else:
            print("  dat header       : VER %d.%d" % (inflated[4], inflated[5]))

    # 5. archive integrity -- a corrupt zip also passes every check above
    bad = z.testzip()
    print("  testzip          : %s" % (bad or "clean"))
    ok = ok and bad is None
    print("  -> %s" % ("OK" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    results = [check(p) for p in PACKS]
    print("=" * 72)
    print("RESULT: %d/%d packs OK" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)

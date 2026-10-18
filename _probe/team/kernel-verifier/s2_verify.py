# -*- coding: utf-8 -*-
"""CLAIM 2 -- an independent, parser-free audit of a real edit.

Only stdlib (zlib/struct/hashlib/json) plus the *game's* civilizations.json is
used.  The product's parser is never imported.  We establish the geometry of
the edited records by self-similarity (a 48-byte record fingerprint), which is
what makes the "all 63 civ copies" claim checkable without trusting the model.
"""
import hashlib
import io
import json
import struct
import sys
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = GAME + r"\resources\_common\dat\empires2_x2_p1.dat"
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")
CIVJSON = GAME + r"\resources\_common\dat\civilizations.json"


def inflate(path, tag):
    blob = open(path, "rb").read()
    d = zlib.decompressobj(-15)
    out = d.decompress(blob) + d.flush()
    print("%-10s file=%d raw=%d eof=%s unused=%d"
          % (tag, len(blob), len(out), d.eof, len(d.unused_data)))
    return out


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def main():
    base = inflate(BASE, "base")
    new = inflate(MOD, "mod")
    assert len(base) == len(new), "length differs"
    print("length delta             :", len(new) - len(base))

    # ---- global diff -----------------------------------------------------
    diffs = [i for i in range(len(base)) if base[i] != new[i]]
    print("changed byte count       :", len(diffs))
    runs, cur = [], [diffs[0]]
    for x in diffs[1:]:
        if x == cur[-1] + 1:
            cur.append(x)
        else:
            runs.append((cur[0], len(cur)))
            cur = [x]
    runs.append((cur[0], len(cur)))
    print("changed runs             :", len(runs))
    print("run widths               :", sorted(set(w for _, w in runs)))
    print("every change is a single in-place byte:",
          all(w == 1 for _, w in runs))

    # ---- split into primary / mirror pairs -------------------------------
    offs = [o for o, _ in runs]
    pairs, used = [], set()
    for o in offs:
        if o in used:
            continue
        cand = [x for x in offs if 0 < x - o <= 200 and x not in used]
        assert cand, "unpaired change at %d" % o
        pairs.append((o, min(cand)))
        used.add(o); used.add(min(cand))
    gaps = sorted(set(b - a for a, b in pairs))
    print("primary/mirror pairs     :", len(pairs))
    print("primary->mirror gaps     :", gaps)

    # ---- what the two slots hold ----------------------------------------
    kinds = {}
    for a, b in pairs:
        hb, hn = base, new
        u16_b = struct.unpack_from("<H", hb, a - 1)[0] if False else None
        # u16 containing the changed byte: try both alignments
        cands = []
        for align in (a - 1, a):
            if align < 0:
                continue
            v0 = struct.unpack_from("<H", hb, align)[0]
            v1 = struct.unpack_from("<H", hn, align)[0]
            if v1 - v0 in (0, 1, 2) and v0 < 0x8000:
                cands.append(("u16@%+d" % (align - a), v0, v1))
        f0 = struct.unpack_from("<f", hb, a - 3)[0]
        f1 = struct.unpack_from("<f", hn, a - 3)[0]
        key = (tuple(cands), round(f0, 6), round(f1, 6))
        kinds.setdefault(key, []).append((a, b))
    for key, lst in kinds.items():
        print("  pattern %s  floats %.6f->%.6f  count=%d  first=%d"
              % (str(key[0]), key[1], key[2], len(lst), lst[0][0]))

    # ---- record geometry via a self-similarity fingerprint ---------------
    d0 = pairs[0][0]
    PREFIX = 48
    prints = []
    for a, _ in pairs:
        prints.append(base[a - PREFIX:a])
    uniq = set(prints)
    print("distinct 48B prefixes    :", len(uniq))
    fp = prints[0]
    hits = find_all(base, fp)
    print("fingerprint occurrences  :", len(hits))
    hit_offsets = [h + PREFIX for h in hits]
    print("all fingerprint tails changed:",
          all(h in set(offs) for h in hit_offsets))
    print("changed primaries covered by fingerprint:",
          len([a for a, _ in pairs if a in set(hit_offsets)]), "/", len(pairs))

    # are the 63 copies one-per-civilization?  Anchor on the civ table.
    civ = json.load(io.open(CIVJSON, encoding="utf-8-sig"))
    cl = civ["civilization_list"]
    print("civilizations.json civs  :", len(cl))
    print("fingerprint deltas from first hit (first 8):",
          [h - hits[0] for h in hits[:8]])

    # ---- +/-200 byte neighbourhood audit ---------------------------------
    offs_set = set(offs)
    bad = []
    for a, b in pairs:
        lo, hi = a - 200, b + 200
        near = [o for o in offs if lo <= o <= hi]
        allowed = {a, b}
        extra = [o for o in near if o not in allowed]
        if extra:
            bad.append((a, b, extra))
    print("neighbourhood violations :", len(bad))
    for rec in bad[:5]:
        print("   ", rec)

    # ---- value checks ----------------------------------------------------
    ok_primary = all(struct.unpack_from("<H", base, a - 1)[0] == 4 and
                     struct.unpack_from("<H", new, a - 1)[0] == 6 for a, _ in pairs)
    ok_mirror = all(struct.unpack_from("<f", base, b - 3)[0] == 4.0 and
                    struct.unpack_from("<f", new, b - 3)[0] == 6.0 for _, b in pairs)
    print("all primaries 4 -> 6     :", ok_primary)
    print("all mirrors   4.0 -> 6.0 :", ok_mirror)

    print("sha256 base raw          :", hashlib.sha256(base).hexdigest())
    print("sha256 mod raw           :", hashlib.sha256(new).hexdigest())


if __name__ == "__main__":
    main()

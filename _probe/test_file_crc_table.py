# -*- coding: utf-8 -*-
"""What broke when the .dat was copied into the game directory, stated as a test.

The player got, before entering any game:

    加载数据集失败。
    有一个重要的游戏文件发生问题。请验证您的游戏文件后再试一次。
    resources\\_common\\dat\\empires2_x2_p1.dat

and asked why.  An earlier answer of mine called this "a format problem, not an
anti-cheat problem".  Half of that was right (nothing inspects what the edit
DOES) and half was wrong (it is not a parse failure either).  This file records
what the binary actually says, so the next person does not have to re-derive it:

  * the second line is IDS_WARN_USER_FILE_CRC_BREAK, a NAMED key -- which is why
    three earlier searches for it in the numeric string table came up empty.  The
    zh table mixes numeric ids and NAMED keys (IDS_*) in one file, and every
    loader in this repo matches only the numeric half;
  * the EXE compiles in the expected crc32 of 50 shipped files and compares them
    in per-file code, not from a data table: the five anchors first found at a
    112-byte stride are five copies of ONE instruction template, and anchoring on
    the two stable dwords of that template finds all 50;
  * empires2_x2_p1.dat is in that set; futuravailableunits.json is NOT.

That last line is the product-relevant consequence: the .dat sitting in the
install directory is held to a compiled-in hash, while the availability panel is
not, so a loose panel file is legitimate where a replaced .dat is not.  It also
fits every successful experiment so far -- a data mod never writes into the
install directory, it ships its own file under its own path.

HONESTY BOUNDARY: this proves the dialog is a checksum on files the player
replaced, and that the panel is not in the checked set.  It does NOT prove the
game never validates the panel by some other means.
"""
import os
import _gamepaths as GP
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GAME = os.environ.get("AOE2DE_GAME_ROOT") or GP.GAME
EXE = os.path.join(GAME, "AoE2DE_s.exe")
DATDIR = os.path.join(GAME, "resources", "_common", "dat")
STR_ZH = os.path.join(GAME, "resources", "zh", "strings", "key-value",
                       "key-value-strings-utf8.txt")

# The template's stable dwords.  The crc immediate sits 24 bytes before the tail
# and 16 bytes after the head -- both offsets verified by dumping three instances.
TAIL = struct.pack("<I", 0x4588C033)
HEAD = struct.pack("<I", 0x48000002)

CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok), detail))
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                        ("  :: " + detail) if detail else ""))
    return ok


class Skip(Exception):
    pass


def crc_table(exe):
    """[(exec_offset, expected_crc32)] for every compiled-in per-file check."""
    out = []
    start = 0
    while True:
        i = exe.find(TAIL, start)
        if i < 0:
            break
        if i - 16 >= 0 and exe[i - 16:i - 12] == HEAD:
            out.append((i - 24, struct.unpack_from("<I", exe, i - 24)[0]))
        start = i + 1
    return out


def covered_by_hash():
    """{crc32: path} for the files this check set can plausibly cover.

    Skips the big binary media (sprites, audio, fonts) purely for runtime: the
    covered set is shipped scripts, JSON and dat files, all small.
    """
    skip_ext = {".sld", ".dds", ".wem", ".bik", ".ttf", ".png", ".exe", ".dll"}
    out = {}
    for root, _dirs, names in os.walk(GAME):
        for name in names:
            if os.path.splitext(name)[1].lower() in skip_ext:
                continue
            p = os.path.join(root, name)
            try:
                if os.path.getsize(p) > 64 << 20:
                    continue
                with open(p, "rb") as fh:
                    out[zlib.crc32(fh.read()) & 0xFFFFFFFF] = p
            except OSError:
                continue
    return out


def main():
    if not os.path.exists(EXE):
        raise Skip("no AoE2DE_s.exe under %s" % GAME)

    print("== A. the dialog's second line names a checksum, not a parser ==")
    zh = open(STR_ZH, "rb").read().decode("utf-8-sig")
    line = [ln for ln in zh.splitlines()
            if ln.startswith("IDS_WARN_USER_FILE_CRC_BREAK")]
    check("the second line is a NAMED key (IDS_*), not a numeric id",
          len(line) == 1, line[0][:60] if line else "not found")
    text = line[0] if line else ""
    check("that key's text tells the player to verify the game FILES",
          "游戏文件" in text and "验证" in text, text[:60])
    check("the table really does mix named keys with numeric ids, which is why "
          "a numeric-only loader cannot see it",
          ("IDS_WARN_USER_FILE_CRC_BREAK" in zh)
          and any(ln[:1].isdigit() for ln in zh.splitlines()
                  if " " in ln or '"' in ln))

    print("== B. the expected hashes are compiled into the EXE ==")
    with open(EXE, "rb") as fh:
        exe = fh.read()
    table = crc_table(exe)
    check("one instruction template carries the expected crc "
          "(%d instances)" % len(table), len(table) >= 20,
          "all distinct: %s" % (len({c for _o, c in table}) == len(table)))
    check("they are not stored as a flat dword table (no run of adjacent crcs)",
          all(abs(a[0] - b[0]) > 16 for a, b in zip(sorted(table),
                                                    sorted(table)[1:])),
          "min gap = %d" % min(abs(a[0] - b[0]) for a, b in
                               zip(sorted(table), sorted(table)[1:])))

    print("== C. what the set covers, and what it does not ==")
    covered = {c for _o, c in table}
    files = covered_by_hash()

    datp = os.path.join(DATDIR, "empires2_x2_p1.dat")
    with open(datp, "rb") as fh:
        dat_crc = zlib.crc32(fh.read()) & 0xFFFFFFFF
    check("empires2_x2_p1.dat is covered, so replacing it trips the dialog",
          dat_crc in covered, "crc=0x%08x" % dat_crc)

    for name in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
        p = os.path.join(DATDIR, name)
        if not os.path.exists(p):
            raise Skip("%s is not installed" % name)
        with open(p, "rb") as fh:
            c = zlib.crc32(fh.read()) & 0xFFFFFFFF
        check("%s is NOT covered, so a loose copy of it is legitimate" % name,
              c not in covered, "crc=0x%08x" % c)

    missing = [o for o, c in table if c not in files]
    # NOT "all 50 match a file here".  That literal is a property of one game
    # version on one machine: on 2026-11-01 three of the fifty (exec offsets
    # 634095 / 634207 / 634319, crc 0x35630df9 / 0xc35cac09 / 0xf95a218c) match
    # NO file anywhere under the install, full tree included -- the game changed
    # or dropped whichever files they were, and the compiled-in table keeps the
    # old hashes.  The claim this suite exists to support is narrower and still
    # holds: the check set is shipped content (the .dat is in it), and the
    # availability panel is not.  So the unmatched entries are REPORTED, and what
    # is asserted is that they are a small minority and never the .dat.
    check("the compiled-in crcs are overwhelmingly shipped files "
          "(%d of %d unmatched, at %r)"
          % (len(missing), len(table), [hex(o) for o in missing]),
          len(missing) * 10 <= len(table),
          "%d candidate files hashed" % len(files))
    check("and none of the unmatched ones is the .dat",
          not (set(missing) and dat_crc not in covered),
          "crc=0x%08x" % dat_crc)

    named = [os.path.relpath(files[c], GAME) for c in covered if c in files]
    check("the covered set is shipped content, not only the .dat (%d files)"
          % len(named), len(named) >= 20,
          "campaigns / rms / dat / json")

    if not CHECKS or any(not ok for _l, ok, _d in CHECKS):
        print("\nFILE CRC TABLE: %d OF %d CHECKS FAILED"
              % (sum(1 for _l, ok, _d in CHECKS if not ok), len(CHECKS)))
        return 1
    print("\nFILE CRC TABLE: %d CHECKS PASSED -- the dialog is a checksum on "
          "files the player replaced, and the availability panel is not in the "
          "checked set" % len(CHECKS))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Skip as exc:
        print("SKIP %s" % exc)
        sys.exit(0)

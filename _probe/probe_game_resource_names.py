"""Does the GAME ship its own resource-type name table?

AGE's `[AoE2DECivResourceNames]` names 3 of the 8 unmapped cost types and stops
at 499.  The game's localized string file has a block starting at 15000 whose
first entries read exactly like that table ("!Food Storage", "Population
Headroom", "Relics Captured"), which suggests a 15000 + id scheme.  If it holds
then the game -- not AGE -- is the authority, and it may name ids AGE cannot.

This prints the whole block plus whatever it says about the ids we care about.
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EN = os.path.join(GAME, "resources", "en", "strings", "key-value",
                  "key-value-strings-utf8.txt")
ZH = os.path.join(GAME, "resources", "zh", "strings", "key-value",
                  "key-value-strings-utf8.txt")

LINE = re.compile(r'^(\d+)\s+"(.*)"\s*$')


def load(path):
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line.strip())
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def main():
    en = load(EN)
    print("english string ids total: %d" % len(en))
    print("zh file exists: %s" % os.path.exists(ZH))

    block = sorted(k for k in en if 15000 <= k <= 15550)
    print()
    print("=== the 15000+ block ===")
    print("entries in 15000..15550: %d  (first %d, last %d)"
          % (len(block), block[0], block[-1]))
    gaps = [k for k in range(block[0], block[-1] + 1) if k not in en]
    print("missing inside that span: %d %s" % (len(gaps), gaps[:20]))
    for k in block[:70]:
        print("  %5d  %s" % (k, en[k]))

    print()
    print("=== the ids this project cares about (candidate scheme 15000 + type) ===")
    declared = [0, 1, 2, 3, 4]
    named = [7, 214, 215]
    unnamed = [501, 506, 508, 513, 514]
    for t in declared + named + unnamed:
        sid = 15000 + t
        tag = ("declared" if t in declared else
               "AGE names it" if t in named else "AGE unnamed")
        print("  type %4d -> string %5d : %-32r  [%s]"
              % (t, sid, en.get(sid), tag))

    # Is the scheme really "15000 + resource id"?  The first five are the ones
    # AGE calls Food/Wood/Stone/Gold Storage + Population Headroom, so compare.
    print()
    print("=== cross-check: does 15000+i agree with AGE for i in 0..4? ===")
    ini = os.path.join(GAME, "Tools_Builds", "AGE3NamesV0007.ini")
    age = {}
    sec = None
    with open(ini, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                sec = line[1:-1]
                continue
            if sec == "AoE2DECivResourceNames" and "=" in line:
                k, _, v = line.partition("=")
                if k.strip().isdigit():
                    age[int(k.strip())] = v.strip()
    for i in range(0, 8):
        g = en.get(15000 + i)
        a = age.get(i)
        same = (g or "").lstrip("!") == (a or "")
        print("  %d  game=%-24r  AGE=%-24r  %s"
              % (i, g, a, "AGREE" if same else "differ"))

    print()
    print("AGE highest named id: %d" % max(age))
    print("AGE 'Unused' slots: %d"
          % sum(1 for v in age.values() if v == "Unused"))
    # what does the game say at the ids AGE declines to name?
    print()
    print("=== game block, looking for the 5 AGE cannot name ===")
    for t in unnamed:
        sid = 15000 + t
        print("  type %4d -> %5d : %r" % (t, sid, en.get(sid)))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "game_resource_name_block.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({str(k): en[k] for k in block}, fh,
                  ensure_ascii=False, indent=1)
    print()
    print("wrote %s (%d entries)" % (out, len(block)))


if __name__ == "__main__":
    main()

"""Two questions the game's 15000+ block raised:

A. Does the game's OWN localized string file give us official Chinese names at
   the same ids (15000 + type)?  If yes, the hand-written 8-entry zh subset in
   `build_resource_labels.py` is unnecessary, and 550 ids get an official name
   instead of 8 hand-translated ones.
B. AGE and the game DISAGREE at exactly one id we care about: 215.  AGE says
   "Mercenary Kipchak Limit", the game says "Bonus Forager Food".  Which one
   describes the slots the dat actually has (unit 1259/1261/1276, amount -1)?
   The kipchak story only holds if 214 and 215 are a pair, so look at both
   tables' neighbours and at every Chinese/English name near there.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LINE = re.compile(r'^(\d+)\s+"(.*)"\s*$')


def load(locale):
    p = os.path.join(GAME, "resources", locale, "strings", "key-value",
                     "key-value-strings-utf8.txt")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line.strip())
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def main():
    en = load("en")
    for loc in ("zh", "zh-Hans", "zh-Hant", "tw", "cn"):
        t = load(loc)
        if t:
            print("locale %-8s ids=%-6d has 15214? %s  15215? %s"
                  % (loc, len(t), t.get(15214) is not None,
                     t.get(15215) is not None))
    print()

    zh = load("zh")
    print("=== A. official localized names at 15000 + type ===")
    for t in (0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514):
        sid = 15000 + t
        print("  type %4d  en=%-38r zh=%r" % (t, en.get(sid), zh.get(sid)))

    print()
    print("=== how many of the game's 551 names have a zh counterpart? ===")
    block = [k for k in en if 15000 <= k <= 15550]
    have = [k for k in block if zh.get(k)]
    print("  en entries %d | zh entries %d | zh coverage %.1f%%"
          % (len(block), len(have), 100.0 * len(have) / len(block)))

    print()
    print("=== B. the 215 conflict ===")
    print("  ids 205..230, both game (en/zh) and AGE")
    ini = os.path.join(GAME, "Tools_Builds", "AGE3NamesV0007.ini")
    age, sec = {}, None
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
    for i in range(205, 231):
        sid = 15000 + i
        g, z, a = en.get(sid), zh.get(sid), age.get(i)
        flag = ""
        if g is not None and a is not None and g.lstrip("!") != a:
            flag = "   <<< DISAGREE"
        print("  %4d  game=%-34r AGE=%-30r zh=%r%s" % (i, g, a, z, flag))

    print()
    print("=== every 'kipchak' mention in the game's string files ===")
    for loc in ("en", "zh"):
        t = load(loc)
        hits = [(k, v) for k, v in t.items() if "kipchak" in v.lower()]
        print("  %s: %d" % (loc, len(hits)))
        for k, v in sorted(hits)[:12]:
            print("      %6d  %r" % (k, v))

    print()
    print("=== and in AGE's ini, every kipchak mention ===")
    with open(ini, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if "kipchak" in line.lower():
                print("      line %d: %s" % (n, line.strip()))

    print()
    print("=== B2. who else in the dat uses type 214 / 215? ===")
    print("  (from _probe/probe_unmapped_carriers.py, recorded: 214 on unit ids")
    print("   1259/1260/1261/1276 amount 1; 215 on 1259/1261/1276 amount -1)")
    print("  AGE's own tooltip for these ids, from the AGE exe:")
    ag = os.path.join(GAME, "Tools_Builds", "AdvancedGenieEditor3.exe")
    b = open(ag, "rb").read()
    for probe in (b"Mercenary Kipchak Count", b"Mercenary Kipchak Limit",
                  b"Bonus Forager Food"):
        print("      %-28s in AGE exe: %s"
              % (probe.decode(), probe in b))


if __name__ == "__main__":
    main()

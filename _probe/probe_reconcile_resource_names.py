"""Reconcile the GAME's 15000+ name block with the tables this project already has.

Three questions this must answer before I touch any product code:

1. Is the game's 15000+ block already captured by an existing schema file
   (`effect_attributes.json`)?  If so, `resource_labels.json` is an inferior
   duplicate and the game block is the one to ship.  (ANSWER, acted on: they are
   different id spaces, and `resource_labels.json` was rebuilt from the game
   block -- see `_probe/schema/build_resource_labels.py`.)
2. AGE says id 215 is "Mercenary Kipchak Limit"; the game says "Bonus Forager
   Food".  They CANNOT both be right.  Which one describes the slots we
   actually found (unit 1259/1261/1276, amount -1)?
3. `build_resource_labels.py` drops 229 entries but only 220 are literally
   "Unused".  What are the other 9, and is dropping them correct?
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SCHEMA = os.path.join(os.path.dirname(HERE), "aoe2mod", "schema")
EN = os.path.join(GAME, "resources", "en", "strings", "key-value",
                  "key-value-strings-utf8.txt")
INI = os.path.join(GAME, "Tools_Builds", "AGE3NamesV0007.ini")

LINE = re.compile(r'^(\d+)\s+"(.*)"\s*$')


def game_block():
    out = {}
    with open(EN, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line.strip())
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def age_names():
    age, sec = {}, None
    with open(INI, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                sec = line[1:-1]
                continue
            if sec == "AoE2DECivResourceNames" and "=" in line:
                k, _, v = line.partition("=")
                if k.strip().isdigit():
                    age[int(k.strip())] = v.strip()
    return age


def main():
    en = game_block()
    age = age_names()

    print("=== 1. what does the project already have? ===")
    for fn in ("effect_attributes.json", "resource_labels.json",
               "effect_labels_zh.json"):
        p = os.path.join(SCHEMA, fn)
        if not os.path.exists(p):
            print("  %-28s MISSING" % fn)
            continue
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
        top = list(doc) if isinstance(doc, dict) else "(list len %d)" % len(doc)
        print("  %-28s %6d B  top=%s" % (fn, os.path.getsize(p), top))

    print()
    print("=== effect_attributes.json in detail (is it the 15000+ space?) ===")
    p = os.path.join(SCHEMA, "effect_attributes.json")
    with open(p, encoding="utf-8") as fh:
        ea = json.load(fh)
    for k, v in list(ea.items())[:6]:
        print("  %-16s -> %r" % (k, (v if not isinstance(v, dict)
                                     else {kk: v[kk] for kk in list(v)[:6]})))
    # does it contain a name for 214/215/501/506/508/513/514 anywhere?
    blob = json.dumps(ea, ensure_ascii=False)
    for probe in ("Mercenary Kipchak", "Polemarch", "Helepolis", "Bonus Forager",
                  "Relics Captured"):
        print("  contains %-20r : %s" % (probe, probe in blob))

    print()
    print("=== 2. the 215 conflict ===")
    print("  AGE  id 215 = %r" % age.get(215))
    print("  GAME id 215 = %r" % en.get(15000 + 215))
    print("  GAME id 214 = %r" % en.get(15000 + 214))
    print("  AGE  id 214 = %r" % age.get(214))
    # The carriers were unit 1259 (CUMANPLACEHOLDER) / 1261 (CUMANDISABLED) /
    # 1276 (Urus Khan), amount -1 for 215.  Where else in the game's block do
    # kipchak-like names live, and does 215 have neighbours that look like a
    # pair?  Print 210..220 from both tables.
    print()
    print("  --- ids 210..220, both tables ---")
    for i in range(210, 221):
        g = en.get(15000 + i)
        a = age.get(i)
        mark = "  <<< DISAGREE" if (g is not None and a is not None
                                   and g.lstrip("!") != a) else ""
        print("  %4d  game=%-34r AGE=%-34r%s" % (i, g, a, mark))

    print()
    print("=== 3. the 229-vs-220 gap in the AGE table ===")
    dropped = sorted(k for k in age if age[k] == "Unused")
    print("  AGE entries: %d" % len(age))
    print("  literally 'Unused': %d" % len(dropped))
    notunused = sorted(k for k in age if age[k] != "Unused")
    print("  not 'Unused': %d" % len(notunused))
    # what the generator kept = those with a name that is neither Unused nor blank
    kept = [k for k in age if age[k] and age[k] != "Unused"]
    print("  generator keeps (non-empty, not Unused): %d" % len(kept))
    odd = sorted(set(notunused) - set(kept))
    print("  dropped but NOT literally 'Unused': %d %s" % (len(odd), odd))
    for k in odd:
        print("      id %d -> %r" % (k, age[k]))
    # Are those ids named by the game?
    print()
    print("  --- do those odd ids fare better in the game block? ---")
    for k in odd:
        print("      id %d : game %r" % (k, en.get(15000 + k)))

    print()
    print("=== 4. coverage comparison over the ids the dat actually uses ===")
    used = [-1, 0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514]
    for t in used:
        g = en.get(15000 + t)
        a = age.get(t)
        print("  %4d  game=%-38r AGE=%r" % (t, g, a))
    print()
    print("  game block covers ids 0..%d" % (max(k - 15000 for k in en
                                                 if 15000 <= k <= 15550)))
    print("  AGE covers ids 0..%d" % max(age))
    # ids 500..550 exist in the game and AGE has nothing
    beyond = [i for i in range(500, 551) if en.get(15000 + i)]
    print("  game names %d ids in 500..550 that AGE cannot:" % len(beyond))
    for i in beyond[:30]:
        print("      %4d  %s" % (i, en[15000 + i]))


if __name__ == "__main__":
    main()

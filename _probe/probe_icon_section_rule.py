# -*- coding: utf-8 -*-
"""probe_icon_section_rule.py -- decide, by measurement, WHICH icons.json
section a unit's icon_id belongs to.

`icons.json` keeps `Units` and `Buildings` as separate namespaces that OVERLAP
on 117 numeric keys -- key "002" is `UnitIcons00250730` in one and
`BuildingIcons002Barracks1` in the other, and (measured by probe_material_index)
the two atlases hold DIFFERENT artwork for every one of the 644 units where both
resolve.  So picking the wrong section is not a cosmetic slip: it shows the
wrong picture.  `_probe/ICONS_RESOLUTION.md` proposed a tie-break --

    use the Buildings entry only when its name denotes THIS entity

-- and this probe measures whether that tie-break can be executed mechanically
on the current install, using the shipped string table for the entity's name.

The control is essential: if the "denotes" test also fires for units that are
NOT buildings, it is measuring name-shaped noise, not the rule.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "_probe", "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")

# BuildingIcons002Barracks1 -> the words a player would see: Barracks
_MAT_RE = re.compile(r"^(Unit|Building)icons(\d+)(.*)$", re.I)


def words(text):
    """Split a CamelCase / snake_case / spaced token into folded words.

    The trailing digits matter: `BuildingIcons002Barracks1` ends in a VARIANT
    number glued to the word, so a naive split yields "barracks1", which does
    not intersect {"barracks"} and made 102 real buildings look like leftovers.
    Digits are split off and dropped; the variant number carries no meaning for
    "does this name denote the entity".
    """
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    out = set()
    for w in s.split():
        w = re.sub(r"\d+", "", w).strip().lower()
        if not w:
            continue
        out.add(w)
    return out


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    def table(loc):
        base = os.path.join(S.G, "resources", loc, "strings", "key-value")
        merged = {}
        for name in S.KV_FILES:
            fp = os.path.join(base, name)
            if os.path.exists(fp):
                merged.update(S.parse_kv_file(fp)[0])
        return merged

    en, zh = table("en"), table("zh")

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    print("units with icon_id > 0: %d" % len(rows))
    print("  of those, type == 80 (building by gameplay): %d"
          % sum(1 for u in rows if u.get("type") == 80))
    print("  name string resolves from the shipped table: %d / %d"
          % (sum(1 for u in rows if en.get(u.get("_dll_name"))), len(rows)))

    def section_name(section, icon_id):
        icons = _ICONS
        return (icons.get(section) or {}).get("%03d" % icon_id)

    # --- how often does the Buildings material name denote the entity? -----
    tally = {}
    examples = []
    for u in rows:
        b = section_name("Buildings", u["icon_id"])
        if not b:
            continue
        m = _MAT_RE.match(b)
        mat_words = words(m.group(3)) if m else words(b)
        name_en = en.get(u.get("_dll_name")) or ""
        ent_words = words(name_en)
        denotes = bool(mat_words & ent_words)
        is_bldg = (u.get("type") == 80)
        key = ("type80" if is_bldg else "type%d" % u.get("type"), "denotes" if denotes else "no")
        tally[key] = tally.get(key, 0) + 1
        if denotes and len(examples) < 14:
            examples.append((u["id"], name_en, zh.get(u.get("_dll_name")), b))

    print("\nBuildings-section material name vs the entity's English name")
    print("(this IS the proposed tie-break, measured):")
    for k in sorted(tally, key=lambda s: (s[0], s[1])):
        print("  %-8s %-7s %4d" % (k[0], k[1], tally[k]))
    print("\n  examples where it fires:")
    for e in examples:
        print("    unit %-5s en=%-26r zh=%-16r -> %s" % e)

    # --- the discriminating statistic ------------------------------------
    t80 = [u for u in rows if u.get("type") == 80]
    hit80 = sum(1 for u in t80
                if section_name("Buildings", u["icon_id"])
                and (words((_MAT_RE.match(section_name("Buildings", u["icon_id"]) or "").group(3)
                            if _MAT_RE.match(section_name("Buildings", u["icon_id"]) or "") else ""))
                     & words(en.get(u.get("_dll_name")) or "")))
    other = [u for u in rows if u.get("type") != 80]
    hit_other = sum(1 for u in other
                    if section_name("Buildings", u["icon_id"])
                    and (words((_MAT_RE.match(section_name("Buildings", u["icon_id"]) or "").group(3)
                                if _MAT_RE.match(section_name("Buildings", u["icon_id"]) or "") else ""))
                         & words(en.get(u.get("_dll_name")) or "")))
    print("\nRATE, type 80     : %d / %d = %.1f%%"
          % (hit80, len(t80), 100.0 * hit80 / max(1, len(t80))))
    print("RATE, everything else: %d / %d = %.1f%%"
          % (hit_other, len(other), 100.0 * hit_other / max(1, len(other))))
    print("  -> the test discriminates only if these two rates are far apart.")
    return 0


_GLOBAL = {}


def _setup():
    import json
    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        _GLOBAL["icons"] = json.load(fh)


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    _setup()
    _ICONS = _GLOBAL["icons"]
    sys.exit(main())

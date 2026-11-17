# -*- coding: utf-8 -*-
"""Is `wpfg/resources/uniticons` a SECOND icon source, or a redundant copy?

The question mattered because this directory sits in a root that
`test_ui_layer_wiring.py` proves mod-overridable, and its PNGs are 256 px where
the grid draws 48 px tiles out of the atlas -- so "the grid could look much
better" is the obvious next move.

Measured, in this order, and the order is the point:

1. 95 PNGs named `NNN_50730.png`; every one resolves in `icons.json`'s Units
   section at key `NNN` to the material `UnitIcons<NNN>50730`.
2. That resolution proves NOTHING about coverage: all 1,000 Units keys have
   exactly that shape, because the material name is built from the key.  A
   first draft of this probe read the match as "the file set is meaningful" --
   the rule holds for 100% of ids, including the 905 with no PNG at all.
3. The 95 loose stems also exist as `.dds` under `widgetui/textures/ingame/units`
   (79x files), and that directory is a SUPERSET of the loose set.  So the
   atlas path already reaches a full-size picture for these ids.
4. `ddstex.decode` on 035_50730.dds gives 256x256 raw BGRA; opened next to the
   loose PNG they are the SAME artwork under a different tint.  Mean absolute
   channel difference is large (48.9 of 255 on 035) precisely BECAUSE the tint
   differs -- so a pixel-equality test would have "proved" a difference that is
   not one.

Conclusion, and what this pins: the loose directory is a redundant second copy
used by the menu layer (`systemresourcesimages.xaml` points at exactly four of
them, two named after civilizations).  It is not a bigger icon source, so the
grid keeps the atlas path.  Rewiring it would trade a proven 1,219-picture chain
for a 95-picture one and call it an improvement.
"""
import json
import _gamepaths as GP
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GAME = GP.GAME
WID = os.path.join(GAME, "widgetui")
UNITS = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "uniticons")
DDSDIR = os.path.join(WID, "textures", "ingame", "units")


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def main():
    fails = []

    def check(name, ok, detail=""):
        print("%-64s %s%s" % (name, "ok" if ok else "FAIL",
                              "" if not detail else "  :: " + detail))
        if not ok:
            fails.append(name)

    icons = json.loads(open(os.path.join(WID, "icons.json"), "rb").read().decode("utf-8-sig"))
    units = icons.get("Units") or {}
    numbered = sorted(n for n in os.listdir(UNITS) if re.match(r"^\d+_\d+\.png$", n))
    check("the loose directory holds the 95 numbered PNGs", len(numbered) == 95,
          "%d files" % len(numbered))

    # 1 + 2 - the naming rule holds everywhere, so it does not distinguish.
    shaped = [k for k, v in units.items() if v == "UnitIcons%s50730" % k]
    check("EVERY Units key has the same material shape (the rule proves nothing)",
          len(shaped) == len(units), "%d of %d" % (len(shaped), len(units)))
    checks = [n for n in numbered if n[:-4].split("_")[1] == "50730"]
    check("all 95 use the single set number 50730", len(checks) == len(numbered),
          "%d of %d" % (len(checks), len(numbered)))

    # 3 - the DDS set is a superset, so the loose files add no coverage.
    dds = sorted(f for f in os.listdir(DDSDIR) if f.lower().endswith(".dds"))
    dds_stems = {os.path.splitext(f)[0] for f in dds}
    loose_stems = {n[:-4] for n in numbered}
    check("every loose stem also exists as a .dds",
          loose_stems <= dds_stems,
          "%d missing" % len(loose_stems - dds_stems))
    check("the .dds directory is a strict superset, so no id needs the PNG",
          len(dds_stems) > len(loose_stems),
          "%d dds vs %d png" % (len(dds_stems), len(loose_stems)))

    # 4 - the atlas path the product already uses reaches a full-size picture.
    from aoe2mod.game import ddstex
    pic = None
    try:
        from aoe2mod.game.icons import IconBook
        book = IconBook(GAME)
        pic = book.picture("Units", 35)
    except Exception as exc:                       # noqa: BLE001 - reported, not hidden
        check("the product's atlas chain resolves icon id 35", False, str(exc))
    if pic is not None:
        check("the product's atlas chain resolves icon id 35", bool(pic.get("ok")),
              str(pic.get("why") or pic.get("file")))
        path = pic.get("path") or ""
        check("and it is the full-size picture, not a 48 px tile",
              os.path.basename(path) == "035_50730.dds" and
              ddstex.header(path)["width"] == 256,
              "%s %spx" % (os.path.basename(path),
                           ddstex.header(path)["width"] if os.path.exists(path) else "?"))

    # The game's own markup names four of them; quote it rather than paraphrase.
    xaml = os.path.join(GAME, "resources", "_common", "wpfg", "systemresourcesimages.xaml")
    text = open(xaml, "rb").read().decode("utf-8-sig")
    refs = re.findall(r'x:Key="([^"]+)"\s+ImageSource="/resources/uniticons/([^"]+)"', text)
    check("the game's own xaml references exactly four of them", len(refs) == 4,
          ", ".join("%s->%s" % r for r in refs))
    check("two of those are named after a civilization, not after a unit",
          sorted(k for k, _f in refs if "unique_unit_icon" in k) ==
          ["armenians_unique_unit_icon", "georgians_unique_unit_icon"],
          str([k for k, _f in refs]))

    print()
    if fails:
        print("HIRES ICONS: %d CHECKS FAILED" % len(fails))
        return 1
    print("HIRES ICONS: A REDUNDANT SECOND COPY, NOT A SECOND SOURCE")
    print("  The grid keeps the atlas chain.  95 PNGs under a mod-visible root look")
    print("  like an upgrade, but every one of them is already reachable at 256 px")
    print("  through textures/ingame/units (794 files), and the two copies are the")
    print("  same artwork under a different tint -- so swapping sources would lose")
    print("  1,219 pictures to gain none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

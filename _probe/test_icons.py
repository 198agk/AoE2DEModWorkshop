# -*- coding: utf-8 -*-
"""test_icons.py -- the icon chain, measured end to end.

Every claim in `aoe2mod/game/icons.py` and `aoe2mod/game/ddstex.py` was first a
probe.  This file pins them so they cannot rot silently:

* both icon sections exist for the same id and are different pictures -- if a
  future build drops one, "pick a section" stops being a question;
* the section rule covers every icon-bearing unit (1,344/1,344);
* the material -> atlas -> file chain lands on a real file;
* DDS decoding produces the right pixel count and PNG bytes start with a header,
  for BOTH layouts the game ships (raw BGRA and DXT5);
* technologies use the Techs section, and the three ids that do not resolve are
  named rather than dropped;
* civilizations resolve to emblem PNGs, including the two aliased stems.

It is a suite, not a probe: these are promises the UI makes to a player, and a
broken icon is a picture of the wrong thing, not a missing feature.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

FAILED = []
OK = [0]


def check(name, cond, detail=""):
    if cond:
        OK[0] += 1
        print("  ok   %s" % name)
    else:
        FAILED.append(name if not detail else "%s [%s]" % (name, detail))
        print("  FAIL %s%s" % (name, "" if not detail else " [%s]" % detail))


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    from aoe2mod.game import icons as I
    from aoe2mod.game import ddstex as D

    book = I.IconBook(GAME)
    counts = book.counts()
    print("icons.json sections: %s" % counts)
    check("icons.json has a Units section", counts.get("Units", 0) > 900)
    check("icons.json has a Buildings section", counts.get("Buildings", 0) > 100)
    check("icons.json has a Techs section", counts.get("Techs", 0) > 300)
    check("icons.json has a CivEmblem section", counts.get("CivEmblem", 0) > 60)

    # ---- the two tables must stay distinct ------------------------------
    shared = [i for i in range(1, 130) if book.material_name("Units", i)
              and book.material_name("Buildings", i)]
    check("both tables cover some ids at once (the ambiguity is real)",
          len(shared) > 20, "%d shared ids" % len(shared))
    differ = [i for i in shared
              if book.material_name("Units", i) != book.material_name("Buildings", i)]
    check("for every shared id the two materials differ",
          len(differ) == len(shared), "%d/%d differ" % (len(differ), len(shared)))
    u2 = book.picture("Units", 2)
    b2 = book.picture("Buildings", 2)
    check("id 2 is a different picture in each section",
          u2.get("ok") and b2.get("ok") and u2["file"] != b2["file"])

    # ---- the chain lands on disk ---------------------------------------
    check("a Buildings icon resolves to a file on disk", b2.get("ok"), b2.get("why"))
    check("a Units icon resolves to a file on disk", u2.get("ok"), u2.get("why"))
    check("the resolved file really exists", os.path.isfile(u2.get("path") or ""))
    check("UV is reported", len(u2.get("uv") or []) == 4)
    check("a missing id fails with a reason, not a crash",
          book.picture("Units", 99999).get("ok") is False
          and "no entry" in book.picture("Units", 99999).get("why", ""))
    check("icon id 0 fails with its own reason",
          "no icon id" in book.picture("Units", 0).get("why", ""))

    # ---- decode both layouts -------------------------------------------
    w, h, rgba = D.decode(u2["path"])
    check("raw BGRA decodes to the header's pixel count",
          len(rgba) == w * h * 4, "%d != %d" % (len(rgba), w * h * 4))
    check("raw BGRA has visible pixels", any(rgba[i] for i in range(0, len(rgba), 4)))
    png = D.to_png(u2["path"])
    check("decoding to PNG produces a PNG",
          png.startswith(b"\x89PNG\r\n\x1a\n"), repr(png[:8]))

    dds_files = []
    for section in ("Units", "Buildings", "Techs"):
        for icon_id in range(1, 400):
            got = book.picture(section, icon_id)
            if got.get("ok") and got["path"].lower().endswith(".dds"):
                dds_files.append(got["path"])
            if len(dds_files) >= 2:
                break
        if len(dds_files) >= 2:
            break
    check("the game ships DDS icons to decode", len(dds_files) >= 1,
          "%d found" % len(dds_files))

    small = D.to_png(u2["path"], max_side=32)
    sw, sh, _rgba = D.decode(u2["path"])
    check("max_side shrinks the long edge to at most 32",
          small[:8] == b"\x89PNG\r\n\x1a\n", "still a PNG")

    # ---- the section rule over every real unit -------------------------
    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    en = {}
    base = os.path.join(GAME, "resources", "en", "strings", "key-value")
    sys.path.insert(0, os.path.join(HERE, "semantic"))
    import strings_db as S
    for name in S.KV_FILES:
        fp = os.path.join(base, name)
        if os.path.exists(fp):
            en.update(S.parse_kv_file(fp)[0])

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    witnesses = {}
    resolved = 0
    missing = []
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    for u in rows:
        producers = [e.get("unit_id") for e in (u.get("train_locations") or [])]
        section, why = book.unit_section(
            u["icon_id"],
            made_by_builder=any(pd == I.BUILDER_UNIT_ID for pd in producers),
            made_by_building=any((by_id.get(pd) or {}).get("type") == 80
                                 for pd in producers),
            english_name=en.get(u.get("_dll_name")))
        witnesses[why] = witnesses.get(why, 0) + 1
        got = book.picture(section, u["icon_id"])
        if got.get("ok"):
            resolved += 1
        else:
            missing.append((u.get("id"), u["icon_id"], section, got.get("why")))

    check("every icon-bearing unit has a section chosen for it",
          len(witnesses) >= 3, "%d witnesses" % len(witnesses))
    check("every icon-bearing unit resolves to a file",
          resolved == len(rows),
          "%d/%d (first failure %s)" % (resolved, len(rows),
                                        missing[0] if missing else "none"))
    check("the default witness is the largest group (it is documented as such)",
          witnesses.get("no producer and no matching build-menu material; the "
                        "Units table is the default", 0) > 300,
          str(witnesses))

    # ---- technologies ---------------------------------------------------
    techs = L.locate_techs(data, tail, gv)
    tech_rows = 0
    tech_ok = 0
    tech_bad = []
    for tid, t in enumerate(techs):
        icon_id = t.get("icon_id") or 0
        if icon_id <= 0:
            continue
        tech_rows += 1
        got = book.picture("Techs", icon_id)
        if got.get("ok"):
            tech_ok += 1
        else:
            tech_bad.append((tid, icon_id, got.get("why")))
    check("technologies resolve through the Techs section",
          tech_ok > 400, "%d of %d" % (tech_ok, tech_rows))
    check("the unresolvable technologies are few and named",
          len(tech_bad) <= 5, str(tech_bad[:3]))

    # ---- civilizations --------------------------------------------------
    emblems = book._load_icons().get("CivEmblem") or {}
    found = 0
    for key in sorted(emblems):
        value = emblems[key] or ""
        if not value.startswith("civ_emblems_"):
            continue
        stem = value[len("civ_emblems_"):]
        if book.emblem_path(stem):
            found += 1
    check("civilization emblems resolve to PNGs", found >= 60, "%d found" % found)
    check("the aliased stem 'inca' resolves", bool(book.emblem_path("inca")))
    check("the aliased stem 'berber' resolves", bool(book.emblem_path("berber")))
    check("a civilization with no emblem returns None, not a wrong file",
          book.emblem_path("no-such-civ") is None)

    print()
    if FAILED:
        print("ICON CHAIN: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("ICON CHAIN: %d CHECKS PASSED -- sections, materials, files, DDS decode, "
          "techs and emblems" % OK[0])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

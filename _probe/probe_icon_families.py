# -*- coding: utf-8 -*-
"""probe_icon_families.py -- do units, techs and civilizations all resolve?

The icon layer has to serve three families, and each goes through a DIFFERENT
part of icons.json:

    units    "Units" (train list) or "Buildings" (build menu) -- chosen by rule
    techs    always "Techs"
    civs     "CivEmblem" -- a bare file name under
             resources/_common/wpfg/resources/civ_emblems/<value>.png

This probe measures all three end to end (icons.json -> material -> atlas
texture -> file on disk) before any of it is written into the product, because
"89% resolved" in a research note is not the same claim as "the file is there".
"""
from __future__ import print_function

import codecs
import contextlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")
WPFG = os.path.join(GAME, "resources", "_common", "wpfg", "resources")
BUILDER = 118

_STOP = {"icon", "icons", "building", "buildings", "unit", "units", "the", "of",
         "and", "a", "b", "full", "empty", "no", "new", "old"}


def words(text):
    if not text:
        return set()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return {w.lower() for w in s.split()
            if len(w) >= 3 and w.lower() not in _STOP}


class Materials(object):
    def __init__(self, path):
        with io.open(path, encoding="utf-8-sig") as fh:
            j = json.load(fh)
        self.atlases = {}
        for e in j.get("AtlasTextures") or []:
            d = e.get("AtlasDef", e)
            if d.get("Name"):
                self.atlases[d["Name"]] = d
        self.mats = {}
        for e in j.get("Materials") or []:
            d = e.get("MaterialDef")
            if d and d.get("Name"):
                self.mats.setdefault(d["Name"], d)

    def resolve(self, mname):
        md = self.mats.get(mname)
        if not md:
            return {"ok": False, "why": "no MaterialDef %r" % (mname,)}
        atlas = md.get("AtlasRef")
        at = self.atlases.get(atlas)
        if at is None:
            return {"ok": False, "why": "AtlasRef %r not in AtlasTextures" % (atlas,)}
        tex = None
        for t in at.get("Textures") or []:
            if t.get("RefName") in (mname, md.get("Name")):
                tex = t
                break
        if tex is None:
            return {"ok": False, "why": "no texture with RefName %r in %r"
                    % (mname, atlas)}
        return {"ok": True, "atlas": atlas, "file": tex.get("FileName"),
                "uv": [float(tex.get("imageTLX")), float(tex.get("imageTLY")),
                       float(tex.get("imageBRX")), float(tex.get("imageBRY"))],
                "atlas_size": [at.get("MaxWidth"), at.get("MaxHeight")]}


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        icons = json.load(fh)
    M = Materials(os.path.join(WID, "materials.json"))

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    en = {}
    base = os.path.join(GAME, "resources", "en", "strings", "key-value")
    for name in S.KV_FILES:
        fp = os.path.join(base, name)
        if os.path.exists(fp):
            en.update(S.parse_kv_file(fp)[0])

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    units_sec = icons.get("Units") or {}
    bld_sec = icons.get("Buildings") or {}

    def section_for(u):
        key = "%03d" % u["icon_id"]
        prods = [e.get("unit_id") for e in (u.get("train_locations") or [])]
        if any(pd == BUILDER for pd in prods):
            return "Buildings", "build menu"
        if any((by_id.get(pd) or {}).get("type") == 80 for pd in prods):
            return "Units", "trained by a building"
        if bld_sec.get(key) and (words(bld_sec[key]) & words(en.get(u.get("_dll_name")) or "")):
            return "Buildings", "build-menu material names it"
        return "Units", "no witness (default)"

    # ---- units -----------------------------------------------------------
    rows = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    ok = miss = 0
    miss_list = []
    why = {}
    for u in rows:
        sec, reason = section_for(u)
        why[reason] = why.get(reason, 0) + 1
        got = M.resolve((bld_sec if sec == "Buildings" else units_sec)["%03d" % u["icon_id"]])
        if got["ok"] and os.path.exists(os.path.join(WID, got["file"])):
            ok += 1
        else:
            miss += 1
            miss_list.append((u.get("id"), u.get("icon_id"), got.get("why")))
    print("UNITS: %d icon rows, %d resolve to a file on disk, %d do not"
          % (len(rows), ok, miss))
    print("  section reasons: %s" % why)
    for m in miss_list[:10]:
        print("  MISS unit %s icon %s: %s" % m)

    # ---- techs -----------------------------------------------------------
    tech_rows = 0
    tech_ok = 0
    tech_miss = []
    for civ in civs:
        for t in civ.get("techs") or []:
            pass
    techs = None
    try:
        # locate_techs(data, tail, gv) -- NOT data,parser=p.  Guessing the
        # signature produced "0 icon rows" and looked like a finding.
        techs = L.locate_techs(data, tail, gv)
    except Exception as exc:
        print("  locate_techs failed: %s" % exc)
    tech_sec = icons.get("Techs") or {}
    if techs:
        seen = set()
        # locate_techs records carry NO 'id': the id IS the array index (the same
        # trap that made every earlier sweep treat all techs as rank 0).  Many
        # rows repeat across civilizations, so dedupe on the index.
        for tid, t in enumerate(techs):
            ic = t.get("icon_id") or 0
            if tid in seen or ic <= 0:
                continue
            seen.add(tid)
            tech_rows += 1
            m = tech_sec.get("%03d" % ic)
            if not m:
                tech_miss.append((tid, ic, "no Techs entry"))
                continue
            got = M.resolve(m)
            if got["ok"] and os.path.exists(os.path.join(WID, got["file"])):
                tech_ok += 1
            else:
                tech_miss.append((tid, ic, got.get("why")))
    print("\nTECHS: %d icon rows, %d resolve, %d do not"
          % (tech_rows, tech_ok, len(tech_miss)))
    for m in tech_miss[:10]:
        print("  MISS tech %s icon %s: %s" % m)

    # ---- civilizations ---------------------------------------------------
    emb = icons.get("CivEmblem") or {}
    ok_civ = miss_civ = 0
    miss_civ_list = []
    for key in sorted(emb):
        val = emb[key] or ""
        # The value is `civ_emblems_britons`; the file on disk is `britons.png`.
        # Key 000 is an empty placeholder -- only 63 of the 67 slots are civs.
        # Two names are spelled differently on disk (inca/incas, berber/berbers);
        # that pair is hard-coded because there is no rule to derive it.
        stem = val[len("civ_emblems_"):] if val.startswith("civ_emblems_") else val
        stem = {"inca": "incas", "berber": "berbers"}.get(stem, stem)
        if not stem:
            miss_civ += 1
            miss_civ_list.append((key, val))
            continue
        path = os.path.join(WPFG, "civ_emblems", "%s.png" % stem)
        if os.path.exists(path):
            ok_civ += 1
        else:
            miss_civ += 1
            miss_civ_list.append((key, val))
    print("\nCIVS: %d emblem entries, %d files found, %d missing"
          % (len(emb), ok_civ, miss_civ))
    for m in miss_civ_list[:10]:
        print("  MISS emblem %s -> %s" % m)

    print("\nsample UnitCivEmblem values: %s"
          % [emb[k] for k in sorted(emb)[:6]])
    print("civilizations.json internal names: %d"
          % len((json.load(io.open(os.path.join(GAME, "resources", "_common", "dat",
                                                "civilizations.json"),
                                   encoding="utf-8-sig")).get("civilization_list") or [])))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

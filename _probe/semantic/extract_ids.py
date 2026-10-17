# -*- coding: utf-8 -*-
"""Capture the LanguageDLL* string-id fields from the AoE2DE .dat.

`parse_dat.py` (verified byte-exact parser) reads LanguageDLLName /
LanguageDLLDescription / LanguageDLLHelp / LanguageDLLTechTree but discards
the values (`r.i32()` with no assignment).  We must NOT re-derive the record
layout by hand and risk a desync, so instead we WRAP the parser's own
`read_unit` / `read_tech` and, for each record, read the LanguageDLL fields
straight out of the same byte buffer at their fixed offsets from the record
start.  The parser remains the single source of truth for where each record
begins and ends; we only sample 4 bytes inside it.

Offsets are derived from the verified read order in parse_dat.py:

  read_unit (parse_dat.py:598-652)
    +0   u8   type
    +1   i16  id
    +3   i32  LanguageDLLName          <-- captured
    +7   i32  LanguageDLLCreation
    ...
  read_tech (parse_dat.py:710-729)
    +0   i16[6] RequiredTechs          (12 B)
    +12  3 x (i16,i16,u8)              (15 B)
    +27  i16  RequiredTechCount
    +29  i16  civ
    +31  i16  FullTechMode
    +33  i32  LanguageDLLName          <-- captured
    +37  i32  LanguageDLLDescription   <-- captured
    +41  i16  effect_id
    +43  i16  type
    +45  i16  icon_id
    +47  i32  LanguageDLLHelp          <-- captured
    +51  i32  LanguageDLLTechTree      <-- captured
"""
import os
import struct
import sys
import json
import time
import collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "datparse"))

import parse_dat  # noqa: E402

DAT = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
       r"\empires2_x2_p1.dat")

_orig_read_unit = parse_dat.read_unit
_orig_read_tech = parse_dat.read_tech

UNIT_DLL_FIELDS = ("LanguageDLLName",)
TECH_DLL_FIELDS = ("LanguageDLLName", "LanguageDLLDescription",
                   "LanguageDLLHelp", "LanguageDLLTechTree")


def _grab(data, off, n_i32):
    """Read n_i32 little-endian int32 at absolute offset `off`."""
    if off + 4 * n_i32 > len(data):
        return None
    return struct.unpack_from("<%di" % n_i32, data, off)


def _wrap_unit(orig):
    def wrapper(r, collect=None):
        start = r.pos
        u = orig(r, collect)
        if collect is not None and u is not None:
            vals = _grab(r.data, start + 3, 1)
            if vals is not None:
                u["LanguageDLLName"] = vals[0]
        return u
    return wrapper


def _wrap_tech(orig):
    def wrapper(r):
        start = r.pos
        t = orig(r)
        # LanguageDLLName @+33, Description @+37, Help @+47, TechTree @+51
        for name, off in (("LanguageDLLName", 33),
                          ("LanguageDLLDescription", 37),
                          ("LanguageDLLHelp", 47),
                          ("LanguageDLLTechTree", 51)):
            v = _grab(r.data, start + off, 1)
            if v is not None:
                t[name] = v[0]
        return t
    return wrapper


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parse_dat.read_unit = _wrap_unit(_orig_read_unit)
    parse_dat.read_tech = _wrap_tech(_orig_read_tech)

    t0 = time.time()
    data, how = parse_dat.load_dat(DAT)
    p = parse_dat.Parser(data)
    st = p.parse()
    t1 = time.time()

    final = p.r.pos
    print("dat size      : %d" % len(data))
    print("final offset  : %d" % final)
    print("exact match   : %s" % ("YES" if final == len(data) else "NO"))
    print("parse time    : %.2f s" % (t1 - t0))
    print("civs          : %d" % st["civ_count"])
    print("techs         : %d" % st["tech_count"])

    # ---- units: one entry per (civ, unit-record) -------------------------
    unit_records = []
    for ci, c in enumerate(st["civs"]):
        for u in c["units"]:
            unit_records.append({
                "civ_index": ci,
                "civ": c["name"],
                "id": u["id"],
                "internal": u["name"],
                "type": u["type"],
                "hit_points": u["hit_points"],
                "LanguageDLLName": u.get("LanguageDLLName"),
            })
    print("unit records  : %d" % len(unit_records))

    # sanity: a civ 0 (Gaia) unit and a normal one
    for rec in unit_records[:3]:
        print("   sample:", rec)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "_raw_ids.json"), "w", encoding="utf-8") as f:
        json.dump({
            "units": unit_records,
            "techs": [{"index": i, **t} for i, t in enumerate(st["techs"])],
            "stats": {k: st[k] for k in ("civ_count", "tech_count",
                                         "unit_header_count")},
        }, f, ensure_ascii=False)

    # ---- quick field sanity ---------------------------------------------
    bad = [r for r in unit_records
           if r["LanguageDLLName"] is None or r["LanguageDLLName"] < 0]
    print("unit records with null/negative LanguageDLLName: %d" % len(bad))
    dll_min = min(r["LanguageDLLName"] for r in unit_records
                  if isinstance(r["LanguageDLLName"], int))
    dll_max = max(r["LanguageDLLName"] for r in unit_records
                  if isinstance(r["LanguageDLLName"], int))
    print("LanguageDLLName range : %d .. %d" % (dll_min, dll_max))

    names = [r["LanguageDLLName"] for r in unit_records]
    c = collections.Counter(names)
    print("most common LanguageDLLName values:", c.most_common(8))

    tnames = [t.get("LanguageDLLName") for t in st["techs"]]
    print("tech LanguageDLLName range: %d .. %d"
          % (min(tnames), max(tnames)))
    print("tech LanguageDLLName counter (top 5):",
          collections.Counter(tnames).most_common(5))


if __name__ == "__main__":
    main()

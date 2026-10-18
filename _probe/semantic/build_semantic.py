# -*- coding: utf-8 -*-
"""Build the semantic layer: unit_names.json / tech_names.json.

Resolution chain (VERIFIED):
    dat record -> LanguageDLLName (int32) -> resources\\<loc>\\strings\\key-value\\
    key-value-strings-utf8.txt numeric key -> localised display string

Design notes / decisions:
  * The dat stores units PER CIV (63 civs).  For 118 unit ids the
    LanguageDLLName is NOT identical across civs.  The divergence is a strict
    civ partition: 57 civs use the standard id, the 6 "Chronicles" civs
    (Achaemenids, Athenians, Macedonians, Puru, Spartans, Thracians) use an
    alternate 405xxx id which is a genuinely different display name
    (Archer->Bowman, Knight->Lancer, Militia->Levy, Monastery->Temple).
    So one lookup table is NOT sufficient; we emit the majority variant as the
    canonical name plus an explicit `civ_variants` map for the divergent ids.
  * 6 unit ids additionally carry a different internal `Name` across civs.
  * We do NOT invent names.  Unresolved ids get en/zh = null plus an explicit
    `unresolved_reason`.
"""
import json
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strings_db import load_language  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8") as f:
    raw = json.load(f)

LANGS = ["en", "zh", "tw"]
DB = {}
for loc in LANGS:
    DB[loc], _pf = load_language(loc)
    print("strings[%s]: %d numeric ids" % (loc, len(DB[loc])))

en = DB["en"]
zh = DB["zh"]
tw = DB["tw"]

# ---------------------------------------------------------------- helpers
def resolve(sid):
    """Return (en, zh, tw) or (None,...) if the id is not a real string id."""
    if not isinstance(sid, int) or sid <= 0:
        return None, None, None
    return en.get(sid), zh.get(sid), tw.get(sid)


REASON = {
    "zero": "LanguageDLLName is 0 (record carries no name string id; 55,038 of "
            "136,861 records, 1,036 distinct unit ids -- these are internal/"
            "eye-candy/placeholder objects)",
    "negative": "LanguageDLLName is a negative sentinel (-1)",
    "not_in_strings": "LanguageDLLName is a valid positive id but the id is "
                      "absent from every key-value string file",
    "no_match_in_zh": "resolved in EN but missing from the zh string files",
}


def build_units():
    by_id = collections.defaultdict(list)
    for r in raw["units"]:
        by_id[r["id"]].append(r)

    out = {}
    stats = collections.Counter()
    for uid in sorted(by_id):
        recs = by_id[uid]
        # group by LanguageDLLName -> list of civs
        groups = collections.defaultdict(list)
        for r in recs:
            groups[r["LanguageDLLName"]].append(r["civ"])
        # canonical = the variant with the most civs (ties -> smallest id)
        canon = max(sorted(groups), key=lambda k: len(groups[k]))
        canon_dll = canon if isinstance(canon, int) else None

        internal = collections.Counter(r["internal"] for r in recs)
        canonical_internal = internal.most_common(1)[0][0]

        e, c, t = resolve(canon_dll)
        entry = {
            "internal": canonical_internal,
            "en": e,
            "zh": c,
            "name_string_id": canon_dll,
            "tw": t,
            "civ_count": len({r["civ"] for r in recs}),
            "record_count": len(recs),
        }

        # explanatory reason when unresolved
        reason = None
        if canon_dll is None:
            reason = REASON["negative"]
        elif canon_dll == 0:
            reason = REASON["zero"]
        elif e is None:
            reason = REASON["not_in_strings"]
        elif c is None:
            reason = REASON["no_match_in_zh"]
        if reason:
            entry["unresolved_reason"] = reason
            entry["resolved"] = False
        else:
            entry["resolved"] = True

        # divergent ids: record every variant explicitly
        if len(groups) > 1:
            variants = {}
            for dll in sorted(groups, key=lambda k: (k is None, k)):
                ve, vc, vt = resolve(dll)
                variants[str(dll)] = {
                    "name_string_id": dll,
                    "en": ve,
                    "zh": vc,
                    "tw": vt,
                    "civs": sorted(groups[dll]),
                    "civ_count": len(groups[dll]),
                    "is_canonical": dll == canon_dll,
                }
            entry["civ_variants"] = variants
            entry["has_civ_variants"] = True
            # alternate internal codes, if any
            if len(internal) > 1:
                entry["internal_variants"] = dict(internal)
            stats["divergent_ids"] += 1
        else:
            entry["has_civ_variants"] = False

        entry["type"] = sorted({r["type"] for r in recs})
        entry["hit_points"] = sorted({r["hit_points"] for r in recs})
        out[str(uid)] = entry

        stats["total_ids"] += 1
        if entry["resolved"]:
            stats["resolved_ids"] += 1
        if e and not c:
            stats["en_only"] += 1
        if not entry["resolved"]:
            stats["unresolved_ids"] += 1
            if canon_dll == 0:
                stats["unresolved_zero"] += 1
            elif canon_dll is None or canon_dll < 0:
                stats["unresolved_neg"] += 1
            else:
                stats["unresolved_missing"] += 1
    return out, stats


def build_techs():
    out = {}
    stats = collections.Counter()
    for t in raw["techs"]:
        sid = t.get("LanguageDLLName")
        internal = t.get("name")
        e, c, twv = resolve(sid)

        reason = None
        if sid is None or (isinstance(sid, int) and sid < 0):
            reason = REASON["negative"]
        elif sid == 0:
            reason = REASON["zero"]
        elif e is None:
            reason = REASON["not_in_strings"]
        elif c is None:
            reason = REASON["no_match_in_zh"]

        def pair(field):
            v = t.get(field)
            a, b, d = resolve(v)
            return {"name_string_id": v, "en": a, "zh": b, "tw": d}

        entry = {
            "internal": internal,
            "en": e,
            "zh": c,
            "name_string_id": sid,
            "tw": twv,
            "civ": t.get("civ"),
            "effect_id": t.get("effect_id"),
            "type": t.get("type"),
            "icon_id": t.get("icon_id"),
            "description": pair("LanguageDLLDescription"),
            "help": pair("LanguageDLLHelp"),
            "tech_tree": pair("LanguageDLLTechTree"),
            "resolved": reason is None,
        }
        if reason:
            entry["unresolved_reason"] = reason
        out[str(t["index"])] = entry

        stats["total_techs"] += 1
        if reason is None:
            stats["resolved_techs"] += 1
        else:
            stats["unresolved_techs"] += 1
            if sid == 0 or sid is None or (isinstance(sid, int) and sid < 0):
                stats["unresolved_zero_neg"] += 1
            else:
                stats["unresolved_missing"] += 1
    return out, stats


units, ustat = build_units()
techs, tstat = build_techs()

with open(os.path.join(HERE, "unit_names.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(units, f, ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "tech_names.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(techs, f, ensure_ascii=False, indent=1)

print()
print("unit_names.json : %d distinct unit ids" % len(units))
print("   resolved          : %d (%.1f%%)"
      % (ustat["resolved_ids"], 100.0 * ustat["resolved_ids"] / ustat["total_ids"]))
print("   unresolved        : %d" % ustat["unresolved_ids"])
print("     zero DLL id     : %d" % ustat["unresolved_zero"])
print("     negative DLL id : %d" % ustat["unresolved_neg"])
print("     id missing from strings: %d" % ustat["unresolved_missing"])
print("   ids with civ variants: %d" % ustat["divergent_ids"])
print("   EN-resolved but ZH-missing: %d" % ustat["en_only"])
print()
print("tech_names.json : %d techs" % len(techs))
print("   resolved   : %d (%.1f%%)"
      % (tstat["resolved_techs"],
         100.0 * tstat["resolved_techs"] / tstat["total_techs"]))
print("   unresolved : %d (zero/neg %d, missing %d)"
      % (tstat["unresolved_techs"], tstat["unresolved_zero_neg"],
         tstat["unresolved_missing"]))

# ---- unresolved id inventory (for the report) --------------------------
unres_unit = {k: {"internal": v["internal"], "name_string_id": v["name_string_id"],
                  "unresolved_reason": v.get("unresolved_reason"),
                  "type": v["type"]}
              for k, v in units.items() if not v["resolved"]}
unres_tech = {k: {"internal": v["internal"], "name_string_id": v["name_string_id"],
                  "unresolved_reason": v.get("unresolved_reason")}
              for k, v in techs.items() if not v["resolved"]}
missing_pos = sorted({v["name_string_id"] for v in units.values()
                      if v.get("name_string_id") and v["name_string_id"] > 0
                      and not v["resolved"]})
with open(os.path.join(HERE, "_unresolved_ids.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump({"units": unres_unit, "techs": unres_tech,
               "unit_string_ids_absent_from_strings": missing_pos,
               "stats": {"units": dict(ustat), "techs": dict(tstat)}},
              f, ensure_ascii=False, indent=1)
print()
print("unresolved unit ids: %d ; unresolved techs: %d ; absent positive unit "
      "string ids: %s" % (len(unres_unit), len(unres_tech), missing_pos or "none"))

# ---- a few spot checks -------------------------------------------------
print()
print("spot checks:")
for uid in ("4", "38", "74", "83", "448", "546", "751"):
    if uid in units:
        v = units[uid]
        print("   id %-4s %-10s en=%-22s zh=%-14s sid=%s resolved=%s"
              % (uid, v["internal"], v["en"], v["zh"], v["name_string_id"],
                 v["resolved"]))
print()
print("divergent example id 4:")
print(json.dumps(units["4"], ensure_ascii=False, indent=1)[:900])

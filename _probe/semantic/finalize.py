# -*- coding: utf-8 -*-
"""Final classification pass: add a `category` to every unit/tech entry and
gather the exact numbers quoted in SEMANTIC_REPORT.md.

Findings this script pins down:
  * unit unresolved = 1042 distinct ids.  1036 carry LanguageDLLName == 0 and
    are internal/eye-candy objects; 4 carry the -1 sentinel; 2 carry a positive
    id that simply has no entry in any key-value string file.
  * tech unresolved = 974.  201 carry 0/-1.  Of the 773 with a positive id,
    743 carry the genieutils DEFAULT placeholder (7000 x734 / 6000 x9) which by
    design has no localised name, and 30 are genuine string-file gaps.
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
raw = json.load(open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8"))
units = json.load(open(os.path.join(HERE, "unit_names.json"), encoding="utf-8"))
techs = json.load(open(os.path.join(HERE, "tech_names.json"), encoding="utf-8"))
en, _ = load_language("en")

# ---------------------------------------------------------------- units
recs_by_id = collections.defaultdict(list)
for r in raw["units"]:
    recs_by_id[r["id"]].append(r)

type_names = {10: "EyeCandy", 70: "Combatant", 80: "Building", 30: "Tree",
              20: "Doodad", 90: "Projectile", 60: "?", 50: "?"}

uclass = collections.Counter()
zero_types = collections.Counter()
for uid, e in units.items():
    sid = e["name_string_id"]
    if e["resolved"]:
        cat = "resolved"
    elif sid == 0:
        cat = "unresolved_zero_id"
    elif sid is None or sid < 0:
        cat = "unresolved_negative_id"
    else:
        cat = "unresolved_missing_from_strings"
    e["category"] = cat
    uclass[cat] += 1
    if cat == "unresolved_zero_id":
        for t in e["type"]:
            zero_types[t] += 1

print("== UNIT categories ==")
for k, v in uclass.most_common():
    print("   %-34s %5d" % (k, v))
print("   types among zero-id ids (type -> distinct ids):",
      dict(zero_types))
print("   zero-id ids whose type is ONLY 10 (EyeCandy): %d"
      % sum(1 for uid, e in units.items()
            if e["category"] == "unresolved_zero_id" and e["type"] == [10]))
print("   the 2 positive-but-missing ids:",
      [(uid, e["internal"], e["name_string_id"]) for uid, e in units.items()
       if e["category"] == "unresolved_missing_from_strings"])
print("   the 4 negative ids:",
      [(uid, e["internal"], e["name_string_id"]) for uid, e in units.items()
       if e["category"] == "unresolved_negative_id"])

# internal-name vs localised-name relationship
alpha_code = 0
for uid, e in units.items():
    if e["resolved"] and e["internal"] and e["internal"].isupper() \
            and e["internal"].replace("_", "").isalnum() \
            and 3 <= len(e["internal"]) <= 8:
        alpha_code += 1
print()
print("== internal Name vs localised name ==")
resolved = [e for e in units.values() if e["resolved"]]
print("   resolved ids: %d" % len(resolved))
print("   resolved ids whose internal code looks like a 3-8 char ALLCAPS code: %d"
      % alpha_code)
same = sum(1 for e in resolved
           if e["internal"] and e["en"]
           and e["internal"].lower() == e["en"].lower())
print("   ids where internal == localised (case-insensitive): %d" % same)
# how many internal codes are unique
codes = collections.Counter(e["internal"] for e in resolved if e["internal"])
print("   distinct internal codes among resolved ids: %d" % len(codes))
dups = [(k, v) for k, v in codes.most_common(6)]
print("   most reused internal codes (code, #ids):", dups)
# does one internal code ever map to multiple localised names?
code_to_names = collections.defaultdict(set)
for e in resolved:
    if e["internal"]:
        code_to_names[e["internal"]].add(e["en"])
multi = {k: sorted(v) for k, v in code_to_names.items() if len(v) > 1}
print("   internal codes mapping to MULTIPLE localised EN names: %d" % len(multi))
print("   examples:", list(multi.items())[:6])

# ---------------------------------------------------------------- techs
tclass = collections.Counter()
DEFAULT_NAMES = {7000, 6000}
default_hits = collections.Counter()
for k, e in techs.items():
    sid = e["name_string_id"]
    if e["resolved"]:
        cat = "resolved"
    elif not isinstance(sid, int) or sid <= 0:
        cat = "unresolved_zero_or_negative"
    elif sid in DEFAULT_NAMES:
        cat = "unresolved_placeholder_default"
        default_hits[sid] += 1
    else:
        cat = "unresolved_missing_from_strings"
    e["category"] = cat
    tclass[cat] += 1

print()
print("== TECH categories ==")
for k, v in tclass.most_common():
    print("   %-36s %5d" % (k, v))
print("   placeholder default id split:", dict(default_hits))
print("   the genuine gaps:",
      sorted((e["name_string_id"], e["internal"]) for e in techs.values()
             if e["category"] == "unresolved_missing_from_strings"))

tres = [e for e in techs.values() if e["resolved"]]
print()
print("   resolved techs with id > 7399 : %d / %d"
      % (sum(1 for e in tres if e["name_string_id"] > 7399),
         sum(1 for e in techs.values()
             if isinstance(e["name_string_id"], int) and e["name_string_id"] > 7399)))
print("   resolved techs description.e n non-null: %d"
      % sum(1 for e in tres if e["description"]["en"]))
print("   resolved techs help.en non-null        : %d"
      % sum(1 for e in tres if e["help"]["en"]))
print("   resolved techs tech_tree.en non-null   : %d"
      % sum(1 for e in tres if e["tech_tree"]["en"]))

# zh coverage
u_zh = sum(1 for e in units.values() if e["resolved"] and e["zh"])
t_zh = sum(1 for e in tres if e["zh"])
print()
print("   unit ids with a zh name : %d" % u_zh)
print("   tech ids with a zh name : %d" % t_zh)
print("   resolved ids missing zh (units): %d"
      % sum(1 for e in units.values() if e["resolved"] and not e["zh"]))
print("   resolved ids missing zh (techs): %d"
      % sum(1 for e in tres if not e["zh"]))

json.dump(units, open(os.path.join(HERE, "unit_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(techs, open(os.path.join(HERE, "tech_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

summary = {"units": dict(uclass), "techs": dict(tclass),
           "unit_total": len(units), "tech_total": len(techs)}
json.dump(summary, open(os.path.join(HERE, "_final_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("updated unit_names.json / tech_names.json with `category`; wrote _final_stats.json")

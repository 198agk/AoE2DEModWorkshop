"""Extract AGE's hardcoded label tables into external JSON schema files.

This is the concrete first step of the 'format description lives in data, not code'
architecture: AGE hardcodes these as C++ string tables; we lift them into JSON.
"""
import os, re, json, io

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.dirname(HERE)
SRC = os.path.join(PROBE, "source")
OUT = HERE
os.makedirs(OUT, exist_ok=True)

lists = open(os.path.join(SRC, "AGE", "AGE_Frame", "Lists.cpp"), encoding="utf-8", errors="replace").read()

def grab_block(var, text):
    """Collect every var.Add("...") in source order, with 1-based selection index."""
    items = []
    for m in re.finditer(r'%s\.Add\(\s*"((?:[^"\\]|\\.)*)"\s*\)' % re.escape(var), text):
        items.append(m.group(1).replace('\\"', '"'))
    return items

# ---- effect command types -------------------------------------------------
eff_types = grab_block("effect_type_names", lists)
# ---- effect attribute (unit stat) names -----------------------------------
eff_attrs = grab_block("effect_attribute_names", lists)
# ---- unit type names, dead-fish, etc: probe everything with _names.Add -----
all_names_vars = sorted(set(re.findall(r'\b(\w*names?)\s*\.Add\(', lists)))

report = {}
print("=== label tables found in AGE/AGE_Frame/Lists.cpp ===")
for v in all_names_vars:
    items = grab_block(v, lists)
    if items:
        print("  %-34s %d entries" % (v, len(items)))
        report[v] = items

# Save the two most important ones under explicit names
json.dump({"source": "AGE_Frame/Lists.cpp effect_type_names",
           "note": "index = combo-box selection - 1; Selection 0 is 'No Type/Invalid Type'",
           "entries": eff_types},
          open(os.path.join(OUT, "effect_command_types.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

json.dump({"source": "AGE_Frame/Lists.cpp effect_attribute_names",
           "note": "index = combo-box selection - 1; describes effect command C parameter",
           "entries": eff_attrs},
          open(os.path.join(OUT, "effect_attributes.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

json.dump(report, open(os.path.join(OUT, "age_label_tables_raw.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

print("\n=== EFFECT COMMAND TYPES (%d) ===" % len(eff_types))
for i, s in enumerate(eff_types):
    print("   %3d  %s" % (i, s))

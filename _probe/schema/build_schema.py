"""Build the authoritative external schema for the AoE2:DE dat effect/attribute layer.

Inputs (all read-only, from the game's own shipped source):
  - AGE/AGE_Frame/Lists.cpp      -> effect type names, attribute names, class names
  - AGE/AGE_Frame/Techs.cpp      -> parameter semantics per command type
  - Tools_Builds/AGE3NamesV0007.ini -> civ resource names, armor names, terrain tables
Output: _probe/schema/*.json

*** The branch rule (read this before touching the extractors) ***

AGE's ``Lists.cpp`` fills each combo table with runtime ``if/else`` on
``GenieVersion`` / ``GameVersion`` / ``isAoE2DE``, i.e. it holds EVERY engine's
names in one file.  Grabbing every ``.Add("...")`` and keying by the number in
the label means the LAST entry written wins -- and AGE happens to put the
correct AoE2 branch first and the other engine's second, so last-write-wins
silently ships Star Wars / AoE1 names.  That is exactly what happened to
attributes 19/101/104/105/106 and to the entire class table.

So: walk the real branches (``cpp_branch.py``) and evaluate them for AoE2:DE.
An unrecognised condition raises instead of guessing.
"""
import os, re, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cpp_branch as CB                                   # noqa: E402

# Paths are derived from this file, not hardcoded: the workspace moved once
# (2026-10-17) and two generators kept writing into the dead path, so the
# regeneration silently produced nothing.  ``..`` from _probe/schema is _probe.
PROBE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT  = os.path.dirname(PROBE)
SRC  = os.path.join(PROBE, "source")
TOOLS= os.path.join(ROOT, "aoe2docs")   # holds AGE3NamesV0007.ini
OUT  = os.path.join(PROBE, "schema")
os.makedirs(OUT, exist_ok=True)

lists = open(os.path.join(SRC, "AGE", "AGE_Frame", "Lists.cpp"), encoding="utf-8", errors="replace").read()

def add_entries(var, text):
    """Naive harvest -- ONLY for tables with no version-conditional branches."""
    return [m.group(1).replace('\\"', '"')
            for m in re.finditer(r'%s\.Add\(\s*"((?:[^"\\]|\\.)*)"\s*\)' % re.escape(var), text)]

def branch_entries(var):
    """Harvest ONLY the entries the AoE2:DE branch of `var` actually adds."""
    return CB.extract(lists, var)

BRANCH_RULE = ("walked AGE's own version branches and evaluated them for AoE2:DE "
               "(GenieVersion = GV_C32 = 54, GameVersion = EV_DE2, isAoE2DE = true); "
               "an unmodelled condition raises rather than guessing")

# ---------------------------------------------------------------------------
# 1. Effect command types.  The raw `Type` byte is what lives in the dat.
# ---------------------------------------------------------------------------
by_num = CB.by_number(branch_entries("effect_type_names"))
types = dict(by_num)
print("effect types from the DE branch: %d" % len(types))

# parameter semantics, lifted from AGE_Frame/Techs.cpp GetEffectCmdName()
TARGET = {}
for v, disp in ((10, "Team"), (20, "Enemy"), (30, "Neutral"), (40, "Gaia"),
                (200, "OwnMasterObjects"), (203, "SelectedUnit")):
    TARGET[v] = disp

SPEC = {
  "0":  {"label": "Attribute Modifier (Set)",      "params": ["A:unit or -1", "B:class or -1", "C:attribute", "D:new value"], "summary": "Set an attribute to a value"},
  "1":  {"label": "Resource Modifier (Set/Change)","params": ["A:resource id", "B:0=set/1=change", "C:times-resource or -1", "D:value"], "summary": "Set or add to a resource"},
  "2":  {"label": "Enable/Disable Unit",           "params": ["A:unit id", "B:0=disable/1=enable"], "summary": "Toggle unit availability"},
  "3":  {"label": "Upgrade Unit",                  "params": ["A:from unit", "B:to unit", "C:-1=all/2=selected/3=incl own master/other=on map"], "summary": "Replace one unit with another"},
  "4":  {"label": "Attribute Modifier (+/-)",      "params": ["A:unit or -1", "B:class or -1", "C:attribute", "D:delta"], "summary": "Add to an attribute"},
  "5":  {"label": "Attribute Modifier (Multiply)", "params": ["A:unit or -1", "B:class or -1", "C:attribute", "D:factor"], "summary": "Multiply an attribute"},
  "6":  {"label": "Resource Modifier (Multiply)",  "params": ["A:resource id", "B:unused", "C:unused", "D:factor"], "summary": "Multiply a resource"},
  "7":  {"label": "Spawn Unit",                    "params": ["A:unit id", "B:source unit/building", "C:count", "D:unused"], "summary": "Create units on the map"},
  "8":  {"label": "Modify Tech",                   "params": ["A:tech id", "B:sub-field (see B-codes)", "C:unused", "D:value"], "summary": "Change a tech's own properties",
         "B_codes": {"-1": "set research time", "-2": "add to research time", "0..3": "set cost type N",
                     "4": "set research location", "5": "set research button", "6": "set icon",
                     "7": "set name", "8": "set description", "9": "enable/disable stacking",
                     "10": "set stacking cap", "11": "set hotkey", "12": "0=disable / 1=enable tech",
                     "16384..16387": "add to cost type (B-16384)"}},
  "101": {"label": "Tech Cost Modifier",           "params": ["A:tech id", "B:cost type", "C:resource", "D:value"], "summary": "Change a tech's cost"},
  "102": {"label": "Disable Tech",                 "params": ["D:tech id (via D)"], "summary": "Remove a tech from the tree"},
  "103": {"label": "Tech Time Modifier",           "params": ["A:tech id", "D:value"], "summary": "Change research time"},
  "206": {"label": "Transform Selected Unit",       "params": ["A:unit id"], "summary": "Morph the selected unit"},
}
for base, prefix in ((10, "Team "), (20, "Enemy "), (30, "Neutral "), (40, "Gaia ")):
    for off, src in ((0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"), (6, "6")):
        v = base + off
        if v in types:
            SPEC[str(v)] = {"label": types[v], "params": SPEC.get(src, {}).get("params", []),
                            "summary": prefix + SPEC.get(src, {}).get("summary", types[v])}
for v in (200, 201, 202, 203, 204, 205):
    src = {"200": "0", "201": "4", "202": "5", "203": "0", "204": "4", "205": "5"}[str(v)]
    SPEC[str(v)] = {"label": types[v], "params": SPEC[src]["params"],
                    "summary": types[v].replace(" Attribute Modifier", ": ") + " on own-master/selected units"}

schema_types = {str(v): {"raw": v, "label": types[v],
                         "params": SPEC.get(str(v), {}).get("params", []),
                         "summary": SPEC.get(str(v), {}).get("summary", ""),
                         "b_codes": SPEC.get(str(v), {}).get("B_codes")}
                for v in sorted(types)}
json.dump({"source": "AGE/AGE_Frame/Lists.cpp + Techs.cpp",
           "note": "raw = the uint8 EffectCommand.Type value as stored in the .dat; "
                   + BRANCH_RULE,
           "types": schema_types},
          open(os.path.join(OUT, "effect_command_types.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
# 2. Effect attributes (the C parameter of type 0/4/5/10..)
# ---------------------------------------------------------------------------
attrs = CB.by_number(branch_entries("effect_attribute_names"))
json.dump({"source": "AGE/AGE_Frame/Lists.cpp effect_attribute_names",
           "note": "value = the C parameter; names are AGE's; some ids have per-unit-type meanings; "
                   + BRANCH_RULE + ".  Do NOT key by list position -- AGE collapses several "
                   "engines' entries into one slot, and the collision picks the wrong name.",
           "attributes": {str(k): v for k, v in sorted(attrs.items())}},
          open(os.path.join(OUT, "effect_attributes.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
# 3. AGE3NamesV0007.ini — the numeric->human table for civ resources & armor
# ---------------------------------------------------------------------------
ini_path = os.path.join(TOOLS, "AGE3NamesV0007.ini")
ini = open(ini_path, encoding="latin-1").read()
sections, cur = {}, None
for line in ini.splitlines():
    line = line.strip()
    if line.startswith("[") and line.endswith("]"):
        cur = line[1:-1]; sections[cur] = {}
    elif cur and "=" in line:
        k, v = line.split("=", 1)
        sections[cur][k.strip()] = v.strip()
json.dump(sections, open(os.path.join(OUT, "AGE3NamesV0007.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
# 4. Class names (the B parameter of a modifier command, and the packed high
#    byte of attribute 8/9).
#
#    Keyed by the NUMBER IN THE LABEL, not by list position.  AGE's first entry
#    is a sentinel ("No Class/Invalid Class") with no number, and several
#    branches collapse two engines' entries into one slot ("18 - Priest" vs
#    "18 - Monk"), so a positional table is shifted from index 19 onwards.  The
#    .dat stores the label's number: Archer's Class field is 0 and the tech
#    "C-Bonus, Archers +20% HP" targets B=0.
# ---------------------------------------------------------------------------
classes = CB.by_number(branch_entries("class_names"))
json.dump({"source": "AGE/AGE_Frame/Lists.cpp class_names",
           "note": "key = the id in AGE's label, NOT the list slot; this is the value the .dat "
                   "stores (Archer's Class field is 0 and its bonus techs target B=0); "
                   + BRANCH_RULE + ".  The sentinel entry carries no number and is dropped; "
                   "ids AGE does not name must be rendered as 'Class <n>', never guessed.",
           "classes": {str(k): v for k, v in sorted(classes.items())}},
          open(os.path.join(OUT, "armor_classes.json"), "w", encoding="utf-8", newline="\n"),
          ensure_ascii=False, indent=1)

print("wrote:", sorted(os.listdir(OUT)))
print("effect types: %d | attributes: %d | classes: %d | ini sections: %s"
      % (len(schema_types), len(attrs), len(classes), list(sections)))
print("\nciv resource names sample:",
      {k: sections.get("AoE2DECivResourceNames", {}).get(k)
       for k in ("0", "4", "6", "11", "91", "92", "93", "94", "110", "195")})

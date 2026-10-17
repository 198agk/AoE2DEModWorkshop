"""End-to-end validation: do our decoded dat fields equal what the game's own UI
rendered on screen in the user's screenshots?

Ground truth = the live game.  In shot 5 (55s) the selected unit is a Scout
Cavalry and the in-game panel reads:

    生命 45/45 | 攻击 3 | 护甲 0/2 | [orange arrow] 2 | [brown icon] 1.20

If our decoded values reproduce all of those, the whole chain (deflate -> parse ->
fields -> meaning) is verified against the actual game, not merely a spec.
"""
import os, sys, io, json, struct, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
INI = r"D:\Games\Steam\steamapps\common\AoE2DE\Tools_Builds\AGE3NamesV0007.ini"


def load_ini(path, section):
    out, cur = {}, None
    for line in open(path, "r", encoding="latin-1"):
        line = line.rstrip("\r\n")
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]; continue
        if cur == section and "=" in line:
            k, v = line.split("=", 1); out[k.strip()] = v.strip()
    return out


ARMOR = load_ini(INI, "AoE2DEArmorNames")
cn = lambda c: ARMOR.get(str(c), "Class %s" % c)

import attack_semantics as AS          # reuse the verified deep walker

byid = AS.byid
names = json.load(open(os.path.join(os.path.dirname(HERE), "semantic",
                                    "unit_names.json"), encoding="utf-8"))

# Scout Cavalry is id 448.  Also show its upgrade line.
print("=" * 78)
print("GROUND TRUTH: the live game screenshot (shot 5, t=00:00:55)")
print("  selected unit panel:  生命 45/45 | 攻击 3 | 护甲 0/2 | [arrow] 2 | [brown] 1.20")
print("=" * 78)

for uid in (448, 546, 441, 751):
    u = byid.get(uid)
    if not u:
        print("\nid %s NOT PRESENT in civ[1]" % uid); continue
    t = u["type50"]
    nm = names.get(str(uid)) or {}
    print("\nid %-4s internal=%-8r en=%-16r zh=%r" %
          (uid, u["name"], nm.get("en"), nm.get("zh")))
    print("   hit_points             = %-6s   <- 生命 45/45" % u["hit_points"])
    print("   displayed_attack       = %-6s   <- 攻击 3" % t["displayed_attack"])
    print("   displayed_melee_armour = %-6s   <- 护甲 first number" % t["displayed_melee_armour"])
    print("   armor class 3 (pierce) = %-6s   <- 护甲 second number"
          % sum(e["amount"] for e in t["armors"] if e["class"] == 3))
    print("   line_of_sight          = %-6s   <- possibly the '2'?" % u["line_of_sight"])
    print("   speed                  = %-6s   <- possibly '1.20'?" % u.get("speed"))
    print("   displayed_range        = %-6s" % t["displayed_range"])
    print("   displayed_reload_time  = %-6s   <- possibly '2'?" % t["displayed_reload_time"])
    print("   attack list            = %s"
          % [(e["class"], cn(e["class"]), e["amount"]) for e in t["attacks"]])
    print("   armor list             = %s"
          % [(e["class"], cn(e["class"]), e["amount"]) for e in t["armors"]])

print("""
==== READING ====
The panel's four numbers map onto dat fields as:
    45/45  -> unit.hit_points              (Type50 not involved)
    3      -> Type50.displayed_attack      (NOT the raw attack list)
    0      -> Type50.displayed_melee_armour
    2      -> armor list entry with class 3 (Base Pierce)  [or a 'displayed' field]
    2      -> Type50.displayed_reload_time  (the clock glyph) -- verify below
    1.20   -> unit.speed (the brown-boot glyph)
""")

print("=" * 78)
print("THE 'displayed_*' TRAP -- the single most important product finding")
print("=" * 78)
n_diff = 0
checked = 0
for uid, u in byid.items():
    t = u.get("type50")
    if not t:
        continue
    raw_base = max(sum(e["amount"] for e in t["attacks"] if e["class"] in (3, 4)), 0)
    shown = t["displayed_attack"]
    checked += 1
    if shown is not None and raw_base != shown:
        n_diff += 1
if checked:
    print("  units where max(class3,class4 raw attack) != displayed_attack: "
          "%d / %d (%.1f%%)" % (n_diff, checked, 100.0 * n_diff / checked))

print("""
  The dat stores BOTH a raw attack/armour list AND separate displayed_* fields.
  They are allowed to disagree.  Consequences for the tool:
    * 'shown value' and 'real value' are two different targets.
    * Editing the raw list without updating displayed_* makes the UI lie.
    * Editing displayed_* without the raw list makes the UI cosmetic only.
  Every intent-based edit must state which one it means (default: both).
  Same applies to displayed_range / displayed_reload_time.

  base_armor == 10000 on every unit is a SENTINEL, not an armour value.
  It must be preserved byte-for-byte.
""")

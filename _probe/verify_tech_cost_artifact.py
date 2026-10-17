# -*- coding: utf-8 -*-
"""BLACK BOX: build a tech.cost mod through the product facade and grade it.

Nothing here imports the compiler's internals to decide whether the artifact is
good.  It reads the emitted file off disk, inflates it with the game's own
path, and hands it to the UNMODIFIED parser from the vendored engine.
"""
import os, sys, json, shutil, contextlib, io, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(HERE)
if root not in sys.path:
    sys.path.insert(0, root)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from aoe2mod import api as A
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_intent", "LoomGoldMinus20_probe")
BASE_DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

fails = []
def check(label, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + ((" :: " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

tk = A.open_toolkit(GAME)
INTENT = {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -20}

print("=== 1. the plan a user would read BEFORE agreeing ===")
pl = tk.plan(INTENT)
print("  ", pl["description"], "| slot", pl.get("cost_slot"), "| current", pl.get("value"))
# The sentence MUST name the resource: "织布机 成本 -20" leaves the user unable
# to tell whether they are about to reprice the food or the gold.  This is the
# same text compiler.Resolved.describe_target() produces, and plan() and build()
# deliberately share it so a preview can never word things differently.
check("plan reads naturally", pl["description"] == "织布机 成本 gold -20", pl["description"])
check("plan knows the slot", pl.get("cost_slot") == 3, pl.get("cost_slot"))

print("\n=== 2. build it ===")
man = tk.build(INTENT, OUT, title="Loom Gold -20", author="probe",
               description="tech.cost black-box probe", overwrite=True)
print("  mod dir:", man["mod_dir"])
for f in sorted(man["files"], key=lambda d: d["rel"]):
    print("   %-56s %10d B" % (f["rel"], f["bytes"]))

print("\n=== 3. mod-folder contract (what the engine scans) ===")
check("info.json at the mod root", os.path.isfile(os.path.join(OUT, "info.json")))
info = json.loads(open(os.path.join(OUT, "info.json"), encoding="utf-8").read(),
                  strict=False)
check("info.json has the 4 shipped keys",
      sorted(info) == ["Author", "CacheStatus", "Description", "Title"], sorted(info))
rel = "resources/_common/dat/empires2_x2_p1.dat"
dat_out = os.path.join(OUT, *rel.split("/"))
check("dat mirrors the GAME ROOT path", os.path.isfile(dat_out), rel)
check("no extra 'resources' nesting",
      not os.path.isdir(os.path.join(OUT, "resources", "resources")))
base_size = os.path.getsize(BASE_DAT)
out_size = os.path.getsize(dat_out)
print("  base %d B -> emitted %d B (%+d)" % (base_size, out_size, out_size - base_size))
check("emitted dat is a real file", out_size > 1000)

print("\n=== 4. the game's OWN inflate path must rebuild it ===")
raw, how = P.load_dat(dat_out)
print("  inflate:", how, "->", len(raw), "B")
check("inflates to the base raw size", len(raw) == 93268152, len(raw))

print("\n=== 5. the UNMODIFIED parser must accept every byte ===")
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
print("  final offset %d of %d | leftover %d" % (p.r.pos, len(raw), len(raw) - p.r.pos))
check("exact EOF", p.r.pos == len(raw), len(raw) - p.r.pos)

print("\n=== 6. the intent is actually IN the artifact ===")
techs = L.locate_techs(raw, [(s, e) for (n, s, e) in p.stage_offsets
                            if n == "9 Techs"][0][0], p.r.gv)
loom = techs[22]
slots = [(c["type"], c["amount"], c["flag"]) for c in loom["costs"]]
print("  Loom slots now:", slots)
gold = [c["amount"] for c in loom["costs"] if c["type"] == 3]
check("gold is 30 (was 50)", gold == [30], gold)
check("the other two slots are untouched",
      [(c["type"], c["amount"]) for c in loom["costs"] if c["type"] != 3]
      == [(-1, 0), (-1, 0)],
      [(c["type"], c["amount"]) for c in loom["costs"] if c["type"] != 3])

print("\n=== 7. nothing else in the stream moved ===")
raw_base, _ = P.load_dat(BASE_DAT)
diff = [i for i in range(len(raw_base)) if raw_base[i] != raw[i]]
print("  changed bytes: %d" % len(diff))
for off in diff:
    print("    @0x%08X  %02X -> %02X" % (off, raw_base[off], raw[off]))
check("exactly the expected bytes changed", len(diff) == 1, len(diff))
# the one byte must be the low byte of the gold amount we located
check("the changed byte is the gold amount's low byte",
      diff[0] == loom["costs"][0]["_off_amount"] if slots[0][0] == 3
      else diff[0] == [c for c in loom["costs"] if c["type"] == 3][0]["_off_amount"],
      hex(diff[0]) if diff else None)

print("\n=== 8. the rest of the world is intact ===")
p_base = P.Parser(raw_base)
with contextlib.redirect_stdout(io.StringIO()):
    p_base.parse()
for key in ("civ_count", "tech_count", "effect_count", "unit_header_count",
            "graphic_count", "sound_count", "terrain_restriction_count"):
    a, b = p_base.stats.get(key), p.stats.get(key)
    check("counter %s unchanged (%s)" % (key, a), a == b, (a, b))
check("civ count is still 63", p.stats.get("civ_count") == 63, p.stats.get("civ_count"))
check("tech count is still 1510", p.stats.get("tech_count") == 1510,
      p.stats.get("tech_count"))
# Loom's research time must not have been collateral damage
check("Loom research time untouched",
      [d["research_time"] for d in loom["research_locations"]] == [25],
      [d["research_time"] for d in loom["research_locations"]])

print("\n=== 9. a toolkit pointed at the ARTIFACT sees the new price ===")
# The mod folder mirrors the game root, so it IS a valid root to open.  This is
# the same code path a user hits after installing the mod.
tk2 = A.open_toolkit(OUT)
d = tk2.describe(22, "tech")
print("  artifact says Loom costs:", d["stats"]["costs"])
check("describe on the artifact reports gold 30",
      any(c["resource"] == "gold" and c["amount"] == 30
          for c in d["stats"]["costs"]), d["stats"]["costs"])
check("describe still exposes Loom's research time",
      d["stats"]["research_time"] == [25], d["stats"]["research_time"])

print("\n" + ("BLACK BOX: SHIPPABLE ARTIFACT VALID" if not fails
              else "FAILURES: %d -> %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)

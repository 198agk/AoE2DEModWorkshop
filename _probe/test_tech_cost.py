# -*- coding: utf-8 -*-
"""tech.cost: structure, slot selection, refusals -- plus the unit.cost fix.

Read-only against the game tree.  Nothing is written outside this process.
"""
import os, sys, struct, contextlib, io

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(HERE)
if root not in sys.path:
    sys.path.insert(0, root)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from aoe2mod import api as A              # noqa: E402
from aoe2mod.dat import parser as P       # noqa: E402
from aoe2mod.dat import locate as L       # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = r"C:\Users\26913\Games\Age of Empires 2 Empire"  # intentionally wrong; fixed below
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
BASE_DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
LEGACY = os.path.join(MODS, "297820_10 倍资源文明联盟3倍科技",
                      "resources", "_common", "dat", "empires2_x2_p1.dat")

fails = []
def check(label, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + ((" :: " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)

tk = A.open_toolkit(GAME)
print("game:", tk.game_root, "| version:", tk.version)

# ---------------------------------------------------------------------------
print("\n=== A. schema declares tech.cost and reuses resource_types ===")
sch = tk.schema()
it = sch["intents"]["intents"]
bd = sch["bindings"]
check("tech.cost exists", "tech.cost" in it, sorted(it))
check("applies_to tech", it["tech.cost"].get("applies_to") == "tech")
check("requires a resource", "resource" in it["tech.cost"]["fields"])
_all_opts = (set(it["tech.cost"]["fields"]["resource"]["options"])
             | set(it["unit.cost"]["fields"]["resource"]["options"]))
check("every resource_types key is reachable by some cost intent",
      _all_opts == set(bd["resource_types"]),
      sorted(set(bd["resource_types"]) - _all_opts))
# A tech's cost enum deliberately omits population: no tech in BASE pays it
# (type 4 appears 0 times across all 1510 techs), while units do (House,
# Villager -- 1 pop each).  Requiring the two enums to be identical would
# demand an intent that can never match a slot.
check("tech.cost omits population (no tech pays it)",
      "population" not in it["tech.cost"]["fields"]["resource"]["options"],
      it["tech.cost"]["fields"]["resource"]["options"])
check("unit.cost offers population (House/Villager pay it)",
      "population" in it["unit.cost"]["fields"]["resource"]["options"],
      it["unit.cost"]["fields"]["resource"]["options"])
check("tech_fields.cost bound to cost_entry",
      bd["tech_fields"]["cost"]["source"] == "cost_entry")
check("cost is non_negative", bd["tech_fields"]["cost"].get("non_negative") is True)
check("unit cost_entry also non_negative", bd["cost_entry"].get("non_negative") is True)

# ---------------------------------------------------------------------------
print("\n=== B. locator records all 3 cost slots of a tech ===")
raw, how = P.load_dat(BASE_DAT)
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
# stage_offsets entries are (name, start, end); match the name EXACTLY -- a
# substring match also hits '10 Tail+TechTree', whose start is the tech END.
tech_start, tech_end = [(s, e) for (n, s, e) in p.stage_offsets if n == "9 Techs"][0]
techs = L.locate_techs(raw, tech_start, p.r.gv)
print("  tech count:", len(techs))
check("1510 techs", len(techs) == 1510, len(techs))
check("every tech has exactly 3 cost slots",
      all(len(t["costs"]) == 3 for t in techs),
      sorted({len(t["costs"]) for t in techs}))
# The three slots must read back the bytes they claim, or the offsets lie.
bad = []
for t in techs:
    for c in t["costs"]:
        if struct.unpack_from("<h", raw, c["_off_amount"])[0] != c["amount"]:
            bad.append(c["_off_amount"])
check("every _off_amount points at its own amount", not bad, bad[:5])

# Known ground truth, verified against the shipped bytes earlier.
TRUTH = {
    22:  ("Loom",           [(3, 50)]),
    103: ("Imperial Age",   [(0, 1000), (3, 800)]),
    12:  ("Crop rotation",  [(0, 250), (1, 250)]),
    50:  ("Masonry",        [(1, 175), (0, 150)]),
    51:  ("Architecture",   [(1, 200), (0, 300)]),
    102: ("Feudal Age",     [(0, 800), (3, 200)]),
}
for tid, (nm, want) in TRUTH.items():
    got = [(c["type"], c["amount"]) for c in techs[tid]["costs"] if c["amount"]]
    check("tech %d %s costs %s" % (tid, nm, want), got == want, got)

# ---------------------------------------------------------------------------
print("\n=== C. slot selection: first NONZERO of that type ===")
def pick(costs, want):
    return C._pick_cost_slot(costs, want)

# Cartography (19) is the real tech whose cost slots are (0,0,1),(3,0,1).
t19 = techs[19]
print("  tech 19 raw slots:", [(c["type"], c["amount"], c["flag"]) for c in t19["costs"]])
c0 = pick(t19["costs"], 0)
check("zero-payment placeholder still selectable", c0 is not None and c0["type"] == 0)
check("and its amount really is 0", c0["amount"] == 0)

# Elite Genitour (430): flagged 0 but genuinely 800 food / 500 gold.
t430 = techs[430]
print("  tech 430 raw slots:", [(c["type"], c["amount"], c["flag"]) for c in t430["costs"]])
c430 = pick(t430["costs"], 0)
check("real cost with flag==0 is NOT skipped", c430 is not None and c430["amount"] == 800,
      c430)
check("absent resource -> None", pick(t430["costs"], 2) is None,
      pick(t430["costs"], 2))

# The whole-table invariant that makes 'by type' safe.
dupes = 0
for t in techs:
    seen = {}
    for c in t["costs"]:
        if c["amount"] and c["type"] >= 0:
            seen[c["type"]] = seen.get(c["type"], 0) + 1
    dupes += sum(1 for v in seen.values() if v > 1)
check("no tech has two PAID slots of one type", dupes == 0, dupes)

# ---------------------------------------------------------------------------
print("\n=== D. compile tech.cost for real ===")
def run(note, intent, expect_ok=True):
    try:
        rep = C.compile_intent(BASE_DAT, intent)
    except C.IntentError as exc:
        print(("  refused: " if not expect_ok else "  UNEXPECTED REFUSAL: ") + str(exc))
        return None, exc
    if not expect_ok:
        print("  UNEXPECTEDLY ACCEPTED: " + note)
        return rep, None
    print("  %s -> %s | edits %d | civs_edited %d | leftover %d"
          % (note, rep["resolved"], rep["edit_count"], rep["civs_edited"],
             (rep.get("verification") or {}).get("leftover", -1)))
    return rep, None

def eof_ok(rep):
    """_compile_* returns the verification sub-report; EOF lives inside it."""
    v = rep.get("verification") or {}
    return v.get("leftover") == 0 and not v.get("unexpected_changes")

rep, err = run("Loom gold -20", {"intent": "tech.cost", "tech": "Loom",
                                 "resource": "gold", "delta": -20})
ok = rep is not None
if ok:
    e = rep["edits"][0]
    check("Loom gold 50 -> 30", e.before == 50 and e.after == 30, (e.before, e.after))
    check("edit is inside the cost slot", e.where.startswith("tech[22] 成本 gold"), e.where)
    check("civs_edited is 0 for a global tech", rep["civs_edited"] == 0)
    check("exact EOF", eof_ok(rep), (rep.get("verification") or {}).get("leftover"))
    check("geometry unchanged", (rep.get("verification") or {}).get("ok", True))

rep2, _ = run("Crop rotation wood +50 (id, not name)",
              {"intent": "tech.cost", "tech": 12, "resource": "wood", "delta": 50})
if rep2:
    e = rep2["edits"][0]
    check("tech 12 wood 250 -> 300", e.before == 250 and e.after == 300, (e.before, e.after))
    check("entity_id resolved from the int", rep2["entity_id"] == 12)

rep3, _ = run("Feudal Age food -> 1000 by value",
              {"intent": "tech.cost", "tech": 102, "resource": "food", "value": 1000})
if rep3:
    e = rep3["edits"][0]
    check("value op ignores the before", e.after == 1000, e.after)

# ---------------------------------------------------------------------------
print("\n=== E. refusals stay user-facing prose ===")
_, err = run("negative cost", {"intent": "tech.cost", "tech": "Loom",
                               "resource": "gold", "value": -10}, expect_ok=False)
check("negative is refused", err is not None and "negative" in str(err), err)

_, err = run("discount below zero", {"intent": "tech.cost", "tech": "Loom",
                                     "resource": "gold", "delta": -100}, expect_ok=False)
check("over-discount refused", err is not None and "negative" in str(err), err)

_, err = run("resource the tech does not cost", {"intent": "tech.cost", "tech": "Loom",
                                                 "resource": "stone", "delta": 10},
             expect_ok=False)
check("absent resource refused", err is not None, err)

_, err = run("unknown resource", {"intent": "tech.cost", "tech": "Loom",
                                  "resource": "bananas", "delta": 1}, expect_ok=False)
check("unknown resource named", err is not None and "bananas" in str(err), err)

_, err = run("unknown tech", {"intent": "tech.cost", "tech": "no such tech",
                              "resource": "gold", "delta": 1}, expect_ok=False)
check("unknown tech refused", err is not None, err)

_, err = run("overflow", {"intent": "tech.cost", "tech": "Loom",
                          "resource": "gold", "value": 40000}, expect_ok=False)
check("overflow refused", err is not None and "16-bit" in str(err), err)

# ---------------------------------------------------------------------------
print("\n=== F. the unit.cost sign defect is closed ===")
u_neg, err = None, None
try:
    C.compile_intent(BASE_DAT, {"intent": "unit.cost", "unit": "Archer",
                                "resource": "wood", "delta": -100})
except C.IntentError as exc:
    err = exc
check("unit.cost no longer writes -75", err is not None and "negative" in str(err), err)
print("  reads: %s" % (err,))
# and a legitimate discount still works
try:
    rep4 = C.compile_intent(BASE_DAT, {"intent": "unit.cost", "unit": "Archer",
                                       "resource": "wood", "delta": -5})
    check("legit -5 still allowed", rep4["edits"][0].after == 20,
          rep4["edits"][0].after)
except C.IntentError as exc:
    check("legit -5 still allowed", False, exc)

# ---------------------------------------------------------------------------
print("\n=== G. plan()/describe() preview the same slot the build will move ===")
pl = tk.plan({"intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -20})
print("  plan:", pl["description"], "| kind:", pl["kind"],
      "| edits:", pl["edit_count"], "| slot:", pl.get("cost_slot"),
      "| value:", pl.get("value"))
check("plan kind is tech", pl["kind"] == "tech")
check("plan reports 0 civs", pl["civ_count"] == 0 and pl["civs"] == [])
check("plan previews 1 edit", pl["edit_count"] == 1)
check("plan names the slot", pl.get("cost_slot") == 3, pl.get("cost_slot"))
check("plan previews the current amount", pl.get("value") == 50, pl.get("value"))
check("no None leaked into the sentence", "None" not in pl["description"],
      pl["description"])

pl_missing = tk.plan({"intent": "tech.cost", "tech": "Loom",
                      "resource": "stone", "delta": 10})
check("plan reports 0 edits when the resource is absent",
      pl_missing["edit_count"] == 0, pl_missing["edit_count"])

d22 = tk.describe(22, "tech")
print("  describe tech 22:", d22["name"], d22["stats"])
check("describe exposes costs", "costs" in d22["stats"], d22["stats"].keys())
check("describe shows Loom's 50 gold",
      any(c["resource"] == "gold" and c["amount"] == 50 for c in d22["stats"]["costs"]),
      d22["stats"]["costs"])
check("describe hides the -1 sentinels",
      all(not c["resource"].startswith("type -") for c in d22["stats"]["costs"]),
      d22["stats"]["costs"])

# ---------------------------------------------------------------------------
print("\n=== H. legacy VER 7.8 also carries 3 cost slots ===")
if os.path.exists(LEGACY):
    raw7, _ = P.load_dat(LEGACY)
    p7 = P.Parser(raw7)
    with contextlib.redirect_stdout(io.StringIO()):
        p7.parse()
    t7 = L.locate_techs(raw7, [(s, e) for (n, s, e) in p7.stage_offsets
                               if n == "9 Techs"][0][0], p7.r.gv)
    print("  version:", p7.r.gv, "| techs:", len(t7))
    check("legacy techs also have 3 slots",
          all(len(t["costs"]) == 3 for t in t7), sorted({len(t["costs"]) for t in t7}))
    try:
        r7 = C.compile_intent(LEGACY, {"intent": "tech.cost", "tech": "Loom",
                                       "resource": "gold", "delta": -20})
        e7 = r7["edits"][0]
        v7 = r7.get("verification") or {}
        print("  legacy Loom gold: %s -> %s | leftover %s" % (e7.before, e7.after,
                                                             v7.get("leftover")))
        check("legacy tech.cost compiles", e7.before == 50 and e7.after == 30,
              (e7.before, e7.after))
        check("legacy exact EOF", v7.get("leftover") == 0, v7.get("leftover"))
    except C.IntentError as exc:
        check("legacy tech.cost compiles", False, exc)
else:
    print("  SKIP (no legacy dataset present)")

print("\n" + ("ALL TECH.COST CHECKS PASSED" if not fails
              else "FAILURES: %d -> %s" % (len(fails), fails)))
sys.exit(1 if fails else 0)

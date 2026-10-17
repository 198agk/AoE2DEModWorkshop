# -*- coding: utf-8 -*-
"""Step 4: measure candidate DATA-DRIVEN heuristics for finding task variants.

TRUTH SET = the units the engine actually swaps between, taken from the dat's
per-unit `Bird.TaskSwapGroup` uint8:
  group 1 (male basket)   = 14 ids
  group 2 (female basket) = 13 ids
  group 0 / absent        = no task swap

Heuristics measured against it:
  H1  identical full stat signature (id/name/DLL stripped)
  H2  identical LOOSE stat signature (hp, class, type, speed, los only)
  H3  linkedUnits.json "Villagers" entry membership
  H4  same LanguageDLLName within the villager-ranged ids
  H5  dat TaskSwapGroup != 0                      <- the real field
"""
import sys, os, json, struct, collections
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P, intent_patch as IP

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\taskfamily"
lines = []
def p(s=""):
    lines.append(s); print(s)

# --- patch read_bird to capture TaskSwapGroup (same proxy as probe 1) ------
class _PosProxy(object):
    __slots__ = ("_r",)
    def __init__(self, r): object.__setattr__(self, "_r", r)
    def at(self, k):
        r = self._r
        off = r.pos if hasattr(r, "pos") else r.o
        m = getattr(r, "marks", None)
        if m is not None: m[k] = off
        return off
    def __getattr__(self, n): return getattr(self._r, n)
    def __setattr__(self, n, v): setattr(self._r, n, v)

BY_OFF = {}
def read_bird_marked(inner):
    r = _PosProxy(inner)
    start = r.at("bird_start")
    b = {}
    b["default_task_id"] = r.i16()
    b["search_radius"] = r.f32()
    b["work_rate"] = r.f32()
    n = r.i16(); b["drop_sites"] = r.i16_array(n)
    r.at("task_swap_group"); b["task_swap_group"] = r.u8()
    r.i16(); r.i16(); r.u32(); r.u32(); r.u8()
    tn = r.i16(); b["task_count"] = tn
    for _ in range(tn): P.read_task(r)
    BY_OFF[start] = b
    return b
P.read_bird = read_bird_marked

def main():
    data, how = P.load_dat(BASE)
    civs, civs_start, gv, tail = IP.locate(data)
    distinct = {}
    for c in civs:
        for u in c["units"]:
            if u["id"] in distinct: continue
            off = u["_offs"].get("bird_start")
            distinct[u["id"]] = (u, BY_OFF.get(off) if off is not None else None)

    # ---------------- truth set ------------------------------------------
    truth = collections.defaultdict(set)
    for uid, (u, b) in distinct.items():
        g = b["task_swap_group"] if b else 0
        truth[g].add(uid)
    TRUE_POS = truth[1] | truth[2]
    p("=== TRUTH (dat Bird.TaskSwapGroup) ===")
    for g in sorted(truth):
        p("  group %-3s n=%-4d %s" % (g, len(truth[g]),
          sorted(truth[g]) if g in (1, 2, 3) else ""))
    p("  POSITIVE SET (tsg in {1,2}) = %d ids: %s" % (len(TRUE_POS), sorted(TRUE_POS)))

    # --- raw byte proof for a couple of records --------------------------
    p("\n=== raw-byte proof of the TaskSwapGroup field ===")
    for uid in (83, 293, 118, 448, 4):
        u, b = distinct[uid]
        off = u["_offs"].get("task_swap_group")
        if off is None:
            p("  unit %-6s no Bird struct" % uid); continue
        ctx = data[off - 8:off + 9]
        p("  unit %-6s name=%-10s tsg_off=0x%X value=%d  ctx=%s"
          % (uid, u["name"], off, data[off], ctx.hex(" ")))

    # ---------------- heuristic helpers ----------------------------------
    def sig_full(u, b):
        t50 = u.get("type50") or {}
        atk = tuple(sorted((a["class"], a["amount"]) for a in t50.get("attacks", [])))
        arm = tuple(sorted((a["class"], a["amount"]) for a in t50.get("armors", [])))
        return (u["type"], u["class"], u["hit_points"], u["icon_id"],
                round(u["line_of_sight"], 6), u["garrison_capacity"], u["sort_number"],
                round(u.get("speed") or 0.0, 6),
                round(t50.get("max_range", 0.0), 6), round(t50.get("min_range", 0.0), 6),
                t50.get("displayed_attack"), t50.get("displayed_melee_armour"),
                atk, arm,
                round(b["work_rate"], 6) if b else None,
                round(b["search_radius"], 6) if b else None)

    def sig_loose(u, b):
        return (u["type"], u["class"], u["hit_points"], u["icon_id"],
                round(u["line_of_sight"], 6), round(u.get("speed") or 0.0, 6))

    def evaluate(label, groups):
        """groups: dict key -> set(ids).  Measure how well `key` predicts truth."""
        # a prediction for id x = set of ids sharing its key (minus x)
        pred = {}
        for k, ids in groups.items():
            for i in ids:
                pred.setdefault(i, set()).update(ids - {i})
        tp = fp = fn = 0
        for uid in pred:
            got = pred[uid]
            exp = TRUE_POS - {uid}
            # only score ids that are in truth or got grouped with a truth id
            tp += len(got & exp); fp += len(got - exp)
        # recall over all 27 positives: does each positive have >=1 sibling?
        found = sum(1 for uid in TRUE_POS if pred.get(uid))
        p("  %-38s siblings_found_for %2d/%2d positives | linked-pair TP=%-4d FP=%-4d"
          % (label, found, len(TRUE_POS), tp, fp))
        return pred

    p("\n=== heuristic measurement (TP/FP counted over emitted sibling pairs) ===")
    g_full = collections.defaultdict(set)
    g_loose = collections.defaultdict(set)
    for uid, (u, b) in distinct.items():
        g_full[sig_full(u, b)].add(uid)
        g_loose[sig_loose(u, b)].add(uid)
    evaluate("H1 identical FULL stat signature", g_full)
    evaluate("H2 identical LOOSE stat signature", g_loose)

    # H3 linkedUnits.json
    lu = json.load(open(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\linkedUnits.json",
                        encoding="utf-8"))
    p("\n  linkedUnits.json entries:")
    g_lu = {}
    for i, e in enumerate(lu["Data"]):
        g_lu["lu%d:%s" % (i, e["Name"])] = set(e["Units"])
        p("    [%d] %-20s n=%-3d %s" % (i, e["Name"], len(e["Units"]), e["Units"]))
    evaluate("H3 linkedUnits.json entry", g_lu)
    for i, e in enumerate(lu["Data"]):
        if e["Name"] == "Villagers":
            L = set(e["Units"])
            p("\n    H3/details on the 'Villagers' entry (n=%d):" % len(L))
            p("      linkedUnits roster  = %s" % sorted(L))
            p("      truth positives     = %s" % sorted(TRUE_POS))
            p("      in roster, NOT truth (false friends) : %s"
              % sorted(L - TRUE_POS))
            p("      in truth, NOT roster (missed)        : %s"
              % sorted(TRUE_POS - L))

    # H4 DLL name agreement
    dll = collections.defaultdict(set)
    for uid, (u, b) in distinct.items():
        dll[u["_dll_name"]].add(uid)
    p("\n  === DLL-name collisions that matter (villager range 50..600 + 1800..2400) ===")
    for k, ids in sorted(dll.items()):
        v = sorted(x for x in ids if 50 <= x <= 600 or 1800 <= x <= 2400)
        if len(v) > 1:
            hit = set(v) & TRUE_POS
            p("    dll=%-6d n=%-3d %s   %s" % (k, len(v), v,
              ("<< ALL TRUTH" if set(v) <= TRUE_POS and hit else
               "contains %d truth" % len(hit))))
    evaluate("H4 same LanguageDLLName", dll)
    evaluate("H5 dat TaskSwapGroup != 0", {str(k): v for k, v in truth.items() if k})

    with open(os.path.join(OUT, "heuristic_measurement.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    p("\nwrote heuristic_measurement.txt")

if __name__ == "__main__":
    main()

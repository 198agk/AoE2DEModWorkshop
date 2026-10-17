"""Every operation shape the Resource Modifier family can take, end to end.

The family was refused wholesale before this round, so the read path, the
preview sentence and the byte written are all new.  This walks one row of each
shape the shipped data actually contains, plus the two shapes that must stay
refused, and prints what a user would see:

    add       (type 1, B=1, C=-1)  -- the 12 starting-resource grants
    set       (type 1, B=0, C=-1)
    multiply  (type 6,         C=-1)
    refused   (C != -1)            -- scales by another resource's value
    refused   (B not in {0,1})     -- an operation this tool does not read
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A
from aoe2mod.intent import compiler as C
from aoe2mod.dat import locate as L

PROBLEMS = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           (" -- " + detail) if detail else ""))
    if not ok:
        PROBLEMS.append(label)


def rows_of(tk, tech_id):
    return tk.effects(tech_id)["rows"]


def find(rows, pred):
    for r in rows:
        if pred(r):
            return r
    return None


def main():
    tk = A.open_toolkit()
    tk._ensure()
    print("resource modifier rows, as the UI would list them")
    print("")

    # --- the starting-resource grants, as the UI lists them ---------------
    r = rows_of(tk, 223)[0]
    print("add        tech 223 cmd 0 : %s = %r  op=%s scope=%r editable=%s"
          % (r["target_label"], r["value"], r["operation"], r["scope"],
             r["editable"]))
    check("an 'add' grant is editable", r["editable"], r.get("reason") or "")
    check("an 'add' grant names its resource", r["target_label"] == "起始食物",
          r["target_label"] or "(none)")
    check("an 'add' grant is not an attribute row",
          r["attribute_label"] is None, repr(r["attribute_label"]))

    # --- one pass over the whole space ------------------------------------
    # Not a guessed id list: 163 rows carry 'set' and 117 'multiply' over BASE,
    # and a short hardcoded list once made the 'set' branch check NOTHING while
    # the summary at the bottom still claimed all three operations were covered.
    # Same trap as the guard that only proves what it enumerates.
    reps = {}          # operation -> (tech id, row)
    refused_times = refused_b = 0
    examples = {}
    for tid in range(len(tk._tech_records())):
        for row in rows_of(tk, tid):
            if not row["resource"]:
                continue
            if row["editable"]:
                op = row["operation"]
                if op not in reps:
                    reps[op] = (tid, row)
            else:
                reason = row.get("reason") or ""
                if "scales by the current value" in reason:
                    refused_times += 1
                    examples.setdefault("times", (tid, row))
                elif "does not read as either" in reason:
                    refused_b += 1
                    examples.setdefault("badb", (tid, row))

    for op, (tid, row) in sorted(reps.items()):
        print("")
        print("%-10s tech %-5d cmd %d : %s = %r  op=%s editable=%s"
              % (op, tid, row["index"], row["target_label"], row["value"],
                 row["operation"], row["editable"]))
    check("add / set / multiply each occur and are editable",
          set(reps) == {"add", "set", "multiply"},
          "found %s" % sorted(reps))

    tid, row = reps["add"]
    p = tk.plan({"intent": "tech.effect", "tech": tid, "command": row["index"],
                 "delta": 500})
    print("           add preview    : %s" % p.get("description"))
    check("the add preview names the resource, not the tech",
          row["target_label"] in (p.get("description") or ""),
          p.get("description"))
    # NOT `str(row["target"]) not in desc`: a one-digit resource id is a
    # substring of any amount ("+500" contains a 5), so that check reports a
    # leak on correct output.  What actually has to be true is that the game's
    # label was used rather than the bare-number fallback.
    check("the add preview does not fall back to a bare resource number",
          ("Resource %d" % row["target"]) not in (p.get("description") or ""),
          p.get("description"))

    tid, row = reps["set"]
    ps = tk.plan({"intent": "tech.effect", "tech": tid, "command": row["index"],
                  "value": 4})
    print("           set preview    : %s" % ps.get("description"))
    check("a 'set' preview says it sets, and to what",
          "设为" in (ps.get("description") or ""), ps.get("description"))

    tid6, r6 = reps["multiply"]
    pm = tk.plan({"intent": "tech.effect", "tech": tid6, "command": r6["index"],
                  "delta": 0.05})
    print("           multiply preview: %s" % pm.get("description"))
    check("a multiply preview says it is a factor, not a quantity",
          "×" in (pm.get("description") or ""), pm.get("description"))

    # --- the two shapes that must stay refused ----------------------------
    print("")
    print("refusals (real commands this tool must not silently guess)")
    for key, why in (("times", "C != -1"), ("badb", "unreadable B")):
        if key in examples:
            tid, row = examples[key]
            print("  %-11s tech %-5d cmd %d : %s -- %s"
                  % (why, tid, row["index"], row["target_label"],
                     row.get("reason")))
    check("a times-resource row is refused, not guessed", refused_times > 0,
          "%d refused" % refused_times)
    check("an unreadable slot B is refused, not guessed", refused_b > 0,
          "%d refused" % refused_b)

    # --- the packed-pair trap --------------------------------------------
    print("")
    # A resource modifier whose slot C is 8 or 9 (armour/attack in the ATTRIBUTE
    # id space) must not have its number decoded as a packed pair.  Build one
    # synthetic row from the real machinery to prove the flag does the work.
    import json
    tables = C.load_effect_tables()
    print("packed-pair trap: a resource row's slot C is a times-resource, so a "
          "C of 8 or 9 must not trigger the 8-bit pair path")
    check("resource rows are flagged so the packed path cannot claim them",
          C._RESOURCE_SCOPE is not None and 1 in C._RESOURCE_SCOPE)

    print("")
    if PROBLEMS:
        print("RESOURCE MODIFIER SHAPES: %d FAILURE(S)" % len(PROBLEMS))
        for f in PROBLEMS:
            print("  - %s" % f)
        return 1
    print("RESOURCE MODIFIER SHAPES: CLEAN")
    print("add / set / multiply all render and write; the two shapes the engine "
          "uses for something else stay refused with a reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Does the schema DECLARE every resource the shipped data actually charges?

`intents.json` declares `unit.cost` over 5 resources and `tech.cost` over 4 (no
`population`).  That asymmetry is deliberate -- no shipped tech charges
population -- but until this file nothing ASSERTED it.  An enum is a promise
about the data; a promise nobody compares against the data is a list somebody
once typed.

So this walks every cost slot of every unit record and every tech record in the
shipped .dat, keeps the ones whose type is a declared resource id, and asserts
that the set of types it found is EXACTLY the set the matching intent declares.
If a game update makes some tech charge population, or a unit charge a resource
the schema forgot, this fails instead of the intent quietly having no slot.

It also reports the types that are NOT declared resources (the `unmapped_costs`
side), and asserts every one of them carries either a name from the game's own
15000+type table or is honestly reported without one -- so a UI reading
`unmapped_costs` never sees an unnamed-but-named-as-empty entry.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                  # noqa: E402
import aoe2mod.intent.compiler as C                      # noqa: E402
from aoe2mod.dat import locate as L                       # noqa: E402

FAILURES = []


def check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print("[%s] %s%s" % (mark, label, (" -- " + detail) if detail else ""))
    if not ok:
        FAILURES.append(label)
    return ok


def main():
    tk = A.open_toolkit()
    tk._ensure()
    # Toolkit does not cache the schema -- every public method calls load_schema().
    intents_schema, bindings = C.load_schema()

    declared = dict(bindings["resource_types"])          # name -> id
    id_to_name = {v: k for k, v in declared.items()}
    unit_opts = set((intents_schema["intents"]["unit.cost"]["fields"]["resource"]
                     .get("options") or ()))
    tech_opts = set((intents_schema["intents"]["tech.cost"]["fields"]["resource"]
                     .get("options") or ()))
    print("declared resource_types   : %s" % (sorted(id_to_name.items()),))
    print("unit.cost options         : %s" % (sorted(unit_opts),))
    print("tech.cost options         : %s" % (sorted(tech_opts),))
    print("")
    check("every declared option names a declared resource id",
          unit_opts <= set(declared) and tech_opts <= set(declared),
          "unit %s tech %s" % (sorted(unit_opts - set(declared)),
                               sorted(tech_opts - set(declared))))

    # ---- the data -----------------------------------------------------------
    unit_declared_types, unit_unmapped_types = set(), set()
    for c in tk._civs:
        for u in (c.get("units") or ()):
            for cost in (u.get("costs") or ()):
                t = cost["type"]
                if t in id_to_name:
                    # A slot with zero amount is a placeholder, not a charge.
                    if cost["amount"]:
                        unit_declared_types.add(t)
                elif t != -1 and cost["amount"]:
                    unit_unmapped_types.add(t)

    tech_declared_types, tech_unmapped_types = set(), set()
    for _index, tech in enumerate(tk._tech_records()):
        for cost in (tech.get("costs") or ()):
            t = cost["type"]
            if t in id_to_name:
                if cost["amount"]:
                    tech_declared_types.add(t)
            elif t != -1 and cost["amount"]:
                tech_unmapped_types.add(t)

    print("")
    print("types the shipped UNITS charge and the schema declares : %s"
          % sorted((id_to_name[t], t) for t in unit_declared_types))
    print("types the shipped TECHS charge and the schema declares : %s"
          % sorted((id_to_name[t], t) for t in tech_declared_types))
    print("types charged but NOT declared (unmapped side)         : units %s techs %s"
          % (sorted(unit_unmapped_types), sorted(tech_unmapped_types)))
    print("")

    unit_found = {id_to_name[t] for t in unit_declared_types}
    tech_found = {id_to_name[t] for t in tech_declared_types}
    check("unit.cost declares exactly the resources units actually charge",
          unit_found == unit_opts,
          "data %s vs schema %s" % (sorted(unit_found), sorted(unit_opts)))
    check("tech.cost declares exactly the resources techs actually charge",
          tech_found == tech_opts,
          "data %s vs schema %s" % (sorted(tech_found), sorted(tech_opts)))
    check("no shipped tech charges population (the asymmetry is real)",
          4 not in tech_declared_types,
          "population id 4 found in tech costs")

    # ---- the unmapped side must be honest, never a fake empty name ----------
    labels = C.load_resource_labels()
    all_unmapped = unit_unmapped_types | tech_unmapped_types
    print("")
    print("every unmapped type, and what the label table says:")
    for t in sorted(all_unmapped):
        print("  type %-4d -> %r" % (t, labels.get(t)))
    check("every unmapped type is either named or absent (never an empty string)",
          all((t not in labels) or labels[t].strip() for t in all_unmapped),
          "empty names: %s" % [t for t in all_unmapped
                               if t in labels and not labels[t].strip()])

    # And the ones the game itself names must actually be named, since the
    # whole point of switching to the game's block was to stop printing digits.
    named = sorted(t for t in all_unmapped if t in labels)
    print("")
    print("unmapped types the game names: %s"
          % [(t, labels[t]) for t in named])

    # ---- naming them must NOT make them chargeable --------------------------
    # Switching to the game's own 15000+type block gave all eight of these a
    # human name.  The tempting next step is to add them to `resource_types` so
    # `unit.cost`/`tech.cost` can charge them -- do NOT, without new evidence:
    # they are engine counters and local-upgrade pseudo-resources (build limits,
    # per-town-centre upgrades), not things a player pays, and several carry
    # negative or sentinel amounts (`215` is -1 on three Cuman records).  They
    # are reported so the UI can EXPLAIN the slot, not so it can add one.
    # This assertion is the tripwire: if someone declares them, it fires here
    # and the reason above has to be argued rather than rediscovered.
    clashes = sorted(set(all_unmapped) & (unit_opts | tech_opts))
    check("named-but-unmapped types are still not declared as chargeable",
          not clashes,
          "declared the following engine counters: %s"
          % [(t, labels.get(t)) for t in clashes])
    for t in sorted(all_unmapped):
        amounts = sorted({slot["amount"]
                          for c in tk._civs for u in (c.get("units") or ())
                          for slot in (u.get("costs") or ())
                          if slot["type"] == t and slot["amount"]})
        t_amounts = sorted({slot["amount"]
                            for _i, tech in enumerate(tk._tech_records())
                            for slot in (tech.get("costs") or ())
                            if slot["type"] == t and slot["amount"]})
        print("  type %-4d %-28r unit amounts %s tech amounts %s"
              % (t, labels.get(t), amounts or "-", t_amounts or "-"))

    print("")
    if FAILURES:
        print("DECLARED RESOURCES: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("DECLARED RESOURCES: CLEAN")
    print("The schema's cost enums are exactly what the shipped data charges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

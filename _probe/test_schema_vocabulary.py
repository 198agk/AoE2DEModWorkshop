# -*- coding: utf-8 -*-
"""Audit the locked architecture rule "format description lives in external
schema files, never in code".

The claim is easy to assert and easy to erode: a table gets hardcoded for a good
reason ("the arithmetic is opaque", "a typo would silently drop a family"), and
then the game patch it describes changes and nothing fails.  So this file does
not ask "is the table in JSON?" -- it asks the questions that actually matter,
for every hardcoded vocabulary in the product:

  COVERAGE   every entry the DATA FILE declares is matched by the code's table
             (otherwise a field exists that no code path can ever reach)
  PRECISION  every entry in the code's table matches the data file
             (otherwise it is a typo that can never fire)

Both failures survive every existing test, because existing tests exercise the
paths that DO work: a missing entry makes a field silently unreachable, an extra
entry makes a typo silently inert.

Third, and the point of the "code-only facts" section: this file NAMES the format
facts that live only in code and cannot be derived from any schema file, so the
set is visible and countable instead of invisible.  A code-only fact is not
automatically a defect (some are arithmetic the generator cannot express), but an
UNCOUNTED one is how the rule erodes.

Writes nothing.  Exit code 0 if every vocabulary is exactly consistent.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.game import locations as G                        # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.mod import emitter as E                           # noqa: E402

SCHEMA = os.path.join(ROOT, "aoe2mod", "schema")
PROFILE = os.path.join(os.path.expanduser("~"), "Games", "Age of Empires 2 DE")
FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)


def load(name):
    with open(os.path.join(SCHEMA, name), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    types = load("effect_command_types.json")["types"]
    attrs = load("effect_attributes.json")["attributes"]

    # Labels are PREFIXED ("Team Attribute Modifier (Set)", "Gaia Resource
    # Modifier (Multiply)"), so a startswith() match silently ignores four of
    # the five scopes -- which is exactly how the first version of this probe
    # reported 15 of 21 ids as "extra".
    def rows_containing(word):
        return {int(k) for k, v in types.items() if word in (v.get("label") or "")}

    print("A  attribute-modifier family: code table vs the shape file")
    want_attr = rows_containing("Attribute Modifier")
    have_attr = set(C._EFFECT_OPERATION)
    check(have_attr == want_attr,
          "the code's %d attribute-modifier ids are exactly the file's "
          "Attribute Modifier rows" % len(have_attr),
          "missing %s / extra %s" % (sorted(want_attr - have_attr),
                                     sorted(have_attr - want_attr)))
    # the operation word is the parenthesised part of the label
    want_op = {}
    for k in want_attr:
        lab = types[str(k)]["label"]
        want_op[k] = {"Set": "set", "+/-": "add", "Multiply": "multiply"}[
            lab[lab.rfind("(") + 1:lab.rfind(")")]]
    wrong = sorted(k for k in want_attr if C._EFFECT_OPERATION[k][0] != want_op[k])
    check(not wrong, "and the operation word agrees for every id",
          [(k, C._EFFECT_OPERATION[k][0], want_op[k]) for k in wrong])
    check(len(have_attr) == 21, "_EFFECT_OPERATION is still the documented 21 ids",
          len(have_attr))
    check(all(v[1] == "" for k, v in C._EFFECT_OPERATION.items() if k < 10),
          "the five unscoped ids carry no scope word")

    print()
    print("B  the scoped ids keep the arithmetic the docstring documents")
    SCOPE_WORDS = ("", "team", "enemy", "neutral", "gaia")
    bad = []
    for k, (_op, scope) in C._EFFECT_OPERATION.items():
        if k >= 200:
            continue
        if scope != SCOPE_WORDS[(k // 10) % 5]:
            bad.append((k, scope))
    check(not bad, "every non-2xx id's scope matches (id // 10) % 5", bad)
    check(all(k >= 200 for k, (_o, s) in C._EFFECT_OPERATION.items()
              if s in ("own_master", "selected")),
          "and the two special scopes only appear on the 2xx ids")
    check(sorted(k for k in C._EFFECT_OPERATION if k >= 200) ==
          [200, 201, 202, 203, 204, 205],
          "and the 2xx block is complete (two scopes x three operations)",
          sorted(k for k in C._EFFECT_OPERATION if k >= 200))

    print()
    print("C  resource-modifier family: three code tables vs the shape file")
    want_res = rows_containing("Resource Modifier")
    have_res = set(C._RESOURCE_SCOPE)
    check(have_res == want_res,
          "the code's resource-modifier ids are exactly the file's "
          "Resource Modifier rows",
          "missing %s / extra %s" % (sorted(want_res - have_res),
                                     sorted(have_res - want_res)))
    check(set(C._RESOURCE_CHANGE) | set(C._RESOURCE_MULTIPLY) == have_res,
          "and CHANGE + MULTIPLY partition that set exactly",
          sorted(set(C._RESOURCE_CHANGE) | set(C._RESOURCE_MULTIPLY)))
    check(not (set(C._RESOURCE_CHANGE) & set(C._RESOURCE_MULTIPLY)),
          "with no id in both halves")
    slot_ok, slot_bad = True, []
    for k in sorted(have_res):
        p = " ".join(types[str(k)].get("params") or [])
        change_row = "B:0=set" in p
        if change_row != (k in C._RESOURCE_CHANGE):
            slot_ok, _ = False, slot_bad.append((k, p))
    check(slot_ok, "and the file's own slot-B note agrees with which half each "
                   "id is in", slot_bad)
    # the scope words in _RESOURCE_SCOPE must follow the same arithmetic
    bad = [(k, s) for k, s in C._RESOURCE_SCOPE.items()
           if s != SCOPE_WORDS[(k // 10) % 5]]
    check(not bad, "and every resource scope word matches the same arithmetic", bad)

    print()
    print("D  the packed attributes are real ids (the packing itself is code-only)")
    check(tuple(sorted(C._PACKED_ATTRIBUTES)) == (8, 9),
          "_PACKED_ATTRIBUTES is still (8, 9)", list(C._PACKED_ATTRIBUTES))
    check(all(str(i) in attrs for i in C._PACKED_ATTRIBUTES),
          "and both are ids the schema names",
          {i: attrs.get(str(i)) for i in C._PACKED_ATTRIBUTES})
    # Does the file state anything about packing?  It does NOT -- attribute
    # entries are plain strings.  Record that as a code-only fact below rather
    # than inventing a source for it.
    print("      (schema says nothing about packing: attribute entries are "
          "plain strings, e.g. 8 = %r)" % attrs["8"])

    print()
    print("E  operation vocabulary covers every operation the tables can produce")
    ops = {o for o, _s in C._EFFECT_OPERATION.values()}
    check(ops == {"set", "add", "multiply"},
          "the tables produce exactly the three operations", sorted(ops))
    check(ops <= set(C._OPERATION_ZH),
          "and every one has a Chinese word (a sentence must not print the "
          "raw op key)", sorted(ops - set(C._OPERATION_ZH)))
    check(set(C._OPERATION_ZH) == ops,
          "and the wording table has no key the tables cannot produce",
          sorted(set(C._OPERATION_ZH) - ops))
    check(set(C._RESOURCE_CHANGE) | set(C._RESOURCE_MULTIPLY) <=
          set(types.keys()) | set(have_res),
          "every resource modifier type is a real command type")

    print()
    print("F  info.json vocabulary vs every real mod on this machine")
    real_keys = set()
    seen_files = 0
    # `path` IS the mod directory already (it ends with the folder that `name`
    # repeats); joining name onto it finds nothing.  An earlier version of this
    # probe believed `path` was the *containing* directory because it printed
    # `str(v)[:70]` and the truncation cut the folder off.
    for m in A.open_toolkit().mods():
        p = os.path.join(m.get("path") or "", "info.json")
        if os.path.isfile(p):
            seen_files += 1
            try:
                with open(p, encoding="utf-8") as fh:
                    real_keys.update(json.loads(fh.read(), strict=False).keys())
            except Exception as exc:
                print("      (unreadable info.json: %s: %s)" % (p, exc))
    check(seen_files > 0, "found real info.json files to compare against",
          "%d files, keys %s" % (seen_files, sorted(real_keys)))
    check(real_keys <= set(E.INFO_REQUIRED) | set(E.INFO_OPTIONAL),
          "every key real mods use is declared (required or optional)",
          sorted(real_keys - set(E.INFO_REQUIRED) - set(E.INFO_OPTIONAL)))
    check(set(E.INFO_REQUIRED) <= real_keys,
          "and every key we require has been seen in the wild",
          sorted(set(E.INFO_REQUIRED) - real_keys))

    print()
    print("G  mod-status vocabulary vs the real file the engine rewrites")
    found = None
    for root, _d, files in os.walk(PROFILE):
        if "mod-status.json" in files:
            found = os.path.join(root, "mod-status.json")
            break
    check(found is not None, "found the engine's mod-status.json", str(found))
    if found:
        with open(found, encoding="utf-8") as fh:
            doc = json.load(fh)
        seen = set()
        for e in doc.get("Mods") or []:
            seen.update(e.keys())
        check(seen <= set(G.MOD_ENTRY_KEYS),
              "every key the engine writes is declared in MOD_ENTRY_KEYS",
              sorted(seen - set(G.MOD_ENTRY_KEYS)))
        check(set(G.MOD_ENTRY_KEYS) <= seen,
              "and every declared key is one the engine actually writes",
              sorted(set(G.MOD_ENTRY_KEYS) - seen))
        check(set(doc) <= {"Mods", "Unsub"},
              "and the file's top-level keys are the two we know", sorted(doc))

    print()
    print("H  civ-tech-tree vocabulary vs the shipped files")
    trees = CT.load_trees(A.open_toolkit().game_root)
    statuses, use_types, status_by_use = set(), set(), collections.defaultdict(set)
    for tree in trees.values():
        for row in CT.rows_of(tree):
            statuses.add(row.get("Node Status"))
            use_types.add(row.get("Use Type"))
            status_by_use[row.get("Use Type")].add(row.get("Node Status"))
    check(statuses <= set(CT.STATUSES),
          "every Node Status in the shipped files is one of the three declared",
          sorted(s for s in statuses - set(CT.STATUSES) if s))
    check(set(CT.STATUSES) <= statuses,
          "and all three declared words actually occur",
          sorted(set(CT.STATUSES) - statuses))
    check(use_types <= {"Unit", "Tech", "Building"},
          "every Use Type in the shipped files is one the tool knows",
          sorted(use_types - {"Unit", "Tech", "Building"}))
    check(CT.UNIT_USE_TYPES[0] == "Unit" and CT.TECH_USE_TYPES[0] == "Tech",
          "and the two id-space constants name real use types")
    print("      statuses by use type: %s"
          % {k: sorted(v, key=str) for k, v in sorted(status_by_use.items(), key=str)})

    print()
    print("J  the civ-name bridge: hardcoded map vs what the data files say")
    # CIV_FILE_OVERRIDES was a measurement ("upper() works except for these
    # six").  It does not have to stay a hand-kept list: civilizations.json is
    # ordered exactly like the .dat civ array, so the bridge can be READ OUT and
    # compared.  This turns the biggest code-only fact into a checked one.
    cj = os.path.join(A.open_toolkit().game_root, "resources", "_common", "dat",
                      "civilizations.json")
    with open(cj, encoding="utf-8") as fh:
        entries = json.load(fh)["civilization_list"]
    tk = A.open_toolkit()
    tk._ensure()
    dat_names = [c.get("name") for c in tk._civs]
    check(len(entries) == len(dat_names),
          "civilizations.json has one entry per .dat civ, in the same order",
          "%d vs %d" % (len(entries), len(dat_names)))
    stems = set(CT.load_trees(tk.game_root))
    by_pos = {}
    bad = []
    for name, e in zip(dat_names, entries):
        stem = (e.get("tech_tree_name") or "").upper()
        if name == "Gaia":
            continue
        if stem not in stems:
            bad.append((name, e.get("tech_tree_name")))
        else:
            by_pos[name] = stem
    check(not bad, "and every entry names a real tree file (positionally)",
          bad)
    # The map in code must equal the map the data implies.
    implied = {n: s for n, s in by_pos.items() if s != (n or "").upper()}
    check(implied == dict(CT.CIV_FILE_OVERRIDES),
          "CIV_FILE_OVERRIDES is exactly the set the data says differs from "
          "upper()", "code %s / data %s" % (dict(CT.CIV_FILE_OVERRIDES), implied))
    check(len(CT.CIV_FILE_OVERRIDES) == 6,
          "and it is still the documented six entries",
          len(CT.CIV_FILE_OVERRIDES))
    # A negative control: the positional join must be able to FAIL, i.e. the
    # upper() fallback genuinely does not cover the whole set.
    plain = sum(1 for n in by_pos if by_pos[n] == (n or "").upper())
    check(plain < len(by_pos),
          "the upper() fallback really is incomplete (so the map is load-bearing)",
          "%d of %d need no override" % (plain, len(by_pos)))
    print("      overrides the data implies: %s"
          % {k: v for k, v in sorted(implied.items())})

    print()
    print("I  CODE-ONLY FORMAT FACTS (named, so the set stays countable)")
    code_only = [
        ("_EFFECT_OPERATION's 21 ids", "the 10*i+base scope arithmetic is "
         "documented in the docstring, not derivable from the file's rows"),
        ("_PACKED_ATTRIBUTES = (8, 9)", "that slot D of these two is a packed "
         "<high><low> pair comes from AGE's Tester(), not from any schema file"),
        ("_SCHEMA_CACHE / _TABLE_CACHE / _CACHE", "in-process caches"),
        ("CIV_FILE_OVERRIDES (6 entries)", "6 dat civ names do not title-case "
         "into their file stem (Hindustanis -> INDIANS, Magyars -> MAGYAR)"),
        ("UNIT_USE_TYPES / TECH_USE_TYPES", "the two id-space tags"),
    ]
    for name, why in code_only:
        print("      * %-38s %s" % (name, why))
    print("      -> %d facts.  Each is either arithmetic a generator cannot "
          "express or a measurement, not a whole vocabulary left in code."
          % len(code_only))

    print()
    if FAILS:
        print("SCHEMA/VOCABULARY AUDIT: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("SCHEMA/VOCABULARY AUDIT: every hardcoded vocabulary is exactly the "
          "set its data file declares -- no field unreachable, no typo inert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

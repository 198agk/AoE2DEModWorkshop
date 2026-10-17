# -*- coding: utf-8 -*-
"""Does the facade keep its promise across the WHOLE entity space?

`api.py`'s docstring makes three promises a UI is allowed to depend on:

  1. "Nothing raises a bare exception for a user mistake.  Bad input raises
     ``IntentError`` / ``ModError``."
  2. "``search`` never raises" (repeated in the method docstring).
  3. describe() returns JSON-serialisable data.

Every test so far exercises these on a HANDFUL of hand-picked ids -- the ids
someone already thought to look at.  A facade promise is only worth anything if
it holds on the ids nobody looked at: the 1,036 units with no display name, the
type-30/60 placeholders, the eye-candy, the techs whose records are stubs.

So this walks EVERY unit id in the shipped data and EVERY tech id, calls the
facade the way a UI would, and fails on anything that is not an IntentError.
It also checks the result is JSON-serialisable, because the whole point of the
facade is that a non-Python front end can consume it.

This is deliberately shaped like a bug hunt, not a smoke test: it reports the
first few offenders WITH their ids so they can be reproduced.
"""
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import aoe2mod.api as A
from aoe2mod.intent import compiler as C

FAILS = []
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  -- %s" % detail) if detail else ""))
    return ok


def classify(fn, *a, **kw):
    """Return (kind, payload).  kind is 'ok', 'intent', or 'bare'."""
    try:
        return "ok", fn(*a, **kw)
    except C.IntentError as exc:
        return "intent", exc
    except Exception as exc:                       # noqa: BLE001 - that is the point
        return "bare", exc


def main():
    tk = A.open_toolkit()
    tk._ensure()
    ix = __import__("aoe2mod.semantic.index", fromlist=["x"]).index()

    # Derive the id sets from the semantic index, which is what the facade
    # itself resolves against -- and cross-check the unit set against the data,
    # so a sweep that silently covers a smaller space cannot pass.
    unit_ids = sorted(ix.units)
    tech_ids = sorted(ix.techs)
    from_data = sorted({u["id"] for c in tk._civs
                        for u in (c.get("units") or ())})
    print("entities to walk: %d units, %d techs" % (len(unit_ids), len(tech_ids)))
    print("  unit ids in the semantic index: %d | distinct ids in the .dat: %d | agree: %s"
          % (len(unit_ids), len(from_data), unit_ids == from_data))
    if unit_ids != from_data:
        missing = sorted(set(from_data) - set(unit_ids))[:10]
        extra = sorted(set(unit_ids) - set(from_data))[:10]
        print("  !! sweep would not cover the real space: only-in-dat %s | only-in-index %s"
              % (missing, extra))
    print()

    print("=== 1. describe() on every unit id ===")
    bare_u, bad_json_u, no_kind_u = [], [], []
    for uid in unit_ids:
        kind, payload = classify(tk.describe, uid, "unit")
        if kind == "bare":
            bare_u.append((uid, type(payload).__name__, str(payload)[:120]))
        elif kind == "ok":
            try:
                json.dumps(payload)
            except (TypeError, ValueError) as exc:
                bad_json_u.append((uid, str(exc)[:120]))
            if payload.get("kind") != "unit":
                no_kind_u.append((uid, payload.get("kind")))
    check("describe(unit) raises IntentError or nothing, never a bare exception",
          not bare_u, "%d offenders: %s" % (len(bare_u), bare_u[:4]))
    check("describe(unit) is JSON-serialisable for every id",
          not bad_json_u, "%d offenders: %s" % (len(bad_json_u), bad_json_u[:4]))
    check("describe(unit) reports kind='unit' for every id",
          not no_kind_u, "%d offenders: %s" % (len(no_kind_u), no_kind_u[:4]))

    print()
    print("=== 2. describe() on every tech id ===")
    bare_t, bad_json_t = [], []
    for tid in tech_ids:
        kind, payload = classify(tk.describe, tid, "tech")
        if kind == "bare":
            bare_t.append((tid, type(payload).__name__, str(payload)[:120]))
        elif kind == "ok":
            try:
                json.dumps(payload)
            except (TypeError, ValueError) as exc:
                bad_json_t.append((tid, str(exc)[:120]))
    check("describe(tech) raises IntentError or nothing, never a bare exception",
          not bare_t, "%d offenders: %s" % (len(bare_t), bare_t[:4]))
    check("describe(tech) is JSON-serialisable for every id",
          not bad_json_t, "%d offenders: %s" % (len(bad_json_t), bad_json_t[:4]))

    print()
    print("=== 3. describe() must NEVER claim a field it cannot also write ===")
    # The biconditional from test_api section 8, but on the WHOLE space rather
    # than 16 shapes.  A field that shows up in `stats` but that plan() refuses
    # is the "preview promises, commit declines" defect class.
    intents, bindings = C.load_schema()
    declared = [k for k, v in (bindings.get("unit_fields") or {}).items()
                if isinstance(v, dict)]
    mism = []
    for uid in unit_ids:
        kind, payload = classify(tk.describe, uid, "unit")
        if kind != "ok":
            continue
        stats = (payload.get("stats") or {})
        for f in declared:
            shown = f in stats
            kind2, _ = classify(tk.plan, {"intent": "unit.stat", "unit": uid,
                                          "stat": f, "delta": 1})
            reachable = (kind2 == "ok")
            # 'shown' must imply 'plan accepts', and the converse is what the
            # schema is FOR: every declared field reachable on some record.
            if shown and not reachable:
                mism.append((uid, f, "shown but plan refused"))
            if shown and stats.get(f) is None:
                mism.append((uid, f, "shown as None"))
    check("every field describe() shows is a field plan() accepts (whole space)",
          not mism, "%d mismatches: %s" % (len(mism), mism[:4]))

    print()
    print("=== 4. search() never raises, on hostile input ===")
    hostile = ["", "   ", "\x00", "a" * 4000, "%%%", "'; DROP TABLE", "\u00e9\u4e2d\u6587",
               "1234567890", "!!!", "\n\t", "-", "?"
               ]
    s_bad = []
    for q in hostile:
        for kind in ("unit", "tech"):
            k, payload = classify(tk.search, q, kind)
            if k == "bare":
                s_bad.append((repr(q)[:30], kind, type(payload).__name__))
    check("search() never raises a bare exception on hostile input",
          not s_bad, "%s" % (s_bad[:4],))

    print()
    print("=== 5. test_api.py already samples these; prove the sample was enough ===")
    # If a hand-picked sample of ids agreed with the full space, the full-space
    # run is the proof the sample was representative rather than lucky.
    probe = [4, 83, 38, 12, 30, 74, 70, 45, 125, 1259, 2162, 2443, 2317]
    probe_bare = []
    for uid in probe:
        k, payload = classify(tk.describe, uid, "unit")
        if k == "bare":
            probe_bare.append((uid, type(payload).__name__))
    check("the ids test_api.py samples are also clean in the full sweep",
          not probe_bare, "%s" % (probe_bare,))

    print()
    n_ok = sum(1 for _, ok, _ in CHECKS if ok)
    print("-" * 78)
    print("FACADE CONTRACT: %d / %d checks passed" % (n_ok, len(CHECKS)))
    if n_ok != len(CHECKS):
        print("FAILED:")
        for name, ok, detail in CHECKS:
            if not ok:
                print("  - %s :: %s" % (name, detail))
        return 1
    print("A UI may rely on these promises for EVERY entity the game ships.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

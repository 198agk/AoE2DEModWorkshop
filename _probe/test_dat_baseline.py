# -*- coding: utf-8 -*-
"""Assert the current `.dat` implementation still matches the frozen baseline.

This is the contract any replacement has to meet.  Run it:
  * before touching `aoe2mod/dat/` (does the tree still agree with the record?)
  * after a rewrite, pointed at the new implementation's output.

It deliberately checks facts a rewrite CANNOT accidentally match by being
"close": byte counts, sha256 of the whole serialized stream, one hash over the
entire parsed structure, and the full ID sequence of three record families.

Exit 0 = agrees.  Anything else = a number moved and the JSON says which.
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402
import aoe2mod.dat.writer as W          # noqa: E402

BASELINE = os.path.join(ROOT, "_golden", "dat_baseline.json")
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

FAILS = []


def check(name, got, want):
    ok = got == want
    if not ok:
        FAILS.append((name, got, want))
    print("%-34s %s" % (name, "ok" if ok else "FAIL got=%r want=%r" % (got, want)))
    return ok


def sha(b):
    return hashlib.sha256(b).hexdigest()


def struct_hash(obj):
    return sha(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          default=str).encode("utf-8"))


def main():
    if not os.path.isfile(BASELINE):
        print("REFUSING: no baseline at %s" % BASELINE)
        print("          run _probe/make_dat_golden.py first")
        return 1
    base = json.loads(io.open(BASELINE, encoding="utf-8").read())

    dat_path = os.path.join(GAME, DAT_REL)
    raw, how = P.load_dat(dat_path)

    check("raw byte count", len(raw), base["raw_bytes"])
    check("raw sha256", sha(raw), base["raw_sha256"])

    q = P.Parser(raw)
    st = q.parse()
    check("parse reached EOF", q.r.pos == len(raw), True)
    check("parsed position", q.r.pos, base["parsed_pos"])

    for key, want in sorted(base["counts"].items()):
        got = len(st.get(key) or [])
        check("count %s" % key, got, want)

    print()
    civs = st.get("civs") or []
    check("civ count", len(civs), len(base["civ_names"]))
    check("civ names", [c.get("name") for c in civs], base["civ_names"])

    # Units live per civilization, NOT at the top level.  The first version of
    # this checker compared st["units"], which is None, so it reported
    # "ok (0)" while testing nothing -- measured 2026-10-27.
    got_units = [u.get("id") for u in (civs[0].get("units") or [])]
    want_units = base["id_sequences"]["units_gaia"]
    same = got_units == want_units
    if not same:
        first = next((i for i, (a, b) in enumerate(zip(got_units, want_units))
                      if a != b), min(len(got_units), len(want_units)))
        FAILS.append(("units_gaia ids", "differs at %d" % first, "identical"))
    print("%-34s %s" % ("units_gaia id sequence",
                        "ok (%d)" % len(got_units) if same
                        else "FAIL len=%d want=%d" % (len(got_units), len(want_units))))
    check("units_gaia is non-empty", len(got_units) > 0, True)

    for key in ("techs", "graphics"):
        got = [r.get("id") for r in (st.get(key) or [])]
        want = base["id_sequences"][key]
        same = got == want
        if not same:
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b),
                         min(len(got), len(want)))
            FAILS.append(("%s ids" % key, "differs at %d" % first,
                          "identical"))
        print("%-34s %s" % ("%s id sequence" % key,
                            "ok (%d)" % len(got) if same else "FAIL"))

    # Field-level divergence inside unit records, which an ID list cannot see.
    check("gaia units sha256",
          struct_hash(civs[0].get("units") or []), base["gaia_units_sha256"])
    check("britons units sha256",
          struct_hash(civs[1].get("units") or []), base["britons_units_sha256"])
    check("unit counts per civ",
          [{"civ": c.get("name"),
            "units": len(c.get("units") or []),
            "pointers_nonzero": c.get("unit_pointers_nonzero"),
            "pointers_total": c.get("unit_pointers_total")} for c in civs],
          base["unit_counts"])

    print()
    print("hashing the whole structure (slow) ...")
    check("structure sha256", struct_hash(st), base["structure_sha256"])

    print()
    out, _wrep = W.serialize_dat(st, raw=raw, gv=q.gv if hasattr(q, "gv") else None)
    check("serialized byte count", len(out), base["serialized_bytes"])
    check("serialized sha256", sha(out), base["serialized_sha256"])
    check("roundtrip identical", out == raw, True)

    print()
    if FAILS:
        print("BASELINE: %d CHECK(S) FAILED" % len(FAILS))
        for name, got, want in FAILS:
            print("   %s: got %r want %r" % (name, got, want))
        return 1
    print("DAT BASELINE: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Freeze the Python `.dat` implementation's observable behaviour into JSON.

Why this file exists
--------------------
`aoe2mod/dat/` is 4,146 lines that took three weeks and a great many expensive
mistakes to get right (variable-width fields, `count` being a geometry field,
`displayed_*` being a different value from the stored one).  Any second
implementation -- Rust, C++, anything -- has to agree with it BYTE FOR BYTE, and
"it looks the same in game" is not agreement: the game silently does nothing
when a byte is wrong, and it refuses to launch when a checksum is wrong.

So this probe records, for the shipped `.dat`, a fixed set of facts that a
replacement must reproduce exactly:

  1. size, version, section byte ranges, per-section record counts
  2. the identity + a few fields of every unit / tech / graphic record, at
     a deterministic sample (all of them would be 20k JSON entries, and the
     sample plus a full-record hash gives the same guarantee cheaper)
  3. a hash of the FULL parsed structure, so a subtle difference anywhere
     changes one number instead of hiding
  4. a round-trip: parse -> serialize -> compare bytes, and the sha256 of
     both, which is the single strongest statement available

The output goes to `_golden/dat_baseline.json` and is meant to be committed:
it is the contract a rewrite is measured against.

Run with the dsh python (the one with the repo installed):
    py -X utf8 _probe/make_dat_golden.py
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

OUT = os.path.join(ROOT, "_golden")
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def struct_hash(obj):
    """A hash that is stable across dict ordering.

    `json.dumps(sort_keys=True)` on the parsed structure is 90+ MB of text and
    takes a while, but it is the only way to compare "everything" with one
    number, and it runs once, offline.
    """
    return sha(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          default=str).encode("utf-8"))


def main():
    dat_path = os.path.join(GAME, DAT_REL)
    print("dat:", dat_path)
    raw, how = P.load_dat(dat_path)
    print("load_dat ->", how, len(raw), "bytes")

    rep = {"file": os.path.basename(dat_path),
           "raw_bytes": len(raw),
           "raw_sha256": sha(raw),
           "how": how}

    # ---- 1. parse and record the shape ------------------------------------
    q = P.Parser(raw)
    st = q.parse()
    rep["parsed_pos"] = q.r.pos
    rep["eof_clean"] = (q.r.pos == len(raw))
    rep["sections"] = sorted(st.keys())
    rep["counts"] = {}
    for k, v in st.items():
        if isinstance(v, list):
            rep["counts"][k] = len(v)

    # ---- 2. the identity of every record, cheaply -------------------------
    # A rewrite must produce the same IDs in the same order; that alone catches
    # almost every parser divergence and costs one line per record.
    def ids(key):
        out = []
        for rec in st.get(key) or []:
            out.append(rec.get("id"))
        return out

    # `units` is NOT a top-level key: this parser keeps them per civilization,
    # at civs[i]["units"] (2,693 records, described by unit_pointers_*).  The
    # first version of this file recorded st["units"], which does not exist, so
    # the check passed while enumerating nothing.  Measured 2026-10-27.
    civs = st.get("civs") or []
    rep["civ_names"] = [c.get("name") for c in civs]
    rep["id_sequences"] = {
        "units_gaia": [u.get("id") for u in (civs[0].get("units") or [])],
        "techs": ids("techs"),
        "graphics": ids("graphics"),
    }
    rep["unit_counts"] = [
        {"civ": c.get("name"),
         "units": len(c.get("units") or []),
         "pointers_nonzero": c.get("unit_pointers_nonzero"),
         "pointers_total": c.get("unit_pointers_total")}
        for c in civs
    ]
    # One hash over every unit record of Gaia: catches a field-level divergence
    # that an ID list cannot, without writing 2,693 records into the JSON.
    rep["gaia_units_sha256"] = sha(json.dumps(
        civs[0].get("units") or [], sort_keys=True, ensure_ascii=False,
        default=str).encode("utf-8"))
    # And the same for one ordinary civ, because a per-civ divergence is the
    # thing this project has been bitten by most.
    rep["britons_units_sha256"] = sha(json.dumps(
        civs[1].get("units") or [], sort_keys=True, ensure_ascii=False,
        default=str).encode("utf-8"))

    # ---- 3. a fixed sample of full records, at both ends and the middle ---
    def sample(key, n=3):
        recs = st.get(key) or []
        if not recs:
            return []
        picks = [0, len(recs) // 2, len(recs) - 1][:n]
        return [recs[i] for i in picks]

    rep["samples"] = {
        "units_gaia": (civs[0].get("units") or [])[:1],
        "techs": sample("techs"),
        "graphics": sample("graphics"),
    }

    # ---- 4. one hash over everything --------------------------------------
    print("hashing the whole structure (this is the slow part) ...")
    rep["structure_sha256"] = struct_hash(st)
    print("  structure", rep["structure_sha256"][:16])

    # ---- 5. round trip ----------------------------------------------------
    print("serializing ...")
    out, wrep = W.serialize_dat(st, raw=raw, gv=q.gv if hasattr(q, "gv") else None)
    rep["serialized_bytes"] = len(out)
    rep["serialized_sha256"] = sha(out)
    rep["roundtrip_identical"] = (out == raw)
    rep["roundtrip_delta"] = len(out) - len(raw)
    print("  %d -> %d bytes, delta %+d, identical=%s"
          % (len(raw), len(out), len(out) - len(raw), out == raw))

    # a second parse of our own output must reach the same length
    q2 = P.Parser(out)
    st2 = q2.parse()
    rep["reparse_pos"] = q2.r.pos
    rep["reparse_clean"] = (q2.r.pos == len(out))
    rep["reparse_structure_sha256"] = struct_hash(st2)
    print("  reparse clean=%s" % rep["reparse_clean"])

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "dat_baseline.json")
    with io.open(dst, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1, default=str)
    print("\nwrote %s (%d bytes)" % (dst, os.path.getsize(dst)))
    print("raw sha256     ", rep["raw_sha256"])
    print("structure      ", rep["structure_sha256"])
    print("roundtrip      ", rep["roundtrip_identical"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

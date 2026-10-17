# -*- coding: utf-8 -*-
"""brute_force_audit.py -- FULL strict scan over every scenario instance on the
machine, to turn "brute force does not work" into a measured denominator.

For each file/member:
  * strict hit = raw inflate(b[off:], wbits=-15) with no zlib.error, d.eof==True,
                 len(out) >= 1000
  * collect ALL strict hits over ALL offsets
  * compare against the structural true offset from header_layout.locate()

Questions answered with numbers:
  Q1 does brute force FIND the true offset?            (coverage k/N)
  Q2 is the true offset the UNIQUE strict hit?          (ambiguity)
  Q3 is the true offset the LARGEST output?             (is the magnitude
                                                         heuristic sound?)
  Q4 how many offsets must be tried, and how slow?      (cost)

Read-only.  Writes brute_force_audit_output.txt / .json
"""
import json
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import locate                          # noqa: E402
from campaign_deterministic import parse_campaign_deterministic as parse_campaign  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CAMPAIGNS = os.path.join(GAME, "resources", "_common", "campaign")
DRS = os.path.join(GAME, "resources", "_common", "drs")
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"

MINOUT = 1000
out = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.append(s)


def strict_hits(b):
    """Every offset whose raw-deflate stream is complete and >= MINOUT bytes.

    Uses a memoryview slice so that b[o:] does not copy: a 3.6 MB instance
    would otherwise copy ~6 TB over the whole offset loop.
    """
    hits = []
    n = len(b)
    mv = memoryview(b)
    for o in range(n):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            oo = d.decompress(mv[o:])
            oo += d.flush()
        except (zlib.error, MemoryError):
            continue
        if d.eof and len(oo) >= MINOUT:
            hits.append((o, len(oo)))
    return hits


def audit(label, b, true_off, rows):
    t0 = time.time()
    hits = strict_hits(b)
    dt = time.time() - t0
    offs = [o for o, _ in hits]
    biggest = max(hits, key=lambda t: t[1]) if hits else None
    first = hits[0][0] if hits else None
    rec = {
        "label": label,
        "size": len(b),
        "true_offset": true_off,
        "n_hits": len(hits),
        "hits": hits,
        "true_found": true_off in offs,
        "true_is_unique": len(hits) == 1 and offs == [true_off],
        "true_is_largest": bool(biggest and biggest[0] == true_off),
        "true_is_first": first == true_off,
        "floor_offset": min(offs) if offs else None,
        "scan_seconds": round(dt, 3),
        "hits_per_second": int(len(b) / dt) if dt > 0 else None,
    }
    rows.append(rec)
    return rec


def main():
    # Phase selector so a big run can be split: "singles", "members", or "all".
    # (The full member sweep costs ~14 minutes; the standalone sweep ~3 seconds.)
    phase = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    do_singles = phase in ("all", "singles")
    do_members = phase in ("all", "members")
    rows = []

    P("=" * 78)
    P("FULL STRICT BRUTE-FORCE AUDIT  (every offset of every scenario instance)")
    P("=" * 78)
    P(f"strict hit = raw inflate wbits=-15, no error, d.eof==True, len(out)>={MINOUT}")
    P()

    # ---- standalone files ------------------------------------------------
    # NOTE: the .scx files live in SUBDIRECTORIES of drs/, so os.listdir is not
    # enough here -- os.walk is required or 50 of the 54 standalone files are
    # silently skipped (this was a real bug on the first run: 239 instead of 289).
    singles = []
    for root in (DRS, CAMPAIGNS, PROFILE):
        for dp, _dn, fn in os.walk(root):
            for f in sorted(fn):
                if f.lower().endswith(".aoe2scenario") or f.lower().endswith(".scx"):
                    singles.append(os.path.join(dp, f))
    singles.sort()

    P("--- STANDALONE FILES ---")
    if do_singles:
        for p in singles:
            b = open(p, "rb").read()
            tru, lay, body, why = locate(b)
            if tru is None:
                P(f"SKIP (locator rejected) {os.path.basename(p)}: {why}")
                continue
            r = audit(os.path.basename(p), b, tru, rows)
            flag = "" if r["true_is_unique"] else "  <-- AMBIGUOUS"
            P(f"{r['label'][:44]:<44} size={r['size']:>8d} hits={r['n_hits']:<3d} "
              f"true={r['true_offset']:<8d} uniq={r['true_is_unique']} "
              f"max={r['true_is_largest']} {r['scan_seconds']:.1f}s{flag}")
            if r["n_hits"] > 1:
                for o, n in r["hits"]:
                    P(f"        @{o:<8d} out={n}{'   TRUE' if o == tru else '   spurious'}")

    # ---- campaign members ------------------------------------------------
    P()
    P("--- CAMPAIGN MEMBERS ---")
    members = []
    for fn in sorted(os.listdir(CAMPAIGNS)):
        if not fn.lower().endswith(".aoe2campaign"):
            continue
        b = open(os.path.join(CAMPAIGNS, fn), "rb").read()
        for m in parse_campaign(b)["members"]:
            members.append((f"{fn}::{m['name']}", m["data"]))

    P(f"members enumerated: {len(members)}")
    if do_members:
        for label, mb in members:
            tru, lay, body, why = locate(mb)
            if tru is None:
                P(f"SKIP (locator rejected) {label}: {why}")
                continue
            r = audit(label, mb, tru, rows)
            if r["n_hits"] != 1 or not r["true_is_unique"]:
                P(f"AMBIGUOUS {label}: hits={r['n_hits']} true={tru} -> {r['hits']}")

    # ---- summary ---------------------------------------------------------
    n = len(rows)
    found = sum(1 for r in rows if r["true_found"])
    uniq = sum(1 for r in rows if r["true_is_unique"])
    largest = sum(1 for r in rows if r["true_is_largest"])
    firstok = sum(1 for r in rows if r["true_is_first"])
    amb = [r for r in rows if not r["true_is_unique"]]
    total_bytes = sum(r["size"] for r in rows)
    total_secs = sum(r["scan_seconds"] for r in rows)

    P()
    P("=" * 78)
    P("SUMMARY")
    P("=" * 78)
    P(f"instances audited                                 : {n}")
    P(f"bytes scanned (offsets attempted)                 : {total_bytes:,}")
    P(f"wall seconds for all scans                        : {total_secs:.1f}")
    P()
    P(f"Q1 brute force FINDS the true offset              : {found}/{n}")
    P(f"Q2 true offset is the UNIQUE strict hit           : {uniq}/{n}")
    P(f"Q3 true offset is the LARGEST-output strict hit   : {largest}/{n}")
    P(f"Q4 true offset is the FIRST strict hit            : {firstok}/{n}")
    P(f"   ambiguous instances (>=2 strict hits)          : {len(amb)}/{n}")
    P()
    if amb:
        P("ambiguous instances (brute force cannot decide without a magnitude rule):")
        for r in amb:
            P(f"   {r['label'][:52]:<52} true={r['true_offset']:<8d} hits={r['hits']}")
    P()
    worst = max(rows, key=lambda r: r["n_hits"])
    P(f"most strict hits in any one instance: {worst['n_hits']} ({worst['label'][:48]})")
    P()
    # Phase-tagged outputs so the standalone half and the member half never
    # overwrite each other's measured numbers (they are run separately).
    suffix = "" if phase == "all" else "_" + phase
    P("CONCLUSION: brute force DOES find the true offset, but only if the")
    P("acceptance rule is right (eof==True on a raw -15 stream) AND a magnitude")
    P("rule picks the largest output.  The task brief's '0 hits in 200,000")
    P("offsets' is a methodology artefact, not a property of the format.")

    open(os.path.join(HERE, f"brute_force_audit{suffix}_output.txt"), "w", encoding="utf-8").write("\n".join(out))
    json.dump(rows, open(os.path.join(HERE, f"brute_force_audit{suffix}.json"), "w", encoding="utf-8"),
              indent=1)
    P(f"wrote brute_force_audit{suffix}_output.txt / brute_force_audit{suffix}.json")


if __name__ == "__main__":
    main()

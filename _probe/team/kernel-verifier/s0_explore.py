# -*- coding: utf-8 -*-
"""Exploration only: what does the product's schema/API actually expose?

Read-only.  Prints intent list, one describe(), one plan(), so the later probes
can be written against the real method names instead of guesses.
"""
import contextlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    t0 = time.time()
    tk = A.open_toolkit(GAME)
    print("toolkit type:", type(tk).__name__)
    print("public verbs:", [n for n in dir(tk) if not n.startswith("_")
                            and callable(getattr(tk, n))][:20])
    sch = tk.schema()
    print("schema keys:", list(sch.keys())[:10])
    print("intents:", list(sch.get("intents", {}).keys()))
    print("loaded in %.1fs" % (time.time() - t0))

    # semantic search contract
    try:
        hits = tk.search("步弓手")
        print("search('步弓手') ->", json.dumps(hits[:3], ensure_ascii=False))
    except Exception as exc:
        print("search raised", type(exc).__name__, exc)

    # units named Archer-ish
    for q in ("Archer", "巡ar", "步弓"):
        try:
            print("search(%r) -> %d hits, first: %s" % (
                q, len(tk.search(q)),
                json.dumps(tk.search(q)[:2], ensure_ascii=False)))
        except Exception as exc:
            print("search(%r) raised %s: %s" % (q, type(exc).__name__, exc))

    d = tk.describe(4)
    print("describe(4) keys:", list(d.keys()))
    print(json.dumps({k: d[k] for k in list(d)[:14]}, ensure_ascii=False)[:1200])

    # the plan under test in claim 2
    intent = {"intent": "unit.stat", "unit": "步弓手",
              "stat": "displayed_attack", "delta": 2}
    t1 = time.time()
    p = tk.plan(intent)
    print("plan took %.1fs" % (time.time() - t1))
    print("plan:")
    print(json.dumps(p, ensure_ascii=False, indent=1)[:2000])

    print("total %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    with contextlib.redirect_stdout(sys.stdout):
        main()

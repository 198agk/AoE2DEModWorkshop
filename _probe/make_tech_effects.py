"""tech id -> how many effect commands that technology carries.

Why this table has to exist at all: the sentence reader is what has to refuse
"织布机效果加5" (three commands, the position is ambiguous) and "第0条效果"
(a position that cannot exist).  But the reader has no .dat and no server -- it
turns text into intents and must keep working with no game installed.  Python
solves the same problem by handing the reader a `effect_count` CALLABLE from the
screen layer (`aoe2mod/ui/server.py:300` passes `self.tk.effect_count`).  Rust's
`read_clause` is a free function with no Server in scope, so the count arrives as
a table instead of a closure.  Same number, different plumbing.

What each entry means: `len(effects[tech.effect_id].commands)`, i.e. exactly what
`aoe2mod/api.py:598 effect_count` returns.  A tech with no effect record (or a
negative effect_id) is 0, which the reader turns into "没有任何效果可以改" rather
than silently editing nothing.

Output: `_golden/tech_effects.json`
    {"gv": 54, "counts": {"22": 3, "0": 0, ...}}

Self-check (fails the export, not the reader): the measured shape of this file is
asserted at the bottom -- 371 technologies with exactly one command and 669 with
two or more, which is the split the loader comment in `nl.py` quotes.
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A  # noqa: E402

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "_golden",
    "tech_effects.json",
)


def main():
    tk = A.open_toolkit(game_root=GAME)
    tk._ensure()
    counts = {}
    for tech in range(len(tk._tech_records())):
        counts[str(tech)] = int(tk.effect_count(tech))

    # The distribution is the check: if the export drifts (wrong effect table,
    # off-by-one in the record walk) these two numbers move, and the reader's
    # "ambiguous, ask which one" branch silently stops firing.
    one = sum(1 for v in counts.values() if v == 1)
    many = sum(1 for v in counts.values() if v >= 2)
    zero = sum(1 for v in counts.values() if v == 0)

    doc = {"gv": 54, "counts": counts}
    payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(payload)
    print("techs %d  exactly-one %d  two-or-more %d  none %d" % (len(counts), one, many, zero))
    print("bytes %d -> %s" % (len(payload.encode("utf-8")), OUT))

    if one != 371 or many != 669:
        sys.exit(
            "the distribution moved (one=%d many=%d, expected 371/669): the reader "
            "would now ask for a position on sentences that have only one, or "
            "silently edit the first of several" % (one, many)
        )
    print("verification ok")


if __name__ == "__main__":
    main()

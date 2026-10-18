# -*- coding: utf-8 -*-
"""Direct proof that BP.verify_surgical's `ok` can never be False.

`ok` is `info["outside_is_untouched"]`, which is computed from p and s that were
FOUND by scanning the two strings for equality -- so it is true by construction.
Feed it two totally unrelated strings and see what it says.
Read-only: imports the product, writes nothing.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)

import aoe2mod.game.buildpanel as BP  # noqa: E402

CASES = [
    ("empty vs empty", "", ""),
    ("a vs b", "a", "b"),
    ("totally different", "AAAA" * 100, "ZZZZ"),
    ("prefix only", "{" * 10, "{" * 10 + "}" * 5),
]

for label, a, b in CASES:
    ok, info = BP.verify_surgical(a, b)
    print("%-22s ok=%-5s outside_is_untouched=%-5s inserted=%d kind=%s"
          % (label, ok, info["outside_is_untouched"], info["inserted"],
             info["kind"]))

# And with inserted_chars supplied, which is the ONLY way to get real signal:
ok, info = BP.verify_surgical("aaaa", "bbbb", inserted_chars=99)
print("%-22s ok=%-5s (inserted_chars=99 supplied; inserted=%d)"
      % ("bogus inserted_chars", ok, info["inserted"]))

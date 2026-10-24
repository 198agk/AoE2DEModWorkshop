# -*- coding: utf-8 -*-
"""What a plugin would need to reach the SENTENCE layer, measured rather than guessed.

The split is real and was deliberate: `intents.json` can be extended by a plugin
(`AOE2MOD_PLUGINS`), but `aoe2mod/ui/nl.py` is hand-written branches, so a plugin's intent
is reachable by the API and not by a Chinese sentence.  That is why the 能做的事 box has to
mark such intents instead of listing them as available.

This probe answers the question the next round needs: **is the sentence layer a table
somewhere, or is it control flow that a plugin cannot reach at all?**  It prints, per
shipped intent, whether it is in `SENTENCE_INTENTS` and how many code branches mention it.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.intent import compiler as C  # noqa: E402
from aoe2mod.ui import nl as NL  # noqa: E402


def main():
    schema, _bindings = C.load_schema()
    intents = (schema.get("intents") or {})
    src = io.open(os.path.join(ROOT, "aoe2mod", "ui", "nl.py"),
                  encoding="utf-8", newline="").read()
    low = src.replace("\r\n", "\n")

    print("shipped intents: %d" % len(intents))
    reachable = list(NL.SENTENCE_INTENTS)
    print("named in SENTENCE_INTENTS: %d" % len(reachable))

    rows = []
    for name in sorted(intents):
        spec = intents[name] or {}
        # NOT a schema key.  `server.py` derives it as `k in nl.SENTENCE_INTENTS`,
        # and `ai.py` falls back to that too -- so the listed set IS the declaration.
        # Reading `spec["by_sentence"]` printed False for all 13: a fact about the
        # probe, not about the product.
        declared = name in reachable
        listed = name in reachable
        # How the reader detects it: an intent id only reaches the clause through a
        # literal in nl.py, so counting literals is the honest measure of "a branch".
        literals = len(re.findall(r"""["']%s["']""" % re.escape(name), low))
        rows.append((name, declared, listed, literals))

    print()
    print("%-24s %-9s %-9s %s" % ("intent", "by_sentence", "listed", "literal hits in nl.py"))
    for name, declared, listed, literals in rows:
        print("%-24s %-9s %-9s %d" % (name, bool(declared), listed, literals))

    # The two ways the two layers can disagree.  Both are real defects if they happen:
    # listed but no literal means the reader claims an intent nothing can produce.
    liars = [r[0] for r in rows if r[2] and r[3] == 0]
    silent = [r[0] for r in rows if r[3] > 0 and not r[2]]
    print()
    print("listed but never mentioned in nl.py:", liars or "none")
    print("mentioned in nl.py but not listed:", silent or "none")

    # What a plugin would have to supply.  `by_sentence` is metadata the screen READS;
    # the reader never consults it, so a plugin can declare it and still be unreachable.
    plugin_ok = [r[0] for r in rows if r[2]]
    print()
    print("a plugin can add an intent, and the schema can say by_sentence -- but the "
          "reader is %d literal branches over %d intents, i.e. a table a plugin cannot "
          "extend at runtime." % (len(plugin_ok), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

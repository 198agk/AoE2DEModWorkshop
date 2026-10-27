# -*- coding: utf-8 -*-
"""Export what the AI grammar needs: reachability + the verified examples.

`ai.grammar` lists only intents a SENTENCE can reach, and separately names the
API-only ones -- because a model told only about ten of thirteen will confidently
write for thirteen. Reproducing that list means knowing `sentence_reachable`,
which lives in the hand-written reader, and the EXAMPLES list, which is the small
set of sentences this project has actually tested.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "_golden", "ai_grammar.json")


def main():
    from aoe2mod.intent import compiler as C
    from aoe2mod.ui import nl
    from aoe2mod import ai

    intents, _bindings = C.load_schema()
    rows = []
    for k, v in intents["intents"].items():
        rows.append({
            "id": k,
            "title": v.get("title") or v.get("title_en") or k,
            "fields": list((v.get("fields") or {})),
            "by_sentence": bool(nl.sentence_reachable(k, v)),
        })
    doc = {"intents": rows, "examples": list(ai.EXAMPLES)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("intents:", len(rows), "| by_sentence:",
          sum(1 for r in rows if r["by_sentence"]))
    print("examples:", len(doc["examples"]))
    print("first example:", doc["examples"][0] if doc["examples"] else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())

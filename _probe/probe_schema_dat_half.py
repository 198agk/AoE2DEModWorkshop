# -*- coding: utf-8 -*-
"""Print the ``dat_half`` declaration of both availability intents, verbatim.

Read-only.  The point is to see the exact wording before changing it: the
`write_operations` field is about to stop being one number per intent, because a
grant writes two things (a new effect, and the tech that points at it) while a
revoke now writes the same two things through a different carrier.  Keeping one
number would force the schema to lie about one of them.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    path = os.path.join(ROOT, "aoe2mod", "schema", "intents.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    for name in ("unit.availability", "tech.availability"):
        comp = doc["intents"][name]["compile"]
        print("=" * 70)
        print(name)
        print("=" * 70)
        print(json.dumps(comp, ensure_ascii=False, indent=2))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

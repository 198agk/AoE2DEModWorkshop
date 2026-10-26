# -*- coding: utf-8 -*-
"""Does the player-facing page agree with the schema, intent for intent?

Two independent artifacts now describe the same thing:

* `aoe2mod/schema/intents.json` -- `compile.verified_in_game` per intent (what a
  running game actually showed, with the date)
* `RELEASE.md` -- two tables, "seen in a running game" and "bytes only"

Nothing forced them to agree before this file existed, and the failure mode is the
expensive one: a page that promises a feature the schema admits was never loaded,
or (worse, and what happened on 2026-10-26) a page that hides a feature the schema
already proves.

The dates are compared too, not just membership -- two artifacts can agree that
`unit.stat` was seen and disagree about when.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  ok   %s" % name)
    else:
        print("FAIL %s :: %s" % (name, detail) if detail else "FAIL %s" % name)
        FAILS.append(name)


DATE = re.compile(r"20\d\d-\d\d-\d\d")
ID = re.compile(r"`((?:unit|tech)\.[a-z_]+)`")


def schema():
    return json.load(io.open(os.path.join(ROOT, "aoe2mod", "schema", "intents.json"),
                             encoding="utf-8"))["intents"]


def table_rows(text, marker):
    """Rows of the first markdown table after `marker`.

    Skips the prose between the heading and the table -- the page has a paragraph
    explaining what the dates mean, and a collector that gives up on the first
    non-row line reports "no table" for a page that has one.  It stops at the
    first blank line *after* the table has started, which is what ends a table.
    """
    i = text.find(marker)
    if i < 0:
        return None
    out = []
    started = False
    for line in text[i:].split("\n")[1:]:
        if line.startswith("|"):
            started = True
            out.append(line)
        elif started:
            break
    return out if started else []


def main():
    rel = os.path.join(ROOT, "RELEASE.md")
    check("RELEASE.md exists", os.path.isfile(rel))
    if not os.path.isfile(rel):
        print("RELEASE: %d CHECKS, %d FAILED" % (CHECKS[0], len(FAILS)))
        return 1

    text = io.open(rel, encoding="utf-8").read()
    intents = schema()

    seen_rows = table_rows(text, "## 二、")
    byte_rows = table_rows(text, "## 三、")
    check("the seen-in-game table is there", bool(seen_rows),
          "no table under 二、")
    check("the bytes-only table is there", bool(byte_rows),
          "no table under 三、")
    if not seen_rows or not byte_rows:
        print("RELEASE: %d CHECKS, %d FAILED" % (CHECKS[0], len(FAILS)))
        return 1

    def ids_and_dates(rows):
        out = {}
        for line in rows:
            ids = ID.findall(line)
            if not ids:
                continue
            d = DATE.search(line)
            for i in ids:
                out[i] = d.group(0) if d else None
        return out

    seen = ids_and_dates(seen_rows)
    byte_only = ids_and_dates(byte_rows)

    # 1. the page covers every intent the schema ships, exactly once
    covered = set(seen) | set(byte_only)
    shipped = set(intents)
    check("every intent the schema ships appears on the page",
          not (shipped - covered), sorted(shipped - covered))
    check("the page invents no intent the schema does not ship",
          not (covered - shipped), sorted(covered - shipped))
    check("no intent is listed as both seen and unseen",
          not (set(seen) & set(byte_only)), sorted(set(seen) & set(byte_only)))

    # 2. membership must match the schema's own `verified_in_game`
    schema_seen = {k for k, v in intents.items()
                   if (v.get("compile") or {}).get("verified_in_game")}
    check("the page's seen list is exactly the schema's verified list",
          set(seen) == schema_seen,
          "page only: %s | schema only: %s" % (sorted(set(seen) - schema_seen),
                                               sorted(schema_seen - set(seen))))

    # 3. and the dates must match, not just the membership
    mismatched = []
    for iid in sorted(set(seen) & schema_seen):
        field = intents[iid]["compile"]["verified_in_game"]
        d = DATE.search(field)
        if not d or d.group(0) != seen[iid]:
            mismatched.append((iid, seen[iid], d.group(0) if d else None))
    check("each date on the page is the date the schema records",
          not mismatched, mismatched)

    # 4. a claim of having been seen must carry its own evidence
    bare = [k for k, v in intents.items()
            if (v.get("compile") or {}).get("verified_in_game")
            and not DATE.search(v["compile"]["verified_in_game"])]
    check("every verified_in_game carries a date", not bare, bare)

    unlabelled = [k for k, v in intents.items()
                  if (v.get("compile") or {}).get("verified_in_game")
                  and not re.search(r"dsh test|build_bundle|install",
                                    v["compile"]["verified_in_game"])]
    check("every verified_in_game names what produced the reading", not unlabelled,
          unlabelled)

    # 5. today's specific regression: the note that a run has since falsified
    create_nvr = (intents["unit.create"]["compile"] or {}).get("not_verified_reason") or ""
    check("unit.create no longer claims the bundle path was never loaded",
          "has not been installed and loaded" not in create_nvr)
    check("and its replacement still answers the icon question",
          "widgetui" in create_nvr and "icon" in create_nvr)

    # 6. the one absence claim that IS still true must survive
    art_nvr = (intents["unit.art"]["compile"] or {}).get("not_verified_reason") or ""
    check("unit.art still says a repainted .sld was never loaded",
          "has not been loaded by a running game" in art_nvr)

    print()
    if FAILS:
        print("RELEASE NOTES: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("RELEASE NOTES: %d CHECKS PASSED -- THE PAGE AND THE SCHEMA AGREE, INTENT "
          "FOR INTENT AND DATE FOR DATE" % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

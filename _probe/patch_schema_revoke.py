# -*- coding: utf-8 -*-
"""Give `unit.availability` a verified `.dat` half for REVOKE, and say how.

What changed and why, in one place:

  * `dat_half.actions` gains ``revoke``.  `dsh test v17` (2026-10-19) is the
    first in-game observation of a civilization LOSING a unit it ships with: the
    Champi Scout button was still there in the Dark Age and gone in the Castle
    Age, because the same disable command was hung on two carriers firing at
    different times.  So `type 2 b=0` gates the build menu and the last command
    to fire wins -- both halves in one experiment.
  * `write_operations` stays the GRANT count it has always been, and
    `write_operations_by_action` states each action's count explicitly, so the
    preview cannot report the grant's 2 for a revoke that writes a different
    number.  The revoke recipe is one effect + one re-pointed tech and no button
    byte, so it is 1 write operation, not 2.
  * `why_not_for_other_actions` is rewritten: it used to say no in-game test had
    shown a revoke working, which is now false.

Section D prints a diff so the change can be reviewed rather than trusted.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "aoe2mod", "schema", "intents.json")

NEW_ACTIONS = ["grant", "revoke"]

NEW_NOTE = (
    "Each action declares its own count above, because the two recipes write "
    "different numbers. GRANT writes two: one new Effect record, then the "
    "re-pointed technology -- plus the training ButtonID byte, which is part of "
    "the same recipe rather than a separate operation. REVOKE writes ONE: one new "
    "Effect record carrying the carrier's commands plus `type 2 b=0`, then the "
    "re-pointed technology. There is no button to move -- the unit simply stops "
    "appearing. The numbers are declared rather than measured because measuring "
    "them serialises the whole 93 MB .dat (25 s) and a preview must stay cheap; "
    "`_probe/test_dat_half_count.py` asserts the declaration still equals "
    "`len(apply_grant(...)[\"edits\"])` and `len(apply_revoke(...)[\"edits\"])`, so "
    "the two cannot drift apart silently."
)

NEW_HELP = (
    "GRANT: appends a NEW effect carrying the anchor technology's own commands "
    "plus 'type 2, unit, 1' and re-points that technology at it, then moves the "
    "unit's training button to a free slot (a byte patch, because the writer's "
    "model does not carry train_locations). REVOKE: appends a NEW effect carrying "
    "the carrier technology's own commands plus 'type 2, unit, 0' and re-points "
    "that technology at it -- no button byte, because the unit has to disappear "
    "rather than move. The carrier for a revoke MUST fire later than whatever "
    "makes the unit available, or the enable overwrites the disable; "
    "`datgrant.pick_revoke_tech` enforces that and refuses when no such carrier "
    "exists. EnablingResearch is deliberately left alone in both directions: the "
    "confirmed grant recipe wrote no such byte, and the field is global per unit "
    "id, so pointing it at one civilization's technology would claim that all 63 "
    "are enabled by it."
)

NEW_WHY_NOT_OTHER = (
    "The technology space has no `.dat` half in either direction: the proven "
    "commands are unit-space ('type 2' names a UNIT id), so pointing one at a tech "
    "node would enable whichever unit happens to share that integer. That is why "
    "tech.availability declares no dat_half at all, while this intent does."
)

NEW_VERIFIED = (
    "GRANT: 2026-10-16, `dsh test v7` -- villagers stayed at 1000 hp, the Castle "
    "Longbowman was unaffected, and the Dark Age Barracks showed the Champi "
    "Scout. REVOKE: 2026-10-19, `dsh test v17` -- the Incas lost the Champi Scout "
    "in the Castle Age (the carrier that fired then) and kept it in the Dark Age "
    "(the carrier that fired first was overwritten). The ordering rule is part of "
    "the result, not a guess: both carriers were byte-verified present in the "
    "shipped .dat, so only the firing time differed between the two readings."
)


def main():
    with open(SCHEMA, encoding="utf-8") as fh:
        doc = json.load(fh)
    dh = doc["intents"]["unit.availability"]["compile"]["dat_half"]

    before = dict(dh)
    dh["actions"] = list(NEW_ACTIONS)
    dh["write_operations_by_action"] = {"grant": 2, "revoke": 1}
    dh["write_operations_note"] = NEW_NOTE
    dh["help"] = NEW_HELP
    dh["why_not_for_other_actions"] = NEW_WHY_NOT_OTHER
    dh["verified_in_game"] = NEW_VERIFIED

    for k in sorted(set(before) | set(dh)):
        if before.get(k) != dh.get(k):
            print("changed %s" % k)
            if k != "write_operations_note":
                print("   was: %r" % (before.get(k),))
                print("   now: %r" % (dh.get(k),))

    with open(SCHEMA, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\nwrote %s" % SCHEMA)
    return 0


if __name__ == "__main__":
    sys.exit(main())

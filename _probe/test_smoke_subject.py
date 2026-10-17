r"""Is the smoke-test subject still a valid subject?

A single-variable in-game test is only worth running if its subject can
actually distinguish the two outcomes.  The 2026-10-14 panel test used
Hand Cannoneer (unit 5) and the archery range did not list it -- but unit 5's
tree row carries ``Age ID: 4`` (Imperial Age), so a game that starts in the
Dark Age could not show it *whichever* file the menu reads.  The test had a
confound and settled nothing, and nothing in the suite noticed.

This pin asserts the properties that make a subject valid, so a game update
that removes them fails loudly instead of quietly making the next test
meaningless:

  1. the subject is AGE-FREE (RequiredAge 1) -- no age gate can hide the result;
  2. the receiver really lacks it (in both the tree and the panel), so a
     successful grant is an observable change;
  3. a donor really has it, so the copy has a source;
  4. the negative control -- the subject that failed -- is still age-gated,
     so this pin keeps explaining WHY it was replaced.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

SUBJECT = 2550          # Champi Scout
RECEIVER = "British"
DONOR = "Incas"
REJECTED = 5            # Hand Cannoneer -- the confounded subject

tk = A.open_toolkit()
trees = tk._trees()
main_path, paphos_path = BP.panel_paths(tk.game_root)
_text, panel = BP.load_panel(main_path)

checks = 0


def _check(cond, msg):
    global checks
    assert cond, msg
    checks += 1


def _tree_row(civ, node_id):
    for r in CT.unit_rows(trees[CT.civ_file_stem(civ)]):
        if r.get("Node ID") == node_id:
            return r
    return None


# --- 1. age-free ------------------------------------------------------------
drow = _tree_row(DONOR, SUBJECT)
_check(drow is not None, "the donor %s has no row for %d" % (DONOR, SUBJECT))
_check(drow["Age ID"] == 1,
       "subject %d is no longer age-free (Age ID=%r); the smoke test would "
       "again be confounded by the age gate" % (SUBJECT, drow["Age ID"]))
_entry = None
for b in BP.buildings(panel, "Incas"):
    for e in b.get("Units", []):
        if e.get("ID") == SUBJECT:
            _entry = e
_check(_entry is not None,
       "the shipped panel no longer lists %d for %s" % (SUBJECT, DONOR))
_check(_entry.get("RequiredAge") == 1,
       "the panel gates subject %d at RequiredAge=%r"
       % (SUBJECT, _entry.get("RequiredAge")))

# --- 2. the receiver lacks it in BOTH layers --------------------------------
_check(_tree_row(RECEIVER, SUBJECT) is None,
       "%s now has a tree row for %d, so a grant is a no-op"
       % (RECEIVER, SUBJECT))
_check(BP.find_entry(panel, "Britons", SUBJECT, BP.UNITS_KEY)[1] is None,
       "the Britons panel already lists %d, so the menu test proves nothing"
       % SUBJECT)

# --- 3. a donor exists (the copy has a source) ------------------------------
_check(_tree_row(DONOR, SUBJECT)["Node Status"] == "ResearchedCompleted",
       "the donor's own row is not ResearchedCompleted")

# --- 4. the replaced subject is still age-gated -----------------------------
_bad = _tree_row(RECEIVER, REJECTED)
_check(_bad is not None and _bad["Age ID"] > 1,
       "the negative control %d is no longer age-gated; this pin's explanation "
       "of why it was replaced no longer holds" % REJECTED)

print("%d checks passed" % checks)
print("SMOKE SUBJECT: unit %d is age-free, absent from %s in both layers, and "
      "donated by %s." % (SUBJECT, RECEIVER, DONOR))
print("The archery-range test's real flaw: unit %d is Age ID %d, so a Dark Age "
      "start could never show it." % (REJECTED, _bad["Age ID"]))

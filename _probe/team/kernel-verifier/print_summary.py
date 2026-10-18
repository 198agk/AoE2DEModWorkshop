# -*- coding: utf-8 -*-
"""Print the 20-line verification summary to stdout."""
L = [
 "1  VERDICT: PARTLY CONFIRMED - round-trip and surgical edits hold to the byte; honesty boundary and no-op contract do not",
 "2  CLAIM 1 CONFIRMED  input 12023754 B -> inflated 93268152 B -> output 93268152 B, sha256 identical, first diff = none",
 "3    parse 6.16 s, serialize 14.24 s, second serialize idempotent; model 6.40 MB + opaque 86.87 MB re-emitted byte-exact",
 "4  CLAIM 2 CONFIRMED  步弓手 displayed_attack +2 -> 126 bytes changed, length delta 0, runs=126 all 1 B wide",
 "5    63 primary/mirror pairs at a constant 78 B gap, one pattern only (u16 4->6 both sides), 63 civ slots 0..62 unique",
 "6    0 violations in the +/-200 B window around every edited offset; 208507 debug-string markers unmoved",
 "7  CLAIM 3 PARTLY     11/13 intents: plan edit_count == build edit_count == my independent byte count",
 "8    2/13 disagree: Loom cost-food and grant-already-held are promised by plan() then refused by build()",
 "9    plan/build description text identical in 8/13; 3 differ in wording only (Loom effect, sprite copy, sprite rename)",
 "10 CLAIM 4 PARTLY     24 malformed cases: 18 rejected by both, 4 accepted by plan() and refused by build(), 2 accepted",
 "11   refusals never wrote anything: 0 files on disk after all 22 refused cases, including the 4 build-only refusals",
 "12   contract violated both ways: plan() returns a dict for a no-op that build() refuses, and delta=0 ships a 12 MB mod",
 "13 CLAIM 5 REFUTED (dat half)  the .dat patcher's verification has 9 keys and NO proven / not_proven, single or bundle",
 "14   sprites DO carry them: copy 2 proven + 1 not_proven, rename 3 + 1; civtechtrees_json 7 + 1 (quoted in the report)",
 "15 D1 high     aoe2mod/api.py:1967 + intent/compiler.py:1904-1938 - data-mod manifest has no honesty boundary",
 "16 D2 high     api.py:382-386, 938-939, 1759-1761, 1812-1814, 2287-2288 - plan() promises what build() refuses",
 "17 D4/D5 med    emitter.py:355 changes_dat=True over an identical .dat; compiler.py:1926-1938 ok=True on 0 changed bytes",
 "18 D6/D7 med    api.py:1807 counts delta=0 as 63 edits; in_place_patch plan() omits editable and changes_dat entirely",
 "19 D9-D12 low   build() says 'strategy None' for a typo; AttributeError on a non-dict; IntentError unexported; 3 desc drifts",
 "20 NOT TESTED   any not_proven sentence (needs the game), repaint_sld, the install path, 63 civ names by label",
]
for line in L:
    print(line)

# Independent verification of the XS / AI research reports

Auditor: main agent. Method: cross-checked both reports against the **shipped game
files** on this machine, not against the third-party sites that produced them.
All read-only; game never started, game directory never written.

Scripts: `crosscheck_local.py`, `gap_triage.py`, `gap_triage2.py`, `gap_triage3.py`,
`const_truth.py` (all in this directory).

## What held up

| Check | Result |
|---|---|
| Every `xs*` function called by the 7 shipped `.xs` files | **31/31 present** in the guide's function tables |
| Every AI command used by the 90 shipped `.per` files | **271/273 present** in the AI report (2 exceptions below) |
| `xsEffectAmount` signature | Matches shipped usage |
| The corrected names (`xsGetObjectAttribute`, `xsArrayCreateInt`, `xsModifyObjectTasks`, `xsSetContextPlayer`) | Present, and `xsGetObjectData` appears exactly once — as the explicitly-flagged wrong name |
| Bug claims spot-checked (`no unary minus`, `for (a = 0; < 10)`, Script Call params) | All present in the guide |

## ★ Finding 1 — the third-party constant list does not match this game build

`Constants.xs` ships **1,175** constants with an `=` declaration. The guide lists
**1,171**. The sets differ **in both directions** — this is not a subset relation.

**1a. 22 constants the game ships that the guide omits.** A generator that trusts
the site's list will not know these exist:

```
cColorId{Aqua,Black,Blue,Gray,Green,Orange,Purple,Red,White,Yellow}   (10)
cVictoryType{Conquest,Custom,Score,Standard,TimeLimit}                (5)
cActionTypeGatherPoint, cActionTypeUnload
cAttributeCivVoiceOverride
cDoubleClickSelectionBehaviour
cGoldHuntableClass
cTechCostDeductFlag
cUnitFacet
```

The `cColorId*` group matters most: it is the **integer** form. The shipped file
declares both families, verbatim:

```c
extern const string cColorAqua = "<AQUA>";   // string form, <AQUA> markup
extern const int    cColorIdAqua = 4;        // integer form  <- what effects need
```

A tool emitting `cColorAqua` into an integer slot is a type error the engine may
not report.

**1b. 28 names the guide lists that are in no shipped `.xs` file at all.** Of
these, these are absent from *every* shipped `.xs` and appear only inside the
site's own `parsed.json` — i.e. they exist only in the reference, not in the build:

```
cAuraDiplomacy{All,AllButYou,Gaia,GaiaNeutralAlly,GaiaYouAlly,NeutralEnemy,You}   (7)
cAuraEffectBit{AdvancedRangeIndicator,AppliedWhenActivatedOnly,Circular,Multiply,RangeIndicator,Temporary}  (6)
```

The remaining 15 (`cActivationTime`, `cAttributeTriggerSharedLOS`, `cInvalidVector`,
`cOriginVector`, `cTechDeductFlag`, the 10 `cColor*` strings) *are* real shipped
symbols — they live in `Constants.xs` and simply sort differently, so they are
benign drift rather than phantom names.

**Consequence for tooling:** validate every constant against the **shipped
`Constants.xs`**, never against the third-party list. Keep the site's list as
documentation of intent only.

## ★ Finding 2 — the community AI dataset is incomplete relative to the shipped game

Two commands are used by the game's own `Promisory` AI but appear **nowhere** in
`commands.js` (2,021,130 bytes):

```
up-chat-data-to-all-using-id
up-chat-data-to-player-using-id
```

Verbatim shipped usage:

```
Promisory\events.per:5         (up-chat-data-to-all-using-id 2313 c: 7031232); "I am preparing to attack %s, please join me."
Promisory\interaction.per:596  (up-chat-data-to-player-using-id every-ally 22080 g: temporary-goal); "Wood: %d"
```

`interaction.per` alone uses the latter **12 times**. Both take a **format string
with `%s` / `%d`** and a value, which the listed `up-chat-data-to-*` commands do
not — so this is a real, distinct command pair, not a spelling variant.

**Consequence for tooling:** the authoritative command set is
**`commands.js ∪ shipped .per corpus`**. Scanning the 90 shipped `.per` files adds
143 distinct names and recovers these two; the site alone is not sufficient.

## Reproduction

```
python crosscheck_local.py   # both directional coverage checks
python const_truth.py        # shipped-vs-guide constant set difference
python gap_triage2.py        # AI command drift + verbatim shipped usage
```

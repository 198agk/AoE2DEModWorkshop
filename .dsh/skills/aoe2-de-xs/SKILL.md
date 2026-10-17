---
name: aoe2-de-xs
description: Write and debug XS (External Subroutines) scripts for AoE2 DE — the C-like interpreted language used for scenario, random-map, and AI scripting. Use when a task touches .xs files, xs* functions, xsEffectAmount tech/attribute modification, or XS bugs and syntax traps. Load this before emitting any XS code.
---

# XS scripting (AoE2 DE)

XS = **External Subroutines**, Ensemble's scripting language (from AoM/AoE3), ported to AoE2 DE in update 42848. One `.xs` file can be loaded by **all three** content types — scenario, RMS, and AI — by three different mechanisms.

Full reference: `_probe/xs_ai_research/XS_GUIDE_AOE2ROCKS.md` (2,588 lines; **274 functions** in 16 sections, **1,160 constants** in 44 sections, 29 documented bugs). Machine-readable form: `_probe/xs_ai_research/parsed.json`.

## Syntax traps that will bite a generator

Emit code defensively — most of these fail *silently* or are parse errors rather than clean diagnostics.

- **No unary minus.** `-a` is a parse error; write `0-a`.
- **No `+=` / `-=` style shorthand, no prefix `++a`.**
- **No boolean NOT operator.** Boolean OR is a **single** pipe `a | b`, never `||`.
- **No bitwise operators** — but functions `bitAnd/bitOr/bitXor/bitLsh/bitRsh/bitNot` exist.
- **`for` is not C.** `for (a = 0; < 10) { }` — initialiser, semicolon, bare comparison. The engine supplies the step and **it cannot be changed**. No third clause.
- **`return` must be parenthesised**: `return (5+5);`.
- **No array syntax.** Arrays are opaque integer IDs from `xsArrayCreateInt` / `xsArrayCreateString`.
- **Max 12 parameters in a call.** 13 can be *defined* but not called.
- **Results take the type of the FIRST operand**: `9*5.5` → `49`, not `49.5`. This is the most dangerous silent-wrong-answer bug.
- **No implicit int↔float cast across parameters or returns**; explicit `(int)` casts are themselves broken.
- **`%` is broken on floats**; `vector()` rejects variables and expressions.
- **Global `string` and global `static` silently kill execution.**
- **Bare `{}` scopes are illegal.** **`goto` to an undefined label crashes the game.** **A `%` in `xsChatData` that cannot be escaped crashes.**
- **Integers above 999,999,999 are parse errors.**
- `mutable` implements overloading; the **last** definition wins even if it appears after the call.
- `long` / `char` / `double` are documented but **do not exist**.
- `infiniteLoopLimit` is off by one; `infiniteRecursionLimit` silently kills **all** XS at the n-th call.

## Names that do not exist (do not emit them)

`xsGetObjectData`, `xsSetObjectData`, `xsSetObjectAttribute`, `xsGetPlayerAttribute`, `xsRandom`, and most `xsTrigger*`. The real names are `xsGetObjectAttribute`, `xsGetObjectCount`, `xsPlayerAttribute` / `xsSetPlayerAttribute`, `xsGetRandomNumber*`. `xsArraySetInt` returns `bool` (not `int`). `xsDumpArrays()` does nothing. `xsDisableSelf()` is illegal outside a rule body.

## Core API

```
void xsEffectAmount(int effectId, int objectOrTechnologyId, int attributeOrOperation, float value, int playerId, int trainLocationIndex)
int  xsArrayCreateInt(int size, int defaultValue, string uniqueName)
bool xsArraySetInt(int arrayId, int index, int value)
bool xsArrayResizeInt(int arrayId, int newSize)
void xsChatData(string message, int value)
int  xsGetObjectAttribute(int playerId, int objectId, int attribute, int damageClass)
int  xsGetRandomNumberLH(int low, int high)
bool xsModifyObjectTasks(int objectId, int playerId, int taskId, bool edit)
bool xsAddRuntimeEvent(string runtimeName, string functionName, int functionArgument)
```

Constants come from `resources/_common/xs/Constants.xs` (auto-included, never `#include` it). Tech-state constants: `cTechStateNotReady=0 cTechStateReady=1 cTechStateResearching=2 cTechStateDone=3 cTechStateQueued=4 cTechStateDisabled=-1`.

**Validate constants against the shipped `Constants.xs`, never against a third-party list.** Verified: the game ships **1,175** `c`-constants with an `=` declaration; the widely-used community reference lists **1,171** and the sets differ **in both directions**. 22 shipped constants are missing from the reference, including the entire integer colour family — and the two families are easy to confuse, verbatim from the shipped file:

```c
extern const string cColorAqua = "<AQUA>";   // string form, <AQUA> markup
extern const int    cColorIdAqua = 4;        // integer form  <- what effects need
```

Also shipped but unlisted: `cVictoryType{Conquest,Custom,Score,Standard,TimeLimit}`, `cActionTypeGatherPoint`, `cActionTypeUnload`, `cAttributeCivVoiceOverride`, `cDoubleClickSelectionBehaviour`, `cGoldHuntableClass`, `cTechCostDeductFlag`, `cUnitFacet`. Conversely, `cAuraDiplomacy*` (7) and `cAuraEffectBit*` (6) appear in the reference but in **no** shipped `.xs` file — treat them as unverified on this build.

**Tech cost/time modifiers moved.** `cSetTechCost` / `cAddTechCost` / `cModTechTime` (and the `cGaia*` variants) **no longer work** — use `cModifyTech` with `cAttrSet*Cost` / `cAttrSetTime`.

## How XS attaches

- **Scenario**: Map tab → `Script Filename` (write it **without** the `.xs` extension) plus a trigger effect of type **Script Call**. `main()` runs automatically when the scenario plays.
- **RMS**: `#includeXS filename.xs` at the top of the `.rms`; `main()` runs at map generation.
- **AI**: `(include "filename.xs")` at the top of the `.per`, then `(xs-script-call "function name")` inside a `defrule`.

**Script Call cannot pass parameters.** Calling a function that takes arguments that way **silently stops all XS execution** — no syntax error. Emit zero-argument wrappers only. A function containing a comment, when invoked by script call, also breaks execution.

## Player context (read before writing AI-side XS)

XS is **not per-player sandboxed**. As AI code it runs on the host and can read and write other players' state — a documented tournament cheating hazard. XS globals *are* created separately per player that loads the file. XS rules are **global** and must not carry per-player AI logic. **There is no `my-player-number` equivalent in XS** — store it in an AI goal, read it via `xsGetGoal`, and pass it as `playerId` explicitly. `xsSetContextPlayer` must be called before any File I/O function.

## EffectFunction<N> — undocumented, do not generate blind

The `EffectFunction<N>` symbols in the shipped `Effects.xs` have **no documented mapping** from dat effect numbers. The only documented effect→XS path is the **Script Call** effect, which names a zero-argument function by string. (`cAttributeEffectFunctionNumber = 33` is a player-resource slot with no documented consumer.) The upstream bug page for effect-amount issues exists but is an **empty stub**.

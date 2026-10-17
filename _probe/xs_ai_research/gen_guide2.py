# -*- coding: utf-8 -*-
"""Part 2 of the XS guide: attachment, bugs, effect calls, libraries, tools, appendix."""
import sys, io, collections, json
sys.stdout.reconfigure(encoding='utf-8')

D = json.load(open('parsed.json', encoding='utf-8'))
FUNCS, CONSTS = D['functions'], D['constants']

o = io.StringIO(); W = o.write

W(r'''
---

# 5. How XS attaches to a scenario, a map and an AI

## 5.1 Where the files live

XS scripts live in

```
C:\Program Files (x86)\Steam\steamapps\common\AoE2DE\resources\_common\xs
```

That directory already ships `Constants.xs` and `xs.txt`.

* **`Constants.xs` contains every constant in §4 and is available to every XS script
  automatically — no `include` needed.** This is why the constant reference is usable without any
  import step.
* **Never write your code into `default0.xs`** — it is a temporary file the game overwrites.
* Extra scripts are loaded by `include "path"` (absolute or relative to the including file).

## 5.2 Attaching to a custom scenario

1. Open the scenario in the Scenario Editor.
2. `Map` tab → `Script Filename` → type the script's name **without the `.xs` extension**.
3. `Triggers` tab → new trigger → new effect → in the **Effects List** select **`Script Call`**.
4. In the effect's message box you may now write a **normal function call** into the XS script.
   > The site is explicit: *"only those functions that do not take any parameters work here!"*
   > Calling a function with arguments silently stops all XS execution (see §6, Editor bug 1).
   > Putting *comments* in that box raises a parsing error (Editor bug 2).
5. A valid `Script Call` effect turns **green** when clicked; if the XS has an error, clicking it
   shows an error message instead.
6. **`main()` is run automatically when the scenario is played**, in addition to any effect that
   calls it explicitly.

The `Script Call` effect is defined in the trigger-effects reference as: *"This effect can be used
to (define and) call an XS function"*, with two configuration fields — **String ID** (the string ID
of the XS script function name to call) and **Message** (the name of the XS function to call, **or a
function definition which will be called**). That second form — pasting a *definition* into the
effect — is the documented way to run XS on a scenario that has no `.xs` file at all, and is what
the Tricks page means by "copy the code above to a non-running `Script Call` effect".

## 5.3 Attaching to an RMS

At the **very top** of the `.rms` file:

```
#includeXS filename.xs
```

`main()` is automatically called when a map is generated with that RMS.

## 5.4 Attaching to an AI (`.per` / `.ai`)

At the top of the `.per` file:

```
(inlcude "filename.xs")     <-- SIC; the site misspells `include`
```

Inside a `defrule`, call an XS function with:

```
(xs-script-call "function name")
```

AI-relevant runtime facts:

* **Each AI runs its XS code separately**, and all AI XS code executes **on the host's machine** —
  AIs behave as if the host controls them.
* `xs-script-call` does not pass arguments; to get data in, first store it in an AI **goal** from the
  AI script, then have the XS function read it with `xsGetGoal`. This is the standard workaround for
  "XS cannot discover which AI player it is running as".
* `xsAddRuntimeEvent(runtimeName, functionName, functionArgument)` is the other injection point.
  `runtimeName` is `"Random Map"` for RMS, `"Scenario Triggers"` for scenarios, and `"Expert"` plus
  the player number for AI. The named function takes one `int`. **A runtime event is called after
  all the XS code has finished executing but before rules start executing.** It returns `true` if the
  function exists; it **does not work with built-ins**.
* To tell which host you are on: `xsGetMapName(true)` and inspect the extension (`"Random Map"` vs
  `"Scenario Triggers"`), per the same function's documentation.

## 5.5 AI scripting functions (the `xsGetGoal` family)

| Function | Signature |
|---|---|
| `xsGetGoal` | `int xsGetGoal(int id)` |
| `xsSetGoal` | `void xsSetGoal(int id, int value)` |
| `xsGetGoal`-adjacent SN access | see the Ai Scripting section in §3 |

These operate on the **current AI's** goal space, i.e. the AI that called `xs-script-call`.

## 5.6 The player-context problem (read this before writing any AI-side XS)

* XS has **no equivalent of `my-player-number`**. You cannot ask "which player am I?".
* Most functions take an explicit `playerId`. If you pass someone else's ID you are effectively
  cheating, and in tournaments that is a disqualification.
* The documented workaround: store the AI's `my-player-number` in a goal from the AI script, then
  call an XS function via `xs-script-call` which does `xsGetGoal` and assigns the result to a global
  XS `myPlayerNumber`, then pass that everywhere.
* `xsGetContextPlayer()` / `xsSetContextPlayer(int playerNumber)` provide a limited ambient context:
  in functions taking a `playerNumber`, passing **`-1`** uses the context player; in
  `xsEffectAmount`, passing **`-2`** uses the context player.
* **Globals are per player** — each player that loads the `.xs` file gets its own copy of every
  global. **Rules are not** — XS rules appear to function globally, independent of AI players, and
  should therefore not be used for per-player AI logic.

---

# 6. Known bugs and quirks — the load-bearing constraints

Source: `/general/xs/bugs/` and its subpages, "Known Bugs And Quirks In XS Scripting" by Alian713 &
Kramb. The index states: *"All the shown code can be directly copy pasted into any XS file to
reproduce"*. Metadata: **Game Version `101.103.26969.0 (#158041)`**, **Last Updated `14.11.2025`**,
Platform Steam, OS Windows 10.

> `/general/xs/bugs/Effect Amount/` **exists but is an empty stub** — its entire rendered article is
> the heading `Effect Amount` with no content. There is no effect-amount bug list to report.

## 6.1 Chat Data (1 bug)

**Cannot Print `0` Or `1` At The Start Of The Line In `xsChatData()`** — if `0` or `1` is the first
character of the chatted string, it does not appear.

```xs
xsChatData("1 the one at the start isn't visible");
// prints:  the one at the start isn't visible
```

This interacts with the documented `xsChatData` de-duplication quirk: `xsChatData` does not send
the same message twice in a row, so the usual advice is to prefix each message with a unique
counter — which is exactly the prefix this bug eats.

## 6.2 Crashes (3 bugs)

1. **Crash On Using `%` Symbols In `xsChatData()`** — `%` cannot be escaped; `%d` and `%f` are
   format specifiers. Expecting `\%` to be a literal percent **crashes the game**.
2. **Using `goto` With A Non Existent Label Crashes The Game** — and *"How to define a working label
   in XS is currently unknown"*.
3. **Crash On Using An Integer Larger Than `999_999_999` In Chat Data** — chatting an integer larger
   than `999 999 999` with `%d` crashes.

## 6.3 Editor (2 bugs)

1. **Script Call A Function With Parameters** — calling a function *that takes arguments* from a
   `Script Call` effect **stops all XS execution silently**, with no syntax error reported.
   Repro: put `test(1, 2);` in the script-call box.
2. **Script Call A Function With Comments** — a function containing comments, placed in a script-call
   box, causes a parsing error.

## 6.4 Important (1 bug)

**Researching a technology twice in XS causes a crash** — calling `xsResearchTechnology` twice for
the same technology and player crashes the game.

## 6.5 Individual Tech Modifiers (1 bug) — page title is `Task`

**`cSetTechCost`, `cAddTechCost`, `cModTechTime` and their Gaia equivalents no longer work.** These
`xsEffectAmount` commands silently do nothing; previously they allowed modifying a technology's cost
and research time and setting arbitrary resources. See §9.4 for the workaround
(`cModifyTech` + `cAttrSet*Cost` / `cAttrSetTime`).

## 6.6 Language Syntax (21 bugs)

Full verbatim text and reproduction code is preserved in `raw_bugs_LanguageSyntax.txt`. Mechanisms:

| # | Title | Mechanism / workaround |
|---|---|---|
| 1 | Outputs Of Operations Are Of The Wrong Data Type | Result type follows the **first** operand: `9*5.5` → `49`, `5.5*9` correct. `int a=7; float b=1.1; a/b` → `6`, not `6.363636` |
| 2 | Modulo Operator Does Not Work Properly With Floating Point Values | `5.5%1` → `0.000000`, not `0.500000` |
| 3 | Function Parameters And Return Statements Do Not Implicitly Type Cast | `int` → `float` param stays int; returned int is not cast to the declared return type. `float test(float a=-1){return (a*5.5/2);}` called as `test(5)` → `13`, not `13.750000` |
| 4 | Limit On Number Of Params In A Function Call | **Max 12 params in a call.** A 13-param function can be defined but not called; error points at the call line |
| 5 | Cannot Use Variables Or Expressions In Vector Initialisation | `vector(5+5,10,4)` and `vector(x,5,3)` fail with `Could not parse the code for 'main' function`. Use `xsVectorSet(x,y,z)` |
| 6 | Unary Negative Does Not Work | `int c = -a;`, `float d = -a;`, `int g = -a+b;` all fail to parse. Use `0-a` |
| 7 | Explicit Type Casting Does Not Work | `float b = (int)a;` → `0`; `b = (int)5.7;` leaves `b` at `6.7` |
| 8 | Loop Variable Not Bounded To The Scope Of The Loop | The `for` variable remains usable after the loop |
| 9 | Assigning Loop Variable To Itself Does Not Throw An Error | `for(j = j; < 10)` runs the body **once** |
| 10 | Integers Softly Limited To `999_999_999` | `int a = 1000000000;` is a parse error. Larger values only reachable via arithmetic; the true int32 range should be `-2147483648` … `2147483647` |
| 11 | Static Variables In Recursive Functions | A `static` inside a recursive function **cannot be changed** — the value is always the same |
| 12 | Static Variables In Global Scope | `static int a = 10;` at global scope makes XS execution **fail silently** (nothing is chatted). `extern static int a = 10;` should not be legal |
| 13 | Strings In Global Scope | `string a = "test";` at global scope does not retain its value — chats random text or `Error invalid encoding` |
| 14 | Off By One Error With `infiniteLoopLimit` | `infiniteLoopLimit = n;` inside a function makes **all** loops in that function run `n+1` times |
| 15 | Silent XS Crash with `infiniteRecursionLimit` | `infiniteRecursionLimit = n;` allows only `n-1` calls in one stack; the n-th call **silently kills all XS execution** (subsequent code in `main()` never runs) |
| 16 | Return Statements Do Not Work As Documented | Parentheses **required**: `return 5+5;` → `Could not parse the code for 'test' function`; `return (5+5);` works |
| 17 | Scopes Cannot Be Explicitly Created | A bare `{ ... }` block is a parse error |
| 18 | Cannot Declare Variables As A `const` In Function Parameters | `float test(const float a = -1)` → `'const' is not a valid parameter type` |
| 19 | Missing Data Types Which Are Documented | `long`, `char`, `double` do not exist despite the official docs; declaring one → `Could not parse the code for 'main' function` |
| 20 | Weird Behaviour With Return Statements | `return thisDoesNotMatterWhatIsGoingOn(a)/55 + 2*2;` in a `float` function returns `4` (an int) and **ignores the first term** |
| 21 | Using Single Quotes Causes The `Could not emit quads` Error | `string x = 'my string';` is not allowed |

### Cross-cutting lesson for tool authors

Almost every one of these fails **silently** or with an error message that points at the wrong
place (`Could not parse the code for 'X' function`, or nothing at all). A generator of XS must
therefore emit code that avoids the whole class: no unary minus, no `+=`, no `-a`, no bare `a[0]`,
no `printf`-style `%`, no functions >12 params called, no global `string`/`static`, no `(int)` cast,
always parenthesised `return`, and `for` loops in the two accepted forms only.

---

# 7. Libraries and tools

## 7.1 XS Libraries (`/general/xs/libraries/`)

| Library | Author | What it provides |
|---|---|---|
| **`aoe2de_xslibs`** | Kramb (mardaravicius) | List types for `int`/`float`/`bool`/`string`/`vector` with a Python-inspired API; hash maps with int and vector keys; AVL-tree maps for string keys; bitwise AND/OR/XOR/NOT plus shifts (needed because XS has no bitwise *operators*); a Mersenne Twister **MT19937** RNG |
| **`XsStructs`** | KSneijders (MrKirby) | Struct-like types: custom schemas with named attributes, instances, nested structs, multi-dimensional arrays, and save/load via a `.xsdat` file |
| **`aoe2_xsSort`** | duct_ape_ (hmis) | Merge sort plus hard-coded sorting networks for int/float arrays: ascending/descending, in-place and out-of-place, sort from a start index, and argsort permutations |

The repositories themselves could not be opened (see the coverage table: `github.com` is not
fetchable from this environment), so no version numbers or APIs are reproduced here. The site
publishes no versions for them either.

## 7.2 Tools (`/general/xs/tools/`)

| Tool | Author | Purpose |
|---|---|---|
| **XS Check** | Alian713 | A **linter** for AoE2:DE's flavour of XS. It warns on common XS pitfalls and on *errors in syntactically valid XS code* — i.e. exactly the silent-failure class in §6. Distributed via GitHub (not reachable here) |
| **VS Code XS Syntax Extension** | Alian713 | Syntax highlighting / editor support for `.xs`. Also recommended on the beginner page, where it is identified as the VS Marketplace item **`Divy.vscode-xs`**: <https://marketplace.visualstudio.com/items?itemName=Divy.vscode-xs> |

No versions are published by the site for either tool.

## 7.3 Useful Resources (`/general/xs/useful/`)

The entire body of this page is:

> **AoM:EE XS Reference** — <https://mythicfreak.github.io/aomcodereference>

**That link is not usable as fetched.** The target is a Java-doc **frameset**
(`overview-frame.html` / `allclasses-frame.html` / `overview-summary.html`), the frames do not
resolve through `web_fetch`, and `noframes.html` returns HTTP 404. The page is recorded here for
completeness but contributes no content to this document.

## 7.4 Tournament-safety notes (from `xs-for-tournaments`, an AoE2 AI-scripting article)

Not on the requested page list, but it contains the most tool-author-relevant constraints found
anywhere on the site, so it is reproduced here:

* **Cheating classification.** Using XS to read or act on *another* player's state is cheating.
  Specifically flagged: `xsResearchTechnology` (researches immediately), `xsCreateUnit` (places a
  unit immediately), and `xsEffectAmount` (*"basically the same as `fe-cc-effect-amount`"*).
* **Create each array once.** *"If XS code repeatedly creates new arrays throughout the game, the
  game can eventually crash after using up all of the computer's memory."* Store the array ID in a
  global at game start.
* **UI functions can desync.** Anything that differs by the player's language can desync a
  multiplayer game; *"really, the only function that should be used in this category is
  `xsChatData`"*.
* **File I/O.** The files are hex files, unique per player, overwritten every game, with no control
  over filename or location. `xsSetContextPlayer` must be called **before** any file-I/O function,
  and it also affects `xsEffectAmount`.
* **XS rules are global**, XS globals are per player (both covered in §5.6).

---

# 8. The `EffectFunction<N>` convention — what is actually documented

**Being explicit: the `EffectFunction<N>` naming convention is NOT documented anywhere on
`ugc.aoe2.rocks`.** Every raw page for the XS section, the trigger-effects reference, and the
constant reference was searched for `EffectFunction` / `effectFunction`. The only hits anywhere are:

1. **`cAttributeEffectFunctionNumber`** — the single real mention, in the constant reference,
   section 13 (Object Attribute):

   | Constant | Value | Description |
   |---|---|---|
   | `cAttributeEffectFunctionNumber` | `int 33` | ID of the player resource *Effect Function Number* |

   So "Effect Function" exists as a **player-resource attribute ID (`33`)**, reachable through
   `xsGetObjectAttribute` / `xsSetPlayerAttribute`-style calls and through the `cSetAttribute` /
   `cSetPlayerData` effect types. It is a *slot for a number*, and the docs never say what consumes it.

2. **User-defined constants on the Tricks page**, unrelated to any engine convention:
   `extern const int cAuraEffectBitMultiply = 1;` etc. — these are the aura helper's own bit flags.

The community-documented mechanism for an effect to reach XS code is the **`Script Call` effect**
(§5.2), which names an XS function **by string**, not by number, and whose *Message* field may also
carry a full inline **function definition**. There is no documented "effect N calls XS function N"
mapping, and no documented `EffectFunction0` / `EffectFunction1` symbol.

**Practical conclusion for a tool author:** if you are generating content that must invoke XS from a
technology or trigger effect, the only mechanism with documentary support is the `Script Call`
effect naming a **zero-argument** XS function by string. The numbered-effect path is real in the
engine (the attribute ID above is evidence of it) but is **undocumented in this source**, so it
should not be generated blind. This gap cannot be closed from `ugc.aoe2.rocks`; the honest options
are the unreachable `github.com` repositories or game-data inspection, neither of which was
available here.

---

# 9. Practical recipes (worked, from the Tricks page)

These are verbatim techniques from `/general/xs/tricks/` (by Alian713 & Kramb). They are included
because they show *correct* usage that a generator must reproduce exactly.

## 9.1 Unit-specific damage class values

Multiply the damage class by `256` and add the value; negate the whole number for a negative delta.
Does **not** work for values > 255. For `cMulAttribute` also multiply the value by `100`. The total
cannot exceed 255, so at most 2.55× per call — call repeatedly for more.

```xs
const int cGenghisKhan = 731;

xsEffectAmount(cSetAttribute, cGenghisKhan, cAttack, cDamageClassPierce * 256 + 5);
xsEffectAmount(cAddAttribute, cGenghisKhan, cAttack, cDamageClassPierce * 256 + 5);
xsEffectAmount(cAddAttribute, cGenghisKhan, cAttack, (cDamageClassPierce * 256 + 3) * -1);
xsEffectAmount(cMulAttribute, cGenghisKhan, cAttack, cDamageClassPierce * 256 + 100 * 2);
```

## 9.2 Setting and unsetting costs

Unset a cost by multiplying it by `-2`; create one by multiplying by `-1`.

```xs
const int HOUSE = 70;

xsEffectAmount(cMulAttribute, HOUSE, cWoodCost, -2, 1);   // remove the wood cost
xsEffectAmount(cMulAttribute, HOUSE, cStoneCost, -1, 1);  // create a stone cost slot
xsEffectAmount(cSetAttribute, HOUSE, cStoneCost, 10, 1);  // set it to 10
```

## 9.3 Multiple train locations and damage sprites

Both are **lists** in DE, with a per-list *Entry Mod* attribute.

Relevant globals: `cTrainLocationsEntryMod`, `cTrainLocationsTotalNum`, `cDamageGraphicsEntryMod`,
`cDamageGraphicsTotalNum`.

> *"Units no longer have a single train location, but a list of train locations. To change the train
> location of a unit, you now have to give the index of the list entry that you want to change. You
> can modify the array size, and you can also use the `multiply attribute` operation on the Entry Mod
> attribute to insert/delete an entry at a specific index. For example you have 5 entries and you want
> to delete the 3rd one, you use `multiply attribute` on entry mod with `-3` and that specific element
> will be gone. Insert entry: mul with `0, 1, 2, ...` Delete entry: mul with `-1, -2, -3, ...` (or
> "Divide" with `0, 1, 2, ...` in Scenario Triggers). So no need to resize and repopulate the rest of
> the list. In a similar way, you can use mul attribute with `32767` to always insert an entry at the
> tail, even when you don't know the current size of the array. This works for both Damage Sprites
> modding and Train Locations modding."*

```xs
// change the 2nd train location
xsEffectAmount(cSetAttribute, unitId, cTrainLocationsEntryMod, 1, player);
xsEffectAmount(cSetAttribute, unitId, cTrainLocation, buildingId, player);

// read how many train locations there are
int numOfLocations = xsGetObjectAttribute(player, unitId, cTrainLocationsTotalNum);

// insert a new 2nd train location
xsEffectAmount(cMulAttribute, unitId, cTrainLocationsEntryMod, 1, player);

// remove the 2nd train location
xsEffectAmount(cMulAttribute, unitId, cTrainLocationsEntryMod, -2, player);

// append at the tail without knowing the size
xsEffectAmount(cMulAttribute, unitId, cTrainLocationsEntryMod, 32767, player);

// read the 2nd train location: set the entry mod first, then read
xsEffectAmount(cSetAttribute, unitId, cTrainLocationsEntryMod, 1, player);
int buildingId = xsGetObjectAttribute(player, unitId, cTrainLocation);
```

*"If location change or value read is needed it's always better to set `cTrainLocationsEntryMod`
beforehand."* For **damage sprites**, use **`254`** instead of `32767` as the "tail" index.

## 9.4 Technology cost and time (works around §6.5)

Use `xsEffectAmount(cModifyTech, techId, subCommand, value, player)`, because `cSetTechCost`,
`cAddTechCost` and `cModTechTime` no longer work.

* *"You can not add or change which resources the tech costs, only their amounts."*
* *"Be careful when using addition and multiplication sub commands such as `cAttrAddFoodCost` or
  `cAttrMulGoldCost`. When doing calculations sometimes they take current tech price and sometimes
  the original price. This leads to unexpected results. It is better to do calculations and cost
  tracking yourself and use sub commands such as `cAttrSetGoldCost` to update the cost."*

```xs
const int loom = 22;

xsEffectAmount(cModifyTech, loom, cAttrSetGoldCost, 66, 1);
xsEffectAmount(cModifyTech, loom, cAttrSetTime, 1, 1);
```

The page walks through `cAttrMulGoldCost, 3` then `cAttrAddGoldCost, 100` and concludes: *"After
running these commands loom cost is 266 gold: (50 + 50 + 66) + 100."* And:

```xs
xsEffectAmount(cModifyTech, loom, cAttrSetFoodCost, 50, 1);
```

*"Does not do anything since loom does not already have food cost."* The safe pattern is to keep the
cost in an XS variable and always use `cAttrSetGoldCost` in `main()` and in a helper the triggers
call.

## 9.5 Auras (`xsAddAura`) — a large user-written helper, not an engine built-in

Signature as published (12 parameters, at the 12-parameter call limit of §6 bug 4):

```xs
bool xsAddAura(int auraUnit = -1, int affectedUnit = -1, int player = -1,
               int attribute = -1, float value = 0, float range = 0,
               int auraEffectsBitField = 0, int targetDiplomacy = 0,
               int tempAuraDuration = 0, int tempAuraCooldown = 0,
               int unitsInRangeToTurnOn = 1, bool affectSelf = false)
```

Documented caveats, verbatim:

* *"adding auras "freezes" the unit for further non task modifications. To work around that can
  respawn the unit or do a double replace with another unit and itself."*
* *"Adding an aura to a unit of the same player that already has an aura for the same attribute and
  affectedUnit will overwrite it instead."*

Bit field (user-defined constants, `extern const int`):

| Constant | Value |
|---|---|
| `cAuraEffectBitMultiply` | `1` |
| `cAuraEffectBitCircular` | `2` |
| `cAuraEffectBitRangeIndicator` | `4` |
| `cAuraEffectBitTemporary` | `8` |
| `cAuraEffectBitAppliedWhenActivatedOnly` | `16` (only works with `cAuraEffectBitTemporary`) |
| `cAuraEffectBitAdvancedRangeIndicator` | `32` |

Diplomacy (user-defined constants):

| Constant | Value |
|---|---|
| `cAuraDiplomacyAll` | `0` |
| `cAuraDiplomacyYou` | `1` |
| `cAuraDiplomacyNeutralEnemy` | `2` |
| `cAuraDiplomacyGaia` | `3` |
| `cAuraDiplomacyGaiaYouAlly` | `4` |
| `cAuraDiplomacyGaiaNeutralAlly` | `5` |
| `cAuraDiplomacyAllButYou` | `6` |

Mechanism: an aura is implemented as an engine **task**. The helper calls `xsResetTaskAmount()`, then
sets `cTaskAttrTaskType` to `0.0 + cTaskTypeAura`, `cTaskAttrWorkValue1` (value),
`cTaskAttrWorkValue2` (unitsInRangeToTurnOn), `cTaskAttrWorkRange` (range),
`cTaskAttrSearchWaitTime` (the attribute being affected), `cTaskAttrCombatLevelFlag` (the effects bit
field), `cTaskAttrOwnerType` (targetDiplomacy), and either `cTaskAttrObjectClass` (if
`900 <= affectedUnit < 1000`) or `cTaskAttrObjectId`; it finishes with
`xsModifyObjectTasks(auraUnit, player)`. It reads the unit's own aura state back out of
`xsGetObjectAttribute(player, auraUnit, cCombatAbility)` — bit `32` means "has an aura", bit `64`
means `affectSelf`. It uses `cGaiaSetAttribute` instead of `cSetAttribute` when `player == 0`. For a
temporary aura it also sets `cMaxCharge` to `1`, `cRechargeRate` to `1000/cooldown`, `cChargeEvent`
to the duration, and `cChargeType` to `-3.0`.

---

# 10. Appendix — raw evidence files

All raw fetched text is kept alongside this document:

| File | Contents |
|---|---|
| `raw_index.txt` | `/general/xs/` index |
| `raw_beginner.txt` (1465 lines) | For Beginners tutorial — full text with code |
| `raw_programmer.txt` | For Programmers tutorial — full text with code |
| `raw_tricks.txt` (430 lines) | Tricks — the 5 techniques above in full |
| `raw_functions.txt` | Functions reference — 274 entries, source of §3 |
| `raw_constants.txt` | Constants reference — 1160 entries, source of §4 |
| `raw_libraries.txt` | XS Libraries |
| `raw_tools.txt` | XS Tools |
| `raw_useful.txt` | Useful Resources (single dead link) |
| `raw_bugs.txt` | Bugs index |
| `raw_bugs_ChatData.txt`, `raw_bugs_Crashes.txt`, `raw_bugs_Editor.txt`, `raw_bugs_Important.txt`, `raw_bugs_IndivTechMod.txt`, `raw_bugs_LanguageSyntax.txt` | Bug subpages |
| `raw_bugs_EffectAmount.txt` | Empty stub (13 bytes of body) |
| `raw_trig_effects.txt` | Trigger-effects reference — `Script Call` definition |
| `raw_guide_xs-for-tournaments.txt` | Tournament-safety article (§7.4) |
| `parsed.json` | Machine-readable `{functions:[…], constants:[…]}` used to build §3 and §4 |
| `extract.py`, `parse_refs.py`, `gen_guide.py` | The extractor, the reference parser, and this generator |

The `raw_*.html` originals are also present. Note that the working directory also contains unrelated
files fetched from other sections of the same site by a different task; they are **not** sources for
this document.

---

*Generated from `https://ugc.aoe2.rocks/` — AoE2DE UGC Guide. Constant and function data extracted
verbatim; narrative sections quote the guide. Gaps are stated explicitly rather than filled from
memory.*
''')

open('guide_part2.md', 'w', encoding='utf-8').write(o.getvalue())
print('part2 chars:', len(o.getvalue()))

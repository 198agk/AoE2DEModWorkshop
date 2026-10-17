---
name: aoe2-de-ai-scripting
description: Write and debug AoE2 DE AI scripts (.per files) — defrule/defconst rules, facts vs actions, goals and strategic numbers, the up-* UserPatch/DE command set, and load-if compile-time conditionals. Use when a task writes AI behaviour, custom AI, DUC unit micro, or AI↔XS bridging. Load before emitting any .per code.
---

# AoE2 DE AI scripting (`.per`)

Full reference: `_probe/xs_ai_research/AI_SCRIPTING_AIREF.md` (8,553 lines / 815 KB) — **386 commands**, **100 parameters**, **313 strategic numbers**, **430 load-if symbols**, and complete **object (778)** and **tech (331)** id tables with their `.per`-writable `aiName` tokens. Upstream data file: `https://airef.github.io/js/commands.js`.

**The authoritative command set is `commands.js` ∪ the shipped `.per` corpus, not `commands.js` alone.** Verified: the game's own `Promisory` AI uses two commands that appear **nowhere** in the 2 MB upstream dataset:

```
Promisory\events.per:5         (up-chat-data-to-all-using-id 2313 c: 7031232); "I am preparing to attack %s, please join me."
Promisory\interaction.per:596  (up-chat-data-to-player-using-id every-ally 22080 g: temporary-goal); "Wood: %d"
```

`interaction.per` uses the latter 12 times. Both take a **`%s`/`%d` format string** plus a value — which the listed `up-chat-data-to-*` commands do not — so they are a genuinely distinct pair. When generating, scan the 90 shipped `.per` files (which contributes 143 distinct names) as well as the documented catalogue.

## Rule structure

```
(defrule
    <fact>          ; zero or more conditions
    <fact>
=>
    <action>        ; zero or more actions
)
```

- `=>` is **mandatory**. Each fact/action is wrapped in its **own** parentheses, nested inside `defrule`.
- `(true)` is the canonical always-true fact. `do-nothing` satisfies the one-action minimum.
- `disable-self` = permanent run-once idiom. A disabled rule **still occupies its rule id** and still counts for `up-jump-rule`.
- **Rules are NOT a first-match chain.** Every pass walks the list in order and every rule whose facts all hold fires. Mutual exclusion is built explicitly with `disable-self`, goal/flag gating, or rule jumps.
- **Rule ids follow definition order**, so `load` order determines numbering — reordering loads silently renumbers later rules.
- Comment character is **`;`**.

Invariants to enforce in a generator: every rule needs ≥1 fact and ≥1 action; **max 32 elements per rule in DE (16 in UP)** — budget 16; `defrule` and `=>` do not count, logical operators **do**.

## Facts, actions, and the guarded-action idiom

`Fact/Action` commands may sit in the fact block and **execute there**; if the action cannot execute they return false and the rest of the rule stops. That is the UP idiom for a guarded action — `(up-research ...)` or `(up-train ...)` in the fact block.

## Compilation model (why argument order matters)

The engine compiles the whole script to strictly numeric code at load. English names and numeric ids are interchangeable:

```
(players-unit-type-count any-enemy archer == 5)
  -> archer => 4 (object id), any-enemy => -106 (wildcard), == => 4
  = (players-unit-type-count -106 4 4 5)
```

Command identity is **positional** — the engine knows slot 2 is an archer because of the slot. A generator must know each command's exact signature and declared argument order. Command names have internal numeric ids that are **not publicly documented**.

## Value-type operators

- `typeOp` = exactly `{c:, g:, s:}` — tells the engine to treat the next parameter as constant / goal / strategic number.
- For `compareOp` the `c:` prefix is optional (`>` == `c:>`).
- **For `mathOp` the `c:` prefix is required** — `c:+` adds a constant; a bare `+` is invalid where a mathOp is expected.

## Storage — there are no variables

The only mutable storage is the fixed arrays of **goals** (`set-goal`, `up-modify-goal`) and **strategic numbers** (`set-strategic-number`, `up-modify-sn`). There is no `defglobal` in the sourced data — do not assume one. The community idiom is to treat unused high-numbered SNs (313 of 0–511 carry no engine behaviour) as scratch.

## Hard limits (DE / UP / 1.0c)

| Quantity | Limit |
|---|---|
| Rules | 10,000 (ids 0–9,999) / 1000 in 1.0c |
| Elements per rule | **32 DE / 16 UP** |
| Goals | 1–16,000 (512 UP, 40 AoC) |
| Strategic Numbers | 0–511 |
| Timers | 1–100 (1–50 UP, 1–10 1.0c) |
| Defconst values | −32768…32767, or a text string |
| Goal / SN values | −2,147,483,648…2,147,483,647 |
| Flags | powers of 2 up to 2^31; defconst capping at 16384 |
| DUC search list | 240 local / 40 remote |
| Taunts | 1–255 |
| **Characters per line** | **255, including comment characters** |
| Nested `load` | 10 files deep |
| Nested `#load-if` | documented 50; real limit "upper 30s" |

**Goal-range caveat:** goals 1–40 must not be used with multi-goal-writing commands (Point commands, Cost Data, `up-get-search-state`, `up-get-guard-state`) — Point writes 2 goals, the others write 4. Safe practice: goals 509–512 for simple tasks only.

**Performance:** any script pass over **20 ms** causes lag; measure with `up-get-precise-time`.

## `up-*` is the main body of real code

Across all 90 shipped `.per` files, `up-*` commands dominate: `up-compare-goal` (7,306), `up-modify-goal` (2,792), `up-jump-rule` (1,998), `up-research-status` (1,837), `up-modify-sn` (1,125), `up-find-local` (896). Shared vanilla command types number only 27.

**Do not emit these 6 commands** — the source marks them "Don't Use": `disable-rule`, `enable-rule` (*"Not Fully Implemented!"*), `set-author-email`, `set-author-name`, `set-author-version` (game ignores all three), `trace-fact` (*"doesn't work"*).

## `load` and compile-time conditionals

`load` is unconditional, takes a **filename with no path and no extension** (`(load "My AI/Example")` — subfolders use `/`), and may appear anywhere **between** rules but **not inside** one. `load-random` is the weighted variant. `#load-if-defined` / `#load-if-not-defined` select at compile time; their symbol namespace is separate from `defconst` (430 symbols across 17 groups, dumped to `_probe/xs_ai_research/raw_ai_loadif_symbols.md`).

## AI ↔ XS bridge

- `(include "filename.xs")` — **the `.xs` extension is required** — then `(xs-script-call "function")` inside a rule.
- Exposed to XS: `xsGetGoal`, `xsSetGoal`, `xsGetStrategicNumber`, `xsSetStrategicNumber` — scoped to the calling AI player.
- **No `my-player-number` in XS.** Store it in a goal, read it with `xsGetGoal`, pass it as `playerId` explicitly.
- **Never use XS rules in AI scripts** — the documented reason: *"XS rules seem to function globally, independent of AI players, which can easily throw off any player-specific code the rules contain."*
- `xsChatData` is the only XS debugging chat command. File I/O writes hex, is per-player, is **overwritten each game**, and **you cannot choose a filename or location** — prefer `up-log-data`.
- XS-only capabilities with no `.per` equivalent: `xsGetGroupMoveTarget`, `xsGetGarrisonedInUnitId`, `xsGetGarrisonedUnitIds`, `xsGetTechAttribute`, and the math functions (`sqrt`, trig).

## The `.ai` extension — stay honest

The `.ai` marker-file / `.per` payload split is **not sourced anywhere**. `.ai` occurs zero times in the entire upstream dataset. AIREF names exactly two extensions: **`.per`** (the language) and **`.xs`**. Locally, all shipped `.ai` files are 0 bytes and sit beside a same-named `.per` — that is consistent with a marker, but "what the interpreter adds to an extensionless `load`" is **undocumented**. Treat any stronger `.ai` claim as unsourced.

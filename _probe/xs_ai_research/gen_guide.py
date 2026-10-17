# -*- coding: utf-8 -*-
"""Generate XS_GUIDE_AOE2ROCKS.md from parsed.json + hand-written narrative."""
import json, sys, io, collections, re
sys.stdout.reconfigure(encoding='utf-8')

D = json.load(open('parsed.json', encoding='utf-8'))
FUNCS, CONSTS = D['functions'], D['constants']

# The site's section headings leak into the last entry's description ("...<br>14. Damage Class¶").
# Strip any trailing "N. Section Name" heading remnant from descriptions.
TRAIL_HEADING = re.compile(r'[\s\u00b6]*(?:\n|\r)+[ \t]*\d+(?:\.\d+)*\.[ \t]*[^\n\r]*[\s\u00b6]*$')

def clean_desc(s):
    if not s:
        return ''
    s = s.strip()
    for _ in range(3):
        s2 = TRAIL_HEADING.sub('', s)
        if s2 == s:
            break
        s = s2.strip()
    return s

# The site's "N. Section" headings leak into the last entry's description, because the
# parser's body ran on to the next heading. Strip that trailing heading remnant.
TRAIL_HEADING = re.compile(r'[ \t\u00b6]*[\r\n]+[ \t]*\d+(?:\.\d+)*\.[ \t]*[^\n\r]*[\s\u00b6]*$')

def clean_desc(s):
    if not s:
        return ''
    s = s.strip()
    for _ in range(4):
        s2 = TRAIL_HEADING.sub('', s).strip()
        if s2 == s:
            break
        s = s2
    return s

def cell(s):
    if s is None: s = ''
    s = str(s).replace('\\', '\\\\').replace('|', '\\|')
    s = re.sub(r'\s*\n+\s*', '<br>', s.strip())
    return s.strip()

o = io.StringIO()
W = o.write

# ---------------------------------------------------------------- header
W(r'''# XS Scripting Reference — Age of Empires II: Definitive Edition

**Source of truth:** the community *AoE2DE UGC Guide* at <https://ugc.aoe2.rocks/> (by Alian713,
Kramb, KSneijders and other contributors). Every signature, constant name and numeric value below
was extracted verbatim from that site's rendered pages, not from memory. The `functions/` and
`constants/` pages are the project's own reference (authored by Alian713, Kramb and KSneijders) and
are the most structured part of this document; §3 and §4 are generated mechanically from them.

**Game version in the docs' bug tracker:** `101.103.26969.0 (#158041)`, bug page last updated
`14.11.2025` (platform Steam, Windows 10).

## Page coverage (honest accounting)

| Page | Status |
|---|---|
| `/general/xs/` (index) | fetched |
| `/general/xs/beginner/` | fetched, full text extracted |
| `/general/xs/programmer/` | fetched, full text extracted |
| `/general/xs/tricks/` | fetched, full text extracted (5 techniques) |
| `/general/xs/functions/functions/` | fetched — **274 functions** parsed |
| `/general/xs/constants/constants/` | fetched — **1160 constants** across 44 sections parsed |
| `/general/xs/libraries/` | fetched (3 libraries listed) |
| `/general/xs/tools/` | fetched (2 tools listed) |
| `/general/xs/useful/` | fetched — **body is a single dead link** to an AoM:EE reference; see below |
| `/general/xs/bugs/` + 6 subpages | fetched |
| `/general/xs/bugs/Effect%20Amount/` | fetched — **page is an empty stub** (heading only, no content) |
| `/general/xs/bugs/Language%20Syntax/` | fetched — 21 documented bugs |
| `/scenarios/triggers/effects/effects/` (extra) | fetched — gives the `Script Call` effect definition |
| AoM:EE XS Reference (`https://mythicfreak.github.io/aomcodereference/`, linked from `/useful/`) | **NOT fetchable** — it is a Java-doc HTML *frameset*; its frames (`overview-frame.html`, `allclasses-frame.html`, `overview-summary.html`) do not resolve; `noframes.html` returns HTTP 404 |
| `web_search` | **UNAVAILABLE** in this environment (`DeepSeek search has no API key for "DEEPSEEK_API_KEY"`), so nothing outside the reachable link graph could be corroborated |
| any `github.com` URL | **NOT fetchable** (`URL hostname "github.com" resolves to a non-public IP address`) — so the three library repos and the two tools' repos could only be described from the site's own prose |

---

# 1. What XS actually is

XS ("X Scripting") is the scripting language of the **Genie engine / AoE2DE**, a small
C-like/Java-like interpreted language. It is the same language family used by *Age of Mythology:
Extended Edition* — which is why the site's "Useful Resources" points at an AoM:EE XS reference and
why some documented leftovers (see *Missing data types*) are ancient.

What matters practically:

* XS is **orthogonal to the trigger system, to RMS and to the AI script system — it plugs into all
  three.** One `.xs` file can be loaded by a scenario, by a random-map script, and by an AI `.per`
  file; the loading mechanism differs, the language does not.
* XS gives you what triggers cannot: real loops, real functions, arithmetic on gameplay attributes,
  reading unit/player state at runtime, file I/O, and the ability to modify **object defs and
  technology defs** (the `xsEffectAmount` family), which is the primary reason people use it for mods.
* XS is **not sandboxed by player.** As an AI script it runs on the *host's* machine for every AI
  player, and many functions will happily read or write another player's state. This is a
  multiplayer/tournament cheating hazard, and it is the reason the tournament guidance insists on
  `xsSetContextPlayer` / an explicit `myPlayerNumber`.
* XS is **fragile and full of asymmetries**. The bug list in §6 is not trivia — it is the practical
  contract. A tool that *generates* XS must respect it or it will emit code that silently does
  nothing, or crashes the game.

---

# 2. Language syntax

## 2.1 Types

| Type | Literal / initialisation | Notes |
|---|---|---|
| `int` | `int a = 10;` | 32-bit in intent, but **softly limited to ±999 999 999** by the parser (§6, bug 10) |
| `float` | `float a = 3.1;` | printed with `%f`-style formatting, e.g. `5.5` → `5.500000` in chat |
| `string` | `string a = "string";` | **double quotes only** — single quotes cause `Could not emit quads` (§6, bug 21) |
| `bool` | `bool a = true;` | `true` is also `1`, `false` is also `0` |
| `vector` | `vector v = vector(1.2, 2.3, 3);` | 3 × float. **Cannot be initialised from variables/expressions** — see below |

The official docs also mention `long`, `char` and `double` — **they do not exist in AoE2DE's XS**;
declaring one yields `Could not parse the code for 'main' function` (§6, bug 19).

## 2.2 Variable declarations

```xs
int a = 10;
float PI = 3.1415;
const int a = 10;            // immutable
static int counter = 0;      // keeps its value across calls to the enclosing function
extern const int cFoo = 1;   // declaration without definition, used for constants
mutable int foo(int a = 0);  // overridable / overloadable function (see 2.7)
```

* Every variable must be assigned a value **where it is declared**.
* `const` values are compile-time constants; `extern const` is how the docs declare named constants.
* **`static` is dangerously broken in two specific positions** — at global scope it silently kills
  all XS execution, and inside a recursive function it cannot be modified (§6, bugs 11–12). Use it
  only as a function-local counter in a non-recursive function.

## 2.3 Naming rules and conventions

* Names may contain only letters, numbers and underscores; **may not start with a number**; are
  **CaSe SeNsItIvE**; may not be a keyword.
* Convention: all-lowercase for single words, `camelCase` for multi-word names, and
  `CONSTANTS_WITH_UNDERSCORES`. The engine's own constants are `cPascalCase`.

## 2.4 Operators (and what does not exist)

| Category | Syntax | Notes |
|---|---|---|
| Arithmetic | `+  -  *  /  %` | Integer division truncates: `5/2 = 2`, `17/6 = 2`. Float division needs at least one float: `5.0/2.0 = 2.5` |
| Assignment | `a = b;` | **No shorthand assignment** (`+=`, `-=`, …) |
| Postfix | `a++;  a--;` | supported |
| **Unary minus** | — | **DOES NOT EXIST.** `-a` is a parse error. Write `0-a`. Use `0-a+20`, not `-a+20` |
| Prefix | — | **not supported** (`++a` / `--a`) |
| Relational | `<  >  <=  >=  ==  !=` | also work on strings (lexicographic) |
| Boolean AND | `&&` | |
| Boolean OR | `\|` — a **single pipe** | `a \| b`, not `\|\|` |
| **Boolean NOT** | — | **not supported**; there is no negation operator |
| Bitwise | — | **not supported as operators** — but see the `bit*` *functions* in §3 (Maths) |
| Concatenation | `+` | Any type concatenates onto a string: `"this is " + 11 + " " + 5.5 + " " + true + " " + v` → `this is 11 5.5 1 (1.0, 2.0, 3.0)` |
| Comments | `// line` and `/* block */` | |

### Type-coercion gotchas (these bite constantly)

1. **The result type of a binary operation is decided by the FIRST operand.** `9*5.5` → `49`
   (int × float → int), but `5.5*9` is correct. Likewise `int a=7; float b=1.1; a/b` prints `6`,
   not `6.363636`.
2. **`%` is broken for floats.** `5.5%1` prints `0.000000`, not `0.500000`.
3. **Function parameters and `return` do not implicitly cast.** An `int` passed to a `float`
   parameter stays an `int`; an `int` returned from a `float` function is not converted.
4. **`int` → `float` → `bool` → `string` casting:** `int`/`float`/`bool` freely cast among
   themselves and all cast onto strings via concatenation. `string a = 5.5;` does *not* work —
   write `string a = ""+5.5;`.
5. **`float` → `int` truncates, it does not round.** `3.9` → `3`.
6. **Explicit casts `(int)x` are documented but broken.** `float b = (int)a;` assigns `0`;
   `b = (int)5.7;` does nothing at all (§6, bug 7).
7. **Strings and `static` cannot live at global scope** (§6, bugs 12–13).

## 2.5 Control flow

```xs
if (a == 1) { ... } else if (a == 2) { ... } else { ... }

switch (a) {
    case 1 : { ... }
    case 2 : { ... }
    default : { ... }
}

while (a < 10) { ... }

// The XS for-loop has NO third clause and NO settable step:
for (a = 0; < 10) { ... }     // counts up, +1 each iteration
for (a = 10; > 0) { ... }     // counts down, -1 each iteration

break;  continue;  return (value);
```

* **The `for` header is not C.** You write the init, a semicolon, then a *bare comparison*; the
  engine supplies the increment. `a++` / `step` clauses are not accepted and **the step size cannot
  be changed**.
* `return` **must have parenthesised expression**: `return (5+5);` works, `return 5+5;` gives
  `Could not parse the code for 'test' function` (§6, bug 16).
* A bare `{ ... }` block to create an explicit scope is a parse error (§6, bug 17).
* A `for` loop's variable **leaks** into the enclosing scope after the loop (§6, bug 8).
* `goto` exists syntactically but the semantics are broken: a non-existent label crashes the game,
  and how to define a working label is unknown (§6, Crashes 2).

## 2.6 Arrays

XS has **no array syntax**. There is no `int a[] = new int[10];`, no `a[2]`. Arrays are opaque
engine objects addressed by an integer **array ID** returned from `xsArrayCreate*` and manipulated
only through functions (§3, Arrays).

* Arrays are **global and never go out of scope** — only their IDs do. An array created inside a
  loop or rule body persists forever.
* Reading an invalid `arrayID`, or an out-of-range/negative index, **returns a default rather than
  erroring**:
  `int -1`, `float -1.0`, `bool false`, `string ""`, `vector (0,0,0)`.
* Array names must be **unique** strings.
* Create an array **once** and store its ID in a global; creating arrays repeatedly leaks memory
  and eventually crashes the game (see the tournament guidance note in §7).
* `xsDumpArrays()` is documented as dumping all arrays and **does absolutely nothing**.

## 2.7 Functions

```xs
returnType functionName(dataType parameter1 = defaultValue1, ...) {
    return (value);
}
```

* Every parameter **must** have a default value (`float test(float a = -1)`).
* The return value **must** be parenthesised.
* **At most 12 parameters may be passed in a call.** A 13-parameter function can be *defined* but
  not *called*; the error is reported at the call site (§6, bug 4).
* Parameters cannot be `const` (`'const' is not a valid parameter type`, bug 18).

### `mutable` — overloading / override hooks

`mutable` marks a function as overridable. This is XS's whole "library hook" mechanism.

```xs
mutable int foo(int a = 0) { return (a+1); }   // must be marked mutable
int foo(int a = 0) { return (a+2); }           // later redefinition, mutable not required
```

* The **first** definition must be marked `mutable`; later redefinitions may omit it.
* There is **no limit** on how many times a function may be redefined.
* Redefinitions **must match the return type, argument count and argument types**, or an error is thrown.
* **The last definition wins, even if it appears textually after the call.** A third overload
  defined *below* `main()` still overrides the call inside `main()`.
* Overloads may specify different default values, but **defaults are not bound to the body** of the
  overload that declares them: a call can take its defaults from an earlier definition and its body
  from a later one.

### Includes / modular code

```xs
include "./VectorOperations.xs";   // relative to the including file, or absolute
```

Code should be grouped into one function per operation and one file per group. **Known bug: XS
scripts are not properly transferred to other players in the lobby** — the documented workaround is
to send every player the `.xs` files manually.

## 2.8 Vectors

```xs
vector v = vector(1, 2, 3);          // literals only
vector v = cInvalidVector;           // (-1,-1,-1)
vector v = cOriginVector;            // (0,0,0)
v = xsVectorSet(1, 2, 3);            // full set, works with variables
v = xsVectorSetX(v, x);              // per-component set (returns the new vector)
float x = xsVectorGetX(v);
float len = xsVectorLength(v);       // sqrt(x^2+y^2+z^2)
vector u = xsVectorNormalize(v);
```

`vector(x, y, z)` accepts **only literals** — variables and expressions inside the constructor are
a parse error. `xsVectorSet*` returns a *new* vector; the argument is not modified in place.

## 2.9 Rules

```xs
rule ruleName
active          // or: inactive
group groupName
minInterval <int>
maxInterval <int>
highFrequency
runImmediately
priority <int>
{
    // body
}
```

* A rule is declared **outside** any function; `main()` or a `Script Call` starts things.
* `active` — runs by default; `inactive` — does not (enable with `xsEnableRule`).
* `groupName` follows the same naming laws as variables.
* `highFrequency` — "Loop the rule 60 times every physical second (this is independent of in-game
  speed)".
* **Only one of `highFrequency` or the `minInterval`/`maxInterval` pair may be used** — not both.
* `runImmediately` — the docs state "it is currently unknown as to what this option does".
* Rules execute in **descending priority** order.
* `cActivationTime` is only defined inside a rule body and holds that rule's activation time (in
  seconds).
* **XS rules are global, not per-player** — they should not be used from AI scripts for
  per-player logic (unlike global XS *variables*, which *are* created separately per player).

## 2.10 Scope

* Local variables are visible only inside the function that declares them; a variable may not be
  used before its declaration.
* A variable declared **outside** all functions is **global**. Globals are initialised once, and —
  critically for AI — **a separate copy of every global is created for each player that loads the
  `.xs` file**, so AI players do not overwrite each other's XS globals.
* A global variable per player is exactly how you safely store "my player number" in an AI.

---

# 3. Function reference

`xs`-prefixed functions below are engine built-ins. The site documents **274** of them in
**16 sections**. Where a parameter is marked *(Optional)* the site means "has a default and may be
omitted"; the parameter order shown is the **exact call order** — XS has no keyword arguments.

| Section | Count |
|---|---|''')

sec_counts = collections.Counter(f['section'] for f in FUNCS)
for s, n in sec_counts.most_common():
    W('\n| %s | %d |' % (cell(s), n))
W('\n\n> **Note — names that do NOT exist.** `xsGetObjectData`, `xsSetObjectData`, `xsSetObjectAttribute`,\n> `xsGetPlayerAttribute`, `xsRandom` and `xsTrigger*` (beyond `xsTriggerVariable` /\n> `xsSetTriggerVariable`) are **absent from the published reference**. The real names are\n> `xsGetObjectAttribute`, `xsGetObjectCount`, `xsGetObjectName`, `xsGetObjectTaskCount`,\n> `xsPlayerAttribute` / `xsSetPlayerAttribute`, and the three `xsGetRandomNumber*` functions.\n> **Verify every name against the tables below before emitting it** — XS reports an unknown\n> function only as a parse error, and only at parse time.\n\n')

# per-section function tables
for s in [k for k, _ in sec_counts.most_common()]:
    rows = [f for f in FUNCS if f['section'] == s]
    W('\n## %s (%d)\n\n' % (s, len(rows)))
    W('| Function / signature | Returns | Description |\n|---|---|---|\n')
    for f in rows:
        desc = f['desc'] or ''
        W('| `%s` | `%s` | %s |\n' % (cell(f['prototype']), cell(f['returning']), cell(clean_desc(desc))))
o.write('\n')

# ---------------------------------------------------------------- constants
W(r'''
---

# 4. Constant reference

**1160 constants** in **44 sections**. Values are reproduced exactly as published (`int N`,
`float N`, `string`); the type prefix is part of the site's published value.

| Section | Count |
|---|---|''')
c_counts = collections.Counter(c['section'] for c in CONSTS)
for s, n in c_counts.most_common():
    W('\n| %s | %d |' % (cell(s), n))
W('\n')

for s, n in c_counts.most_common():
    rows = [c for c in CONSTS if c['section'] == s]
    W('\n## %s (%d)\n\n' % (s, n))
    W('| Constant | Value | Description |\n|---|---|---|\n')
    for c in rows:
        W('| `%s` | `%s` | %s |\n' % (cell(c['name']), cell(c['value']), cell(clean_desc(c['desc']))))
o.write('\n')

open('guide_part1.md', 'w', encoding='utf-8').write(o.getvalue())
print('part1 chars:', len(o.getvalue()))

const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {commands: commandsArray, params: parametersArray, sn: snArray, bugs: (typeof bugsArray!=="undefined"?bugsArray:null)};');
const r = fn();
const { commands, params, sn } = r;

const clean = s => String(s == null ? '' : s)
  .replace(/<br\s*\/?>/gi, ' ')
  .replace(/<[^>]+>/g, '')
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;?/g, ' ')
  .replace(/\s+/g, ' ').trim();

const mn = c => '(' + c.commandName + (c.commandParameters.length ? ' ' + c.commandParameters.map(p =>
  (p.dir && p.type ? p.dir + ':' : '') + p.name).join(' ') : '') + ')';

const sig = c => c.commandParameters.length
  ? '(' + c.commandName + ' ' + c.commandParameters.map(p => '<' + p.name + '>').join(' ') + ')'
  : '(' + c.commandName + ')';

const esc = s => clean(s).replace(/\|/g, '\\|');

// ---------- Category counts
const catCount = {};
for (const c of commands) for (const k of c.commandCategory) catCount[k] = (catCount[k] || 0) + 1;
const typeCount = {};
for (const c of commands) typeCount[c.commandType] = (typeCount[c.commandType] || 0) + 1;
const verCount = {};
for (const c of commands) verCount[c.commandVersion] = (verCount[c.commandVersion] || 0) + 1;

const upCmds = commands.filter(c => c.commandName.startsWith('up-'));
const ccCmds = commands.filter(c => c.commandName.startsWith('cc-'));
const feCmds = commands.filter(c => c.commandName.startsWith('fe-'));
const xsCmds = commands.filter(c => c.commandName.startsWith('xs'));

// ---------- Write raw text dumps
const rawCmd = commands.map(c => [
  '=== ' + c.commandName,
  'Type: ' + c.commandType + ' | Version: ' + c.commandVersion + ' | Complexity: ' + c.complexity,
  'Category: ' + c.commandCategory.join(', '),
  'Syntax: ' + mn(c),
  'Short: ' + clean(c.shortDescription),
  'Description: ' + clean(c.description),
  'Parameters:',
  ...c.commandParameters.map((p, i) => '  ' + (i + 1) + '. ' + p.name + ' [dir=' + p.dir + ' type=' + p.type + '] range=' + clean(p.range) + ' :: ' + clean(p.note)),
  'Example: ' + (c.example || []).map(e => clean(e.title) + ' || ' + clean(e.data)).join(' ;; '),
  ''
].join('\n')).join('\n');
fs.writeFileSync(dir + 'raw_ai_commands_full.txt', rawCmd);

const rawParams = params.map(p => [
  '=== ' + p.upParamName + ' [version=' + p.paramVersion + ']',
  'Short: ' + clean(p.shortDescription),
  'Description: ' + clean(p.description),
  'Range: ' + clean(p.range),
  'Prefixes: ' + JSON.stringify(p.prefixTypes) + ' | Operators: ' + JSON.stringify(p.operatorTypes) + ' | RuleVars: ' + JSON.stringify(p.ruleVariables),
  'Values:',
  ...p.valueList.map(v => '  ' + v.name + ' = ' + v.id + ' :: ' + clean(v.description)),
  ''
].join('\n')).join('\n');
fs.writeFileSync(dir + 'raw_ai_parameters_full.txt', rawParams);

const rawSn = sn.map(s => [
  '=== SN ' + s.id + ' ' + s.snName,
  'Category: ' + s.category + ' | min=' + s.min + ' max=' + s.max + ' rmin=' + s.rmin + ' rmax=' + s.rmax + ' default=' + s.default,
  'effective=' + s.effective + ' network=' + s.network + ' defined=' + s.defined + ' available=' + s.available,
  'aoe=' + s.aoe + ' aoc=' + s.aoc + ' up=' + s.up + ' de=' + s.de,
  'Short: ' + clean(s.shortDescription),
  'Description: ' + clean(s.description),
  ''
].join('\n')).join('\n');
fs.writeFileSync(dir + 'raw_ai_sns_full.txt', rawSn);

// ---------- Build the Markdown
const L = [];
const P = s => L.push(s);

P('# AoE2 DE AI Scripting — AIREF Reference Extract');
P('');
P('Source: <https://airef.github.io/> (AoE2 AI Scripting Encyclopedia). Machine-extracted from `js/commands.js`');
P('(the data file behind `commands-index.html`, `parameters-index.html`, `sn-index.html`) plus the site\'s guide articles.');
P('All identifiers and argument ORDER are preserved verbatim from the site data.');
P('');
P('| Extracted dataset | Count |');
P('|---|---|');
P('| Commands (`commandsArray`) | ' + commands.length + ' |');
P('| Parameters (`parametersArray`) | ' + params.length + ' |');
P('| Strategic Numbers (`snArray`, "active"/documented) | ' + sn.length + ' |');
P('');
P('### Command type breakdown');
P('');
P('| Type | Count |');
P('|---|---|');
for (const k of Object.keys(typeCount).sort()) P('| ' + k + ' | ' + typeCount[k] + ' |');
P('');
P('### Command version breakdown');
P('');
P('| Version | Count |');
P('|---|---|');
for (const k of Object.keys(verCount).sort()) P('| ' + k + ' | ' + verCount[k] + ' |');
P('');
P('### Command category breakdown');
P('');
P('| Category | Count |');
P('|---|---|');
for (const k of Object.keys(catCount).sort()) P('| ' + k + ' | ' + catCount[k] + ' |');
P('');
P('Prefix families: `up-*` = ' + upCmds.length + ', `cc-*` = ' + ccCmds.length + ', `fe-*` = ' + feCmds.length + ', `xs-*` = ' + xsCmds.length + '.');
P('');
P('---');
P('');

// ===== 1. LANGUAGE STRUCTURE
P('## 1. Language structure');
P('');
P('### 1.1 File roles: `.ai` marker vs `.per` payload');
P('');
P('| Extension | Role |');
P('|---|---|');
P('| `.ai` | The **marker/loader stub**. Filename must match the AI name (`MyAI.ai`) and lives in `AI/` in the game folder. It is a small file containing the load directives that pull in the `.per` payload(s). |');
P('| `.per` | The **payload** — the actual rule/constant/global program (from "Per" = the AoE AI personality language). Large AI files are split into many `.per` files chained by `load`. |');
P('| `.xs` | XS (AoE2 scripting) source, loaded by scenario triggers or by the AI via `xs-script-call`; not part of `.per` parsing. |');
P('');
P('A `.ai` file is a `.per` file in every respect (same grammar, same directives); "`.ai`" is the conventional name of the entry point the game picks up.');
P('The game resolves the AI by name, so `MyAI.ai` is the file to select in the lobby.');
P('');
P('### 1.2 Top-level (non-rule) sections');
P('');
P('These are the file-organization constructs. They are **not** enclosed in a `defrule` and are processed by the loader at parse time, not at game-tick time.');
P('');
P('| Construct | Syntax (exact) | Meaning |');
P('|---|---|---|');
P('| `defconst` | `(defconst <name> <value>)` | Declares a named compile-time constant. Substituted numerically where used. Used for goal ids, SN ids, `c:` values, object ids, etc. |');
P('| `defglobal` | `(defglobal <name> <value>)` | Declares a global variable usable as a goal/SN alias in expressions. |');
P('| `load` | `(load "<file>")` or `(load "file")` | Loads another `.per` file, unconditionally, in place. |');
P('| `load-random` | `(load-random <p1> "<f1>" <p2> "<f2>" ...)` | Loads exactly one of the listed files, picked at random with the given weights/probabilities. |');
P('| `include` | `(include "<file>")` | Include a file; semantics follow the engine\'s per-line include handling. |');
P('| `#load-if-defined` | `#load-if-defined <SYMBOL>` … `#else` … `#end-if` | Conditional compilation, keyed on a **LoadIf symbol** — a text token, not a `defconst`. |');
P('| `#load-if-not-defined` | `#load-if-not-defined <SYMBOL>` … `#else` … `#end-if` | Negated form of the above. |');
P('| `#else` | `#else` | Alternate branch inside a load-if block. |');
P('| `#end-if` | `#end-if` | Closes every `#load-if-*` block. **Mandatory** — a missing `#end-if` is a compile error. |');
P('');
P('Load-if symbols are a separate namespace (see `tables/load-if.html`); they come from the map/game configuration (e.g. the example in the site data uses `POCKET-POSITION` and `POST-IMPERIAL-AGE-START`).');
P('');
P('### 1.3 Rules');
P('');
P('```');
P('(defrule');
P('    <fact>            ; zero or more facts (conditions)');
P('    <fact>');
P('=>');
P('    <action>          ; zero or more actions');
P(')');
P('```');
P('');
P('- `(defrule` opens a rule; the closing `)` terminates it. Facts come first, actions after the arrow.');
P('- `=>` is the **mandatory** separator between the fact block and the action block. Without it the rule is not a rule.');
P('- Every command — fact or action — is wrapped in its **own** parentheses, nested inside the `defrule` parentheses.');
P('- `(true)` is the canonical always-true fact, used for a rule that should always fire.');
P('- `(disable-self)` as an action permanently disables the rule after it has run once (the standard "run-once" idiom).');
P('- **Rule ordering / priority**: for standard AI, rules are evaluated in the order they appear in the loaded file, and the first rule whose facts are all true executes its actions. This is why `load` order is meaningful and why `disable-self` / `set-goal` gating is used to sequence behaviour. (The UP/DE extension set adds explicit prioritization via the rule-priority XS functions, which the site flags as unsuitable for AI use.)');
P('- **Command limit per rule**: 32 commands per rule in AoC; **16** in UserPatch (stated in the Logical Operator Commands guide: "Like other commands, logical operator commands count toward the 32 command limit per rule (in UP the limit is 16 commands per rule)").');
P('');
P('### 1.4 Facts vs actions vs Fact/Action');
P('');
P('| Command type | Semantics (verbatim from the site) |');
P('|---|---|');
P('| **Fact** | "The command is a condition that must be true for the actions in the rule to be executed." |');
P('| **Action** | "The command will execute if all the facts in the rule are true." |');
P('| **Fact/Action** | "This command can be used as a fact or an action. When used as a fact, it will attempt to execute as an action even though it\'s in the fact section of the rule. If the action cannot be executed, then it will return false, and all following commands in the rule will not execute." |');
P('| **Other** | "This command is neither a fact, nor an action." (covers `defconst`, `defrule`, `#load-if-*`, logical operators, etc.) |');
P('');
P('The Fact/Action behaviour is the key idiom of the UP extension set: putting `(up-research ...)` or `(up-train ...)` in the fact block makes it a *guarded* action.');
P('');
P('### 1.5 Comments');
P('');
P('AI files use `;` for line comments (comment runs to end of line) — the standard convention shown throughout AIREF examples. Comments are stripped at compile time; they do not count toward the per-rule command limit.');
P('');
P('### 1.6 Parameters and prefix grammar');
P('');
P('Every parameter in a command signature is written with a **direction prefix** and a **type prefix** in the reference (`dir:Type`), and the concrete value you supply obeys the type.');
P('');
P('| Direction | Meaning (verbatim) |');
P('|---|---|');
P('| `in` | "An input. The parameter provides information for the command to use." |');
P('| `out` | "An output. Most of the time an output parameter is a goal that stores information that the command found." |');
P('| `io` | "Both an input and an output. The command uses the information in this parameter, and it stores information in this parameter when the command is finished. Most of the time this is a goal." |');
P('');
P('| Type | Meaning (verbatim) |');
P('|---|---|');
P('| `Const` | "the parameter must be a constant." |');
P('| `Goal` | "the parameter must be a goal." |');
P('| `Sn` | "the parameter must be a strategic number." |');
P('| `Op` | "the parameter must match the preceeding operator type … If the operator is a constant operator, then the parameter must be a constant. Likewise, if the operator is a goal operator, it must be a goal, and if the operator is a strategic number operator it must be a strategic number." |');
P('| `Player` | "the parameter must be a type of player." |');
P('| `Text` | "the parameter must be text within quotation marks." |');
P('');
P('### 1.7 The `c:` / `g:` / `s:` value-type operators');
P('');
P('These are the single most important syntactic detail of the language.');
P('');
P('| Prefix | Applies to | Meaning |');
P('|---|---|---|');
P('| `c:` | constants | "You can add a `c:` in front to specify that you\'re comparing constants, like `c:>` **but it\'s not necessary**. `>` means the same thing as `c:>`." |');
P('| `g:` | goals | "add a `g:` in front like this: `g:>`" — compares the value stored in the named goal. |');
P('| `s:` | strategic numbers | "add a `s:` in front like this: `s:>`" — compares the SN\'s value. |');
P('');
P('**Asymmetry that must not be misremembered**: for `compareOp`, the `c:` prefix is optional (`>` == `c:>`). For `mathOp`, "**Unlike compareOp, the `c:` prefix is necessary.**" (`c:+` adds a constant; `+` alone is not valid where a mathOp is expected).');
P('');
P('`typeOp` is exactly the set `{c:, g:, s:}` — it exists to tell the engine how to treat the *next* parameter (constant / goal / strategic number).');
P('');
P('### 1.8 How the AI engine compiles the source');
P('');
P('From *Defconsts, Goals, and SNs — Part 1*: the AI engine converts the whole script to strictly numeric code at load/compile time and error-checks it. Worked example given on the site:');
P('');
P('```');
P('(players-unit-type-count any-enemy archer == 5)');
P('  -> archer => 4 (object id)');
P('  -> any-enemy => -106 (player-number id, a wildcard)');
P('  -> == => 4 (comparison-symbol id)');
P('= (players-unit-type-count -106 4 4 5)');
P('```');
P('');
P('Consequences for tooling:');
P('- English names and their numeric ids are **interchangeable** in source ("you can always use -106 instead of any-enemy throughout your own AI code").');
P('- Command identity is positional: "each command is built with an expected order of parameters" — the engine knows `4` is an archer in slot 2 and an `==` in slot 3 *because of the slot*, not the token. A generator/analyzer must therefore know each command\'s **exact signature and argument order**.');
P('- Command names themselves have internal numeric ids but **no public documentation of those ids exists**, and it is unclear whether the engine accepts a number in place of a command name.');
P('');
P('---');
P('');

// ===== 2. COMMAND LIST
P('## 2. Command catalogue');
P('');
P('Syntax strings use `<Name>` for each parameter **in exact declared order**.');
P('Read the per-command tables as `dir:Type ParameterName` — that is the engine\'s positional contract.');
P('');
P('### 2.1 All commands, alphabetical (name / type / version / syntax / short description)');
P('');
P('| Command | Type | Ver | Syntax | Short description |');
P('|---|---|---|---|---|');
const sorted = [...commands].sort((a, b) => a.commandName.localeCompare(b.commandName));
for (const c of sorted) {
  P('| `' + c.commandName + '` | ' + c.commandType + ' | ' + c.commandVersion + ' | `' + mn(c).replace(/\|/g, '\\|') + '` | ' + esc(c.shortDescription) + ' |');
}
P('');

// ===== 3. UP EXTENSION CATALOGUE
P('## 3. The `up-*` extension catalogue (UserPatch / DE)');
P('');
P('`up-*` commands are the UserPatch extension set, carried into DE. They are the primary tooling surface.');
P('Each row gives the exact positional signature. `dir:Type` follows the site\'s own prefix notation.');
P('');
for (const c of upCmds.sort((a, b) => a.commandName.localeCompare(b.commandName))) {
  P('### `' + c.commandName + '`');
  P('');
  P('- **Type:** ' + c.commandType + '  **Version:** ' + c.commandVersion + '  **Complexity:** ' + c.complexity);
  P('- **Categories:** ' + (c.commandCategory.length ? c.commandCategory.join(', ') : '(none)'));
  P('- **Syntax:** `' + mn(c) + '`');
  if (c.commandParameters.length) {
    P('');
    P('| # | Parameter | dir | Type | Range | Note |');
    P('|---|---|---|---|---|---|');
    c.commandParameters.forEach((p, i) => {
      P('| ' + (i + 1) + ' | `' + p.name + '` | ' + p.dir + ' | ' + p.type + ' | ' + esc(p.range) + ' | ' + esc(p.note) + ' |');
    });
  }
  const desc = clean(c.description) || clean(c.shortDescription);
  if (desc) { P(''); P('> ' + desc); }
  if (c.example && c.example.length) {
    // NOTE: example.data is HTML-escaped in source; unescape
    P('');
    for (const e of c.example) {
      P('*Example — ' + clean(e.title) + '*');
      P('');
      P('```');
      P(String(e.data).replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\r\n/g, '\n').trim());
      P('```');
    }
  }
  P('');
}
P('---');
P('');

// ===== 4. PARAMETERS
P('## 4. Parameter reference');
P('');
P('`parametersArray` holds ' + params.length + ' parameter *types*. Each has an operator/prefix contract and often a closed `valueList` of named constants with numeric ids.');
P('');
P('### 4.1 Parameter index');
P('');
P('| Parameter | Version | Range | Short description |');
P('|---|---|---|---|');
for (const p of [...params].sort((a, b) => a.upParamName.localeCompare(b.upParamName))) {
  P('| `' + p.upParamName + '` | ' + p.paramVersion + ' | ' + esc(p.range) + ' | ' + esc(p.shortDescription) + ' |');
}
P('');
P('### 4.2 Parameter details + value lists');
P('');
for (const p of [...params].sort((a, b) => a.upParamName.localeCompare(b.upParamName))) {
  P('#### `' + p.upParamName + '`');
  P('');
  const d = clean(p.description) || clean(p.shortDescription);
  if (d) P('> ' + d);
  P('');
  const meta = [];
  if (p.range && clean(p.range) !== '') meta.push('**Range:** ' + clean(p.range));
  if (p.prefixTypes && p.prefixTypes.length) meta.push('**Prefixes:** `' + p.prefixTypes.join('`, `') + '`');
  if (p.operatorTypes && p.operatorTypes.length) meta.push('**Operators:** `' + p.operatorTypes.join('`, `') + '`');
  if (p.ruleVariables && p.ruleVariables.length) meta.push('**Rule variables:** `' + p.ruleVariables.join('`, `') + '`');
  if (meta.length) { P(meta.join('  \n')); P(''); }
  if (p.valueList && p.valueList.length) {
    P('| Name | ID | Description |');
    P('|---|---|---|');
    for (const v of p.valueList) P('| `' + v.name + '` | ' + v.id + ' | ' + esc(v.description) + ' |');
    P('');
  }
}
P('---');
P('');

// ===== 5. SNs
P('## 5. Strategic Numbers');
P('');
P('Site facts (verbatim, from `sn-index.html`):');
P('');
P('> "There are a total of 512 strategic numbers, numbered 0 to 511, that the game has made available, but currently there are only about 300 of them being used. The other 200 or so strategic numbers are not listed in the table below, and they can be used like extra goals."');
P('');
P('> "It\'s recommended to start with strategic number ID 510 (SN ID 511 currently has some bugs in DE) and work your way descending in ID until you reach the active strategic numbers, because DE can continue to add strategic numbers to the game and you don\'t want your custom strategic number to conflict with it."');
P('');
P('> "If a strategic number is set outside of the Min/Max ranges, then the game will automatically modify the value to be within this range. The Req. Min and Req. Max ranges specify which range of values work for the strategic number."');
P('');
P('Tables list **Min/Max** (clamp range) and **Req. Min/Req. Max** (the range in which the SN actually works). Where a source column says "Min"/"Max", the absolute limits are **-2,147,483,648** and **2,147,483,647**.');
P('');
P('Flags columns: **Effective** (does it affect behaviour at all — several are AoE1 holdovers/never implemented), **Network** (is it synced over the network), **Defined** (is the name predefined in the engine, i.e. usable without a `defconst`), **Active** (Active / Conditional / Obsolete — whether it can be reused as an "extra goal").');
P('');
P('`sn-*` names are usable directly as parameters; `(set-strategic-number <sn-name> <value>)` is the canonical writer and SN names are readable in `s:` expressions.');
P('');
P('| ID | SN name | Min | Max | Req.Min | Req.Max | Default | Eff | Net | Def | Active | Versions (AoE1,AoC,UP,DE) |');
P('|---|---|---|---|---|---|---|---|---|---|---|---|');
for (const s of [...sn].sort((a, b) => a.id - b.id)) {
  const act = (typeof s.available === 'string') ? 'Conditional' : (s.available === 0 ? 'Active' : 'Obsolete');
  P('| ' + s.id + ' | `' + s.snName + '` | ' + s.min + ' | ' + s.max + ' | ' + s.rmin + ' | ' + s.rmax + ' | ' + s.default + ' | ' + s.effective + ' | ' + s.network + ' | ' + s.defined + ' | ' + act + ' | ' + s.aoe + ',' + s.aoc + ',' + s.up + ',' + s.de + ' |');
}
P('');
P('### 5.1 SN descriptions (documented SNs only)');
P('');
for (const s of [...sn].sort((a, b) => a.id - b.id)) {
  const d = clean(s.description) || clean(s.shortDescription);
  if (d) P('- **SN ' + s.id + ' `' + s.snName + '`** (' + s.category + '): ' + d);
}
P('');
P('---');
P('');

// ===== 6. XS
P('## 6. AI ↔ XS interface');
P('');
P('XS functionality was extended to AI scripting in AoE2:DE. Per the guide *XS Scripting for AI Tournaments*:');
P('');
P('- XS code is invoked from `.per` through the AI-side XS bridge; `xs-script-call` is the AI command that calls into a `.xs` function.');
P('- **AI Scripting Functions** exposed to XS, all permitted, and when called from a function invoked by `xs-script-call` they "will only get and set values for the current AI player":');
P('  `xsGetGoal`, `xsGetStrategicNumber`, `xsSetGoal`, `xsSetStrategicNumber`.');
P('- **No `my-player-number` equivalent exists in XS.** The documented workaround: store the AI\'s `my-player-number` in a goal, call an XS function via `xs-script-call`, and have the XS side read it with `xsGetGoal` to populate a global `myPlayerNumber` variable, then pass that as the `playerId` argument to every player-scoped XS function.');
P('- Global XS variables are "separately created for each player that loads the `.xs` file that creates them", so per-AI globals do not collide.');
P('- **XS rules must not be used in AI scripts**: "XS rules seem to function globally, independent of AI players, which can easily throw off any player-specific code the rules contain." Only variable-creating code should exist outside XS functions.');
P('- `xsSetContextPlayer` **must** be called before any File I/O function; the context player also affects `xsEffectAmount`.');
P('- `xsChatData` is described as "essentially `up-chat-data-to-self` and is the only debugging chat command available in XS".');
P('- File I/O functions (`xsOpenFile`, `xsWriteString`, `xsWriteInt`, `xsWriteFloat`, `xsWriteVector`, `xsReadString`, `xsReadInt`, `xsReadFloat`, `xsReadVector`, `xsOffsetFilePosition`, `xsCloseFile`, `xsGetFilePosition`, `xsGetDataTypeSize`, `xsGetFileSize`) write hex files, are unique per player, **overwritten each game**, and **you cannot specify a file name or save location**. `up-log-data` is recommended instead.');
P('- XS-only capabilities with no `.per` equivalent, flagged as useful to AI scripters: `xsGetGroupMoveTarget`, `xsGetGarrisonedInUnitId`, `xsGetGarrisonedUnitIds`, and (for tech research time/location) `xsGetTechAttribute`. Math functions (`sqrt`, trig) are also called out as hard to replicate in `.per`.');
P('');
P('### 6.1 XS functions flagged as cheating when used from AI scripts (verbatim list)');
P('');
P('| Category | Functions |');
P('|---|---|');
P('| Non-Functions | XS rules shouldn\'t be used |');
P('| All Rules Functions | `xsDisableRule`, `xsDisableSelf`, `xsEnableRule`, `xsIsRuleEnabled`, `xsSetRulePriority`, `xsSetRulePrioritySelf`, `xsSetRuleMinInterval`, `xsSetRuleMinIntervalSelf`, `xsSetRuleMaxInterval`, `xsSetRuleMaxIntervalSelf`, `xsEnableRuleGroup`, `xsDisableRuleGroup`, `xsIsRuleGroupEnabled` |');
P('| Techs Functions | `xsResearchTechnology` |');
P('| Player Functions | `xsEffectAmount`, `xsSetPlayerAttribute`, `xsDeclareVictory` |');
P('| Tasks Functions | `xsTaskAmount`, `xsResetTaskAmount`, `xsModifyObjectTasks`, `xsModifyUnitTasks`, `xsTask`, `xsRemoveTask` |');
P('| Units & Objects Functions | `xsCreateUnit`, `xsRemoveUnit`, `xsGetUnitOwner`, `xsSetUnitPosition`, `xsSetUnitHitpoints`, `xsSetUnitBuildPoints`, `xsSetUnitAttributeHeld`, `xsSetUnitCharge` |');
P('| Map Functions | `xsSetColorMood` |');
P('| UI Functions | `xsPlaySound`, `xsDisplayInstructions`, `xsClearInstructions`, `xsDisplayTimer`, `xsClearTimer`, `xsGetTimerRemaining` |');
P('');
P('### 6.2 Cheating only if used on *other* players (verbatim list)');
P('');
P('| Category | Functions |');
P('|---|---|');
P('| Techs Functions | `xsGetTechState`, `xsGetTechAttribute` |');
P('| Player Functions | `xsGetPlayerUnitIds`, `xsPlayerAttribute` |');
P('| Tasks Functions | `xsGetObjectTaskCount`, `xsObjectTaskCount`, `xsGetUnitTaskCount`, `xsUnitTaskAmount` |');
P('| Units & Objects Functions | `xsGetObjectAttribute`, `xsGetUnitAttribute`, `xsDoesUnitExist`, `xsGetUnitPosition`, `xsGetUnitName`, `xsGetObjectName`, `xsGetUnitTargetUnitId`, `xsGetUnitMoveTarget`, `xsGetUnitGroupId`, `xsGetGroupMoveTarget`, `xsIsObjectAvailable`, `xsGetUnitHitpoints`, `xsGetUnitBuildPoints`, `xsGetUnitObjectId`, `xsGetUnitCopyId`, `xsGetObjectCopyId`, `xsGetUnitClass`, `xsGetObjectClass`, `xsGetUnitType`, `xsGetUnitAttributeTypesHeld`, `xsGetUnitAttributeHeld`, `xsGetUnitCharge`, `xsGetGarrisonedInUnitId`, `xsGetGarrisonedUnitIds`, `xsGetObjectCount`, `xsGetObjectCountTotal`, `xsObjectHasAction`, `xsIsObjectValid`, `xsGetPlayerNumberOfObjects` |');
P('');
P('### 6.3 XS functions explicitly permitted in AI scripts (verbatim list)');
P('');
P('| Category | Functions |');
P('|---|---|');
P('| All Vector Functions | `xsVectorGetX`, `xsVectorGetY`, `xsVectorGetZ`, `xsVectorSetX`, `xsVectorSetY`, `xsVectorSetZ`, `xsVectorSet`, `xsVectorLength`, `xsVectorNormalize` |');
P('| All Array Functions | `xsArrayCreateInt`, `xsArrayCreateFloat`, `xsArrayCreateBool`, `xsArrayCreateString`, `xsArrayCreateVector`, `xsArraySetInt`, `xsArraySetFloat`, `xsArraySetBool`, `xsArraySetString`, `xsArraySetVector`, `xsArrayGetInt`, `xsArrayGetFloat`, `xsArrayGetBool`, `xsArrayGetString`, `xsArrayGetVector`, `xsArrayResizeInt`, `xsArrayResizeFloat`, `xsArrayResizeBool`, `xsArrayResizeString`, `xsArrayResizeVector`, `xsArrayGetSize` |');
P('| All Maths Functions | `abs`, `sqrt`, `pow`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `atan2v`, `exp`, `ceil`, `floor`, `bitCastToFloat`, `bitCastToInt`, `xsCeilToInt`, `ln`, `log2`, `log10`, `round`, `radians`, `degrees`, `dist`, `bitAnd`, `bitOr`, `bitXor`, `bitNot` |');
P('| All Randomization Functions | `xsGetRandomNumber`, `xsGetRandomNumberLH`, `xsGetRandomNumberMax` |');
P('| Techs Functions | `xsGetTechName` |');
P('| Player Functions | `xsGetHandicapMultiplier`, `xsGetWorldPlayerId`, `xsGetPlayerCivilization`, `xsGetPlayerInGame`, `xsGetPlayerNumberOfTechs`, `xsGetPlayerName`, `xsGetPlayerType`, `xsGetDiplomacy`, `xsSetDiplomacy`, `xsGetDifficulty` |');
P('| Tasks Functions | `xsGetTaskAmount` (if the stored task struct doesn\'t belong to another player) |');
P('| Map Functions | `xsGetMapName`, `xsGetMapId`, `xsGetMapHeight`, `xsGetMapWidth`, `xsGetColorMood`, `xsGetMapSeed` |');
P('| All Game Info Functions | `xsGetNumPlayers`, `xsGetTime`, `xsGetGameTime`, `xsGetTurn`, `xsGetVictoryType`, `xsGetVictoryPlayer`, `xsGetVictoryPlayerForSecondaryGameMode`, `xsGetVictoryTime`, `xsGetVictoryTimeForSecondaryGameMode`, `xsGetVictoryCondition`, `xsGetVictoryConditionForSecondaryGameMode` |');
P('| UI Functions | `xsChatData`, `xsGetPlayerColorTag` |');
P('| All File I/O Functions | `xsOpenFile`, `xsWriteString`, `xsWriteInt`, `xsWriteFloat`, `xsWriteVector`, `xsReadString`, `xsReadInt`, `xsReadFloat`, `xsReadVector`, `xsOffsetFilePosition`, `xsCloseFile`, `xsGetFilePosition`, `xsGetDataTypeSize`, `xsGetFileSize` |');
P('| All AI Scripting Functions | `xsGetGoal`, `xsGetStrategicNumber`, `xsSetGoal`, `xsSetStrategicNumber` |');
P('| Miscellaneous Functions | `xsGetContextPlayer`, `xsSetContextPlayer` |');
P('');
P('### 6.4 Use-with-care list (verbatim)');
P('');
P('| Category | Functions | Reason given |');
P('|---|---|---|');
P('| Array Functions | `xsArrayCreateInt`, `xsArrayCreateFloat`, `xsArrayCreateBool`, `xsArrayCreateString`, `xsArrayCreateVector`, `xsArrayResizeInt`, `xsArrayResizeFloat`, `xsArrayResizeBool`, `xsArrayResizeString`, `xsArrayResizeVector` | "can use excessive memory if not managed properly" |');
P('| Map Functions | `xsTriggerVariable`, `xsSetTriggerVariable` | "these functions only work in custom scenarios" |');
P('| UI Functions | `xsGetLocale`, `xsGetString`, `xsGetPlayerAttributeName`, `xsGetDamageClassName`, `xsGetLocalPlayerId`, `xsSendChat` | "can cause a desync in some situations because of language localization differences" |');
P('| Miscellaneous Functions | `xsDumpArrays`, `xsGetFunctionId`, `xsBreakPoint`, `xsAddRuntimeEvent` | "these apparently do nothing or are of little use to anyone besides devs" |');
P('');
P('---');
P('');

// ===== 7. TOOLING NOTES
P('## 7. Tool-relevant command groupings');
P('');
P('### 7.1 Rule/flow control ("Other" type)');
P('');
P('| Command | Syntax |');
P('|---|---|');
for (const c of commands.filter(c => c.commandType === 'Other' && (c.commandName.startsWith('#') || c.commandName === 'defrule' || c.commandName === 'defconst' || c.commandName === 'defglobal' || c.commandName === 'load' || c.commandName === 'load-random' || c.commandName === 'include'))) {
  P('| `' + c.commandName + '` | `' + mn(c) + '` |');
}
P('');
P('### 7.2 Logical operators');
P('');
for (const c of commands.filter(c => ['and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor'].includes(c.commandName))) {
  P('- `' + c.commandName + '` — ' + esc(c.shortDescription));
}
P('');
P('Truth table reproduced from the site (Logical Operator Commands):');
P('');
P('| Fact A | Fact B | and | nand | or | nor | xor | xnor |');
P('|---|---|---|---|---|---|---|---|');
P('| false | false | false | true | false | true | false | true |');
P('| true | false | false | true | true | false | true | false |');
P('| false | true | false | true | true | false | true | false |');
P('| true | true | true | false | true | false | false | true |');
P('');
P('`not` takes exactly one nested fact. Nesting is supported; each nested logical operator counts as a single fact. Logical operators count toward the per-rule command limit.');
P('');
P('### 7.3 Economy / training / building / research / attack (core AoC actions)');
P('');
for (const name of ['build', 'train', 'research', 'attack-now', 'set-strategic-number', 'set-goal', 'chat-to-all', 'chat-to-allies', 'chat-to-enemies', 'chat-to-player', 'chat-to-self', 'disable-self', 'buy-commodity', 'sell-commodity', 'build-wall', 'build-gate', 'build-forward', 'train', 'research', 'up-target-point', 'up-find-local', 'up-find-remote', 'up-find-for', 'up-find-player', 'up-filter-status', 'up-filter-distance', 'up-filter-type', 'up-filter-include', 'up-filter-exclude', 'up-filter-reset', 'up-find-status-local', 'up-find-status-remote']) {
  const c = commands.find(x => x.commandName === name);
  if (c) P('- `' + mn(c) + '` — ' + esc(c.shortDescription));
}
P('');
P('### 7.4 Complete alphabetised command-name list');
P('');
P('```');
let line = '';
for (const c of sorted) {
  if ((line + c.commandName).length > 100) { P(line.trim()); line = ''; }
  line += c.commandName + '  ';
}
if (line.trim()) P(line.trim());
P('```');
P('');

fs.writeFileSync(dir + 'AI_SCRIPTING_AIREF.md', L.join('\n'));
console.log('Wrote AI_SCRIPTING_AIREF.md', L.join('\n').length, 'chars');
console.log('up-* count', upCmds.length, 'params', params.length, 'sn', sn.length);

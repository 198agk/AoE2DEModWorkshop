# Suite audit — can these tests fail?

Scope: the 73 suites registered in `_probe/run_suites.py` plus all 10 files in
`aoe2mod/tests/`. Read-only; nothing in `aoe2mod/` or `_probe/` was modified.
Every mutation ran against a throwaway copy of the product tree under
`_probe/team/suite-auditor/scratch/`, never against the real source.

---

## VERDICT: THIN

Most load-bearing claims are real — 15 of 24 deliberate bugs were caught — but the
green aggregate is not the reason: one registered suite exits 0 while asserting
nothing, thirteen assertions are constant-true (twelve `check(True)` / `... or True`
plus one literal-vs-literal comparison),
`verify_surgical`'s `ok` is true by construction at all three of its call sites, and
nine mutants (including a no-op `tech.effect` write and a broken sprite id index)
survived a full-green run.

---

## Suite run

Command, run to completion in the background (10:55 → 11:31, ~36 min):

```
python -X utf8 _probe/run_suites.py > _probe/team/suite-auditor/suites.txt 2>&1
```

**Exact final line:**

```
SUITES: ALL PASSED
```

73 suites, **73 lines with `exit=0`, zero non-zero exits.** The runner's own
predicate is `bad = p.returncode != 0 or _FAIL_RE.search(out)`, with
`_FAIL_RE = re.compile(r"\bFAIL(?:ED|URE)?\b")`, so no suite produced either signal.
Per-suite exits are in `_probe/team/suite-auditor/suite_exits.txt` (73 rows,
`name|exit|tail`), produced from `suites.txt`.

The three lines that match `\bFAIL` are all innocent:

| line | suite | why it is not a failure |
|---|---|---|
| `exit=0  ... because the game fails to start without it -- as the user reported twice.` | `test_dat_carrier.py` | the word "fails" is prose about the game |
| `exit=0  BUNDLE DAT HALF: 0 failure(s)` | `test_bundle_dat_half_e2e.py` | "0 failure(s)" |
| `exit=0  NOT PROVEN: ... it is a UI-level failure that appears ...` | `probe_install_safety.py` | a scope note |

**The aggregate cannot distinguish "passed" from "skipped".** The line

```
test_smoke5_design.py                          exit=0    (no artifact, so the design is unverified, not disproven)
```

is a `sys.exit(0)` taken before a single assertion, inside a suite the gate counts
as passing (see finding 15). Two more suites are artifact-gated the same way in
shape (`aoe2mod/tests/test_product_v7_recipe.py:75`), and that one happened to run
only because `D:\Games\Steam\steamapps\common\AoE2DE` exists here.

Not in this gate at all: `aoe2mod/tests/test_roundtrip.py` (the 5-file byte-exact
`.dat` round trip) and all of `_probe/run_long.py`'s suites. Of 441 `test_*`/
`probe_*` files under `_probe/`, **73 are registered and 369 are not**; the 16
unregistered `test_*` files include `test_plan_matches_build.py`, `test_repaint.py`
and `test_retarget.py` — the plan/build agreement sweep and the only end-to-end
`unit.art` and retarget suites.

---

## Tests that cannot fail

Each entry is quoted verbatim from the file at the cited line.

**1. `_probe/test_panel_edit.py:73`**

```python
check("British" in json.dumps(_obj) or True, "sanity: object loads")
```

`X or True` is `True` for either value of `X`; the `check()` helper only marks a
failure when its `ok` argument is false. The left operand is also *false* in fact —
the file's own note at `:77-80` records that the panel keys civs by `"Britons"`,
not `"British"` — so the `or True` suppresses a genuine wrong-answer as well as
being unfalsifiable.

**2. `_probe/probe_bundle_dat_half.py:131-132`**

```python
check("A alone: manifest does not claim a carrier when it shipped a grant",
      not (raw_a == base_raw) or True)
```

`not X or True` ≡ `True`. This is the same defect shape as the historical
`assert gone == back[...] or True`— here the *conclusion the label states* (the
manifest does not claim a carrier) is never inspected at all; the neighbouring
`:129` check and this one are the only claims about the shipped grant `.dat`.

**3. `_probe/probe_install_safety.py:156-162`** — both arms tautological

```python
if 5 in _units_of(_mobj, "Britons", 87):
    check(True, "the mod's copy ALSO gives Britons Hand Cannoneer at the Range")
else:
    check(5 not in _units_of(_mobj, "Britons", 87),
          "this mod does not touch the Hand Cannoneer entry (so no contrast "
          "is available for it here -- that is a fact about the artifact, "
          "not a failure)")
```

The `if` arm passes a literal `True`; the `else` arm asserts the negation of the
guard that just evaluated false. Whichever branch runs, the check cannot fail — and
it is labelled `PASS`. The comment at `:150-155` shows the author knew the
assertion had become vacuous.

**4. `_probe/test_dat_json_override.py:91`**

```python
check(True, "the corpus was enumerated")
```

Literal `True`. The enumeration happened at `:88-90` and its result printed; nothing
about it is asserted. The suite's only real assertion is `:113`.

**5. `_probe/test_dat_json_override.py:165`**

```python
check(True, "every shipped dat-layer JSON was compared against the base game's copy")
```

Literal `True`, and the label claims the strongest result in the file ("*every*
... was compared") while asserting nothing about any comparison.

**6. `_probe/test_mod_load_timing.py:140`**

```python
check("the log-position fact is reported without asserting a direction", True)
```

`check(<label>, True)`. The label itself states that no direction is asserted; the
check then "passes" on the strength of that statement.

**7. `_probe/test_time_gate_and_tooltip.py:138-139`**

```python
check("explanation 3 is supported by the file carrying prereq display fields",
      True)
```

**8. `_probe/test_time_gate_and_tooltip.py:146-147`**

```python
check("the panel is at most 0.6% different from the tree",
      True)
```

Both encode a conclusion reached earlier by measurement, then assert `True`. The
0.6% figure is a hard-coded number that no longer touches the data; a regression
that made the panel 60% different would still print PASS.

**9. `_probe/test_smoke6_result.py:113`**

```python
check("the smoke6 artifact is installed", True)
```

The suite exists to report on an in-game run; "the artifact is installed" is the
precondition of everything after it and is asserted as a constant. `_find_installed`
at `:74-92` computes the real answer and the result is discarded here.

**10. `_probe/test_smoke6_result.py:211-212`**

```python
check("2550 carries no enabling research at all (so that mechanism is not it)",
      True)
```

Literal `True` on a claim about `.dat` bytes that the suite's own earlier section
could have read.

**11. `_probe/test_zero_mod_experiment.py:268`**

```python
check("the injective answer is therefore a TWO-GAME protocol", True)
```

Literal `True`; "therefore" marks it as a deduction from the preceding check, but
the deduction is never computed.

**12. `_probe/test_protocol_subjects.py:257-258`**

```python
check("the two subjects are not name-colliding",
      "精锐炮舰" != "重型投石车")
```

Two hard-coded string literals compared to each other. This is a constant
expression: it is `True` before, during and after any product change. It cannot
fail and it tests nothing.

**13. `aoe2mod/tests/test_buildpanel.py:94-99`**

```python
try:
    BP.insert_entry(after, key, bldg, entry)
    check(False, "a second identical insert raises PanelError")
except BP.PanelError as e:
    check(True, "a second identical insert raises PanelError",
          str(e)[:70])
```

The failure signal is `check(False, ...)` *not running*; the success signal is a
literal `True`, carrying no information. The pair as a whole does discriminate (a
silent duplicate fails via the `check(False, ...)`), so this is a weak-assertion
finding rather than a free pass — but the `check(True)` line is what a reader and a
`check()`-counting tool both see, and it is the same defect shape as entries 1–12.

**14. `aoe2mod/game/buildpanel.py:478-485` — `ok` is true by construction at every call site**

```python
    info["outside_is_untouched"] = (
        before_text[:p] == after_text[:p]
        and before_text[len(before_text) - s:] == after_text[len(after_text) - s:])
    ok = info["outside_is_untouched"]
```

`p` and `s` were found by scanning forward/backward for exactly that equality
(`:466-472`), so both conjuncts are true for *any* pair of strings. The only real
signal is the optional `inserted_chars` arm at `:482-484`, and no caller passes it:

- `aoe2mod/tests/test_buildpanel.py:74` `ok, info = BP.verify_surgical(text, after)`
- `aoe2mod/tests/test_buildpanel.py:107` `ok, info = BP.verify_surgical(after, back)`
- `_probe/test_panel_wire.py:95` `ok_s, info = BP.verify_surgical(shipped_txt, txt2)`

Direct proof (read-only import of the real product): `verify_surgical("", "")`,
`verify_surgical("a", "b")` and `verify_surgical("AAAA"*100, "ZZZZ")` all return
`ok=True, outside_is_untouched=True`; `ok` only becomes `False` when
`inserted_chars=99` is supplied. So the two assertions built on it —
`check(ok and info["inserted"] > 0, "everything outside one contiguous insertion is
unchanged")` (`test_buildpanel.py:75`) and `check(ok and info["kind"] == "delete",
"removal also moved only a contiguous region")` (`:108`) — reduce to the
`inserted`/`kind` half. Confirmed empirically by mutations m01 and m21, which
replace the line with `ok = True` and are not noticed by either caller.

**15. `_probe/test_smoke5_design.py:60-63` — a registered suite that is green today while asserting nothing**

```python
if not os.path.isdir(OUT):
    print("SMOKE5 DESIGN: SKIP -- %s is not built" % OUT)
    print("  (no artifact, so the design is unverified, not disproven)")
    sys.exit(0)
```

`OUT = os.path.join(HERE, "out_smoke5")` (`:43`); that directory does not exist on
this machine. Re-run in a pristine copy: exit 0, tail
`SMOKE5 DESIGN: SKIP -- ...out_smoke5 is not built`. The runner counted it in
`SUITES: ALL PASSED`. This is the "no diff assertion whose glob matched zero files"
shape, in its strongest form: the whole file skips.

**16. `_probe/test_dat_layer_override.py:132-133` — a guard that re-tests the line above it**

```python
check(os.path.isfile(AGG_POMPEII), "Pompeii ships one")
if os.path.isfile(AGG_POMPEII):
    check(os.path.getsize(AGG_POMPEII) == 1671526, "it is 1,671,526 B", ...)
```

The `if` condition is the assertion immediately preceding it, so it can only be
false when the suite has already recorded a failure — while if the file is absent
the five checks it guards (`:134`, `:137`, `:139`, `:142`, and the `:132` line
itself) simply never run, and the suite still exits 0.

**17. `_probe/test_panel_tree_agreement.py:207` — the only mtime assertion is optional, with no else**

```python
if len(mt) == 3:
```

`mt` is built from three paths (`futuravailableunits.json`, `Sicilians.json`,
`AoE2DE_s.exe`); if any is missing the guarded check — "the panel file is OLDER than
the engine that reads it" — silently disappears, and there is no `else` recording
the skip.

**18. `_probe/test_unit_sprite_chain.py:35` + `:151-152` — a glob that can match zero files**

```python
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))
...
check("all loose .sld files on disk come in x1/x2 pairs",
      not _pair_bad, "%d unpaired files on disk" % len(_pair_bad))
```

If `GP` were empty or absent, `_on_disk` is empty, `_pair_bad` is empty and the
`not _pair_bad` assertion passes vacuously while the detail string prints
`0 unpaired files on disk`. (Mitigating: other sections of the same file do count
against `_on_disk`, and on this machine the directory is populated.)

**19. `_probe/probe_bundle_dat_half.py:139-140` — a length comparison standing in for a byte comparison**

```python
check("B: the villager edit is also there",
      len(raw_b) != len(base_raw))
```

Any same-length corruption satisfies it; a wrong edit that preserves file size is
invisible.

**Not defects (checked and cleared).** `_probe/test_dat_carrier.py:126`,
`_probe/test_tech_availability_e2e.py:182/187`, `_probe/test_zero_mod_experiment.py:187`,
`aoe2mod/tests/test_availability_intent.py:82/88/191/197/213/218`,
`aoe2mod/tests/test_civtechtrees.py:132` and
`aoe2mod/tests/test_product_v7_recipe.py:123/138/165/193/207/235` are all
`check(False, ...)` inside `except`/error arms — deliberate forced failures, the
correct pattern. `except ...: pass` at `_probe/test_revoke_is_not_enough.py:118`
and `_probe/test_enabling_research.py:71` wraps parsing helpers, not assertions.
No suite anywhere compares a float field to an unrounded float literal:
`aoe2mod/tests/test_api.py:603-606` (`encode_effect_value(8, 1025.0, 3) == 1027.0`,
`decode_effect_value(9, float(0x03C8)) == (200, 3)`) is arithmetic that is exact in
both binary32 and binary64, not the `2.4 != 2.4` trap.

---

## Mutation results

Method: `mutate.py` copies `_probe/team/suite-auditor/scratch/` (a pristine copy of
`aoe2mod/` + `_probe/`) to a fresh tree, applies **one** exact string replacement
(asserting the anchor occurs exactly once), runs the suite with
`cwd=<mutated root>` and a cleared `PYTHONPATH`, and records exit code. The suites
insert their own root into `sys.path`, so the mutated copy is what gets imported.
"No FAIL lines but a traceback" still counts as caught — the gate's own predicate is
`returncode != 0`.

| # | suite | mutation (file: line → edit) | still passed? | conclusion |
|---|---|---|---|---|
| m01 | `aoe2mod/tests/test_buildpanel.py` | `aoe2mod/game/buildpanel.py:481` `ok = info["outside_is_untouched"]` → `ok = True` | **YES (exit 0)** | `verify_surgical`'s verdict is dead at this call site |
| m02 | `aoe2mod/tests/test_buildpanel.py` | `buildpanel.py` `removed += 1` → `removed += 7` | no (exit 1) | removal count is really asserted |
| m03 | `aoe2mod/tests/test_availability_e2e.py` | `aoe2mod/game/civtechtrees.py` `grant()` append line duplicated | no (exit 1) | "exactly one row was appended" is real |
| m04 | `_probe/test_dat_half_count.py` | `aoe2mod/intent/datgrant.py` `patched[boff] = slot` → `patched[boff] = bbefore` | **YES (exit 0)** | the declared-count contract never checks that the bytes moved |
| m05 | `_probe/test_reskin.py` | `aoe2mod/game/sprites.py` `if a and b and a != b:` → `if False:` | no (exit 1) | `grid_mismatches` reporting is asserted |
| m06 | `_probe/test_mechanism_gate.py` | `civtechtrees.py` `can_build` → `return True` | no (exit 1) | `can_build` vs `has` distinction is pinned |
| m07 | `_probe/test_reskin.py` | `aoe2mod/intent/reskin.py:574` `rep["ok"] = not (...)` → `rep["ok"] = True` | **YES (exit 0)** | `verify_files` certifies without checking |
| m08 | `aoe2mod/tests/test_availability_e2e.py` | `civtechtrees.py` `return text.encode("utf-8")` → `+ "\n"` | **YES (exit 0)** | this suite moves both sides together; byte-exactness lives in a different suite |
| m09 | `aoe2mod/tests/test_availability_e2e.py` | `aoe2mod/mod/emitter.py:340` `"dat_is_carrier": dat_carrier` → `True` | **YES (exit 0)** | every mod could falsely claim a carrier `.dat` |
| m10 | `aoe2mod/tests/test_availability_intent.py` | `emitter.py` `manifest["changes_dat"] = ...` → `False` | no (exit 1) | `changes_dat` is really derived |
| m11 | `aoe2mod/tests/test_availability_e2e.py` | `civtechtrees.py` `if not found: return None` → `return "ResearchedCompleted"` | no — **crash**, not assertion | `AttributeError` in `_row_key`; caught only by exit code |
| m12 | `_probe/test_declared_resources.py` | `compiler.py` `new = (before + amount) if op == "delta" else amount` → `new = amount` | **YES (exit 0)** | that suite only checks the resource-name table |
| m13 | `_probe/test_dat_carrier.py` | `emitter.py` `"dat_is_carrier": dat_carrier` → `True` (+ `dat_identical_to_base`) | no (exit 1) | carrier flag is asserted here |
| m14 | `_probe/test_dat_half_count.py` | `datgrant.py` `report["edits"].append(...)` → `_ = (...)` | no (exit 1) | declared count equals the recipe's own count |
| m15 | `_probe/test_mechanism_gate.py` | docstring-only change (control) | yes, as required | harness reports on code, not on the patch |
| m16 | `_probe/test_dat_edit_routes.py` | `aoe2mod/dat/writer.py` `self.mismatches += 1` → `+= 0` | no (exit 1) | `model_vs_original_mismatches` is asserted (== 2) |
| m17 | `aoe2mod/tests/test_emit_mod.py` | `compiler.py` int delta → absolute | no (exit 1) | `assert after == [6]` catches it (traceback, 0 FAIL lines) |
| m18 | `_probe/test_unit_sprite_chain.py` | `sprites.py:200` `self._by_id.setdefault(g["id"], g)` → `setdefault(-1, g)` | **YES (exit 0)** | the suite builds its own `_by_id` at `:62` and never calls `SpriteIndex.record`/`file_of` |
| m19 | `aoe2mod/tests/test_buildpanel.py` | `buildpanel.py` `if _entry_spans(...)` → `if False:` | no (exit 1) | duplicate insert is refused and checked |
| m20 | `aoe2mod/tests/test_compiler.py` | `compiler.py` mirror slot `yield` → `continue` | no (exit 1) | the mirrored displayed-stat contract is asserted |
| m21 | `_probe/test_panel_wire.py` | `buildpanel.py:481` `ok = info["outside_is_untouched"]` → `ok = True` | **YES (exit 0)** | the *second* caller is equally blind |
| m22 | `aoe2mod/tests/test_api.py` | `compiler.py:546` `buf[off:off+4] = struct.pack("<f", row["stored"])` → `= data[off:off+4]` | **YES (exit 0)** | `tech.effect` is only ever *planned*, never written, by the one registered suite that invokes it |
| m23 | `aoe2mod/tests/test_compiler.py` | `compiler.py:1171` `if c.get("type") != want:` → `if False:` | no (exit 1) | caught by the `tech.cost` refusal case at `:250`. The `unit.cost` case printed `成本 wood: 25 -> 20` and passed under the mutation (Archer's first slot is wood by luck) |
| m24 | `aoe2mod/tests/test_compiler.py` | `compiler.py:1141` `locs = ... or ()` → `[:1]` | no (exit 1) | `assert rmulti["edit_count"] == 2` at `:212` |
| m25 | `aoe2mod/tests/test_compiler.py` | `compiler.py:1086` `which = resolved.raw.get("kind", "attack")` → `"attack"` | no (exit 1) | `assert _w7 == {"基础护甲", "近战护甲"}` at `:127` |

Baselines run against the pristine copy, all exit 0:
`b01` `_probe/test_repaint.py` (unregistered; the only end-to-end `unit.art` suite),
`b02` `_probe/test_retarget.py` (unregistered), `b04` `_probe/test_smoke5_design.py`
(the SKIP-and-exit-0 suite), `b05` `_probe/test_test_validity.py`.
`b03` `_probe/test_plan_matches_build.py` (unregistered) **did not finish in 900 s** —
see "What I did not test".

Score: **24 deliberate bugs, 15 caught, 9 survived.** Every survivor sits on a
claim someone would reasonably believe the suite covers:

- **m01 + m21** — "the panel edit is surgical" rests on an `ok` that is `True` by
  construction (finding 14). Both callers are blind.
- **m22** — "changing what a technology does" (`tech.effect`) has no registered
  byte-level test. The one suite that invokes it sweeps `plan()` only.
- **m18** — "the `.dat` answers which `.sld` draws this unit" is asserted, but by a
  hand-built index inside the test, not by `SpriteIndex`, whose id map is the thing
  a regression would break.
- **m07** — "the payload verifies against the install" is `rep["ok"]` that nothing
  can make false.
- **m09** — a mod could claim to carry a `.dat` it did not, in the suite that exists
  to police exactly that.
- **m08** — the tree serialiser is byte-pinned, but not by *this* suite (it compares
  `blob == CT.serialize(target)`, both sides moving together); the only real guard
  is `aoe2mod/tests/test_civtechtrees_writer.py:77-83`.
- **m04** — a `.dat` grant that reports an edit it did not make passes.
- **m12** — a `tech.cost` arithmetic break is invisible to the suite that claims to
  police declared resource costs.

---

## Coverage of declared intents

`aoe2mod/schema/intents.json` declares exactly 10 intents. "Invoked" is measured by
AST: a dict literal `{"intent": "<name>"}` present in the file (a bare string
mention in a comparison list does not count — several files do that and never run
the intent).

| intent | strategy | registered suites that invoke it | mutation evidence | real coverage? |
|---|---|---|---|---|
| `unit.stat` | in_place_patch | `test_compiler.py`, `test_api.py`, `test_emit_mod.py`, `test_reskin.py`, `test_product_v7_recipe.py`, `test_bundle_dat_half_e2e.py`, `probe_bundle_dat_half.py` | m17 caught (`test_emit_mod` `assert after == [6]`); m02 caught | **yes** — absolute values, 63-civ fan-out and int/float kinds asserted |
| `unit.attack_class` | in_place_patch | `test_compiler.py`, `test_api.py` | m25 caught (`:127`), m20 caught (mirror slot) | **yes** |
| `unit.cost` | in_place_patch | `test_compiler.py`, `test_api.py` | m23 broke the shared slot picker. The `tech.cost` refusal case caught it, but **`test_compiler.py:188-190` printed `成本 wood: 25 -> 20` and passed** — Archer's first cost slot happens to be wood, and the label is schema-derived (`compiler.py:1101`), so that assertion cannot see a wrong slot | **partly** — the label and the number are asserted for a unit whose slot order hides the bug; the selector is pinned only by a `tech.cost` case (`:237 (50, 30)` where gold is NOT slot 0) |
| `tech.research_time` | in_place_patch | `test_compiler.py`, `test_api.py` | m24 caught (`:212` `edit_count == 2`) | **yes** — the per-research-location fan-out is pinned |
| `tech.cost` | in_place_patch | `test_compiler.py`, `test_api.py` | m23 caught (expected refusal at `:250`) | **yes** — including "value is NOT in the first slot" (`:237` `(50, 30)`) |
| `tech.effect` | in_place_patch | `test_api.py` **only** | **m22 survived** — the write is replaced with a no-op and the suite says ALL API CHECKS PASSED | **no** — plan-level only; `test_api.py:577-598` never calls `build()` |
| `unit.availability` | civtechtrees_json | 8 suites incl. `test_availability_intent.py`, `test_panel_wire.py`, `test_dat_half_count.py` | m03 caught, m13 caught, m14 caught, **m04 survived**, **m09 survived** | **yes for the tree/panel half; no for the `.dat` half's bytes** |
| `tech.availability` | civtechtrees_json | `test_tech_availability_e2e.py`, `test_panel_wire.py`, `test_api.py` | m06 caught (`has` vs `can_build`), m10 caught (`changes_dat`) | **yes** |
| `unit.sprite` | loose_files | `test_reskin.py`, `test_api.py` | m05 caught (`grid_mismatches`), **m07 survived** (`verify_files`), **m18 survived** (`SpriteIndex`) | **partly** — plan + grid rules are real; the payload verification and the id index are not |
| `unit.art` | repaint_sld | **none** | not applicable — no registered suite names it | **no** — only `_probe/test_repaint.py`, which is unregistered and green on this machine |

Two structural notes:

- `unit.art` is the one declared intent with **zero** registered coverage. It is
  exercised end-to-end only by `_probe/test_repaint.py` (b01, exit 0),
  `_probe/test_sld_encode.py` and four `tmp_paint_*.py` scratch scripts — none of
  which `run_suites.py` runs. The schema itself records the honesty boundary
  (`not_verified_reason`: a repainted `.sld` has not been loaded by a running game),
  which is a different thing from having no regression test at all.
- `tech.effect` is the sharpest single gap: it is the intent whose entire purpose is
  writing a float32 into an effects array, and no registered suite re-reads the
  bytes after a write. `aoe2mod/tests/test_api.py:579-596` sweeps
  `range(0, len(tk._stats["techs"]), 37)` and compares `plan()["edit_count"] > 0`
  against each row's `editable` flag — a real contract, but a plan-level one.

---

## What I did not test

- **`aoe2mod/tests/test_roundtrip.py` was not run.** It is not in `run_suites.py`;
  it belongs to `run_long.py` (5 `.dat` targets, ~2–3 min). The `.dat` writer's
  byte-exactness therefore rests on suites I did not execute. Mutation m16 does
  probe the writer's mismatch counter via `test_dat_edit_routes.py`, and m08 shows
  the tree serialiser's byte-exactness is pinned elsewhere (`test_civtechtrees_writer.py`).
- **`_probe/test_plan_matches_build.py` timed out at 900 s** and produced no verdict.
  It is the regression guard for the whole plan/build disagreement class and it is
  **not registered** — so the claim "plan() never promises work build() refuses" has
  no green gate behind it, and I could not establish whether the sweep itself is
  sound. Same for the rest of `run_long.py`.
- **No mutation targeted `aoe2mod/api.py`** (157 KB, the biggest surface) beyond the
  suites that go through it incidentally. I mutated the modules the suites call into,
  not the facade's routing.
- **The install/emit path was only lightly covered.** I did not mutate
  `aoe2mod/mod/emitter.py`'s manifest-file writing, `info.json` validation, or
  `aoe2mod/install` (m09/m10/m13 touch only two flags).
- **`unit.art`'s repaint encoder was not mutation-tested.** I ran `test_repaint.py`
  as a baseline (green) but did not break `aoe2mod/game/sldencode.py` or
  `aoe2mod/intent/repaint.py:151-170` and re-run, because the suite is not in the
  gate and a green baseline is not evidence of sensitivity.
- **I did not audit the 352 unregistered `probe_*` scripts** beyond counting them and
  checking the ones that a reader might trust (`probe_shipped_disagreement.py` and
  the three `probe_panel_*` files do contain real numeric assertions despite having no
  `check()` helper).
- **Timing and stability were measured under load.** Other agents' Python processes
  were running in the same tree throughout (two `run_suites.py` copies, a kernel
  verifier), so the timings in `timing.txt` are inflated; the pass/fail verdicts are
  not affected, but I cannot rule out an intermittent failure hidden by the fact
  that nothing failed.
- **Cross-suite interaction was not tested.** Several suites write into
  `aoe2mod/tests/out/`; I did not verify that a clean `out/` and a dirty `out/` give
  the same verdicts.
- **Game-verified claims are out of reach for any test here** — nothing in this
  suite can prove the engine reads a written file. Many suites say so explicitly in
  a `NOT PROVEN:` line (about 20 files), which is honest and should be credited, not
  flagged.

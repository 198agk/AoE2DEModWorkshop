# Pipeline audit — `D:\Software\AI\帝国项目`

Auditor: `pipeline-auditor`. Scope: `tools/sync_engine.py` + the six generators + the
artifacts under `aoe2mod/` and `_probe/{schema,semantic}/`.
Working tree state at audit time: git HEAD `2678d05`, `core.autocrlf=false`, no
`.gitattributes`, ~35 modified files. Workspace was **not** modified; every experiment
ran against a throwaway sandbox under `C:\Users\26913\AppData\Local\Temp\paudit\`.

## VERDICT: GAPS

Every artifact on disk today is correct, reproducible and loads at runtime — but at least
six checks in the pipeline are tautological or absent, so real drift, garbage tables and a
`python -O` run all report success (six "OK" lines, exit 0) while testing nothing.

---

## Q1 — The 3 "DIFF" files: legitimate transformation or real drift?

**Measurement.** Read `tools/sync_engine.py` in full (455 lines), then rebuilt a sandbox with
copies of the 5 research sources + `sync_engine.py` + the 10 generated tables, ran
`sync_engine.py` there, and compared the sandbox output to the workspace's shipped copies
(`C:\Users\26913\AppData\Local\Temp\paudit\q1_final.py`, `q1_lines.py`). Workspace untouched.
All three shipped files are byte-identical to what a *fresh* sync produces:

| shipped | source | src sha / bytes | dst sha / bytes | changed lines |
|---|---|---|---|---|
| `aoe2mod/dat/writer.py` | `_probe/serializer/write_dat.py` | `b7675df0dc202924…` / 41,473 | `8a887fd17b24b319…` / 39,463 | 49 (41 src-only, 8 dst-only) |
| `aoe2mod/dat/locate.py` | `_probe/datparse/intent_patch.py` | `56519761e3b5f6c1…` / 29,331 | `2faf8a80b3dcd405…` / 28,506 | 38 (28 src-only, 10 dst-only) |
| `aoe2mod/game/sldencode.py` | `_probe/sldencode.py` | `676a5a27188b74b3…` / 10,690 | `a8a374e662945558…` / 10,694 | 2 (1 + 1) |

First 5 differing lines of each:

```
--- aoe2mod/dat/writer.py  <-  _probe/serializer/write_dat.py
-# -*- coding: utf-8 -*-
-"""write_dat.py -- re-serializer (writer) for AoE2 DE ``.dat`` files.
-
-This is the exact inverse of the proven parser
-``D:\Software\DeepSeek Harness\工作区2\_probe\datparse\parse_dat.py``.

--- aoe2mod/dat/locate.py  <-  _probe/datparse/intent_patch.py
-"""INTENT COMPILER -- turn a human sentence into dat bytes.
-
-    INTENT = {"match_en": "Archer", "unit_id": 4, "field": "attack", "delta": 2}
-
-A player says "archers +2 attack".  They never say "class-3 Base Pierce amount".

--- aoe2mod/game/sldencode.py  <-  _probe/sldencode.py
-import sldlib as S
+from . import sld as S
```

**Decision: all three are legitimate, none is real drift.**

- `sldencode`: exactly the one `import` rewrite `tools/sync_engine.py:316` performs.
- `writer.py`: the 5-line docstring header swap (`sync_engine.py:181-191`, which also drops
  the stale `# -*- coding: utf-8 -*-` line and the old UTF-8-BOM-mangled `工作区2` path
  mention), the `WRITER_PATH_HACK` block (`sync_engine.py:133-139` → `:172`) replaced by
  `from . import parser as _pd` (shipped L17), the `import parse_dat` rewrite
  (`sync_engine.py:175-176` → shipped L1004), plus a trailing-`rstrip` difference.
- `locate.py`: header swap, `import parse_dat as P` → `from . import parser as P`
  (shipped L15), and the tail cut at `if __name__ == "__main__":` (`sync_engine.py:217-220`).

**What is asserted vs silently written** (exact `assert` sites in `tools/sync_engine.py`):

| asserted (sha or text equality) | line |
|---|---|
| `aoe2mod/dat/parser.py` == source | 413 |
| `aoe2mod/game/sld.py` == source | 415 |
| `aoe2mod/game/sldencode.py` == `source.replace(import)` | 422–424 |
| `sldencode` no longer mentions `sldlib` | 425–426 |
| 3 AGE effect tables byte-identical | 430 (loop at 429) |
| `effect_labels_zh.json` (only if source exists) | 434 |
| resource label tables (only if source exists each) | 440 |
| attribute label tables (only if source exists each) | 448 |

**Never asserted — silently written:** `aoe2mod/dat/writer.py` (`vendor_writer`,
write at L193), `aoe2mod/dat/locate.py` (`vendor_locator`, write at L231),
`aoe2mod/semantic/data/unit_names.json` and `tech_names.json` (`vendor_names` L326-332,
plain `shutil.copyfile` at L330; the manifest records `bytes` only, L381-384).

**Proof that the gap is live** (sandbox, `q_decisive.py`): injected
`WRITER_DRIFT = 'LEAKED'` / `LOCATOR_DRIFT = 'LEAKED'` before the `__main__` guard of each
source (injection asserted non-no-op: +26 B / +27 B) and ran `sync_engine.py`:
`rc=0`, all six `…: OK` lines still printed, shipped writer grew 39,463→39,489 B, shipped
locator 28,506→28,533 B, and provenance recorded
`sources.writer.sha=6dd372a8eaf64ef8` vs `vendored_writer.sha=8b341d8c42e26ab0`
(equal=False, no complaint).

---

## Q2 — Does `sync_engine.py` verify anything about the GENERATED tables?

**Measurement.** Grepped `sync_engine.py` for every generator filename and for
`subprocess`/`import`: it references `_probe/schema/build_*.py` **only in comments and in
error strings** (L55, 74, 76, 81, 88, 113, 249, 256, 272, 285). It never runs a generator
(no `subprocess` import at all, L20-25) and never reads `_probe/schema/*.py`. It only
compares files it is about to copy against files it just copied.

**Answer: no. It is purely a `_probe/` → `aoe2mod/` copy-verifier. If a generator produced
garbage, `sync_engine` would ship it and say OK.** Measured with a poisoned-input sandbox
(`C:\Users\26913\AppData\Local\Temp\paudit\q2_sync.py`):

| scenario | rc | "OK" lines | shipped? |
|---|---|---|---|
| S1 `resource_labels.json` → `{"names":{}}` (zero names) | **0** | yes | yes |
| S2 `unit_names.json` → `{}` | **0** | yes | yes — provenance records `"bytes": 3` |
| S3 `effect_labels_zh.json` deleted (stale copy already shipped) | **0** | yes | stale copy survives, still in provenance |
| S4 `effect_command_types.json` note replaced with old-extractor text | **1** | — | refused (`SystemExit`, L252) |
| S5 `effect_attributes.json`: note kept, every value → `"GARBAGE"` | **0** | yes | yes |
| S6 real edit to `intent_patch.py` | **0** | yes | yes (drift present in shipped `locate.py`) |
| S8 `python -O sync_engine.py` | **0** | yes | yes, **zero checks executed** |

Two structural reasons the checks cannot fail on content:

1. **They are self-referential.** `assert sha256(PKG/schema/x) == sha256(_probe/schema/x)`
   (L430/440/448) after `shutil.copyfile(src, dst)` (L259/275/288) proves only that
   `copyfile` worked. S1 and S2 are this shape: empty-but-identical passes.
2. **They are self-attesting.** The one real guard is
   `if BRANCH_RULE_MARKER not in (data.get("note") or ""): raise SystemExit(...)`
   (`sync_engine.py:252`). `BRANCH_RULE_MARKER` (L78) is the literal string that
   `_probe/schema/build_schema.py:49-51` writes into every table it emits. Any consumer
   (or corruptor) that keeps the `note` passes, regardless of content — measured in S5.

Also: the manifest is written at **L391-394, before every assertion (L413-450)**, and
`main()` never reads a previous manifest (filename appears only in the L2 docstring and
L391). So `ENGINE_PROVENANCE.json` records what the run just wrote; it cannot detect drift,
only describe it. A failed run leaves a manifest that happily describes the bad state.

Runtime-side corroboration that today's tables are *not* garbage (so this is a latent gap,
not a present corruption): `unit_names.json` 2,693 ids / 1,651 resolved / 118 civ_variants;
`tech_names.json` 1,510 ids / 536 resolved; `load_resource_labels()` → 328 entries,
`load_attribute_labels()` → 224; `SemanticIndex.find("unit","Archer")` → `(4, '步弓手')`,
`find("unit","长弓兵")` → `(8, '长弓兵')`, `find("tech","Loom")` → `(22, '织布机')`.

**No test guards the tables either.** Grepping `aoe2mod/tests/` for the eight generated
filenames, only `aoe2mod/tests/test_api.py` matches: `_C.load_resource_labels()` (L314),
`assert _labels` (L315), 13 named resource types (L316-320), `34/194 not in _labels`
(L323). No test touches `unit_names`, `tech_names`, `attribute_labels`,
`effect_attributes`, `armor_classes` or `ENGINE_PROVENANCE.json`.

---

## Q3 — Run each generator twice: idempotent and deterministic?

**Measurement.** `C:\Users\26913\AppData\Local\Temp\paudit\q3_idem.py`: sha256-snapshotted
all 36 files under `_probe/schema/` + `_probe/semantic/`, backed them up, ran each generator
**twice**, re-snapshotted, then restored anything that differed.

```
build_schema.py             run1 rc=0 0.1s  run2 rc=0 0.1s  changed_by_run1=0  changed_by_run2=0
build_attribute_labels.py   run1 rc=0 0.1s  run2 rc=0 0.1s  changed_by_run1=0  changed_by_run2=0
build_resource_labels.py    run1 rc=0 0.1s  run2 rc=0 0.1s  changed_by_run1=0  changed_by_run2=0
build_labels_zh.py          run1 rc=0 0.0s  run2 rc=0 0.0s  changed_by_run1=0  changed_by_run2=0
extract_ids.py              run1 rc=0 6.1s  run2 rc=0 6.0s  changed_by_run1=0  changed_by_run2=0
build_semantic.py           run1 rc=0 0.4s  run2 rc=0 0.4s  changed_by_run1=0  changed_by_run2=0
restored 0 path(s): []  |  post-restore identical to snapshot: True
```

**Answer: yes — generation is idempotent and deterministic. No file changed on the second
run, and no file changed relative to the pre-existing on-disk state**, i.e. today's tables
are exactly what these generators produce from today's inputs. (This also independently
proves the generators emit LF: a CRLF rewrite would have changed bytes on run 1.)

Caveat: determinism is only as good as the inputs' stability. `_probe/semantic/strings_db.py:9`
hardcodes the game root, and `_probe/semantic/extract_ids.py:47-48` hardcodes the `.dat` path,
so a game patch silently changes the output (correctly) but a *missing* game install fails the
run rather than degrading — acceptable, but worth knowing.

---

## Q4 — Artifacts under `aoe2mod/` with NO generator and NO research source

**Measurement.** `C:\Users\26913\AppData\Local\Temp\paudit\q4_census.py` — walked all 58
files of `aoe2mod/` (excluding `__pycache__`), classified each against sync_engine's outputs
(16 files + 8 zero-byte `__init__.py`) and against the 12 `_probe/`-side generator outputs;
cross-checked with a basename search over `_probe/` excluding `_probe/team/` (another
auditor's sandbox, not a research source).

**24 covered / 34 uncovered** (48,695,820 bytes). The 34 unreproducible files:

Hand-authored Python (17): `api.py` 157,335 · `dat/families.py` 14,586 ·
`game/buildpanel.py` 27,766 · `game/buttons.py` 7,040 · `game/civtechtrees.py` 31,593 ·
`game/locations.py` 30,459 · `game/sprites.py` 36,492 · `intent/availability.py` 17,524 ·
`intent/compiler.py` 102,781 · `intent/datgrant.py` 18,592 · `intent/repaint.py` 13,387 ·
`intent/reskin.py` 28,883 · `intent/retarget.py` 7,957 · `mod/emitter.py` 21,052 ·
`semantic/index.py` 7,360.
Hand-authored data (2): `schema/dat_bindings.json` 13,785 · `schema/intents.json` 26,830.
Tests (10): `tests/test_api.py` 73,366 · `test_availability_e2e.py` 8,625 ·
`test_availability_intent.py` 16,189 · `test_buildpanel.py` 9,997 · `test_civtechtrees.py`
18,076 · `test_civtechtrees_writer.py` 20,733 · `test_compiler.py` 35,338 ·
`test_emit_mod.py` 5,137 · `test_product_v7_recipe.py` 11,344 · `test_roundtrip.py` 4,136.
Binary test fixtures (5, the genuinely unreproducible class): `tests/out/archer_attack_plus2.dat`
11,982,182 · `tests/out/ArcherAttackPlus2/resources/_common/dat/empires2_x2_p1.dat`
11,982,182 · `tests/out/ArcherAttackPlus2_via_api/…/empires2_x2_p1.dat` 11,982,182 ·
`tests/out/_identical_probe/…/empires2_x2_p1.dat` 11,982,480 · plus 3 `info.json`
(156 / 119 / 156 B).

This is a legitimate architecture (a shipped product is not all generated), and all 58 files
are git-tracked, so it is recoverable from git even if the install directory is wiped again.
The risk is narrower: **the 5 `.dat` fixtures cannot be replayed** — they must be regenerated
by running writer + installer against the live game, and nothing in the pipeline does that or
even checks they still parse. Secondary finding: `_probe/schema/AGE3NamesV0007.json`
(14,692 B) IS generated by `build_schema.py:134` and IS listed by two rebuild tools, but is
never vendored into `aoe2mod/` — a generated artifact whose only consumers are one-off probes.

---

## Q5 — Line endings

**Measurement.** `C:\Users\26913\AppData\Local\Temp\paudit\q456.py`: binary read of every
file, counting `\r\n` and lone `\r`, plus a UTF-8 BOM check.

```
aoe2mod/**/*.py       38 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
aoe2mod/**/*.json     16 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
_probe/schema/*.py     8 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
_probe/schema/*.json   9 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
_probe/semantic/*.py  14 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
_probe/semantic/*.json 4 files   offenders 0   (crlf 0, lone_cr 0, bom 0)
TOTAL 89 files, 0 offending
```

**Answer: 0 CRLF, 0 lone CR, 0 BOM across all 89 text files.** The LF fix holds. Caveat, so
the number is not over-read: 4 files under `aoe2mod/tests/out/` *do* contain `\r\n` byte
pairs, but they are `.dat` binaries (`archer_attack_plus2.dat`, three `empires2_x2_p1.dat`
copies) where `0D 0A` is incidental data, not a line ending. Those are correctly excluded
from the check — but note that `aoe2mod/**/*.json` and `**/*.py` globs mean the check never
looks at them anyway.

---

## Q6 — `aoe2mod/ENGINE_PROVENANCE.json` vs disk

**Measurement.** `C:\Users\26913\AppData\Local\Temp\paudit\q_final.py`: loaded the manifest
(106 lines, 3,315 B) and re-hashed every path it names — 5 `sources`, 5 `vendored_*`,
2 `data[]`, 8 `effect_tables[]` = 20 entries.

```
total entries 20 | missing files 0 | sha mismatches 0 | entries without sha 2
```

**Answer: it matches disk exactly right now — 0 mismatches.** 13 of the 20 entries carry a
sha256 and all 13 verify (5 vendored + 8 effect_tables). The two exceptions are the
semantic name tables, which carry `bytes` only:

| path | claimed sha | actual sha256 | bytes |
|---|---|---|---|
| `aoe2mod/semantic/data/unit_names.json` | *(none)* | `2717d9720b2fe2f2fecc4cdf3f84014dcd59cb0bd882fc5350ca7eacb7c2bbd2` | 1,088,495 |
| `aoe2mod/semantic/data/tech_names.json` | *(none)* | `9712ba2b485489690e714247074fd1800b20ef2d57321502b6c83ef6f3773497` | 975,859 |

Two weaknesses that make "it matches" weaker than it looks: (a) the manifest has **no
transform/patch field anywhere**, so it records `sources.writer.sha256 = b7675df0…` and
`vendored_writer.sha256 = 8a887fd1…` as two unrelated hashes it never proves are related —
provenance cannot distinguish "correctly patched" from "arbitrarily rewritten"; (b) it is
written *before* the asserts (L391 vs L413-450), so its agreement with disk proves only that
`copyfile`/`write` succeeded, not that any check passed. And `_probe/tools_rebuild_all.py:160-163`
re-verifies only `dict`-shaped entries, silently skipping `data` and `effect_tables` — 10 of
these 20 files.

---

## Failure modes found

1. **`tools/sync_engine.py:412-450` — four shipped artifacts are never asserted.** `writer.py`,
   `locate.py`, `semantic/data/unit_names.json`, `semantic/data/tech_names.json` are copied
   and never verified. Measured: injected drift shipped with rc=0 and six "OK" lines.
   **Severity: HIGH.**
2. **`tools/sync_engine.py:430/440/448` — the table assertions are tautological.**
   `sha(pkg)==sha(src)` immediately after `shutil.copyfile(src,pkg)` proves only that the copy
   worked. Measured: `resource_labels.json` reduced to zero names → rc=0, "byte-identical …
   OK". **Severity: HIGH.**
3. **`tools/sync_engine.py:252` — the branch-rule guard is self-attesting.** It checks a
   substring of `note` that `_probe/schema/build_schema.py:49-51` itself writes. Measured:
   keep the note, replace all 89 attribute values with `"GARBAGE"` → rc=0, shipped.
   **Severity: HIGH.**
4. **`tools/sync_engine.py:413,415,422,425,430,434,440,448` — every check is a bare `assert`**,
   so `python -O tools/sync_engine.py` executes zero verification while printing six "OK"
   lines. Measured: rc=0, 6 OK, empty stderr, with drift present. **Severity: HIGH.**
5. **`_probe/tools_rebuild_all.py:131,150,168` — three post-checks compute a result and
   discard it.** CRLF, import failures and provenance mismatches are printed but never
   appended to `problems`, so `return 0` at L182 is reported over a failed Post-Rebuild
   Check block. **Severity: HIGH** (canonical "reports success while testing nothing").
6. **`tools/sync_engine.py:391-394` — manifest written before the assertions**, and never
   compared against the previous manifest. A run that fails at L413 still leaves a fresh
   `ENGINE_PROVENANCE.json`. **Severity: MEDIUM.**
7. **`tools/sync_engine.py:261-264,267-276,279-289` — missing optional tables are silently
   skipped, leaving stale copies shipped *and still listed in provenance*.** Measured (S3):
   delete `_probe/schema/effect_labels_zh.json` → rc=0, stale file unchanged, still in the
   manifest. **Severity: MEDIUM.**
8. **`tools/sync_engine.py:217-231` — `vendor_locator()`'s header claims "the demo `main()`
   is trimmed" but only the 2-line `__main__` guard is cut.** The shipped
   `aoe2mod/dat/locate.py` is 668 lines and still contains `def main()` at L542-668, which
   writes `out_intent/…` and a ~12 MB blob into the package. No package code calls it, so it
   is dead weight, but the tool's own docstring misstates what it did. **Severity: MEDIUM.**
9. **`tools/sync_engine.py:177-178` — a literal no-op "rewrite".**
   `src.replace("    p = parse_dat.Parser(raw)\n", "    p = parse_dat.Parser(raw)\n")` —
   old string == new string, provably cannot change anything (both strings measured to occur
   once in the source). **Severity: LOW-MEDIUM** (the "reports work, does none" shape; a
   future refactor will assume this line does something).
10. **`_probe/tools_rebuild_inventory.py:33-44` — it verifies the presence of inputs the
    generators never read.** It claims `attribute_labels*.json` need
    `_probe/schema/effect_attributes.json` and `resource_labels*.json` need
    `_probe/schema/AGE3NamesV0007.json`. Actual reads: `build_attribute_labels.py:112-116`
    and `build_resource_labels.py:112` open the **game's**
    `resources/<locale>/strings/key-value/key-value-strings-utf8.txt` (plus
    `dat_bindings.json` at L170-171). So the true inputs — the game string files — are never
    checked for presence at all. **Severity: MEDIUM.**
11. **`_probe/tools_rebuild_inventory.py:122-127` — it conflates "transformed" with
    "drifted".** `same = (a is not None and a == b)`; the 3 known transforms can never be
    `same`, so "vendored copies that differ: 3" is the expected steady state, and the script
    exits 1 every run. This is what produced the 3-DIFF report that prompted this audit.
    **Severity: MEDIUM** (a permanent red light trains operators to ignore it).
12. **`_probe/tools_regen_tables.py` — the "regenerate the tables" script skips a generator
    and discards a result.** `STEPS` (L20-26) omits `_probe/schema/build_schema.py`, so the
    three AGE tables are never regenerated; L31-33 returns `True` for a `(missing)` script;
    L72 calls `crlf_report()` and throws the return value away. **Severity: MEDIUM.**
13. **`aoe2mod/intent/compiler.py:190-236,242-291` — a stripped install silently yields `{}`
    labels.** Both loaders `continue` when a table is absent, contradicting the L230 comment
    "the English table ships always"; nothing enforces it. Module-level caches
    (`_RESOURCE_LABELS`, `_ATTRIBUTE_LABELS`) mean a mid-session fix is never picked up.
    **Severity: MEDIUM.**
14. **`aoe2mod/dat/locate.py:19` — dead path.** `SEM = os.path.join(os.path.dirname(HERE),
    "semantic", "unit_names.json")` resolves to `aoe2mod/semantic/unit_names.json`, which
    does not exist (`Test-Path` False; the real file is `semantic/data/unit_names.json`).
    `SEM` occurs exactly once in the file — its own definition. **Severity: LOW.**
15. **`aoe2mod/dat/writer.py:1002-1003` — dead `sys.path` hack shipped.** `_main` inserts
    `<pkg>/datparse` (does not exist) into `sys.path`, and the `if __name__ == "__main__":`
    entry point ships at L1033. Harmless today; a trap the moment someone runs the module.
    **Severity: LOW.**
16. **`_probe/schema/extract_labels.py` — a stale naive generator with the same output
    filenames.** 2,470 B, writes `effect_command_types.json` / `effect_attributes.json` with
    a wrong-shaped `entries` **list** and note "index = combo-box selection - 1" (no branch
    rule). Not in any STEPS list, so today it is inert — but running it would replace two
    correct tables with the shape `sync_engine` then rejects at L252. **Severity: LOW.**
17. **`_probe/schema/AGE3NamesV0007.json` — generated, listed by two rebuild tools, never
    shipped.** 14,692 B with no consumer in `aoe2mod/`; only one-off probe scripts read it.
    **Severity: LOW.**

---

## What I could not check

- **The binary `.dat` fixtures** (`aoe2mod/tests/out/*.dat`, 4 × ~12 MB). I did not parse
  them, so I cannot say whether they still round-trip against the current writer, nor
  whether they reflect the current VER 8.9 game file. Regenerating them requires the
  installer path against the live game, which is outside this read-only audit.
- **The full test suite.** I loaded modules and exercised `SemanticIndex`,
  `load_resource_labels()`, `load_attribute_labels()` directly, and grepped for table usage,
  but did not run `aoe2mod/tests/*` (10 modules, `test_api.py` alone is 73 KB / 1,308 lines).
  "Tests do not guard the tables" is a grep-level claim, not a mutation-testing result.
- **Whether the shipped tables are semantically *correct*.** I verified they are
  reproducible, non-empty, load, and resolve known names (`Archer`→4, `长弓兵`→8,
  `Loom`→22). I did not audit them against the game's string files id-by-id.
- **`_probe/tools_rebuild_all.py`'s end-to-end run.** I read it and proved its exit code
  ignores three checks, but did not execute it (it re-runs 7 steps twice, including
  `extract_ids.py` at ~6 s each, and would have rewritten the tables under audit).
- **`cpp_branch.py`'s branch-evaluation logic** (300 lines). I confirmed it reads no file and
  that `build_schema.py` is its only writer, but did not verify the AGE version-branch
  modelling is right — that would need AGE's own source to compare against, which is not in
  `_probe/source/`.
- **`_probe/team/` contents of other auditors**, and `_probe/source/AGE/**` beyond
  `AGE_Frame/Lists.cpp` (which exists, 126,807 B, as the generators expect).
- **Concurrency/reentrancy**: whether two `sync_engine.py` runs or a run concurrent with a
  test suite can interleave. Not attempted.

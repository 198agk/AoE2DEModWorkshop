# Adversarial audit of `_probe/build_smoke5.py` (task-1)

VERDICT: DESIGN IS AMBIGUOUS BECAUSE the co-installed sibling mod
`aoe2mod Bundle VillagerHP plus Britons HandCannon` ships the *same three engine
paths* with the *opposite* contents on each, and its `.dat` is *byte-identical*
to smoke5's, so (1) smoke5 is not even registered/enabled, and (2) no cell of the
observed 2x2 can be attributed to smoke5's edits.

Auditor: `design-auditor`. All numbers below were produced by the probes named in
`_probe/team/auditor/` and are reproducible with `_probe/team_audit_design.py`.

---

## F1 — FATAL: smoke5 is not installed in the eyes of the game, and never has been

| measurement | value | source |
|---|---|---|
| `Smoke5` anywhere in `mod-status.json` | **False** | `p15_mixture.py` 15a |
| `mod-status.json` mtime | 2026-10-15 00:54:44 | `p23_final.py` 23b |
| smoke5 mod dir mtime | 2026-10-15 **01:14:25** | `p23_final.py` 23b |
| game log sessions that ever print `Enabling mod #0 (aoe2mod Smoke5 ...)` | **0** of 10 sessions that have a `MainLog.txt` (11 log dirs, 124 txt files) | `_probe/team_audit_design.py` F1, `p22_logmods.py` 22b |
| distinct mods the logs have enabled | 10; the only aoe2mod ones are `smoke2 build panel gate` x4, `smoke villager HP + Britons units` x4, `Bundle - Villager HP + Britons Hand Cannoneer` x2, `Panel Smoke - Britons Hand Cannoneer` x2 | `p22_logmods.py` 22b |

`install_smoke5.py` copies the folder and then states, at line 104,
`mod-status.json was NOT modified by this script.` The Bundle mod, by contrast,
*is* a `Mods` entry (`{"Enabled": false, "Priority": 1, "Path": "local//aoe2mod
Bundle VillagerHP plus Britons HandCannon"}`, `p14_sibling.py` 14a). The install
instructions (`install_smoke5.py:95-102`) tell the user to "make sure <smoke5> is
ENABLED" — but the mod is not in `Mods`, so it cannot be enabled from the mod
manager. The 01:14:25 copy post-dates the 00:54:44 status write, i.e. the copy
has never been registered.

Consequence: the very first reading instruction is unsatisfiable as written. Any
run performed after a naive install loads the *Bundle*, not smoke5.

## F2 — FATAL: the positive control cannot attribute load

`build_smoke5.py:15-17` designates Villager 1000 HP as the control that "proves
the mod loaded at all". Measured, by inflating each `.dat` (raw deflate, wbits
-15) and reading unit 83:

| copy | bytes | sha256[:12] | Villager (83) hp |
|---|---|---|---|
| SHIPPED | 12023754 | `4aa2f0a719e8` | 25 |
| BUNDLE | 11983020 | `330665c06b53` | **1000** |
| SMOKE5 | 11983020 | `330665c06b53` | **1000** |
| OUT (`_probe/out_smoke5`) | 11983020 | `330665c06b53` | **1000** |

Source: `p19_inflate.py` 19b (`p18_controlparse.py` and `p16_control.py` 16a give
the identical sha values without inflation). The Bundle and smoke5 `.dat` files
are **byte-identical**. The control therefore fires identically whichever of the
two mods is enabled: seeing Villager HP 1000 proves *some Villager-HP mod*
loaded, not that *smoke5* loaded. The fallback cell of the reading table
(`install_smoke5.py:102`, "control: Villager HP must read 1000, or the mod did
not load") is vacuous.

Note the control *is* correctly built: unit 83 goes 25 -> 1000 in all 63 civ
copies of the record (`p19_inflate.py` 19a, `n=63` for ids 83/13/545/74/2550),
and the emitted `.dat` is 11983020 B matching `_probe/out_smoke5`. The half of
the build that is broken is *attribution*, not the edit.

## F3 — FATAL: a sibling mod ships the same three paths with opposite contents

`p23_final.py` 23e, `p15_mixture.py` 15b:

| mod | tree has A=2550 | tree has B=74 | panel has A | panel has B |
|---|---|---|---|---|
| Bundle | **False** | True | False | **True** |
| Smoke5 | **True** | True | False | **False** |

Both mods ship `resources\_common\dat\empires2_x2_p1.dat`,
`...\futuravailableunits.json` and `...\CivTechTrees\BRITONS.json` (all three
verified present, `p16_control.py` 16e). Because layering may be resolved
per-file, the engine can take the tree from one mod and the panel from the other.
Enumerated (`p15_mixture.py` 15b):

| tree from | panel from | A (2550) | B (74) | design reads it as |
|---|---|---|---|---|
| Bundle | Bundle | absent | present | "neither / mod did not load" |
| Bundle | Smoke5 | absent | absent | **"PANEL drives"** |
| Smoke5 | Bundle | present | present | **"TREE drives"** |
| Smoke5 | Smoke5 | present | absent | "both" |

Row 2 is the failure: smoke5's *tree* edit is entirely absent from the game, yet
the observation is the design's headline conclusion "the menu is driven by the
PANEL". Row 3 is the mirror image. Every one of the four cells is reachable from
the state already on disk, so the experiment has no power to attribute.

## F4 — the outcome -> hypothesis table is not injective

Enumerating all six plausible engine regimes against the two observable bits
(`p23_final.py` 23c):

| outcome | regimes that produce it |
|---|---|
| A present, B present | `tree-only` **or** `union (either file)` |
| A absent, B absent | `panel-only` **or** `intersection` |
| A present, B absent | `tree-for-A + panel-for-B` |
| A absent, B present | `panel-for-A + tree-for-B` |

The design claims (A present, B present) means "the menu is driven by the TREE"
(`build_smoke5.py:21`) and (A absent, B absent) means "driven by the PANEL"
(`:22`). Both cells are 2-to-1. Even with a clean single-mod install the design
cannot separate "only the tree is read" from "both are read, and the union is
shown", nor "only the panel" from "the intersection is shown" — and those are
different answers to the question being asked.

## F5 — subject B is masked by the design's own precondition (99.2% of the space)

`build_smoke5.py:91` asserts, as a *precondition*, that Britons' tree row for 74
reads `ResearchedCompleted`. `CT.can_build` counts that as buildable
(`aoe2mod/game/civtechtrees.py`, `can_build = st is not None and st !=
"NotAvailable"`). So the tree independently grants Militia; removing the panel
entry cannot remove the button in any regime where the tree is consulted.

Measured (`p20_masking.py` 20a/20b):

* Britons' panel at bldg 12 lists **8** units; **8 are MASKED** (the tree grants
  each one too), **0 are clean**. There is **no** Britons bldg-12 panel unit with
  a non-granting/missing tree row (20c: 0 candidates).
* Across all 62 bridged civs, of **495** panel bldg-12 unit entries,
  **491 (99.2%) are MASKED** and only **4 are clean**.

The 4 clean cases are the shipped contradictions: `JURCHENS 77 Long Swordsman`,
`JURCHENS 473 Two-Handed Swordsman`, `JURCHENS 567 Champion`, `MUISCA 359
Halberdier` — panel lists them at bldg 12 while the tree row reads
`NotAvailable` (`p20_masking.py` 20d). The design chose a subject from the 99.2%
instead of the 0.8%.

## F6 — the A half has no shipped precedent, and the panel is the dominant source

`p12_bridge.py` (recorded in the audit trail) over the bridged tree/panel pairs:

* A-direction, granting statuses at bldg 12 with the panel omitting the node:
  **0** instances where the tree grants and the panel omits it at the source
  building. The only granting cases are 4x `2552 Champi Warrior`
  `ResearchedCompleted` at **building 118** (panel agrees at 118), plus GOTHS 759/761
  `ResearchRequired` with no panel row.
* B-direction: **4** shipped instances (the JURCHENS/MUISCA four above).
* Field mismatches between panel and tree: **28** total (`{'AGE': 13, 'BLDG': 15}`),
  e.g. `('BLDG','MAPUCHE',93,'Spearman',2556,12)`, `('AGE','SICILIANS',1658,
  'Serjeant',2,3)`, `('BLDG','ARMENIANS',125,'Monk',104,1806)`.
* Of 4323 bridged panel unit entries, **1201 (27.8%) have no tree row at all**
  and 11 have a non-granting row.

So the panel, not the tree, is where the menu entries overwhelmingly come from —
and the A causal step ("grant in tree -> a new button appears") is not
demonstrated by any shipped pair in either direction. The design's positive
branch rests on an unobserved behaviour.

## F7 — minor / explicitly NOT a finding

The granted 2550 row carries `Trigger Tech ID = 1350`, a key no native Britons
Age-1 bldg-12 row carries (`p23_final.py` 23d). I checked whether this is a gate
and it is **not**: of 1894 unit rows carrying a `Trigger Tech ID`, only 224
(11.8%) belong to a civ that holds that tech; 1670 (88.2%) do not, and INCAS's
own `2550` row carries 1350 while INCAS holds no TECH row 1350, yet INCAS shows
the button natively (`p5_trigger.py`). Tech 1350 exists as a TECH row in 0 of 62
trees. So this asymmetry must **not** be cited as a suppression rule. All four
native Champi civs have tree `TriggerTech=1350 status=ResearchedCompleted`, panel
bldg 12 (`p5_trigger.py` 5e).

Also checked and clean:

* `BP.remove_entry(txt, kb, 74, BP.UNITS_KEY)` removes exactly **1** entry and is
  namespace-correct — id 74 is dual-namespace (Units=Militia at bldg 12,
  Techs=Scale Mail Armor at bldg 103); the Techs entry survives (`p3_edits.py`
  B1/B2).
* Surgical: `verify_surgical` -> `ok=True`, `kind="delete"`,
  `outside_is_untouched=True`, unit-74 entries across all 58 panel civs
  **110 -> 109**, exactly one civ affected (`p3_edits.py` B3).
* Grant side: donor `INCAS`, Britons unit rows **58 -> 59**, granted row
  byte-identical to the donor, exactly 1 row with Node ID 2550, `can_build=True`
  (`p3_edits.py` A1).
* Control edit present in the emitted `.dat` (25 -> 1000, 63 copies; `p19_inflate.py`).
* The panel JSON has no suppression key on the two subjects: Britons bldg-12
  `Units` entries are all exactly `('ID','Name','RequiredAge')`; the only extra
  fields at bldg 12 are `RequiredTechID` on two `Techs` entries for nodes
  207/217 (`p23_final.py` 23a).

---

## What would make it discriminate

1. **Remove the confound.** Uninstall (or delete) `aoe2mod Bundle VillagerHP plus
   Britons HandCannon`, and give smoke5 a *unique* `.dat` control value (e.g.
   Villager HP 1001, or a distinctive HP on a unit no other mod touches) so the
   control attributing load is smoke5-specific.
2. **Register the mod.** Write the `Mods` entry for smoke5 (or extend
   `install_smoke5.py` to do so) and verify the game log prints `Enabling mod #0
   (aoe2mod Smoke5 TreeVsPanel)` for the session used.
3. **Pick a subject B that is not masked.** The only clean candidates in the
   shipped data are panel-listed nodes whose tree row is missing or
   `NotAvailable` (the JURCHENS/MUISCA pattern); none exists in Britons' bldg-12
   set, so subject B must move to a civ/node pair from the 4 clean cases — or the
   design must state that it is testing the panel-only regime by construction.
4. **Break the outcome collision.** Add a third probe (e.g. an unrelated
   tree-only grant at a *different* building, or a panel-only removal at a
   building whose tree row is absent) so `tree-only` and `union` cease to be
   indistinguishable.

## Verdict line

VERDICT: DESIGN IS AMBIGUOUS BECAUSE the same three engine paths are shipped by
both `aoe2mod Bundle VillagerHP plus Britons HandCannon` (tree: 2550 absent/74
present; panel: 2550 absent/74 present; `.dat` sha `330665c06b53`) and
`aoe2mod Smoke5 TreeVsPanel` (tree: 2550 present/74 present; panel: 2550
absent/74 absent; same `.dat` sha `330665c06b53`), smoke5 is absent from
`mod-status.json` and from every `Enabling mod` log line, and its positive
control is byte-identical to the Bundle's, so all four 2x2 outcomes are reachable
without smoke5's tree edit loading; additionally the (A present,B present) and
(A absent,B absent) cells are each 2-to-1 against the regimes they are claimed to
distinguish, and subject B is masked by the design's own `ResearchedCompleted`
precondition in 491 of 495 (99.2%) comparable panel entries.

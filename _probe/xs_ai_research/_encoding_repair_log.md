# Encoding repair log — AI_SCRIPTING_AIREF.md

## What happened

A section-renumbering step round-tripped the UTF-8 deliverable through PowerShell
`Get-Content` (no `-Encoding`). On this zh-CN host that reads UTF-8 as **cp936/GBK**,
and the write-back re-encoded the mis-decoded text. 312 lines were damaged.

## The exact failure mode (proved, not guessed)

cp936 decodes a 3-byte UTF-8 sequence as: take `E2 80` as one GBK pair, then read the
**third byte together with the next character's first byte** as a second pair. When
that second pair is invalid the decoder emits `?` **and consumes both bytes**.

| Lead | Third byte | Original | Consumed |
|---|---|---|---|
| `U+9225` | `94` / `93` / `A6` | `—` / `–` / `…` | 1 following char |
| `U+922B` | `92` / `94` | `→` / `↔` | 1 following char |
| `U+922E` | `A4` | `≤` | 1 following char |
| `U+6402` | — (clean 2→2) | `§` | 0 |
| `U+947E U+7D66` | double-corrupted `ç` | `ç` | 1 (`o`) |

Confirmed against ground truth: `raw_commands.js` holds `Duke D'Alençon` as bytes
`... 6E C3 A7 6F 6E`; cp936 reads that as `D'Alen莽on`, and a second pass gives the
`D'Alen鑾給n` seen in the backup.

## Repair method

`fixenc.py` — 342 replacements, backup first (`AI_SCRIPTING_AIREF.corrupt.bak.md`).
Then `fix2.py` — 5 more replacements for the digit-lossy sites where the swallowed
character was a **digit**, not a space (backup: `AI_SCRIPTING_AIREF.pre_digitfix.bak.md`).

| Line | Was | Now | Authority |
|---|---|---|---|
| 85 | `extension— the` | `extension— the` (spacing recorded) | `load` description |
| 114 | `facts— is true` | `facts — is true` | `xor`/`xnor` description |
| 138 | `in UP— 'Elements'` | `in UP — 'Elements'` | *Data Limits* guide |
| 138 | `operators— In UP` | `operators — In UP` | Logical Operator guide |
| 227 | `(313–11` | `(313–511` | *Data Limits*: SNs 0–511 |
| 240 | `goals 1–0` | `goals 1–40` | *Data Limits* |
| 240 | `goals 511–12` | `goals 511–512` | UserPatch doc, quoted |
| 240 | `509–12` | `509–512` | UserPatch doc, quoted |
| 259 | `**0–,222 chars**` | `**0–3,222 chars**` | `txt_objects.txt` measures 3222 |
| 9630 | `Alen鑾給n` | `Alençon` | `raw_commands.js` `C3 A7 6F 6E` |

## Verification (decisive)

Method: **re-corrupt the repaired file with the same cp936 decoder** and compare to the
byte-truth backup. Any correct repair must re-corrupt to exactly the damaged original.

```
$gbk = [System.Text.Encoding]::GetEncoding(936)
$u8  = [System.Text.UTF8Encoding]::new($false)
$recon = $gbk.GetString($u8.GetBytes($cur[$i]))   # must equal $bak[$i]
```

Result: **1 mismatch out of 10,270 lines**, and it is a provable false positive —
L9630, where the backup was *double*-corrupted (`ç`→`莽`→`鑾給`) while the current text
matches `raw_commands.js` byte-exact. Every other line round-trips identically.

Final state:
- bytes `815,448`; chars `814,775`; lines `10,271`; UTF-8 **no BOM**
- non-ASCII: `—`×310, `§`×12, `…`×7, `→`×6, `–`×5, `↔`×1, `≤`×1, `ç`×1
- **CJK ideographs 0, PUA 0, U+FFFD 0**
- the 8 remaining literal `?` are all genuine prose question marks

## Structural re-verification after repair

| Section | Expected | Found |
|---|---|---|
| `## N.` H2 sections | 8 | 8 |
| `### N.M` H3 subsections | 28 | 28 |
| §2.1 command rows | 386 | 386 |
| §4.2 `####` parameter entries | 100 | 100 |
| §5 SN bullets | 313 | 313 |
| §3 `up-*` sections | 189 | 189 |
| §7.7 name list vs §2.1 | identical sets | **sets equal** |

## Lesson

Never round-trip a UTF-8 file through PowerShell `Get-Content`/`Set-Content` on this
host — the default encoding is GBK. Use `[IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false))`
with an explicit UTF-8 write, or `io.open(..., encoding='utf-8')` in Python.
`Get-Content -Encoding UTF8` on PS 5.1 also writes a BOM, so prefer the .NET route.

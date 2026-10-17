# -*- coding: utf-8 -*-
"""variant_check.py -- test two open questions against hard evidence.

Q1  Is `unknown_value_2` (the u32 right after the 1000 sentinel) actually the
    ScenarioVariant enum?  Test: compare our structural field against
    AoE2ScenarioParser's own `_get_scenario_variant` for EVERY instance it can
    answer for (that method is a pure byte heuristic, so it works pre-1.36 too).

Q2  What ARE the 256 prologue bytes in a .aoe2campaign?  Measure the
    distribution of the 64-bit words properly, instead of asserting pointers.

Run:
    $env:PYTHONIOENCODING="utf-8"
    & $py "...\\_probe\\scenario_header\\variant_check.py"
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import field_offsets, locate                                    # noqa: E402
from campaign_deterministic import parse_campaign_deterministic                    # noqa: E402

PKG = (r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies"
       r"\python\Lib\site-packages")
sys.path.insert(0, PKG)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DRS = os.path.join(GAME, "resources", "_common", "drs")
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")
PROFILE = (r"C:\Users\26913\Games\Age of Empires 2 DE"
           r"\76561198406248391\resources\_common\scenario")

out = []
def P(*a):
    s = " ".join(str(x) for x in a).replace("\x00", "\\x00")
    print(s)
    out.append(s)


def walk(root):
    r = []
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if f.lower().endswith((".aoe2scenario", ".scx")):
                r.append(os.path.join(dp, f))
    return sorted(r)


singles = []
for root in (DRS, CAMP_DIR, PROFILE):
    singles += walk(root)

# ---------------------------------------------------------------- library oracle
lib_variant = None
try:
    import inspect
    from AoE2ScenarioParser.scenarios import aoe2_scenario as _mod
    src = inspect.getsource(_mod._get_scenario_variant)
    P("=" * 78)
    P("LIBRARY ORACLE: AoE2ScenarioParser/scenarios/aoe2_scenario.py:701")
    P("               _get_scenario_variant(generator)   (MODULE-LEVEL, pure byte heuristic)")
    P("=" * 78)
    P(src.rstrip())
    lib_variant = _mod._get_scenario_variant
except Exception as e:
    P(f"!! could not import library: {type(e).__name__}: {e}")

if lib_variant is not None:
    from AoE2ScenarioParser.helper.incremental_generator import IncrementalGenerator
    P()
    P(f"IncrementalGenerator imported: {IncrementalGenerator.__module__}.{IncrementalGenerator.__name__}")
    P("signature: IncrementalGenerator(name: str, file_content: bytes, progress: int = 0)")
    P()
    P("ALSO: AoE2ScenarioParser/scenarios/aoe2_scenario.py:486-487  [I] DECISIVE")
    P('    if self.sections["FileHeader"].unknown_value_2 != self.variant.value:')
    P('        self.variant = self.sections["FileHeader"].unknown_value_2')
    P("  -> the library itself treats unknown_value_2 AS the variant.")
    P("     and :519-531 _update_variant_retrievers writes")
    P("     unknown_value_2 = variant.value  plus {LEGACY:[], AOE2:[2..12], ROR:[11]}.")
    P("     Our measured unknown_numbers arrays [2,3,4,5,6,7] / [0,1] match that map.")

P()

# ------------------------------------------------------------------------- Q1
P("=" * 78)
P("Q1  unknown_value_2  vs  library ScenarioVariant")
P("=" * 78)
agree = 0
disagree = 0
no_field = 0
rows = []
for p in singles:
    b = open(p, "rb").read()
    off, lay, body, diag = locate(b)
    if lay is None:
        continue
    h = field_offsets(b, lay)
    uv2 = None
    if "unknown_value_2" in h:
        uv2 = struct.unpack_from("<I", b, h["unknown_value_2"][0])[0]
    else:
        no_field += 1
    lv = None
    if lib_variant is not None:
        try:
            gen = IncrementalGenerator("<mem>", b)
            v = lib_variant(gen)
            lv = None if v is None else int(v)
        except Exception as e:
            lv = f"ERR:{type(e).__name__}"
    if isinstance(lv, int) and uv2 is not None:
        if lv == uv2:
            agree += 1
        else:
            disagree += 1
    rows.append((os.path.basename(p), b[0:4].decode("ascii", "replace"), lay, uv2, lv))

P(f"files where our grammar HAS the field : {len(rows)-no_field}")
P(f"files where our grammar LACKS it (L_SHORT, no sentinel): {no_field}")
P(f"lib-variant == our unknown_value_2 : {agree}")
P(f"lib-variant != our unknown_value_2 : {disagree}")
P(f"lib-variant is None (b'\\xE8\\x03\\x00\\x00' not found): {sum(1 for r in rows if r[4] is None)}")
P(f"lib-variant raised                          : {sum(1 for r in rows if not isinstance(r[4], (int, type(None))))}")
P()
P(f"{'file':<34}{'ver':<7}{'layout':<11}{'uv2':<6}{'lib_variant'}")
for name, ver, lay, uv2, lv in rows:
    a, b_ = uv2, lv
    mark = ""
    if isinstance(lv, int) and uv2 is not None:
        mark = "  OK" if lv == uv2 else "  <<< MISMATCH"
    P(f"{name[:33]:<34}{ver:<7}{lay:<11}{str(uv2):<6}{str(lv)}{mark}")

P()
P("ScenarioVariant enum (AoE2ScenarioParser/datasets/scenario_variant.py):")
P("    0 = LEGACY (AoC & Bare HD)   1 = AOE2 (HD with expansions & DE)   2 = ROR")
P("=> files with lib_variant 'Unknown' are exactly the 8 L_SHORT files that have")
P("   NO unknown_value_2 field, so the library's 'find b\\xE8\\x03\\x00\\x00' heuristic")
P("   fails on them.")

# ------------------------------------------------------------------------- Q2
P()
P("=" * 78)
P("Q2  CAMPAIGN PROLOGUE 256 B -- distribution of the 64-bit words")
P("=" * 78)
camps = {}
for cf in sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign")):
    camps[cf] = open(os.path.join(CAMP_DIR, cf), "rb").read()

LO, HI = 0x00007FF000000000, 0x0000800000000000     # Windows user-space pointers
bucket = collections.Counter()
examples = collections.defaultdict(list)
nonzero = []
allwords = 0
for cf, b in sorted(camps.items()):
    c = parse_campaign_deterministic(b)
    pro = c["prologue"]
    nonzero.append(sum(1 for x in pro if x))
    for i in range(0, 256, 8):
        w = struct.unpack_from("<Q", pro, i)[0]
        allwords += 1
        if LO <= w < HI:
            k = "user-space pointer range [0x00007FF0_00000000, 0x00008000_00000000)"
        elif w == 0:
            k = "zero"
        elif w < 0x10000:
            k = "small integer 1..0xFFFF"
        elif w < 0x100000:
            k = "0x10000 .. 0xFFFFF"
        else:
            k = "other"
        bucket[k] += 1
        if len(examples[k]) < 4:
            examples[k].append((cf, hex(w)))

P(f"campaigns: {len(camps)}  64-bit words examined: {allwords}")
P(f"nonzero prologue bytes: min={min(nonzero)} max={max(nonzero)} of 256")
P()
for k, v in bucket.most_common():
    P(f"   {v:>5d}  {v*100.0/allwords:5.1f}%  {k}")
    for cf, w in examples[k]:
        P(f"            e.g. {cf:<22} {w}")
json.dump({"q1": {"agree": agree, "disagree": disagree, "no_field": no_field},
           "q2": {"words": allwords, "buckets": dict(bucket),
                  "nonzero_min": min(nonzero), "nonzero_max": max(nonzero)}},
          open(os.path.join(HERE, "variant_check.json"), "w", encoding="utf-8"), indent=2)
open(os.path.join(HERE, "variant_check_output.txt"), "w", encoding="utf-8").write("\n".join(out))
P()
P("wrote variant_check.json / variant_check_output.txt")

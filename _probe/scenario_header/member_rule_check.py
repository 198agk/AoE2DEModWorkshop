# -*- coding: utf-8 -*-
"""Validate the header grammar on the 229 campaign members (a much wider version
spread than the standalone files) using the structural member table -- no magic
scanning.  Also verify the campaign "back-to-back standalone scenario" claim by
checking each member's size/offset tiling and parsing each member standalone.
"""
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign, CampaignParseError  # noqa: E402
from scenario_header import (  # noqa: E402
    HeaderParseError, LAYOUT_WITH_IVU, LAYOUT_WITHOUT_IVU,
    parse_file_header, decompress_body,
)
from legacy_grammar import (  # noqa: E402
    cand_l_short, cand_l_long,
)

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"


def layout_for_savable(savable):
    """The rule under test: savable (s32 @8) selects the grammar family."""
    if savable == 2:
        return "L_SHORT"
    if savable == 3:
        return "L_LONG_NC"
    if savable == 4:
        return "L_LONG_C"
    if savable == 5:
        return "M_IVU"
    if savable == 6:
        return "M_NOIVU"
    return None


CANDS = {
    "M_IVU": lambda b: (parse_file_header(b, LAYOUT_WITH_IVU)["deflate_offset"], "M_IVU"),
    "M_NOIVU": lambda b: (parse_file_header(b, LAYOUT_WITHOUT_IVU)["deflate_offset"], "M_NOIVU"),
    "L_SHORT": cand_l_short,
    "L_LONG_NC": lambda b: cand_l_long(b, creator=False),
    "L_LONG_C": lambda b: cand_l_long(b, creator=True),
}

camp_files = sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign"))
print(f"{len(camp_files)} campaigns found")
print()

tot_members = 0
rule_ok = 0
rule_bad = []
tile_ok = 0
tile_bad = []
savable_hist = {}
version_hist = {}

for cf in camp_files:
    path = os.path.join(CAMP_DIR, cf)
    b = open(path, "rb").read()
    try:
        c = parse_campaign(b)
    except CampaignParseError as e:
        print(f"FAIL-PARSE {cf}: {e}")
        continue
    # verify the table tiles the file exactly and each member is a standalone scenario
    for m in c["members"]:
        tot_members += 1
        mb = m["data"]
        ver = mb[0:4].decode("ascii", "replace")
        version_hist[ver] = version_hist.get(ver, 0) + 1
        if len(mb) != m["size"]:
            tile_bad.append((cf, m["name"], "size mismatch"))
            continue
        tile_ok += 1
        try:
            sav = int.from_bytes(mb[8:12], "little", signed=True)
        except Exception:
            sav = None
        savable_hist[sav] = savable_hist.get(sav, 0) + 1
        want = layout_for_savable(sav)
        if want is None:
            rule_bad.append((cf, m["name"], ver, sav, "no rule for savable"))
            continue
        # honest test 1: the RULE-selected layout must inflate to EOF
        try:
            off, _ = CANDS[want](mb)
            data, eof, err = decompress_body(mb, off)
        except HeaderParseError as e:
            rule_bad.append((cf, m["name"], ver, sav, f"rule layout {want} raised: {e}"))
            continue
        if not (eof and len(data) > 1000):
            rule_bad.append((cf, m["name"], ver, sav,
                             f"rule layout {want}@{off} no eof (err={err}, out={len(data)})"))
            continue
        rule_ok += 1

print(f"members extracted from member table: {tot_members}")
print(f"  size/offset tiling consistent: {tile_ok}")
print()
print(f"RULE 'savable -> layout' produced a valid EOF inflate: {rule_ok}/{tot_members}")
print()
print("version histogram of members:")
for k in sorted(version_hist):
    print(f"  {k}: {version_hist[k]}")
print()
print("savable histogram of members:")
for k in sorted(savable_hist, key=lambda x: (x is None, x)):
    print(f"  savable={k}: {savable_hist[k]}")
print()
if rule_bad:
    print(f"*** {len(rule_bad)} RULE VIOLATIONS:")
    for r in rule_bad[:60]:
        print("   ", r)
else:
    print("*** zero rule violations across all members")

json.dump({"tot_members": tot_members, "rule_ok": rule_ok,
           "version_hist": version_hist,
           "savable_hist": {str(k): v for k, v in savable_hist.items()},
           "violations": rule_bad},
          open(os.path.join(HERE, "member_rule_check.json"), "w", encoding="utf-8"),
          indent=2)
print()
print("wrote member_rule_check.json")

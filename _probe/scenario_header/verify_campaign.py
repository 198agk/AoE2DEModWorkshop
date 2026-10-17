# -*- coding: utf-8 -*-
"""Validate campaign.py against ALL 42 shipped .aoe2campaign files, and check that
every extracted member is itself a valid standalone scenario (by locating its
RAW DEFLATE stream with scenario_header.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign, CampaignParseError  # noqa: E402
from scenario_header import locate_deflate               # noqa: E402

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"
OUT = os.path.join(HERE, "campaign_parse_results.txt")

rows = []
files = sorted(f for f in os.listdir(CAMP_DIR) if f.endswith(".aoe2campaign"))
print(f"campaign files found: {len(files)}")

n_ok = n_fail = 0
member_total = member_ok = 0
count_field_offsets = {}
junk_lens = {}
version_hist = {}

with open(OUT, "w", encoding="utf-8") as log:
    for name in files:
        p = os.path.join(CAMP_DIR, name)
        b = open(p, "rb").read()
        try:
            c = parse_campaign(b)
        except CampaignParseError as e:
            n_fail += 1
            rows.append((name, "PARSE_FAIL", str(e), 0, 0))
            log.write(f"FAIL {name}: {e}\n")
            continue
        n_ok += 1
        count_field_offsets[c["count_field_offset"]] = count_field_offsets.get(c["count_field_offset"], 0) + 1
        junk_lens[c["header_junk_len"]] = junk_lens.get(c["header_junk_len"], 0) + 1
        m_ok = 0
        detail = []
        for m in c["members"]:
            member_total += 1
            h, data, diag = locate_deflate(m["data"])
            if h is not None:
                member_ok += 1
                m_ok += 1
                version_hist[h["version"]] = version_hist.get(h["version"], 0) + 1
                detail.append(f"{m['name']}:v{h['version']}:off={h['deflate_offset']}:out={len(data)}")
            else:
                detail.append(f"{m['name']}:FAIL({diag.get('reason')})")
        rows.append((name, "OK", f"{c['member_count']} members, {m_ok} located",
                     c["member_count"], m_ok))
        log.write(f"OK   {name}  version={c['version']} count={c['member_count']} "
                  f"count_off={c['count_field_offset']} junk={c['header_junk_len']} "
                  f"located={m_ok}/{c['member_count']}\n")
        for d in detail:
            log.write(f"       {d}\n")

print(f"campaigns parsed OK = {n_ok}, failed = {n_fail}")
print(f"members total = {member_total}, deflate located = {member_ok}")
print(f"count_field_offsets = {count_field_offsets}")
print(f"header_junk_lens = {junk_lens}")
print(f"member version histogram = {dict(sorted(version_hist.items()))}")
print(f"log -> {OUT}")
for r in rows:
    if r[1] != "OK":
        print(" ", r)

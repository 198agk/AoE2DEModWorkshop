# -*- coding: utf-8 -*-
"""Resolve the CivTechTrees vs strings-DB discrepancy and quantify it.

Finding: for the 6 Chronicles civs the CivTechTrees JSON `Name` field holds the
BASE-GAME label while its own `Name String ID` points at a paphos (Chronicles)
string.  Example ACHAEMENIDS node 4: Name="Archer", Name String ID=405052, and
405052 in key-value-paphos-strings-utf8.txt is literally "Bowman"/"弓兵".
The JSON is internally inconsistent; the string file is authoritative.
"""
import json
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strings_db import load_language  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
units = json.load(open(os.path.join(HERE, "unit_names.json"), encoding="utf-8"))
en, _ = load_language("en")

CT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\CivTechTrees"

node_state = collections.Counter()
agree = disagree = 0
dis_by_civ = collections.Counter()
disagreements = []
for fn in sorted(os.listdir(CT)):
    d = json.load(open(os.path.join(CT, fn), encoding="utf-8"))
    for key in ("civ_techs_units", "civ_techs_buildings"):
        for node in d.get(key, []):
            nid = node.get("Node ID")
            nsid = node.get("Name String ID")
            nm = node.get("Name")
            if not isinstance(nid, int):
                node_state["node id not an int"] += 1
                continue
            if str(nid) not in units:
                node_state["node id not a dat unit id"] += 1
                continue
            e = units[str(nid)]
            if e["name_string_id"] == nsid:
                node_state["sid == our canonical sid"] += 1
                got = e["en"]
            elif e.get("civ_variants") and str(nsid) in e["civ_variants"]:
                node_state["sid == one of our civ variants"] += 1
                got = e["civ_variants"][str(nsid)]["en"]
            else:
                node_state["sid reachable neither way"] += 1
                continue
            if got == nm:
                agree += 1
            else:
                disagree += 1
                dis_by_civ[fn] += 1
                disagreements.append((fn, nid, nsid, nm, got))

print("node classification:")
for k, v in node_state.most_common():
    print("   %-34s %6d" % (k, v))
print()
print("agree: %d ; disagree: %d" % (agree, disagree))
print("disagreements by civ file:")
for k, v in dis_by_civ.most_common():
    print("   %-24s %4d" % (k, v))

# The decisive test: for each disagreement, does the string file agree with us?
print()
print("decisive check - does the raw string file back US or the JSON's Name field?")
backed_us = backed_json = neither = 0
for fn, nid, nsid, nm, got in disagreements:
    raw = en.get(nsid)
    if raw == got:
        backed_us += 1
    elif raw == nm:
        backed_json += 1
    else:
        neither += 1
print("   string file says OUR value : %d" % backed_us)
print("   string file says JSON value: %d" % backed_json)
print("   neither                    : %d" % neither)
print()
print("first 15 disagreements with the raw string:")
for fn, nid, nsid, nm, got in disagreements[:15]:
    print("   %-20s node %-5s sid %-7s json=%-20r ours=%-20r raw=%-20r"
          % (fn, nid, nsid, nm, got, en.get(nsid)))

# Are ALL disagreements Chronicles civs?
chron = {"ACHAEMENIDS", "ATHENIANS", "MACEDONIANS", "PURU", "SPARTANS", "THRACIANS"}
non = [d for d in disagreements if d[0].replace(".json", "") not in chron]
print()
print("disagreements NOT in a Chronicles civ: %d" % len(non))
for d in non[:10]:
    print("   ", d)

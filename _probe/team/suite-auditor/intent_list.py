# -*- coding: utf-8 -*-
"""List declared intents and their declared compile strategies."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
p = os.path.join(ROOT, "aoe2mod", "schema", "intents.json")
with open(p, encoding="utf-8") as f:
    doc = json.load(f)
intents = doc["intents"]
print("schema_version", doc.get("schema_version"))
print("targets", doc.get("targets_dat_version"))
print("count", len(intents))
print()
for k, v in intents.items():
    comp = v.get("compile", {}) or {}
    strat = comp.get("strategy", "")
    fields = ",".join(sorted((v.get("fields") or {}).keys()))
    print("%-34s %-16s applies=%-10s strat=%-22s fields=%s"
          % (k, str(v.get("title_en"))[:34], str(v.get("applies_to")), strat, fields))

# -*- coding: utf-8 -*-
"""Dump the mod manager status file verbatim so the pre-flight check is exact."""
import json, os, sys

P = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\mod-status.json"
raw = open(P, "rb").read()
s = raw.decode("utf-8-sig")
o = json.loads(s)
print("file      :", P)
print("bytes     :", len(raw))
print("top keys  :", list(o.keys()))
for k, v in o.items():
    if k.lower() == "mods":
        print("Mods      :", len(v), "entries")
        for e in v:
            if isinstance(e, dict):
                print("   -", json.dumps(e, ensure_ascii=False))
            else:
                print("   -", e)
    else:
        print(k, "=", json.dumps(v, ensure_ascii=False)[:300])

print()
print("=== is the Smoke5 mod registered? ===")
blob = s.lower()
for probe in ("smoke5", "smoke 5", "treevspanel", "tree vs panel"):
    print("  %-16s in file: %s" % (probe, probe in blob))
print("  'local//'       entries:", [e for e in (o.get("Mods") or []) if str(e.get("Path", e.get("path", ""))).startswith("local//")])

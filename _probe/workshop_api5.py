"""Find the POST body shape the site uses for /Find, and probe it.

405 on GET => POST. Look for the axios/fetch call sites in the bundle.

Read-only.
"""
import json
import os
import re
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
t = open(os.path.join(OUT, "main.f91b17.js"), encoding="utf-8", errors="replace").read()

print("=== call sites: modsFind ===")
for m in re.finditer(r"modsFind", t):
    a, b = max(0, m.start() - 400), m.start() + 400
    print("---")
    print(t[a:b].replace("\n", " "))

print()
print("=== words near 'Find' that look like body fields ===")
for key in ("gameTitleId", "pageSize", "pageNumber", "modTypeId", "searchText",
            "searchString", "sortOrder", "sortColumn", "isAscending", "pagination"):
    n = t.count(key)
    if n:
        print("   %-16s %d" % (key, n))

print()
print("=== context around first gameTitleId ===")
m = re.search(r"gameTitleId", t)
if m:
    a, b = max(0, m.start() - 500), m.start() + 500
    print(t[a:b].replace("\n", " "))

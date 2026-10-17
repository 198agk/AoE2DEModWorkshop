"""Find how the bundle builds mod API URLs: which suffixes, query params, and
auth headers it uses.

Read-only.
"""
import os
import re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
t = open(os.path.join(OUT, "main.f91b17.js"), encoding="utf-8", errors="replace").read()

print("=== occurrences of the mods base variable F (= V+'\"/api/v4/mods\"') ===")
for m in re.finditer(r"\bF\s*\+", t):
    a, b = max(0, m.start() - 120), m.start() + 220
    print("---", t[a:b].replace("\n", " ")[:330])

print()
print("=== string literals starting with '/' near 'mods' ===")
for m in sorted(set(re.findall(r"['\"](/[A-Za-z0-9_\-/{}$.]{1,60})['\"]", t))):
    if any(k in m.lower() for k in ("mod", "tag", "search", "list", "like", "rate", "review", "download", "publish", "subscribe", "install", "user", "auth", "token", "login")):
        print("   ", m)

print()
print("=== likely query-parameter names ===")
for k in ("pageSize", "page_number", "pageNumber", "orderBy", "order_by", "sortBy",
          "sort_by", "searchTerm", "searchterm", "search_term", "modName", "tagIds",
          "tags=", "types=", "civilization", "sort=", "order=", "count=", "offset=",
          "limit=", "title=", "author=", "keyword"):
    n = t.count(k)
    if n:
        print("   %-18s %d" % (k, n))

print()
print("=== context for 'modsFind' / 'modsMine' (the UI strings near the fetch) ===")
for key in ("modsFind", "modsMine", "modsFeatured", "modsTags", "modsTypes"):
    m = re.search(re.escape(key), t)
    if m:
        a, b = max(0, m.start() - 300), m.start() + 300
        print("---", key)
        print(t[a:b].replace("\n", " ")[:560])

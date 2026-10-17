"""Pin down HOW the website authenticates to api.ageofempires.com.

`withCredentials` appears 3x in the bundle -> cookies. Find the request helper
`gt(...)` and its credential handling.

Read-only.
"""
import os
import re

BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "workshop", "main.f91b17.js")
t = open(BUNDLE, encoding="utf-8", errors="replace").read()

print("=" * 104)
print("withCredentials occurrences")
print("=" * 104)
for m in re.finditer(r"withCredentials", t):
    a, b = max(0, m.start() - 400), m.start() + 300
    print("---")
    print(t[a:b].replace("\n", " "))

print()
print("=" * 104)
print("the request helper: search for 'function gt(' and 'gt=' definitions")
print("=" * 104)
for pat in (r"function gt\s*\(", r"\bgt\s*=\s*function", r"\bgt\s*=\s*\(", r"const gt\s*=",
            r"var gt\s*=", r"let gt\s*="):
    for m in re.finditer(pat, t):
        a, b = max(0, m.start() - 100), m.start() + 900
        print("--- %s" % pat)
        print(t[a:b].replace("\n", " ")[:1000])

print()
print("=" * 104)
print("nonce / X-WP-Nonce / security tokens in the bundle")
print("=" * 104)
for k in ("nonce", "Nonce", "X-WP-Nonce", "wp_object", "user_logged_in",
          "security", "apiNonce", "ajax_nonce"):
    n = t.count(k)
    if n:
        print("  %-18s %d" % (k, n))
m = re.search(r"wp_object", t)
if m:
    a, b = max(0, m.start() - 200), m.start() + 600
    print("--- wp_object context:")
    print(t[a:b].replace("\n", " ")[:800])

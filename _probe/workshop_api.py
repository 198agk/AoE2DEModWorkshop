"""Extract the mod-workshop API surface from the site's main bundle.

Read-only.
"""
import os
import re
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

URL = "https://www.ageofempires.com/wp-content/themes/ageOfEmpires/public/js/main.f91b17.js"
req = urllib.request.Request(URL, headers={"User-Agent": UA})
with urllib.request.urlopen(req, timeout=40) as r:
    t = r.read().decode("utf-8", "replace")
print("bundle bytes:", len(t))
open(os.path.join(OUT, "main.f91b17.js"), "w", encoding="utf-8").write(t)

# full URLs
print()
print("=== absolute / base URLs containing api or webapi ===")
for m in sorted(set(re.findall(r"https?://[A-Za-z0-9_.\-/]*(?:api|webapi)[A-Za-z0-9_.\-/]*", t))):
    print("   ", m)

print()
print("=== every occurrence of /api/v4/mods with context ===")
for m in re.finditer(r"/api/v4/mods", t):
    a, b = max(0, m.start() - 260), m.start() + 260
    print("---")
    print(t[a:b].replace("\n", " "))

print()
print("=== every occurrence of webapi with context ===")
seen = 0
for m in re.finditer(r"webapi", t):
    a, b = max(0, m.start() - 220), m.start() + 220
    print("---", seen)
    print(t[a:b].replace("\n", " "))
    seen += 1
    if seen >= 8:
        break

print()
print("=== template-literal paths mentioning mods ===")
for m in sorted(set(re.findall(r"`[^`]{0,80}mods[^`]{0,80}`", t)))[:40]:
    print("   ", m[:150])

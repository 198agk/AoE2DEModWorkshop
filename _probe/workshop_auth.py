"""Why 401 with 0 bytes? The gateway wants a header the website sends.

Look for API-key / auth-header names and the mods HTTP client setup in the exe,
plus what the website bundle sends (axios defaults).

Read-only.
"""
import os
import re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
raw = open(EXE, "rb").read()
BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "workshop", "main.f91b17.js")
t = open(BUNDLE, encoding="utf-8", errors="replace").read()

print("=" * 104)
print("A) header-ish names in the exe (near HTTP strings)")
print("=" * 104)
seen = set()
for pat in (rb"x-api-key", rb"X-Api-Key", rb"api-key", rb"apiKey", rb"apikey",
            rb"Authorization", rb"Bearer", rb"x-access-token", rb"X-Auth",
            rb"Subscription-Key", rb"Ocp-Apim-Subscription-Key", rb"x-functions-key"):
    for m in re.finditer(re.escape(pat), raw):
        a, b = max(0, m.start() - 60), m.start() + 90
        s = raw[a:b]
        strs = " | ".join(x.decode("ascii", "replace") for x in re.findall(rb"[\x21-\x7e]{4,}", s))
        key = (pat, m.start())
        if key in seen:
            continue
        seen.add(key)
        print("  %-28s @0x%08X  %s" % (pat.decode(), m.start(), strs[:200]))

print()
print("=" * 104)
print("B) the exe's HTTP header-building strings (Content-Type etc.)")
print("=" * 104)
i = raw.find(b"api/v1/Mods/Find/")
if i > 0:
    for a, b, lbl in ((i - 4000, i, "BEFORE Find"),
                      (i, i + 4000, "AFTER Find")):
        print("--- %s ---" % lbl)
        for s in re.findall(rb"[\x20-\x7e]{4,}", raw[a:b]):
            d = s.decode("ascii")
            if any(k in d for k in ("Content-Type", "application/json", "User-Agent",
                                    "Accept", "auth", "Auth", "token", "Token",
                                    "key", "Key", "header", "Header", "POST", "GET",
                                    "http", "Http", "HTTP")):
                print("    %s" % d[:170])

print()
print("=" * 104)
print("C) what does the WEBSITE bundle set as default headers?")
print("=" * 104)
for k in ("xsrf", "XSRF", "X-XSRF", "withCredentials", "Authorization",
          "Bearer", "apiKey", "api-key", "x-api", "headers:"):
    n = t.count(k)
    if n:
        print("  %-20s %d" % (k, n))
for m in list(re.finditer(r"headers\s*:\s*\{[^}]{0,220}\}", t))[:6]:
    print("  ---")
    print("  %s" % m.group(0).replace("\n", " ")[:230])
for m in list(re.finditer(r"withCredentials\s*:\s*\w+", t))[:6]:
    print("  %s" % m.group(0))

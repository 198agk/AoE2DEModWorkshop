"""The game client's own mod-manager API surface.

The exe talks to the same backend with Steam auth. Its string table is the
authoritative list of endpoints the *game* uses (not just the website).

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
raw = open(EXE, "rb").read()
print("exe bytes: %d" % len(raw))

print()
print("=== URLs / hosts in the exe ===")
urls = set()
for m in re.finditer(rb"https?://[\x21-\x7e]{4,120}", raw):
    urls.add(m.group().decode("ascii"))
for u in sorted(urls):
    print("   %s" % u)

print()
print("=== api-ish path fragments ===")
frags = set()
for m in re.finditer(rb"/[\x21-\x7e]{2,90}", raw):
    s = m.group().decode("ascii", "replace")
    if re.search(r"/(api|mods|webapi|ugc|v[0-9])", s) and " " not in s:
        frags.add(s)
for f in sorted(frags)[:80]:
    print("   %s" % f)
print("   -> %d fragments" % len(frags))

print()
print("=== 'ageofempires' host mentions with context ===")
for m in re.finditer(rb"ageofempires\.com", raw):
    a, b = max(0, m.start() - 90), m.start() + 90
    ctx = raw[a:b]
    strs = re.findall(rb"[\x21-\x7e]{6,}", ctx)
    print("   0x%08X: %s" % (m.start(), b" | ".join(strs)[:190].decode("ascii", "replace")))

print()
print("=== mod-manager HTTP-facing symbols ===")
for probe in (b"api/v4", b"/v4/mods", b"GetPublishedFileDetails", b"ISteamRemoteStorage",
              b"steamcommunity", b"api.steampowered", b"ModManager::", b"FetchModList",
              b"GetModList", b"WorkshopID", b"PublishID", b"ModDb", b"mod_db"):
    hits = [m.start() for m in re.finditer(re.escape(probe), raw)]
    print("   %-26s %d  %s" % (probe.decode(), len(hits), [hex(h) for h in hits[:5]]))

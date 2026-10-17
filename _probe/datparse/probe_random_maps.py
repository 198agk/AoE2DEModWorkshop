"""Does any real dataset carry a non-empty RandomMaps section?

The data-mod catalogue flags the RandomMaps MapInfo body as "the largest
untested path" because BASE has count == 0 and the writer has therefore never
executed that branch against real data.

NOTE: do NOT use Parser.parse(stop_after=4) here -- parse_dat._stage() implements
`stop_after` with `raise SystemExit(0)`, which terminates the whole interpreter
and would silently truncate this script's output.  Parse fully instead, and
instrument read_random_maps to learn the section's byte span.
"""
import os
import sys
import contextlib
import io

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import parse_dat as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USERMODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"

TARGETS = [
    ("BASE", os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MODE_Pompeii", os.path.join(GAME, r"modes\Pompeii\resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_297820", os.path.join(USERMODS, "297820_10 倍资源文明联盟3倍科技",
                                r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_423821", os.path.join(USERMODS, "423821_四月-juntuanzhangtianfumozu军团长天赋模组",
                                r"resources\_common\dat\empires2_x2_p1.dat")),
    ("MOD_550749", os.path.join(USERMODS, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48",
                                r"resources\_common\dat\empires2_x2_p1.dat")),
]

# instrument the RandomMaps reader to capture its byte span
_SPANS = {}
_orig = P.read_random_maps


def _wrapped(r):
    start = r.pos
    out = _orig(r)
    _SPANS["start"] = start
    _SPANS["end"] = r.pos
    return out


P.read_random_maps = _wrapped

print("%-14s %-10s %-9s %-22s %s"
      % ("target", "version", "rm_count", "section bytes", "note"))
print("-" * 92)
for name, path in TARGETS:
    if not os.path.exists(path):
        print("%-14s MISSING" % name)
        continue
    _SPANS.clear()
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    ver = p.stats.get("file_version", "?")
    rmaps = p.stats.get("random_maps") or {}
    cnt = rmaps.get("count")
    span = (_SPANS.get("end", 0) - _SPANS.get("start", 0)) if _SPANS else 0
    note = "EMPTY -- nothing to exercise" if not cnt else "*** NON-EMPTY ***"
    print("%-14s %-10s %-9s %-22s %s" % (name, ver, cnt, span, note))
    if cnt:
        for m in rmaps.get("maps", []):
            print("      map_id=%r io_all=%r" % (m.get("map_id"), m.get("io_all")))

print()
print("byte span of an empty RandomMaps section = u32 count + i32 ptr = 8 bytes")

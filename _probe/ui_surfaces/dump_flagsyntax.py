import re, io, collections

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

# 1) Look for command-line parsing hints near the flag table
lo, hi = 0x3258a00, 0x3259a00
seg = data[lo:hi]
w("### raw hex view of flag table region, looking for separator chars ###\n")
# Strings are usually NUL separated. Show the actual byte layout between desc and flag
for m in re.finditer(rb"[\x20-\x7e]{12,}", seg):
    s = m.group()
    tail = seg[m.end():m.end() + 8]
    if b"-" in tail or b"/" in tail or b"=" in tail:
        w("  @0x%08x %r  then %r\n" % (lo + m.start(), s[:60], tail))

# 2) Search whole exe for common flag-prefix conventions
w("\n### prefix probes (raw bytes) ###\n")
probes = [b"-EXIT", b"/EXIT", b"--EXIT", b"EXIT=", b"-exit", b"/exit", b"--exit",
          b"-NO_WINDOW", b"/NO_WINDOW", b"NO_WINDOW=", b"-RANDOMMAP", b"/RANDOMMAP",
          b"-GAM", b"/GAM", b"-EDITOR", b"/EDITOR", b"-RUN_REGRESSION_TESTS",
          b"-LAUNCH_GAME_VARIANT", b"-MORE_MAP_SIZES", b"-WRITE_MAP_INFO"]
for p in probes:
    n = data.count(p)
    if n:
        off = data.find(p)
        w("  FOUND %-26s x%d  first@0x%x\n" % (p.decode(), n, off))

# 3) Any string that looks like a usage/help line
w("\n### usage / help-like strings ###\n")
for m in re.finditer(rb"[\x20-\x7e]{10,200}", data):
    s = m.group().decode("ascii", "ignore")
    if re.search(r"(?i)\b(usage|command line|commandline|switches|parameters|arguments|options are)\b", s):
        if not re.search(r"[{}|\\^~]", s):
            w("  0x%08x  %s\n" % (m.start(), s[:180]))

# 4) The dash/flag-parsing helper strings
w("\n### strings mentioning 'flag' or 'switch' or 'argv' ###\n")
seen = set()
for m in re.finditer(rb"[\x20-\x7e]{8,160}", data):
    s = m.group().decode("ascii", "ignore")
    if re.search(r"(?i)\b(argv|argc|switch|prefs|preference|command.?line)\b", s) and not re.search(r"[{}|\\^~]", s):
        if s not in seen:
            seen.add(s)
            w("  0x%08x  %s\n" % (m.start(), s[:170]))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_flagsyntax.txt", "w", encoding="utf-8").write(txt)
print(txt[:5000])

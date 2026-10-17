import re, io

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

# Find all English "help text" runs (sentences that look like CLI/app option descriptions)
desc_pat = re.compile(
    rb"(?:Specify|Run |Request|Enable|Disable|Set |Use |Force|Override|Print|Log|Select|"
    rb"Toggle|Load |Play |Start|Changes|Verbose|Turn |Modify|Show |Write|Skip|Only|"
    rb"Determines|Whether|When |Tool |Game |Allows)[\x20-\x7e]{15,150}"
)

hits = [(m.start(), m.group().decode("ascii")) for m in desc_pat.finditer(data)]
w("### English help-text runs: %d\n" % len(hits))

# For each, look backwards up to 120 bytes for an ALLCAPS token (the flag name)
tok = re.compile(rb"[A-Z][A-Z0-9_]{4,40}")
rows = []
for off, s in hits:
    back = data[max(0, off - 160):off]
    toks = tok.findall(back)
    flag = toks[-1].decode("ascii") if toks else "?"
    rows.append((off, flag, s))

w("\n### flag -> help text (grouped by offset) ###\n")
for off, flag, s in rows:
    w("0x%08x  %-34s %s\n" % (off, flag, s[:140]))

# Also: dedicated window around key tool flags
for centre, label in [(0x334e7a0, "REGRESSION tool flags"), (0x32590e0, "REGRESSION_TESTS flag"),
                      (0x3258f00, "area A"), (0x3259380, "area B"), (0x3259800, "area C")]:
    w("\n########## %s around 0x%x ##########\n" % (label, centre))
    lo, hi = centre - 0x200, centre + 0x1A00
    seg = data[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{6,}", seg):
        s = m.group().decode("ascii")
        if re.search(r"[a-z]{3,}.*[a-z]{3,}", s) and not re.search(r"[<>{}|\\^~\[\]]{3,}", s):
            w("  0x%08x  %s\n" % (lo + m.start(), s[:170]))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_flags.txt", "w", encoding="utf-8").write(txt)
print("ok len", len(txt))

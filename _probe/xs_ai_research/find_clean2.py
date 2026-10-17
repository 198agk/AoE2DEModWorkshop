import io, os, glob, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))
BAD = [0x9225, 0x922B, 0x922E, 0xE6C6, 0xE6D5, 0x6402, 0x947E, 0x7D66]

def load(p):
    try:
        return io.open(p, encoding='utf-8', errors='replace', newline='').read()
    except Exception:
        return None

files = {}
for p in glob.glob(os.path.join(D, '*.md')) + glob.glob(os.path.join(D, '*.txt')):
    t = load(p)
    if t:
        files[os.path.basename(p)] = t

probes = [
    ("L1",   "AI Scripting",            "AIREF Reference Extract"),
    ("L72",  "File roles",              "honesty note"),
    ("L85",  "an extension",            "interpreter adds them"),
    ("L114", "one of the facts",        "the other is false"),
    ("L116", "defglobal",               "documented? NO"),
    ("L118", "separate compile-time",   "text token, not a"),
    ("L133", "Every command",           "wrapped in its"),
    ("L137", "address rules by those",  "load"),
    ("L154", "command examples",        "the site's"),
    ("L203", "Defconsts, Goals, and SNs", "Part 1"),
    ("L231", "2,147,483,648",           "2^31"),
    ("L235", "characters in a comment", "Otherwise your script"),
    ("L256", "with a descriptive sentence", "see"),
    ("L257", "Downloaded but not re-tabulated", "scenario"),
    ("L259", "of text",                 "pure JS shells"),
    ("L270", "ParameterName",           "positional"),
]
for tag, a, b in probes:
    print(f"\n=== {tag}: {a!r} .. {b!r} ===")
    hit = False
    for n, t in sorted(files.items()):
        if a not in t:
            continue
        if b and b not in t:
            continue
        for m in [i for i in range(len(t)) if t.startswith(a, i)][:3]:
            hit = True
            print(f"  {n}: {t[max(0,m-50):m+130]}")
    if not hit:
        print("   (no file contains this fragment)")

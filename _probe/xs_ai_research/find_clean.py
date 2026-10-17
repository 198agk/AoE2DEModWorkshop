import io, os, glob, re

D = os.path.dirname(os.path.abspath(__file__))
BAD = [0x9225, 0x922B, 0x922E, 0xE6C6, 0xE6D5, 0x6402, 0x947E, 0x7D66]

def load(p):
    try:
        return io.open(p, encoding='utf-8', errors='replace', newline='').read()
    except Exception as e:
        return None

files = {}
for p in glob.glob(os.path.join(D, '*.md')) + glob.glob(os.path.join(D, '*.txt')) + glob.glob(os.path.join(D, '*.json')):
    t = load(p)
    if t:
        files[os.path.basename(p)] = t

print("=== files with ZERO corruption markers ===")
for n, t in sorted(files.items()):
    bad = sum(1 for ch in t if ord(ch) in BAD)
    if bad == 0 and len(t) > 5000:
        print(f"  {n:48} chars={len(t)}")

# probe fragments around each ambiguous site
probes = [
    ("L1",   "AI Scripting", "AIREF Reference Extract"),
    ("L72",  "File roles", None),
    ("L85",  "an extension", "the interpreter adds them"),
    ("L100", "defrule", "Defines the start of a new rule"),
    ("L114", "one of the facts", "is true and the other is false"),
    ("L116", "defglobal", "documented? NO"),
    ("L118", "namespace", "text token, not a"),
    ("L133", "Every command", "is wrapped in its"),
    ("L137", "address rules by those ids", "load"),
    ("L154", "command examples", "the site's"),
    ("L203", "Defconsts, Goals, and SNs", "Part 1"),
    ("L231", "2,147,483,648", "2^31"),
    ("L235", "characters in a comment", "Otherwise your script"),
    ("L259", "of text", "pure JS shells"),
    ("L270", "dir:Type ParameterName", "positional"),
]
for tag, a, b in probes:
    print(f"\n=== probe {tag}: {a!r} ... {b!r} ===")
    for n, t in sorted(files.items()):
        if a not in t:
            continue
        if b and b not in t:
            continue
        # show the window
        i = t.find(a)
        print(f"  {n}: {t[max(0,i-60):i+120]!r}")

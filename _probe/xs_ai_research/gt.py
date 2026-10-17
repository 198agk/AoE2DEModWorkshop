import io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

def rd(n):
    return io.open(os.path.join(D, n), encoding='utf-8', errors='replace', newline='').read()

js = rd('raw_commands.js')

print("=== GROUND TRUTH: load description (L85 site) ===")
i = js.find('The .per file extension is not needed')
print(repr(js[i-700:i+300]))

print("\n=== GROUND TRUTH: defrule description (L138 site) ===")
i = js.find('Each rule is limited to')
print(repr(js[i-900:i+300]))

print("\n=== GROUND TRUTH: xnor / xor descriptions (L114 site) ===")
for m in re.finditer(r'one of the facts', js):
    print(repr(js[max(0,m.start()-300):m.start()+220]))
    print('---')

print("\n=== GROUND TRUTH: data-limits guide (L227, L240) ===")
g = rd('txt_guide_data-limits.txt')
print(g)

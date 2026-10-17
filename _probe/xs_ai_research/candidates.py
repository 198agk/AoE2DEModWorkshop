import sys, io, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

def sim(o):
    """Encode candidate original as UTF-8, then mis-decode as GBK (cp936)."""
    return o.encode('utf-8').decode('gbk', 'replace')

old = io.open(os.path.join(D, 'AI_SCRIPTING_AIREF.corrupt.bak.md'),
              encoding='utf-8', newline='').read()
js  = io.open(os.path.join(D, 'raw_commands.js'),
              encoding='utf-8', errors='replace', newline='').read()

tests = {
 'L85  an extension': [
    'an extension\u2014 the interpreter adds them',
    'an extension \u2014 the interpreter adds them',
    'an extension \u2014the interpreter adds them',
    'an extension-- the',
 ],
 'L114 one of the facts': [
    'one of the facts\u2014 is true',
    'one of the facts \u2014 is true',
    'one of the facts\u2026is true',
 ],
 'L138 UP': [
    "in UP\u2014 'Elements'",
    "in UP \u2014 'Elements'",
    "in UP. 'Elements'",
 ],
 'L138 operators': [
    'operators\u2014 In UP',
    'operators \u2014 In UP',
 ],
 'L227 313-511': [
    '(313-511 carry no',
    '(313\u2013511 carry no',
    '(313\u2014511 carry no',
 ],
 'L240 goals 1-40': [
    'goals 1-40 cannot',
    'goals 1\u201340 cannot',
    'goals 1\u201440 cannot',
 ],
 'L240 511 and 512': [
    'avoid goals 511 and 512 for point',
    'avoid goals 511-512 for point',
    'avoid goals 511\u2013512 for point',
 ],
 'L240 509-512': [
    'and 509-512 for the four',
    'and 509\u2013512 for the four',
    'and 509\u2014512 for the four',
 ],
 'L259 0-1,222': [
    'Strip to **0-1,222 chars**',
    'Strip to **0\u20131,222 chars**',
    'Strip to **0\u20141,222 chars**',
    'Strip to **0 chars**',
 ],
}
for tag, cands in tests.items():
    print(f"\n=== {tag} ===")
    for c in cands:
        r = sim(c)
        print(f"   {sim(c)!r:60}  <- {c!r}")

print("\n\n=== AIREF source: 'Notice that the filename' ===")
i = js.find('Notice that the filename')
print(repr(js[i-200:i+240]) if i >= 0 else '  NOT FOUND')

print("\n=== AIREF source: 'elements in UP' ===")
for m in [i for i in range(len(js)) if js.startswith('elements in UP', i)][:3]:
    print(repr(js[m-160:m+200]))

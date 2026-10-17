"""Parse raw_functions.txt and raw_constants.txt into structured JSON, so the
final markdown reference can be assembled mechanically without retyping."""
import os, re, json
os.environ.setdefault('PYTHONIOENCODING','utf-8')
import sys
sys.stdout.reconfigure(encoding='utf-8')

OUT = os.path.dirname(os.path.abspath(__file__))

def rd(name):
    with open(os.path.join(OUT,name), encoding='utf-8') as f:
        return f.read()

# ---------------- FUNCTIONS ----------------
ft = rd('raw_functions.txt')
# Drop the leading index (list of bare function names, one per line)
body_start = ft.find('1. Rules')
# find the section heading occurrence that begins the reference body: the line '1. Rules' followed by '1.1.'
m = re.search(r'(?m)^1\. Rules\s*\n', ft)
# there are two 'Rules' lines; body begins after the last occurrence of '1. Rules'
idxs = [mm.start() for mm in re.finditer(r'(?m)^1\. Rules', ft)]
body_start = idxs[-1]
body = ft[body_start:]

TRIM = r'[\s\u00b6]*$'
# Sections: lines like "7. Player" (mkdocs appends a pilcrow anchor '¶')
sec_re = re.compile(r'(?m)^(\d+)\. ([A-Za-z][^\n]*?)' + TRIM)
# Entries: "7.1. xsEffectAmount"
ent_re = re.compile(r'(?m)^(\d+)\.(\d+)\. ([A-Za-z_][A-Za-z0-9_]*)' + TRIM)

secs = [(mm.start(), int(mm.group(1)), mm.group(2).strip()) for mm in sec_re.finditer(body)]
ents = [(mm.start(), mm.group(3).strip()) for mm in ent_re.finditer(body)]

# Build entry dicts by slicing body between entry starts
entries = []
for i,(pos,name) in enumerate(ents):
    end = ents[i+1][0] if i+1 < len(ents) else len(body)
    # also stop at the next SECTION heading, so a section title never leaks into the
    # last entry's description (e.g. "... <br>14. Damage Class")
    for spos, snum, sname in secs:
        if pos < spos < end:
            end = spos
    chunk = body[pos:end]
    # section this entry belongs to = last section whose start < pos
    secname = 'Uncategorised'
    for spos, snum, sname in secs:
        if spos < pos:
            secname = sname
        else:
            break
    proto = re.search(r'Prototype:\s*`([^`]+)`', chunk)
    rtype = re.search(r'Returning Type:\s*`([^`]+)`', chunk)
    # description = text after the parameters list, before next entry
    lines = chunk.split('\n')
    # gather description: lines that are not 'Returning Type', 'Prototype', 'Parameters:', param bullets
    desc_lines = []
    started = False
    for ln in lines[1:]:
        s = ln.strip()
        if s.startswith('Returning Type:') or s.startswith('Prototype:') or s == 'Parameters:':
            started = True
            continue
        if not started:
            continue
        if re.match(r'^\(?Optional\)?', s) and s.startswith('(Optional)'):
            desc_lines.append(s)
            continue
        if s.startswith('`') and ':' in s and not s.startswith('```'):
            # parameter line
            continue
        desc_lines.append(s)
    desc = '\n'.join(desc_lines).strip()
    desc = re.sub(r'\n{2,}', '\n', desc)
    entries.append({
        'section': secname,
        'name': name,
        'returning': rtype.group(1).strip() if rtype else None,
        'prototype': proto.group(1).strip() if proto else None,
        'desc': desc,
    })

# ---------------- CONSTANTS ----------------
ct = rd('raw_constants.txt')
sidx = [mm.start() for mm in re.finditer(r'(?m)^1\. File Io', ct)]
cbody = ct[sidx[-1]:] if sidx else ct
csecs = [(mm.start(), int(mm.group(1)), mm.group(2).strip()) for mm in sec_re.finditer(cbody)]
# constant entries: "1.1. cOffsetString"
cent_re = re.compile(r'(?m)^(\d+)\.(\d+)\. ([A-Za-z_][A-Za-z0-9_]*)' + TRIM)
cents = [(mm.start(), mm.group(3).strip()) for mm in cent_re.finditer(cbody)]
constants = []
for i,(pos,name) in enumerate(cents):
    end = cents[i+1][0] if i+1 < len(cents) else len(cbody)
    for spos, snum, sname in csecs:
        if pos < spos < end:
            end = spos
    chunk = cbody[pos:end]
    secname = 'Uncategorised'
    for spos, snum, sname in csecs:
        if spos < pos: secname = sname
        else: break
    val = re.search(r'Value:\s*`([^`]+)`', chunk)
    lines = chunk.split('\n')
    rest = []
    seen_value = False
    for ln in lines[1:]:
        s = ln.strip()
        if s.startswith('Value:'):
            seen_value = True
            continue
        if seen_value and s:
            rest.append(s)
    constants.append({
        'section': secname,
        'name': name,
        'value': val.group(1).strip() if val else None,
        'desc': ' '.join(rest).strip(),
    })

json.dump({'functions': entries, 'constants': constants},
          open(os.path.join(OUT,'parsed.json'),'w',encoding='utf-8'),
          indent=1, ensure_ascii=False)

print(f'functions={len(entries)}  constants={len(constants)}')
from collections import Counter
print('FUNC SECTIONS:', Counter(e['section'] for e in entries))
print()
print('CONST SECTIONS:', len(set(c['section'] for c in constants)))
for s,c in Counter(x['section'] for x in constants).items():
    print(f'  {c:4d}  {s}')
missing_p = [e['name'] for e in entries if not e['prototype']]
print('missing prototype:', missing_p[:20])
missing_v = [c['name'] for c in constants if not c['value']]
print('missing value:', missing_v[:20], len(missing_v))

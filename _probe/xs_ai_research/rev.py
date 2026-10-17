import sys, io, re
p = 'AI_SCRIPTING_AIREF.md'
s = io.open(p, encoding='utf-8').read()
# collect distinct non-ascii runs
runs = {}
for m in re.finditer(r'[^\x00-\x7F]+', s):
    r = m.group(0)
    runs.setdefault(r, 0)
    runs[r] += 1
print('distinct runs:', len(runs))
for r, c in sorted(runs.items(), key=lambda kv: -kv[1]):
    cp = ' '.join('U+%04X' % ord(ch) for ch in r)
    try:
        b = r.encode('gbk')
        by = ' '.join('%02X' % x for x in b)
        try:
            back = b.decode('utf-8')
            ok = 'OK  -> ' + repr(back)
        except Exception as e:
            ok = 'utf8 FAIL: %s' % e
    except Exception as e:
        by = '(encode FAIL: %s)' % e
        ok = ''
    print('%-28s x%-4d %-22s %s' % (cp, c, repr(r), ''))
    print('      gbk=%s' % by)
    print('      %s' % ok)

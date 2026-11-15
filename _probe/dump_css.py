# -*- coding: utf-8 -*-
"""Dump selected CSS rules with their line numbers."""
import io, re, sys

P = 'aoe2mod/ui/static/index.html'
s = io.open(P, encoding='utf-8').read()
lines = s.split('\n')

pats = sys.argv[1:] or [r'\.shell', r'\.content', r'\.rail', r'^header', r'\.byline',
                        r'\.spacer', r'\.railfoot', r'\.brand', r'\.mark', r'\.wordmark']

for pat in pats:
    for m in re.finditer(r'^\s*' + pat + r'[^{]*\{', s, re.M):
        line_no = s.count('\n', 0, m.start()) + 1
        end = s.find('}', m.end())
        print('--- %s (line %d)' % (pat, line_no))
        print(s[m.start():end + 1][:600])

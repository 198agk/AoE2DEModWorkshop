import os, re, sys, html
from html.parser import HTMLParser

OUT = os.path.dirname(os.path.abspath(__file__))

BLOCK = {'p','div','li','ul','ol','h1','h2','h3','h4','h5','h6',
         'br','pre','blockquote','section','article','dt','dd','hr','summary','details'}
DROP_TAGS = {'script','style','svg','noscript','button','form','input','select','option','iframe','nav'}

class Extractor(HTMLParser):
    """Walks the article HTML.

    Code blocks (div.highlight > table.highlighttable) are emitted intact as
    fenced blocks: the linenos column is skipped, the code column keeps its
    line structure.  Ordinary tables are emitted as pipe-tables.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_stack = []
        self.table_depth = 0
        self.rows = []
        self.cur_table = None
        self.tables = []
        self.row = None
        self.cell_buf = None
        self.in_cell = 0
        # code-block state
        self.in_highlight = 0
        self.in_linenos = 0
        self.in_code_pre = 0
        self.code_buf = None
        self.hl_div_depth = 0
        self.pre_depth = 0
        self.in_code_td = False   # only the td.code column of a highlight table

    # ---------- helpers ----------
    def _raw(self, s):
        self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get('class','') or '')
        if tag in DROP_TAGS:
            self.skip_stack.append(tag)
            return
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.append(tag)
            return

        if tag == 'div':
            if 'highlight' in cls.split():
                self.in_highlight += 1
                self.hl_div_depth = 1
                self.code_buf = []
                return
            if self.in_highlight:
                self.hl_div_depth += 1
                return
        if self.in_highlight and tag == 'div':
            return

        if self.in_highlight:
            if tag == 'td':
                tcls = cls.split()
                if 'linenos' in tcls:
                    self.in_linenos += 1
                if 'code' in tcls:
                    self.in_code_td = True
                return
            if tag == 'pre':
                self.pre_depth += 1
                if not self.in_linenos:
                    self.in_code_pre += 1
                return
            if tag in ('code','table','tr','div','span'):
                return
            return

        if tag == 'pre':
            # standalone pre outside highlight
            self.pre_depth += 1
            self.code_buf = []
            self.in_code_pre += 1
            return

        if tag == 'table':
            self.table_depth += 1
            if self.table_depth == 1:
                self.cur_table = []
            return
        if self.table_depth:
            if tag == 'tr':
                self.row = []
            elif tag in ('td','th'):
                self.cell_buf = []
                self.in_cell += 1
            return
        if tag == 'code':
            self._raw('`')
            return
        if tag in BLOCK:
            self._raw('\n')
        if tag == 'br':
            self._raw('\n')

    def handle_endtag(self, tag):
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return

        if tag == 'div':
            if self.in_highlight:
                self.hl_div_depth -= 1
                if self.hl_div_depth == 0:
                    self.in_highlight = 0
                    if self.code_buf is not None:
                        txt = ''.join(self.code_buf)
                        txt = txt.strip('\n')
                        self._raw('\n```xs\n' + txt + '\n```\n')
                        self.code_buf = None
                return

        if self.in_highlight:
            if tag == 'td':
                if self.in_linenos:
                    self.in_linenos = max(0, self.in_linenos-1)
                self.in_code_td = False
                return
            if tag == 'pre':
                self.pre_depth = max(0, self.pre_depth-1)
                if not self.in_linenos:
                    self.in_code_pre = max(0, self.in_code_pre-1)
                return
            if tag == 'div':
                return
            return

        if tag == 'pre':
            self.pre_depth = max(0, self.pre_depth-1)
            if self.code_buf is not None:
                txt = ''.join(self.code_buf).strip('\n')
                self._raw('\n```\n' + txt + '\n```\n')
                self.code_buf = None
            self.in_code_pre = max(0, self.in_code_pre-1)
            return

        if tag == 'table':
            if self.table_depth == 1 and self.cur_table:
                self.tables.append(self.cur_table)
                self.cur_table = None
            self.table_depth = max(0, self.table_depth-1)
            self._raw('\n')
            return
        if self.table_depth:
            if tag in ('td','th'):
                if self.cell_buf is not None:
                    txt = ' '.join(''.join(self.cell_buf).split())
                    if self.row is not None:
                        self.row.append(txt)
                    self.cell_buf = None
                self.in_cell = max(0, self.in_cell-1)
            elif tag == 'tr':
                if self.row is not None and self.cur_table is not None:
                    if any(c.strip() for c in self.row):
                        self.cur_table.append(self.row)
                self.row = None
            return
        if tag == 'code':
            self._raw('`')
            return
        if tag in BLOCK:
            self._raw('\n')

    def handle_data(self, data):
        if self.skip_stack:
            return
        if self.in_highlight:
            if self.in_linenos:
                return
            if self.code_buf is not None:
                self.code_buf.append(data)
            return
        if self.pre_depth and self.code_buf is not None:
            self.code_buf.append(data)
            return
        if self.table_depth:
            if self.cell_buf is not None:
                self.cell_buf.append(data)
            return
        self.out.append(data)

def get_article(htmltext):
    m = re.search(r'<article[^>]*>(.*?)</article>', htmltext, re.S|re.I)
    if m:
        return m.group(1)
    m = re.search(r'<body[^>]*>(.*?)</body>', htmltext, re.S|re.I)
    return m.group(1) if m else htmltext

def clean_text(article_html):
    p = Extractor()
    p.feed(article_html)
    txt = ''.join(p.out)
    txt = re.sub(r'[ \t]+\n', '\n', txt)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    lines = [l.rstrip() for l in txt.split('\n')]
    return '\n'.join(lines).strip(), p.tables

def main():
    files = sorted(f for f in os.listdir(OUT) if f.startswith('raw_') and f.endswith('.html'))
    for f in files:
        base = f[:-5]
        with open(os.path.join(OUT,f), encoding='utf-8', errors='replace') as fh:
            h = fh.read()
        art = get_article(h)
        txt, tabs = clean_text(art)
        with open(os.path.join(OUT, base + '.txt'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        with open(os.path.join(OUT, base + '.tables.txt'), 'w', encoding='utf-8') as fh:
            for i,t in enumerate(tabs):
                fh.write(f'=== TABLE {i} ({len(t)} rows) ===\n')
                for r in t:
                    fh.write(' | '.join(r) + '\n')
                fh.write('\n')
        print(f'{base}: text={len(txt)} tables={len(tabs)}')

if __name__ == '__main__':
    main()

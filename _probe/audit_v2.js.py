"""What the v2 rail layout got wrong, measured. Run after the UI is up.

Every number here is a fact about the rendered page at 1237x880, not an opinion.
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1800)

    def go(v):
        pg.evaluate("(v)=>{document.querySelectorAll('.navitem').forEach(b=>b.classList.remove('on'));"
                    "document.getElementById('nav-'+v).classList.add('on');"
                    "document.querySelectorAll('.view').forEach(x=>x.classList.remove('on'));"
                    "document.getElementById('view-'+v).classList.add('on');}", v)
        pg.wait_for_timeout(500)

    # 1. rail is mostly empty
    go("home")
    rail = pg.evaluate("""() => {
      const r = document.querySelector('.rail');
      const rb = r.getBoundingClientRect();
      const kids = [...r.children].map(c => {
        const b = c.getBoundingClientRect();
        return {cls: c.className, top: Math.round(b.top - rb.top), h: Math.round(b.height)};
      });
      // vertical dead space between last nav item and rail footer
      const nav = r.querySelector('.navlist').getBoundingClientRect();
      const foot = r.querySelector('.railfoot').getBoundingClientRect();
      return {railW: Math.round(rb.width), railH: Math.round(rb.height),
              navBottom: Math.round(nav.bottom - rb.top),
              footTop: Math.round(foot.top - rb.top),
              deadBand: Math.round(foot.top - nav.bottom),
              kids};
    }""")
    print("RAIL DEAD SPACE:", json.dumps(rail, ensure_ascii=False))

    # 2. content column left margin / unused right space
    layout = pg.evaluate("""() => {
      const shell = document.querySelector('.shell');
      const content = document.querySelector('.content');
      const cb = content.getBoundingClientRect();
      const main = document.querySelector('main');
      const mb = main ? main.getBoundingClientRect() : null;
      const cards = [...document.querySelectorAll('.box')].map(c => {
        const b = c.getBoundingClientRect();
        return {w: Math.round(b.width)};
      });
      return {shellCols: getComputedStyle(shell).gridTemplateColumns,
              contentW: Math.round(cb.width),
              contentLeft: Math.round(cb.left), contentRight: Math.round(cb.right),
              viewport: window.innerWidth,
              rightGap: Math.round(window.innerWidth - cb.right),
              cardWidths: cards};
    }""")
    print("LAYOUT:", json.dumps(layout, ensure_ascii=False))

    # 3. mods view: 21 identical buttons
    go("mods")
    mods = pg.evaluate("""() => {
      const rows = document.querySelectorAll('.mod');
      const btn = document.querySelector('.remove');
      const sw = document.querySelector('.switch');
      const mv = document.querySelector('.move');
      const box = e => e ? (() => { const r = e.getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height)}; })() : null;
      // how many pixels of each row are a control
      const row = rows[0];
      const controls = row ? [...row.querySelectorAll('button')] : [];
      const rowW = row ? row.getBoundingClientRect().width : 0;
      const ctrlW = controls.reduce((s, c) => s + c.getBoundingClientRect().width, 0);
      return {rowCount: rows.length,
              removeBtn: box(btn), removeCount: document.querySelectorAll('.remove').length,
              switch: box(sw), move: box(mv), moveCount: document.querySelectorAll('.move').length,
              rowWidth: Math.round(rowW),
              controlWidth: Math.round(ctrlW),
              controlShare: rowW ? Math.round(ctrlW / rowW * 100) : null};
    }""")
    print("MODS CONTROLS:", json.dumps(mods, ensure_ascii=False))

    # 4. editor view: 18 identical buttons, header weaker than body
    go("editor")
    pg.wait_for_timeout(800)
    ed = pg.evaluate("""() => {
      const th = document.querySelector('#editor table.f th');
      const td = document.querySelector('#editor table.f td');
      const btn = document.querySelector('#editor table.f button');
      const cs = e => e ? getComputedStyle(e) : null;
      const parse = c => { const m=c.match(/rgba?\\(([^)]+)\\)/); if(!m) return null;
        const p=m[1].split(',').map(Number); return {r:p[0],g:p[1],b:p[2]}; };
      const lum = ({r,g,b}) => { const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
        return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
      const cr = (a,b) => { const L=lum(a),M=lum(b);
        return Math.round(((Math.max(L,M)+0.05)/(Math.min(L,M)+0.05))*100)/100; };
      const bg = e => { let x=e; while(x){ const c=cs(x).backgroundColor;
        if(c && c!=='rgba(0, 0, 0, 0)') return parse(c); x=x.parentElement; }
        return {r:255,g:255,b:255}; };
      return {
        headerColor: cs(th).color, headerSize: cs(th).fontSize, headerWeight: cs(th).fontWeight,
        headerContrast: cr(parse(cs(th).color), bg(th)),
        cellSize: cs(td).fontSize, cellContrast: cr(parse(cs(td).color), bg(td)),
        headerWeakerThanCell: cr(parse(cs(th).color), bg(th)) < cr(parse(cs(td).color), bg(td)),
        applyBtnCount: document.querySelectorAll('#editor table.f button').length,
        applyBtnLabel: btn ? btn.textContent.trim() : null,
        applyBtnBox: btn ? (()=>{const r=btn.getBoundingClientRect();return {w:Math.round(r.width),h:Math.round(r.height)};})() : null
      };
    }""")
    print("EDITOR TABLE:", json.dumps(ed, ensure_ascii=False))

    # 5. empty-looking home: how much of the first screen is real content
    go("home")
    pg.wait_for_timeout(400)
    home = pg.evaluate("""() => {
      const v = document.getElementById('view-home');
      const cards = [...v.querySelectorAll('.box')];
      const used = cards.reduce((s,c)=>s+c.getBoundingClientRect().height,0);
      const vb = v.getBoundingClientRect();
      return {viewH: Math.round(vb.height), cardsH: Math.round(used),
              fill: Math.round(used/vb.height*100),
              cardCount: cards.length,
              cardTextLens: cards.map(c=>c.textContent.trim().length)};
    }""")
    print("HOME FILL:", json.dumps(home, ensure_ascii=False))

    b.close()

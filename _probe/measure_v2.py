import json, os
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1800)

    def view(vid):
        pg.evaluate("(v) => { document.querySelectorAll('.navitem').forEach(b => b.classList.remove('on')); "
                    "document.getElementById('nav-'+v).classList.add('on'); "
                    "document.querySelectorAll('.view').forEach(x => x.classList.remove('on')); "
                    "document.getElementById('view-'+v).classList.add('on'); }", vid)
        pg.wait_for_timeout(500)

    # --- mods view: repeated button count + row geometry
    view("mods")
    mods = pg.evaluate("""() => {
      const rows = [...document.querySelectorAll('#mods .mod, .mod')];
      const btns = [...document.querySelectorAll('button')].filter(b => (b.textContent||'').trim() === '放进回收站');
      const row0 = rows[0] ? rows[0].getBoundingClientRect() : null;
      const rail = document.querySelector('.rail');
      const railBox = rail ? rail.getBoundingClientRect() : null;
      const railChildren = rail ? [...rail.children].map(c => {
        const r = c.getBoundingClientRect();
        return {cls: c.className, h: Math.round(r.height), top: Math.round(r.top)};
      }) : [];
      return {
        rowCount: rows.length,
        rowHeight: row0 ? Math.round(row0.height) : null,
        recycleBtnCount: btns.length,
        recycleBtnW: btns[0] ? Math.round(btns[0].getBoundingClientRect().width) : null,
        railWidth: railBox ? Math.round(railBox.width) : null,
        railHeight: railBox ? Math.round(railBox.height) : null,
        railChildren
      };
    }""")
    print("MODS:", json.dumps(mods, ensure_ascii=False, indent=1))

    # --- editor view: repeated 改成 buttons + table header contrast
    view("editor")
    pg.wait_for_timeout(900)
    ed = pg.evaluate("""() => {
      const btns = [...document.querySelectorAll('#editor table.f button')];
      const ths = [...document.querySelectorAll('#editor table.f th')];
      const th = ths[0];
      const parse = c => { const m=c.match(/rgba?\\(([^)]+)\\)/); if(!m) return null;
        const p=m[1].split(',').map(Number); return {r:p[0],g:p[1],b:p[2]}; };
      const lum = ({r,g,b}) => { const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
        return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
      const cr = (a,b) => { const L1=lum(a),L2=lum(b); return Math.round(((Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05))*100)/100; };
      const bgOf = el => { let e=el; while(e){ const c=parse(getComputedStyle(e).backgroundColor);
        if(c && getComputedStyle(e).backgroundColor !== 'rgba(0, 0, 0, 0)') return c; e=e.parentElement; } return {r:255,g:255,b:255}; };
      return {
        rowCount: btns.length,
        btnLabel: btns[0] ? btns[0].textContent.trim() : null,
        btnHeight: btns[0] ? Math.round(btns[0].getBoundingClientRect().height) : null,
        thText: th ? th.textContent.trim() : null,
        thColor: th ? getComputedStyle(th).color : null,
        thSize: th ? getComputedStyle(th).fontSize : null,
        thWeight: th ? getComputedStyle(th).fontWeight : null,
        thContrast: th ? cr(parse(getComputedStyle(th).color), bgOf(th)) : null,
        tdContrast: (() => { const td=document.querySelector('#editor table.f td');
          return td ? cr(parse(getComputedStyle(td).color), bgOf(td)) : null; })(),
        edlistH: (() => { const l=document.querySelector('#editor .edlist');
          return l ? {h:Math.round(l.getBoundingClientRect().height), ch:l.clientHeight, sh:l.scrollHeight} : null; })()
      };
    }""")
    print("EDITOR:", json.dumps(ed, ensure_ascii=False, indent=1))

    b.close()

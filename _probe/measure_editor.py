"""Measure the two things the last CSS round was supposed to change:
the editor table header's visual weight, and the 18 "改成" buttons' ghost state.
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1600)
    pg.click("#nav-editor")
    pg.wait_for_timeout(1400)

    r = pg.evaluate("""() => {
      const cs = (e) => e ? getComputedStyle(e) : null;
      const parse = (c) => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
        const p = m[1].split(',').map(Number); return {r:p[0], g:p[1], b:p[2]}; };
      const lum = ({r,g,b}) => { const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
        return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
      const cr = (a,b) => { const L=lum(a),M=lum(b);
        return Math.round(((Math.max(L,M)+0.05)/(Math.min(L,M)+0.05))*100)/100; };
      const bgOf = e => { let x=e; while(x){ const c=cs(x).backgroundColor;
        if(c && c!=='rgba(0, 0, 0, 0)') return parse(c); x=x.parentElement; }
        return {r:255,g:255,b:255}; };

      const th = document.querySelector('#editor table.f th');
      const td = document.querySelector('#editor table.f td');
      const btns = [...document.querySelectorAll('#editor table.f td.e button')];
      const inputs = [...document.querySelectorAll('#editor table.f td.e input')];
      const b0 = cs(btns[0]);

      return {
        th: {size: cs(th).fontSize, weight: cs(th).fontWeight, color: cs(th).color,
             contrast: cr(parse(cs(th).color), bgOf(th))},
        td: {size: cs(td).fontSize, contrast: cr(parse(cs(td).color), bgOf(td))},
        btnCount: btns.length,
        btnRest: {color: b0.color, background: b0.backgroundColor,
                  border: b0.borderColor, weight: b0.fontWeight},
        btnRestContrast: cr(parse(b0.color), bgOf(btns[0])),
        supportsHas: CSS.supports('selector(:has(*))'),
        typedCheck: (() => {
          if (!inputs.length) return null;
          inputs[0].value = '999';
          const after = getComputedStyle(btns[0]);
          const out = {color: after.color, background: after.backgroundColor};
          inputs[0].value = '';
          return out;
        })()
      };
    }""")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    b.close()

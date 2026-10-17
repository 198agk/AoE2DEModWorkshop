const fs = require('fs');
const buf = fs.readFileSync('AI_SCRIPTING_AIREF.md');
console.log('bytes: ' + buf.length);
console.log('first 4 bytes: ' + [...buf.slice(0, 4)].map(b => b.toString(16)).join(' '));
// find the em-dash in the title line
const t = buf.toString('utf8');
const i = t.indexOf('Reference Extract');
console.log('title context: ' + JSON.stringify(t.slice(i - 30, i + 20)));
for (const probe of ['File roles', 'loadIfSymbolsArray', 'Object and technology id tables', 'Duke D']) {
  const j = t.indexOf(probe);
  const seg = t.slice(j, j + 80);
  console.log('--- ' + probe + ' @' + j);
  console.log('    chars: ' + JSON.stringify(seg));
  console.log('    codes: ' + [...seg].slice(0, 40).map(c => c.charCodeAt(0) > 127 ? 'U+' + c.charCodeAt(0).toString(16) : c).join(''));
}

const fs = require('fs');
const s = fs.readFileSync('AI_SCRIPTING_AIREF.md', 'utf8');
// What follows each U+9225 (鈥), U+922B (鈫), U+922E (鈮)?
function survey(lead, label) {
  const tally = new Map();
  let n = 0;
  for (let i = 0; i < s.length; i++) {
    if (s.charCodeAt(i) !== lead) continue;
    n++;
    const nxt = [...s.slice(i + 1, i + 3)].map(c => 'U+' + c.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')).join('+');
    tally.set(nxt, (tally.get(nxt) || 0) + 1);
  }
  console.log('## ' + label + '  total=' + n);
  for (const [k, v] of [...tally.entries()].sort((a, b) => b[1] - a[1])) console.log('   after=' + k + '  x' + v);
}
survey(0x9225, 'U+9225');
survey(0x922B, 'U+922B');
survey(0x922E, 'U+922E');
// contexts of the PUA-bearing runs
const pua = /\u9225[\uE000-\uF8FF]+/g;
let m;
while ((m = pua.exec(s)) !== null) {
  console.log('PUA @' + m.index + ' cps=' + [...m[0]].map(c => 'U+' + c.charCodeAt(0).toString(16).toUpperCase()).join(' '));
  console.log('   ctx=' + JSON.stringify(s.slice(m.index - 60, m.index + 40)));
}

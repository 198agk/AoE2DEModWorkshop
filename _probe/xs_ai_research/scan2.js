const fs = require('fs');
const lines = fs.readFileSync('AI_SCRIPTING_AIREF.md', 'utf8').split(/\r?\n/);
const runs = new Map(); // run -> {count, examples:[{line,ctx}]}
for (let i = 0; i < lines.length; i++) {
  const L = lines[i];
  const re = /[^\x00-\x7F]+/g;
  let m;
  while ((m = re.exec(L)) !== null) {
    const r = m[0];
    const key = [...r].map(c => 'U+' + c.charCodeAt(0).toString(16).toUpperCase()).join(' ');
    if (!runs.has(key)) runs.set(key, { text: r, cp: key, count: 0, ex: [] });
    const e = runs.get(key);
    e.count++;
    if (e.ex.length < 2) e.ex.push((i + 1) + ': ' + JSON.stringify(L.slice(Math.max(0, m.index - 40), m.index + r.length + 25)));
  }
}
console.log('distinct non-ASCII runs: ' + runs.size);
const arr = [...runs.values()].sort((a, b) => b.count - a.count);
for (const e of arr) {
  console.log('--- ' + e.cp + '  x' + e.count + '  text=' + JSON.stringify(e.text));
  for (const x of e.ex) console.log('      ' + x);
}

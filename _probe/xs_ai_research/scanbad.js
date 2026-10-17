const fs = require('fs');
const t = fs.readFileSync('AI_SCRIPTING_AIREF.md', 'utf8');
const lines = t.split(/\r?\n/);
const bad = [];
lines.forEach((ln, i) => {
  if (/[\u4E00-\u9FFF\uFFFD\u9225\u922B\u922E\u6402\u93BC]/.test(ln)) bad.push(i + 1);
});
console.log('lines with corruption: ' + bad.length);
// group into contiguous runs
const runs = [];
let s = null, p = null;
for (const n of bad) {
  if (s === null) { s = n; p = n; continue; }
  if (n === p + 1) { p = n; continue; }
  runs.push([s, p]); s = n; p = n;
}
if (s !== null) runs.push([s, p]);
console.log('runs: ' + runs.length);
runs.forEach(r => console.log(r[0] + '-' + r[1] + '  (' + (r[1] - r[0] + 1) + ' lines)'));

const fs = require('fs');
const s = fs.readFileSync('AI_SCRIPTING_AIREF.md', 'utf8');
// 1) verify the char BEFORE every U+9225+? site is a space
let odd = 0, tot = 0, prevTally = new Map();
for (let i = 0; i < s.length - 1; i++) {
  if (s.charCodeAt(i) === 0x9225 && s.charCodeAt(i + 1) === 0x3F) {
    tot++;
    const p = s[i - 1];
    const k = p === undefined ? 'BOL' : JSON.stringify(p);
    prevTally.set(k, (prevTally.get(k) || 0) + 1);
    if (p !== ' ') { odd++; if (odd <= 12) console.log('ODD prev=' + k + ' ctx=' + JSON.stringify(s.slice(i - 70, i + 40))); }
  }
}
console.log('U+9225? sites=' + tot + '  prev-not-space=' + odd);
console.log('prev tally: ' + [...prevTally.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15).map(e => e[0] + 'x' + e[1]).join(' '));
// 2) same for U+922B
prevTally = new Map();
for (let i = 0; i < s.length - 1; i++) {
  if (s.charCodeAt(i) === 0x922B && s.charCodeAt(i + 1) === 0x3F) {
    prevTally.set(JSON.stringify(s[i - 1]), (prevTally.get(JSON.stringify(s[i - 1])) || 0) + 1);
  }
}
console.log('U+922B? prev tally: ' + [...prevTally.entries()].map(e => e[0] + 'x' + e[1]).join(' '));
// 3) full context of every PUA site and every 鈮
const re = /\u9225[\uE000-\uF8FF]|\u922E/g;
let m;
while ((m = re.exec(s)) !== null) {
  console.log('@@@ @' + m.index + ' ' + JSON.stringify(s.slice(m.index - 130, m.index + 90)));
}
// 4) line numbers for each U+922B site
const lines = s.split(/\r?\n/);
lines.forEach((L, i) => { if (/[\u922B\u922E]/.test(L)) console.log('LINE ' + (i + 1) + ': ' + JSON.stringify(L)); });

const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {lif:typeof loadIfSymbolsArray!=="undefined"?loadIfSymbolsArray:null, bugs:typeof bugsArray!=="undefined"?bugsArray:null, obj:typeof objectsArray!=="undefined"?objectsArray:null, tech:typeof techsArray!=="undefined"?techsArray:null};');
const r = fn();
console.log('loadIf arrays:', r.lif ? r.lif.length : 'null');
const out = [];
let total = 0;
if (r.lif) for (const g of r.lif) {
  if (!g || !g.length) continue;
  out.push('### ' + (g[0].type || '?') + ' (' + g.length + ')');
  for (const s of g) out.push('- `' + s.name + '` — ' + String(s.description).replace(/<[^>]+>/g, ''));
  total += g.length;
  out.push('');
}
out.unshift('# Load-If symbols, total ' + total);
fs.writeFileSync(dir + 'raw_ai_loadif_symbols.md', out.join('\n'));
console.log(out.join('\n').slice(0, 3000));

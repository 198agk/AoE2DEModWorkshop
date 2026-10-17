const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8').replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {c:commandsArray,sn:snArray,p:parametersArray};');
const r = fn();
console.log('--- commandCategory containing "Don\'t Use" ---');
r.c.filter(x => (x.commandCategory || []).some(c => /Don.t Use/i.test(c))).forEach(x =>
  console.log(' -', x.commandName, '|', x.commandType, x.commandVersion, '|', String(x.shortDescription).replace(/<[^>]+>/g, '')));
console.log('\n--- SN object keys ---');
console.log(Object.keys(r.sn[0]).join(', '));
console.log('\n--- SN sample (index 2) ---');
console.log(JSON.stringify(r.sn[2], (k, v) => /^(linked|related)$/.test(k) ? '[refs]' : v, 1));
console.log('\n--- SN available distribution ---');
const avail = {}; for (const s of r.sn) { avail[String(s.available)] = (avail[String(s.available)] || 0) + 1; }
console.log(JSON.stringify(avail));
const eff = {}; for (const s of r.sn) { eff[String(s.effective)] = (eff[String(s.effective)] || 0) + 1; }
console.log('effective:', JSON.stringify(eff));
console.log('\n--- parameter object keys ---');
console.log(Object.keys(r.p[0]).join(', '));
console.log('\n--- parameter names/versions ---');
r.p.forEach(p => console.log(' ', p.upParamName, '|', p.paramVersion, '|', (p.prefixTypes||[]).join('+'), '|', (p.operatorTypes||[]).join('+')));

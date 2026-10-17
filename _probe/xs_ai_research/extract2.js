const fs = require('fs');
const path = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(path + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {commands: (typeof commandsArray!=="undefined"?commandsArray:null), params: (typeof parametersArray!=="undefined"?parametersArray:null), sn: (typeof snArray!=="undefined"?snArray:null), objects: (typeof objectsArray!=="undefined"?objectsArray:null), techs: (typeof techsArray!=="undefined"?techsArray:null) };');
const r = fn();
for (const k of ['commands', 'params', 'sn', 'objects', 'techs']) {
  const v = r[k];
  const out = (k === 'objects' || k === 'techs') ? v.flat().filter(Boolean) : v;
  fs.writeFileSync(path + 'data_' + k + '.json', JSON.stringify(out, null, 1));
  console.log(k, out ? out.length : 0);
}

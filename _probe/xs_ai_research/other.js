const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {c:commandsArray,p:parametersArray,sn:snArray};');
const r = fn();
const out = [];
out.push('## Other-type commands (' + r.c.filter(x => x.commandType === 'Other').length + ')');
for (const c of r.c.filter(x => x.commandType === 'Other').sort((a,b)=>a.commandName.localeCompare(b.commandName))) {
  out.push('- `(' + c.commandName + (c.commandParameters.length ? ' ' + c.commandParameters.map(p=>p.name).join(' ') : '') + ')` | ver=' + c.commandVersion + ' | cat=' + c.commandCategory.join('/') + ' | ' + String(c.shortDescription).replace(/<[^>]+>/g,''));
}
out.push('');
out.push('## DE-version commands (' + r.c.filter(x => x.commandVersion === 'DE').length + ')');
for (const c of r.c.filter(x => x.commandVersion === 'DE').sort((a,b)=>a.commandName.localeCompare(b.commandName))) {
  out.push('- `(' + c.commandName + (c.commandParameters.length ? ' ' + c.commandParameters.map(p=>p.name).join(' ') : '') + ')` | ' + String(c.shortDescription).replace(/<[^>]+>/g,''));
}
out.push('');
out.push('## UP-version commands (' + r.c.filter(x => x.commandVersion === 'UP').length + ')');
for (const c of r.c.filter(x => x.commandVersion === 'UP').sort((a,b)=>a.commandName.localeCompare(b.commandName))) {
  out.push('- `(' + c.commandName + (c.commandParameters.length ? ' ' + c.commandParameters.map(p=>p.name).join(' ') : '') + ')` | cat=' + c.commandCategory.join('/'));
}
out.push('');
out.push('## All parameter names');
out.push(r.p.map(p=>p.upParamName + ' [' + p.paramVersion + ']').join('\n'));
fs.writeFileSync(dir + 'other_cmds.txt', out.join('\n'));
console.log(out.join('\n').slice(0, 14000));

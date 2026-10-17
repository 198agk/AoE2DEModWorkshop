const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {commands: commandsArray, params: parametersArray, sn: snArray};');
const r = fn();

// find up-get-object-data to inspect parameter object shape
const c = r.commands.find(x => x.commandName === 'up-get-object-data');
const out = JSON.stringify(c, (k, v) => (k === 'relatedCommands' || k === 'commandLinks') ? '[ref]' : v, 1);
fs.writeFileSync(dir + 'sample_upgetobjectdata.json', out);
console.log(out.slice(0, 6000));

// Extract AIREF data arrays from commands.js by running it with stubs for DOM.
const fs = require('fs');
const path = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(path + 'raw_commands.js', 'utf8');
// Strip the trailing DOM usage
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {commands: (typeof commandsArray!=="undefined"?commandsArray:null), params: (typeof parametersArray!=="undefined"?parametersArray:null), sn: (typeof snArray!=="undefined"?snArray:null), events: (typeof eventsArray!=="undefined"?eventsArray:null), objects: (typeof objectsArray!=="undefined"?objectsArray:null), techs: (typeof techsArray!=="undefined"?techsArray:null), dls: (typeof dlsArray!=="undefined"?dlsArray:null) };');
let r;
try { r = fn(); } catch (e) { console.log('ERR', e.message); process.exit(1); }
console.log('commands:', r.commands ? r.commands.length : 'null');
console.log('params:', r.params ? r.params.length : 'null');
console.log('sn:', r.sn ? r.sn.length : 'null');
console.log('events:', r.events ? r.events.length : 'null');
console.log('objects:', r.objects ? r.objects.length : 'null');
console.log('techs:', r.techs ? r.techs.length : 'null');

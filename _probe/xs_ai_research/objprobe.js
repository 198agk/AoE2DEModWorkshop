const fs = require('fs');
const src = fs.readFileSync('raw_commands.js', 'utf8')
  .replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const api = new Function(
  'var urlPrefix="";var currPage="";' +
  'var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};' +
  'var window={location:{href:""}};' +
  'var $=function(){return {tooltip:function(){}};};\n' +
  src +
  '\n;return {objectsArray:objectsArray, techsArray:techsArray, objectsBuildingNamesArray:(typeof objectsBuildingNamesArray!=="undefined"?objectsBuildingNamesArray:null)};')();

const repl = (k, v) => (k === 'relatedCommands' || k === 'commandLinks' || k === 'relatedParams' || k === 'linked' || k === 'related') ? '[refs]' : v;

console.log('=== objectsArray: ' + api.objectsArray.length + ' groups ===');
api.objectsArray.forEach((g, i) => {
  const arr = Array.isArray(g) ? g : (g.objects || g.items || []);
  console.log(i + ': len=' + (Array.isArray(arr) ? arr.length : 'n/a') + ' keys=' + JSON.stringify(Object.keys(g).slice(0, 12)));
});
console.log('=== sample group[0] first 3 entries ===');
const g0 = api.objectsArray[0];
const a0 = Array.isArray(g0) ? g0 : (g0.objects || []);
console.log(JSON.stringify(a0.slice(0, 3), repl, 1));
console.log('=== techsArray: ' + api.techsArray.length + ' groups ===');
api.techsArray.forEach((g, i) => {
  const arr = Array.isArray(g) ? g : (g.techs || g.items || []);
  console.log(i + ': len=' + (Array.isArray(arr) ? arr.length : 'n/a') + ' keys=' + JSON.stringify(Object.keys(g).slice(0, 12)));
});
const t0 = api.techsArray[0];
const b0 = Array.isArray(t0) ? t0 : (t0.techs || []);
console.log('=== sample techs group[0] first 3 entries ===');
console.log(JSON.stringify(b0.slice(0, 3), repl, 1));

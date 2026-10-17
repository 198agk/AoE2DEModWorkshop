const fs = require('fs');
const src = fs.readFileSync('raw_commands.js', 'utf8')
  .replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const api = new Function(
  'var urlPrefix="";var currPage="";' +
  'var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};' +
  'var window={location:{href:""}};' +
  'var $=function(){return {tooltip:function(){}};};\n' +
  src +
  '\n;return {keys:Object.keys(this)};').call({});
console.log(api.keys.filter(k => /object|tech/i.test(k)).join('\n'));

const fs = require('fs');
const src = fs.readFileSync('raw_commands.js', 'utf8')
  .replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const api = new Function(
  'var urlPrefix="";var currPage="";' +
  'var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};' +
  'var window={location:{href:""}};' +
  'var $=function(){return {tooltip:function(){}};};\n' +
  src +
  '\n;return {commandsArray:commandsArray};')();
const names = ['and', 'nand', 'nor', 'not', 'or', 'xnor', 'xor'];
for (const c of api.commandsArray) {
  if (names.indexOf(c.commandName) >= 0) {
    console.log(JSON.stringify({
      n: c.commandName,
      type: c.commandType,
      short: c.shortDescription,
      desc: c.description,
      params: c.commandParameters.map(p => p.dir + ':' + p.type + ' ' + p.name),
      examples: (c.example || []).map(e => e.data)
    }, null, 1));
  }
}

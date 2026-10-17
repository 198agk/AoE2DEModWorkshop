const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
let src = fs.readFileSync(dir + 'raw_commands.js', 'utf8');
src = src.replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const fn = new Function('var urlPrefix="";var currPage="";var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};var window={location:{href:""}};var $=function(){return {tooltip:function(){}};};\n' + src + '\n;return {c:commandsArray,p:parametersArray};');
const r = fn();
const names = ['defrule', 'defconst', 'defglobal', 'load', 'load-random', 'include', 'set-strategic-number', 'set-goal', 'train', 'research', 'build', 'attack-now', 'xs-script-call', 'up-log-data', 'up-chat-data-to-self', 'up-cc-add-resource', 'cc-add-resource', 'fe-break-point', 'up-get-fact', 'up-get-object-data', 'up-get-player-fact', 'up-research-status', 'up-can-build', 'up-set-target-object', 'up-find-local', 'up-find-remote', 'up-find-for', 'up-find-player', 'up-find-status-local', 'up-find-status-remote', 'up-filter-status', 'up-filter-distance', 'up-filter-type', 'up-filter-include', 'up-filter-exclude', 'up-filter-reset', 'up-target-point', 'up-set-attack-stance', 'up-modify-goal', 'up-modify-sn', 'up-bound-goal', 'up-bound-sn', 'up-jump-rule', 'up-jump-dynamic', 'up-train', 'up-build', 'up-build-line', 'up-build-line-with-escrow', 'up-research', 'up-assign-builders', 'up-drop-resources', 'up-delete-unit', 'up-remove-object', 'up-get-threat-data', 'up-retreat-now', 'up-retreat-to', 'up-full-reset-search'];
const out = [];
for (const n of names) {
  const c = r.c.find(x => x.commandName === n);
  if (!c) { out.push('MISSING: ' + n); continue; }
  out.push('=== ' + n + ' | ' + c.commandType + ' | ' + c.commandVersion + ' | cat=' + c.commandCategory.join('/') + ' | complexity=' + c.complexity);
  out.push('PARAMS: ' + JSON.stringify(c.commandParameters.map(p => p.dir + ':' + p.type + ' ' + p.name)));
  out.push('RANGES: ' + JSON.stringify(c.commandParameters.map(p => p.range)));
  out.push('NOTES: ' + JSON.stringify(c.commandParameters.map(p => p.note)));
  out.push('SYNTAX: (' + n + (c.commandParameters.length ? ' ' + c.commandParameters.map(p => p.name).join(' ') : '') + ')');
  out.push('SHORT: ' + String(c.shortDescription).replace(/<[^>]+>/g, ''));
  out.push('DESC: ' + String(c.description).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').slice(0, 1500));
  out.push('EX: ' + (c.example || []).map(e => e.title + ' || ' + String(e.data).replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&').replace(/\r\n/g, '\n')).join('\n---\n'));
  out.push('');
}
fs.writeFileSync(dir + 'core_cmds.txt', out.join('\n'));
console.log(out.join('\n'));

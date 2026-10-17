const fs = require('fs');
const src = fs.readFileSync('raw_commands.js', 'utf8')
  .replace(/document\.[A-Za-z]+\([^)]*\)\.innerHTML\s*=[^;]*;/g, '');
const api = new Function(
  'var urlPrefix="";var currPage="";' +
  'var document={getElementById:function(){return {innerHTML:"",style:{},setAttribute:function(){}};},addEventListener:function(){}};' +
  'var window={location:{href:""}};' +
  'var $=function(){return {tooltip:function(){}};};\n' +
  src +
  '\n;return {objectsArray:objectsArray, techsArray:techsArray, objectsBuildingNamesArray:objectsBuildingNamesArray, objectsArrayROR:objectsArrayROR, objectsArrayChr:objectsArrayChr, techsArrayROR:techsArrayROR, techsArrayChr:techsArrayChr};')();

const objectGroupNames = api.objectsBuildingNamesArray;
const techGroupNames = ['Archery Range', 'Barracks', 'Blacksmith', 'Castle', 'Dock', 'Lumber Camp', 'Market', 'Mill', 'Mining Camp', 'Monastery', 'Siege Workshop', 'Stable', 'Town Center', 'University'];

function esc(s) { return String(s == null ? '' : s).replace(/\|/g, '\\|').replace(/\r?\n/g, ' ').trim(); }
function ver(o) {
  const p = [];
  if (o.aok) p.push('AoC');
  if (o.tc) p.push('TC');
  if (o.wk) p.push('WK');
  if (o.de) p.push('DE');
  if (o.aoe1) p.push('AoE1');
  return p.length ? p.join('/') : '-';
}

let out = [];
out.push('');
out.push('---');
out.push('');
out.push('## 8. Object and technology id tables');
out.push('');
out.push('Extracted from the same authoritative file, `js/commands.js`, which is the data source behind');
out.push('<https://airef.github.io/tables/objects.html> and <https://airef.github.io/tables/techs.html>.');
out.push('Both HTML pages are JS shells and contain no data of their own (see §1.10).');
out.push('');
out.push('Column meanings, verbatim from the dataset keys: **AI name** = `aiName` (the token you may write in a `.per` file,');
out.push('including any parenthesised aliases the site records); **Line** = `line` (the `*-line` wildcard group the unit belongs to);');
out.push('**Class** = `class`; **CmdId** = `cmdId`; **Building** = `building` (train site, or research site for techs);');
out.push('**Age** = `age` (2 Feudal, 3 Castle, 4 Imperial per the site\'s convention); **Civ** = `civ` (empty when generic).');
out.push('');

let objTotal = 0;
out.push('### 8.1 Object (unit / building) ids');
out.push('');
out.push('| Group | Objects |');
out.push('|---|---|');
const objGroups = [];
api.objectsArray.forEach((g, i) => {
  objTotal += g.length;
  objGroups.push({ name: objectGroupNames[i] || ('Group ' + i), rows: g });
  out.push('| ' + esc(objectGroupNames[i] || ('Group ' + i)) + ' | ' + g.length + ' |');
});
out.push('| **Total** | **' + objTotal + '** |');
out.push('');
for (const grp of objGroups) {
  out.push('#### ' + grp.name + ' (' + grp.rows.length + ')');
  out.push('');
  out.push('| ID | Name | AI name | Line | Class | CmdId | Building | Age | Civ | Versions | Notes |');
  out.push('|---|---|---|---|---|---|---|---|---|---|---|');
  for (const o of grp.rows) {
    out.push('| ' + esc(o.id) + ' | ' + esc(o.name) + ' | `' + esc(o.aiName) + '` | `' + esc(o.line) + '` | ' + esc(o.class) + ' | ' + esc(o.cmdId) + ' | ' + esc(o.building) + ' | ' + esc(o.age) + ' | ' + esc(o.civ) + ' | ' + esc(ver(o)) + ' | ' + esc(o.notes) + ' |');
  }
  out.push('');
}

let techTotal = 0;
out.push('### 8.2 Technology ids');
out.push('');
out.push('| Group | Techs |');
out.push('|---|---|');
const techGroups = [];
api.techsArray.forEach((g, i) => {
  techTotal += g.length;
  techGroups.push({ name: techGroupNames[i] || ('Group ' + i), rows: g });
  out.push('| ' + esc(techGroupNames[i] || ('Group ' + i)) + ' | ' + g.length + ' |');
});
out.push('| **Total** | **' + techTotal + '** |');
out.push('');
for (const grp of techGroups) {
  const keys = Object.keys(grp.rows[0] || {});
  out.push('#### ' + grp.name + ' (' + grp.rows.length + ')');
  out.push('');
  out.push('| ID | Name | AI name | Building | Age | Civ | Versions | Notes |');
  out.push('|---|---|---|---|---|---|---|---|');
  for (const t of grp.rows) {
    out.push('| ' + esc(t.id) + ' | ' + esc(t.name) + ' | `' + esc(t.aiName) + '` | ' + esc(t.building) + ' | ' + esc(t.age) + ' | ' + esc(t.civ) + ' | ' + esc(ver(t)) + ' | ' + esc(t.notes) + ' |');
  }
  out.push('');
}

out.push('### 8.3 Group composition and the non-AoE2 variants');
out.push('');
out.push('The AoE2 group order in `objectsArray` is fixed and is what the "Group" names above refer to:');
out.push('');
out.push('```js');
out.push('objectsArray = [objectsRangeArray, objectsBarracksArray, objectsCastleArray, objectsDockArray,');
out.push('  objectsDonjonArray, objectsKrepostArray, objectsMarketArray, objectsMonasteryArray,');
out.push('  objectsSiegeWorkshopArray, objectsStableArray, objectsTownCenterArray, objectsBuildingsArray,');
out.push('  objectsGaiaArray, objectsHeroesArray, objectsOtherArray];');
out.push('```');
out.push('');
out.push('```js');
out.push('techsArray = [rangeTechsArray, barracksTechsArray, blacksmithTechsArray, castleTechsArray,');
out.push('  dockTechsArray, lcTechsArray, marketTechsArray, millTechsArray, mcTechsArray,');
out.push('  monasteryTechsArray, siegeWorkshopTechsArray, stableTechsArray, tcTechsArray, universityTechsArray];');
out.push('```');
out.push('');
out.push('Parallel tables exist for the other games and are **not** reproduced here:');
out.push('');
out.push('```js');
out.push('objectsArrayROR = [objectsAcademyArrayROR, objectsRangeArrayROR, objectsBarracksArrayROR, objectsDockArrayROR,');
out.push('  objectsMarketArrayROR, objectsSiegeWorkshopArrayROR, objectsStableArrayROR, objectsTempleArrayROR,');
out.push('  objectsTownCenterArrayROR, objectsBuildingsArrayROR, objectsOtherArrayROR];');
out.push('objectsArrayChr = [objectsRangeArrayChr, objectsBarracksArrayChr, objectsFortArray, objectsMarketArray,');
out.push('  objectsPortArray, objectsShipyardArray, objectsSiegeWorkshopArrayChr, objectsStableArrayChr,');
out.push('  objectsTempleArrayChr, objectsTownCenterArrayChr, objectsBuildingsArrayChr];');
out.push('techsArrayROR = [academyTechsArrayROR, rangeTechsArrayROR, barracksTechsArrayROR, dockTechsArrayROR,');
out.push('  governmentCenterTechsArrayROR, granaryTechsArrayROR, marketTechsArrayROR, siegeWorkshopTechsArrayROR,');
out.push('  stableTechsArrayROR, storagePitTechsArrayROR, templeTechsArrayROR, townCenterTechsArrayROR];');
out.push('techsArrayChr = [academyTechsArrayChr, rangeTechsArrayChr, barracksTechsArrayChr, blacksmithTechsArrayChr,');
out.push('  fortTechsArrayChr, lcTechsArray, marketTechsArrayChr, millTechsArrayChr, mcTechsArray, outpostTechsArrayChr,');
out.push('  portTechsArrayChr, shipyardTechsArrayChr, siegeWorkshopTechsArrayChr, stableTechsArrayChr,');
out.push('  templeTechsArrayChr, tcTechsArrayChr];');
out.push('```');
out.push('');
out.push('`objectsBuildingNamesArray` supplies the AoE2 group labels verbatim:');
out.push('');
out.push('```js');
out.push('objectsBuildingNamesArray = ' + JSON.stringify(objectGroupNames));
out.push('```');
out.push('');

fs.writeFileSync('_section8.md', out.join('\n'), 'utf8');
console.log('objects total: ' + objTotal + ' in ' + objGroups.length + ' groups');
console.log('techs total: ' + techTotal + ' in ' + techGroups.length + ' groups');
console.log('section8 bytes: ' + fs.statSync('_section8.md').size);

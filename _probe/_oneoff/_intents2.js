const fs = require("fs");
const j = JSON.parse(fs.readFileSync("aoe2mod/schema/intents.json", "utf8"));
const intents = j.intents;
console.log("type", Array.isArray(intents) ? "array" : typeof intents, Array.isArray(intents) ? intents.length : Object.keys(intents).length);
const keys = Array.isArray(intents) ? intents.map((x) => x.id) : Object.keys(intents);
console.log(keys);
const first = Array.isArray(intents) ? intents[0] : intents[keys[0]];
console.log(JSON.stringify(first, null, 1).slice(0, 1200));

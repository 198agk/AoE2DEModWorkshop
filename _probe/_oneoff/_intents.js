const fs = require("fs");
const j = JSON.parse(fs.readFileSync("aoe2mod/schema/intents.json", "utf8"));
console.log("top keys:", Object.keys(j));
const arr = Array.isArray(j) ? j : j.items || j.list || j.verbs || [];
console.log("items:", arr.length);
console.log(JSON.stringify(arr.slice(0, 10), null, 1).slice(0, 2200));

const fs = require("fs");
const raw = fs.readFileSync("aoe2mod/ui/static/index.html", "utf8").split("\n");
const seg = raw.slice(716, 798).join("\n");
console.log("raw source chars (717-798):", seg.length);
console.log("raw source incl newlines trimmed-of-indent:", seg.replace(/^[ \t]+/gm, "").length);
// collapse whitespace
console.log("collapsed:", seg.replace(/\s+/g, " ").length);

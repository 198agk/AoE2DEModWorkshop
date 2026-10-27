const fs = require("fs");
const lines = fs.readFileSync("aoe2mod/ui/static/index.html", "utf8").split("\n");
const seg = lines.slice(716, 798).join("\n"); // card1 lines 717-798
function clean(s) { return s.replace(/\s+/g, ""); }
const ph = [...seg.matchAll(/placeholder="([^"]*)"/g)].map((m) => clean(m[1]));
const textNodes = [];
let s = seg.replace(/<!--[\s\S]*?-->/g, "").replace(/<textarea[\s\S]*?<\/textarea>/g, "");
s = s.replace(/<[^>]+>/g, "\n").replace(/[ \t]+/g, "");
for (const p of s.split("\n")) if (p.trim()) textNodes.push(clean(p));
const labelChars = textNodes.reduce((n, p) => n + p.length, 0);
const phChars = ph.reduce((n, p) => n + p.length, 0);
console.log("visible label/body chars:", labelChars);
console.log("placeholder chars:", phChars, JSON.stringify(ph));
console.log("total:", labelChars + phChars);
// prose only: hints + notes
const proseLines = [731, 732, 733, 743, 744, 745, 746, 755, 756, 771, 772, 791, 792, 793, 794];
console.log("prose blocks:", proseLines.length);

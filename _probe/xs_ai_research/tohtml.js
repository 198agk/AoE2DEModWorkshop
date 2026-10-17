const fs = require('fs');
const dir = 'D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\xs_ai_research\\';
function strip(h) {
  let s = h;
  s = s.replace(/<script[\s\S]*?<\/script>/gi, '');
  s = s.replace(/<style[\s\S]*?<\/style>/gi, '');
  s = s.replace(/<head[\s\S]*?<\/head>/gi, '');
  s = s.replace(/<br\s*\/?>/gi, '\n');
  s = s.replace(/<\/(p|div|li|tr|h1|h2|h3|h4|h5|pre|table|ul|ol)>/gi, '\n');
  s = s.replace(/<li[^>]*>/gi, '- ');
  s = s.replace(/<td[^>]*>/gi, ' | ');
  s = s.replace(/<th[^>]*>/gi, ' | ');
  s = s.replace(/<[^>]+>/g, '');
  s = s.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&#10007/g, 'X').replace(/&#10003/g, 'Y');
  s = s.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n');
  return s.trim();
}
const files = fs.readdirSync(dir).filter(f => f.startsWith('raw_') && f.endsWith('.html'));
for (const f of files) {
  const t = strip(fs.readFileSync(dir + f, 'utf8'));
  fs.writeFileSync(dir + f.replace(/^raw_/, 'txt_').replace(/\.html$/, '.txt'), t);
  console.log(f, '->', t.length);
}

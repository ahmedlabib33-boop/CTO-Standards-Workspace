import fs from 'node:fs';
import path from 'node:path';
const root = process.cwd();
const target = path.join(root, 'data', 'generated');
function walk(dir){
  if(!fs.existsSync(dir)) return;
  for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
    const p=path.join(dir,entry.name);
    if(entry.isDirectory()) walk(p);
    else if(entry.isFile() && entry.name.endsWith('.json')) fs.rmSync(p,{force:true});
  }
}
walk(target);
console.log('Deleted generated JSON locally. Use Clean.bat to also commit/push deletions to GitHub and trigger Vercel.');

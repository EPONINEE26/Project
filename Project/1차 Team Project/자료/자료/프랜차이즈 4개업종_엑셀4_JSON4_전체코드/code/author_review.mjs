import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.argv[2],mode=process.argv[3]??'baseline';
const plan=JSON.parse(await fs.readFile(path.join(root,'보완계획.json'),'utf8'));
await fs.mkdir(path.join(root,'work'),{recursive:true});
for(const item of plan){
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root,'original',item.filename)));
 if(mode==='apply'){
  for(const p of item.patches){const sheet=wb.worksheets.getItem(p.sheet);if(sheet.getRange(p.cell).values[0][0]!==null&&sheet.getRange(p.cell).values[0][0]!=='')throw Error('빈칸 아님 '+p.cell);sheet.getRange(p.cell).values=[[p.value]];}
  wb.recalculate();
  const x=await SpreadsheetFile.exportXlsx(wb);await x.save(path.join(root,'work',item.filename));
 }
 for(const sheetName of [...new Set(item.patches.map(p=>p.sheet))]){
  const range=sheetName==='02_원본값_단위'?'A1:J7':sheetName==='01_창업비용'?'A1:K8':sheetName==='03_지역집계'?'A1:H6':'A1:J8';
  const png=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(path.join(root,'work',mode+'_'+item.industry+'_'+sheetName+'.png'),new Uint8Array(await png.arrayBuffer()));
 }
 console.log(mode,item.industry,item.patches.length);
}

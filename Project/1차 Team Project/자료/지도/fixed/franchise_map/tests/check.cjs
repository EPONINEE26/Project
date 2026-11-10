const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const sandbox={window:{},console};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'assets/core.js'),'utf8'),sandbox);
const D=sandbox.window.MarketData;
const stores=D.parseStores({'브랜드':{regions:{'서울':[{lat:37.54,lon:127.05,rdnmAdr:'서울특별시 성동구 성수동'}]}}},'file').stores;
assert.equal(stores.length,1);assert.equal(stores[0].brand,'브랜드');assert.equal(stores[0].city,'서울');assert.equal(stores[0].district,'성동구');
assert.equal(D.parseStores([{lat:null,lon:127},{lat:'',lon:127},{lat:200,lon:127},{lat:37.5,lon:127}], 'file').stores.length,1);
assert.equal(D.parseStores({stores:[{latitude:37.5,longitude:127,brand:'API',category:'카페'}]},'api').stores[0].brand,'API');
assert.equal(D.location('경기도 수원시 팔달구','').district,'수원시');
const ring=[[127,37],[128,37],[128,38],[127,38],[127,37]],hole=[[127.4,37.4],[127.6,37.4],[127.6,37.6],[127.4,37.6],[127.4,37.4]];
const geo={type:'Polygon',coordinates:[ring,hole]};
assert.equal(D.contains(geo,{lon:127.2,lat:37.2}),true);
assert.equal(D.contains(geo,{lon:127.5,lat:37.5}),false);
assert.equal(D.contains(geo,{lon:126,lat:37.2}),false);
assert.equal(D.contains(geo,{lon:127,lat:37.2}),true);
assert.equal(D.contains({type:'MultiPolygon',coordinates:[[ring]]},{lon:127.2,lat:37.2}),true);
assert.equal(D.areas({type:'Feature',properties:{TRDAR_CD:'123',TRDAR_CD_NM:'상권'},geometry:geo})[0].properties.area_code,'123');
assert.throws(()=>D.areas({type:'Feature',geometry:{type:'Polygon',coordinates:[[[100000,200000],[1,2],[3,4],[100000,200000]]]}}));
assert.throws(()=>D.stats({stats:[{area_code:'a',year:2025,quarter:5}]}));
assert.equal(D.stats({stats:[{area_code:'a',year:2025,quarter:1,sales:0}]})[0].sales,0);
assert.throws(()=>D.stats({stats:[{area_code:'a',year:2025,quarter:1,sales:-1}]}));
assert.ok(D.csv([{brand:'=HYPERLINK("x")',name:'A,B'}]).includes("'=HYPERLINK"));
console.log('PASS: nested/API store formats, coordinates, city/district, polygon holes and edges, multipolygons, invalid CRS, quarter/metric validation, CSV escaping');

// A small DOM harness exercises application state without requesting map tiles.
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.options=[];this.value='';this.checked=false;this.hidden=false;this.dataset={};this.listeners={};this.style={};this.attributes={};this.textContent='';this.classList={toggle(){}};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=[...items];if(this.tagName==='select'){this.options=[...items];this.value=items[0]?.value||'';}}
 add(option){this.options.push(option);}
 addEventListener(type,fn){this.listeners[type]=fn;}
 setAttribute(k,v){this.attributes[k]=v;}
 remove(){} showModal(){this.open=true;} close(){this.open=false;}
}
const html=fs.readFileSync(path.join(root,'index.html'),'utf8'),elements=new Map();
for(const match of html.matchAll(/<([\w-]+)[^>]*\bid="([^"]+)"[^>]*>/g))elements.set(match[2],new Element(match[1]));
for(const id of ['show-stores','show-areas'])elements.get(id).checked=true;
const metrics=['stores','sales','floating_population','residential_population'].map(metric=>{const el=new Element('button');el.dataset.metric=metric;return el;});
const document={getElementById:id=>elements.get(id),createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),head:new Element(),body:new Element(),querySelectorAll:selector=>selector==='[data-metric]'?metrics:[]};
Object.assign(sandbox,{document,location:{protocol:'http:'},Option:function(text,value){this.text=text;this.value=value;},Blob,AbortSignal,setTimeout,URL,fetch:async()=>{throw Error('offline test');}});
sandbox.window.MARKET_CONFIG={};
vm.runInContext(fs.readFileSync(path.join(root,'assets/app.js'),'utf8'),sandbox);
assert.equal(elements.get('city').value,'서울');
elements.get('demo').listeners.click();
assert.equal(elements.get('result-count').textContent,'6');
assert.equal(elements.get('district').value,'성동구');
assert.equal(elements.get('data-badge').textContent,'가상 예시 데이터');
elements.get('search').value='로스터리';elements.get('search').listeners.input();
assert.equal(elements.get('result-count').textContent,'1');
elements.get('report').listeners.click();assert.equal(elements.get('report-dialog').open,true);
elements.get('online').listeners.click();assert.ok(elements.get('data-status').textContent.includes('config.js'));
elements.get('search').value='';elements.get('search').listeners.input();
assert.equal(elements.get('result-count').textContent,'6');
metrics[1].listeners.click();assert.ok(elements.get('metric-content').children[0].textContent.includes('상권 경계'));
console.log('PASS: initial app, demo dataset, district selection, live address/name search, report, missing API config, metric empty state');

(async()=>{
 elements.get('files').value='test.json';
 await elements.get('files').listeners.change({target:{files:[{name:'my.json',text:async()=>JSON.stringify({stores:[{brand:'실제 입력',lat:35.17,lon:129.07,rdnmAdr:'부산광역시 부산진구 주소'}]})}]}});
 assert.equal(elements.get('data-badge').textContent,'내 데이터 연결됨');
 assert.equal(elements.get('city').value,'부산');
 assert.equal(elements.get('result-count').textContent,'1');
 assert.ok(elements.get('data-status').textContent.includes('1개 파일 연결'));
 console.log('PASS: importing own API-format JSON clears demo and selects correct city');
 sandbox.window.MARKET_CONFIG={storesUrl:'https://example.test/api/stores/'};
 sandbox.fetch=async()=>({ok:true,text:async()=>JSON.stringify({stores:[{brand:'온라인',lat:35.17,lon:129.07,rdnmAdr:'부산광역시 부산진구 주소'}]})});
 await elements.get('online').listeners.click();
 await elements.get('online').listeners.click();
 assert.equal(elements.get('result-count').textContent,'1');
 assert.equal(elements.get('online').disabled,false);
 sandbox.fetch=async()=>({ok:false,status:500});
 await elements.get('online').listeners.click();
 assert.equal(elements.get('result-count').textContent,'1');
 assert.ok(elements.get('data-status').textContent.includes('HTTP 500'));
 sandbox.fetch=async()=>({ok:true,text:async()=>'{"bad":"payload"}'});
 await elements.get('online').listeners.click();
 assert.equal(elements.get('result-count').textContent,'1');
 sandbox.fetch=async()=>({ok:true,text:async()=>'{"stores":[]}'});
 await elements.get('online').listeners.click();
 assert.equal(elements.get('result-count').textContent,'0');
 console.log('PASS: API snapshot refresh without duplicates, HTTP failure and invalid payload preserve current data, empty snapshots');
})().catch(error=>{console.error(error);process.exitCode=1;});

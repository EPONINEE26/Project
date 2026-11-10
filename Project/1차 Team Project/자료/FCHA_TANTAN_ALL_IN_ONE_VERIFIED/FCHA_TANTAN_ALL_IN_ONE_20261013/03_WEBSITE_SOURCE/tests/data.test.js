import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {filterBrands,stats,monthly,regional} from '../dist/js/data-utils.js';
const data=JSON.parse(fs.readFileSync(new URL('../dist/data/brands.json',import.meta.url)));
test('실제 표시 기준: 연매출 원 → 월 매출 만원, 결측치는 미제공',()=>{assert.equal(monthly({annual_sales_krw:312000000}),2600);assert.equal(monthly({annual_sales_krw:null}),null);assert.equal(monthly(null),null);});
test('지역 합계는 전국 합계와 일치하고 비용 합계 일치',()=>{for(const b of data.brands){assert.equal(Object.values(b.costs).reduce((a,v)=>a+v,0),b.initial_cost_krw);for(const s of b.stats){assert.equal(Object.values(s.regions).reduce((a,v)=>a+v,0),s.stores);assert.equal(Object.keys(s.regions).length,17);}}});
test('복합 필터와 정렬, 관심 목록, 검색결과 없음',()=>{let rows=filterBrands(data.brands,{year:2024,category:'카페',region:'서울',sort:'sales'});assert.equal(rows.length,2);assert.equal(rows[0].id,'morning');assert.equal(filterBrands(data.brands,{year:2024,query:'존재하지않음'}).length,0);assert.deepEqual(filterBrands(data.brands,{year:2024,saved:['tantan']}).map(b=>b.id),['tantan']);});
test('선택 연도와 지역에 맞는 통계를 반환',()=>{const b=data.brands[0];assert.equal(stats(b,2024).stores,1240);assert.equal(regional(stats(b,2024),'전국'),1240);assert.equal(stats(b,2000),null);assert.equal(regional(null,'서울'),null);});

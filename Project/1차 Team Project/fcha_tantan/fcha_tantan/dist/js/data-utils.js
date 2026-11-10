export const num = v => v == null ? '미제공' : new Intl.NumberFormat('ko-KR').format(v);
export function stats(brand, year) {return brand.stats.find(s=>s.year===Number(year)) || null;}
export function monthly(s) {return s?.annual_sales_krw == null ? null : Math.round(s.annual_sales_krw/12/10000);}
export function regional(s,region){return s ? (region==='전국'?s.stores:(s.regions[region]??null)) : null;}
export function filterBrands(brands,{query='',category='전체',region='전국',year,sort='stores',saved=null}) {
 let rows=brands.filter(b=>(!query||b.name.includes(query)||b.category.includes(query))&&(category==='전체'||b.category===category)&&(!saved||saved.includes(b.id))&&(region==='전국'||(regional(stats(b,year),region)||0)>0));
 return rows.sort((a,b)=>{const x=stats(a,year),y=stats(b,year);return sort==='name'?a.name.localeCompare(b.name,'ko'):sort==='sales'?(monthly(y)??-1)-(monthly(x)??-1):sort==='opened'?(y?.opened??-1)-(x?.opened??-1):sort==='closed'?(x?.closed??Infinity)-(y?.closed??Infinity):(regional(y,region)??-1)-(regional(x,region)??-1);});
}

'use strict';
// Pure data functions. Uploaded coordinates must be WGS84 longitude/latitude.
window.MarketData = (() => {
  const METROS = ['서울','부산','대구','인천','광주','대전','울산','세종'];
  const clean = value => value == null ? '' : String(value).trim();
  function location(address, region) {
    const text = clean(address) || clean(region);
    const metro = text.match(/^(서울|부산|대구|인천|광주|대전|울산|세종)(?:특별자치시|특별시|광역시)?(?:\s|$)/);
    if (metro) return {city:metro[1],district:(text.slice(metro[0].length).match(/^(\S+[구군])(?:\s|$)/)||[])[1] || ''};
    const province = text.match(/^(\S+(?:도))\s+(\S+[시군])(?:\s|$)/);
    if (province) return {city:province[1],district:province[2]};
    const city = METROS.find(name => clean(region) === name);
    return {city:city || clean(region) || '지역 미분류',district:''};
  }
  function parseStores(data, filename) {
    const result = []; let rejected = 0;
    function visit(node, brand='', region='', depth=0) {
      if (!node || typeof node !== 'object' || depth>25) return;
      if (Array.isArray(node)) {node.forEach(item=>visit(item,brand,region,depth+1));return;}
      if ('lat' in node || 'latitude' in node) {
        const rawLat=node.lat??node.latitude, rawLon=node.lon??node.lng??node.longitude;
        const lat=Number(rawLat),lon=Number(rawLon);
        if (rawLat==null||rawLon==null||clean(rawLat)===''||clean(rawLon)===''||!Number.isFinite(lat)||!Number.isFinite(lon)||lat<33||lat>39.5||lon<124||lon>132) {rejected++;return;}
        const address=clean(node.rdnmAdr||node.address||node.road_address),r=clean(node.region||region);
        const loc=location(address,r);
        result.push({id:result.length,brand:clean(node.brand||node.brandName||node.brand_name||brand||filename||'미분류'),name:clean(node.name||node.store_name),category:clean(node.category||node.industry||'미분류'),region:r,city:clean(node.city||loc.city),district:clean(node.district||loc.district),address,building:clean(node.bldNm||node.building),lat,lon});
        return;
      }
      const nextBrand=clean(node.brand||node.brandName||node.brand_name||brand);
      if (node.regions) {Object.entries(node.regions).forEach(([name,values])=>visit(values,nextBrand||filename,name,depth+1));return;}
      if (node.stores) {visit(node.stores,nextBrand,clean(node.region||region),depth+1);return;}
      Object.entries(node).forEach(([key,value])=>{
        if (!value || typeof value !== 'object') return;
        if (value.regions) visit(value,key,region,depth+1);
        else if (brand) visit(value,brand,region||key,depth+1);
        else visit(value,Array.isArray(data)?filename:key,region,depth+1);
      });
    }
    if (!data || typeof data!=='object') throw Error('매장 JSON은 배열 또는 객체여야 합니다.');
    visit(data,Array.isArray(data)?filename:'');return {stores:result,rejected};
  }
  function onSegment(x,y,a,b) {
    const cross=(x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0]);
    return Math.abs(cross)<1e-10 && x>=Math.min(a[0],b[0])-1e-10 && x<=Math.max(a[0],b[0])+1e-10 && y>=Math.min(a[1],b[1])-1e-10 && y<=Math.max(a[1],b[1])+1e-10;
  }
  function inRing(lon,lat,ring) {
    let inside=false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
      const a=ring[i],b=ring[j];
      if(onSegment(lon,lat,a,b))return true;
      if((a[1]>lat)!==(b[1]>lat)&&lon<(b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0])inside=!inside;
    }return inside;
  }
  function contains(geometry,store) {
    const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
    return polygons.some(rings=>inRing(store.lon,store.lat,rings[0])&&!rings.slice(1).some(ring=>inRing(store.lon,store.lat,ring)));
  }
  function areas(data) {
    const list=data.type==='FeatureCollection'?data.features:data.type==='Feature'?[data]:null;
    if(!Array.isArray(list))throw Error('경계는 GeoJSON FeatureCollection 또는 Feature여야 합니다.');
    return list.map((feature,index)=>{
      const g=feature.geometry,p=feature.properties||{};
      if(!g||!['Polygon','MultiPolygon'].includes(g.type))throw Error('상권 경계에는 Polygon 또는 MultiPolygon이 필요합니다.');
      const polygons=g.type==='Polygon'?[g.coordinates]:g.coordinates;
      if(!Array.isArray(polygons)||!polygons.length)throw Error('빈 상권 경계입니다.');
      polygons.forEach(rings=>{
        if(!Array.isArray(rings)||!rings.length)throw Error('잘못된 경계입니다.');
        rings.forEach(ring=>{
          if(!Array.isArray(ring)||ring.length<4)throw Error('경계의 각 고리는 최소 4개 좌표가 필요합니다.');
          ring.forEach(p=>{if(!Array.isArray(p)||typeof p[0]!=='number'||typeof p[1]!=='number'||!Number.isFinite(p[0])||!Number.isFinite(p[1])||p[0]<124||p[0]>132||p[1]<33||p[1]>39.5)throw Error('한국 WGS84 경위도 좌표가 필요합니다. 투영 좌표는 변환 후 불러오세요.');});
          if(ring[0][0]!==ring[ring.length-1][0]||ring[0][1]!==ring[ring.length-1][1])throw Error('GeoJSON 경계의 시작점과 끝점이 같아야 합니다.');
        });
      });
      return {type:'Feature',geometry:g,properties:{...p,area_code:clean(p.area_code||p.TRDAR_CD||p.ADM_CD||feature.id||`area-${index}`),name:clean(p.name||p.TRDAR_CD_NM||p.ADM_NM||`상권 ${index+1}`)}};
    });
  }
  function stats(data) {
    const rows=Array.isArray(data)?data:data.stats;
    if(!Array.isArray(rows))throw Error('통계 JSON은 stats 배열이 필요합니다.');
    const metrics=['store_count','sales','floating_population','residential_population','opened','closed'];
    return rows.map(row=>{
      if(!row.area_code||!Number.isInteger(Number(row.year))||Number(row.year)<1900||!Number.isInteger(Number(row.quarter))||Number(row.quarter)<1||Number(row.quarter)>4)throw Error('통계에는 area_code, year, quarter(1~4)가 필요합니다.');
      const out={area_code:clean(row.area_code),year:Number(row.year),quarter:Number(row.quarter),category:clean(row.category),brand:clean(row.brand)};
      metrics.forEach(k=>{if(row[k]!=null&&row[k]!==''){const value=Number(row[k]);if(!Number.isFinite(value)||value<0)throw Error('통계 수치는 0 이상의 숫자여야 합니다.');out[k]=value;}});
      return out;
    });
  }
  function rank(stores,key='brand') {
    const counts=new Map();stores.forEach(s=>counts.set(s[key]||'미분류',(counts.get(s[key]||'미분류')||0)+1));
    return [...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'ko'));
  }
  function csv(rows) {
    const cell=v=>'"'+String(v??'').replace(/"/g,'""').replace(/^[=+@\-\t\r]/,"'$&")+'"';
    return '\ufeff'+[['브랜드','매장명','업종','도시','시군구','주소','위도','경도'],...rows.map(s=>[s.brand,s.name,s.category,s.city,s.district,s.address,s.lat,s.lon])].map(row=>row.map(cell).join(',')).join('\r\n');
  }
  return {parseStores,areas,stats,contains,rank,csv,location};
})();

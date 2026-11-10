'use strict';
(() => {
  const $=id=>document.getElementById(id), D=window.MarketData;
  const cities={'서울':[37.5665,126.978],'부산':[35.1796,129.0756],'대구':[35.8714,128.6014],'인천':[37.4563,126.7052],'광주':[35.1595,126.8526],'대전':[36.3504,127.3845],'울산':[35.5384,129.3114],'세종':[36.4801,127.289],'경기도':[37.275,127.01],'강원특별자치도':[37.88,127.73],'충청북도':[36.64,127.49],'충청남도':[36.66,126.67],'전북특별자치도':[35.82,127.15],'전라남도':[34.82,126.46],'경상북도':[36.57,128.73],'경상남도':[35.23,128.68],'제주특별자치도':[33.49,126.53]};
  const seoulDistricts=['강남구','강동구','강북구','강서구','관악구','광진구','구로구','금천구','노원구','도봉구','동대문구','동작구','마포구','서대문구','서초구','성동구','성북구','송파구','양천구','영등포구','용산구','은평구','종로구','중구','중랑구'];
  let stores=[],features=[],statistics=[],selected=null,metric='stores',isDemo=false,map=null,markers=null,areaLayer=null,tiles=null,visible=[],areaObjects=new Map(),tileErrors=0;
  let filters={city:'서울',district:'',category:'',brand:'',year:'',quarter:'',search:''};
  const fmt=n=>Number(n).toLocaleString('ko-KR');
  function element(tag,text,className) {const el=document.createElement(tag);if(text!=null)el.textContent=text;if(className)el.className=className;return el;}
  function status(message,error=false){$('map-status').textContent=message;$('map-status').classList.toggle('error',error);$('map-status').hidden=!message;}
  function selectOptions(id,values,label){const el=$(id),old=el.value;el.replaceChildren(new Option(label,''));[...new Set(values.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),'ko')).forEach(value=>el.add(new Option(value,value)));if([...el.options].some(o=>o.value===old))el.value=old;}
  function refreshOptions(){
    selectOptions('city',[...Object.keys(cities),...stores.map(s=>s.city)],'전국');$('city').value=filters.city;
    refreshDistricts();selectOptions('category',stores.map(s=>s.category),'전체 업종');selectOptions('brand',stores.map(s=>s.brand),'전체 브랜드');
    selectOptions('year',statistics.map(s=>String(s.year)),'전체');
  }
  function refreshDistricts(){selectOptions('district',[...($('city').value==='서울'?seoulDistricts:[]),...stores.filter(s=>!$('city').value||s.city===$('city').value).map(s=>s.district)],'전체');}
  function readFilters(){for(const key of Object.keys(filters))filters[key]=$(key).value.trim();}
  function filtered(){
    const needle=filters.search.toLocaleLowerCase('ko');
    return stores.filter(s=>(!filters.city||s.city===filters.city)&&(!filters.district||s.district===filters.district)&&(!filters.category||s.category===filters.category)&&(!filters.brand||s.brand===filters.brand)&&(!needle||[s.brand,s.name,s.address,s.building].join(' ').toLocaleLowerCase('ko').includes(needle))&&(!selected||D.contains(selected.geometry,s))&&(!$('viewport').checked||!map||map.getBounds().contains([s.lat,s.lon])));
  }
  function fitStores(rows){if(map&&rows.length)map.fitBounds(L.latLngBounds(rows.map(s=>[s.lat,s.lon])),{paddingTopLeft:[40,90],paddingBottomRight:window.innerWidth>760?[350,45]:[40,45],maxZoom:16});}
  function navigateCity(){
    if(!map)return;
    const matching=stores.filter(s=>(!filters.city||s.city===filters.city)&&(!filters.district||s.district===filters.district));
    if(filters.district&&matching.length)fitStores(matching);
    else if(cities[filters.city])map.setView(cities[filters.city],['서울','부산','대구','인천','광주','대전','울산','세종'].includes(filters.city)?12:9);
    else if(matching.length)fitStores(matching);
    else if(!filters.city)map.setView([36.3,127.8],7);
  }
  function apply(navigate=false){readFilters();render();if(navigate)navigateCity();}
  function popup(store){const box=element('div',null,'store-popup');box.append(element('strong',store.name||store.brand),element('div',store.brand+' · '+store.category),element('div',store.address||[store.city,store.district].join(' ')));if(store.building)box.append(element('small',store.building));if(isDemo)box.append(element('small','가상 예시 매장 · 실제 영업 정보 아님'));return box;}
  function renderMarkers(){
    if(!map)return;markers.clearLayers();
    if(!$('show-stores').checked)return;
    visible.slice(0,5000).forEach(store=>L.circleMarker([store.lat,store.lon],{renderer:map._marketRenderer,radius:6,color:'#fff',weight:2,fillColor:'#ed6a3e',fillOpacity:.9}).bindPopup(popup(store)).addTo(markers));
  }
  function setArea(feature){selected=feature;$('popup')?.remove();render();if(map){const layer=areaObjects.get(feature.properties.area_code);if(layer)map.fitBounds(layer.getBounds(),{paddingTopLeft:[40,80],paddingBottomRight:window.innerWidth>760?[350,50]:[40,50],maxZoom:16});}}
  function drawAreas(){
    if(!map)return;areaLayer.clearLayers();areaObjects.clear();
    L.geoJSON({type:'FeatureCollection',features},{style:feature=>({color:selected?.properties.area_code===feature.properties.area_code?'#ef6a3d':'#3476d2',weight:2,fillOpacity:.12}),onEachFeature:(feature,layer)=>{
      areaObjects.set(feature.properties.area_code,layer);
      const label=element('span',feature.properties.name);
      layer.bindTooltip(label,{className:'area-label',sticky:true});layer.on('click',()=>setArea(feature));
    }}).addTo(areaLayer);
    if(!$('show-areas').checked)map.removeLayer(areaLayer);
  }
  function updateAreaStyle(){areaObjects.forEach((layer,code)=>{const active=selected?.properties.area_code===code;layer.setStyle({color:active?'#ef6a3d':'#3476d2',weight:active?3:2,fillOpacity:active?.22:.10});});}
  function metricRows(){
    if(!selected)return [];
    let rows=statistics.filter(s=>s.area_code===selected.properties.area_code&&(!filters.year||s.year===Number(filters.year))&&(!filters.quarter||s.quarter===Number(filters.quarter))&&(!filters.category||s.category===filters.category)&&(!filters.brand||s.brand===filters.brand));
    // Show a single quarter to avoid summing the same population across periods.
    if(rows.length){const latest=Math.max(...rows.map(s=>s.year*4+s.quarter));rows=rows.filter(s=>s.year*4+s.quarter===latest);}
    return rows;
  }
  function renderMetric(){
    const target=$('metric-content');target.replaceChildren();
    if(metric==='stores'){
      target.append(element('span',fmt(visible.length)+'개','metric-value'),element('div','현재 조건에 맞는 매장 파일의 점포수입니다.','metric-note'));
      if(filters.year||filters.quarter)target.append(element('div','매장 위치 파일에는 시점 정보가 없어 연도·분기 조건은 별도 통계에만 적용합니다.','metric-note'));
      return;
    }
    if(!selected){target.append(element('p','불러온 상권 경계를 지도에서 선택하세요.','empty-copy'));return;}
    const rows=metricRows().filter(s=>s[metric]!=null);
    if(!rows.length){target.append(element('p','해당 조건의 통계 데이터가 없습니다. 통계 JSON을 불러오세요.','empty-copy'));return;}
    const unit=metric==='sales'?'원':'명';
    rows.forEach(s=>{const block=element('div');block.append(element('strong',fmt(s[metric])+unit,'metric-value'),element('div',`${s.year}년 ${s.quarter}분기 · ${s.category||'전체 업종'} · ${s.brand||'전체 브랜드'}`,'metric-note'));target.append(block);});
    target.append(element('div','선택 조건의 최신 분기만 표시합니다. 서로 겹칠 수 있는 통계는 합산하지 않습니다.','metric-note'));
  }
  function renderRanking(){
    const rank=D.rank(visible).slice(0,10),target=$('ranking');target.replaceChildren();
    if(!rank.length){target.append(element('p',stores.length?'이 지역·조건에 해당하는 매장이 없습니다.':'매장 파일을 불러오면 브랜드 순위가 표시됩니다.','empty-copy'));return;}
    rank.forEach(([name,count],index)=>{const row=element('div',null,'rank-row'),nameBox=element('div'),track=element('div',null,'rank-track'),bar=element('span');bar.style.width=(count/rank[0][1]*100)+'%';track.append(bar);nameBox.append(element('div',name,'rank-name'),track);row.append(element('span',String(index+1).padStart(2,'0'),'rank-index'),nameBox,element('span',fmt(count)+'개','rank-count'));target.append(row);});
  }
  function render(){
    visible=filtered();
    $('location-title').textContent=[filters.city||'전국',filters.district||'전체 지역'].join(' · ');
    $('selection-title').textContent=selected?selected.properties.name:'선택 지역 분석';
    $('selection-description').textContent=selected?'선택한 경계 안의 매장과 연결된 통계입니다. 주소 검색·업종·브랜드 필터도 함께 적용됩니다.':'도시·시군구를 선택하거나, 불러온 상권 경계를 클릭하세요.';
    $('store-count').replaceChildren(document.createTextNode(fmt(visible.length)),element('small','개'));
    $('brand-count').replaceChildren(document.createTextNode(fmt(D.rank(visible).length)),element('small','개'));
    $('result-count').textContent=fmt(visible.length);$('area-count').textContent='상권 경계 '+fmt(features.length)+'개';
    $('empty-state').hidden=stores.length>0||features.length>0;
    $('data-badge').textContent=isDemo?'가상 예시 데이터':stores.length||features.length?'내 데이터 연결됨':'데이터 미연결';$('data-badge').classList.toggle('demo',isDemo);
    $('scope-note').textContent=(isDemo?'가상 예시 · 실제 상권 분석에 사용하지 마세요. ':'입력된 데이터만 분석 · 서울시 공식 통계 자동 연동 없음. ')+(visible.length>5000?'조회 매장 중 지도에는 최대 5,000개 점을 표시합니다.':'');
    renderMarkers();updateAreaStyle();renderRanking();renderMetric();
  }
  function mergeByCode(existing,incoming){const records=new Map(existing.map(f=>[f.properties.area_code,f]));incoming.forEach(f=>records.set(f.properties.area_code,f));return [...records.values()];}
  async function loadOnline(){
    const config=window.MARKET_CONFIG||{};
    const sources=[['매장',config.storesUrl],['상권',config.areasUrl],['통계',config.statsUrl]].filter(([,url])=>url);
    if(!sources.length){$('data-status').textContent='assets/config.js에 storesUrl, areasUrl, statsUrl 서버 주소를 넣으면 연결됩니다. 온라인연결.md를 참고하세요.';return;}
    $('online').disabled=true;$('data-status').textContent='온라인 서버에서 데이터를 불러오는 중입니다…';
    try{
      // Download all configured responses before changing the current data.
      const files=await Promise.all(sources.map(async([name,url])=>{
        const response=await fetch(url,{headers:{Accept:'application/json'},credentials:'same-origin',signal:AbortSignal.timeout(20000)});
        if(!response.ok)throw Error(name+' 서버 응답 오류: HTTP '+response.status);
        const text=await response.text(),data=JSON.parse(text.replace(/^\uFEFF/,''));
        // Validate every snapshot before discarding the previous working data.
        if(name==='매장'){if(!D.parseStores(data,'온라인 매장').stores.length && !(Array.isArray(data)&&data.length===0) && !(Array.isArray(data?.stores)&&data.stores.length===0))throw Error('매장 서버의 응답 형식이나 좌표를 확인하세요.');}
        else if(name==='상권')D.areas(data);
        else D.stats(data);
        return {name:name+'.json',text:async()=>text};
      }));
      // A reload is a fresh snapshot, not an append of duplicate stores.
      stores=[];features=[];statistics=[];selected=null;isDemo=false;
      await importFiles(files);
    }catch(error){$('data-status').textContent='온라인 연결 실패: '+error.message+' · 서버 주소, HTTPS, 서버의 CORS 설정을 확인하세요.';}
    finally{$('online').disabled=false;}
  }
  async function importFiles(files){
    const errors=[];let accepted=0,rejected=0,storeAdded=false;
    // Selecting another upload replaces the demo before adding real user data.
    if(isDemo){stores=[];features=[];statistics=[];selected=null;isDemo=false;}
    for(const file of files){
      try{
        const data=JSON.parse((await file.text()).replace(/^\uFEFF/,''));
        if(data?.type==='FeatureCollection'||data?.type==='Feature')features=mergeByCode(features,D.areas(data));
        else if(data&&Array.isArray(data.stats)){
          const incoming=D.stats(data),records=new Map(statistics.map(s=>[JSON.stringify([s.area_code,s.year,s.quarter,s.category,s.brand]),s]));incoming.forEach(s=>records.set(JSON.stringify([s.area_code,s.year,s.quarter,s.category,s.brand]),s));statistics=[...records.values()];
        }else{
          const parsed=D.parseStores(data,file.name.replace(/\.json$/i,''));
          const emptySnapshot=(Array.isArray(data)&&data.length===0)||(Array.isArray(data?.stores)&&data.stores.length===0);
          if(!parsed.stores.length&&!emptySnapshot)throw Error('유효한 한국 위도·경도 매장을 찾지 못했습니다.');
          stores.push(...parsed.stores);rejected+=parsed.rejected;storeAdded=true;
        }
        accepted++;
      }catch(e){errors.push(file.name+': '+e.message);}
    }
    if(storeAdded&&stores.length&&!stores.some(s=>s.city===filters.city)){filters.city=stores[0].city;filters.district='';}
    refreshOptions();readFilters();drawAreas();render();
    if(storeAdded){navigateCity();fitStores(visible);}else if(features.length&&map)map.fitBounds(areaLayer.getBounds(),{padding:[40,40]});
    $('data-status').textContent=`${accepted}개 파일 연결 · 매장 ${fmt(stores.length)}개 · 상권 ${features.length}개 · 통계 ${statistics.length}행`+(rejected?` · 좌표 오류 ${rejected}개 제외`:'')+(errors.length?' / '+errors.join(' / '):'');
    $('files').value='';
  }
  function loadDemo(){
    if(!isDemo&&(stores.length||features.length||statistics.length)){$('data-status').textContent='불러온 데이터를 유지합니다. 예시를 보려면 새로고침 후 예시 버튼을 누르세요.';return;}
    isDemo=true;selected=null;
    const rows=[['예시 커피 A','예시 성수 1호점','카페',37.5445,127.0553],['예시 커피 A','예시 성수 2호점','카페',37.5462,127.058],['예시 커피 B','예시 로스터리','카페',37.5424,127.052],['예시 식당','예시 한식점','음식점',37.5452,127.05],['예시 베이커리','예시 빵집','제과점',37.5431,127.0573],['예시 편의점','예시 성수점','소매업',37.547,127.0534]];
    stores=D.parseStores(rows.map(([brand,name,category,lat,lon])=>({brand,name,category,lat,lon,address:'서울특별시 성동구 성수동 (가상 예시 주소)'})),'예시').stores;
    features=D.areas({type:'FeatureCollection',features:[{type:'Feature',properties:{area_code:'DEMO-01',name:'성수 일대 · 가상 예시 경계'},geometry:{type:'Polygon',coordinates:[[[127.046,37.539],[127.062,37.539],[127.062,37.55],[127.046,37.55],[127.046,37.539]]]}}]});
    statistics=[];filters={city:'서울',district:'성동구',category:'',brand:'',year:'',quarter:'',search:''};
    Object.keys(filters).forEach(k=>$(k).value=filters[k]);refreshOptions();$('district').value='성동구';drawAreas();readFilters();render();fitStores(visible);
    $('data-status').textContent='가상 매장 6개와 가상 경계 1개입니다. 실제 주소·점포·상권이 아닙니다. 매출·인구 예시는 만들지 않았습니다.';
  }
  function report(){
    const target=$('report-content');target.replaceChildren();
    target.append(element('p',(isDemo?'가상 예시 데이터 / ':'')+[$('location-title').textContent,selected?.properties.name].filter(Boolean).join(' / ')));
    target.append(element('p',`업종: ${filters.category||'전체'} · 브랜드: ${filters.brand||'전체'} · 연도: ${filters.year||'전체'} · 분기: ${filters.quarter||'전체'}`));
    target.append(element('p',`매장 ${fmt(visible.length)}개 · 브랜드 ${fmt(D.rank(visible).length)}개`));
    const table=element('table'),head=element('tr');head.append(element('th','브랜드'),element('th','점포수'));table.append(head);D.rank(visible).slice(0,20).forEach(([name,count])=>{const tr=element('tr');tr.append(element('td',name),element('td',fmt(count)));table.append(tr);});target.append(table);
    const rows=metricRows();if(rows.length)rows.forEach(s=>target.append(element('p',`${s.year}년 ${s.quarter}분기 · ${s.category||'전체'} · ${s.brand||'전체'} / 매출 ${s.sales==null?'미등록':fmt(s.sales)+'원'} / 유동인구 ${s.floating_population==null?'미등록':fmt(s.floating_population)+'명'} / 주거인구 ${s.residential_population==null?'미등록':fmt(s.residential_population)+'명'}`)));
    else target.append(element('p','연결된 매출·인구 통계가 없습니다.'));
    target.append(element('p','사용자가 불러온 데이터 기준입니다. 공식 서울시 통계와 연동되지 않습니다. 매장 위치 파일의 점포수는 연도·분기에 따라 변경되지 않습니다.'));
    $('report-dialog').showModal();
  }
  function loadScript(url){return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=url;script.onload=resolve;script.onerror=()=>{script.remove();reject(Error('지도 라이브러리 연결 실패'));};document.head.append(script);});}
  async function initMap(){
    try{await loadScript('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js');}catch{
      $('leaflet-css').href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      try{await loadScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js');}catch{status('지도 라이브러리를 불러오지 못했습니다. 인터넷 연결과 CDN 접속 차단 여부를 확인하세요. 매장 파일 분석은 사용할 수 있습니다.',true);return;}
    }
    map=L.map('map',{preferCanvas:true,zoomControl:true}).setView([37.5665,126.978],12);
    map._marketRenderer=L.canvas({padding:.5});markers=L.layerGroup().addTo(map);areaLayer=L.layerGroup().addTo(map);
    L.control.scale({imperial:false,position:'bottomleft'}).addTo(map);
    if(location.protocol!=='file:'){
      tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{minZoom:5,maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',referrerPolicy:'strict-origin-when-cross-origin',updateWhenIdle:true,keepBuffer:1});
      tiles.on('tileerror',()=>{tileErrors++;status('도로 지도 연결에 실패했습니다. 인터넷·보안 확장 프로그램을 확인하세요. Access blocked가 보이면 서비스 차단 상태이므로 아래 안내의 정책을 확인하세요.',true);});
      tiles.on('load',()=>{if(!tileErrors)status('');});tiles.addTo(map);
    }else status('도로 지도는 지도실행.cmd로 실행한 로컬 웹주소에서 표시됩니다. HTML 파일 직접 열기로는 지도 타일을 요청하지 않습니다.',true);
    map.on('moveend',()=>{if($('viewport').checked)render();});
    drawAreas();render();
    if(stores.length)fitStores(visible);
  }
  $('city').addEventListener('change',()=>{selected=null;$('district').value='';refreshDistricts();apply(true);});
  $('district').addEventListener('change',()=>{selected=null;apply(true);if(filters.district&&!visible.length)$('data-status').textContent='이 시·군·구의 매장이나 경계가 없습니다. 해당 지역 파일을 불러오면 위치를 확대할 수 있습니다.';});
  $('apply').addEventListener('click',()=>apply(true));
  ['category','brand','year','quarter'].forEach(id=>$(id).addEventListener('change',()=>apply()));
  $('search').addEventListener('input',()=>apply());
  $('reset').addEventListener('click',()=>{selected=null;Object.keys(filters).forEach(k=>$(k).value='');refreshDistricts();$('viewport').checked=false;apply(true);});
  $('fit').addEventListener('click',()=>{if(visible.length)fitStores(visible);else $('data-status').textContent='현재 조건에 맞는 매장이 없습니다. 지역·업종 필터를 확인하거나 매장 파일을 불러오세요.';});
  $('show-stores').addEventListener('change',renderMarkers);
  $('show-areas').addEventListener('change',()=>{if(!map)return;if($('show-areas').checked)areaLayer.addTo(map);else map.removeLayer(areaLayer);});
  $('viewport').addEventListener('change',render);
  $('clear-area').addEventListener('click',()=>{selected=null;render();});
  $('files').addEventListener('change',e=>importFiles([...e.target.files]));
  $('online').addEventListener('click',loadOnline);
  ['demo','empty-demo'].forEach(id=>$(id).addEventListener('click',loadDemo));
  document.querySelectorAll('[data-metric]').forEach(button=>button.addEventListener('click',()=>{metric=button.dataset.metric;document.querySelectorAll('[data-metric]').forEach(b=>b.setAttribute('aria-selected',String(b===button)));renderMetric();}));
  $('export').addEventListener('click',()=>{const blob=new Blob([D.csv(visible)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=element('a');link.href=url;link.download=(isDemo?'가상예시_':'')+'상권지도_조회매장.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('guide').addEventListener('click',()=>$('help-dialog').showModal());$('report').addEventListener('click',report);$('print').addEventListener('click',()=>window.print());
  document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  if(location.protocol==='file:')$('file-warning').hidden=false;
  refreshOptions();$('city').value='서울';render();initMap();
})();

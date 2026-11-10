(() => {
 const t=value=>window.TT?window.TT(value):value;
 const note=message=>window.tantanToast?.(message);
 const SIDO={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','강원도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','전라북도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주'};
 const areaForm=document.querySelector('[data-area-filter]');
 if(areaForm){
  const sido=areaForm.elements.region,district=areaForm.elements.sigungu,dong=areaForm.elements.dong;
  let seq=0;
  async function options(){const call=++seq;try{const params=new URLSearchParams({region:sido.value,sigungu:district.value});const data=await (await fetch('/market/map/areas/?'+params)).json();if(call!==seq)return;
   for(const [id,values] of [['district-options',data.districts],['dong-options',data.dongs]]){const list=document.getElementById(id);list.replaceChildren(...values.map(value=>{const option=document.createElement('option');option.value=value;return option;}));}
  }catch(_){} }
  sido.addEventListener('change',()=>{district.value='';dong.value='';options();});district.addEventListener('change',()=>{dong.value='';options();});options();
  areaForm.querySelector('[data-area-address]').addEventListener('click',()=>{
   if(!window.daum?.Postcode){note('주소 검색 서비스를 불러오지 못했습니다.');return;}
   new daum.Postcode({oncomplete(data){sido.value=SIDO[data.sido]||data.sido;district.value=data.sigungu||'';dong.value=data.bname||data.bname1||'';areaForm.requestSubmit();}}).open();
  });
 }
 function ready(callback,box){
  function run(){if(window.kakao?.maps)kakao.maps.load(callback);else if(box&&!box.querySelector('.map-empty')){const p=document.createElement('div');p.className='map-empty';p.textContent=t('지도를 불러오지 못했습니다. 연결 설정을 확인해주세요.');box.replaceChildren(p);}}
  if(document.readyState==='complete')run();else window.addEventListener('load',run,{once:true});
 }
 const region=document.querySelector('[data-region-map]');
 if(region){
  const status=document.querySelector('[data-map-status]'),list=document.querySelector('[data-place-list]');
  if(!region.dataset.keyReady){status.textContent=t('지도 연결 후 매장 분포를 확인할 수 있습니다.');document.querySelectorAll('[data-map-mode]').forEach(button=>button.addEventListener('click',()=>note('지도 연결 후 매장 분포를 확인할 수 있습니다.')));}
  ready(()=>{
   let markers=[],mode='kakao',searchId=0,publicTimer=null,publicController=null;const fallback=new kakao.maps.LatLng(37.5665,126.9780);
   const map=new kakao.maps.Map(region,{center:fallback,level:7});map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
   const geocoder=new kakao.maps.services.Geocoder(),places=new kakao.maps.services.Places(map),info=new kakao.maps.InfoWindow({removable:true});
   const cluster=window.kakao.maps.MarkerClusterer?new kakao.maps.MarkerClusterer({map,averageCenter:true,minLevel:7}):null;
   const area=[region.dataset.region,region.dataset.district,region.dataset.dong].filter(Boolean).join(' ');
   const hasSelection=region.dataset.lat!=='' && region.dataset.lng!=='' && region.hasAttribute('data-lat') && region.hasAttribute('data-lng');
   const conditionForm=document.querySelector('[data-dashboard-condition]');
   const conditionField=name=>conditionForm?.elements.namedItem(name);
   const selectedCategory=()=>conditionField('category')?.value||'전체';
   const categoryActive=()=>!['','전체'].includes(selectedCategory());
   let selectedPoint=null,selectionMarker=null,selectionCircle=null,selectionSequence=0;
   let radius=Number(conditionField('radius_m')?.value||region.dataset.radius||500);
   const boundaryShapes=[];
   async function loadNearby(point,sequence){
    try{
     const params=new URLSearchParams({lat:point.getLat(),lng:point.getLng()});
     const response=await fetch('/market/analysis/geometry/?'+params);if(!response.ok)throw new Error();
     const data=await response.json();if(sequence!==selectionSequence)return;
     boundaryShapes.forEach(shape=>shape.setMap(null));boundaryShapes.length=0;
     const areas=data.areas||[];
     const nearbyBounds=new kakao.maps.LatLngBounds();nearbyBounds.extend(point);
     areas.forEach(a=>{
      const polygons=a.geometry.type==='Polygon'?[a.geometry.coordinates]:a.geometry.coordinates;
      polygons.forEach(rings=>{
       rings[0].forEach(p=>{const position=new kakao.maps.LatLng(Number(p[1]),Number(p[0]));nearbyBounds.extend(position);});
       const shape=new kakao.maps.Polygon({map,path:rings.map(ring=>ring.map(p=>new kakao.maps.LatLng(Number(p[1]),Number(p[0])))),strokeColor:a.contains?'#247fff':'#e39429',strokeWeight:2,fillColor:a.contains?'#80baff':'#ffc56c',fillOpacity:.18});
       boundaryShapes.push(shape);
       const label=document.createElement('div');label.className='map-info';label.textContent=a.name;
       const popup=new kakao.maps.InfoWindow({content:label,removable:true});boundaryShapes.push({setMap:()=>popup.close()});
       kakao.maps.event.addListener(shape,'mouseover',event=>{popup.setPosition(event.latLng);popup.open(map);});
       kakao.maps.event.addListener(shape,'mouseout',()=>popup.close());
       kakao.maps.event.addListener(shape,'click',event=>{kakao.maps.event.preventMap();popup.close();updateSelection(event.latLng,true);});
      });

     });
     if(areas.length)map.setBounds(nearbyBounds,40,40,40,40);
    }catch(error){}
   }

   function withinRadius(lat,lng){if(!selectedPoint)return true;const rad=Math.PI/180,dy=(Number(lat)-selectedPoint.getLat())*rad,dx=(Number(lng)-selectedPoint.getLng())*rad;const a=Math.sin(dy/2)**2+Math.cos(selectedPoint.getLat()*rad)*Math.cos(Number(lat)*rad)*Math.sin(dx/2)**2;return 12742000*Math.asin(Math.min(1,Math.sqrt(a)))<=radius;}
   function circleParams(params){if(selectedPoint){params.set('lat',selectedPoint.getLat());params.set('lng',selectedPoint.getLng());params.set('radius',radius);}return params;}
   function updateSelection(point,reverse=false){
    const sequence=++selectionSequence;selectedPoint=point;
    boundaryShapes.forEach(shape=>shape.setMap(null));boundaryShapes.length=0;
    if(!selectionMarker){selectionMarker=new kakao.maps.Marker({map,position:point,draggable:true,title:'희망 위치'});kakao.maps.event.addListener(selectionMarker,'dragend',()=>updateSelection(selectionMarker.getPosition(),true));}
    else selectionMarker.setPosition(point);
    if(!selectionCircle)selectionCircle=new kakao.maps.Circle({map,center:point,radius,strokeColor:'#1677ff',strokeStyle:'dashed',fillColor:'#1677ff',fillOpacity:.08});
    else {selectionCircle.setPosition(point);selectionCircle.setRadius(radius);}
    if(conditionForm){conditionField('latitude').value=String(point.getLat());conditionField('longitude').value=String(point.getLng());conditionField('location_scope').value='address';
     if(reverse){conditionField('location').value='지도에서 선택한 위치';geocoder.coord2Address(point.getLng(),point.getLat(),(rows,code)=>{if(sequence!==selectionSequence)return;if(code===kakao.maps.services.Status.OK&&rows.length)conditionField('location').value=rows[0].road_address?.address_name||rows[0].address.address_name;});}}
    map.setCenter(point);loadNearby(point,sequence);runSearch();
   }
   kakao.maps.event.addListener(map,'click',event=>updateSelection(event.latLng,true));
   conditionForm?.addEventListener('analysis-location-changed',()=>{const lat=conditionField('latitude').value,lng=conditionField('longitude').value;if(lat!==''&&lng!=='')updateSelection(new kakao.maps.LatLng(Number(lat),Number(lng)));});
   conditionField('category')?.addEventListener('change',()=>runSearch());
   conditionField('radius_m')?.addEventListener('change',()=>{radius=Number(conditionField('radius_m').value);if(selectionCircle)selectionCircle.setRadius(radius);runSearch();});
   if(hasSelection){
    selectedPoint=new kakao.maps.LatLng(Number(region.dataset.lat),Number(region.dataset.lng));
    selectionMarker=new kakao.maps.Marker({map,position:selectedPoint,draggable:true,title:'희망 위치'});
    kakao.maps.event.addListener(selectionMarker,'dragend',()=>updateSelection(selectionMarker.getPosition(),true));
    selectionCircle=new kakao.maps.Circle({map,center:selectedPoint,radius,strokeColor:'#1677ff',strokeStyle:'dashed',fillColor:'#1677ff',fillOpacity:.08});
    map.setCenter(selectedPoint);map.setLevel(5);
    loadNearby(selectedPoint,selectionSequence);
   }
   let areaCenter=null;
   geocoder.addressSearch(area,(results,code)=>{if(code===kakao.maps.services.Status.OK&&results[0]){areaCenter=new kakao.maps.LatLng(results[0].y,results[0].x);if(!selectedPoint){map.setCenter(areaCenter);map.setLevel(region.dataset.dong?4:region.dataset.district?6:8);}}});
   const hoverInfo=new kakao.maps.InfoWindow({removable:false});
   function clear(){hoverInfo.close();markers.forEach(marker=>marker.setMap(null));markers=[];cluster?.clear();list.replaceChildren();info.close();}
   function showPoint(item,bounds){
    if(!withinRadius(item.lat,item.lng))return;
    const position=new kakao.maps.LatLng(Number(item.lat),Number(item.lng));const marker=new kakao.maps.Marker({position,map:cluster?null:map,title:item.name});markers.push(marker);bounds.extend(position);
    const hoverName=document.createElement('div');hoverName.className='map-info';hoverName.textContent=item.name;
    kakao.maps.event.addListener(marker,'mouseover',()=>{hoverInfo.setContent(hoverName);hoverInfo.open(map,marker);});
    kakao.maps.event.addListener(marker,'mouseout',()=>hoverInfo.close());
    const content=document.createElement('div');content.className='map-info';const title=document.createElement('b');title.textContent=item.name;content.append(title,document.createTextNode(item.address||item.area||''));
    if(item.industry){content.append(document.createElement('br'),document.createTextNode(item.industry));}
    if(item.url){const link=document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=t('카카오맵에서 보기');content.append(document.createElement('br'),link);}
    function focus(){map.panTo(position);info.setContent(content);info.open(map,marker);}
    kakao.maps.event.addListener(marker,'click',()=>{updateSelection(position,true);info.setContent(content);info.open(map,selectionMarker);});
    const button=document.createElement('button');button.type='button';button.className='map-place-item';const b=document.createElement('b');b.textContent=item.name;const small=document.createElement('small');small.textContent=item.address||item.area||'';button.append(b,small);button.addEventListener('click',focus);list.append(button);
   }
   async function registered(){const id=++searchId;clear();status.textContent=t('등록 매장을 불러오는 중입니다.');try{const params=circleParams(new URLSearchParams(location.search));params.set('category',selectedCategory());params.delete('query');if(!params.get('region'))params.set('region',region.dataset.region);const response=await fetch('/market/map/locations/?'+params);if(!response.ok)throw new Error();const data=await response.json();if(id!==searchId)return;
    const bounds=new kakao.maps.LatLngBounds();data.points.forEach(point=>showPoint(point,bounds));if(cluster)cluster.addMarkers(markers);if(markers.length&&!selectedPoint)map.setBounds(bounds);
    status.textContent=t('공개 등록 매장')+' '+data.total+' · '+t('지도 표시')+' '+data.points.length+(data.located>data.limit?' / '+data.located:'');
    if(!data.points.length)status.textContent=t('이 지역의 공개 등록 매장이 없습니다. 전국 장소검색을 이용해보세요.');
   }catch(_){if(id===searchId)status.textContent=t('매장 분포를 불러오지 못했습니다. 다시 시도해주세요.');}}
   async function publicStores(){
    if(mode!=='kakao')return;
    const id=++searchId;publicController?.abort();publicController=new AbortController();clear();status.textContent=t('장소를 불러오는 중입니다.');
    const bounds=map.getBounds(),sw=bounds.getSouthWest(),ne=bounds.getNorthEast();
    const dy=radius/111000,dx=selectedPoint?dy/Math.max(.01,Math.cos(selectedPoint.getLat()*Math.PI/180)):0;
    const params=circleParams(new URLSearchParams({west:selectedPoint?selectedPoint.getLng()-dx:sw.getLng(),south:selectedPoint?selectedPoint.getLat()-dy:sw.getLat(),east:selectedPoint?selectedPoint.getLng()+dx:ne.getLng(),north:selectedPoint?selectedPoint.getLat()+dy:ne.getLat()}));
    params.set('category',selectedCategory());
    try{
     const response=await fetch('/market/map/public-stores/?'+params,{signal:publicController.signal});const data=await response.json();if(id!==searchId)return;
     if(!response.ok)throw new Error(data.error||'장소 조회에 실패했습니다.');
     if(!data.total){if(data.category_mapping==='unmapped'){status.textContent=t('선택한 희망 업종의 공공 업종 대응이 없어 표시할 수 없습니다. 인증 점주 모드에서는 브랜드 업종으로 조회합니다.');return;}search(true);return;}
     const pointBounds=new kakao.maps.LatLngBounds();data.points.forEach(point=>showPoint(point,pointBounds));if(cluster)cluster.addMarkers(markers);
     status.textContent='저장된 상가정보 · 조건 일치 '+data.total.toLocaleString()+'개 · 지도 표시 '+data.points.length.toLocaleString()+'개'+(data.truncated?' · 희망 업종이나 반경으로 범위를 좁혀주세요.':'')+' · 프로젝트 스냅샷 '+(data.reference_on||'미등록');
    }catch(error){if(id===searchId&&error.name!=='AbortError')search(true);}
   }
   kakao.maps.event.addListener(map,'idle',()=>{if(mode!=='kakao')return;clearTimeout(publicTimer);publicTimer=setTimeout(publicStores,300);});
   function setMode(value){mode=value;++searchId;publicController?.abort();clearTimeout(publicTimer);document.querySelectorAll('[data-map-mode]').forEach(button=>button.classList.toggle('active',button.dataset.mapMode===mode));}
   function search(useBounds=false){
    if(categoryActive()){++searchId;clear();status.textContent=t('선택한 희망 업종의 저장 매장이 없거나 조회에 실패했습니다. 카카오는 세부 업종 조건을 보장할 수 없어 대체 검색을 중단합니다.');return;}
    const keyword='매장';
    setMode('kakao');const id=++searchId;clear();status.textContent=t('카카오 장소를 검색하고 있습니다.');const bounds=new kakao.maps.LatLngBounds();let count=0,pages=0,total=0;const seen=new Set();
    const options={size:15};if(selectedPoint){options.location=selectedPoint;options.radius=radius;options.sort=kakao.maps.services.SortBy?.DISTANCE||'distance';}else if(useBounds)options.bounds=map.getBounds();
    places.keywordSearch(useBounds?keyword:area+' '+keyword,(results,code,pagination)=>{
     if(id!==searchId)return;
     if(code!==kakao.maps.services.Status.OK){status.textContent=t(code===kakao.maps.services.Status.ZERO_RESULT?'검색 결과가 없습니다.':'지도 검색에 실패했습니다. 키와 허용 도메인을 확인해주세요.');return;}
     pages++;total=pagination.totalCount;
     results.forEach(place=>{if(seen.has(place.id)||count>=45)return;seen.add(place.id);count++;
      showPoint({name:place.place_name,lat:place.y,lng:place.x,address:place.road_address_name||place.address_name,url:place.place_url},bounds);
     });
     if(pagination.hasNextPage&&pages<3&&count<45){pagination.nextPage();return;}
     if(cluster)cluster.addMarkers(markers);if(markers.length&&!useBounds)map.setBounds(bounds);
     status.textContent=t('카카오 검색')+' '+total+' · '+t('지도 표시')+' '+markers.length+' / '+t('전체 매장 수와 다를 수 있습니다.');
    },options);
   }
   document.querySelectorAll('[data-map-mode]').forEach(button=>button.addEventListener('click',()=>{setMode(button.dataset.mapMode);mode==='registered'?registered():publicStores();}));
   const runSearch=()=>mode==='registered'?registered():publicStores();
   publicStores();
  },region);
 }
 const transfer=document.querySelector('[data-transfer-map]');
 if(transfer){ready(()=>{
  const data=JSON.parse(document.getElementById('transfer-map-data')?.textContent||'[]');const map=new kakao.maps.Map(transfer,{center:new kakao.maps.LatLng(37.5665,126.9780),level:7});map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
  const bounds=new kakao.maps.LatLngBounds(),info=new kakao.maps.InfoWindow({removable:true,disableAutoPan:true});const byId=new Map();
  let infoCloseTimer;
  const keepInfo=()=>clearTimeout(infoCloseTimer);
  const hideInfo=()=>{keepInfo();infoCloseTimer=setTimeout(()=>info.close(),180);};
  kakao.maps.event.addListener(map,'click',()=>info.close());
  data.forEach(item=>{
   const position=new kakao.maps.LatLng(item.lat,item.lng),marker=new kakao.maps.Marker({position,map});bounds.extend(position);
   function showInfo(){
    keepInfo();
    const box=document.createElement('div');box.className='map-info';
    box.style.cssText='box-sizing:border-box;width:220px;max-width:220px;white-space:normal;overflow-wrap:anywhere;overflow:hidden;';
    const brand=document.createElement('b');brand.textContent=item.brand;
    const address=document.createElement('div');address.textContent=item.label;
    const link=document.createElement('a');link.href=item.url;link.textContent=t('매물 상세 보기');
    box.addEventListener('mouseenter',keepInfo);box.addEventListener('mouseleave',hideInfo);
    box.addEventListener('focusin',keepInfo);box.addEventListener('focusout',hideInfo);
    box.append(brand,address,link);info.setContent(box);info.open(map,marker);
   }
   function focus(){map.setLevel(4);map.setCenter(position);showInfo();document.querySelectorAll('[data-listing-card]').forEach(card=>card.classList.toggle('is-focused',card.dataset.listingCard==item.id));}
   byId.set(String(item.id),focus);kakao.maps.event.addListener(marker,'mouseover',showInfo);kakao.maps.event.addListener(marker,'click',focus);
   kakao.maps.event.addListener(marker,'mouseout',hideInfo);
  });
  if(data.length){
   map.setBounds(bounds);
   // 매물이 한 곳에 모여 있어도 첫 화면은 동네 범위로 표시합니다.
   if(map.getLevel()<7)map.setLevel(7);
  }
  document.querySelectorAll('[data-focus-listing]').forEach(button=>button.addEventListener('click',()=>{byId.get(button.dataset.focusListing)?.();if(innerWidth<960)transfer.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'center'});}));
 },transfer);}
})();

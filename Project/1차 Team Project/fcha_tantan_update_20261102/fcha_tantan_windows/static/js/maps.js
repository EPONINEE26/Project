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
  if(!region.dataset.keyReady){status.textContent=t('지도 연결 후 매장 분포를 확인할 수 있습니다.');document.querySelectorAll('[data-map-mode],[data-place-search],[data-bounds-search]').forEach(button=>button.addEventListener('click',()=>note('지도 연결 후 매장 분포를 확인할 수 있습니다.')));}
  ready(()=>{
   let markers=[],mode='registered',searchId=0;const fallback=new kakao.maps.LatLng(37.5665,126.9780);
   const map=new kakao.maps.Map(region,{center:fallback,level:7});map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
   const geocoder=new kakao.maps.services.Geocoder(),places=new kakao.maps.services.Places(map),info=new kakao.maps.InfoWindow({removable:true});
   const cluster=window.kakao.maps.MarkerClusterer?new kakao.maps.MarkerClusterer({map,averageCenter:true,minLevel:7}):null;
   const area=[region.dataset.region,region.dataset.district,region.dataset.dong].filter(Boolean).join(' ');
   let areaCenter=null;
   geocoder.addressSearch(area,(results,code)=>{if(code===kakao.maps.services.Status.OK&&results[0]){areaCenter=new kakao.maps.LatLng(results[0].y,results[0].x);if(!markers.length){map.setCenter(areaCenter);map.setLevel(region.dataset.dong?4:region.dataset.district?6:8);}}});
   function clear(){markers.forEach(marker=>marker.setMap(null));markers=[];cluster?.clear();list.replaceChildren();info.close();}
   function showPoint(item,bounds){
    const position=new kakao.maps.LatLng(Number(item.lat),Number(item.lng));const marker=new kakao.maps.Marker({position,map:cluster?null:map});markers.push(marker);bounds.extend(position);
    const content=document.createElement('div');content.className='map-info';const title=document.createElement('b');title.textContent=item.name;content.append(title,document.createTextNode(item.address||item.area||''));
    if(item.url){const link=document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=t('카카오맵에서 보기');content.append(document.createElement('br'),link);}
    function focus(){map.panTo(position);info.setContent(content);info.open(map,marker);}
    kakao.maps.event.addListener(marker,'click',focus);
    const button=document.createElement('button');button.type='button';button.className='map-place-item';const b=document.createElement('b');b.textContent=item.name;const small=document.createElement('small');small.textContent=item.address||item.area||'';button.append(b,small);button.addEventListener('click',focus);list.append(button);
   }
   async function registered(){const id=++searchId;clear();status.textContent=t('등록 매장을 불러오는 중입니다.');try{const params=new URLSearchParams(location.search);if(!params.get('region'))params.set('region',region.dataset.region);const response=await fetch('/market/map/locations/?'+params);if(!response.ok)throw new Error();const data=await response.json();if(id!==searchId)return;
    const bounds=new kakao.maps.LatLngBounds();data.points.forEach(point=>showPoint(point,bounds));if(cluster)cluster.addMarkers(markers);if(markers.length)map.setBounds(bounds);
    status.textContent=t('공개 등록 매장')+' '+data.total+' · '+t('지도 표시')+' '+data.points.length+(data.located>data.limit?' / '+data.located:'');
    if(!data.points.length)status.textContent=t('이 지역의 공개 등록 매장이 없습니다. 전국 장소검색을 이용해보세요.');
   }catch(_){status.textContent=t('매장 분포를 불러오지 못했습니다. 다시 시도해주세요.');}}
   function setMode(value){mode=value;document.querySelectorAll('[data-map-mode]').forEach(button=>button.classList.toggle('active',button.dataset.mapMode===mode));}
   function search(useBounds=false){
    const keyword=document.querySelector('#place-keyword').value.trim();if(!keyword){note('브랜드 또는 업종을 입력해주세요.');return;}
    setMode('kakao');const id=++searchId;clear();status.textContent=t('카카오 장소를 검색하고 있습니다.');const bounds=new kakao.maps.LatLngBounds();let count=0,pages=0,total=0;const seen=new Set();
    const options={size:15};if(useBounds)options.bounds=map.getBounds();
    places.keywordSearch(useBounds?keyword:area+' '+keyword,(results,code,pagination)=>{
     if(id!==searchId)return;
     if(code!==kakao.maps.services.Status.OK){status.textContent=t(code===kakao.maps.services.Status.ZERO_RESULT?'검색 결과가 없습니다.':'지도 검색에 실패했습니다. 키와 허용 도메인을 확인해주세요.');return;}
     pages++;total=pagination.totalCount;
     results.forEach(place=>{if(seen.has(place.id)||count>=45)return;seen.add(place.id);count++;
      showPoint({name:place.place_name,lat:place.y,lng:place.x,address:place.road_address_name||place.address_name,url:place.place_url},bounds);
     });
     if(pagination.hasNextPage&&pages<3&&count<45){pagination.nextPage();return;}
     if(cluster)cluster.addMarkers(markers);if(markers.length&&!useBounds)map.setBounds(bounds);
     status.textContent=t('카카오 검색')+' '+total+' · '+t('지도 표시')+' '+count+' / '+t('전체 매장 수와 다를 수 있습니다.');
    },options);
   }
   document.querySelectorAll('[data-map-mode]').forEach(button=>button.addEventListener('click',()=>{setMode(button.dataset.mapMode);mode==='registered'?registered():search();}));
   document.querySelector('[data-place-search]').addEventListener('click',()=>search());document.querySelector('[data-bounds-search]').addEventListener('click',()=>search(true));
   document.querySelector('#place-keyword').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();search();}});
   registered();
  },region);
 }
 const transfer=document.querySelector('[data-transfer-map]');
 if(transfer){ready(()=>{
  const data=JSON.parse(document.getElementById('transfer-map-data')?.textContent||'[]');const map=new kakao.maps.Map(transfer,{center:new kakao.maps.LatLng(37.5665,126.9780),level:7});map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
  const bounds=new kakao.maps.LatLngBounds(),info=new kakao.maps.InfoWindow({removable:true});const byId=new Map();
  data.forEach(item=>{
   const position=new kakao.maps.LatLng(item.lat,item.lng),marker=new kakao.maps.Marker({position,map});bounds.extend(position);
   function focus(){map.panTo(position);map.setLevel(4);const box=document.createElement('div');box.className='map-info';const title=document.createElement('b');title.textContent=item.name;box.append(title,document.createTextNode(item.label));const link=document.createElement('a');link.href=item.url;link.textContent=t('매물 상세 보기');box.append(document.createElement('br'),link);info.setContent(box);info.open(map,marker);document.querySelectorAll('[data-listing-card]').forEach(card=>card.classList.toggle('is-focused',card.dataset.listingCard==item.id));}
   byId.set(String(item.id),focus);kakao.maps.event.addListener(marker,'click',focus);
  });
  if(data.length)map.setBounds(bounds);
  document.querySelectorAll('[data-focus-listing]').forEach(button=>button.addEventListener('click',()=>{byId.get(button.dataset.focusListing)?.();if(innerWidth<960)transfer.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'center'});}));
 },transfer);}
})();

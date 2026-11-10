(()=>{
 const form=document.querySelector('.analysis-condition-form');if(!form)return;
 const field=n=>form.elements.namedItem(n);
 form.addEventListener('invalid',event=>{const details=event.target.closest('details');if(details)details.open=true;},true);
 document.querySelectorAll('[data-budget]').forEach(b=>b.addEventListener('click',()=>field('total_budget_manwon').value=b.dataset.budget));
 const geo=address=>{if(!window.kakao?.maps)return;const previousLat=field('latitude').value,previousLng=field('longitude').value;kakao.maps.load(()=>new kakao.maps.services.Geocoder().addressSearch(address,(rows,status)=>{if(field('location').value!==address||field('latitude').value!==previousLat||field('longitude').value!==previousLng)return;if(status===kakao.maps.services.Status.OK&&rows.length){field('latitude').value=rows[0].y;field('longitude').value=rows[0].x;form.dispatchEvent(new CustomEvent('analysis-location-changed'));}}));};
 document.querySelector('#analysis-address')?.addEventListener('click',()=>{if(!window.daum?.Postcode){alert('주소 검색을 불러오지 못했습니다. 주소를 직접 입력해주세요.');return;}new daum.Postcode({oncomplete:data=>{field('location').value=data.roadAddress||data.jibunAddress;field('location_scope').value='address';field('latitude').value='';field('longitude').value='';geo(field('location').value);}}).open();});
 field('location').addEventListener('input',()=>{field('latitude').value='';field('longitude').value='';field('location_scope').value='dong';});
 const shopFields=['area','area_unit','floor','rent_manwon','management_manwon','deposit_manwon','premium_manwon'];const showShop=()=>shopFields.forEach(n=>{const row=field(n)?.closest('.analysis-field');if(row)row.hidden=field('store_status').value==='none';});field('store_status').addEventListener('change',showShop);showShop();
 if(form.hasAttribute('data-dashboard-condition'))return;
 const box=document.createElement('div');box.className='analysis-selected-map';box.setAttribute('aria-label','선택 위치와 공식 상권 경계');const side=document.createElement('aside');side.className='analysis-map-side';form.after(side);side.append(box);
 if(!window.kakao?.maps){box.textContent='지도 연결 대기 · 주소 입력과 조건 저장은 이용하실 수 있습니다.';return;}
 kakao.maps.load(()=>{const lat=field('latitude').value,lon=field('longitude').value;if(!lat||!lon){box.textContent='주소 검색 후 저장하면 선택 위치와 공식 경계를 표시합니다.';return;}
 const point=new kakao.maps.LatLng(Number(lat),Number(lon)),map=new kakao.maps.Map(box,{center:point,level:5});const marker=new kakao.maps.Marker({map,position:point,draggable:true});
 const pick=position=>{marker.setPosition(position);field('latitude').value=String(position.getLat());field('longitude').value=String(position.getLng());field('location_scope').value='address';field('location').value='지도에서 선택한 위치';new kakao.maps.services.Geocoder().coord2Address(position.getLng(),position.getLat(),(rows,status)=>{if(status===kakao.maps.services.Status.OK&&rows.length)field('location').value=rows[0].road_address?.address_name||rows[0].address.address_name;});};
 kakao.maps.event.addListener(map,'click',event=>pick(event.latLng));kakao.maps.event.addListener(marker,'dragend',()=>pick(marker.getPosition()));
 const note=document.createElement('p');note.className='analysis-scope';side.append(note);
 fetch('/market/analysis/geometry/').then(r=>r.json()).then(data=>{note.textContent=data.name?('통계 구역: '+data.name+(data.note?' · '+data.note:'')):data.note;let g=data.geometry;if(!g)return;let polys=g.type==='Polygon'?[g.coordinates]:g.coordinates;polys.forEach(rings=>new kakao.maps.Polygon({map,path:rings.map(r=>r.map(c=>new kakao.maps.LatLng(c[1],c[0]))),strokeColor:'#247fff',fillColor:'#80baff',fillOpacity:.15}));}).catch(()=>note.textContent='상권 경계를 불러오지 못했습니다.');
 const label=document.createElement('label'),toggle=document.createElement('input');toggle.type='checkbox';label.append(toggle,document.createTextNode(' 반경 표시 (공식 통계 구역과 별개 · 매장 집계는 자료 연결 전 판단 보류)'));side.append(label);const circle=new kakao.maps.Circle({center:point,radius:Number(field('radius_m').value),strokeStyle:'dashed',strokeColor:'#247fff',fillOpacity:.05});toggle.addEventListener('change',()=>circle.setMap(toggle.checked?map:null));
 });
})();

// 2026-10-26 추가 기능: 주소 검색, 매장 지도, 양도양수 고정 패널, 업종 대분류 칩

// 0) 업종 묶음(커피·한식…)을 바꾸면 세부 업종을 ‘전체’로 되돌린 뒤 제출합니다(제출보다 먼저 실행되도록 capture 단계).
document.addEventListener('change', event => {
 if(!event.target.matches('input[name="group"]') || !event.target.form) return;
 const form = event.target.form;
 const select = form.querySelector('select[name="category"]');
 if(select) select.value = '전체';
 form.querySelectorAll('input[name="category"]').forEach(input => { input.checked = input.value === '전체'; });
}, true);

// 0-0) 좁은 화면에서 업종 아이콘 줄이 가로로 넘칠 때, 선택한 업종이 보이도록 스크롤합니다.
document.querySelectorAll('.category-grid').forEach(grid => {
 const active = grid.querySelector('.cat-tile.active');
 if(active && grid.scrollWidth > grid.clientWidth) grid.scrollLeft = Math.max(0, active.offsetLeft - grid.offsetLeft - 8);
});

// 0-2) 회원가입 이메일 인증 — 인증번호 받기 → 6자리 입력 → 인증 확인
document.querySelectorAll('[data-email-verify]').forEach(box => {
 const form = box.closest('form');
 const email = form.querySelector('[data-email-input]');
 const send = box.querySelector('[data-send]'), row = box.querySelector('[data-code-row]');
 const code = box.querySelector('[data-code]'), check = box.querySelector('[data-check]'), status = box.querySelector('[data-status]');
 let verified = (box.dataset.verified || '').toLowerCase(), timer;
 const value = () => email.value.trim().toLowerCase();
 function show(message, ok){ status.textContent = message; status.className = 'verify-status' + (ok === true ? ' ok' : ok === false ? ' bad' : ''); }
 function refresh(){
  const done = verified && value() === verified;
  box.classList.toggle('is-verified', !!done);
  send.hidden = !!done;
  if(done){ row.hidden = true; show('✓ 이메일 인증 완료', true); }
  else if(status.classList.contains('ok')) show('');
 }
 function cooldown(seconds){
  clearInterval(timer); let left = seconds; send.disabled = true;
  const tick = () => { send.textContent = left > 0 ? `다시 받기 (${left}초)` : '인증번호 다시 받기'; if(left-- <= 0){ clearInterval(timer); send.disabled = false; } };
  tick(); timer = setInterval(tick, 1000);
 }
 async function post(url, data){
  const body = new FormData();
  body.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);
  Object.entries(data).forEach(([k, v]) => body.append(k, v));
  const response = await fetch(url, {method:'POST', body, headers:{'X-Requested-With':'fetch'}});
  return response.json();
 }
 send.addEventListener('click', async () => {
  if(!email.value.trim() || !email.checkValidity()){ show('이메일 주소를 먼저 올바르게 입력해주세요.', false); email.focus(); return; }
  send.disabled = true;
  try {
   const result = await post(box.dataset.sendUrl, {email: value()});
   show(result.message, result.ok ? null : false);
   if(result.ok){ row.hidden = false; code.value = ''; code.focus(); }
   if(result.cooldown) cooldown(result.cooldown); else send.disabled = false;
  } catch (_) { show('인증번호를 보내지 못했어요. 잠시 후 다시 시도해주세요.', false); send.disabled = false; }
 });
 check.addEventListener('click', async () => {
  if(!/^\d{6}$/.test(code.value.trim())){ show('인증번호 6자리를 입력해주세요.', false); code.focus(); return; }
  try {
   const result = await post(box.dataset.checkUrl, {email: value(), code: code.value.trim()});
   if(result.ok){ verified = value(); refresh(); } else show(result.message, false);
  } catch (_) { show('확인하지 못했어요. 잠시 후 다시 시도해주세요.', false); }
 });
 code.addEventListener('keydown', event => { if(event.key === 'Enter'){ event.preventDefault(); check.click(); } });
 email.addEventListener('input', refresh);
 refresh();
});

// 0-3) 창업 목적 질문 — ‘예’일 때만 창업 조건 입력칸을 펼칩니다.
document.querySelectorAll('[data-startup-fields]').forEach(section => {
 const form = section.closest('form');
 const sync = () => {
  const yes = form.querySelector('input[name="wants_startup"][value="yes"]');
  section.hidden = !(yes && yes.checked);
 };
 form.addEventListener('change', event => { if(event.target.name === 'wants_startup') sync(); });
 sync();
});

// 0-1) 브랜드 검색 입력칸 — 입력한 글자로 서버에서 20개까지 찾아 자동완성 목록(datalist)에 넣습니다.
document.querySelectorAll('input[data-brand-lookup]').forEach((input, index) => {
 const list = document.createElement('datalist');
 list.id = 'brand-lookup-' + index;
 input.setAttribute('list', list.id);
 input.insertAdjacentElement('afterend', list);
 let timer, last = '';
 input.addEventListener('input', () => {
  clearTimeout(timer);
  const q = input.value.trim();
  if(!q || q === last || /\([-\w]+\)\s*$/.test(q)) return;
  timer = setTimeout(async () => {
   last = q;
   try {
    const response = await fetch('/brands/lookup/?q=' + encodeURIComponent(q));
    const data = await response.json();
    list.replaceChildren(...data.results.map(item => { const o = document.createElement('option'); o.value = item.value; o.label = item.label; return o; }));
   } catch (_) {}
  }, 200);
 });
});

// 1) 주소 검색(다음 우편번호 서비스) — data-postcode="address" 입력칸 옆에 버튼을 붙입니다.
(() => {
 const SIDO = {'서울':'서울','부산':'부산','대구':'대구','인천':'인천','광주':'광주','대전':'대전','울산':'울산','세종':'세종','경기':'경기','강원':'강원','제주':'제주',
  '충청북도':'충북','충북':'충북','충청남도':'충남','충남':'충남','전라북도':'전북','전북':'전북','전라남도':'전남','전남':'전남','경상북도':'경북','경북':'경북','경상남도':'경남','경남':'경남'};
 function sidoName(value){
  if(!value) return '';
  for(const key of Object.keys(SIDO)){ if(value.startsWith(key)) return SIDO[key]; }
  return '';
 }
 document.querySelectorAll('input[data-postcode="address"]').forEach(address => {
  const form = address.form;
  const field = name => form.querySelector('[data-postcode="'+name+'"]');
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'button small outline postcode-button'; button.textContent = '주소 검색';
  address.insertAdjacentElement('afterend', button);
  button.addEventListener('click', () => {
   if(!window.daum || !daum.Postcode){ alert('주소 검색 서비스를 불러오지 못했습니다. 인터넷 연결을 확인해주세요.'); return; }
   new daum.Postcode({oncomplete(data){
    if(field('postcode')) field('postcode').value = data.zonecode;
    address.value = data.roadAddress || data.jibunAddress || data.address;
    const sido = field('sido'); if(sido){ const name = sidoName(data.sido); if(name) sido.value = name; }
    if(field('sigungu')) field('sigungu').value = data.sigungu || '';
    if(field('dong')) field('dong').value = data.bname || '';
    address.dispatchEvent(new CustomEvent('tantan:address', {bubbles:true, detail:{address:address.value}}));
    if(field('detail')) field('detail').focus();
   }}).open();
  });
 });
})();

// 2) 카카오 지도 — 키가 있을 때만 스크립트가 로드됩니다. data-editable이면 클릭으로 좌표 변경.
(() => {
 const box = document.querySelector('[data-kakao-map]');
 if(!box) return;
 function start(){
  if(!window.kakao || !kakao.maps){ box.textContent = '지도를 불러오지 못했습니다. 카카오 지도 키와 등록 도메인을 확인하세요.'; return; }
  kakao.maps.load(() => {
   const lat = parseFloat(box.dataset.lat), lng = parseFloat(box.dataset.lng);
   const center = Number.isFinite(lat) && Number.isFinite(lng) ? new kakao.maps.LatLng(lat, lng) : new kakao.maps.LatLng(37.5665, 126.9780);
   const map = new kakao.maps.Map(box, {center, level: Number.isFinite(lat) ? 3 : 7});
   const marker = new kakao.maps.Marker({position:center, map: Number.isFinite(lat) ? map : null, draggable:!!box.dataset.editable});
   if(!box.dataset.editable) return;
   const latInput = document.querySelector('[data-map="lat"]'), lngInput = document.querySelector('[data-map="lng"]');
   function setPoint(point){
    marker.setPosition(point); marker.setMap(map); map.panTo(point);
    if(latInput) latInput.value = point.getLat().toFixed(6);
    if(lngInput) lngInput.value = point.getLng().toFixed(6);
   }
   kakao.maps.event.addListener(map, 'click', event => setPoint(event.latLng));
   kakao.maps.event.addListener(marker, 'dragend', () => setPoint(marker.getPosition()));
   const geocoder = kakao.maps.services ? new kakao.maps.services.Geocoder() : null;
   const addressInput=document.querySelector('[data-postcode=address]');
   addressInput?.addEventListener('change',()=>addressInput.dispatchEvent(new CustomEvent('tantan:address',{bubbles:true,detail:{address:addressInput.value}})));
   document.addEventListener('tantan:address', event => {
    if(!geocoder) return;
    geocoder.addressSearch(event.detail.address, (result, status) => {
     if(status === kakao.maps.services.Status.OK && result[0]) setPoint(new kakao.maps.LatLng(result[0].y, result[0].x));
    });
   });
  });
 }
 if(document.readyState === 'complete') start(); else window.addEventListener('load', start, {once:true});
})();

// 3) 양도양수 고정 패널 — 넓은 화면에서는 펼쳐 두고, 좁은 화면에서는 탭을 눌러 엽니다.
(() => {
 const widget = document.querySelector('[data-transfer-widget]');
 if(!widget) return;
 const tab = widget.querySelector('.transfer-tab'), close = widget.querySelector('.transfer-close');
 const key = 'tantan-transfer-widget';
 let stored = null;
 try { stored = localStorage.getItem(key); } catch (_) {}
 function open(value, remember){
  widget.classList.toggle('is-open', value);
  tab.setAttribute('aria-expanded', String(value));
  if(remember){ try { localStorage.setItem(key, value ? 'open' : 'closed'); } catch (_) {} }
 }
 const wide = matchMedia('(min-width: 1600px)');
 open(stored ? stored === 'open' : wide.matches, false);
 tab.addEventListener('click', () => open(!widget.classList.contains('is-open'), true));
 close.addEventListener('click', () => { open(false, true); tab.focus(); });
 document.addEventListener('keydown', event => { if(event.key === 'Escape' && widget.classList.contains('is-open') && !wide.matches) open(false, false); });
})();

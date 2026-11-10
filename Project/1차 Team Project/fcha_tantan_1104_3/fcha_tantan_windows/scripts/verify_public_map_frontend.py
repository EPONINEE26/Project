"""실제 지도 JS를 headless Chrome과 카카오 SDK 모형으로 실행합니다."""
import json
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CHROME = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
HTML = '''<!doctype html><html><body>
<button data-map-mode="registered"></button><button data-map-mode="kakao" class="active"></button>
<div data-region-map data-region="서울" data-key-ready="1" data-lat="" data-lng=""></div>
<p data-map-status></p><div data-place-list></div>
<form class="analysis-condition-form" data-dashboard-condition>
<input name="location"><input name="latitude"><input name="longitude"><input name="location_scope">
<select name="radius_m"><option>300</option><option selected>500</option><option>1000</option></select>
<div class="analysis-field"><input name="store_status" value="none"></div>
<div class="analysis-field"><input name="area"><input name="area_unit"><input name="floor"><input name="rent_manwon"><input name="management_manwon"><input name="deposit_manwon"><input name="premium_manwon"></div>
<button id="analysis-address" type="button">주소</button></form>
<pre id="result">PENDING</pre>
<script>
window.errors=[];window.addEventListener('error',event=>errors.push(event.message));
window.calls=[];window.tantanToast=()=>{};
class LatLng {constructor(lat,lng){this.lat=lat;this.lng=lng;} getLat(){return this.lat;} getLng(){return this.lng;}}
class Bounds {extend(){} getSouthWest(){return new LatLng(37.49,126.97);} getNorthEast(){return new LatLng(37.51,127);}}
class MapMock {constructor(){window.testMap=this;} addControl(){} setCenter(){} setLevel(){} panTo(){} setBounds(){} getBounds(){return new Bounds();}}
window.testMarkers=[];
class Overlay {constructor(options){this.position=options?.position;if(options?.title&&options.title!=='희망 위치')testMarkers.push(this);}setPosition(point){this.position=point;}getPosition(){return this.position;}setRadius(){}setMap(){} addMarkers(){} clear(){} close(){this.visible=false;} setContent(content){this.content=content;} open(){this.visible=true;window.lastInfo=this;}}
window.kakao={maps:{load:fn=>fn(),LatLng,LatLngBounds:Bounds,Map:MapMock,ZoomControl:Overlay,
 Marker:Overlay,MarkerClusterer:Overlay,InfoWindow:Overlay,Circle:Overlay,Polygon:Overlay,
 ControlPosition:{RIGHT:1},event:{addListener:(obj,name,fn)=>{obj[name]=fn;}},
 services:{Status:{OK:'OK',ZERO_RESULT:'ZERO'},Geocoder:class{addressSearch(address,fn){if(address==='검색 주소')fn([{y:'37.501',x:'127.001'}],'OK');}coord2Address(lng,lat,fn){fn([{address:{address_name:'클릭 주소'}}],'OK');}},
 Places:class{keywordSearch(keyword,fn){fn([{id:1,place_name:'카카오 장소',y:37.5,x:127,address_name:'서울'}],'OK',{totalCount:1,hasNextPage:false});}}}}};
window.fetch=async url=>{calls.push(String(url));
 const data=String(url).includes('public-industries')?{industries:[{id:1,name:'카페'}]}:
 String(url).includes('public-stores')?{points:window.emptyStores?[]:[{id:1,name:'공공 카페',lat:37.5,lng:127,address:'서울',industry:'카페'}],total:window.emptyStores?0:1,reference_on:'2026-11-03'}:
 {points:[{id:2,name:'인증 매장',lat:37.5,lng:127}],total:1,located:1,limit:500};
 return {ok:true,json:async()=>data};};
</script>
<script>new Function(SOURCE)();</script>
<script>window.daum={Postcode:class{constructor(options){this.options=options;}open(){this.options.oncomplete({roadAddress:'검색 주소'});}}};new Function(ANALYSIS_SOURCE)();</script>
<script>
window.addEventListener('load',async()=>{
 const wait=()=>new Promise(resolve=>setTimeout(resolve,100));
 const assert=(ok,message)=>{if(!ok)throw new Error(message);};
 try {
  await wait();assert(document.querySelector('[data-place-list]').textContent.includes('공공 카페'),'기본 공공 상가 표시');
  const marker=testMarkers.at(-1);marker.mouseover();assert(lastInfo.visible&&lastInfo.content.textContent==='공공 카페','마커 이름 호버');marker.mouseout();assert(!lastInfo.visible,'호버 닫기');
  assert(!document.querySelector('#place-keyword,[data-place-search],[data-bounds-search]'),'검색 UI 제거');
  document.querySelector('[data-map-mode="registered"]').click();await wait();assert(document.querySelector('[data-place-list]').textContent.includes('인증 매장'),'인증 모드');
  window.emptyStores=true;document.querySelector('[data-map-mode="kakao"]').click();await wait();assert(document.querySelector('[data-place-list]').textContent.includes('카카오 장소'),'카카오 자동 검색');
  window.emptyStores=false;document.querySelector('[data-map-mode="kakao"]').click();await wait();assert(document.querySelector('[data-place-list]').textContent.includes('공공 카페'),'저장 데이터 복귀');
  assert(document.querySelectorAll('[data-map-mode]').length===2,'탭 2개 유지');
  window.testMap.click({latLng:new LatLng(37.5,127)});await wait();
  const form=document.querySelector('form');assert(form.elements.latitude.value==='37.5'&&form.elements.location.value==='클릭 주소','지도 클릭 위치 반영');
  assert(new URL(calls.at(-1),'https://local').searchParams.get('radius')==='500','반경 전달');
  form.elements.radius_m.value='300';form.elements.radius_m.dispatchEvent(new Event('change'));await wait();assert(new URL(calls.at(-1),'https://local').searchParams.get('radius')==='300','반경 변경 반영');
  document.querySelector('#analysis-address').click();await wait();assert(form.elements.latitude.value==='37.501'&&form.elements.longitude.value==='127.001','주소검색으로 핀 이동');
  assert(!errors.length,errors.join(';'));document.querySelector('#result').textContent='PASS: marker hover, no search UI, two tabs, registered, fallback, radius, address pin';
 }catch(error){document.querySelector('#result').textContent='FAIL: '+error.message;}
});
</script></body></html>'''


def main():
    source = (BASE / 'static/js/maps.js').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='map-frontend-') as directory:
        path = Path(directory) / 'check.html'
        analysis=(BASE / 'static/js/analysis.js').read_text(encoding='utf-8')
        html=HTML.replace('ANALYSIS_SOURCE',json.dumps(analysis).replace('</','<\\/'))
        path.write_text(html.replace('SOURCE', json.dumps(source).replace('</', '<\\/')), encoding='utf-8')
        result = subprocess.run([
            str(CHROME), '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            '--disable-background-networking', '--virtual-time-budget=4000',
            '--user-data-dir=' + str(Path(directory) / 'profile'), '--dump-dom', path.as_uri(),
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45,
           creationflags=subprocess.CREATE_NO_WINDOW)
        import re
        match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout)
        message = match.group(1) if match else 'FAIL: Chrome did not return test output: ' + result.stderr[-500:]
        print(message)
        if not message.startswith('PASS:'):
            raise SystemExit(1)


if __name__ == '__main__':
    main()

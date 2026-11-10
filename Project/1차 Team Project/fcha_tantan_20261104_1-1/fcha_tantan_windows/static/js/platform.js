(() => {
 const t = value => window.TT ? window.TT(value) : value;
 const csrf = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
 let toastTimer;
 function toast(message){const node=document.querySelector('.site-toast');if(!node)return;node.textContent=t(message);node.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.hidden=true,4500);}
 window.tantanToast=toast;
 document.addEventListener('submit',event=>{const form=event.target;if(form.dataset.confirm&&!confirm(t(form.dataset.confirm)))event.preventDefault();});
 // Checkbox selection is idempotent on the server and keeps the viewport steady.
 function syncComparison(data){
  document.querySelectorAll('[data-compare-form]').forEach(form=>{const checked=data.ids.includes(form.dataset.slug);form.querySelector('[data-compare-checkbox]').checked=checked;form.elements.selected.value=checked?'0':'1';});
  const count=document.querySelector('#compare-count');if(count)count.textContent=data.ids.length;
  const tray=document.querySelector('[data-compare-tray]');if(!tray)return;
  tray.hidden=!data.ids.length;document.body.classList.toggle('has-compare',!!data.ids.length);
  tray.querySelector('[data-tray-title]').textContent=t('브랜드 비교')+' '+data.ids.length+'/'+(data.limit||tray.dataset.limit);
  tray.querySelector('[data-tray-items]').replaceChildren(...data.brands.map(brand=>{
   const tag=document.createElement('span');tag.className='tray-item';tag.append(document.createTextNode(brand.name));
   const remove=document.createElement('button');remove.type='button';remove.textContent='×';remove.setAttribute('aria-label',brand.name+' '+t('비교 해제'));
   remove.addEventListener('click',()=>select(brand.toggle_url,false,remove));tag.append(remove);return tag;
  }));
 }
 let comparisonQueue=Promise.resolve();
 function select(url,wanted,control){control.disabled=true;comparisonQueue=comparisonQueue.then(()=>updateSelection(url,wanted,control));}
 async function updateSelection(url,wanted,control){
  control.disabled=true;
  try{const body=new FormData();body.append('csrfmiddlewaretoken',csrf());body.append('selected',wanted?'1':'0');
   const response=await fetch(url,{method:'POST',body,headers:{'X-Requested-With':'fetch'}});const data=await response.json();
   if(!Array.isArray(data.ids))throw new Error();syncComparison(data);
   const feedback=document.querySelector('[data-compare-feedback]');if(feedback)feedback.textContent=data.message||'';
   if(data.message)toast(data.message);
  }catch(_){if(control.matches('input'))control.checked=!wanted;toast('처리하지 못했습니다. 다시 시도해주세요.');}finally{control.disabled=false;}
 }
 document.querySelectorAll('[data-compare-form]').forEach(form=>{
  form.querySelector('[data-compare-checkbox]').addEventListener('change',event=>select(form.action,event.target.checked,event.target));
 });
 document.body.classList.toggle('has-compare',!!document.querySelector('[data-compare-tray]:not([hidden])'));
 // All brands are rendered by Django. Search is a case-insensitive contains match,
 // never a 30-row API sample; the native select retains every matching brand.
 document.querySelectorAll('[data-reference-form]').forEach(form=>{
  const search=form.querySelector('[data-reference-search]'),select=form.querySelector('[data-reference-select]');
  const status=form.querySelector('[data-reference-count]'),suggestions=form.querySelector('[data-reference-suggestions]');
  const brands=[...select.options].filter(option=>option.value).map(option=>({slug:option.value,name:option.textContent,category:option.dataset.category||'',company:option.dataset.company||''}));
  const normalize=value=>value.normalize('NFKC').toLocaleLowerCase().trim();
  const count=value=>new Intl.NumberFormat(document.body.dataset.language==='en'?'en-US':'ko-KR').format(value);
  const en=document.body.dataset.language==='en';let composing=false;
  select.options[0].textContent=t('선택 안 함 · 직접 입력');
  function render(){
   if(composing)return;
   const query=normalize(search.value),matches=brands.filter(brand=>normalize(brand.name).includes(query));
   const previous=select.value,fragment=document.createDocumentFragment();fragment.append(new Option(t('선택 안 함 · 직접 입력'),''));
   const groups=new Map();matches.forEach(brand=>{if(!groups.has(brand.category))groups.set(brand.category,[]);groups.get(brand.category).push(brand);});
   groups.forEach((items,category)=>{const group=document.createElement('optgroup');group.label=category+' ('+count(items.length)+')';items.forEach(brand=>group.append(new Option(brand.name,brand.slug,false,brand.slug===previous)));fragment.append(group);});
   select.replaceChildren(fragment);if(!matches.some(brand=>brand.slug===previous))select.value='';
   status.textContent=en?(query?count(matches.length)+' matching brands / '+count(brands.length)+' total':count(brands.length)+' brands · grouped by category'):(query?'검색 결과 '+count(matches.length)+'개 / 전체 '+count(brands.length)+'개':'전체 '+count(brands.length)+'개 브랜드 · 업종별 목록');
   suggestions.replaceChildren();suggestions.hidden=!query;
   if(!query)return;
   if(!matches.length){const empty=document.createElement('p');empty.textContent=t('검색 결과가 없습니다.');suggestions.append(empty);return;}
   // Suggestions stay compact; all matches remain in the select below.
   matches.slice().sort((a,b)=>Number(normalize(b.name).startsWith(query))-Number(normalize(a.name).startsWith(query))||a.name.localeCompare(b.name,'ko')).slice(0,8).forEach(brand=>{const button=document.createElement('button');button.type='button';button.dataset.referenceSuggestion=brand.slug;const name=document.createElement('b');name.textContent=brand.name;name.dataset.noTranslate='';const meta=document.createElement('small');meta.textContent=[brand.category,brand.company].filter(Boolean).join(' · ');meta.dataset.noTranslate='';button.append(name,meta);button.addEventListener('click',()=>{select.value=brand.slug;suggestions.hidden=true;select.focus();status.textContent=(en?'Selected: ':'선택: ')+brand.name;});suggestions.append(button);});
   if(matches.length>8){const more=document.createElement('p');more.textContent=en?'All matches are available in the dropdown below.':'일치하는 모든 브랜드는 아래 드롭다운에서 볼 수 있어요.';suggestions.append(more);}
  }
  search.addEventListener('compositionstart',()=>composing=true);
  search.addEventListener('compositionend',()=>{composing=false;render();});
  search.addEventListener('input',render);
  search.addEventListener('keydown',event=>{if(event.isComposing)return;if(event.key==='Escape'){suggestions.hidden=true;}if(event.key==='ArrowDown'){const first=suggestions.querySelector('button');if(first&&!suggestions.hidden){event.preventDefault();first.focus();}}if(event.key==='Enter'&&search.value.trim()){event.preventDefault();select.focus();}});
  suggestions.addEventListener('keydown',event=>{const buttons=[...suggestions.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);if(event.key==='Escape'){suggestions.hidden=true;search.focus();}if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();buttons[Math.max(0,Math.min(buttons.length-1,i+(event.key==='ArrowDown'?1:-1)))]?.focus();}});
  select.addEventListener('change',()=>suggestions.hidden=true);
 });
 // Local input filtering, with Korean composition support. Auth and ID fields are untouched.
 const terms=JSON.parse(document.querySelector('#content-filter-terms')?.textContent||'[]');
 const excluded=new Set(['email','username','login','brand','password','password1','password2','phone','contact_phone','business_number','postcode','url','path']);
 const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const patterns=terms.filter(v=>typeof v==='string'&&v.length&&v.length<=40).map(word=>{
  const body=[...word.normalize('NFKC')].map(escape).join('[\\s._*·\\-]*');return new RegExp(/^[\x00-\x7f]+$/.test(word)?'(?<![A-Za-z])'+body+'(?![A-Za-z])':body,'gi');
 });
 const rawByForm=new WeakMap();
 function clean(value){let result=value.normalize('NFKC').replace(/[\u200b-\u200f\u202a-\u202e\u2060\ufeff]/g,'');let found=false;patterns.forEach(pattern=>{pattern.lastIndex=0;if(pattern.test(result)){found=true;pattern.lastIndex=0;result=result.replace(pattern,'');}});return {value:found?result.trim():value,found};}
 function eligible(input){return input.matches('textarea,input:not([type]),input[type=text],input[type=search]')&&!input.readOnly&&!excluded.has(input.name)&&!/(password|token|secret)/i.test(input.name)&&!input.matches('[data-brand-lookup],[data-postcode]');}
 function filter(input){if(!eligible(input))return;const result=clean(input.value);if(!result.found)return;
  if(input.form&&input.name){const map=rawByForm.get(input.form)||{};map[input.name]={raw:input.value,clean:result.value};rawByForm.set(input.form,map);}
  input.value=result.value;toast('입력한 비속어를 자동 제외했습니다.');
 }
 document.addEventListener('focusout',event=>{if(event.target instanceof HTMLInputElement||event.target instanceof HTMLTextAreaElement)filter(event.target);});
 document.addEventListener('compositionend',event=>{if(event.target instanceof HTMLInputElement||event.target instanceof HTMLTextAreaElement)filter(event.target);});
 document.addEventListener('submit',event=>{
  const form=event.target;if(!(form instanceof HTMLFormElement))return;
  form.querySelectorAll('input,textarea').forEach(filter);
  const originals={};Object.entries(rawByForm.get(form)||{}).forEach(([key,value])=>{if(form.elements.namedItem(key)?.value===value.clean)originals[key]=value.raw;});
  if(Object.keys(originals).length){let hidden=form.querySelector('[name=__filtered_originals]');if(!hidden){hidden=document.createElement('input');hidden.type='hidden';hidden.name='__filtered_originals';form.append(hidden);}hidden.value=JSON.stringify(originals);}
 },true);
 // Search assistant, completely local to this Django site.
 const widget=document.querySelector('[data-chat-widget]');
 if(widget){
  const panel=widget.querySelector('.chat-panel'),launcher=widget.querySelector('.chat-launcher'),form=widget.querySelector('.chat-form'),input=form.elements.question,log=widget.querySelector('.chat-messages');
  function opened(value){panel.hidden=!value;launcher.setAttribute('aria-expanded',String(value));if(value)input.focus();else launcher.focus();}
  launcher.addEventListener('click',()=>opened(panel.hidden));widget.querySelector('.chat-close').addEventListener('click',()=>opened(false));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden)opened(false);});
  function bubble(message,type){const item=document.createElement('div');item.className='chat-message '+type;item.textContent=message;item.dataset.noTranslate='';log.append(item);log.scrollTop=log.scrollHeight;return item;}
  form.addEventListener('submit',async event=>{
   event.preventDefault();const value=input.value.trim();if(!value||form.dataset.busy)return;
   form.dataset.busy='1';const button=form.querySelector('button');button.disabled=true;bubble(value,'user');input.value='';const reply=bubble(t('사이트 정보를 찾고 있어요…'),'bot');
   const body=new FormData();body.append('csrfmiddlewaretoken',csrf());body.append('question',value);body.append('language',document.body.dataset.language||'ko');body.append('path',location.pathname);
   try{const response=await fetch(form.action,{method:'POST',body});const data=await response.json();reply.textContent=data.answer||data.error||t('답변을 불러오지 못했습니다.');
    (data.sources||[]).forEach(source=>{const url=new URL(source.url,location.origin);if(url.origin!==location.origin)return;const link=document.createElement('a');link.className='chat-source';link.href=url.pathname+url.search;link.textContent=source.title+' ↗';reply.append(link);});
   }catch(_){reply.textContent=t('연결하지 못했습니다. 잠시 후 다시 시도해주세요.');}
   finally{delete form.dataset.busy;button.disabled=false;log.scrollTop=log.scrollHeight;input.focus();}
  });
  widget.querySelectorAll('.chat-suggestions button').forEach(button=>button.addEventListener('click',()=>{input.value=button.textContent;form.requestSubmit();}));
 }
})();

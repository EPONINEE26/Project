// Normal forms still work with JavaScript off.
document.addEventListener('change', function(event) {
 const form = event.target.closest('#filter-form, .year-form');
 if(form && event.target.matches('select, input[type="radio"]')) form.requestSubmit();
});
(() => {
 const menu=document.querySelector('[data-account-menu]'); if(!menu) return;
 const button=menu.querySelector('.menu-trigger'), panel=menu.querySelector('.account-panel');
 let timer;
 function open(value){ clearTimeout(timer);menu.classList.toggle('is-open',value);button.setAttribute('aria-expanded',String(value));panel.inert=!value; }
 menu.addEventListener('mouseenter',()=>{if(matchMedia('(hover:hover)').matches) open(true);});
 menu.addEventListener('mouseleave',()=>{timer=setTimeout(()=>{if(!menu.contains(document.activeElement)) open(false);},150);});
 button.addEventListener('click',()=>open(matchMedia('(hover:hover)').matches || button.getAttribute('aria-expanded')!=='true'));
 menu.addEventListener('focusout',()=>{setTimeout(()=>{if(!menu.contains(document.activeElement))open(false);},0);});
 document.addEventListener('pointerdown',event=>{if(!menu.contains(event.target))open(false);});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu.classList.contains('is-open')){open(false);button.focus();}});
})();

// Preserve the viewport only for same-page form updates (filters, sorting,
// reference values, calculator submissions, compare/save toggles).
// Normal links to another page keep their usual navigation behavior.
(() => {
 const key = 'tantan-scroll:' + location.pathname;
 document.addEventListener('click', event => {
  const link = event.target.closest('a[href]');
  if(!link || event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.closest('.logo,.gnb')) return;
  const target = new URL(link.href, location.href);
  if(target.origin!==location.origin || target.pathname!==location.pathname || target.hash) return;
  try {sessionStorage.setItem(key, JSON.stringify({x:scrollX,y:scrollY,at:Date.now()}));} catch (_) {}
 });
 document.addEventListener('submit', event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  const next = form.method.toLowerCase() === 'post' ? form.elements.namedItem('next') : null;
  const target = new URL(next && next.value ? next.value : (form.getAttribute('action') || location.href), location.href);
  if (target.origin !== location.origin || target.pathname !== location.pathname) return;
  try { sessionStorage.setItem(key, JSON.stringify({x:scrollX,y:scrollY,at:Date.now()})); } catch (_) {}
 }, true);
 let saved;
 try { saved=JSON.parse(sessionStorage.getItem(key));sessionStorage.removeItem(key); } catch (_) { return; }
 if (!saved || !Number.isFinite(saved.y) || !Number.isFinite(saved.x) || !Number.isFinite(saved.at) || Date.now()-saved.at>120000) return;
 const restore = () => {
  // If filtering reduces the page height, retain enough room for the old viewport.
  if(document.documentElement.scrollHeight < saved.y + innerHeight) document.body.style.minHeight=(saved.y+innerHeight)+'px';
  const oldBehavior=document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior='auto';
  window.scrollTo({left:saved.x,top:saved.y,behavior:'instant'});
  document.documentElement.style.scrollBehavior=oldBehavior;
 };
 requestAnimationFrame(()=>requestAnimationFrame(restore));
 if(document.readyState!=='complete') window.addEventListener('load',restore,{once:true});
})();

/* Small, progressive motion accents. No library or external service required. */
(() => {
 const reduce=matchMedia('(prefers-reduced-motion:reduce)');
 const fine=matchMedia('(hover:hover) and (pointer:fine)');
 const running=new Set();
 function animate(node,frames,options={}){
  if(reduce.matches||!node?.animate)return;
  const animation=node.animate(frames,{duration:550,easing:'cubic-bezier(.22,1,.36,1)',...options});
  running.add(animation);animation.finished.catch(()=>{}).finally(()=>running.delete(animation));return animation;
 }
 function reveal(node,delay=0){
  animate(node,[{opacity:0,transform:'translateY(18px)'},{opacity:1,transform:'translateY(0)'}],{delay,fill:'backwards'});
 }
 const hero=document.querySelector('.hero');
 if(hero){
  const light=document.createElement('div');light.className='hero-light';light.setAttribute('aria-hidden','true');hero.prepend(light);
  hero.querySelectorAll('.hero-copy > *').forEach((node,i)=>reveal(node,90*i));
  animate(light,[{opacity:0,transform:'translateX(-6%) scale(.96)'},{opacity:1,transform:'translateX(0) scale(1)'}],{duration:1100});
  let frame=0;
  hero.addEventListener('pointermove',event=>{
   if(reduce.matches||!fine.matches)return;
   const box=hero.getBoundingClientRect(),x=(event.clientX-box.left)/box.width,y=(event.clientY-box.top)/box.height;
   cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{light.style.transform=`translate(${(x-.5)*16}px,${(y-.5)*10}px)`;});
  },{passive:true});
  hero.addEventListener('pointerleave',()=>{cancelAnimationFrame(frame);light.style.transform='';});
 }
 document.querySelectorAll('.page-header h1,.page-header > .eyebrow,.page-header > p').forEach((node,i)=>reveal(node,Math.min(i,3)*60));
 if('IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
   entries.filter(entry=>entry.isIntersecting).forEach((entry,i)=>{reveal(entry.target,Math.min(i,3)*65);observer.unobserve(entry.target);});
  },{threshold:.08});
  document.querySelectorAll('.brand-card,.post-card,.listing-card,.community-hero,.help-hero,.insight-card').forEach(node=>observer.observe(node));
 }
 document.addEventListener('pointerdown',event=>{
  const button=event.target.closest('.button,.chat-launcher');
  if(!button||button.hasAttribute('data-no-motion')||button.disabled||reduce.matches||event.button!==0)return;
  const box=button.getBoundingClientRect(),ripple=document.createElement('span'),size=Math.max(box.width,box.height)*1.5;
  ripple.className='button-ripple';ripple.setAttribute('aria-hidden','true');
  Object.assign(ripple.style,{width:size+'px',height:size+'px',left:event.clientX-box.left-size/2+'px',top:event.clientY-box.top-size/2+'px'});button.append(ripple);
  const action=animate(ripple,[{transform:'scale(0)',opacity:.5},{transform:'scale(1)',opacity:0}],{duration:550,easing:'ease-out'});
  if(action)action.finished.catch(()=>{}).finally(()=>ripple.remove());else ripple.remove();
 });
 const panel=document.querySelector('.chat-panel');
 if(panel)new MutationObserver(()=>{if(!panel.hidden)animate(panel,[{opacity:0,transform:'translateY(12px) scale(.97)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:300});}).observe(panel,{attributes:true,attributeFilter:['hidden']});
 reveal(document.querySelector('.chat-launcher'),240);
 const header=document.querySelector('.header');let scheduled=false;
 function updateHeader(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{header?.classList.toggle('is-scrolled',scrollY>16);scheduled=false;});}
 window.addEventListener('scroll',updateHeader,{passive:true});updateHeader();
 reduce.addEventListener('change',()=>{if(reduce.matches){running.forEach(animation=>animation.cancel());const light=document.querySelector('.hero-light');if(light)light.style.transform='';}});
})();

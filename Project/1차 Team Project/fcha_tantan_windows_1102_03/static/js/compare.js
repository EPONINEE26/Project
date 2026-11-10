(() => {
 const dataNode=document.getElementById('comparison-data'); if(!dataNode) return;
 const data=JSON.parse(dataNode.textContent), host=document.getElementById('comparison-charts');
 const choices=[...document.querySelectorAll('input[name="metric"]')], feedback=document.getElementById('metric-feedback');
 function el(tag, cls, text){const node=document.createElement(tag); if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
 const t=value=>window.TT?window.TT(value):value;
 const palette=['#2777d4','#299c91','#8e67c7','#d68b3b','#ce6877','#506db8','#57875b','#b679a2','#668b9d','#8b715c'];
 const scroll=document.querySelector('.multi-compare-scroll');
 document.querySelectorAll('[data-compare-scroll]').forEach(button=>button.addEventListener('click',()=>scroll.scrollBy({left:Number(button.dataset.compareScroll)*Math.max(220,scroll.clientWidth-180),behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth'})));
 const format=n=>new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(n);
 function draw(){
  host.replaceChildren();
  const selected=choices.filter(c=>c.checked);
  if(!selected.length){host.append(el('p','data-note','표에서 비교할 항목을 최대 5개 선택하세요.'));return;}
  selected.forEach(c=>{
   const m=data.metrics.find(m=>m.id===c.value), card=el('section','comparison-chart');
   card.append(el('h3','',m.label),el('p','chart-scale','단위: '+m.unit));
   const max=Math.max(0,...m.values.filter(v=>typeof v==='number'));
   m.values.forEach((value,i)=>{
    const row=el('div','chart-series series-'+i), name=el('div','series-label');
    const brandLabel=el('span','',data.brands[i]);brandLabel.dataset.noTranslate='';name.append(brandLabel,el('strong','',value===null?'미제공':format(value)));
    const track=el('div','series-track'),bar=el('div','series-fill');
    bar.style.background=palette[i%palette.length];
    bar.style.width=(value===null||max===0?0:value/max*100)+'%';track.append(bar);row.append(name,track);card.append(row);
   });
   card.append(el('p','chart-scale','눈금: 0 — '+format(max)+' '+m.unit));host.append(card);
  });
 }
 choices.forEach(c=>c.addEventListener('change',()=>{
  if(choices.filter(x=>x.checked).length>5){c.checked=false;feedback.textContent='그래프 항목은 최대 5개입니다. 선택한 항목 하나를 먼저 해제해주세요.';return;}
  feedback.textContent='';draw();
 }));draw();
})();

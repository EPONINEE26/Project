(() => {
 const dataNode=document.getElementById('comparison-data'); if(!dataNode) return;
 const data=JSON.parse(dataNode.textContent), host=document.getElementById('comparison-charts');
 const choices=[...document.querySelectorAll('input[name="metric"]')], feedback=document.getElementById('metric-feedback');
 function el(tag, cls, text){const node=document.createElement(tag); if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
 const format=n=>new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(n);
 function draw(){
  host.replaceChildren();
  const selected=choices.filter(c=>c.checked);
  if(!selected.length){host.append(el('p','data-note','표에서 비교할 항목을 최대 2개 선택하세요.'));return;}
  selected.forEach(c=>{
   const m=data.metrics.find(m=>m.id===c.value), card=el('section','comparison-chart');
   card.append(el('h3','',m.label),el('p','chart-scale','단위: '+m.unit));
   const max=Math.max(0,...m.values.filter(v=>typeof v==='number'));
   m.values.forEach((value,i)=>{
    const row=el('div','chart-series series-'+i), name=el('div','series-label');
    name.append(el('span','',data.brands[i]),el('strong','',value===null?'미제공':format(value)));
    const track=el('div','series-track'),bar=el('div','series-fill');
    bar.style.width=(value===null||max===0?0:value/max*100)+'%';track.append(bar);row.append(name,track);card.append(row);
   });
   card.append(el('p','chart-scale','눈금: 0 — '+format(max)+' '+m.unit));host.append(card);
  });
 }
 choices.forEach(c=>c.addEventListener('change',()=>{
  if(choices.filter(x=>x.checked).length>2){c.checked=false;feedback.textContent='그래프 항목은 최대 2개입니다. 선택한 항목 하나를 먼저 해제해주세요.';return;}
  feedback.textContent='';draw();
 }));draw();
})();

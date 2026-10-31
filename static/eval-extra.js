document.getElementById('runEval').onclick=async()=>{
  const out=document.getElementById('evalResult');
  out.textContent='Running frozen cases…';
  const cases=[];
  try{
    await runEval();
    const base=out.innerHTML;
    const asOf=await api('/api/execute',{recipe_id:'history-as-of-order',params:{as_of:'2026-02-01T10:30:00'}});
    cases.push(['Temporal join excludes future history',JSON.stringify(asOf.rows)===JSON.stringify([['o1','paid','open','2026-02-01T10:00:00'],['o2','paid',null,null],['o3','open',null,null]])]);
    const unknown=await api('/api/retrieve',{question:'tell me something interesting'});
    cases.push(['Unsupported intent asks for clarification',unknown.status==='clarification_required']);
    const markup=cases.map(([label,ok])=>'<div class="evalcase"><span>'+esc(label)+'</span><span class="'+(ok?'pass':'error')+'">'+(ok?'PASS':'FAIL')+'</span></div>').join('');
    out.innerHTML=base+markup+'<p class="muted">Additional temporal and retrieval checks. Synthetic fixture only.</p>';
  }catch(e){out.textContent='Evaluation stopped: '+e.message;}
};

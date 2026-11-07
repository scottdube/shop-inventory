"""The /receive page: camera-first, text under it, three outcomes, one card.
One file, one string, same as PAGE in app.py. Every state carries a glyph."""

RECEIVE_PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>receive</title>
<style>
body{background:#111;color:#eee;font:17px system-ui;margin:0;padding:12px 12px 80px}
h1{font-size:20px;margin:4px 0 10px}
.row{display:flex;gap:8px;align-items:center;margin:8px 0}
input[type=text],input[type=number]{font:inherit;padding:10px;border-radius:8px;border:1px solid #444;background:#1b1b1b;color:#eee;width:100%}
input[type=number]{width:70px;text-align:right}
button{font:inherit;padding:12px 16px;border-radius:10px;border:0;background:#2b6cb0;color:#fff}
button.big{width:100%;font-size:20px;padding:16px;background:#2f855a}
button.chip{background:#333;padding:8px 12px;font-size:15px}
button.chip.on{background:#2b6cb0}
button.warn{background:#b7791f}
.card{background:#1b1b1b;border:1px solid #333;border-radius:12px;padding:12px;margin:10px 0}
.card.pick{cursor:pointer}
.line{border-top:1px solid #2a2a2a;padding:8px 0}
.muted{color:#999;font-size:14px}
.ok{color:#9ae6b4}.bad{color:#feb2b2}.warnc{color:#fbd38d}
img.thumb{width:56px;height:56px;object-fit:cover;border-radius:8px;background:#222}
#msg{min-height:24px}
.tabs{display:flex;gap:8px}.tabs button{flex:1;background:#333}.tabs button.on{background:#2b6cb0}
select{font:inherit;padding:8px;border-radius:8px;background:#1b1b1b;color:#eee;border:1px solid #444;max-width:100%}
</style></head><body>
<div class="tabs"><button id="tabR" class="on" onclick="tab('R')">Receive</button><button id="tabP" onclick="tab('P')">Pending <span id="pcount"></span></button></div>
<div id="R">
<h1>Receive a box <span class="muted" id="siteTag"></span></h1>
<div class="row">
 <label class="chip" style="flex:1"><input id="photo" type="file" accept="image/*" capture="environment" onchange="go()" style="width:100%"></label>
</div>
<div class="row"><input id="text" type="text" placeholder="or type / dictate a few words" enterkeyhint="go" onkeydown="if(event.key==='Enter')go()"><button onclick="go()">Go</button></div>
<div class="row"><button class="chip" id="siteLRD" onclick="setSite('LRD')">LRD</button><button class="chip" id="siteSLN" onclick="setSite('SLN')">SLN</button><span class="muted">site</span></div>
<div id="msg" class="muted"></div>
<div id="out"></div>
</div>
<div id="P" style="display:none"><h1>Pending</h1><div id="pend"></div></div>
<script>
const $=id=>document.getElementById(id);
let SITE=null, LAST=null, PLAN=null, RECEIPT=null, UNDO_T=null;
try{SITE=localStorage.getItem('binscan.home')||null}catch(e){}
function setSite(s){SITE=s;try{localStorage.setItem('binscan.home',s)}catch(e){};paintSite()}
function paintSite(){['LRD','SLN'].forEach(s=>$('site'+s).classList.toggle('on',SITE===s));$('siteTag').textContent=SITE?'('+SITE+')':'(site?)'}
paintSite();
function tab(t){$('R').style.display=t==='R'?'':'none';$('P').style.display=t==='P'?'':'none';$('tabR').classList.toggle('on',t==='R');$('tabP').classList.toggle('on',t==='P');if(t==='P')loadPending()}
function msg(t,cls){$('msg').innerHTML='<span class="'+(cls||'muted')+'">'+t+'</span>'}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function jpost(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let d={};try{d=await r.json()}catch(e){d={error:'HTTP '+r.status+' (not JSON)'}};if(!r.ok)throw new Error(d.error||d.detail||('HTTP '+r.status));return d}
async function go(){
  const fd=new FormData();fd.append('text',$('text').value);fd.append('site',SITE||'');
  const f=$('photo').files[0];if(f)fd.append('photo',f);
  if(!f&&!$('text').value.trim()){msg('[??] shoot the label or type a few words');return}
  msg('[..] reading…');$('out').innerHTML='';
  let d;try{const r=await fetch('/api/receive/match',{method:'POST',body:fd});d=await r.json();if(!r.ok)throw new Error(d.error||r.status)}catch(e){msg('[XX] '+esc(e.message),'bad');return}
  LAST=d;$('photo').value='';
  if(d.site&&!SITE)setSite(d.site);
  if(d.label_error)msg('[!!] label not read ('+esc(d.label_error)+') - matched on the text only','warnc');
  else if(d.label)msg('[OK] read: '+esc([...d.label.orders,...d.label.skus,...d.label.words].join(' · ').slice(0,120)));
  else msg('[OK] matched on text');
  if(d.verdict==='one'){openCard(d.results[0].card,d.results[0]);return}
  if(d.verdict==='several'){$('out').innerHTML='<div class="muted">[??] which one is in your hand?</div>'+d.results.map(cardHtml).join('');return}
  const o=await fetch('/api/receive/open?site='+(SITE||''));const od=await o.json();
  $('out').innerHTML='<div class="muted">[??] no match - every open order'+(SITE?' at '+SITE:'')+', newest first</div>'+(od.orders||[]).map(c=>cardHtml({card:c,decisive:[],shared:[]})).join('')+
   '<button class="chip" onclick="location.href=\'/\'">no PO for this - file it by hand</button>';
  if(d.results&&d.results.length)fetch('/api/receive/unsettled',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:d.text,results:d.results.map(r=>({reference:r.reference,po:r.po,score:r.score}))})});
}
function cardHtml(r){const c=r.card;const tail=(c.supplier_reference||'').slice(-7);const why=(r.decisive&&r.decisive.length)?'[OK] '+r.decisive.join(', '):(r.shared&&r.shared.length?'matches on '+r.shared.join(', '):'');
  const img=(c.lines[0]&&c.lines[0].image)?'<img class="thumb" src="'+esc(c.lines[0].image)+'">':'<div class="thumb"></div>';
  const flag=c.closed?'<div class="warnc">[!!] already '+(c.status===60?'RETURNED':'received')+' - a second delivery?</div>':'';
  return '<div class="card pick" onclick=\'openCard('+JSON.stringify(c).replace(/'/g,'&#39;')+')\'><div class="row">'+img+'<div><b>'+esc(c.reference)+'</b> · '+esc(c.issue_date)+' · …'+esc(tail)+' · '+esc(c.supplier)+' · '+esc(c.site||'site?')+'<div class="muted">'+c.lines.map(l=>esc(l.name)+' ×'+l.quantity).join('<br>')+'</div><div class="muted">'+esc(why)+'</div></div></div>'+flag+'</div>'}
async function openCard(c){
  if(c.closed){$('out').innerHTML='<div class="card"><div class="warnc">[!!] '+esc(c.reference)+' is already '+(c.status===60?'RETURNED':'received')+'.</div><div class="muted">A second box for a closed order. Nothing to receive here; keep the box and the order link: <a href="'+esc(c.url)+'">'+esc(c.reference)+'</a></div></div>';return}
  let p;try{p=await jpost('/api/receive/plan',{po:c.po,site:SITE})}catch(e){msg('[XX] '+esc(e.message),'bad');return}
  PLAN=p;renderPlan()}
function renderPlan(){const p=PLAN;const other=p.site&&SITE&&p.site!==SITE?'<div class="warnc">[!!] this order ships to '+esc(p.site)+', you are at '+esc(SITE)+' - boxes do travel; carry on if it is in your hand</div>':'';
  let h='<div class="card"><b>'+esc(p.reference)+'</b> <span class="muted">'+esc(p.when)+'</span>'+other;
  if(p.warnings.length)h+='<div class="bad">[XX] '+p.warnings.map(esc).join('<br>')+'<br><span class="muted">fix the supplier part first; receiving now would book the pack price per piece</span></div>';
  p.lines.forEach((l,i)=>{h+='<div class="line"><div>'+esc(l.name)+' <span class="muted">'+esc(l.sku)+'</span></div><div class="row"><input type="number" min="0" step="any" value="'+l.packs+'" onchange="setPacks('+i+',this.value)"> <span class="muted">of '+l.outstanding+' packs × '+l.pack+' = <b>'+(l.packs*l.pack)+'</b> pieces @ $'+l.unit+'</span></div>'+
    '<div class="row"><span class="muted">to</span> <b>'+esc(l.dest.path)+'</b> <span class="muted">('+esc(l.dest.source)+(l.merge_into?', merges into '+l.before:', new row')+')</span></div>'+
    '<div class="row"><button class="chip" onclick="toReceiving('+i+')">Receiving</button><button class="chip" onclick="pick('+i+')">choose…</button><span id="pick'+i+'"></span></div></div>'});
  h+=p.lines.length?'<button class="big" '+(p.warnings.length?'disabled':'')+' onclick="commit()">All here</button>':'<div class="muted">[OK] nothing outstanding on this order</div>';
  h+='</div>';$('out').innerHTML=h}
async function replan(){const lines={};PLAN.lines.forEach(l=>{lines[l.line]={packs:l.packs,dest:l.dest.pk}});try{PLAN=await jpost('/api/receive/plan',{po:PLAN.po,lines:lines,site:SITE})}catch(e){msg('[XX] '+esc(e.message),'bad')};renderPlan()}
function setPacks(i,v){PLAN.lines[i].packs=parseFloat(v)||0;replan()}
function toReceiving(i){PLAN.lines[i].dest={pk:(PLAN.site||SITE)==='SLN'?472:473,path:'Receiving',source:'chosen'};replan()}
async function pick(i){const r=await fetch('/api/drawers');const g=await r.json();let s='<select onchange="PLAN.lines['+i+'].dest={pk:parseInt(this.value),path:this.selectedOptions[0].text,source:\'chosen\'};replan()"><option>pick a drawer…</option>';g.forEach(grp=>{s+='<optgroup label="'+esc(grp.group)+'">'+grp.items.map(it=>'<option value="'+it.pk+'">'+esc(grp.group+'/'+it.name)+'</option>').join('')+'</optgroup>'});$('pick'+i).innerHTML=s+'</select>'}
async function commit(){const keep=PLAN.lines.filter(l=>l.packs>0);if(!keep.length){msg('[??] every line is 0 - nothing to book');return}
  msg('[..] booking…');let rc;try{rc=await jpost('/api/receive/commit',{plan:Object.assign({},PLAN,{lines:keep})})}catch(e){msg('[XX] '+esc(e.message)+' - nothing booked','bad');return}
  RECEIPT=rc;msg('[OK] booked','ok');
  let h='<div class="card"><b>'+esc(rc.reference)+'</b> → '+(rc.status===30?'<span class="ok">[OK] CLOSED</span>':'<span class="warnc">[!!] still open - lines outstanding</span>');
  rc.lines.forEach(l=>{h+='<div class="line">'+l.pieces+' pieces @ $'+l.unit+' → '+esc(l.dest_path)+' <a href="'+esc(l.url)+'">stock '+l.stock+'</a> '+(l.created?'(new row)':'(merged, was '+l.before_qty+')')+'</div>'});
  h+='<div class="row"><button class="warn" id="undoBtn" onclick="undo()">Undo</button><span class="muted" id="undoLeft"></span></div><div class="row"><button class="chip" onclick="goingBack()">going back (return requested)</button></div></div>';
  $('out').innerHTML=h;const until=new Date(rc.undo_until).getTime();clearInterval(UNDO_T);UNDO_T=setInterval(()=>{const s=Math.floor((until-Date.now())/1000);if(s<=0){clearInterval(UNDO_T);$('undoBtn').disabled=true;$('undoLeft').textContent='undo window closed - use binscan_undo.py';return}$('undoLeft').textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')+' left'},1000)}
async function undo(){msg('[..] undoing…');try{const u=await jpost('/api/receive/undo',{receipt:RECEIPT});msg('[OK] undone - '+esc(u.reference)+' back to status '+u.status,'ok');$('out').innerHTML=''}catch(e){msg('[XX] '+esc(e.message),'bad')}}
async function goingBack(){const c=RECEIPT;if(!c)return;msg('[..] marking going back…');try{const d=await jpost('/api/receive/going-back',{po:c.po});msg('[OK] '+esc(d.action)+' - '+esc(d.reference),'ok')}catch(e){msg('[XX] '+esc(e.message),'bad')}}
async function loadPending(){const r=await fetch('/api/receive/pending?site='+(SITE||''));const d=await r.json();$('pcount').textContent=d.items.length?'('+d.items.length+')':'';
  $('pend').innerHTML=d.items.length?d.items.map(it=>{if(it.kind==='overdue')return '<div class="card"><div class="warnc">[!!] '+esc(it.reference)+' is '+it.days+' days past its date - did it arrive?</div>'+cardHtml({card:it.card,decisive:[],shared:[]})+'</div>';
    if(it.kind==='decision')return '<div class="card"><div class="warnc">[??] '+esc(it.reference)+'</div><div>'+esc(it.question)+'</div><div class="muted"><a href="'+esc(it.url)+'">open the order</a> and answer in its note; the morning task reads it</div></div>';
    return '<div class="card"><div class="muted">[??] unsettled '+esc(it.at)+': "'+esc(it.text)+'"</div><div>'+(it.results||[]).map(r=>esc(r.reference)).join(', ')+'</div><button class="chip" onclick="$(\'text\').value='+JSON.stringify(it.text||'')+';tab(\'R\');go()">try again</button></div>'}).join(''):'<div class="muted">[OK] nothing pending</div>';
  if(d.error)$('pend').innerHTML+='<div class="bad">[XX] '+esc(d.error)+'</div>'}
loadPending();
</script></body></html>"""

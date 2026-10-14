let prepareChallenge=null,preparePending=false,operatorCode=sessionStorage.getItem('supervised-operator')||'';
const checks=()=>Array.from(document.querySelectorAll('#prepare-checks input'));
function prepareEnabled(){ $('prepare-next').disabled=preparePending||!operatorCode||!prepareChallenge?.eligible||!checks().every(c=>c.checked); }
$('pair-operator').addEventListener('click',()=>{operatorCode=$('operator-code').value.trim();sessionStorage.setItem('supervised-operator',operatorCode);$('operator-code').value='';$('pairing-panel').open=false;text('prepare-feedback','연결 코드를 이 탭에 보관했습니다. 승인 시 서버에서 권한을 확인합니다.');prepareEnabled()});
checks().forEach(c=>c.addEventListener('change',prepareEnabled));
$('prepare-next').addEventListener('click',async()=>{
 if($('prepare-next').disabled)return;
 preparePending=true;prepareEnabled();
 const body={challenge_id:prepareChallenge.id,confirmations:checks().map(c=>c.value)};
 try{const r=await fetch('/api/v1/line/supervised/prepare',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+operatorCode},body:JSON.stringify(body),signal:AbortSignal.timeout(4500)});
  if(!r.ok)throw Error(r.status===403?'운영자 연결 코드를 확인하세요.':'현재 준비 조건이 바뀌었습니다. 상태를 다시 확인하세요.');
  text('prepare-feedback','승인 요청을 접수했습니다. 상단에 「검사 준비됨」이 표시될 때까지 START를 누르지 마세요.');
 }catch(e){text('prepare-feedback','승인 여부 확인 필요: '+e.message+' 자동 재전송하지 않습니다.');}
 finally{checks().forEach(c=>c.checked=false);preparePending=false;prepareChallenge=null;prepareEnabled();}
});
function renderSupervised(s,live){
 $('supervised-panel').hidden=!s;
 if(!s){$('prepare-link').hidden=true;prepareChallenge=null;prepareEnabled();return}
 $('prepare-link').hidden=false;$('pairing-panel').open=!operatorCode;const next=s.challenge;
 if(!live||!next?.eligible||next.id!==prepareChallenge?.id)checks().forEach(c=>c.checked=false);
 prepareChallenge=live?next:null;
 text('trial-number','이번 실행 승인 '+s.prepared_count+'회');
 text('prepare-status',next?.eligible?'다음 제품 준비: 아래 다섯 항목을 직접 확인하세요.':(s.reason||next?.reason||'준비 조건 확인 중'));
 prepareEnabled();
 $('evidence-panel').open=true;
}

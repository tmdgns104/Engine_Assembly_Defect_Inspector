"""Local, explicit commissioning approval. No PLC write or motor command."""
import argparse
import json
from pathlib import Path
import time
import uuid
from src.runtime.initial_approval import atomic_json, POLICY

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    for name in ('physical-stop','supervised','no-unfinished-product','real-ai-output'):
        p.add_argument('--confirm-'+name,action='store_true',required=True)
    a=p.parse_args()
    info=(a.directory/'challenge.json')
    c=json.loads(info.read_text(encoding='utf-8'))
    now=time.monotonic()
    if not c['eligible'] or c['policy']!=POLICY or not 0<=now-c['generated']<=2:
        raise SystemExit('현재 Runtime의 정지·준비 확인이 유효하지 않습니다. 승인하지 않았습니다.')
    request=a.directory/'request.json'
    if request.exists(): raise SystemExit('기존 승인 요청 처리 중입니다.')
    identifier=uuid.uuid4().hex
    atomic_json(request,dict(approval_id=identifier,policy=POLICY,binding=c['binding'],
        created=now,confirmations=['PHYSICAL_STOP','SUPERVISED','NO_UNFINISHED_PRODUCT','REAL_AI_OUTPUT']))
    print('승인 요청 제출: '+identifier+' (접수 여부는 Runtime 상태에서 확인)')

if __name__=='__main__': main()

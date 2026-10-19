"""Package small inspectable evidence; omit raw archives, full crops and weights."""
import ast
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from verify_artifacts import OUTPUT, BASELINE, PROJECT, PARTS, load, sha


def main():
    browser_bytes = (PROJECT/'output/playwright/recovery-browser-result.txt').read_bytes()
    # PowerShell redirects native output as UTF-16; inspect BOM before decoding.
    browser_text = browser_bytes.decode('utf-16' if browser_bytes.startswith(b'\xff\xfe') else 'utf-8-sig').replace('\r\n', '\n')
    encoded = browser_text.split('### Result\n', 1)[1].split('\n###', 1)[0].strip()
    browser = json.loads(json.loads(encoded))
    assert browser['status'] == 'PASS'
    (OUTPUT/'browser_verification.json').write_text(json.dumps(browser, ensure_ascii=False, indent=2), encoding='utf-8')
    evidence = OUTPUT/'browser_evidence'; evidence.mkdir(exist_ok=True)
    for source in (PROJECT/'output/playwright').glob('recovery-*.png'):
        shutil.copyfile(source, evidence/source.name)
    tests = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'notebook/training/engine_recovery', '-p', 'test_recovery.py', '-v'],
                           cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
    assert tests.returncode == 0, tests.stderr
    (OUTPUT/'unit_tests.log').write_text(tests.stdout+tests.stderr, encoding='utf-8')
    source_root = PROJECT/'notebook/training/engine_recovery'
    snapshot = OUTPUT/'source_snapshot'; snapshot.mkdir(exist_ok=True)
    source_hashes = {}
    for path in source_root.iterdir():
        if path.suffix not in ('.py', '.html', '.js'): continue
        if path.suffix == '.py': ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        shutil.copyfile(path, snapshot/path.name); source_hashes[str(path)] = sha(path)
    import cv2
    import torch
    import torchvision
    import ultralytics
    identity = dict(recorded_at=datetime.now(timezone.utc).isoformat(), executable=sys.executable,
                    python=sys.version, torch=torch.__version__, torchvision=torchvision.__version__,
                    ultralytics=ultralytics.__version__, opencv=cv2.__version__,
                    cuda_available=torch.cuda.is_available(), cuda=torch.version.cuda,
                    gpu=torch.cuda.get_device_name(0), source_hashes=source_hashes,
                    models={p: dict(path=str(BASELINE/'full'/p/'weights/best.pt'), sha256=sha(BASELINE/'full'/p/'weights/best.pt')) for p in PARTS},
                    config_sha256=sha(OUTPUT/'alignment/config_frozen.json'),
                    train_bank_sha256=sha(OUTPUT/'alignment/train_body_bank.npz'),
                    retraining=False, human_reviewed=False)
    (OUTPUT/'execution_identity.json').write_text(json.dumps(identity, indent=2), encoding='utf-8')
    package = OUTPUT/'review_package'; package.mkdir(exist_ok=True)
    for path in OUTPUT.iterdir():
        if path.suffix in ('.md', '.json', '.jsonl') and path.name != 'delivery_verification.json':
            shutil.copyfile(path, package/path.name)
    settings = package/'alignment'; settings.mkdir(exist_ok=True)
    for path in (OUTPUT/'alignment').glob('*.json'): shutil.copyfile(path, settings/path.name)
    shutil.copytree(snapshot, package/'source_snapshot', dirs_exist_ok=True)
    text = (OUTPUT/'visual_report_v001/REPORT.html').read_text(encoding='utf-8')
    data = json.loads(re.search(r'<script id="recovery-data" type="application/json">(.*?)</script>', text, re.S)[1])
    images = package/'representatives'; images.mkdir(exist_ok=True)
    cards = []
    for case in data['cases']:
        if case['id'] not in ['V0025', 'V0089', 'V0118', 'V0013', 'V0139']: continue
        def picture(link, title):
            source = (OUTPUT/'visual_report_v001'/link).resolve()
            name = case['id']+'_'+str(len(list(images.iterdir())))+'_'+source.name
            shutil.copyfile(source, images/name)
            return '<figure><figcaption>'+html.escape(title)+'</figcaption><img src="representatives/'+name+'"></figure>'
        panels = picture(case['original'], '원본 축소 미리보기')
        for phase, label in [('before', '수정 전'), ('after', '수정 후')]:
            panels += picture(case[phase]['overlay'], label+' 정렬 · '+case[phase]['status'])
        crops = ''
        for part in PARTS:
            for phase, label in [('before', '전'), ('after', '후')]:
                row = case[phase]['parts'][part]
                title = f"{part} {label} | 정답 {row['truth']} / 예측 {row['prediction'] or '없음'} | "+('실제 입력' if row['crop'] else '진단용·입력 아님')
                crops += picture(row['crop'] or row['diagnostic'], title)
        cards.append(f"<section><h2>{case['id']} · {case['before']['status']} → {case['after']['status']}</h2><div class='photos'>{panels}</div><div class='crops'>{crops}</div></section>")
    standalone = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>전처리 회복 대표 비교</title><style>body{font:16px system-ui;background:#f3f6fa;color:#183148;margin:24px}section{background:white;padding:20px;margin:24px 0;border-radius:12px}.photos,.crops{display:grid;gap:12px}.photos{grid-template-columns:repeat(3,1fr)}.crops{grid-template-columns:repeat(4,1fr)}figure{margin:0}img{width:100%;height:auto}figcaption{min-height:45px;font-size:13px}@media(max-width:700px){.photos,.crops{grid-template-columns:1fr 1fr}}</style><h1>전처리 회복 · 대표 5사례</h1><p>155장 중110→151장 처리, 보류4장 유지. 기존 모델 고정, 재학습 없음. 같은 엔진의 Codex 검토 라벨을 사용한 개발 회귀검증입니다. 전체155장 탐색 HTML은 로컬 run의 visual_report_v001/REPORT.html에 있습니다.</p>'+''.join(cards)+'</html>'
    (package/'REPRESENTATIVES.html').write_text(standalone, encoding='utf-8')
    archive = OUTPUT/'RECOVERY_REVIEW_PACKAGE.zip'
    assert not archive.exists(), 'Preserve delivered package'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package.rglob('*')):
            if path.is_file(): z.write(path, path.relative_to(package).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for entry in z.infolist():
            assert not entry.filename.endswith('.pt') and not entry.filename.startswith('crops/')
            assert z.read(entry.filename) == (package/entry.filename).read_bytes()
        members = len(z.infolist())
    report_check = load(OUTPUT/'visual_report_v001/report_generation_verification.json')
    report_check['browser_verification'] = 'PASS'
    (OUTPUT/'visual_report_v001/report_generation_verification.json').write_text(json.dumps(report_check, indent=2), encoding='utf-8')
    required = ['RECOVERY_SUMMARY.md', 'RECOVERY_VERIFICATION.md', 'preprocessing_report.json', 'before_after_metrics.json', 'validation_predictions.jsonl', 'artifact_verification.json', 'browser_verification.json', 'execution_identity.json', 'visual_report_v001/REPORT.html', 'RECOVERY_REVIEW_PACKAGE.zip']
    result = dict(status='PASS', browser_checks=len(browser['checks']), unit_tests=4, syntax='PASS',
                  zip_members=members, zip_bytes=archive.stat().st_size, zip_sha256=sha(archive),
                  artifacts={name:dict(bytes=(OUTPUT/name).stat().st_size,sha256=sha(OUTPUT/name)) for name in required})
    (OUTPUT/'delivery_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='artifacts'}))


if __name__ == '__main__': main()

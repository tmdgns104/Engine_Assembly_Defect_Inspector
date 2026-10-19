"""엔진 부품 3종 학습. 원본 ZIP은 읽기만 하고 E04 Test Reserved는 추출하지 않는다.

VS Code에서 기존 engine_training_kit_v001/.venv Python으로 실행한다.
라벨 미리보기를 실제로 검토한 뒤에만 APPROVE 216을 입력한다.
--check-only: 파일/좌표 검사만. --prepare-only: 검토 승인 후 데이터셋만 생성.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import sys
import traceback
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
CLASS_NAMES = ['gray_pipe', 'exhaust_top', 'symbol_module']
ULTRALYTICS_VERSION = '8.3.253'  # 앞서 실제 노트북에서 사용한 버전
SOURCE_SHA256 = 'e2dc231326f2c0969848923a498f9febbeabe063e3638dbe84fcb83b58cbf430'
INDEX_SHA256 = '2b7e63b905be865e2003f72ac3b5b384e2ffb6ecb45f7cc3e5460bf5b43f86f8'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def validate_annotations(data: dict, source_index: dict) -> dict:
    """변경 가능한 박스와, 변경하면 안 되는 원본/분할 정보를 분리해 검사한다."""
    if data.get('class_names') != CLASS_NAMES or source_index.get('class_names') != CLASS_NAMES:
        raise ValueError('class mapping must be gray_pipe / exhaust_top / symbol_module')
    expected = {r['review_id']: r for r in source_index['rows']}
    items = data['items']
    ids = [r['review_id'] for r in items]
    if len(ids) != 216 or len(set(ids)) != 216 or set(ids) != set(expected):
        raise ValueError('exactly the 216 selected development records are required')
    groups = {'train': set(), 'val': set()}
    image_counts, empty_counts, boxes = Counter(), Counter(), 0
    immutable = ['capture_id', 'image_member', 'image_sha256', 'split', 'round_id',
                 'scenario_capture_truth', 'origin_group_id', 'width', 'height']
    for row in items:
        original = expected[row['review_id']]
        for key in immutable:
            if row[key] != original[key]:
                raise ValueError(f"{row['review_id']}: source field changed: {key}")
        if original['test_reserved'] or original['rejected'] or not original['capture_human_accepted']:
            raise ValueError('reserved/rejected/unaccepted source is not permitted')
        if row['split'] not in groups or row['round_id'] not in ('E01', 'E02', 'E03'):
            raise ValueError('only original E01/E02 train and E03 validation are permitted')
        parts = PurePosixPath(row['image_member'])
        if parts.is_absolute() or '..' in parts.parts or '\\' in row['image_member']:
            raise ValueError('unsafe source member')
        groups[row['split']].add(row['origin_group_id'])
        image_counts[row['split']] += 1
        empty_counts[row['split']] += not row['boxes']
        counts = Counter()
        for b in row['boxes']:
            c = b['class_id']
            if type(c) is not int or c not in range(3) or b['class_name'] != CLASS_NAMES[c]:
                raise ValueError('invalid class id/name')
            xy = b['bbox_xyxy']
            if len(xy) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in xy):
                raise ValueError('bbox must contain four finite numbers')
            x1, y1, x2, y2 = xy
            if not (0 <= x1 < x2 <= row['width'] and 0 <= y1 < y2 <= row['height']):
                raise ValueError(f"{row['review_id']}: bbox must have positive area inside image")
            counts[CLASS_NAMES[c]] += 1
        if any(counts[c] != original['expected_counts'][c] for c in CLASS_NAMES):
            raise ValueError(f"{row['review_id']}: labels and declared part counts disagree; review truth, do not guess")
        boxes += len(row['boxes'])
    if groups['train'] & groups['val'] or dict(image_counts) != {'train': 144, 'val': 72}:
        raise ValueError('source split/group separation changed')
    return {'images': dict(image_counts), 'boxes': boxes, 'empty_labels': dict(empty_counts),
            'test_images_used': 0, 'scope': 'STRUCTURAL_CHECK_NOT_VISUAL_LABEL_APPROVAL'}


def yolo_text(row: dict) -> str:
    """원본 픽셀 xyxy를 class + 정규화 xywh로 변환한다. 없는 부품은 행을 만들지 않는다."""
    lines = []
    W, H = row['width'], row['height']
    for b in row['boxes']:
        x1, y1, x2, y2 = b['bbox_xyxy']
        vals = ((x1+x2)/(2*W), (y1+y2)/(2*H), (x2-x1)/W, (y2-y1)/H)
        lines.append(str(b['class_id']) + ' ' + ' '.join(f'{v:.10f}' for v in vals))
    return '\n'.join(lines) + ('\n' if lines else '')


def make_approval(answer: str, annotation_hash: str, count: int) -> dict:
    """정해진 확인 문구 없이는 미리보기의 후보를 학습 정답으로 승격하지 않는다."""
    if answer.strip() != f'APPROVE {count}':
        raise ValueError('라벨 승인 없음: 미리보기를 검토한 뒤 다시 실행하세요. 학습하지 않았습니다.')
    return {'type': 'USER_DECLARED_VISUAL_REVIEW', 'answer': answer.strip(),
            'annotations_sha256': annotation_hash, 'bbox_approval_count': count,
            'count_unit': 'image_label_sets_not_individual_boxes',
            'defect_truth_changed': False, 'approved_at_utc': datetime.now(timezone.utc).isoformat()}


def require_weights(path: Path) -> Path:
    if not path.is_file() or path.suffix.lower() != '.pt' or path.stat().st_size == 0:
        raise FileNotFoundError(f'기존 사전학습 가중치 파일이 필요합니다: {path}')
    return path.resolve()


def prepare_dataset(zip_path: Path, data: dict, source_index: dict, destination: Path) -> Path:
    """검토된 216장만 byte 그대로 복사한다. ZIP 전체 extractall은 사용하지 않는다."""
    validate_annotations(data, source_index)
    if sha256(zip_path) != SOURCE_SHA256:
        raise ValueError('원본 ZIP SHA-256 불일치. 다른 수집본은 별도 검토가 필요합니다.')
    if destination.exists():
        raise FileExistsError('새 출력 폴더만 사용합니다: ' + str(destination))
    destination.mkdir(parents=True)
    for split in ('train', 'val'):
        (destination/'images'/split).mkdir(parents=True)
        (destination/'labels'/split).mkdir(parents=True)
    copied = []
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        for row in data['items']:
            member = row['image_member']
            if names.count(member) != 1:
                raise ValueError('원본 이미지 이름 누락/중복: ' + member)
            content = z.read(member)  # E04는 선택 목록에 없으므로 읽지 않는다.
            if hashlib.sha256(content).hexdigest() != row['image_sha256']:
                raise ValueError('image SHA mismatch: ' + row['review_id'])
            if content[:8] != b'\x89PNG\r\n\x1a\n' or (int.from_bytes(content[16:20],'big'), int.from_bytes(content[20:24],'big')) != (row['width'],row['height']):
                raise ValueError('PNG header shape mismatch')
            alias = row['review_id']
            image_path = destination/'images'/row['split']/(alias+'.png')
            image_path.write_bytes(content)
            (destination/'labels'/row['split']/(alias+'.txt')).write_text(yolo_text(row),encoding='utf-8')
            copied.append({'review_id':alias,'source_member':member,'sha256':row['image_sha256'],'split':row['split']})
    # JSON 문법은 YAML에서도 읽을 수 있지만 읽기 쉬운 YAML로 저장한다.
    yaml_text = 'path: ' + json.dumps(destination.resolve().as_posix()) + '\ntrain: images/train\nval: images/val\nnames:\n'
    yaml_text += ''.join(f'  {i}: {name}\n' for i,name in enumerate(CLASS_NAMES))
    (destination/'data.yaml').write_text(yaml_text,encoding='utf-8')
    write_json(destination/'lineage.json',copied)
    return destination/'data.yaml'


def run_training(args, run_dir: Path, data_yaml: Path, weights: Path) -> None:
    """기존 노트북의 YOLO11n 환경을 재사용한다. 설치나 CPU 자동 전환은 하지 않는다."""
    import torch
    from ultralytics import YOLO
    installed = importlib.metadata.version('ultralytics')
    if installed != ULTRALYTICS_VERSION:
        raise RuntimeError(f'기존 학습 venv를 선택하세요. expected={ULTRALYTICS_VERSION}, actual={installed}')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU를 사용할 수 없습니다. CPU로 자동 변경하지 않았습니다.')
    write_json(run_dir/'environment.json',{'python':sys.version,'torch':torch.__version__,
        'ultralytics':installed,'gpu':torch.cuda.get_device_name(0),'initial_weights':str(weights),
        'initial_weights_sha256':sha256(weights)})
    # baseline 설정이다. 최적 성능이나 실시간 운전 성능을 보장하는 수치가 아니다.
    model = YOLO(str(weights))
    model.train(data=str(data_yaml), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                device=0, workers=0, seed=42, amp=False, patience=20,
                fliplr=0.0, flipud=0.0, degrees=0.0, mosaic=0.0,
                project=str(run_dir/'training'), name='engine_parts', exist_ok=False)
    train_root = Path(model.trainer.save_dir)
    best = train_root/'weights/best.pt'
    last = train_root/'weights/last.pt'
    if not best.is_file() or not last.is_file():
        raise RuntimeError('학습 완료 가중치를 확인할 수 없습니다.')
    (run_dir/'models').mkdir()
    shutil.copy2(best,run_dir/'models/engine_parts_best.pt')
    shutil.copy2(last,run_dir/'models/engine_parts_last.pt')
    model = YOLO(str(best))
    if [model.names[i] for i in range(3)] != CLASS_NAMES or len(model.names) != 3:
        raise RuntimeError('학습한 모델 클래스가 기존 검사 계약과 다릅니다.')
    metrics = model.val(data=str(data_yaml),split='val',device=0,workers=0,imgsz=args.imgsz,
                        project=str(run_dir),name='validation',exist_ok=False)
    write_json(run_dir/'validation_metrics.json',{'split':'E03_DEVELOPMENT_VALIDATION_NOT_FINAL_TEST',
        'metrics': {k:float(v) for k,v in metrics.results_dict.items()}})
    predictions = model.predict(source=str(data_yaml.parent/'images/val'), stream=True,
         imgsz=args.imgsz, device=0,conf=0.25,save=True,project=str(run_dir),name='val_predictions',verbose=False)
    with (run_dir/'val_predictions.jsonl').open('w',encoding='utf-8') as stream:
        for result in predictions:
            boxes=result.boxes
            value={'image':Path(result.path).name,'detections':[
               {'class_id':int(c),'confidence':float(p),'bbox_xyxy':[float(v) for v in b]}
               for b,c,p in zip(boxes.xyxy.cpu().tolist(),boxes.cls.cpu().tolist(),boxes.conf.cpu().tolist())]}
            stream.write(json.dumps(value,ensure_ascii=False)+'\n')
    write_json(run_dir/'model_manifest.json',{'classes':CLASS_NAMES,
        'best_sha256':sha256(run_dir/'models/engine_parts_best.pt'),
        'purpose':'ENGINE_PART_DETECTION_NOT_WHOLE_PRODUCT_TRACKING',
        'train_images':144,'validation_images':72,'final_test_images_used':0,
        'physical_inspection_acceptance':False,'deployed_to_runtime':False})


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip',type=Path)
    parser.add_argument('--weights',type=Path,default=ROOT.parent/'engine_training_kit_v001/models/yolo11n.pt')
    parser.add_argument('--epochs',type=int,default=100)
    parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--batch',type=int,default=8)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if any(v<=0 for v in (args.epochs,args.imgsz,args.batch)):
        parser.error('epochs/imgsz/batch must be positive')
    if sha256(ROOT/'source_index.json') != INDEX_SHA256:
        raise ValueError('source_index.json이 변경됐습니다. Test Reserved 보호를 위해 중단합니다.')
    annotation_path=ROOT/'bbox_candidates.json'
    data=json.loads(annotation_path.read_text(encoding='utf-8'))
    source_index=json.loads((ROOT/'source_index.json').read_text(encoding='utf-8'))
    print(json.dumps(validate_annotations(data,source_index),ensure_ascii=False,indent=2))
    if args.check_only:
        print('파일/좌표 구조 검사만 완료. 시각 라벨 승인/학습은 하지 않았습니다.')
        return 0
    zip_path=args.source_zip or ROOT.parent/'CFA8507BBBF384292.zip'
    if not zip_path.is_file():
        zip_path=Path(input('원본 CFA8507BBBF384292.zip 전체 경로: ').strip().strip('"'))
    if not zip_path.is_file(): raise FileNotFoundError(zip_path)
    weights=None
    if not args.prepare_only:
        if not args.weights.is_file():
            args.weights=Path(input('기존 사전학습 yolo11n.pt 전체 경로: ').strip().strip('"'))
        weights=require_weights(args.weights)
    print('review/의 라벨 216장을 검토했을 때만 APPROVE 216을 입력하세요.')
    print('색: 0 파이프(청록), 1 상단 배기구(주황), 2 문양 모듈(자홍). Test E04 제외.')
    receipt=make_approval(input('검토 확인: '),sha256(annotation_path),216)
    run_dir=ROOT/'outputs'/('run_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    run_dir.mkdir(parents=True,exist_ok=False)
    write_json(run_dir/'approval.json',receipt)
    shutil.copy2(annotation_path,run_dir/'annotations_used.json')
    write_json(run_dir/'status.json',{'state':'PREPARING','training_completed':False})
    try:
        data_yaml=prepare_dataset(zip_path,data,source_index,run_dir/'dataset')
        if args.prepare_only:
            write_json(run_dir/'status.json',{'state':'DATASET_PREPARED','training_completed':False})
            print('학습 데이터만 생성: ',data_yaml)
            return 0
        run_training(args,run_dir,data_yaml,weights)
        write_json(run_dir/'status.json',{'state':'TRAINING_AND_VAL_COMPLETE','training_completed':True,
                    'final_test_performed':False,'runtime_replaced':False})
        # 원본 이미지 복사본/epoch 결과를 제외한 작은 결과 ZIP을 만든다.
        target=run_dir.with_name(run_dir.name+'_return.zip')
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in run_dir.rglob('*'):
                rel=p.relative_to(run_dir)
                if p.is_file() and rel.parts[0] not in ('dataset','training'):
                    z.write(p,arcname=run_dir.name+'/'+rel.as_posix())
        print('결과 ZIP:',target)
        return 0
    except Exception as error:
        write_json(run_dir/'status.json',{'state':'FAILED','training_completed':False,'error':str(error)})
        (run_dir/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        print('오류를 숨기지 않고 종료했습니다. 원본/최종 시험/통합 Runtime은 변경하지 않았습니다.')
        raise SystemExit(1)

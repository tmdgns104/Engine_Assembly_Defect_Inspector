"""Sequential smoke/full local training with independently loaded start weights."""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import platform
import time

import cv2
import numpy as np
from PIL import Image
import torch
import torchvision
import ultralytics
from ultralytics import YOLO
from ultralytics.cfg import get_cfg
from ultralytics.utils.downloads import attempt_download_asset

from classification import FixedDataset,FixedTrainer,FixedValidator,FixedPredictor,base_transform
from preprocess import PARTS,sha,read_image
from process_dataset import dump


def verify_transforms(model,data):
    args=get_cfg(overrides=dict(imgsz=224,cache=False,auto_augment=None,erasing=0.,fliplr=0.,flipud=0.))
    train=FixedDataset(str(data/'train'),args,augment=True,prefix='parity_train')
    val=FixedDataset(str(data/'val'),args,augment=False,prefix='parity_val')
    sample=val.samples[0][0]
    bgr=read_image(sample)
    expected=torch.from_numpy(bgr[:,:,::-1].copy()).permute(2,0,1).float()/255
    # Exercise both dataset __getitem__ and training/validation transform objects.
    val_tensor=val[0]['img']
    train_tensor=train.torch_transforms(Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)))
    assert torch.equal(expected,val_tensor) and torch.equal(expected,train_tensor)
    result=model.predict([bgr],predictor=FixedPredictor,imgsz=224,device=0,quantize=32,verbose=False)[0]
    predicted_tensor=model.predictor.preprocess([bgr]).cpu()[0]
    assert torch.equal(expected,predicted_tensor)
    assert set(train.base.class_to_idx)==set(val.base.class_to_idx)
    assert train.base.class_to_idx==val.base.class_to_idx
    assert {name:int(i) for i,name in model.names.items()}==train.base.class_to_idx
    return dict(status='PASS',sample=sample,shape=list(expected.shape),range=[float(expected.min()),float(expected.max())],
                exact_tensor_equality=True,class_to_idx=train.base.class_to_idx,
                transform=repr(base_transform()),checkpoint_prediction_scores=result.probs.data.cpu().tolist())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--stage',choices=['smoke','full'],required=True);args=parser.parse_args()
    output=Path(args.output).resolve()
    weights=output/'starting_weights/yolo11n-cls.pt';weights.parent.mkdir(exist_ok=True)
    if not weights.exists():attempt_download_asset(str(weights))
    assert weights.exists()
    starting_sha=sha(weights)
    env=dict(python=platform.python_version(),torch=torch.__version__,torchvision=torchvision.__version__,
             ultralytics=ultralytics.__version__,opencv=cv2.__version__,cuda=torch.version.cuda,
             gpu=torch.cuda.get_device_name(0),gpu_bytes=torch.cuda.get_device_properties(0).total_memory,
             initial_weights=str(weights),initial_weights_sha256=starting_sha,
             source='https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n-cls.pt',
             source_note='Actual download URL is preserved in the training log.',label_source='Codex reviewed approved_part_states; human_reviewed=false')
    dump(output/'environment.json',env)
    summary=[]
    parts=PARTS if args.stage=='full' else ('pipe_left',)
    for part in parts:
        assert sha(weights)==starting_sha
        data=output/'crops'/part
        report=json.loads((output/'preprocessing_report.json').read_text(encoding='utf-8'))['by_part'][part]
        required={'CORRECT','MISSING','UPSIDE_DOWN'} if part=='symbol' else {'CORRECT','MISSING','REVERSED','SIDEWAYS'} if part=='exhaust' else {'CORRECT','MISSING','UPWARD_ROTATED','OUTWARD_SPLAYED'}
        if set(report['TRAIN']['classes'])!=required or set(report['VALIDATION']['classes'])!=required:
            summary.append(dict(part=part,status='BLOCKED_MISSING_CLASS'));continue
        dest=output/args.stage/part
        assert not dest.exists(),f'Existing run must not be overwritten: {dest}'
        started=time.monotonic()
        model=YOLO(str(weights))
        settings=dict(data=str(data),imgsz=224,epochs=2 if args.stage=='smoke' else 60,patience=10,batch=16,seed=42,
                      workers=0,device=0,project=str(output/args.stage),name=part,exist_ok=False,
                      auto_augment=None,erasing=0.,fliplr=0.,flipud=0.,degrees=0.,translate=0.,scale=0.,
                      shear=0.,perspective=0.,hsv_h=0.,hsv_s=0.,hsv_v=0.,mixup=0.,cutmix=0.,mosaic=0.,
                      amp=False,quantize=32,optimizer='AdamW',lr0=.001,weight_decay=.0005,
                      deterministic=True,cache=False,plots=False,save=True,verbose=False)
        model.train(trainer=FixedTrainer,**settings)
        best=dest/'weights/best.pt'
        assert best.exists()
        # A fresh model must use the exact same base transform, not defaults.
        reloaded=YOLO(str(best))
        parity=verify_transforms(reloaded,data)
        mapping={str(i):name for i,name in reloaded.names.items()}
        dump(dest/'class_mapping.json',mapping)
        dump(dest/'preprocessing_parity.json',parity)
        record=dict(part=part,status='TRAINED',stage=args.stage,settings=settings,initial_weights_sha256=starting_sha,
                    best_path=str(best),best_sha256=sha(best),class_mapping=mapping,
                    best_criterion='Development VALIDATION macro F1, unweighted across actual classes',
                    elapsed_seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),
                    preprocessing_parity=parity)
        dump(dest/'execution.json',record);summary.append(record)
        dump(output/f'{args.stage}_execution.json',summary)
        print('STAGE_COMPLETE',args.stage,part,record['elapsed_seconds'],flush=True)
        del model,reloaded;gc.collect();torch.cuda.empty_cache()


if __name__=='__main__':main()

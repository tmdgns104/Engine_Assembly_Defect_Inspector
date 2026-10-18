"""Image-only frozen PyTorch replay in temporary staging; never opens camera/PLC."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'notebook/training/engine_recovery'),str(ROOT/'notebook/training/engine_baseline')]
from recovery import RecoveryPreprocessor
from classification import FixedPredictor
from preprocess import read_image,write_image,sha
from policy import PARTS,aggregate_frame
import cv2
import numpy as np
import torch
from ultralytics import YOLO

BASELINE=ROOT/'runs/engine_misassembly_baseline_training_001/v001_20261002T191929Z'
CONFIG=ROOT/'runs/engine_preprocessing_recovery_001/v001_20261003T033452Z/alignment/config_frozen.json'


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def sync():torch.cuda.synchronize()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    assert torch.cuda.is_available(),'CUDA_REQUIRED_NO_CPU_PARITY_SUBSTITUTION'
    inputs=[json.loads(s) for s in args.inputs.read_text(encoding='utf-8').splitlines() if s]
    started=time.perf_counter();processor=RecoveryPreprocessor(CONFIG)
    models={p:YOLO(str(BASELINE/'full'/p/'weights/best.pt')) for p in PARTS}
    mappings={p:{str(k):v for k,v in model.names.items()} for p,model in models.items()}
    for part in PARTS:
        assert mappings[part]==json.loads((BASELINE/'full'/part/'class_mapping.json').read_text()),'CLASS_MAPPING_CHANGED'
    sync();model_load_ms=(time.perf_counter()-started)*1000
    def classify(part,image):
        return models[part].predict([image],predictor=FixedPredictor,imgsz=224,device=0,quantize=32,verbose=False)[0]
    # Three warm-up requests use real input pixels but are never counted as frames or parity samples.
    warmup=read_image(ROOT/inputs[0]['raw_path'])
    for _ in range(3):
        _,_,crops=processor.process(warmup)
        for part,image in crops.items():classify(part,image)
    timings={}
    def timed(owner,name,key):
        original=getattr(owner,name)
        def call(*a,**kw):
            sync();start=time.perf_counter()
            try:return original(*a,**kw)
            finally:
                sync();timings[key]=timings.get(key,0)+(time.perf_counter()-start)*1000
        setattr(owner,name,call)
    timed(processor.detector,'predict','detection_ms')
    timed(processor.estimator,'_estimate','pose_matching_ms')
    timed(processor,'extract','crop_ms')
    records=[]
    for index,source in enumerate(inputs):
        record=dict(capture_id=source['capture_id'],display_index=source['display_index'],raw_sha256=source['raw_sha256'],
                    scope='OFFLINE_STILL_IMAGE_NOT_LIVE',timestamp=datetime.now(timezone.utc).isoformat(),parts={})
        timings.clear()
        try:
            path=ROOT/source['raw_path'];assert sha(path)==source['raw_sha256'],'RAW_HASH_MISMATCH'
            image=read_image(path);sync();start=time.perf_counter()
            result,canonical,crops=processor.process(image);sync();preprocessing_ms=(time.perf_counter()-start)*1000
            record['preprocessing']=result
            arrays={}
            for part in PARTS:
                details=dict(valid=part in crops,predicted_state=None,class_scores=None,class_mapping=mappings[part],crop_sha256=None)
                if part in crops:
                    sync();stage=time.perf_counter();prediction=classify(part,crops[part]);sync()
                    timings[part+'_ms']=(time.perf_counter()-stage)*1000
                    scores=prediction.probs.data.cpu().numpy()
                    details.update(predicted_state=mappings[part][str(int(scores.argmax()))],
                        class_scores={mappings[part][str(i)]:float(v) for i,v in enumerate(scores)},
                        crop_shape=list(crops[part].shape),pixel_sha256=hashlib.sha256(crops[part].tobytes()).hexdigest())
                    arrays[part]=crops[part]
                record['parts'][part]=details
            sync();timings['total_inspection_ms']=(time.perf_counter()-start)*1000
            timings['preprocessing_ms']=preprocessing_ms
            timings['alignment_and_preprocess_other_ms']=preprocessing_ms-timings.get('detection_ms',0)-timings.get('crop_ms',0)
            record['timings_ms']=dict(timings)
            # File encoding/writes are outside measured inference latency.
            folder=args.output/'images'/source['display_index'];folder.mkdir(parents=True)
            if canonical is not None:
                write_image(folder/'canonical.png',canonical);record['canonical_path']=str((folder/'canonical.png').relative_to(args.output))
            for part,array in arrays.items():
                crop_path=folder/(part+'.png');record['parts'][part]['crop_sha256']=write_image(crop_path,array)
                record['parts'][part]['crop_path']=str(crop_path.relative_to(args.output))
        except Exception as error:
            record.update(error=type(error).__name__+': '+str(error),preprocessing=dict(status='ERROR'))
        record['shadow_state']=aggregate_frame(record);records.append(record)
        with (args.output/'predictions.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
        if index%10==0:print(index+1,len(inputs),record['shadow_state'],flush=True)
    dump(args.output/'execution.json',dict(status='ERROR' if any(r.get('error') for r in records) else 'EXECUTED',
        samples=len(records),warmup=3,model_load_ms=model_load_ms,torch=torch.__version__,opencv=cv2.__version__,
        gpu=torch.cuda.get_device_name(0),config_sha256=sha(CONFIG),models={p:sha(BASELINE/'full'/p/'weights/best.pt') for p in PARTS},
        plc_output=False,camera_opened=False,production_decision_modified=False))
    print('SAVED',args.output,flush=True)


if __name__=='__main__':main()

"""One-class envelope candidate; explicit CUDA and development-only sources."""
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
os.environ['YOLO_AUTOINSTALL']='false'
os.environ['PYTHONUTF8']='1'
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'ultralytics_config')


def main():
    import torch
    from ultralytics import YOLO
    assert torch.cuda.is_available()
    assert '5070' in torch.cuda.get_device_name(0)
    weights='D:/OneDevice_Worktrees/jetson-p0-004c0/runs/manual_tracking_dev/engine_training_kit_v001/models/yolo11n.pt'
    started=time.time()
    model=YOLO(weights)
    model.train(data=str(ROOT/'dataset_v004/data.yaml'),device=0,epochs=100,patience=20,
        imgsz=640,batch=8,workers=0,project=str(ROOT/'training'),name='envelope_v004',exist_ok=False,
        seed=42,deterministic=True,amp=False,degrees=180,translate=.2,scale=.25,
        flipud=0,fliplr=0,mosaic=.5,close_mosaic=10,plots=True)
    best=ROOT/'training/envelope_v004/weights/best.pt'
    trained=YOLO(str(best))
    metrics=trained.val(data=str(ROOT/'dataset_v004/data.yaml'),split='val',device=0,
        imgsz=640,batch=8,workers=0,project=str(ROOT/'validation'),name='e03',plots=True)
    records=[]
    for path in sorted((ROOT/'dataset_v004/images/val').glob('D*.png')):
        assert 145<=int(path.stem[1:])<=216
        r=trained.predict(str(path),device=0,imgsz=640,rect=False,conf=.05,iou=.45,verbose=False)[0]
        r.save(filename=str(ROOT/'validation/e03'/f'{path.stem}_pred.jpg'))
        records.append({'id':path.stem,'detections':[{'class_id':int(b.cls.item()),'class_name':'product_envelope',
            'confidence':float(b.conf.item()),'bbox':b.xyxy[0].tolist()} for b in r.boxes]})
    (ROOT/'envelope_predictions_e03.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    report={'status':'TRAINED_DEVELOPMENT_CANDIDATE','metrics':metrics.results_dict,'seconds':time.time()-started,
        'e03_count':len(records),'e04_used':0,'device':torch.cuda.get_device_name(0),'best':str(best)}
    (ROOT/'training_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()

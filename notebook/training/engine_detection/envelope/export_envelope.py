"""Static raw-head ONNX export in the existing verified export environment."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
os.environ['YOLO_AUTOINSTALL']='false'
ROOT=Path(__file__).resolve().parent
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'ultralytics_export_config')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    import torch
    import onnx
    import ultralytics
    from ultralytics import YOLO
    source=ROOT/'training/envelope_v004/weights/best.pt'
    stage=ROOT/'envelope_export_v004'
    stage.mkdir(exist_ok=False)
    weights=stage/'envelope_best.pt'
    shutil.copyfile(source,weights)
    options=dict(format='onnx',imgsz=640,batch=1,dynamic=False,half=False,nms=False,simplify=False,opset=12,device=0)
    path=Path(YOLO(str(weights)).export(**options))
    model=onnx.load(str(path));onnx.checker.check_model(model)
    shapes={v.name:[d.dim_value for d in v.type.tensor_type.shape.dim] for v in model.graph.output}
    assert shapes=={'output0':[1,5,8400]},shapes
    value={'pt_sha256':sha(weights),'onnx_path':str(path),'source_onnx':{
        'sha256':sha(path),'export':{'tool':'Ultralytics YOLO.export','version':ultralytics.__version__,'options':options},
        'export_environment':{'torch':torch.__version__,'ultralytics':ultralytics.__version__,'onnx':onnx.__version__,'python':sys.version,'host_architecture':platform.machine()}},'outputs':shapes,'e04_used':0}
    (ROOT/'envelope_export.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value))

if __name__=='__main__':main()

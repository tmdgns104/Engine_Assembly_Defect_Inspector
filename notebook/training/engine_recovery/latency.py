"""PC single-image latency, including detector, pose, crops and four classifiers."""
import time
import numpy as np
import torch
from ultralytics import YOLO
from fit_train import OUTPUT
from investigate import BASELINE
from recovery import RecoveryPreprocessor
from preprocess import PARTS,read_image
from prepare_alignment import read_rows
from process_dataset import dump
from evaluate import predict


def main():
    started=time.perf_counter()
    processor=RecoveryPreprocessor(OUTPUT/'alignment/config_frozen.json')
    models={p:YOLO(str(BASELINE/'full'/p/'weights/best.pt')) for p in PARTS}
    rows={r['display_index']:r for r in read_rows(BASELINE/'export_validation_candidates.jsonl')}
    ids=['V0025','V0086','V0089','V0100','V0111','V0127','V0130','V0139','V0147','V0166','V0169','V0176']
    def one(id):
        raw=read_image(rows[id]['raw_image_path'])
        torch.cuda.synchronize();t=time.perf_counter()
        result,_,crops=processor.process(raw)
        torch.cuda.synchronize();aligned=time.perf_counter()
        for part in PARTS:
            if part in crops:predict(models[part],[crops[part]])
        torch.cuda.synchronize();finished=time.perf_counter()
        return dict(id=id,status=result['status'],pose_route=result['pose_route'],
            preprocessing_ms=(aligned-t)*1000,classifiers_ms=(finished-aligned)*1000,end_to_end_ms=(finished-t)*1000,
            classifier_count=len(crops))
    first=one(ids[0]);startup=(time.perf_counter()-started)*1000
    for id in ids[:3]:one(id)
    samples=[one(id) for repeat in range(3) for id in ids]
    stats={}
    for name,group in [('all',samples),('complete',[r for r in samples if r['classifier_count']==4]),('rejected',[r for r in samples if r['classifier_count']!=4])]:
        stats[name]={key:dict(median=float(np.median([r[key] for r in group])),p95=float(np.percentile([r[key] for r in group],95)),minimum=min(r[key] for r in group),maximum=max(r[key] for r in group)) for key in ['preprocessing_ms','classifiers_ms','end_to_end_ms']}
    dump(OUTPUT/'pc_latency.json',dict(device=torch.cuda.get_device_name(0),scope='Local PC only, batch1, FP32, CUDA synchronized; not Jetson or throughput',
        startup_model_construction_and_first_request_ms=startup,first_request=first,
        timing_excludes='Python import/process startup; image disk decode; report/image writes',
        warmup_requests=3,measured_requests=len(samples),repetitions=3,ids=ids,statistics=stats,samples=samples))
    print(stats,flush=True)


if __name__=='__main__':main()

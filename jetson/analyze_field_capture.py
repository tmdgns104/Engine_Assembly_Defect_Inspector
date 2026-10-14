"""Offline same-frame geometry evidence; never invokes a model, camera or PLC."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from src.vision.tensorrt_preprocess import preprocess


def sha(data):return hashlib.sha256(data).hexdigest()


def analyze(folder, output):
    folder=Path(folder).resolve();output=Path(output).resolve()
    if output==folder or folder.is_relative_to(output):raise ValueError('SEPARATE_ANALYSIS_DIRECTORY_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    rows=[json.loads(line) for line in (folder/'frames.jsonl').read_text(encoding='utf-8').splitlines()]
    request=json.loads((folder/'request.json').read_text(encoding='utf-8'))
    result=[]
    for row in rows:
        if row.get('raw_status')!='SAVED' or row.get('tensor_status')!='SAVED':continue
        raw_path=(folder/row['raw_path']).resolve();tensor_path=(folder/row['tensor_path']).resolve()
        if not raw_path.is_relative_to(folder) or not tensor_path.is_relative_to(folder):raise ValueError('UNSAFE_CAPTURE_PATH')
        raw_bytes=raw_path.read_bytes();tensor_bytes=tensor_path.read_bytes()
        assert sha(raw_bytes)==row['raw_sha256'] and sha(tensor_bytes)==row['tensor_sha256']
        image=cv2.imdecode(np.frombuffer(raw_bytes,np.uint8),cv2.IMREAD_COLOR)
        assert sha(image.tobytes())==row['pixel_sha256']
        obs=row['observation'];assert obs['detector_frame_id']==row['frame_id']
        stages=obs['engine']['detector_stages']
        model_input,transform=preprocess(image,stages['input_tensor_dtype'])
        assert sha(model_input.tobytes())==stages['input_tensor_sha256']
        raw=np.load(tensor_path,allow_pickle=False)
        before=[]
        for index in stages['eligible_raw_indices']:
            xywh=raw[0,:4,index].astype(np.float64)
            xyxy=np.r_[xywh[:2]-xywh[2:]/2,xywh[:2]+xywh[2:]/2]
            restored=(xyxy-np.array([transform.padding[0],transform.padding[1]]*2))/transform.gain
            scores=raw[0,4:,index]
            before.append(dict(raw_index=index,raw_xywh=xywh.tolist(),letterbox_xyxy=xyxy.tolist(),
                restored_before_clip=restored.tolist(),class_id=int(scores.argmax()),confidence=float(scores.max())))
        traces=stages['bbox_coordinate_trace']
        by_index={v['raw_index']:v for v in before}
        for trace in traces:
            np.testing.assert_array_equal(by_index[trace['raw_index']]['restored_before_clip'],trace['restored_before_clip'])
        prefix=f'{row["freshness"]["sequence"]:06d}'
        np.save(output/(prefix+'_model_input.npy'),model_input,allow_pickle=False)
        model_image=np.rint(model_input[0].transpose(1,2,0)[:,:,::-1]*255).astype(np.uint8)
        if not cv2.imwrite(str(output/(prefix+'_model_input.png')),model_image):raise OSError('MODEL_INPUT_VISUAL_SAVE_FAILED')
        result.append(dict(frame_id=row['frame_id'],sequence=row['freshness']['sequence'],
            raw_path=row['raw_path'],raw_pixel_sha256=row['pixel_sha256'],input_sha256=stages['input_tensor_sha256'],
            pre_nms=before,kept_raw_indices=stages['kept_raw_indices'],
            suppressed_raw_indices=stages['nms_suppressed_raw_indices'],
            post_nms=traces,final_detections=obs['detections'],product_envelope=obs['provider'],
            original_shape=stages['original_shape'],gain=transform.gain,padding=list(transform.padding),
            mathematical_clipping_observed=any(t['clipped_edges'] for t in traces),
            semantic_cause='UNRESOLVED_REQUIRES_ACTUAL_IMAGE_AND_OPERATOR_SCENE_REVIEW',
            inference_ms=obs.get('inference_ms')))
    document=dict(frames=result,source_context=request['context'],
        new_inference_executed=False,thresholds_changed=False,
        result='NO_MATCHED_RAW_TENSOR' if not result else 'SAME_FRAME_MATHEMATICS_VERIFIED_NOT_SEMANTIC_ROOT_CAUSE')
    (output/'BBOX_ANALYSIS.json').write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    return document


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(json.dumps({'matched_frames':len(analyze(args.folder,args.output)['frames'])}))

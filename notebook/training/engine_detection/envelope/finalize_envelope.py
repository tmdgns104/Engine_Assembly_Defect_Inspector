"""Freeze visually reviewed proposals with per-image correction lineage."""
import json
import shutil
import cv2
import numpy as np
from prepare_data import ROOT, TRAIN

def main():
    audit=json.loads((ROOT/'dataset_pose_audit_v002.json').read_text(encoding='utf-8'))
    alternative={r['review_id']:r for r in json.loads((ROOT/'dataset_pose_audit_v003.json').read_text(encoding='utf-8'))['rows']}
    out=ROOT/'dataset_v004'
    shutil.copytree(ROOT/'dataset_v002',out,dirs_exist_ok=True)
    review=ROOT/'review_final_v004'
    review.mkdir(exist_ok=True)
    tiles=[]
    for n,row in enumerate(audit['rows'],1):
        rid,split=row['review_id'],row['split']
        row['selected_proposal']='v002'
        if rid in {'D049','D053','D057'}:
            row['corrected_box']=alternative[rid]['corrected_box']
            row['selected_proposal']='v003'
            row['correction_reason']='Exclude bright background outside engine; visual review.'
        box=np.array(row['corrected_box'])
        image=cv2.imread(str(out/f'images/{split}/{rid}.png'))
        h,w=image.shape[:2]
        values=' '.join(f'{v:.10f}' for v in [(box[0]+box[2])/2/w,(box[1]+box[3])/2/h,(box[2]-box[0])/w,(box[3]-box[1])/h])
        (out/f'labels/{split}/{rid}.txt').write_text('0 '+values+'\n',encoding='utf-8')
        approved=(TRAIN/f'dataset/labels/{split}/{rid}.txt').read_bytes()
        combined=approved+(b'' if approved.endswith(b'\n') else b'\n')+('3 '+values+'\n').encode()
        (out/f'labels_combined/{split}/{rid}.txt').write_bytes(combined)
        assert combined.startswith(approved)
        assert [line for line in combined.splitlines() if line and not line.startswith(b'3 ')]==[line for line in approved.splitlines() if line]
        old=np.array(row['original_box'])
        cv2.rectangle(image,tuple(np.rint(old[:2]).astype(int)),tuple(np.rint(old[2:]).astype(int)),(0,0,255),2)
        cv2.rectangle(image,tuple(np.rint(box[:2]).astype(int)),tuple(np.rint(box[2:]).astype(int)),(0,255,255),3)
        tile=np.vstack([np.full((20,384,3),15,np.uint8),cv2.resize(image,(384,216))])
        cv2.putText(tile,rid+' '+row['scenario_capture_truth'],(4,14),cv2.FONT_HERSHEY_SIMPLEX,.36,(255,255,255),1)
        tiles.append(tile)
        if len(tiles)==12:
            cv2.imwrite(str(review/f'sheet_{n//12:02}.jpg'),np.vstack([np.hstack(tiles[j:j+4]) for j in range(0,12,4)]))
            tiles=[]
    (out/'data.yaml').write_text(f'path: {out.as_posix()}\ntrain: images/train\nval: images/val\nnames:\n  0: product_envelope\n',encoding='utf-8')
    audit['review_status']='AI visually reviewed all 216 v002 proposals; D049/D053/D057 replaced by visually reviewed v003. No human approval claimed.'
    audit['rejected_training']='envelope_v001 stopped: D007 shaft clipping. All originals retained.'
    (ROOT/'dataset_pose_audit_v004.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('216 envelopes frozen; original part labels preserved; E04=0')

if __name__=='__main__':main()

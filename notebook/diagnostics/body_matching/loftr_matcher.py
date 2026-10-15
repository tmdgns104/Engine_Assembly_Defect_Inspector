"""Pinned pretrained Kornia LoFTR, evaluated offline. Never downloads in inference."""
import copy
import time

import cv2
import kornia
import numpy as np
import torch
from kornia.feature.loftr.loftr import default_cfg

from geometry import body_regions, fit_body, hom, quarter_turn, transform


class LearnedBodyMatcher:
    def __init__(self, reference, profile, weights):
        if not torch.cuda.is_available():
            raise RuntimeError("Required notebook CUDA path unavailable")
        self.profile = profile
        self.reference = reference
        self.labels = body_regions(reference.shape, profile)
        config = copy.deepcopy(default_cfg)
        config['coarse']['temp_bug_fix'] = True  # indoor_new checkpoint contract
        start = time.perf_counter()
        self.model = kornia.feature.LoFTR(pretrained=None, config=config)
        state = torch.load(weights, map_location="cpu", weights_only=True)
        self.model.load_state_dict(state['state_dict'])
        self.model.eval().cuda()
        torch.cuda.synchronize()
        self.load_ms = (time.perf_counter()-start)*1000

    def tensor(self,im):
        # Fixed sampling from the recorded profile, then pad to eight.
        # Returned keypoints follow this pinned implementation's pixel frame;
        # synthetic controls measure any residual subpixel sampling bias.
        h, w = im.shape[:2]
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        fraction=self.profile['loftr']['resize']
        small = cv2.resize(gray, (round(w*fraction), round(h*fraction)), interpolation=cv2.INTER_AREA)
        ph, pw = (-small.shape[0]) % 8, (-small.shape[1]) % 8
        small = cv2.copyMakeBorder(small,0,ph,0,pw,cv2.BORDER_CONSTANT,value=40)
        return torch.from_numpy(small.astype(np.float32)/255.)[None,None].cuda()

    def match(self, current, mode="full"):
        start = time.perf_counter()
        reference = self.reference.copy()
        if mode == "reference_body_only":
            # Deliberately separate ablation; never silently substitute this
            # result for the full-image path. Target has no oracle body mask.
            reference[self.labels == 0] = 40
        t0 = self.tensor(reference)
        candidates = []
        for turn in self.profile['loftr']['quarter_turns_clockwise']:
            rotated, rotation = quarter_turn(current, turn)
            with torch.inference_mode():
                out = self.model(dict(image0=t0, image1=self.tensor(rotated)))
            factor=1/self.profile['loftr']['resize']
            p = out['keypoints0'].cpu().numpy()*factor
            q = transform(out['keypoints1'].cpu().numpy()*factor, np.linalg.inv(rotation))
            scores = out['confidence'].cpu().numpy()
            result = fit_body(p,q,scores,self.labels,len(self.profile['body_regions']))
            result['quarter_turn_clockwise'] = turn
            candidates.append(result)
        torch.cuda.synchronize()
        def rank(row):
            return (row['reason'] == 'BODY_GEOMETRY_CANDIDATE',
                    sum(n >= 3 for n in row['support']), row.get('inlier_unique',0),
                    -(row.get('median_residual_px') or 1e6))
        candidates.sort(key=rank, reverse=True)
        best = candidates[0]
        return dict(method="C_LOFTR", mode=mode, best=best, alternatives=candidates[1:],
                    elapsed_ms=(time.perf_counter()-start)*1000,
                    gpu_peak_bytes=torch.cuda.max_memory_allocated(),
                    validation="CANDIDATE_ONLY_REQUIRES_INDEPENDENT_GEOMETRY_AND_CROP_CHECK")

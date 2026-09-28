"""Whole-product observations only; never uses parts, pose or inspection truth."""
from src.observation.contracts import ProviderResult,ProviderStatus,AmbiguityReason
from src.tracking.contracts import ProductObservation,NormalizedBox


def envelope_provider(detections,width,height,threshold):
    from src.decision.engine_dynamic import box_of
    valid=[]
    for d in detections:
        if d['class_name']!='product_envelope': raise ValueError('PRODUCT_OBSERVATION_CLASS_INVALID')
        if d['confidence']<threshold: continue
        x1,y1,x2,y2=box_of(d)
        valid.append(ProductObservation(NormalizedBox(max(0,x1/width),max(0,y1/height),
            min(1,x2/width),min(1,y2/height)),'envelope_v007_fp16'))
    if len(valid)>1:
        return ProviderResult((),ProviderStatus.AMBIGUOUS_FOREGROUND,AmbiguityReason.MULTIPLE_FOREGROUND_COMPONENTS,0,0,len(valid),())
    return ProviderResult(tuple(valid),ProviderStatus.PRODUCT_OBSERVED if valid else ProviderStatus.NO_FOREGROUND,None,0,0,len(valid),())

"""Verify each inspected envelope against its latched product, never against parts."""
import math
from src.decision.engine_dynamic import box_of,SLOTS


def verify_observations(result,observations,binding,generation,package_sha):
    reasons=[]; checks=[]; previous=binding.get('product_box')
    epoch=binding['camera_epoch']; last_sequence=binding.get('sequence',-1)
    last_time=binding.get('monotonic_s',0)
    if generation!=binding['worker_generation'] or package_sha!=binding['package_manifest_sha']:
        reasons.append('WORKER_OR_PACKAGE_IDENTITY_CHANGED')
    zone=binding['inspection_zone']['polygon_normalized']
    for i,o in enumerate(observations,1):
        fresh=o['freshness']; failed=[]
        if fresh.get('camera_epoch')!=epoch: failed.append('CAMERA_EPOCH_CHANGED')
        if fresh['sequence']<=last_sequence or fresh['estimated_source_monotonic']<=last_time:
            failed.append('FRAME_ORDER_INVALID')
        last_sequence=fresh['sequence']; last_time=fresh['estimated_source_monotonic']
        product=o['engine_dynamic'].get('product')
        if product:
            x1,y1,x2,y2=box_of(product); box=[x1/o['width'],y1/o['height'],x2/o['width'],y2/o['height']]
            center=((box[0]+box[2])/2,(box[1]+box[3])/2)
            if not (zone[0][0]-.025<=center[0]<=zone[2][0]+.025 and zone[0][1]-.025<=center[1]<=zone[2][1]+.025):
                failed.append('PRODUCT_OUTSIDE_INSPECTION_ZONE')
            if binding.get('track_id') is None: failed.append('NO_ELIGIBLE_TRACK_AT_REQUEST_DEADLINE')
            if previous:
                distance=math.hypot(center[0]-(previous[0]+previous[2])/2,center[1]-(previous[1]+previous[3])/2)
                intersection=max(0,min(box[2],previous[2])-max(box[0],previous[0]))*max(0,min(box[3],previous[3])-max(box[1],previous[1]))
                union=(box[2]-box[0])*(box[3]-box[1])+(previous[2]-previous[0])*(previous[3]-previous[1])-intersection
                if distance>.22 or (intersection/max(union,1e-12)<.02 and distance>.12):
                    failed.append('INSPECTED_PRODUCT_ASSOCIATION_UNCERTAIN')
            previous=box
        checks.append(dict(frame_number=i,frame_id=o['frame_id'],failed_conditions=failed))
        reasons.extend(failed)
    result['production_identity']=binding.copy()
    result['production_frame_checks']=checks
    if reasons and result['decision']!='ERROR' and result.get('reason_code')!='PRODUCT_ENVELOPE_NOT_FOUND':
        result.update(decision='REVIEW',reason='PRODUCTION_BINDING_UNCERTAIN',reason_code='PRODUCTION_BINDING_UNCERTAIN',
            disposition='REJECT',slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'),binding_failures=sorted(set(reasons)))
    return result

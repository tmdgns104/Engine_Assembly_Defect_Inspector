"""Pure engine-relative assignment and conservative three-frame decision policy."""
import math
import cv2
import numpy as np

SLOTS = ('pipe_left','pipe_right','exhaust','symbol')
CLASSES = {'gray_pipe','exhaust_top','symbol_module','product_envelope'}
MISSING_CODES = dict(zip(SLOTS,('LEFT_PIPE_MISSING','RIGHT_PIPE_MISSING','EXHAUST_TOP_MISSING','SYMBOL_MODULE_MISSING')))


def box_of(detection):
    box=detection.get('bounding_box',detection.get('bbox'))
    if isinstance(box,dict): box=[box[k] for k in ('x1','y1','x2','y2')]
    if box is None or len(box)!=4: raise ValueError('INVALID_DETECTION_BOX')
    box=[float(v) for v in box]
    if not all(math.isfinite(v) for v in box) or box[2]<=box[0] or box[3]<=box[1]:
        raise ValueError('INVALID_DETECTION_BOX')
    return box


def result(decision,code,**evidence):
    return dict(decision=decision,reason_code=code,reason=code,
        disposition='PASS' if decision=='PASS' else 'REJECT',
        slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'),defects=[],unassessed=[],**evidence)


def detection_geometry(detection):
    """Camera coordinates; restored quadrilateral is decision geometry, AABB is display only."""
    x1,y1,x2,y2=box_of(detection)
    polygon=np.asarray(detection.get('detection_polygon',
        [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]),np.float32)
    if (polygon.shape!=(4,2) or not np.isfinite(polygon).all()
            or not cv2.isContourConvex(polygon) or cv2.contourArea(polygon)<=0):
        raise ValueError('INVALID_DETECTION_POLYGON')
    # A malformed restored polygon must not escape its recorded display bounds.
    if np.any(polygon.min(axis=0)<np.array([x1,y1])-.1) or np.any(polygon.max(axis=0)>np.array([x2,y2])+.1):
        raise ValueError('DETECTION_GEOMETRY_MISMATCH')
    return polygon


def select_products(detections,threshold,shape):
    candidates=[d for d in detections if d['class_name']=='product_envelope']
    products=[d for d in candidates if d['confidence']>=threshold]
    h,w=shape[:2]
    detail=('NO_RETURNED_CANDIDATES' if not candidates else 'CANDIDATES_BELOW_THRESHOLD'
        if not products else 'MULTIPLE_VALID_CANDIDATES' if len(products)>1 else 'SELECTED')
    return products,dict(stage='POST_NMS_PRODUCT_SELECTION',detail=detail,
        confidence_threshold=threshold,candidate_count=len(candidates),valid_count=len(products),
        candidates=[dict(detection_index=detections.index(d),confidence=d['confidence'],box=box_of(d),
            accepted=d['confidence']>=threshold,
            touches_frame_boundary=any((box_of(d)[0]<=0,box_of(d)[1]<=0,box_of(d)[2]>=w,box_of(d)[3]>=h))) for d in candidates])


def inspect_frame(frame,detections,estimator,*,pose=None):
    if not isinstance(frame,np.ndarray) or frame.ndim!=3 or frame.shape[2]!=3 or not frame.size:
        return result('ERROR','INVALID_FRAME')
    try:
        for d in detections:
            if d['class_name'] not in CLASSES: raise ValueError('UNEXPECTED_DETECTION_CLASS')
            if not math.isfinite(float(d['confidence'])) or not 0<=float(d['confidence'])<=1:
                raise ValueError('INVALID_DETECTION_CONFIDENCE')
            box_of(d)
            if d['class_name']!='product_envelope':detection_geometry(d)
    except (ValueError,KeyError,TypeError) as error:
        return result('ERROR',str(error))
    policy=estimator.cfg['decision_policy']
    products,selection=select_products(detections,policy['product_confidence'],frame.shape)
    if not products:return result('FAIL','PRODUCT_ENVELOPE_NOT_FOUND',product_selection=selection)
    if len(products)!=1:return result('REVIEW','MULTIPLE_PRODUCT_ENVELOPES',products=products,product_selection=selection)
    product=products[0]
    pose=pose if pose is not None else estimator.estimate(frame,box_of(product))
    pose_evidence={'reliable':pose.ok,'reliability_reason':pose.reason,'angle_deg':pose.angle_deg,'scale':pose.scale,
        'translation':pose.matrix[:,2].tolist() if pose.matrix is not None else None,
        'matrix':pose.matrix.tolist() if pose.matrix is not None else None,
        'matches':pose.good_matches,'inliers':pose.inliers,'reprojection_error_px':pose.median_error_px,
        'diagnostics':getattr(pose,'diagnostics',None)}
    if not pose.ok:return result('REVIEW','ENGINE_POSE_UNCERTAIN',product=product,pose=pose_evidence,product_selection=selection)
    polygons=estimator.current_slots(pose)
    visible_polygons=estimator.visibility_slots(pose) if hasattr(estimator,'visibility_slots') else polygons
    if any(np.min(poly[:,0])<0 or np.min(poly[:,1])<0 or np.max(poly[:,0])>frame.shape[1] or np.max(poly[:,1])>frame.shape[0] for poly in visible_polygons.values()):
        return result('REVIEW','SLOT_OUTSIDE_FRAME',product=product,pose=pose_evidence,
            slot_polygons={s:p.tolist() for s,p in polygons.items()},product_selection=selection)
    assignments={s:[] for s in SLOTS}
    unassigned=[]
    diagnostics=[]
    ambiguous_slots=set()
    px1,py1,px2,py2=box_of(product)
    product_polygon=np.float32([[px1,py1],[px2,py1],[px2,py2],[px1,py2]])
    for index,d in enumerate(detections):
        if d['class_name']=='product_envelope':continue
        rectangle=detection_geometry(d)
        area=cv2.contourArea(rectangle)
        center=tuple(map(float,rectangle.mean(axis=0)))
        product_intersection,_=cv2.intersectConvexConvex(rectangle,product_polygon)
        inside_product=cv2.pointPolygonTest(product_polygon,center,False)>=0
        candidates=[]
        comparisons=[]
        for slot,poly in polygons.items():
            if estimator.cfg['slot_expected_class'][slot]!=d['class_name']:continue
            overlap,_=cv2.intersectConvexConvex(rectangle,poly.astype(np.float32))
            ratio=max(0.,min(1.,float(overlap)/area))
            inside=cv2.pointPolygonTest(poly.astype(np.float32),center,False)>=0
            comparisons.append(dict(slot=slot,center_inside=inside,overlap=ratio))
            if inside and ratio>=policy.get('slot_overlap',.4):candidates.append((slot,ratio))
        if len(candidates)==1 and d['confidence']>=policy['part_confidence']:
            slot,overlap=candidates[0]
            assignments[slot].append({'detection_index':index,'overlap':overlap})
            reason='ASSIGNED'
        else:
            unassigned.append(index)
            reason=('LOW_CONFIDENCE' if d['confidence']<policy['part_confidence'] else
                'MULTIPLE_SLOT_CANDIDATES' if len(candidates)>1 else 'WRONG_POSITION_OR_OUTSIDE_SLOTS')
            # Unobserved and observed-but-unassignable are different evidence.
            affected=[s for s,_ in candidates] or [c['slot'] for c in comparisons if c['center_inside'] or c['overlap']>0]
            if not affected:affected=[s for s in SLOTS if estimator.cfg['slot_expected_class'][s]==d['class_name']]
            ambiguous_slots.update(affected)
        diagnostics.append(dict(detection_index=index,class_name=d['class_name'],confidence=d['confidence'],
            confidence_threshold=policy['part_confidence'],overlap_threshold=policy.get('slot_overlap',.4),
            coordinate_space='camera',geometry='restored_polygon' if 'detection_polygon' in d else 'legacy_aabb',
            center_in_product_bbox=inside_product,product_overlap=max(0.,min(1.,float(product_intersection)/area)),
            position_detail='INSIDE_PRODUCT_BBOX' if inside_product else 'OUTSIDE_PRODUCT_BBOX',
            expected_count=1,
            polygon=rectangle.tolist(),area=area,overlap_definition='intersection_area / detection_polygon_area',
            slot_candidates=comparisons,assigned_slot=candidates[0][0] if reason=='ASSIGNED' else None,reason=reason))
    states={s:'PRESENT' if len(a)==1 else 'MISSING' if not a else 'UNCERTAIN' for s,a in assignments.items()}
    for slot in ambiguous_slots:states[slot]='UNCERTAIN'
    for diagnostic in diagnostics:
        slot=diagnostic['assigned_slot']
        if slot and len(assignments[slot])>1:diagnostic['reason']='DUPLICATE_DETECTION'
    uncertain=bool(unassigned) or 'UNCERTAIN' in states.values()
    missing='MISSING' in states.values()
    value=result('REVIEW' if uncertain or missing else 'PASS',
        'PART_ASSIGNMENT_UNCERTAIN' if uncertain else 'AWAITING_THREE_FRAME_CONFIRMATION' if missing else 'ALL_REQUIRED_PARTS_PRESENT',
        product=product,pose=pose_evidence,assignments=assignments,unassigned_detections=unassigned,
        slot_polygons={s:p.tolist() for s,p in polygons.items()},
        assignment_diagnostics=diagnostics,product_selection=selection)
    value['slot_states']=states
    value['assignment_reliable']=not uncertain
    return value


def aggregate_three(frames):
    def outcome(decision,code):
        value=result(decision,code,frames=frames)
        value['slot_states']={s:('NOT_EVALUATED' if any(f.get('slot_states',{}).get(s,'NOT_EVALUATED')=='NOT_EVALUATED' for f in frames)
            else 'UNCERTAIN') for s in SLOTS}
        value['blocking_frames']=[]
        for number,frame in enumerate(frames,1):
            blocks=(frame.get('reason_code')==code or
                code=='IMAGE_QUALITY_INSUFFICIENT' and frame.get('quality_valid') is not True or
                code=='PART_ASSIGNMENT_UNCERTAIN' and not frame.get('assignment_reliable'))
            if blocks:value['blocking_frames'].append(dict(frame_number=number,frame_id=frame.get('frame_id'),reason_code=code))
        value['representative_frame_id']=frames[-1].get('frame_id') if frames else None
        return value
    if len(frames)!=3:return outcome('ERROR','FRESH_FRAME_COUNT_INVALID')
    fault=next((f for f in frames if f['decision']=='ERROR'),None)
    if fault:return outcome('ERROR',fault['reason_code'])
    identifiers=[f.get('frame_id') for f in frames]
    pts=[f.get('source_pts_ns') for f in frames]
    context_invalid=any(any(k in f for f in frames) and (any(f.get(k) is None for f in frames) or
        len({f.get(k) for f in frames})!=1) for k in ('inspection_id','camera_epoch'))
    if context_invalid or None in identifiers or len(set(identifiers))!=3 or any(type(p) is not int for p in pts) or not pts[0]<pts[1]<pts[2]:
        return outcome('ERROR','FRESH_FRAME_IDENTITY_INVALID')
    if any(f.get('reason_code')=='PRODUCT_ENVELOPE_NOT_FOUND' for f in frames):
        return outcome('FAIL','PRODUCT_ENVELOPE_NOT_FOUND')
    if any(f.get('quality_valid') is not True for f in frames):return outcome('REVIEW','IMAGE_QUALITY_INSUFFICIENT')
    for code in ('MULTIPLE_PRODUCT_ENVELOPES','ENGINE_POSE_UNCERTAIN','SLOT_OUTSIDE_FRAME'):
        if any(f['reason_code']==code for f in frames):return outcome('REVIEW',code)
    if any(not f.get('assignment_reliable') for f in frames):return outcome('REVIEW','PART_ASSIGNMENT_UNCERTAIN')
    states={s:('PRESENT' if all(f['slot_states'][s]=='PRESENT' for f in frames) else
               'MISSING_CONFIRMED' if all(f['slot_states'][s]=='MISSING' for f in frames) else 'UNCERTAIN') for s in SLOTS}
    missing=[s for s,state in states.items() if state=='MISSING_CONFIRMED']
    if 'UNCERTAIN' in states.values():value=outcome('REVIEW','INCONSISTENT_THREE_FRAME_RESULT')
    elif missing:
        code='ALL_TARGET_PARTS_MISSING' if len(missing)==4 else MISSING_CODES[missing[0]] if len(missing)==1 else 'MULTIPLE_TARGET_PARTS_MISSING'
        value=outcome('FAIL',code)
        value['reason_codes']=[MISSING_CODES[s] for s in missing]
        value['defects']=[{'slot':s,'code':MISSING_CODES[s],'reason_code':MISSING_CODES[s]} for s in missing]
    else:value=outcome('PASS','ALL_REQUIRED_PARTS_PRESENT_3_FRAMES')
    value['slot_states']=states
    return value

"""Closed STL versus convex optical volume; numpy only, no mesh repair.

Clip candidate triangles against all six half-spaces. This catches crossings
with no interior mesh vertex. A solid-angle containment check also rejects a
keep-out volume completely enclosed by a closed mesh. Contact is conservative
FAIL; the numerical epsilon is 1e-7 mm, never the 5 mm design margin.
"""
import math
import numpy as np

EPS = 1e-7


def fov_planes(origin, hfov, vfov, uncertainty, margin, target_z):
    tx, ty = np.tan(np.radians([hfov, vfov])/2)
    hx = uncertainty+margin*math.sqrt(1+tx*tx)
    hy = uncertainty+margin*math.sqrt(1+ty*ty)
    x,y,z = origin
    normals = np.array([[1,0,tx],[-1,0,tx],[0,1,ty],[0,-1,ty],[0,0,1],[0,0,-1]],float)
    bounds = np.array([x+tx*z+hx,-x+tx*z+hx,y+ty*z+hy,-y+ty*z+hy,z,-target_z])
    lengths = np.linalg.norm(normals,axis=1)
    return normals/lengths[:,None], bounds/lengths


def clipped_triangle(triangle, normals, bounds):
    polygon = triangle.tolist()
    for normal,bound in zip(normals,bounds):
        output = []
        for start,end in zip(polygon,polygon[1:]+polygon[:1]):
            start,end = np.asarray(start),np.asarray(end)
            a,b = np.dot(start,normal)-bound,np.dot(end,normal)-bound
            if a<=EPS:
                output.append(start.tolist())
            if (a<=EPS)!=(b<=EPS):
                fraction = (a-EPS)/(a-b)
                output.append((start+fraction*(end-start)).tolist())
        polygon = output
        if not polygon:
            return []
    return polygon


def inside_closed_mesh(triangles, point):
    vectors = triangles-np.asarray(point)
    lengths = np.linalg.norm(vectors,axis=2)
    if np.any(lengths<EPS):
        return True
    a,b,c = vectors[:,0],vectors[:,1],vectors[:,2]
    la,lb,lc = lengths.T
    numerator = np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator = la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
    winding = np.sum(2*np.arctan2(numerator,denominator))
    return bool(abs(winding)>2*math.pi)


def intersection_check(mesh, normals, bounds, interior_point):
    triangles = mesh.triangles
    distance = triangles@normals.T-bounds
    excluded = np.any(np.all(distance>EPS,axis=1),axis=1)
    candidates = np.flatnonzero(~excluded)
    for index in candidates:
        polygon = clipped_triangle(triangles[index],normals,bounds)
        if polygon:
            return {"intersection":"FOUND","method":"triangle half-space clipping",
                    "triangle_index":int(index),"witness_xyz_mm":polygon[0]}
    if inside_closed_mesh(triangles,interior_point):
        return {"intersection":"FOUND","method":"keep-out enclosed by closed mesh"}
    return {"intersection":"NONE","candidate_triangles":int(len(candidates))}


def translated(mesh, offset):
    result=mesh.copy()
    result.apply_translation(offset)
    return result


def cable_segment_boxes(p,slide,z):
    body=p['DECK_BOTTOM_Z']+p['DECK_T']-p['POCKET_DEPTH']+p['PAD_T']
    cy=p['CAMERA_Y']
    post=(p['PORTAL_INNER_CLEAR_WIDTH']+p['UPRIGHT_WIDTH'])/2
    points=np.array([[30,cy-10,body+p['CAMERA_D']+2],[42,cy-17,117],
        [48,cy-30,110],[48,cy-45,76],[0,80,76],[0,-22,76],[post-slide,-22,76]])
    return np.array([[np.minimum(a,b)-2,np.maximum(a,b)+2] for a,b in zip(points,points[1:])])+[slide,0,z]


def cable_boxes_cover_mesh(mesh,boxes):
    # Each actual triangle must be wholly inside at least one convex segment box.
    covered=np.zeros(len(mesh.faces),dtype=bool)
    for lower,upper in boxes:
        covered |= np.all((mesh.triangles>=lower-0.001)&(mesh.triangles<=upper+0.001),axis=(1,2))
    return bool(covered.all())


def check_all(meshes, refs, p, dimensions, original_deck):
    rail=meshes['upright_300'].copy()
    v=rail.vertices.copy()
    rail.vertices=np.column_stack([v[:,0]-p['UPRIGHT_WIDTH']/2,
        v[:,2]-p['UPRIGHT_THICKNESS'],p['RAIL_LENGTH']-v[:,1]+p['RAIL_BOTTOM_Z']])
    bar=meshes['crossbar'].copy()
    v=bar.vertices.copy()
    bar.vertices=np.column_stack([v[:,0]-bar.extents[0]/2,v[:,2],p['BAR_H']-v[:,1]])
    deck=original_deck(meshes['camera_deck'],p)
    post=(p['PORTAL_INNER_CLEAR_WIDTH']+p['UPRIGHT_WIDTH'])/2
    fixed={
        'left_upright':translated(rail,[-post,0,0]),
        'right_upright':translated(rail,[post,0,0]),
        'base_left':translated(meshes['base_left'],[-post-p['BASE_W']+p['UPRIGHT_WIDTH']/2,-40,0]),
        'base_right':translated(meshes['base_right'],[post-p['UPRIGHT_WIDTH']/2,-40,0]),
        'base_bolts_nuts_washers':refs['base_fasteners_reference'],
        'table_fasteners':refs['table_fasteners_reference'],
        'cable_tail':refs['cable_tail_reference'],
    }
    rows=[]
    for pose in dimensions['height_positions']:
        z=pose['table_to_crossbar_bottom_mm']
        support=pose['table_to_deck_support_mm']
        for slide in [-30,0,30]:
            origin=np.array([slide+p['LENS_OFFSET_X'],p['CAMERA_Y']+p['LENS_OFFSET_Y'],support+p['OPTICAL_ORIGIN_ABOVE_SUPPORT']])
            normals,bounds=fov_planes(origin,p['CAMERA_HFOV'],p['CAMERA_VFOV'],
                p['OPTICAL_ORIGIN_MARGIN_XY'],p['OPTICAL_CLEARANCE_MARGIN'],p['OPTICAL_TARGET_Z'])
            probe=[origin[0],origin[1],(origin[2]+p['OPTICAL_TARGET_Z'])/2]
            parts={**fixed,'crossbar':translated(bar,[0,0,z]),
                'deck_including_stops_retainer_tie_guides':translated(deck,[slide,0,z]),
                'cable_route':translated(refs.get(f'cable_reference_{slide}',refs['cable_reference']),[slide,0,z]),
                'velcro_route':translated(refs['strap_reference'],[slide,0,z]),
                'rail_bolts_nuts_washers':translated(refs['rail_fasteners_reference'],[0,0,z]),
                'deck_bolts_nuts_washers':translated(refs['deck_fasteners_reference'],[slide,0,z])}
            results={name:intersection_check(m,normals,bounds,probe) for name,m in parts.items()}
            belt_z=p['CONVEYOR_BOTTOM_Z']+p['CONVEYOR_SIDE_HEIGHT']
            # Nominal rays only for coverage; clearance/uncertainty must not inflate coverage.
            nominal_h=(origin[2]-belt_z)*np.tan(np.radians([p['CAMERA_HFOV'],p['CAMERA_VFOV']])/2)
            required=[p['INSPECTION_ZONE_W']/2+abs(origin[0]),p['INSPECTION_ZONE_L']/2+abs(p['LENS_OFFSET_Y'])]
            coverage=bool(belt_z<origin[2] and np.all(nominal_h>=required))
            sections={}
            tangents=np.tan(np.radians([p['CAMERA_HFOV'],p['CAMERA_VFOV']])/2)
            for name,level in [('lens_reference_plane',origin[2]),('deck_top',support+p['POCKET_DEPTH']),
                               ('contact_plane',support),('deck_bottom',z+p['DECK_BOTTOM_Z']),('belt_reference',belt_z)]:
                depth=origin[2]-level
                raw=2*depth*tangents
                expanded=raw+2*p['OPTICAL_ORIGIN_MARGIN_XY']+2*p['OPTICAL_CLEARANCE_MARGIN']*np.sqrt(1+tangents*tangents)
                sections[name]={'z_mm':float(level),'nominal_ray_xy_mm':raw.tolist(),'expanded_keepout_xy_mm':expanded.tolist()}
            rows.append({'lower_index':pose['lower_index'],'height_label':{2:'LOW',7:'MID',12:'HIGH'}.get(pose['lower_index'],'INTERMEDIATE'),
                'slide_mm':slide,'support_z_mm':support,'origin_xyz_mm':origin.tolist(),
                'parts':results,'nominal_belt_footprint_xy_mm':(2*nominal_h).tolist(),
                'fov_plane_sections':sections,
                'inspection_zone_covered':coverage,
                'status':'PASS' if coverage and all(r['intersection']=='NONE' for r in results.values()) else 'FAIL'})
    mid_origin=[p['LENS_OFFSET_X'],p['CAMERA_Y']+p['LENS_OFFSET_Y'],225+p['OPTICAL_ORIGIN_ABOVE_SUPPORT']]
    n,b=fov_planes(mid_origin,p['CAMERA_HFOV'],p['CAMERA_VFOV'],p['OPTICAL_ORIGIN_MARGIN_XY'],p['OPTICAL_CLEARANCE_MARGIN'],p['OPTICAL_TARGET_Z'])
    fov=refs['fov_reference']
    errors=np.abs(np.max(fov.vertices@n.T-b,axis=0))
    reference_ok=bool(np.all(errors<0.002))
    aliases={'camera_stop':'deck_including_stops_retainer_tie_guides',
             'cable_guide':'deck_including_stops_retainer_tie_guides',
             'retainer':'deck_including_stops_retainer_tie_guides'}
    return {'source':'PROVISIONAL_DESIGN_ENVELOPE','HFOV':p['CAMERA_HFOV'],'VFOV':p['CAMERA_VFOV'],
        'optical_axis':'TOP-DOWN','origin_above_support_mm':p['OPTICAL_ORIGIN_ABOVE_SUPPORT'],
        'origin_uncertainty_xy_mm':p['OPTICAL_ORIGIN_MARGIN_XY'],
        'lateral_clearance_margin_mm':p['OPTICAL_CLEARANCE_MARGIN'], 'numerical_epsilon_mm':EPS,
        'method':'actual exported STL triangles clipped against expanded convex FOV + closed-solid containment',
        'inspection_zone_xy_mm':[p['INSPECTION_ZONE_W'],p['INSPECTION_ZONE_L']],
        'integrated_features_checked_with':aliases,
        'scad_fov_reference':{'bounds_mm':fov.bounds.tolist(),'face_plane_errors_mm':errors.tolist(),
            'status':'PASS' if reference_ok else 'FAIL'},
        'poses':rows,'part_checks':sum(len(r['parts']) for r in rows),
        'physical_fov':'UNVERIFIED','status':'PASS' if reference_ok and all(r['status']=='PASS' for r in rows) else 'FAIL'}

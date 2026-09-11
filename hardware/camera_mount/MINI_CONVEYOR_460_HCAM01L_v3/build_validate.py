"""Export and verify the actual V3 print meshes. Uses only numpy/trimesh + OpenSCAD.

Default invocation is a fresh complete build. --mesh-only is a diagnostic and
cannot produce a final PASS. No automatic mesh repair or camera access occurs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import tempfile
import time

import numpy as np
import trimesh
import optical_validation

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCE = ROOT / "src/MINI_CONVEYOR_460_HCAM01L_v3.scad"
PARTS = {"base_left": 1, "base_right": 1, "upright_300": 2, "crossbar": 1,
         "camera_deck": 1, "camera_deck_fit_coupon": 1,
         "upright_hole_coupon": 1, "base_mount_coupon": 1}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def constants():
    return {k: float(v) for k, v in re.findall(
        r"^([A-Z_0-9]+)\s*=\s*([0-9.]+)\s*;", SOURCE.read_text(encoding="utf-8"), re.M)}


def run_cad(exe, path, part, definitions=None, extra=()):
    cmd = [exe, "-o", str(path), "-D", f'PART="{part}"']
    for key, value in (definitions or {}).items():
        cmd += ["-D", f"{key}={value}"]
    cmd += list(extra) + [str(SOURCE)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    log = result.stdout + result.stderr
    (ROOT/"validation"/(path.stem+".txt")).write_text(log, encoding="utf-8")
    return result, log


def mesh_checks(mesh):
    # Face adjacency components without scipy/networkx; never silently repair.
    parents = np.arange(len(mesh.faces))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in mesh.face_adjacency:
        parents[find(a)] = find(b)
    components = len({find(i) for i in range(len(parents))})
    return {"nonempty": len(mesh.vertices)>0 and len(mesh.faces)>0,
            "positive_volume": bool(mesh.volume>0), "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "one_connected_solid": components==1,
            "finite_positive_bounds": bool(np.isfinite(mesh.bounds).all() and (mesh.extents>0).all()),
            "bed_z_zero": bool(abs(mesh.bounds[0,2])<0.002)}


def ray_hit(mesh, point, direction):
    tri = mesh.triangles
    edge1, edge2 = tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]
    direction = np.asarray(direction, dtype=float)
    cross = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
    det = np.einsum("ij,ij->i", edge1, cross)
    good = abs(det)>1e-9
    inv = np.zeros_like(det)
    inv[good] = 1/det[good]
    offset = np.asarray(point)-tri[:,0]
    u = np.einsum("ij,ij->i",offset,cross)*inv
    q = np.cross(offset,edge1)
    v = np.einsum("j,ij->i",direction,q)*inv
    dist = np.einsum("ij,ij->i",edge2,q)*inv
    good &= (u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(dist>1e-7)
    return float(dist[good].min()) if good.any() else None


def section_loops(mesh, axis, level):
    """Intersect actual triangles, then assemble closed 2D polygons without extras."""
    normal = np.eye(3)[axis]
    origin = normal*level
    lines = trimesh.intersections.mesh_plane(mesh, normal, origin)
    keep = [i for i in range(3) if i!=axis]
    pts, ids = np.unique(np.round(lines[:,:,keep].reshape(-1,2),5), axis=0, return_inverse=True)
    edges = {tuple(sorted(e)) for e in ids.reshape(-1,2) if e[0]!=e[1]}
    adjacent = {i:set() for e in edges for i in e}
    for a,b in edges:
        adjacent[a].add(b)
        adjacent[b].add(a)
    if any(len(n)!=2 for n in adjacent.values()):
        raise ValueError("Section did not form closed degree-2 loops")
    loops = []
    remaining = set(adjacent)
    while remaining:
        first = min(remaining)
        previous, current, route = None, first, []
        while current not in route:
            route.append(current)
            options = adjacent[current]-({previous} if previous is not None else set())
            nxt = min(options)
            previous, current = current, nxt
        assert current==first
        remaining.difference_update(route)
        loops.append(pts[route])
    return loops


def circle_sections(mesh, axis, level):
    found = []
    for loop in section_loops(mesh,axis,level):
        lower, upper = loop.min(axis=0), loop.max(axis=0)
        extent = upper-lower
        centre = (lower+upper)/2
        radii = np.linalg.norm(loop-centre,axis=1)
        if abs(extent[0]-extent[1])<0.01 and np.ptp(radii)<0.06:
            found.append({"centre": centre.tolist(), "diameters": extent.tolist(),
                          "minimum_vertex_diameter": float(2*radii.min())})
    return sorted(found,key=lambda r:tuple(r["centre"]))


def close(actual, expected, tol=0.003):
    return bool(np.allclose(actual,expected,atol=tol,rtol=0))


def original_deck(mesh, p, coupon=False):
    result = mesh.copy()
    v = mesh.vertices
    if coupon:
        result.vertices = np.column_stack([v[:,0]-p["DECK_W"]/2,v[:,1]+p['CAMERA_Y']-p['COUPON_REAR_OFFSET'],v[:,2]+p["DECK_BOTTOM_Z"]])
    else:
        result.vertices = np.column_stack([v[:,2]-p['DECK_W']/2,v[:,0]+p['BAR_T'],v[:,1]])
    return result


def deck_dimensions(mesh, p):
    centre = [0,p["CAMERA_Y"],p["DECK_BOTTOM_Z"]+p["DECK_T"]-p["POCKET_DEPTH"]+0.5]
    width = ray_hit(mesh,centre,[1,0,0])+ray_hit(mesh,centre,[-1,0,0])
    length = ray_hit(mesh,centre,[0,1,0])+ray_hit(mesh,centre,[0,-1,0])
    lands = [100-ray_hit(mesh,[x,p["CAMERA_Y"]+y,100],[0,0,-1])
             for x in [-35,35] for y in [-12,12]]
    outer_top = 100-ray_hit(mesh,[53,p['CAMERA_Y']+18,100],[0,0,-1])
    relief_floor = 100-ray_hit(mesh,[25,p["CAMERA_Y"],100],[0,0,-1])
    circles = circle_sections(mesh,2,p["DECK_BOTTOM_Z"]+3)
    lens = [c for c in circles if c["diameters"][0]>20]
    assert len(lens)==1
    slope=math.sqrt(sum(np.tan(np.radians([p['CAMERA_HFOV'],p['CAMERA_VFOV']])/2)**2))
    window_sections=[]
    for level in [p['DECK_BOTTOM_Z']+0.02, p['DECK_BOTTOM_Z']+3, p['DECK_BOTTOM_Z']+p['DECK_T']-0.02]:
        # Rays through the actual cut measure the aperture even where the pocket removes its top wall.
        origin=[p['LENS_OFFSET_X'],p['CAMERA_Y']+p['LENS_OFFSET_Y'],level]
        xy=[ray_hit(mesh,origin,a)+ray_hit(mesh,origin,-np.asarray(a)) for a in [[1,0,0],[0,1,0]]]
        expected=p['LENS_WINDOW_D']+2*(p['DECK_BOTTOM_Z']+p['DECK_T']-level)*slope
        window_sections.append({'z_mm':level,'clear_xy_mm':xy,'cone_diameter_mm':expected,
            'status':'PASS' if min(xy)>=expected-0.004 else 'FAIL'})
    measured = {"pocket_xy_mm":[width,length], "contact_land_z_mm":lands,
                "pocket_depth_mm":float(outer_top-lands[0]), "relief_depth_mm":float(lands[0]-relief_floor),
                "lens_window":lens[0], 'flared_sections':window_sections,
                'window_top_nominal_mm':p['LENS_WINDOW_D'],'window_bottom_nominal_mm':p['LENS_WINDOW_D']+2*p['DECK_T']*slope}
    measured["status"] = "PASS" if (close([width,length],[88.2,38.2])
        and close(lands,[65.5]*4) and close(outer_top-lands[0],2.5)
        and close(lens[0]["diameters"],[p['LENS_WINDOW_D']+2*(p['DECK_T']-3)*slope]*2,0.006)
        and all(r['status']=='PASS' for r in window_sections)
        and close(lens[0]["centre"],[p["LENS_OFFSET_X"],p["CAMERA_Y"]+p["LENS_OFFSET_Y"]])) else "FAIL"
    return measured


def dimension_checks(meshes,p):
    rail = meshes["upright_300"]
    circles = circle_sections(rail,2,7.13)
    # Transform measured printed centres to table coordinates. Base bolts are separate.
    holes = sorted([[c["centre"][0]-p["UPRIGHT_WIDTH"]/2,
                     p["RAIL_LENGTH"]-c["centre"][1]+p["RAIL_BOTTOM_Z"]] for c in circles],key=lambda c:c[1])
    height_holes = np.array(holes[2:])
    pitch = np.diff(height_holes[:,1])
    rail_ok = (len(circles)==17 and len(height_holes)==15 and close(height_holes[:,0],0)
        and close(pitch,15) and close(height_holes[:,1],np.arange(77.5,287.6,15))
        and all(close(c["diameters"],[6.8,6.8]) for c in circles)
        and close(rail.extents,[36,300,14]))
    bar = meshes["crossbar"]
    bar_circles = circle_sections(bar,2,9.13)
    bar_ok = len(bar_circles)==4
    measured_posts = []
    for x in sorted({round(c["centre"][0],3) for c in bar_circles}):
        ys = sorted(c["centre"][1] for c in bar_circles if abs(c["centre"][0]-x)<0.001)
        bar_ok &= len(ys)==2 and close(ys[1]-ys[0],45)
        measured_posts.append(x-bar.extents[0]/2)
    portal_clear = measured_posts[1]-measured_posts[0]-rail.extents[0]
    bar_ok &= close(bar.extents,[232,61,18]) and close(portal_clear,160)
    slot_loops = [q for q in section_loops(bar,2,9.13) if close(np.ptp(q,axis=0),[66.8,6.8])]
    bar_ok &= len(slot_loops)==2
    base_rows = {}
    for name in ["base_left","base_right"]:
        holes_base = circle_sections(meshes[name],2,5.13)
        xs = sorted({round(c["centre"][0],3) for c in holes_base})
        ys = sorted({round(c["centre"][1],3) for c in holes_base})
        ok = len(holes_base)==4 and len(xs)==2 and len(ys)==2 and close([xs[1]-xs[0],ys[1]-ys[0]],[50,48])
        ok &= all(close(c["diameters"],[6.5,6.5]) for c in holes_base)
        base_rows[name] = {"holes":holes_base,"spacing_xy_mm":[xs[1]-xs[0],ys[1]-ys[0]],"status":"PASS" if ok else "FAIL"}
    deck = deck_dimensions(original_deck(meshes["camera_deck"],p),p)
    coupon = deck_dimensions(original_deck(meshes["camera_deck_fit_coupon"],p,True),p)
    positions=[]
    measured_hole_z = height_holes[:,1]
    measured_bar_bolt_z = bar.extents[1]-max(c["centre"][1] for c in bar_circles)
    for i in range(2,13):
        z0,z1=measured_hole_z[i-1],measured_hole_z[i+2]
        support_z=z0-measured_bar_bolt_z+deck["contact_land_z_mm"][0]
        positions.append({"lower_index":i,"upper_index":i+3,"lower_bolt_z_mm":float(z0),
            "upper_bolt_z_mm":float(z1),"table_to_crossbar_bottom_mm":float(z0-measured_bar_bolt_z),
            "table_to_deck_support_mm":float(support_z),"bolts_per_side":2,
            "left_right_pattern":"same STL, same hole pair", "status":"PASS" if close(z1-z0,45) else "FAIL"})
    support=[r["table_to_deck_support_mm"] for r in positions]
    heights_ok=close(support,np.arange(150,301,15)) and all(r["status"]=="PASS" for r in positions)
    return {"upright":{"height_holes_xz_mm":height_holes.tolist(),"pitch_mm":pitch.tolist(),
                "bore_diameter_mm":circles[0]["diameters"],"bore_web_mm":float(pitch.min()-circles[0]["diameters"][0]),
                "side_material_mm":float((rail.extents[0]-circles[0]["diameters"][0])/2),
                "entry_chamfer_d_mm":8,"entry_surface_web_mm":7,
                "status":"PASS" if rail_ok else "FAIL"},
            "crossbar":{"hole_sections":bar_circles,"horizontal_slots":len(slot_loops),
                "extent_mm":bar.extents.tolist(),"portal_inner_clear_mm":float(portal_clear),
                "status":"PASS" if bar_ok else "FAIL"}, "bases":base_rows,
            "camera_deck":deck,"camera_deck_coupon":coupon,"height_positions":positions,
            "height_range_status":"PASS" if heights_ok else "FAIL",
            "status":"PASS" if rail_ok and bar_ok and heights_ok and deck["status"]==coupon["status"]=="PASS"
                and all(r["status"]=="PASS" for r in base_rows.values()) else "FAIL"}


def empty_check(exe,temp,kind,index,slide):
    path=temp/f"{kind}_index{index}_slide{slide}.stl"
    result,log=run_cad(exe,path,kind,{"LOWER_INDEX":index,"CAMERA_SLIDE":slide})
    ok="Current top level object is empty" in log and not path.exists() and "ERROR:" not in log and "WARNING:" not in log
    return {"kind":kind,"lower_index":index,"slide_mm":slide,"exit_code":result.returncode,
            "empty_intersection":ok,"status":"PASS" if ok else "FAIL"}


def bounds_checks(meshes,refs,p,dimensions):
    """Exact separation proof using actual STL bounds; touching mating faces allowed.

    Positive AABB separation guarantees no penetration, without expensive CSG.
    Invert the documented print transforms before positioning exported parts.
    """
    rail=meshes["upright_300"].copy()
    v=rail.vertices.copy()
    rail.vertices=np.column_stack([v[:,0]-18,v[:,2]-14,300-v[:,1]+10])
    bar=meshes["crossbar"].copy()
    v=bar.vertices.copy()
    bar.vertices=np.column_stack([v[:,0]-116,v[:,2],61-v[:,1]])
    deck=original_deck(meshes["camera_deck"],p)
    left=meshes["base_left"].bounds+[-62-98,-40,0]
    right=meshes["base_right"].bounds+[-18+98,-40,0]
    fixed={"base_left":left,"base_right":right,"rail_left":rail.bounds+[-98,0,0],"rail_right":rail.bounds+[98,0,0]}
    rows=[]
    for position in dimensions["height_positions"]:
        z=position["table_to_crossbar_bottom_mm"]
        for slide in [-30,0,30]:
            solids={**fixed,"crossbar":bar.bounds+[0,0,z],"deck":deck.bounds+[slide,0,z]}
            body=refs["camera_body_reference"].bounds+[slide,0,z]
            cable_mesh=refs.get(f'cable_reference_{slide}',refs['cable_reference'])
            cable=cable_mesh.bounds+[slide,0,z]
            pairs=[]
            pairs += [("conveyor/"+n,refs["conveyor_reference"].bounds,b,False) for n,b in solids.items()]
            pairs += [("motor/"+n,refs["motor_reference"].bounds,b,False) for n,b in {**solids,"camera":body,"cable":cable}.items()]
            segment_boxes=optical_validation.cable_segment_boxes(p,slide,z)
            assert optical_validation.cable_boxes_cover_mesh(cable_mesh,segment_boxes-[slide,0,z])
            pairs += [(f'cable_segment{k}/'+n,a,b,False) for k,a in enumerate(segment_boxes) for n,b in solids.items()]
            pairs += [("bar/"+n,solids["crossbar"],solids[n],True) for n in ["rail_left","rail_right"]]
            pairs += [("deck/bar",solids["deck"],solids["crossbar"],True)]
            pairs += [("camera/"+n,body,b,False) for n,b in solids.items() if n!="deck"]
            gaps={}
            passed=True
            for name,a,b,touch in pairs:
                gap=float(np.max(np.maximum(a[0]-b[1],b[0]-a[1])))
                ok=gap>=-0.00001 if touch else gap>0.00001
                gaps[name]=round(gap,6)
                passed &= ok
            rows.append({"lower_index":position["lower_index"],"slide_mm":slide,
                "axis_separation_mm":gaps,"status":"PASS" if passed else "FAIL"})
    return {"method":"actual STL AABB separation; nonnegative permitted only at designated mating faces",
        "configurations":rows,"pair_checks":sum(len(r["axis_separation_mm"]) for r in rows),
        "status":"PASS" if all(r["status"]=="PASS" for r in rows) else "FAIL"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad",default="C:/Program Files/OpenSCAD/openscad.com")
    parser.add_argument("--mesh-only",action="store_true")
    args=parser.parse_args()
    for name in ["stl","preview","validation"]:
        (ROOT/name).mkdir(parents=True,exist_ok=True)
    began=time.time()
    version=subprocess.run([args.openscad,"--version"],capture_output=True,text=True,check=True)
    report={"task":"HARDWARE-CAD-003","machine":"Windows PC","units":"mm",
        "source_sha256":sha(SOURCE),"validator_sha256":sha(Path(__file__)),
        "optical_validator_sha256":sha(ROOT/'optical_validation.py'),
        "openscad":(version.stdout+version.stderr).strip(),"python":platform.python_version(),
        "numpy":np.__version__,"trimesh":trimesh.__version__,"parts":[],"collision_checks":[]}
    report['status']='IN_PROGRESS'
    (ROOT/'validation/stl_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tests=subprocess.run([sys.executable,'-m','unittest','test_optical_validation','-v'],cwd=ROOT,capture_output=True,text=True,timeout=30)
    (ROOT/'validation/optical_predicate_tests.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    report['optical_predicate_tests']={'exit_code':tests.returncode,'status':'PASS' if tests.returncode==0 else 'FAIL'}
    if tests.returncode:
        raise RuntimeError(tests.stdout+tests.stderr)
    meshes={}
    for name,quantity in PARTS.items():
        path=ROOT/"stl"/(name+".stl")
        result,log=run_cad(args.openscad,path,name,extra=["--export-format","binstl"])
        if result.returncode or "ERROR:" in log or "WARNING:" in log:
            raise RuntimeError(f"{name}: {log}")
        mesh=trimesh.load_mesh(path,process=True)
        checks=mesh_checks(mesh)
        meshes[name]=mesh
        row={"file":f"stl/{name}.stl","quantity":quantity,"sha256":sha(path),"bytes":path.stat().st_size,
            "vertices":len(mesh.vertices),"faces":len(mesh.faces),"volume_mm3":float(mesh.volume),
            "extents_mm":mesh.extents.tolist(),"bounds_mm":mesh.bounds.tolist(),"checks":checks,
            "status":"PASS" if all(checks.values()) else "FAIL"}
        report["parts"].append(row)
        print(name,row["status"],row["extents_mm"],flush=True)
    p=constants()
    report["dimensions"]=dimension_checks(meshes,p)
    print("dimensions",report["dimensions"]["status"],flush=True)
    with tempfile.TemporaryDirectory(prefix="cad-v3-check-") as folder:
        temp=Path(folder).resolve()
        refs={}
        for name in ["camera_body_reference","conveyor_reference","motor_reference","cable_reference",
                     'strap_reference','cable_tail_reference','rail_fasteners_reference',
                     'deck_fasteners_reference','base_fasteners_reference','table_fasteners_reference','fov_reference']:
            path=temp/(name+".stl")
            result,log=run_cad(args.openscad,path,name,{'LOWER_INDEX':12} if name=='cable_tail_reference' else None)
            if result.returncode or "ERROR:" in log or "WARNING:" in log:
                raise RuntimeError(log)
            refs[name]=trimesh.load_mesh(path)
            assert refs[name].is_watertight and refs[name].is_winding_consistent, name
        for slide in [-30,30]:
            path=temp/f'cable_reference_{slide}.stl'
            result,log=run_cad(args.openscad,path,'cable_reference',{'CAMERA_SLIDE':slide})
            if result.returncode:
                raise RuntimeError(log)
            refs[f'cable_reference_{slide}']=trimesh.load_mesh(path)
        body_mesh=refs["camera_body_reference"]
        report["camera_body_reference"]={"extents_mm":body_mesh.extents.tolist(),
            "status":"PASS" if close(body_mesh.extents,[87,37,33]) else "FAIL"}
        report["collision_bounds"]=bounds_checks(meshes,refs,p,report["dimensions"])
        print("collision_bounds",report["collision_bounds"]["status"],flush=True)
        report['optical_fov']=optical_validation.check_all(meshes,refs,p,report['dimensions'],original_deck)
        report['optical_fov']['lens_window']=report['dimensions']['camera_deck']
        print('optical_fov',report['optical_fov']['status'],flush=True)
        offset=temp/"offset_coupon.stl"
        result,log=run_cad(args.openscad,offset,"camera_deck_fit_coupon",{"LENS_OFFSET_X":2,"LENS_OFFSET_Y":1},['--export-format','binstl'])
        if result.returncode:
            raise RuntimeError(log)
        offset_mesh=original_deck(trimesh.load_mesh(offset),p,True)
        lens=[c for c in circle_sections(offset_mesh,2,63.173) if c["diameters"][0]>20][0]
        report["offset_parameter_smoke"]={"measured_window":lens,"status":"PASS" if close(lens["centre"],[2,p['CAMERA_Y']+1]) else "FAIL"}
        if not args.mesh_only:
            for index,slide in [(2,-30),(7,0),(12,30)]:
                for kind in ["collision_hardware"]:
                    row=empty_check(args.openscad,temp,kind,index,slide)
                    report["collision_checks"].append(row)
                    print(kind,index,slide,row["status"],flush=True)
            for kind in ["collision_base_rail","collision_body_deck","collision_lens"]:
                row=empty_check(args.openscad,temp,kind,7,0)
                report["collision_checks"].append(row)
                print(kind,row["status"],flush=True)
            row=empty_check(args.openscad,temp,'collision_optical_deck',2,0)
            report['collision_checks'].append(row)
            print('collision_optical_deck',row['status'],flush=True)
    report["previews"]=[]
    for label,index,slide in [('low',2,0),('mid',7,0),('high',12,0),('low_left',2,-30),('low_right',2,30)]:
        path=ROOT/"preview"/f"fov_{label}.png"
        result,log=run_cad(args.openscad,path,"assembly",{"LOWER_INDEX":index,'CAMERA_SLIDE':slide},
            ["--imgsize=1400,1100","--autocenter","--viewall","--projection=o","--camera=0,0,150,64,0,210,700"])
        report["previews"].append({"file":f"preview/{path.name}","lower_index":index,"sha256":sha(path) if path.exists() else None,
            "status":"PASS" if result.returncode==0 and path.exists() else "FAIL"})
    report["print_bed_review"]={"upright_flat_xy_mm":meshes["upright_300"].extents[:2].tolist(),
        "upright_45_degree_bounding_square_mm":float(sum(meshes["upright_300"].extents[:2])/np.sqrt(2)),
        "220_square_bed":"DOES_NOT_FIT upright flat outline", "250_square_bed":"geometric diagonal candidate only; slicer/brim/machine clearance unverified"}
    report["limitations"]=["No physical print, strength, vibration or PETG creep tests",
        "Lens centre/ring/protrusion and cable route are estimated references",
        "Conveyor table datum and motor full envelope unmeasured",
        "Belt-to-lens and optical focus/FOV derived after physical measurement",
        "Camera insertion/stand/microphone/pad fit requires coupon",
        "Collision checks cover listed references and poses, not unknown real equipment",
        "300 mm means table to unpadded deck contact lands, not total assembly height"]
    checks=[all(r["status"]=="PASS" for r in report["parts"]),report["dimensions"]["status"]=="PASS",
        report["camera_body_reference"]["status"]=="PASS",report["offset_parameter_smoke"]["status"]=="PASS",
        report["collision_bounds"]["status"]=="PASS",
        report['optical_fov']['status']=='PASS',
        len(report["collision_checks"])==7,all(r["status"]=="PASS" for r in report["collision_checks"]),
        all(r["status"]=="PASS" for r in report["previews"])]
    report["status"]="PASS" if all(checks) else "FAIL"
    report["duration_seconds"]=round(time.time()-began,2)
    (ROOT/"validation/stl_validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("FINAL",report["status"],flush=True)
    return 0 if report["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())

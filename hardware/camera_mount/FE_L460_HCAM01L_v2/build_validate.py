"""Rebuild real STL files with OpenSCAD and audit meshes without the ML venv.

Run using tools/cad/.venv/Scripts/python.exe. Only numpy/trimesh are required.
Geometry failures remain failures; this script does not repair meshes silently.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
import time

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent
SCAD = ROOT / "src/FE_L460_HCAM01L_v2.scad"
PARTS = {
    "upright": 2, "clamp_body": 1, "clamp_body_left": 1, "clamp_jaw": 2, "crossbar": 1,
    "camera_carriage": 1, "camera_mount_plate": 1,
    "camera_cradle_HCAM01L": 1, "clamp_fit_coupon": 1,
    "clamp_fit_coupon_jaw": 1, "camera_mount_fit_coupon": 1,
}


def run_cad(exe, output, part, extra=()):
    command = [exe, "-o", str(output), "-D", f'PART="{part}"', *extra, str(SCAD)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    log = result.stdout + result.stderr
    (ROOT / "validation" / (output.stem + ".txt")).write_text(log, encoding="utf-8")
    return result, log


def constants():
    text = SCAD.read_text(encoding="utf-8")
    return {k: float(v) for k, v in re.findall(r"^([A-Z_0-9]+)\s*=\s*([0-9.]+)\s*;", text, re.M)}


def mesh_result(path):
    mesh = trimesh.load_mesh(path, process=True)
    # Face adjacency connected components, using only numpy (no scipy/networkx).
    parents = np.arange(len(mesh.faces))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in mesh.face_adjacency:
        parents[find(a)] = find(b)
    components = len({find(i) for i in range(len(parents))})
    checks = {
        "nonempty": len(mesh.vertices) > 0 and len(mesh.faces) > 0,
        "positive_volume": bool(mesh.volume > 0),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "one_connected_component": components == 1,
        "finite_positive_bounds": bool(np.isfinite(mesh.bounds).all() and (mesh.extents > 0).all()),
        "bed_z_zero": bool(abs(mesh.bounds[0, 2]) < 0.002),
    }
    filename = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name
    return {"file": str(filename).replace("\\", "/"),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file_bytes": path.stat().st_size, "vertices": len(mesh.vertices),
            "faces": len(mesh.faces), "volume_mm3": float(mesh.volume),
            "bounds_mm": mesh.bounds.tolist(), "extents_mm": mesh.extents.tolist(),
            "components": components, "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL"}


def ray_hit(mesh, point, direction):
    """Nearest triangle hit using numpy only; independent of SCAD cavity subtraction."""
    triangles = mesh.triangles
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    direction = np.array(direction, dtype=float)
    cross = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
    determinant = np.einsum("ij,ij->i", edge1, cross)
    good = abs(determinant) > 1e-9
    inverse = np.zeros_like(determinant)
    inverse[good] = 1 / determinant[good]
    offset = np.array(point) - triangles[:, 0]
    u = np.einsum("ij,ij->i", offset, cross) * inverse
    q = np.cross(offset, edge1)
    v = np.einsum("j,ij->i", direction, q) * inverse
    distance = np.einsum("ij,ij->i", edge2, q) * inverse
    good &= (u >= -1e-7) & (v >= -1e-7) & (u+v <= 1+1e-7) & (distance > 1e-7)
    return float(distance[good].min()) if good.any() else None


def trig_min(a, b):
    """Exact interval extrema of a*cos(angle)+b*sin(angle), -15..30 degrees."""
    lo, hi = np.deg2rad([-15,30])
    candidates = [lo, hi]
    for k in range(-2,3):
        stationary = np.arctan2(b,a) + k*np.pi
        if lo <= stationary <= hi:
            candidates.append(stationary)
    return min(a*np.cos(t)+b*np.sin(t) for t in candidates)


def rotated_box_min(y_range, z_range, axis):
    return min(trig_min(y,-z) if axis=="y" else trig_min(z,y)
               for y in y_range for z in z_range)


def empty_intersection(exe, name, part, definitions):
    output = ROOT / "validation" / (name + ".stl")
    # Old positive evidence must never mask an empty or failed new operation.
    if output.exists():
        output.unlink()
    args = []
    for key, value in definitions.items():
        args += ["-D", f"{key}={value}"]
    result, log = run_cad(exe, output, part, args)
    empty = "Current top level object is empty" in log
    passed = empty and not output.exists() and "ERROR:" not in log and "WARNING:" not in log
    return {"name": name, "parameters": definitions, "empty_intersection": empty,
            "exit_code": result.returncode, "status": "PASS" if passed else "FAIL"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="C:/Program Files/OpenSCAD/openscad.com")
    parser.add_argument("--skip-export", action="store_true", help="Audit existing files only")
    parser.add_argument("--skip-csg", action="store_true", help="Diagnostic mode, not full acceptance")
    args = parser.parse_args()
    for folder in ["stl", "preview", "validation"]:
        (ROOT / folder).mkdir(exist_ok=True)
    version = subprocess.run([args.openscad, "--version"], capture_output=True, text=True, check=True)
    report = {"task": "HARDWARE-CAD-001", "units": "mm", "machine": "Windows PC",
              "python": platform.python_version(), "openscad": (version.stdout+version.stderr).strip(),
              "numpy": np.__version__, "trimesh": trimesh.__version__,
              "source_sha256": hashlib.sha256(SCAD.read_bytes()).hexdigest(),
              "print_parts": [], "csg_checks": [], "parameter_smoke": []}
    started = time.time()
    for name, quantity in PARTS.items():
        path = ROOT / "stl" / (name + ".stl")
        if not args.skip_export:
            result, log = run_cad(args.openscad, path, name, ["--export-format", "binstl"])
            if result.returncode or "ERROR:" in log or "WARNING:" in log:
                raise RuntimeError(f"{name} export failed: {log}")
        row = mesh_result(path)
        row["quantity"] = quantity
        report["print_parts"].append(row)
        print(name, row["status"], row["extents_mm"], flush=True)
    p = constants()
    # Re-check mirrored print orientation at both supported lip limits.
    with tempfile.TemporaryDirectory(prefix="cad-lip-check-") as folder:
        temp_root = Path(folder).resolve()
        for lip in [22, 40]:
            path = temp_root / f"clamp_left_lip_{lip}.stl"
            assert path.resolve().is_relative_to(temp_root)
            result, log = run_cad(args.openscad, path, "clamp_body_left",
                ["--export-format", "binstl", "-D", f"FRAME_LIP_DEPTH={lip}"])
            if result.returncode or "ERROR:" in log or "WARNING:" in log:
                raise RuntimeError(f"Parametric lip {lip} export failed: {log}")
            row = mesh_result(path)
            row["FRAME_LIP_DEPTH"] = lip
            row["temporary_export"] = True
            row["width_matches_parameter"] = abs(row["extents_mm"][2]-(lip+22))<0.002
            if not row["width_matches_parameter"]:
                row["status"] = "FAIL"
            report["parameter_smoke"].append(row)
            print("clamp_left_lip", lip, row["status"], flush=True)
    bar = next(r for r in report["print_parts"] if r["file"].endswith("/crossbar.stl"))
    c = p["CAMERA_CLEARANCE"]
    report["dimensions"] = {
        "camera_confirmed_WHD_mm": [p[k] for k in ["CAMERA_W", "CAMERA_H", "CAMERA_D"]],
        "cradle_internal_WHD_mm": [p[k]+c for k in ["CAMERA_W", "CAMERA_H", "CAMERA_D"]],
        "per_side_clearance_mm": c/2,
        "crossbar_length_mesh_mm": bar["extents_mm"][0],
        "crossbar_length_matches_source": abs(bar["extents_mm"][0]-p["CROSSBAR_LENGTH"])<0.002,
        "body_front_datum_height_mm": [p[k]-12+p["PIVOT_Z"]+p["CAMERA_Z"]-p["CAMERA_D"]/2 for k in ["HEIGHT_LOWER", "HEIGHT_UPPER"]],
        "lens_working_distance": "UNVERIFIED: actual belt/frame/lens offset unknown",
    }
    cradle_mesh = trimesh.load_mesh(ROOT/"stl/camera_cradle_HCAM01L.stl")
    centre = (p["CAMERA_W"]+c+2*p["CRADLE_WALL"])/2
    left = ray_hit(cradle_mesh,[centre,20,20],[-1,0,0])
    right = ray_hit(cradle_mesh,[centre,20,20],[1,0,0])
    floor = 20-ray_hit(cradle_mesh,[centre,20,20],[0,0,-1])
    rear = 20-ray_hit(cradle_mesh,[centre,20,14],[0,-1,0])
    front_open = ray_hit(cradle_mesh,[centre,20,20],[0,1,0]) is None
    geometry = {"inner_width_ray_mm": left+right, "floor_z_ray_mm": floor,
        "rear_y_ray_mm": rear, "inner_wall_height_mm": float(cradle_mesh.bounds[1,2]-floor),
        "open_depth_mm": float(cradle_mesh.bounds[1,1]-rear), "front_open_ray": front_open,
        "csg_gauge_boundary_inset_mm": p["GAUGE_EPS"]}
    geometry["status"] = "PASS" if (abs(left+right-(p["CAMERA_W"]+c))<0.002
        and abs(floor-10)<0.002 and abs(rear-p["CRADLE_WALL"])<0.002 and front_open
        and abs(geometry["inner_wall_height_mm"]-(p["CAMERA_H"]+c))<0.002
        and abs(geometry["open_depth_mm"]-(p["CAMERA_D"]+c))<0.002) else "FAIL"
    report["camera_fit_geometry"] = geometry
    # Conservative disjoint bounds for far obstacles, including interior extrema.
    body_y_min = p["PLATE_FRONT"]+p["FOLDED_STAND_GAP"]-p["PIVOT_Y"]
    rectangles = [([p["PLATE_BACK"]-p["PIVOT_Y"],p["PLATE_FRONT"]-p["PIVOT_Y"]],[-14,42]),
                  ([0,p["PLATE_FRONT"]-p["PIVOT_Y"]],[-14,14]),
                  ([body_y_min,body_y_min+p["CAMERA_H"]],
                   [p["CAMERA_Z"]-p["CAMERA_D"]/2,p["CAMERA_Z"]+p["CAMERA_D"]/2])]
    moving_min_y = p["PIVOT_Y"]+min([-16]+[rotated_box_min(y,z,"y") for y,z in rectangles])
    moving_min_z = p["HEIGHT_LOWER"]-12+p["PIVOT_Z"]+min([-16]+[rotated_box_min(y,z,"z") for y,z in rectangles])
    report["fixed_structure_bounds"] = {
        "bar_post_y_clearance_mm": float(moving_min_y-18),
        "clamp_z_clearance_mm": float(moving_min_z-48),
        "scope": "All configured heights/slides and tilt -15..30; excludes unmeasured stand/cable/bolts",
        "status": "PASS" if moving_min_y>18 and moving_min_z>48 else "FAIL"}
    # Fallback fasteners: conservative M6 nut radius6, external washer t1.6/OD18.
    # Nut and washer occupy different Y intervals; do not collapse them into one box.
    nut_x_gap = p["CRADLE_FIX_X"]-6-(p["HINGE_GAP"]/2+8)
    washer_relative_y = p["PLATE_BACK"]-1.6-p["PIVOT_Y"]
    washer_low_z = p["PLATE_SLOT_Z"]-9
    washer_radial_gap = np.hypot(washer_relative_y,washer_low_z)-12
    washer_low_swept_z = rotated_box_min([washer_relative_y,p["PLATE_BACK"]-p["PIVOT_Y"]],
                                         [washer_low_z,p["PLATE_SLOT_Z"]+9],"z")
    fork_root_top = max(0,42+5-p["PIVOT_Z"])
    report["fallback_fastener_clearance"] = {
        "nut_to_fork_x_mm": nut_x_gap, "washer_to_fork_radial_mm": float(washer_radial_gap),
        "washer_min_swept_z_above_pivot_mm": float(washer_low_swept_z),
        "washer_to_fork_root_z_mm": float(washer_low_swept_z-fork_root_top),
        "scope": "Tilt -15..30, M6 nut radius <=6, washer thickness <=1.6/OD<=18; actual camera screw unmeasured",
        "status": "PASS" if nut_x_gap>0 and washer_radial_gap>0 and washer_low_swept_z>fork_root_top else "FAIL"}
    if not args.skip_csg:
        report["csg_checks"].append(empty_intersection(args.openscad,"cradle_clearance", "clearance_intersection", {}))
        for tilt in [-15, 0, 30]:
            for height, slide in [(84,-50), (84,50), (184,-50), (184,50)]:
                report["csg_checks"].append(empty_intersection(args.openscad,
                    f"tilt_{tilt}_height_{height}_slide_{slide}", "tilt_intersection",
                    {"TILT": tilt, "HEIGHT_POSITION": height, "CAMERA_SLIDE": slide}))
                print(report["csg_checks"][-1]["name"], report["csg_checks"][-1]["status"], flush=True)
    preview, log = run_cad(args.openscad, ROOT/"preview/assembly_preview.png", "assembly",
        ["--imgsize=1500,1100", "--autocenter", "--viewall", "--projection=o", "--camera=0,60,90,65,0,208,540"])
    report["assembly_preview"] = {"exit_code": preview.returncode,
        "exists": (ROOT/"preview/assembly_preview.png").exists()}
    report["duration_seconds"] = round(time.time()-started, 2)
    report["limitations"] = ["No physical print or FE-L460 fit test", "No load/creep/vibration qualification",
        "Folded stand/cable/insert positions are unmeasured", "CSG collision checks cover listed sample poses only",
        "Belt plane and camera lens position are reference assumptions", "STL mesh validity is not slicer or printer qualification"]
    report["status"] = "PASS" if (all(r["status"]=="PASS" for r in report["print_parts"])
        and len(report["parameter_smoke"])==2 and all(r["status"]=="PASS" for r in report["parameter_smoke"])
        and len(report["csg_checks"])==13 and all(r["status"]=="PASS" for r in report["csg_checks"])
        and report["dimensions"]["crossbar_length_matches_source"]
        and report["camera_fit_geometry"]["status"]=="PASS"
        and report["fixed_structure_bounds"]["status"]=="PASS"
        and report["fallback_fastener_clearance"]["status"]=="PASS") else "FAIL"
    (ROOT/"validation/stl_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FINAL", report["status"], flush=True)
    return 0 if report["status"]=="PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

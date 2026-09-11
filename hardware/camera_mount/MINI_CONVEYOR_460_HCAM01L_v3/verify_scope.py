"""Read-only audit of protected repository files and the retained ML snapshot."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
PREFIX=ROOT.relative_to(REPO).as_posix()+"/"
BASELINE="95886b5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    changed=subprocess.check_output(["git","diff","--name-only",BASELINE],cwd=REPO,text=True).splitlines()
    unrelated=[p for p in changed if not p.startswith(PREFIX) and p!="docs/learning-notes/HARDWARE-CAD-002.md"]
    snapshot=json.loads((REPO/"runs/t04-preservation-before.json").read_text(encoding="utf-8"))
    mismatches=[p for p,h in snapshot["files"].items() if not (REPO/p).exists() or sha(REPO/p)!=h]
    program='import importlib.metadata as m,json; print(json.dumps(sorted((d.metadata["Name"],d.version) for d in m.distributions())))'
    packages=json.loads(subprocess.check_output([str(REPO/".venv/Scripts/python.exe"),"-c",program],text=True))
    v2=REPO/"hardware/camera_mount/FE_L460_HCAM01L_v2"
    old=json.loads((v2/"validation/stl_validation.json").read_text(encoding="utf-8"))
    v2_errors=[r["file"] for r in old["print_parts"] if sha(v2/r["file"])!=r["sha256"]]
    task=(REPO/"tasks/v0-t05-labeling-validation.md").read_text(encoding="utf-8")
    result={"baseline":BASELINE,"unrelated_tracked_changes":unrelated,
        "protected_file_hashes_checked":len(snapshot["files"]),"protected_file_mismatches":mismatches,
        "ml_distribution_count":len(packages),"ml_packages_match_retained_snapshot":packages==snapshot["packages"],
        "v2_stl_hashes_checked":len(old["print_parts"]),"v2_stl_mismatches":v2_errors,
        "v0_t05_todo":"Status: TODO" in task,"jetson_access":False,"camera_access":False,"training":False,
        "user_photo_zip_and_directory":"preserved outside new CAD folder; excluded from CAD commit"}
    passed=not unrelated and not mismatches and not v2_errors and packages==snapshot["packages"] and result["v0_t05_todo"]
    result["status"]="PASS" if passed else "FAIL"
    (ROOT/"validation/scope_verification.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())

"""Read-only target probe. Run on Jetson; missing modules are not GPU verdicts."""

import importlib
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path


def command(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15)
        return {"exit_code": result.returncode, "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"error": str(error)}


def probe():
    report = {"hostname": platform.node(), "machine": platform.machine(),
              "platform": platform.platform(), "python": platform.python_version(),
              "python_executable": __import__("sys").executable,
              "disk_free_bytes": shutil.disk_usage(Path.home()).free}
    for filename in ("/etc/nv_tegra_release", "/etc/os-release", "/proc/meminfo",
                     "/proc/device-tree/model"):
        path = Path(filename)
        report[filename] = path.read_text().strip("\x00\n") if path.exists() else None
    for name in ("torch", "torchvision", "ultralytics", "tensorrt", "cv2"):
        try:
            module = importlib.import_module(name)
            report[name] = {"version": getattr(module, "__version__", None),
                            "file": getattr(module, "__file__", None)}
            if name == "torch":
                report[name]["cuda_build"] = module.version.cuda
                report[name]["cuda_available"] = module.cuda.is_available()
                if module.cuda.is_available():
                    started = time.perf_counter()
                    value = module.ones((64, 64), device="cuda")
                    answer = value @ value
                    module.cuda.synchronize()
                    report[name]["cuda_execution"] = {
                        "device": str(answer.device), "gpu": module.cuda.get_device_name(0),
                        "finite": bool(module.isfinite(answer).all().item()),
                        "sum": float(answer.sum().item()),
                        "elapsed_ms": (time.perf_counter() - started) * 1000}
        except Exception as error:
            report[name] = {"error": f"{type(error).__name__}: {error}"}
    report["nvcc"] = command(["nvcc", "--version"])
    report["jetpack_packages"] = command(["dpkg-query", "-W", "nvidia-jetpack", "nvidia-l4t-core", "libnvinfer*"])
    report["camera_devices"] = command(["v4l2-ctl", "--list-devices"])
    report["camera_formats"] = {
        str(path): command(["v4l2-ctl", "-d", str(path), "--list-formats-ext"])
        for path in sorted(Path("/dev").glob("video*"))}
    return report


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))

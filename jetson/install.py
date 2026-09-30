"""Verify a downloaded checkout and install a new, stopped MOCK runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

from build_bundle import checked_file, collect_release

ROOT = Path(__file__).resolve().parent


def verify_source(source=ROOT):
    from src.recipe.package import load_package

    files, release, encoded = collect_release(source.parent)
    models = []
    for name in ('dynamic_parts_005', 'envelope_v007_fp16'):
        package = source / 'products/ENGINE_Z3005_5' / name
        load_package(package)
        model = package / 'model.plan'
        models.append({'package': name, 'bytes': model.stat().st_size,
                       'sha256': hashlib.sha256(model.read_bytes()).hexdigest()})
    pose_root = source / 'products/ENGINE_Z3005_5/dynamic_parts_005/pose'
    pose = json.loads((pose_root / 'pose_reference.json').read_text(encoding='utf-8'))
    for name, expected in ((pose['reference_image'], pose['reference_image_sha256']),
                           (pose['reference_bank']['path'], pose['reference_bank']['sha256'])):
        if hashlib.sha256(checked_file(pose_root, name).read_bytes()).hexdigest() != expected:
            raise ValueError('POSE_ASSET_HASH_MISMATCH: ' + name)
    return {'release_id': release['release_id'], 'files': len(files), 'models': models,
            'physical_output_enabled': False, 'hardware_execution': 'NOT_RUN'}


def device_settings(camera):
    if (not re.fullmatch(r'/dev/[A-Za-z0-9_./:-]+', camera)
            or '..' in Path(camera).parts):
        raise ValueError('Select an explicit /dev/videoN or /dev/v4l/by-id/... camera path')
    station = json.loads((ROOT / 'station.example.json').read_text(encoding='utf-8'))
    station['camera_device'] = camera
    runtime = {
        'package': '../assets/products/ENGINE_Z3005_5/dynamic_parts_005',
        'station': 'station.json', 'data_root': '../data', 'pythonpath': '../current',
        'port': 18771, 'plc_bench': False, 'mock_auto_request': True,
        'inspection_motion_mode': 'STATIONARY',
    }
    return station, runtime


def require_new_install(base):
    for name in ('current', 'assets', 'config', 'data'):
        path = base / name
        if path.exists() or path.is_symlink():
            raise FileExistsError('Existing installation/data preserved: ' + str(path))
    for path in (base, *base.parents):
        if path.is_symlink():
            raise ValueError('Install path must not contain symbolic links')
    for path in (base / 'envs', base / 'envs/app_v1'):
        if path.is_symlink():
            raise ValueError('Environment path must not be a symbolic link')


def install_layout(base, camera, source=ROOT):
    base = base.expanduser().absolute()
    require_new_install(base)
    station, runtime = device_settings(camera)
    verify_source(source)
    files, release, encoded = collect_release(source.parent)
    base.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.install-', dir=base))
    for name, original in files.items():
        content = original.read_bytes()
        if hashlib.sha256(content).hexdigest() != release['files'][name]:
            raise ValueError('SOURCE_CHANGED_DURING_INSTALL: ' + name)
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(content)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != release['files'][name]:
            raise ValueError('INSTALLED_FILE_HASH_MISMATCH: ' + name)
    (stage / 'current/release.json').write_bytes(encoded)
    (stage / 'current/config').symlink_to('../assets/runtime_config', target_is_directory=True)
    for name, value in (('station', station), ('runtime', runtime)):
        (stage / f'config/{name}.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    (stage / 'data').mkdir()
    subprocess.run([sys.executable, '-B', '-X', 'utf8', str(stage / 'current/launch_live.py'),
                    '--package', str(stage / runtime['package'][3:]),
                    '--station', str(stage / 'config/station.json'),
                    '--data-root', str(stage / 'data'), '--check-only'], check=True)
    require_new_install(base)
    for name in ('assets', 'config', 'data', 'current'):
        (stage / name).rename(base / name)
    stage.rmdir()
    return {'release_id': release['release_id'], 'base': str(base),
            'backend': 'MOCK', 'runtime_started': False, 'physical_output_enabled': False}


def check_environment():
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        raise RuntimeError('Runtime requires Linux aarch64 on Jetson Orin Nano')
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError('JetPack TensorRT bindings require the supported Python 3.10 environment')
    board = Path('/proc/device-tree/model').read_text().strip('\0\n')
    if 'Orin Nano' not in board:
        raise RuntimeError('This release is qualified for Jetson Orin Nano only: ' + board)
    import numpy
    import cv2
    import tensorrt
    import fastapi
    import uvicorn
    import PIL
    import gi

    if tensorrt.__version__.split('.')[:2] != ['10', '3']:
        raise RuntimeError('Bundled engines require TensorRT 10.3; rebuild/revalidate for other versions')
    if numpy.__version__.split('.')[0] != '1':
        raise RuntimeError('Use the pinned NumPy 1.26 environment for this runtime')
    from src.vision.cuda_runtime_ctypes import LIBCUDART
    if not Path(LIBCUDART).is_file():
        raise RuntimeError('Required JetPack CUDA runtime is missing: ' + LIBCUDART)
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gst, GstVideo
    Gst.init(None)
    for name in ('v4l2src', 'jpegdec', 'videoconvert', 'appsink'):
        if Gst.ElementFactory.find(name) is None:
            raise RuntimeError('Missing GStreamer plugin: ' + name)
    return {'board': board, 'numpy': numpy.__version__, 'opencv': cv2.__version__,
            'tensorrt': tensorrt.__version__, 'camera_opened': False, 'gpu_inference': 'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--environment-only', action='store_true')
    parser.add_argument('--base', type=Path, default=Path.home() / 'oned_device_bench')
    parser.add_argument('--camera')
    args = parser.parse_args()
    if args.check_only:
        result = verify_source()
        if args.camera:
            device_settings(args.camera)
            require_new_install(args.base.expanduser().absolute())
            if not Path(args.camera).exists():
                parser.error('Selected camera device does not exist')
    elif args.environment_only:
        result = check_environment()
    else:
        if not args.camera:
            parser.error('--camera is required; choose your actual camera with ls /dev/v4l/by-id/')
        check_environment()
        if not Path(args.camera).exists():
            parser.error('Selected camera device does not exist')
        result = install_layout(args.base, args.camera)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

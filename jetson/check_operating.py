"""새 장치 환경/저장 사진 GPU 호환성 점검. 카메라·PLC·원장은 열지 않는다."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from install import check_environment
from install_operating import verify_installed


def environment():
    result = check_environment()
    import torch
    import torchvision
    import ultralytics
    if not torch.cuda.is_available():
        raise RuntimeError('PYTORCH_CUDA_REQUIRED_NO_CPU_FALLBACK')
    boxes = torch.tensor([[0., 0., 2., 2.]], device='cuda')
    scores = torch.tensor([0.9], device='cuda')
    if torchvision.ops.nms(boxes, scores, 0.5).numel() != 1:
        raise RuntimeError('TORCHVISION_CUDA_NMS_FAILED')
    torch.cuda.synchronize()
    result.update(torch=torch.__version__, torchvision=torchvision.__version__,
                  ultralytics=ultralytics.__version__, cuda=torch.version.cuda,
                  gpu=torch.cuda.get_device_name(0), torch_cuda_execution=True)
    return result


def gpu_smoke(base):
    """묶인 모델 7개의 실제 장치 실행만 검증한다. 검사 정확도 시험은 아니다."""
    active = subprocess.run(['systemctl', 'is-active', 'engine-inspector.service'], capture_output=True, text=True)
    if active.stdout.strip() not in ('inactive', 'failed', 'unknown'):
        raise RuntimeError('STOP_EXISTING_SERVICE_BEFORE_GPU_SMOKE')
    release = verify_installed(base)
    sys.path.insert(0, str(base/'current'))
    from src.recipe.package import load_package
    from src.vision.detector_factory import create_detector
    from src.contracts import CameraFrame
    from src.vision.misassembly_shadow import verify_assets
    import cv2
    import torch
    from ultralytics import YOLO
    records = []
    for name in ('dynamic_parts_005', 'envelope_v007_fp16'):
        package = load_package(base/'assets/products/ENGINE_Z3005_5'/name)
        image = cv2.imread(str(package.root/'self_test.png'))
        if image is None:
            raise ValueError('SELF_TEST_IMAGE_UNREADABLE')
        frame = CameraFrame(image, 'INSTALL_SMOKE_'+name, datetime.now(timezone.utc),
                            image.shape[1], image.shape[0], 'stored_self_test_not_camera')
        detector = create_detector(package)
        try:
            result = detector.detect(frame)
            records.append({'model': name, 'backend': 'TensorRT CUDA', 'runtime': detector.runtime_metadata()})
        finally:
            detector.close()
    frozen = base/'assets/misassembly_runtime'
    manifest = verify_assets(frozen)
    for item in manifest['files']:
        if not item['relative_path'].endswith('.pt'):
            continue
        path = frozen/item['relative_path']
        model = YOLO(str(path))
        model.predict(image, imgsz=224 if model.task == 'classify' else 640, device=0,
                      verbose=False, save=False)
        torch.cuda.synchronize()
        records.append({'model':item['relative_path'], 'backend':'PyTorch CUDA', 'task':model.task})
        del model
    if len(records) != 7:
        raise ValueError('EXPECTED_SEVEN_MODELS')
    return {'release_id':release['release_id'], 'models':records,
            'scope':'MODEL_EXECUTION_COMPATIBILITY_ONLY', 'camera':'NOT_RUN', 'PLC':'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path.home()/'oned_device_bench')
    parser.add_argument('--gpu-smoke', action='store_true')
    args = parser.parse_args()
    result = {'environment':environment()}
    if args.gpu_smoke:
        result['gpu_smoke'] = gpu_smoke(args.base.expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

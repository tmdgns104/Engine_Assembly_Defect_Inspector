"""임시 검증 영상 재생. 기존 패키지와 실제 Detector/Worker는 그대로 사용한다.

영상은 manifest에 해시가 등록된 self_test만 허용한다. 재생 시계는 센서의 신선도를
증명하지 않으며 물리 Camera를 열지 않는다. 실제 촬영 모드의 기본 동작과 분리한다.
"""
from unittest.mock import patch

from src.contracts import CameraFrame
from src.recipe.package import load_package
from src.runtime.diagnostic_devices import DiagnosticCamera


def package_replay_worker_main(*args):
    import cv2
    from src.vision.inspection_worker import worker_main
    package=load_package(args[0])
    entry=package.manifest['files'].get('self_test')
    if entry is None:
        raise ValueError('PACKAGE_SELF_TEST_REPLAY_REQUIRES_HASHED_IMAGE')
    image=cv2.imread(str(package.root/entry['path']))
    if image is None:
        raise ValueError('PACKAGE_SELF_TEST_IMAGE_INVALID')

    class PackageReplayCamera(DiagnosticCamera):
        pipeline_text='TEMPORARY_PACKAGE_SELF_TEST_REPLAY sha256='+entry['sha256']

        def capture(self):
            clock=super().capture()
            self.frame_info['freshness_method']='REPLAY_DIAGNOSTIC_CLOCK_NOT_PHYSICAL'
            return CameraFrame(image.copy(),clock.frame_id,clock.captured_at,
                image.shape[1],image.shape[0],self.pipeline_text)

    # Camera만 교체한다. create_detector/TensorRT/quality/recipe/decision은 수정하지 않는다.
    with patch('src.camera.gstreamer_camera.GStreamerCamera',PackageReplayCamera):
        worker_main(*args)

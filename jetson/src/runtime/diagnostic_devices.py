"""CPU 전용 합성 장치. 기존 Worker를 실행하며 실제 장치 수용을 뜻하지 않는다.

기존 test_fresh_frame_worker의 Camera/DetectionResult 패턴을 장수 spawn에 적용한다.
검사·품질·판정·증거 인코딩·저장은 기존 구현을 그대로 실행한다.
"""
from datetime import datetime, timezone
import time
import uuid
from unittest.mock import patch

import numpy as np

from src.contracts import BoundingBox, CameraFrame, Detection, DetectionResult
from src.recipe.package import load_package


class DiagnosticCamera:
    pipeline_text = 'SYNTHETIC_CPU_CAMERA'

    def __init__(self, config):
        self.sequence = 0
        self.epoch = uuid.uuid4().hex
        self.frame_info = {}
        self.closed = False

    def capture(self):
        if self.closed:
            raise RuntimeError('DIAGNOSTIC_CAMERA_CLOSED')
        time.sleep(.01)
        self.sequence += 1
        now = time.monotonic()
        frame_id = f'{self.epoch}-{self.sequence}'
        captured = datetime.now(timezone.utc)
        self.frame_info = {'frame_id':frame_id,'camera_epoch':self.epoch,'sequence':self.sequence,
            'source_pts_ns':self.sequence*10_000_000,'received_monotonic':now,
            'estimated_source_monotonic':now,'age_seconds':0,'received_at':captured.isoformat(),
            'freshness_method':'SYNTHETIC_DIAGNOSTIC_CLOCK','sensor_exposure_timestamp_verified':False}
        image = np.full((100,100,3),127,dtype=np.uint8)
        return CameraFrame(image,frame_id,captured,100,100,'SYNTHETIC_CPU_CAMERA')

    def close(self):
        self.closed = True


class DiagnosticDetector:
    """합성 fixture 전용 고정 검출. 학습 모델이나 ENGINE 모델이 아니다."""
    def __init__(self, package):
        if package.manifest['product_id'] != 'integration-diagnostic':
            raise ValueError('DIAGNOSTIC_DEVICES_REQUIRE_DIAGNOSTIC_PACKAGE')
        self.closed = False

    def runtime_metadata(self):
        return {'backend':'mock','device':'cpu','label':'SYNTHETIC_DIAGNOSTIC_DETECTOR'}

    def detect(self, frame):
        if self.closed:
            raise RuntimeError('DIAGNOSTIC_DETECTOR_CLOSED')
        return DetectionResult(frame.frame_id,(
            Detection(1,'bolt',.95,BoundingBox(10,10,25,25)),
            Detection(2,'cover',.95,BoundingBox(65,10,80,25))), 'synthetic', 0.0)

    def close(self):
        self.closed = True


def diagnostic_worker_main(*args):
    """子 프로세스에서만 장치 두 개를 대체; 원본 Worker 호출 경로는 유지한다."""
    from src.vision.inspection_worker import worker_main
    with patch('src.camera.gstreamer_camera.GStreamerCamera',DiagnosticCamera), \
         patch('src.vision.detector_factory.create_detector',DiagnosticDetector):
        worker_main(*args)

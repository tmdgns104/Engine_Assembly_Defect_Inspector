"""후보 전용 오류 파일 로그. Runtime이 handler의 설치/해제를 한 번씩 소유한다."""
import logging
from pathlib import Path


class RuntimeLog:
    def __init__(self,data_root):
        self.path = Path(data_root).resolve()/'logs/runtime.log'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handler = logging.FileHandler(self.path,encoding='utf-8')
        self.handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        logging.getLogger().addHandler(self.handler)
        self.closed = False

    def close(self):
        if not self.closed:
            logging.getLogger().removeHandler(self.handler)
            self.handler.close()
            self.closed = True

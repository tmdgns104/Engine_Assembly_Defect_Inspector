"""Single-screen operator UI for the separate one-click collection policy."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import filedialog, ttk
import uuid

import cv2
from PIL import Image, ImageTk

from .camera import CameraClient, CameraSettings
from .misassembly import SimpleCollection, load_capture_plan
from .misassembly_guidance import (DEFAULT_BODY_ROI, PART_NAMES, ZERO_GUIDE,
                                   guide_geometry, render_guide)
from .wizard_quality import CaptureGate, WARNING_TEXT


def assets_folder():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / 'assets'
    return Path(__file__).resolve().parent / 'assets'


class MisassemblyApp:
    def __init__(self, root, *, home=None, camera=None, auto_start=True):
        self.root = root
        self.home = Path(home) if home else (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path.cwd())
        self.settings_path = self.home / 'misassembly-settings.json'
        self.plan = load_capture_plan(assets_folder() / 'misassembly-plan.json')
        self.camera = camera if camera is not None else CameraClient()
        self.collection = None
        self.blocked_folder = None
        self.gate = self.future = self.declaration = None
        self.future_phase = None
        self.cancel_preparation = False
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='misassembly-storage')
        self.closed = self.closing = self.space_down = False
        self.last_preview = 0.0
        self.pending_capture = None
        self.next_click_after = 0.0
        self.preview_box = self.drag_start = None
        self.setting_roi = False
        self.setup_panel_open = True
        self.setup_complete = False
        self.body_roi = list(DEFAULT_BODY_ROI)
        self.setup_window = None
        self.reconnect_settings = None
        self.last_camera_error = ''
        self.last_scenario = None
        self.last_step_id = None
        self.compact = False
        self.setup_revision = uuid.uuid4().hex[:8].upper()
        self.preview_image = self.normal_image = self.target_image = self.recent_image = None
        self.operator = tk.StringVar()
        self.output = tk.StringVar(value=str(self.home / 'data'))
        self.index = tk.StringVar(value='0')
        self.backend = tk.StringVar(value='DSHOW')
        self.resolution = tk.StringVar(value='1280x720')
        self.camera_text = tk.StringVar(value='미연결 · 카메라 설정에서 실제 영상을 확인하세요.')
        self.change_text = tk.StringVar(value='첫 조립 상태')
        self.status = tk.StringVar(value='촬영자·저장 폴더·카메라 후보를 설정하고 실제 영상을 확인하세요.')
        self.progress = tk.StringVar(value='저장 0 / 목표 ' + str(len(self.plan['steps'])))
        self.instruction = tk.StringVar()
        self.remaining = tk.StringVar()
        self.direction = tk.StringVar()
        self._load_settings()
        self._build()
        self._open_previous()
        self.refresh()
        if self.setup_complete:
            self.toggle_setup(False)
        if auto_start and self.setup_complete:
            self.connect()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(50, self.tick)

    def _load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            data = json.loads(self.settings_path.read_text(encoding='utf-8'))
            for key in ('operator', 'output', 'index', 'backend', 'resolution'):
                if key in data:
                    getattr(self, key).set(str(data[key]))
            self.body_roi = data.get('body_roi', list(DEFAULT_BODY_ROI))
            guide_geometry(self.body_roi, 'CENTER', 0, (1280, 720))
            self.setup_complete = data.get('setup_complete', False)
        except (OSError, ValueError, KeyError):
            self.status.set('이전 설정을 읽지 못했습니다. 카메라를 다시 선택하세요.')

    def _build(self):
        root = self.root
        root.title('엔진 오조립 추가 촬영')
        root.geometry('1240x820')
        root.minsize(960, 650)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', -14), background='#edf2f6')
        style.configure('TButton', padding=(10, 6))
        style.configure('Capture.TButton', font=('맑은 고딕', -23, 'bold'), padding=(20, 12), background='#146d94', foreground='white')
        style.map('Capture.TButton', background=[('active', '#195b7c'), ('disabled', '#9aabb8')])
        style.configure('Title.TLabel', font=('맑은 고딕', -22, 'bold'))
        style.configure('Hint.TLabel', foreground='#536b7c')
        root.configure(background='#edf2f6')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        header = tk.Frame(root, bg='#173653', padx=16, pady=9)
        header.grid(row=0, column=0, sticky='ew')
        tk.Label(header, text='엔진 오조립 촬영', bg='#173653', fg='white',
                 font=('맑은 고딕', -23, 'bold')).pack(side='left')
        ttk.Button(header, text='카메라 · 최초 설정', command=self.toggle_setup).pack(side='right')
        tk.Label(header, textvariable=self.progress, bg='#173653', fg='#dce8f3',
                 font=('맑은 고딕', -15)).pack(side='right', padx=20)
        self.progressbar = ttk.Progressbar(root, maximum=len(self.plan['steps']))
        self.progressbar.grid(row=1, column=0, sticky='ew')
        content = ttk.Frame(root, padding=(12, 8))
        content.grid(row=2, column=0, sticky='nsew')
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, minsize=310)
        content.rowconfigure(1, weight=1)
        self.setup = ttk.LabelFrame(content, text='처음 한 번: 카메라 연결 → 실제 영상 확인 → 구도 맞춤', padding=8)
        self.setup.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        self._build_setup(self.setup)
        live = ttk.Frame(content)
        live.grid(row=1, column=0, sticky='nsew', padx=(0, 12))
        live.columnconfigure(0, weight=1)
        live.rowconfigure(1, weight=1)
        self.camera_label = ttk.Label(live, textvariable=self.camera_text, style='Hint.TLabel')
        self.camera_label.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        self.video = tk.Canvas(live, bg='#142332', highlightthickness=0, width=500, height=240)
        self.video.grid(row=1, column=0, sticky='nsew')
        self.video.bind('<ButtonPress-1>', self.roi_press)
        self.video.bind('<B1-Motion>', self.roi_drag)
        self.video.bind('<ButtonRelease-1>', self.roi_release)
        ttk.Label(live, text='노란 박스: 회전 공간   |   하늘색: 기존 촬영 구도의 정렬 박스',
                  style='Hint.TLabel').grid(row=2, column=0, sticky='w', pady=5)
        self.direction_label = ttk.Label(live, textvariable=self.direction, font=('맑은 고딕', -19, 'bold'))
        self.direction_label.grid(row=3, column=0, sticky='ew')
        self.zero_label = ttk.Label(live, text=ZERO_GUIDE, style='Hint.TLabel')
        self.zero_label.grid(row=4, column=0, sticky='ew', pady=(5, 0))
        live.bind('<Configure>', lambda event: self._wrap_live(event.width))
        guide = ttk.Frame(content, width=310)
        guide.grid(row=1, column=1, sticky='nsew')
        guide.columnconfigure(0, weight=1)
        ttk.Label(guide, textvariable=self.change_text, foreground='#a15b00').grid(row=0, column=0, sticky='w')
        ttk.Label(guide, textvariable=self.instruction, style='Title.TLabel', wraplength=300).grid(row=1, column=0, sticky='ew', pady=(3, 8))
        ttk.Label(guide, textvariable=self.remaining, wraplength=300).grid(row=2, column=0, sticky='ew')
        examples = ttk.Frame(guide)
        examples.grid(row=3, column=0, sticky='ew', pady=8)
        self.normal = ttk.Label(examples, text='정상 기준', compound='top', anchor='center')
        self.normal.pack(side='left', expand=True)
        self.target = ttk.Label(examples, text='대상 부품', compound='top', anchor='center')
        self.target.pack(side='left', expand=True)
        for widget in (self.normal, self.target):
            widget.bind('<Button-1>', lambda event: self.show_examples())
        self.example_caption = ttk.Label(guide, text='사진을 누르면 크게 보기 · 오른쪽은 설명용 부분 사진', style='Hint.TLabel', wraplength=300)
        self.example_caption.grid(row=4, column=0, sticky='ew')
        self.angle_canvas = tk.Canvas(guide, width=300, height=115, bg='#edf2f6', highlightthickness=0)
        self.angle_canvas.grid(row=5, column=0, sticky='ew', pady=6)
        self.recent = ttk.Label(guide, text='최근 저장 사진', anchor='center', compound='left')
        self.recent.grid(row=6, column=0, sticky='ew')
        footer = ttk.Frame(root, padding=(12, 6))
        footer.grid(row=3, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        self.capture_button = ttk.Button(footer, text='촬영 · Space', style='Capture.TButton', command=self.capture, takefocus=False)
        self.capture_button.grid(row=0, column=0, sticky='ew', padx=(0, 12))
        actions = ttk.Frame(footer)
        actions.grid(row=0, column=1, sticky='e')
        ttk.Button(actions, text='직전 사진 다시 찍기', command=self.retake, takefocus=False).grid(row=0, column=0)
        ttk.Button(actions, text='잠시 멈춤', command=self.pause, takefocus=False).grid(row=0, column=1, padx=4)
        ttk.Button(actions, text='촬영 종료 / 전달 폴더', command=self.finish, takefocus=False).grid(row=0, column=2)
        self.status_label = ttk.Label(root, textvariable=self.status, anchor='w', wraplength=1150)
        self.status_label.grid(row=4, column=0, sticky='ew', padx=12, pady=(0, 8))
        root.bind('<Configure>', self._resize)
        root.bind('<KeyPress-space>', self._space_press)
        root.bind('<KeyRelease-space>', self._space_release)

    def _build_setup(self, panel):
        row = ttk.Frame(panel)
        row.pack(fill='x')
        ttk.Label(row, text='카메라 후보').pack(side='left')
        ttk.Spinbox(row, from_=0, to=99, textvariable=self.index, width=4).pack(side='left', padx=5)
        ttk.Combobox(row, textvariable=self.backend, values=('DSHOW', 'MSMF'), state='readonly', width=7).pack(side='left')
        ttk.Combobox(row, textvariable=self.resolution, values=('1280x720', '640x480', '1920x1080'), state='readonly', width=12).pack(side='left', padx=5)
        ttk.Button(row, text='영상 연결 / 재연결', command=self.connect).pack(side='left')
        ttk.Button(row, text='연결 해제', command=self.disconnect).pack(side='left', padx=5)
        ttk.Label(row, text='번호는 모델명이 아닙니다. 영상으로 선택하세요.', style='Hint.TLabel').pack(side='left')
        row = ttk.Frame(panel)
        row.pack(fill='x', pady=(7, 0))
        ttk.Label(row, text='촬영자').pack(side='left')
        ttk.Entry(row, textvariable=self.operator, width=12).pack(side='left', padx=5)
        ttk.Button(row, text='저장 폴더 선택', command=self.choose_folder).pack(side='left')
        ttk.Button(row, text='0° 배치 박스 맞추기', command=self.begin_alignment).pack(side='left', padx=5)
        ttk.Button(row, text='설정 완료 · 촬영 화면', command=self.accept_setup).pack(side='left')
        ttk.Label(row, text='촬영 중에는 추가 확인 없음', style='Hint.TLabel').pack(side='left', padx=8)

    def _resize(self, event):
        if event.widget == self.root:
            self.status_label.configure(wraplength=max(400, event.width-30))
            compact = event.height < 740
            if compact != self.compact:
                self.compact = compact
                self.angle_canvas.configure(height=85 if compact else 115)
                self.refresh()

    def _wrap_live(self, width):
        for label in (self.camera_label, self.direction_label, self.zero_label):
            label.configure(wraplength=max(260, width-8))

    def toggle_setup(self, opened=None):
        if self.gate or self.future:
            return
        self.setup_panel_open = not self.setup_panel_open if opened is None else opened
        self.setup.grid() if self.setup_panel_open else self.setup.grid_remove()

    def accept_setup(self):
        try:
            if not self.operator.get().strip():
                raise ValueError('촬영자 이름 또는 간단한 식별자를 입력하세요.')
            frame = self.camera.snapshot()
            guide_geometry(self.body_roi, 'CENTER', 0, (frame.camera['width'], frame.camera['height']))
            self.setup_complete = True
            self.setting_roi = False
            self._save_settings()
            self.toggle_setup(False)
            self.status.set('설정 완료. 화면의 상태와 박스에 맞추고 촬영을 한 번 누르세요.')
            self.root.focus_set()
        except Exception as exc:
            self.status.set(str(exc))

    def _save_settings(self):
        data = {key: getattr(self, key).get().strip() for key in ('operator', 'output', 'index', 'backend', 'resolution')}
        data.update(body_roi=self.body_roi, setup_complete=self.setup_complete)
        temp = self.settings_path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(self.settings_path)

    def begin_alignment(self):
        if self.gate or self.future:
            return
        self.setting_roi = True
        self.toggle_setup(False)
        self.status.set('처음 구도 맞춤: 0° 엔진 전체 외곽을 영상에서 드래그하세요. 놓으면 박스를 기억합니다. ' + ZERO_GUIDE)

    def roi_press(self, event):
        if self.setting_roi and self.preview_box:
            self.drag_start = (event.x, event.y)

    def roi_drag(self, event):
        if self.drag_start:
            self.video.delete('roi-drag')
            self.video.create_rectangle(*self.drag_start, event.x, event.y, outline='#23ebff', width=3, tags='roi-drag')

    def roi_release(self, event):
        if not self.drag_start or not self.preview_box:
            return
        px, py, width, height = self.preview_box
        start = self.drag_start
        self.drag_start = None
        self.video.delete('roi-drag')
        roi = [(min(start[0], event.x)-px)/width, (min(start[1], event.y)-py)/height,
               abs(event.x-start[0])/width, abs(event.y-start[1])/height]
        try:
            frame = self.camera.snapshot()
            guide_geometry(roi, 'CENTER', 0, (frame.camera['width'], frame.camera['height']))
            self.body_roi = roi
            self.setup_revision = uuid.uuid4().hex[:8].upper()
            self.setting_roi = False
            self._save_settings()
            self.toggle_setup(True)
            self.status.set('배치 박스를 기억했습니다. 실제 영상 확인 후 설정 완료를 누르세요.')
        except Exception as exc:
            self.status.set(f'박스를 다시 그려주세요: {exc}')

    def _space_press(self, event):
        if isinstance(event.widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Entry)):
            return
        if not self.space_down:
            self.space_down = True
            self.capture()
        return 'break'

    def _space_release(self, event):
        self.space_down = False
        return 'break'

    def choose_folder(self):
        if self.gate or self.future:
            return
        if self.collection:
            self.status.set('진행 중인 수집의 저장 위치: ' + str(self.collection.folder))
            return
        folder = filedialog.askdirectory(initialdir=self.output.get())
        if folder:
            self.output.set(folder)
            self._open_previous()
            self.refresh()

    def connect(self):
        if self.gate or self.future:
            self.status.set('현재 저장이 끝난 뒤 카메라를 변경하세요.')
            return
        try:
            width, height = map(int, self.resolution.get().split('x'))
            settings = CameraSettings(int(self.index.get()), self.backend.get(), width, height)
            self.setup_revision = uuid.uuid4().hex[:8].upper()
            if self.camera.process is not None:
                self.reconnect_settings = settings
                self.camera.disconnect()
            else:
                self.camera.connect(settings)
            self.status.set('선택한 카메라에 연결 중입니다. 실제 화면과 위치를 확인하세요.')
        except Exception as exc:
            self.status.set(f'연결하지 못했습니다. 후보 번호·해상도를 확인하세요: {exc}')

    def disconnect(self):
        self.reconnect_settings = None
        self.pause()
        self.camera.disconnect()
        self.status.set('선택한 카메라 연결을 해제합니다. 다른 후보를 확인하려면 해제 완료 뒤 연결하세요.')

    def new_setup(self):
        if self.gate or self.future:
            self.status.set('현재 촬영 저장이 끝난 뒤 새 구도를 기록하세요.')
            return
        self.setup_revision = uuid.uuid4().hex[:8].upper()
        self.status.set('다음 사진부터 새 setup ID와 세션으로 저장합니다. 실제 조립 독립성은 확인된 것으로 표시하지 않습니다.')

    def _open_previous(self):
        root = Path(self.output.get()) / 'collections'
        candidates = sorted(root.glob('M*/collection-info.json'), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            return
        try:
            self.collection = SimpleCollection.open(candidates[0].parent)
            if self.collection.plan != self.plan:
                self.plan = self.collection.plan
                self.status.set('이전 수집의 저장된 계획으로 이어갑니다. 기존 촬영 계획과 기록을 보존합니다.')
            if self.collection.records:
                last = list(self.collection.records.values())[-1]
                self._show_recent(last)
        except Exception as exc:
            self.blocked_folder = candidates[0].parent
            self.status.set(f'기존 수집을 검증해 열지 못했습니다: {exc}')

    def _ensure_collection(self):
        if self.collection and self.collection.folder.parent != (Path(self.output.get()) / 'collections').resolve():
            # Extended Windows paths have a different spelling for the same directory.
            from .storage_paths import storage_path
            if self.collection.folder.parent != storage_path(Path(self.output.get()) / 'collections'):
                raise ValueError('수집 도중 저장 폴더가 바뀌었습니다. 원래 폴더를 다시 선택하세요.')
        if self.collection is None:
            self.collection = SimpleCollection.create(Path(self.output.get()) / 'collections', self.plan)
        self._save_settings()

    def capture(self):
        if self.gate or self.future or self.closing or time.monotonic() < self.next_click_after:
            return
        try:
            if self.setup_panel_open or not self.setup_complete or self.setting_roi:
                raise ValueError('처음 한 번 카메라와 구도를 설정하고 설정 완료를 누르세요.')
            if not self.operator.get().strip():
                raise ValueError('촬영자 식별자를 입력하세요.')
            if self.blocked_folder:
                raise ValueError(f'기존 수집 검증 실패: {self.blocked_folder}. 원본을 보존하고 제작자에게 전달하세요.')
            if self.camera.state != 'connected':
                raise ValueError('실제 카메라 영상 연결을 확인하세요.')
            self._ensure_collection()
            step = self.collection.next_step
            if step is None:
                raise ValueError('계획 촬영을 마쳤습니다. 전달 폴더를 만드세요.')
            frame = self.camera.snapshot()
            geo = guide_geometry(self.body_roi, step['target_position'], step['target_engine_angle'],
                                 (frame.camera['width'], frame.camera['height']))
            self.declaration = self.collection.declare(step, self.operator.get().strip())
            setup_id = (f"{frame.camera['backend']}_{frame.camera['index']}_"
                        f"{frame.camera['width']}x{frame.camera['height']}_{self.setup_revision}")
            self.pending_capture = dict(step=deepcopy(step), operator=self.operator.get().strip(),
                                        setup_id=setup_id, body_roi=list(self.body_roi), quality_roi=geo['envelope'])
            self.cancel_preparation = False
            self.future_phase = 'prepare'
            frame = self.camera.snapshot()
            self.future = self.worker.submit(self.collection.prepare_capture, deepcopy(step), frame,
                                             setup_id, source_kind=self.camera.source_kind)
            self.status.set('현재 단계 고정. 저장 준비 뒤 새 프레임을 받습니다.')
            self.capture_button.configure(state='disabled')
        except Exception as exc:
            self.pending_capture = self.declaration = self.future_phase = None
            self.status.set(f'저장하지 않았습니다: {exc}')

    def pause(self):
        if self.future and self.future_phase == 'prepare':
            self.cancel_preparation = True
            self.status.set('준비가 끝나면 멈춥니다. 사진은 저장하지 않습니다.')
            return
        if self.future:
            self.status.set('현재 사진의 저장을 마친 뒤 기다립니다. 다음 촬영은 버튼을 눌러 시작하세요.')
            return
        if self.gate:
            self.gate.cancel()
            self.gate = None
            self.declaration = None
            self.pending_capture = None
            self.capture_button.configure(state='normal')
        self.status.set('잠시 멈췄습니다. 같은 단계에서 촬영을 누르면 다시 시작합니다.')

    def retake(self):
        if self.gate or self.future or not self.collection:
            return
        try:
            row = self.collection.supersede_last()
            self.status.set(f"직전 원본 보존. 같은 단계 {row['step_id']}를 다시 촬영하세요.")
            self.refresh()
        except Exception as exc:
            self.status.set(str(exc))

    def finish(self):
        if self.gate or self.future:
            self.status.set('현재 저장이 끝난 뒤 전달 폴더를 만드세요.')
            return
        if not self.collection:
            self.status.set('저장한 사진이 아직 없습니다.')
            return
        try:
            folder = self.collection.export()
            self.status.set(f'부분/전체 진행 요약 포함 전달 폴더: {folder}  — 이 폴더 전체를 보내세요.')
            if sys.platform == 'win32':
                os.startfile(folder)
        except Exception as exc:
            self.status.set(f'전달 폴더 검증 실패: {exc}')

    def refresh(self):
        if self.blocked_folder:
            self.instruction.set('기존 원본/기록 확인 필요')
            self.remaining.set(str(self.blocked_folder))
            return
        step = self.pending_capture['step'] if self.pending_capture else (self.collection.next_step if self.collection else self.plan['steps'][0])
        count = len(self.collection.completed) if self.collection else 0
        self.progress.set(f"저장 {count} / 목표 {len(self.plan['steps'])} · 남음 {len(self.plan['steps'])-count}")
        self.progressbar.configure(maximum=len(self.plan['steps']), value=count)
        if step is None:
            self.instruction.set('계획 촬영 완료')
            self.remaining.set('전달 폴더를 만들어 원본과 manifest를 함께 보내세요.')
            self.direction.set('모든 촬영 단계를 저장했습니다.')
            self.capture_button.configure(state='disabled')
            return
        self.capture_button.configure(state='disabled' if self.gate or self.future else 'normal')
        target = step['target_part']
        if step['step_id'] != self.last_step_id:
            changed = step['scenario_id'] != self.last_scenario
            self.change_text.set('부품 상태 변경' if changed else '조립 상태 유지 · 엔진만 이동 / 회전')
            self.last_scenario, self.last_step_id = step['scenario_id'], step['step_id']
        self.instruction.set(step['scenario_label'])
        others = ' · '.join(PART_NAMES[part] for part, state in step['part_states'].items() if state == 'CORRECT')
        self.remaining.set('정상 유지: ' + (others or '본체·중심축만 유지') + '\n부품 좌우는 0° 기준의 실물 자리입니다.')
        position = '중앙' if step['target_position'] == 'CENTER' else '오른쪽 위치'
        same_turn = [s for s in self.plan['steps'] if s['scenario_id'] == step['scenario_id'] and s['target_position'] == step['target_position']]
        turn_index = next(i for i, s in enumerate(same_turn, 1) if s['step_id'] == step['step_id'])
        self.direction.set(f"{position} · 목표 {step['target_engine_angle']}° · 한 바퀴 {turn_index}/{len(same_turn)}\n하늘색 박스와 화살표에 엔진 전체를 맞추세요.")
        self.draw_angle(step['target_engine_angle'])
        image = Image.open(assets_folder() / 'normal_reference.png')
        image.thumbnail((148, 85 if self.compact else 125))
        self.normal_image = ImageTk.PhotoImage(image, master=self.root)
        self.normal.configure(image=self.normal_image)
        target = Image.open(assets_folder() / step['example_image'])
        target.thumbnail((148, 85 if self.compact else 125))
        self.target_image = ImageTk.PhotoImage(target, master=self.root)
        self.target.configure(image=self.target_image)
        missing = 'MISSING' in step['part_states'].values()
        normal = step['scenario_id'] == 'NORMAL'
        self.target.configure(text='제거 전 모습 참고' if missing else ('정상 목표' if normal else '대상 부품'))
        self.example_caption.configure(text=('결품 단계: 표시한 부품을 빼세요. 사진은 제거 전 정상 모습입니다.' if missing else
                                            ('사진을 누르면 크게 보기 · 기존 학습용 정상 기준' if normal else
                                             '사진을 누르면 크게 보기 · 오른쪽은 설명용 부분 사진')))

    def draw_angle(self, angle):
        canvas = self.angle_canvas
        canvas.delete('all')
        cx, cy, radius = (55, 42, 25) if self.compact else (60, 55, 34)
        canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline='#8aa0b3')
        for value in (0, 90, 180, 270):
            radians = math.radians(value)
            distance = 36 if self.compact else 49
            canvas.create_text(cx+distance*math.sin(radians), cy-distance*math.cos(radians), text=f'{value}°', font=('맑은 고딕', -11))
        radians = math.radians(angle)
        canvas.create_line(cx, cy, cx+radius*math.sin(radians), cy-radius*math.cos(radians), arrow='last', width=3, fill='#146d94')
        canvas.create_text(138, 25 if self.compact else 35, anchor='w', text=f'목표 {angle}°', fill='#173653', font=('맑은 고딕', -23, 'bold'))
        canvas.create_text(138, 57 if self.compact else 68, anchor='w', text='시계 방향으로 회전\n목표값 · 실측 아님', font=('맑은 고딕', -13))

    def _show_recent(self, row):
        with Image.open(self.collection.folder / row['raw_relative_path']) as original:
            image = original.copy()
        image.thumbnail((115, 65))
        self.recent_image = ImageTk.PhotoImage(image, master=self.root)
        self.recent.configure(image=self.recent_image, text=f"  최근 저장 {row['target_engine_angle']}°\n  별도 검토 전")

    def show_examples(self):
        if self.gate or self.future:
            return
        step = self.collection.next_step if self.collection else self.plan['steps'][0]
        if step is None:
            return
        window = tk.Toplevel(self.root)
        window.title('정상 기준 / 대상 부품 설명')
        window.geometry('1000x640')
        window.columnconfigure((0, 1), weight=1)
        window.rowconfigure(1, weight=1)
        window.photos = []
        for col, filename, title in ((0, 'normal_reference.png', '정상 기준 · ' + ZERO_GUIDE),
                                      (1, step['example_image'], step['scenario_label'] + ' · 대상 부분만 참고')):
            ttk.Label(window, text=title, wraplength=470).grid(row=0, column=col, sticky='ew', padx=10, pady=10)
            with Image.open(assets_folder()/filename) as original:
                img = original.copy()
            img.thumbnail((470, 490))
            photo = ImageTk.PhotoImage(img, master=window)
            window.photos.append(photo)
            ttk.Label(window, image=photo).grid(row=1, column=col)
        ttk.Label(window, text='설명용 이미지입니다. 대상 이외 부품은 정상 기준을 유지하세요.').grid(row=2, column=0, columnspan=2, pady=12)

    def _render_video(self):
        frame = self.camera.latest
        width, height = max(1, self.video.winfo_width()), max(1, self.video.winfo_height())
        if not frame or not frame.fresh() or self.camera.state != 'connected':
            self.video.delete('frame')
            self.video.delete('no-signal')
            self.preview_box = None
            if self.camera.state == 'connecting':
                text = ('카메라 작업 실행 준비 중…' if self.camera.worker_started is None
                        else '선택한 카메라의 첫 영상을 기다리는 중…')
            elif self.camera.state == 'stopping':
                text = '선택한 카메라 연결 해제 중…'
            else:
                text = '카메라 영상 없음\n카메라 · 최초 설정에서 연결하세요.'
            self.video.create_text(width/2, height/2, text=text, fill='#dce8f3', font=('맑은 고딕', -20), tags='no-signal')
            self.camera_text.set(self.camera.error or ('오래된 프레임 · 같은 단계에서 재연결하세요.' if frame else text.replace('\n', ' ')))
            return
        self.video.delete('no-signal')
        detail = frame.camera
        self.camera_text.set(f"후보 {detail['index']} · {detail['backend']} · 실제 {detail['width']}×{detail['height']} · 보고 FPS {detail.get('fps_reported') or '미확인'}")
        step = self.pending_capture['step'] if self.pending_capture else (self.collection.next_step if self.collection else self.plan['steps'][0])
        angle = 0 if self.setting_roi or step is None else step['target_engine_angle']
        position = 'CENTER' if self.setting_roi or step is None else step['target_position']
        try:
            image = render_guide(frame.image, self.body_roi, position, angle)
        except ValueError as exc:
            image = Image.fromarray(cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB))
            self.camera_text.set(f'배치 박스를 다시 맞춰주세요: {exc}')
        image.thumbnail((width, height))
        x, y = (width-image.width)//2, (height-image.height)//2
        self.preview_box = (x, y, image.width, image.height)
        self.preview_image = ImageTk.PhotoImage(image, master=self.root)
        self.video.delete('frame')
        self.video.create_image(x, y, image=self.preview_image, anchor='nw', tags='frame')
        self.video.tag_lower('frame')

    def tick(self):
        if self.closed:
            return
        self.camera.poll()
        if self.reconnect_settings is not None and self.camera.process is None and not self.closing:
            settings, self.reconnect_settings = self.reconnect_settings, None
            try:
                self.camera.connect(settings)
            except Exception as exc:
                self.status.set(f'카메라 재연결 실패: {exc}')
        if self.camera.error and self.camera.error != self.last_camera_error:
            self.status.set('카메라 오류: ' + self.camera.error)
        self.last_camera_error = self.camera.error
        if self.future and self.future_phase == 'prepare' and self.future.done():
            preparation, self.future = self.future, None
            self.future_phase = None
            try:
                preparation.result()
                if self.cancel_preparation or self.closing:
                    self.pending_capture = self.declaration = None
                    self.status.set('잠시 멈췄습니다. 같은 단계에서 다시 촬영할 수 있습니다.')
                else:
                    frame = self.camera.snapshot()
                    self.gate = CaptureGate(self.plan['quality'], self.pending_capture['quality_roi'], frame)
                    self.status.set('현재 단계 고정. 새 프레임과 짧은 안정 대기 중입니다.')
            except Exception as exc:
                self.pending_capture = self.declaration = None
                self.status.set(f'촬영 준비 실패, 단계 유지: {exc}')
            self.refresh()
        if self.gate:
            try:
                frame = self.camera.snapshot()
                chosen = self.gate.observe(frame)
                if chosen is not None:
                    pending = self.pending_capture
                    self.gate = None
                    self.future_phase = 'save'
                    self.future = self.worker.submit(self.collection.save, pending['step'], chosen,
                                                     pending['operator'], pending['setup_id'], self.declaration,
                                                     guide_setup={'body_roi': pending['body_roi'], 'quality_roi': pending['quality_roi'],
                                                                  'zero_reference': ZERO_GUIDE,
                                                                  'outline_policy': 'original_alignment_with_shaft_tail_margin_v1'},
                                                     source_kind=self.camera.source_kind)
                    self.declaration = None
            except Exception as exc:
                self.gate = None
                self.declaration = None
                self.pending_capture = None
                self.capture_button.configure(state='normal')
                self.status.set(f'촬영하지 않았습니다: {exc}')
        if self.future and self.future.done():
            try:
                row = self.future.result()
                self._show_recent(row)
                warning = ', '.join(WARNING_TEXT.get(w, w) for w in row['quality_warnings'])
                self.status.set('저장 완료. 다음 안내로 이동했습니다.' + (' 보조 경고: ' + warning if warning else ''))
                self.root.bell()
            except Exception as exc:
                message = f'저장 실패, 단계 유지: {exc}'
                if self.collection and self.collection.failed:
                    folder = self.collection.folder
                    self.collection.close()
                    try:
                        self.collection = SimpleCollection.open(folder)
                        message += ' 저장 기록 재검증 완료. 같은 촬영 버튼으로 재시도하세요.'
                    except Exception as recovery_error:
                        self.collection = None
                        self.blocked_folder = folder
                        message += f' 원본·manifest를 보존하고 제작자에게 전달하세요: {recovery_error}'
                self.status.set(message)
            self.future = None
            self.future_phase = None
            self.pending_capture = None
            self.next_click_after = time.monotonic() + .4
            self.capture_button.configure(state='normal')
            self.refresh()
        now = time.monotonic()
        if now - self.last_preview >= 0.12:
            self._render_video()
            self.last_preview = now
        if self.closing and not self.future and self.camera.process is None:
            if self.collection:
                self.collection.close()
            self.worker.shutdown(wait=False)
            self.closed = True
            self.root.destroy()
            return
        self.root.after(50, self.tick)

    def close(self):
        if self.closing:
            return
        self.pause()
        self.closing = True
        self.reconnect_settings = None
        self.camera.disconnect()

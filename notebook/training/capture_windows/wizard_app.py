"""Novice collection wizard: one physical instruction, one readiness action.

CameraClient owns the device, a single worker owns storage, Tk owns all widgets.
No automatic camera opening, physical-state inference, or automatic human review.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import gc
import math
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import cv2
from PIL import Image, ImageTk

from training.scripts import capture_proxy as capture
from .app import DEFAULT_PROFILE, PROJECT_ROOT
from .camera import CameraClient, CameraSettings
from .guide import load_guide
from .session import connection_matches, load_display
from .wizard import Collection
from .wizard_plan import expand_plan, load_plan, target_roi, rotation_plan, placement_for_action, target_counts
from .wizard_quality import CaptureGate, WARNING_TEXT, overlay
from .wizard_views import LightingWindow, ReviewWindow, progress_window
from .wizard_store import WriterLock
from . import engine_dataset as engine
from . import engine_views
from .engine_contract import SCENARIO_LABELS, PRODUCT_NAME


class WizardApp:
    def __init__(self, root, profile_path=DEFAULT_PROFILE, output_root=None, camera=None):
        self.root, self.profile_path = root, Path(profile_path)
        self.raw_output_root = Path(output_root or PROJECT_ROOT/'data/proxy/raw')
        self.output_root = self.raw_output_root/'collections'
        self.camera = camera or CameraClient()
        self.collection = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='wizard-storage')
        self.future = self.on_done = self.gate = self.ticket = None
        self.review_window = None
        self.lighting_window = self.lighting_key = None
        self.engine_gate_window = None
        self.angle_role = None
        self.paused, self.closing, self.closed, self.manual_requested = True, False, False, False
        self.space_down, self.resume_verified = False, False
        self.roi, self.drag_start, self.preview_box = None, None, None
        self.alignment_roi = None
        self.region_kind = 'quality'
        self.setting_roi = False
        self.last_render, self.last_action_key = 0., None
        self.preview_photo = None
        self.load_product(self.profile_path)
        self._build()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<KeyPress-space>', self.key_ready)
        root.bind('<KeyRelease-space>', self.key_release)
        root.bind('<Escape>', lambda e: self.pause())
        root.after(50, self.tick)
        self.bind_shortcuts(root)
        self.refresh()

    def bind_shortcuts(self, widget):
        # Widget bindings run before ttk.Button's class bindings. Otherwise its
        # Space key-release could invoke a second capture after a long key hold.
        widget.bind('<KeyPress-space>', self.key_ready)
        widget.bind('<KeyRelease-space>', self.key_release)
        for child in widget.winfo_children():
            self.bind_shortcuts(child)

    def load_product(self, path):
        profile = capture.load_profile(path)
        guide = load_guide(path, profile)
        plan = load_plan(path, profile, guide)
        name, labels = load_display(path, profile)
        if engine.engine_v1(plan):
            from .engine_contract import semantic_contract
            semantic_contract(profile, plan)
            expected_labels = {key: SCENARIO_LABELS[key] for key in profile['scenarios']}
            if labels != expected_labels or name != PRODUCT_NAME:
                raise ValueError('display.json과 Human/Codex 공통 의미 사전이 다릅니다.')
        self.profile_path, self.profile, self.guide, self.plan = Path(path), profile, guide, plan
        self.product_name, self.labels = name, labels

    def label(self, scenario):
        return self.labels.get(scenario, scenario)

    def _build(self):
        r = self.root
        r.title('수집 길잡이 | Dataset Wizard')
        r.geometry('1240x860')
        r.minsize(980, 740)
        style = ttk.Style(r)
        style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', -15))
        style.configure('TButton', padding=(12, 7))
        style.configure('Ready.TButton', font=('맑은 고딕', -23, 'bold'), padding=(20, 14))
        style.configure('TFrame', background='#edf2f6')
        style.configure('TLabel', background='#edf2f6')
        header = tk.Frame(r, bg='#173653', padx=18, pady=10)
        header.pack(fill='x')
        tk.Label(header, text='한 번에 한 가지씩, 수집 길잡이', bg='#173653', fg='white',
                 font=('맑은 고딕', -25, 'bold')).pack(side='left')
        self.product_text = tk.StringVar(value=self.product_name)
        tk.Label(header, textvariable=self.product_text, bg='#173653', fg='#dce8f3').pack(side='right')
        top = ttk.Frame(r, padding=(14, 8))
        top.pack(fill='x')
        self.start_button = ttk.Button(top, text='시작 / 이어하기', command=self.start)
        self.start_button.pack(side='left')
        ttk.Button(top, text='고급 설정 ▾', command=self.settings).pack(side='right')
        ttk.Button(top, text='수집 현황', command=lambda: self.guard(lambda: progress_window(self))).pack(side='right', padx=6)
        self.progress_text = tk.StringVar(value='아직 수집을 시작하지 않았습니다.')
        ttk.Label(top, textvariable=self.progress_text).pack(side='left', padx=18)
        self.progress = ttk.Progressbar(r, maximum=100)
        self.progress.pack(fill='x', padx=14)
        self.rotation_text = tk.StringVar()
        self.rotation_label = ttk.Label(r, textvariable=self.rotation_text, padding=(18, 4), wraplength=1150)
        center = ttk.Frame(r, padding=(14, 8))
        self.center_panel = center
        center.pack(fill='both', expand=True)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)
        self.camera_text = tk.StringVar(value='카메라 미연결 · 시작 버튼에서 직접 후보를 선택합니다.')
        ttk.Label(center, textvariable=self.camera_text).grid(row=0, column=0, sticky='ew', pady=(0, 5))
        self.preview = tk.Canvas(center, bg='#142332', highlightthickness=0)
        self.preview.grid(row=1, column=0, sticky='nsew')
        self.preview.bind('<ButtonPress-1>', self.roi_press)
        self.preview.bind('<B1-Motion>', self.roi_drag)
        self.preview.bind('<ButtonRelease-1>', self.roi_release)
        action_panel = ttk.Frame(r, padding=(18, 5))
        self.action_panel = action_panel
        action_panel.pack(fill='x')
        self.light_canvas = tk.Canvas(action_panel, width=115, height=90, bg='#edf2f6', highlightthickness=0)
        self.light_canvas.pack(side='right', padx=8)
        self.angle_canvas = tk.Canvas(action_panel, width=180, height=165, bg='#edf2f6', highlightthickness=0)
        self.title = tk.StringVar()
        self.instruction = tk.StringVar()
        self.title_label = ttk.Label(action_panel, textvariable=self.title, font=('맑은 고딕', -22, 'bold'))
        self.title_label.pack(anchor='w')
        words = ttk.Label(action_panel, textvariable=self.instruction, wraplength=980, justify='left')
        words.pack(fill='x', pady=5)
        words.bind('<Configure>', lambda e: words.configure(wraplength=max(300, e.width-15)))
        buttons = ttk.Frame(r, padding=(18, 8))
        self.button_panel = buttons
        buttons.pack(fill='x')
        self.ready_button = ttk.Button(buttons, text='준비됐어요', style='Ready.TButton', command=self.ready)
        self.ready_button.pack(side='left', fill='x', expand=True)
        self.pause_button = ttk.Button(buttons, text='잠시 멈춤  (Esc)', command=self.pause)
        self.pause_button.pack(side='left', padx=10)
        self.review_button = ttk.Button(buttons, text='사진 묶음 확인', command=self.show_review)
        self.review_button.pack(side='left')
        self.angle_confirmed = tk.BooleanVar(value=False)
        self.angle_check = ttk.Checkbutton(r, text='현재 Engine 목표 각도를 사람이 맞추고 확인했습니다 (센서 측정 아님)', variable=self.angle_confirmed)
        self.challenge_button = ttk.Button(top, text='Challenge Capture', command=lambda: self.guard(lambda: engine_views.challenge_dialog(self)))
        if engine.engine_v1(self.plan):
            self.angle_check.pack(fill='x', padx=18)
            self.challenge_button.pack(side='right', padx=6)
        self.message = tk.StringVar(value='선택한 상태는 촬영자가 기록한 정답이며 AI 판정 결과가 아닙니다.')
        footer = tk.Label(r, textvariable=self.message, bg='#dce7f0', fg='#173653', anchor='w',
                          justify='left', padx=16, pady=8, wraplength=1180)
        footer.pack(fill='x')
        self.message_label = footer
        footer.bind('<Configure>', lambda e: footer.configure(wraplength=max(300, e.width-32)))

    def guard(self, action, require_collection=True):
        if self.future or self.closing or self.gate:
            return
        try:
            if require_collection and self.collection is None:
                raise ValueError('먼저 시작 / 이어하기를 누르세요.')
            action()
        except Exception as exc:
            self.message.set(str(exc))

    def submit(self, job, done=None):
        if self.future or self.closing:
            return
        # Dispose closed dialog callback cycles on Tk's owner thread, before a
        # storage allocation can trigger their finalizers on the worker thread.
        gc.collect()
        self.future = self.executor.submit(job)
        self.on_done = done
        self.message.set('파일과 기록을 확인하고 있습니다…')
        self.refresh()

    def start(self):
        if self.future or self.gate or self.closing:
            return
        if self.collection:
            if not self.resume_verified:
                self.guard(self.verify_resume)
            else:
                self.paused = False
                self.last_action_key = None
                self.refresh()
            return
        window = tk.Toplevel(self.root)
        window.title('시작 / 이어하기')
        window.transient(self.root)
        ttk.Label(window, text='처음이면 새 계획을 시작하세요. 기존 사진은 자동 편입하지 않습니다.', padding=16).pack()
        ttk.Button(window, text='새 수집 계획', command=lambda: (window.destroy(), self.new_collection())).pack(fill='x', padx=16, pady=8)
        ttk.Button(window, text='중단한 계획 이어하기', command=lambda: (window.destroy(), self.open_collection())).pack(fill='x', padx=16, pady=8)

    def new_collection(self, profile_path=None):
        if self.future or self.gate:
            return
        window = tk.Toplevel(self.root)
        window.title('처음 한 번 · 가능한 조명 선택')
        window.transient(self.root)
        window.grab_set()
        path = Path(profile_path or self.profile_path)
        profile = capture.load_profile(path)
        guide = load_guide(path, profile)
        template = load_plan(path, profile, guide)
        lamp = tk.BooleanVar(value=False)
        rotating = rotation_plan(template)
        station_controls = engine_views.StationControls(window) if engine.engine_v1(template) else None
        self.station_controls = station_controls
        if rotating:
            light_words = ('E02: Station A 좌100 / 우약70, Station B 좌약70 / 우100. 위 선택에서 변경 가능합니다.'
                           if engine.engine_v1(template) else 'E02는 좌100 / 우약70으로 고정합니다.')
            ttk.Label(window, text='카메라 고정 · 왼쪽/오른쪽 조명 2개\n'+light_words, padding=16).pack()
            ttk.Checkbutton(window, text='왼쪽/오른쪽 조명 2개를 준비할 수 있습니다.', variable=lamp).pack(anchor='w', padx=16)
        else:
            ttk.Label(window, text='카메라·배경을 고정하세요. 실제로 옮길 수 있는 조명이 있나요?', padding=16).pack()
            ttk.Radiobutton(window, text='방 조명만 사용 — 가능한 기준 조명으로 수집', variable=lamp, value=False).pack(anchor='w', padx=16)
            ttk.Radiobutton(window, text='옮길 수 있는 스탠드가 있음', variable=lamp, value=True).pack(anchor='w', padx=16, pady=8)
        target = tk.StringVar()
        def update(*unused):
            plan = expand_plan(template, True if rotating else lamp.get())
            count = sum(len(b['steps']) for b in plan['blocks'] if b['phase'] == 'main')
            pilot = sum(len(b['steps']) for b in plan['blocks'] if b['phase'] == 'pilot')
            target.set(f'먼저 기준 사진 2장 + 준비 시험 {pilot}장 → 확인 후 본수집 {count}장\n여러 번에 나눠 진행합니다. 학습에 충분한 수량이라는 보장은 아닙니다.')
            if rotating:
                counts = target_counts(template)
                target.set(target.get()+f"\nTrain {counts['train_candidate']} · Validation {counts['validation_candidate']} · Test Reserved {counts['test_reserved']} · Total {sum(counts.values())}\nChallenge 별도 · 실제 각도 센서 검증 없음")
        lamp.trace_add('write', update)
        update()
        ttk.Label(window, textvariable=target, padding=16).pack()
        def create():
            available = lamp.get()
            if rotating and not available:
                target.set('왼쪽/오른쪽 조명 2개 준비 가능 여부를 먼저 확인하세요.')
                return
            try:
                station = station_controls.value() if station_controls else None
            except ValueError as exc:
                target.set(str(exc))
                return
            parent = self.collection.lineage_info() if self.collection else None
            if station and parent and parent.get('station') != station:
                parent = None
            old = self.collection
            window.destroy()
            def job():
                output = self.raw_output_root if station else self.output_root
                output.mkdir(parents=True, exist_ok=True)
                allocation = WriterLock(output)
                try:
                    lineage_root = output/station['station_id']/'collections' if station else output
                    lineage = parent or Collection.latest_lineage(lineage_root)
                    created = Collection.create(output, profile, guide, template, available,
                                                self.camera.source_kind, lineage, station)
                finally:
                    allocation.close()
                if old:
                    old.close()
                return created
            def done(col):
                self.load_product(path)
                self.product_text.set(self.product_name)
                self.adopt_new(col)
            self.submit(job, done)
        ttk.Button(window, text='이 계획으로 시작', command=create).pack(fill='x', padx=16, pady=12)

    def adopt_new(self, col):
        self.collection, self.roi = col, None
        self.alignment_roi = None
        self.paused, self.resume_verified, self.setting_roi = False, True, True
        self.last_action_key = None
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings(setup=True)

    def open_collection(self, folder=None):
        if self.future or self.gate:
            return
        folder = folder or filedialog.askdirectory(title='collection.json이 있는 C… 수집 폴더 선택', initialdir=self.raw_output_root)
        if not folder:
            return
        def adopt(col):
            self.collection = col
            self.profile, self.guide, self.plan = col.profile, col.guide, col.template
            self.product_text.set(col.profile['product_id']+' · 저장된 계획')
            self.labels = {s: self.labels.get(s, s) for s in col.profile['scenarios']}
            if engine.engine_v1(col.template):
                self.labels = dict(SCENARIO_LABELS)
            self.roi = col.setups[col.setup_id]['roi'] if col.setup_id else None
            self.alignment_roi = col.setups[col.setup_id].get('alignment_roi') if col.setup_id else None
            self.resume_verified, self.paused = False, True
            self.last_action_key = None
            self.message.set('저장 위치를 복원했습니다. 카메라 연결 후 시작 / 이어하기로 실제 구도가 같은지 확인하세요.')
            self.settings()
        self.submit(lambda: Collection.open(folder), adopt)

    def verify_resume(self):
        if self.setting_roi:
            self.settings(setup=True)
            raise ValueError('변경한 기준 영역·회전 정렬을 먼저 저장하세요. 이 구도로 기준 사진 시작을 누르세요.')
        frame = self.camera.snapshot()
        col = self.collection
        if self.camera.source_kind != col.info['source_kind']:
            raise ValueError('모의 입력과 실제 카메라 수집은 서로 이어갈 수 없습니다.')
        if col.setup_id is None:
            self.resume_verified, self.paused, self.setting_roi = True, False, True
            self.settings(setup=True)
            return
        setup = col.setups[col.setup_id]
        if not connection_matches(frame.camera, setup['camera']):
            self.setting_roi = True
            self.settings(setup=True)
            raise ValueError('카메라/해상도가 달라 새 기준 확인이 필요합니다. 이전 자료는 보존됩니다.')
        same = messagebox.askyesno('실제 설치 확인', '카메라 높이·각도·화면 구도·주요 촬영 조건이 이전과 같나요?\n같지 않으면 아니오를 눌러 새 기준 사진을 만드세요.', parent=self.root)
        if not same:
            self.setting_roi = True
            self.settings(setup=True)
            return
        if engine.engine_v1(col.template):
            confirmed = messagebox.askyesno('Crank/부품 상태 재개 확인', '현재 안내할 Scenario와 손잡이 목표를 다시 확인하며 재개합니다.\n부품 상태와 Crank를 확인할 준비가 됐나요?', parent=self.root)
            if not confirmed:
                return
            self.submit(col.reconfirm_physical_state, lambda _: self.finish_resume())
            return
        self.finish_resume()

    def finish_resume(self):
        self.resume_verified, self.paused = True, False
        self.last_action_key = None
        self.refresh()

    def settings(self, setup=False):
        if self.future or self.gate or self.closing:
            return
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        w = self.settings_window = tk.Toplevel(self.root)
        w.title('카메라 연결 / 기준 설정' if setup else '고급 설정')
        w.transient(self.root)
        body = ttk.Frame(w, padding=16)
        body.pack(fill='both', expand=True)
        settings = self.camera.settings
        index = tk.StringVar(value=str(settings.index) if settings else '0')
        backend = tk.StringVar(value=settings.backend if settings else 'DSHOW')
        resolution = tk.StringVar(value=f'{settings.width}x{settings.height}' if settings else '1280x720')
        ttk.Label(body, text='후보 인덱스는 장치 이름이 아닙니다. 직접 연결해 영상을 확인하세요.').pack(anchor='w')
        row = ttk.Frame(body)
        row.pack(fill='x', pady=8)
        ttk.Spinbox(row, from_=0, to=99, textvariable=index, width=5).pack(side='left')
        ttk.Combobox(row, textvariable=backend, values=['DSHOW', 'MSMF'], state='readonly', width=9).pack(side='left', padx=8)
        ttk.Combobox(row, textvariable=resolution, values=['1280x720', '640x480', '1920x1080'], state='readonly', width=15).pack(side='left')
        def connect():
            def action():
                if self.camera.process is not None:
                    raise ValueError('먼저 연결 해제하고 해제가 끝난 뒤 연결하세요.')
                width, height = map(int, resolution.get().split('x'))
                self.camera.connect(CameraSettings(int(index.get()), backend.get(), width, height))
                self.resume_verified = False if self.collection and self.collection.setup_id else True
                self.message.set('선택한 후보에 연결 중입니다. 실제 영상 크기는 미리보기 위에 표시합니다.')
            self.guard(action, False)
        ttk.Button(row, text='연결', command=connect).pack(side='left', padx=8)
        ttk.Button(row, text='연결 해제', command=self.disconnect).pack(side='left')
        ttk.Separator(body).pack(fill='x', pady=12)
        rotating = rotation_plan(self.plan)
        setup_words = ('정상 엔진을 0°로 놓으세요. 모든 회전에서 전체 엔진이 들어가는 고정 영역을 드래그하세요.\n'
                       '화면 약70~80% 크기·회전 중심 유지·엔진 전체 가시성을 직접 확인하세요.\n'+self.plan['rotation_guide']) if rotating else '기준 배치: 정상 상태를 화면 중앙에 놓고, 큰 영상에서 물체 외곽을 드래그하세요.'
        ttk.Label(body, text=setup_words+'\n노란 테두리는 배치 안내용이며 원본/라벨에 저장되지 않습니다.', wraplength=680).pack(anchor='w')
        self.lr_value = tk.StringVar(value='')
        lr_choices = ['0° 배기구 위 / 문양 아래 · 시계 방향+ 확인'] if rotating else ['화면 왼쪽 자리가 실물 L', '화면 오른쪽 자리가 실물 L']
        lr = ttk.Combobox(body, textvariable=self.lr_value, values=lr_choices, state='readonly', width=40)
        lr.pack(anchor='w', pady=8)
        ttk.Label(body, text=('파이프 LEFT/RIGHT는 0°에서 정한 실제 자리입니다. 회전 중 화면 좌우로 바꾸지 마세요.' if rotating else
                            '실물 L/R 표기를 확인하고 선택하세요. 화면 위치만 보고 추측하지 마세요.')).pack(anchor='w')
        def region(kind='quality'):
            if not self.collection:
                self.message.set('먼저 새 수집 계획을 시작하세요.')
                return
            if kind == 'alignment' and self.roi is None:
                self.message.set('먼저 노란 고정 영역을 지정하세요.')
                return
            self.region_kind = kind
            self.setting_roi, self.paused = True, True
            w.withdraw()
            self.message.set('0° 정상 엔진의 외곽에 맞게 드래그하세요. 배기구 위 / 문양 모듈 아래. 이것은 정렬 표시이며 라벨이 아닙니다.'
                             if kind == 'alignment' else '모든 회전의 엔진이 들어갈 고정 영역을 드래그하세요. 끝나면 설정 창이 다시 열립니다.')
        ttk.Button(body, text='영상에서 기준 영역 지정', command=region).pack(fill='x', pady=6)
        if rotating:
            alignment_row = ttk.Frame(body)
            alignment_row.pack(fill='x')
            ttk.Button(alignment_row, text='0° 엔진 외곽 지정 · 회전 정렬', command=lambda: region('alignment')).pack(side='left', fill='x', expand=True)
            ttk.Button(alignment_row, text='회전 정렬 미리보기', command=lambda: self.guard(self.show_alignment_preview)).pack(side='left', padx=6)
            ttk.Label(body, text='하늘색 외곽·중심·배기구 화살표에 맞추세요. 스티커 불필요 · 각도는 사람 확인, 자동 측정 아님.', wraplength=680).pack(anchor='w')
        def accept_setup():
            def action():
                if self.roi is None or lr.current() < 0:
                    raise ValueError('영상에서 기준 영역과 실물 L/R 대응을 먼저 지정하세요.')
                frame = self.camera.snapshot()
                if self.camera.source_kind != self.collection.info['source_kind']:
                    raise ValueError('실제/모의 입력은 같은 계획에 섞을 수 없습니다.')
                mapping = self.collection.setup_mappings()[lr.current()]
                roi = list(self.roi)
                alignment_roi = list(self.alignment_roi) if self.alignment_roi is not None else None
                w.destroy()
                def done(unused):
                    self.setting_roi, self.paused, self.resume_verified = False, False, True
                    self.last_action_key = None
                self.submit(lambda: self.collection.new_setup(frame, roi, mapping, alignment_roi), done)
            self.guard(action)
        ttk.Button(body, text='이 구도로 기준 사진 시작', command=accept_setup).pack(fill='x', pady=6)
        ttk.Separator(body).pack(fill='x', pady=12)
        for text, command in [('제품 설정 바꾸기…', self.choose_product), ('기존 수동 / 한 조건 도우미', self.open_manual),
                              ('현재 조건 생략…', self.skip_condition), ('생략한 조건 다시 안내', self.resume_missing),
                              ('라벨링용 자료 정리', self.export), ('저장 폴더 열기', self.open_folder)]:
            ttk.Button(body, text=text, command=command).pack(fill='x', pady=2)
        if engine.engine_v1(self.plan):
            ttk.Button(body, text='Contact Sheet 포함 내보내기', command=lambda: self.guard(lambda: self.submit(
                lambda: self.collection.export(contact_sheets=True), lambda path: self.message.set(str(path))))).pack(fill='x', pady=2)
            ttk.Button(body, text='Final Test 라벨링 명시적 unlock…', command=self.unlock_final_test).pack(fill='x', pady=2)

    def choose_product(self):
        if self.future or self.gate:
            return
        path = filedialog.askopenfilename(title='profile.json 선택 · collection-plan.json도 필요합니다', filetypes=[('제품 설정', '*.json')])
        if not path:
            return
        def change():
            self.paused = True
            self.new_collection(Path(path))  # adopt only after the new plan is created
        self.guard(change, False)

    def open_manual(self):
        if self.future or self.gate:
            return
        self.manual_requested = True
        self.close()

    def disconnect(self):
        self.pause()
        self.camera.disconnect()
        self.resume_verified = False

    def roi_press(self, event):
        if self.setting_roi and self.preview_box and not self.future:
            self.drag_start = (event.x, event.y)

    def roi_drag(self, event):
        if self.drag_start:
            self.preview.delete('roi-drag')
            self.preview.create_rectangle(*self.drag_start, event.x, event.y, outline='#ffdc4b', width=3, tags='roi-drag')

    def roi_release(self, event):
        if not self.drag_start or not self.preview_box:
            return
        x, y, width, height = self.preview_box
        ax, ay = self.drag_start
        self.drag_start = None
        left, right = sorted(((ax-x)/width, (event.x-x)/width))
        top, bottom = sorted(((ay-y)/height, (event.y-y)/height))
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            self.message.set('영상 내부에서 다시 드래그하세요.')
            return
        region = [left, top, right-left, bottom-top]
        if self.region_kind == 'alignment':
            from .engine_alignment import validate_alignment
            try:
                frame = self.camera.snapshot()
                validate_alignment(region, self.roi, (frame.camera['width'], frame.camera['height']))
            except (ValueError, capture.CaptureError) as exc:
                self.message.set(str(exc))
                return
            self.alignment_roi = region
        else:
            self.roi = region
            self.alignment_roi = None  # A changed envelope needs its own alignment selection.
        self.preview.delete('roi-drag')
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()

    def show_alignment_preview(self):
        """Inspect guide rotation without changing the current target or taking a photo."""
        if self.alignment_roi is None:
            raise ValueError('먼저 0° 엔진 외곽을 지정하세요.')
        frame = self.camera.snapshot()
        self.pause()
        window = tk.Toplevel(self.root)
        window.title('회전 정렬 미리보기 · 촬영 아님')
        window.transient(self.root)
        ttk.Label(window, text='정상 0°에서 지정한 외곽이 시계 방향으로 회전합니다.\n'
                  '하늘색 화살표 = 상단 배기구 방향 · 반대쪽 = 문양 모듈 방향\n'
                  '배경은 지금 화면입니다. 엔진을 돌렸거나 각도를 측정했다는 뜻이 아닙니다.', padding=12).pack()
        angle = tk.StringVar(value='0')
        choices = ttk.Combobox(window, textvariable=angle, values=['0', '30', '90', '120', '180', '240', '330'], state='readonly')
        choices.pack()
        canvas = tk.Canvas(window, width=640, height=360, highlightthickness=0)
        canvas.pack(padx=12, pady=12)
        def draw(*unused):
            placement = {'dx': 0, 'dy': 0, 'angle_deg': int(angle.get()), 'rotation_only': True}
            picture = overlay(frame.image, self.roi, placement, self.alignment_roi)
            picture.thumbnail((640, 360))
            canvas.photo = ImageTk.PhotoImage(picture, master=self.root)
            canvas.delete('all')
            canvas.create_image(320, 180, image=canvas.photo)
        angle.trace_add('write', draw)
        draw()
        ttk.Label(window, text='미리보기 각도는 촬영 목표·진행률·사람 확인을 변경하지 않습니다.').pack(padx=12)
        ttk.Button(window, text='닫기 · 기준 설정으로', command=window.destroy).pack(pady=12)

    def placement(self, action=None):
        action = action or (self.collection.next_action() if self.collection else {})
        return placement_for_action(self.plan, action)

    def key_ready(self, event):
        if self.space_down:
            return 'break'
        self.space_down = True
        if event.widget.winfo_toplevel() == self.root and not isinstance(event.widget, (ttk.Entry, ttk.Combobox, tk.Text)):
            self.ready()
            return 'break'

    def key_release(self, event):
        self.space_down = False
        return 'break'

    def ready(self):
        if (self.paused or self.setting_roi or self.future or self.gate or self.review_window or self.lighting_window
                or self.closing or not self.resume_verified):
            return
        def action():
            next_action = self.collection.next_action()
            if next_action['kind'] not in ('reference', 'capture'):
                return
            if self.needs_lighting(next_action):
                self.show_lighting(next_action)
                return
            frame = self.camera.snapshot()
            self.ticket = self.collection.prepare(frame, engine_angle_confirmed=self.angle_confirmed.get())
            roi = target_roi(self.collection.setups[self.collection.setup_id]['roi'], self.placement(),
                             (frame.camera['width'], frame.camera['height']))
            self.gate = CaptureGate(self.collection.rules, roi, frame, now=self.ticket.prepared_mono)
            self.message.set('손을 빼고 잠시 기다리세요. 움직임이 잦아들면 한 장만 저장합니다. Esc로 취소.')
            self.refresh()
        self.guard(action)

    def pause(self):
        if self.lighting_window:
            self.lighting_window.close()
        self.lighting_key = None
        if self.gate:
            self.gate.cancel()
        self.gate, self.ticket, self.paused = None, None, True
        if self.collection and not self.future and not self.collection.failed and not self.closing:
            self.guard(self.collection.pause)
        self.message.set('잠시 멈췄습니다. 저장 중인 한 장은 검증을 마칩니다. 재개 후 배치를 다시 확인하세요.')
        self.refresh()

    def show_review(self):
        if self.future or self.gate or self.review_window or not self.collection:
            return
        action = self.collection.next_action()
        if action['kind'] in ('review', 'setup_review'):
            self.review_window = ReviewWindow(self, action)

    def show_saved_review(self, block_id):
        """Reopen a confirmed block without adding another human acceptance."""
        if (self.future or self.gate or self.review_window or self.lighting_window or self.closing
                or not self.collection or self.collection.failed):
            self.message.set('촬영·저장·검토가 끝난 뒤 다시 여세요.')
            return False
        if block_id not in self.collection.accepted:
            self.message.set('이미 사람 확인을 마친 묶음의 행을 선택하세요.')
            return False
        block = self.collection.block_by_id[block_id]
        self.review_window = ReviewWindow(self, {'kind': 'review', 'block': block, 'historical': True})
        return True

    def lighting_context(self, action):
        block = action['block']
        return (str(self.collection.folder), self.collection.setup_id,
                block['phase'], block['round_id'], block['condition_id'])

    def needs_lighting(self, action):
        kinds = ('capture', 'state_setup', 'crank_setup') if engine.engine_v1(self.plan) else ('capture',)
        return action['kind'] in kinds and action.get('block') and self.lighting_key != self.lighting_context(action)

    def show_lighting(self, action):
        condition = next(c for c in self.collection.effective['conditions']
                         if c['id'] == action['block']['condition_id'])
        self.lighting_window = LightingWindow(self, condition, self.lighting_context(action))
        self.ready_button.configure(state='disabled')

    def quality_dialog(self, action):
        a = action['attempt']
        w = tk.Toplevel(self.root)
        w.title('사진 품질 보조 안내 · 자동 판정 아님')
        w.transient(self.root)
        w.grab_set()
        words = '\n'.join(WARNING_TEXT.get(s, s) for s in a['metrics']['warnings'])
        ttk.Label(w, text=words+'\n어두운 조명·빈자리의 선명도 지표는 다를 수 있습니다.\n상태와 손 가림은 사람이 확인합니다.', padding=16, wraplength=620).pack()
        def choose(keep):
            w.destroy()
            self.submit((lambda: self.collection.acknowledge_quality(a['attempt_id'], True)) if keep else
                        (lambda: self.collection.reject(a['attempt_id'], '품질 보조 경고로 보류', False, True)))
        keep_label = 'ACCEPT 검토로 · 경고 확인 후 묶음 검토까지 유지' if engine.engine_v1(self.plan) else '경고를 확인했어요 · 묶음 검토까지 유지'
        hold_label = 'REVIEW · 이 사진 보류 / 다시 준비' if engine.engine_v1(self.plan) else '이 사진 보류 · 다시 준비'
        ttk.Button(w, text=keep_label, command=lambda: choose(True)).pack(fill='x', padx=16, pady=6)
        ttk.Button(w, text=hold_label, command=lambda: choose(False)).pack(fill='x', padx=16, pady=6)
        if engine.engine_v1(self.plan):
            ttk.Button(w, text='RETAKE · 원본 보존하고 재촬영', command=lambda: (
                w.destroy(), self.submit(lambda: self.collection.reject(a['attempt_id'], '품질 경고 후 RETAKE', False, False)))).pack(fill='x', padx=16, pady=6)
        w.protocol('WM_DELETE_WINDOW', lambda: (w.destroy(), self.pause()))

    def round_dialog(self, action):
        w = tk.Toplevel(self.root)
        w.title('다음 촬영 회차 준비')
        w.transient(self.root)
        w.grab_set()
        block = action['block']
        round_info = next(r for r in self.plan['rounds'] if r['id'] == block['round_id'])
        independent = tk.BooleanVar(value=False)
        reset = tk.BooleanVar(value=False)
        ttk.Label(w, text=round_info['label']+'\n물체를 치웠다가 다시 배치하세요. 가능하면 다른 시간/날짜에 촬영하세요.\n연속 촬영은 같은 자료 묶음입니다. 앱 재시작만으로 독립 자료가 되지 않습니다.', padding=16, wraplength=630).pack()
        ttk.Checkbutton(w, text='물체를 실제로 치웠다가 새로 준비했습니다.', variable=reset).pack(anchor='w', padx=16, pady=6)
        ttk.Checkbutton(w, text='촬영을 중단했다가 별도 시간에 설치·배치를 새로 준비했습니다.\n(독립성에 대한 사람 선언이며 자동 검증은 아닙니다.)', variable=independent).pack(anchor='w', padx=16, pady=6)
        def begin():
            if not reset.get():
                self.message.set('새 회차의 실제 배치 준비를 먼저 확인하세요.')
                return
            declared = independent.get()
            w.destroy()
            self.submit(lambda: self.collection.begin_round(declared, repositioned=True))
        ttk.Button(w, text='회차 준비 완료', command=begin).pack(fill='x', padx=16, pady=12)
        w.protocol('WM_DELETE_WINDOW', lambda: (w.destroy(), self.pause()))

    def state_setup_dialog(self, action):
        """A physical declaration, saved separately from shutter preparation."""
        if engine.engine_v1(self.plan):
            return engine_views.state_dialog(self, action)
        w = tk.Toplevel(self.root)
        w.title('상태 시작 · 엔진 재배치 확인')
        w.transient(self.root)
        w.grab_set()
        reset, fixed = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        state_words = next(s['instruction'] for s in self.guide['steps'] if s['scenario'] == action['scenario'])
        ttk.Label(w, text=action['scenario']+'\n'+state_words+'\n엔진을 한 번 치웠다가 회전 중심에 다시 놓으세요.',
                  padding=16, wraplength=650).pack()
        ttk.Checkbutton(w, text='해당 부품 상태로 준비하고 엔진을 치웠다가 다시 놓았습니다.', variable=reset).pack(anchor='w', padx=16)
        ttk.Checkbutton(w, text='카메라는 고정했고 회전 중심을 다시 맞췄습니다.', variable=fixed).pack(anchor='w', padx=16, pady=8)
        def confirm():
            if not reset.get() or not fixed.get():
                self.message.set('실제 부품 상태·재배치·카메라 고정을 확인하세요. 사진은 아직 찍지 않습니다.')
                return
            w.destroy()
            self.submit(lambda: self.collection.confirm_state_preparation(True, True))
        ttk.Button(w, text='상태 준비 완료 · 각도 안내로', command=confirm).pack(fill='x', padx=16, pady=12)
        w.protocol('WM_DELETE_WINDOW', lambda: (w.destroy(), self.pause()))

    def skip_condition(self):
        def action():
            reason = simpledialog.askstring('조건 생략', '생략 이유를 적으세요. 목표에서 제거하지 않고 미수집으로 남깁니다.', parent=self.root)
            if reason:
                self.submit(lambda: self.collection.skip_condition(reason))
        self.guard(action)

    def resume_missing(self):
        self.guard(lambda: self.submit(self.collection.resume_missing))

    def export(self):
        self.guard(lambda: self.submit(self.collection.export, lambda path: self.message.set(
            f'라벨링 인계 목록 저장: {path} · 부품 위치 라벨링/학습/평가는 아직 하지 않았습니다.')))

    def unlock_final_test(self):
        def action():
            phrase = simpledialog.askstring('Final Test 라벨링 unlock',
                '학습·튜닝 금지는 유지됩니다. E04 라벨링을 의도한 경우에만\nUNLOCK FINAL TEST LABELING을 정확히 입력하세요.', parent=self.root)
            if phrase is not None:
                self.submit(lambda: self.collection.unlock_final_test(phrase))
        self.guard(action)

    def open_folder(self):
        self.guard(lambda: os.startfile(self.collection.folder))

    def refresh(self):
        if self.closed:
            return
        busy = bool(self.future or self.gate or self.closing or self.lighting_window)
        self.start_button.configure(state='disabled' if busy else 'normal')
        action = self.collection.next_action() if self.collection and not self.future else {'kind': 'working'}
        kind = action['kind']
        if engine.engine_v1(self.plan):
            # Reserve the shutter/check controls before allowing the preview to
            # expand. Long engine instructions must not push them off screen.
            self.message_label.pack(side='bottom', fill='x', before=self.center_panel)
            self.angle_check.pack(side='bottom', fill='x', padx=18, before=self.center_panel)
            self.button_panel.pack(side='bottom', fill='x', before=self.center_panel)
            self.action_panel.pack(side='bottom', fill='x', before=self.center_panel)
            self.challenge_button.pack(side='right', padx=6)
            role = action.get('role_id')
            if role != self.angle_role:
                self.angle_confirmed.set(False)
                self.angle_role = role
        else:
            self.angle_check.pack_forget()
            self.challenge_button.pack_forget()
        self.refresh_rotation(action)
        enabled = self.collection and not self.collection.failed and kind in ('reference', 'capture') and not busy and not self.paused and not self.setting_roi and self.resume_verified
        self.ready_button.configure(state='normal' if enabled else 'disabled')
        self.review_button.configure(state='normal' if kind in ('review', 'setup_review') and not busy else 'disabled')
        if not self.collection:
            self.title.set('처음이면 시작 / 이어하기를 누르세요')
            self.instruction.set(self.guide['setup'] if rotation_plan(self.plan) else '카메라와 조명을 처음 한 번 설정하면, 다음 배치와 상태는 프로그램이 안내합니다.')
            return
        if self.future:
            self.title.set('원본과 기록 검증 중')
            return
        summary = self.collection.summary()
        self.progress_text.set(f"준비 시험 {summary['pilot_accepted']}/{summary['pilot_target']}  ·  본수집 {summary['main_accepted']}/{summary['main_target']}  ·  검토 대기 {summary['pending']}")
        self.progress['value'] = 100*summary['main_accepted']/max(1, summary['main_target'])
        if self.collection.failed:
            self.title.set('기록 오류 · 창을 닫고 같은 수집 폴더를 다시 열어 검증하세요')
            return
        if self.paused:
            self.title.set('잠시 멈춤 · 시작 / 이어하기로 재개')
        elif kind in ('reference', 'capture'):
            block = action.get('block')
            self.title.set(('기준 사진 · ' if not block else ('준비 시험 · ' if block['phase'] == 'pilot' else '본수집 · '))+self.label(action['scenario']))
            state_words = (engine.CHALLENGES[action['scenario']] if action['scenario'] in engine.CHALLENGES else
                           next(s['instruction'] for s in self.guide['steps'] if s['scenario'] == action['scenario']))
            words = state_words
            if block:
                condition = next(c for c in self.collection.effective['conditions'] if c['id'] == block['condition_id'])
                first = not any(s['step_id'] in self.collection.current for s in block['steps'])
                previous = next((b for b in reversed(self.collection.blocks[:self.collection.blocks.index(block)])
                                 if b['block_id'] in self.collection.accepted), None)
                same_light = previous and all(previous[k] == block[k] for k in ('phase', 'round_id', 'condition_id'))
                lighting = (condition['instruction'] if not same_light else '조명은 그대로 유지하세요.') if first else '조명과 물체 외곽 배치는 그대로 유지하세요.'
                if rotation_plan(self.plan):
                    lighting = condition['instruction'] if first else '조명·부품 상태·회전 중심은 유지하고 엔진만 다음 목표 각도로 돌리세요.'
                words = lighting+'\n'+self.placement(action)['instruction']+'\n'+words
                self.draw_light(condition)
            else:
                words = '카메라·조명을 고정하고 노란 기준 테두리에 맞추세요.\n'+words
            if rotation_plan(self.plan) and self.alignment_roi is not None:
                words = ('하늘색 외곽·중심에 엔진을 맞추고, 화살표 쪽으로 상단 배기구 방향을 맞추세요.\n'
                         '누락 부품 자리보다 남아 있는 본체·중심·방향을 기준으로 맞추세요. 각도는 사람 확인입니다.\n'+words)
            self.instruction.set(words)
        else:
            titles = {'setup': '기준 영역을 지정하세요', 'setup_review': '기준 사진 두 장을 확인하세요',
                      'review': '상태별 사진 묶음을 확인하세요', 'round': '다음 회차를 실제로 준비하세요',
                      'state_setup': '부품 상태를 바꾸고 엔진을 다시 배치하세요',
                      'crank_setup': '손잡이 목표 위치를 사람이 확인하세요',
                      'quality': '사진 품질 보조 경고를 확인하세요', 'pilot_incomplete': '생략한 준비 시험이 남아 있습니다',
                      'finished': '계획한 사진 수집을 마쳤습니다' if summary['complete'] else '미수집 조건이 남아 있습니다'}
            self.title.set(titles.get(kind, '진행 기록 확인'))
            self.instruction.set('다음은 사진 속 부품 위치를 표시하는 라벨링입니다. 모델 학습과 정확도 평가는 아직 하지 않았습니다.'
                                 if summary['complete'] else '저장과 사람 확인은 별도입니다. 안내창을 닫았다면 시작 / 이어하기를 누르세요. 생략 조건은 고급 설정에서 다시 안내할 수 있습니다.')
        if not self.paused and not busy and not self.review_window and self.needs_lighting(action):
            self.show_lighting(action)
            return
        key = (kind, action.get('role_id'), action.get('block', {}).get('block_id'), action.get('attempt', {}).get('attempt_id'))
        if not self.paused and not busy and key != self.last_action_key:
            self.last_action_key = key
            if kind in ('review', 'setup_review'):
                self.show_review()
            elif kind == 'quality':
                self.quality_dialog(action)
            elif kind == 'round':
                self.round_dialog(action)
            elif kind == 'state_setup':
                self.state_setup_dialog(action)
            elif kind == 'crank_setup':
                engine_views.crank_dialog(self, action)

    def refresh_rotation(self, action):
        if not rotation_plan(self.plan):
            self.rotation_label.pack_forget()
            self.angle_canvas.pack_forget()
            return
        self.rotation_label.pack(fill='x', after=self.progress)
        self.angle_canvas.pack(side='right', padx=4)
        if engine.engine_v1(self.plan):
            self.angle_canvas.pack(side='right', padx=4, before=self.title_label)
            self.rotation_text.set(engine_views.rotation_status(self, action, self.placement(action)))
            self.draw_angle(self.placement(action)['angle_deg'])
            return
        counts = target_counts(self.plan)
        normal = self.profile['scenarios']['NORMAL']['expected_counts']
        object_names = {'gray_pipe': '회색 파이프', 'exhaust_top': '상단 배기구', 'symbol_module': '문양 모듈'}
        object_counts = ' · '.join(f'{object_names.get(name, name)} {count}개' for name, count in normal.items())
        text = (f"검사 대상: {object_counts}\n"
                f"본수집 목표: Train {counts['train_candidate']} · Validation {counts['validation_candidate']} · Test Reserved {counts['test_reserved']} · Total {sum(counts.values())} (기준/준비/Challenge 별도)")
        block = action.get('block')
        placement = self.placement(action)
        if block:
            index = next((i for i,s in enumerate(block['steps']) if s['placement_id'] == placement['id']), 0)
            following = block['steps'][index+1]['placement_id'].removeprefix('ANGLE_')+'°' if index+1 < len(block['steps']) else '사진 묶음 확인 → 다음 상태/회차'
            text += (f"\n현재 회차 {block['round_id']} · 상태 {action.get('scenario', block['scenario'])} · 조명 {block['condition_id']}"
                     f"\n목표 각도 {placement['angle_deg']:03d}° · ANGLE {index+1} / {len(block['steps'])} · 다음 {following}")
        else:
            text += '\nE01/E02 Train → E03 Validation → E04 Test Reserved · 목표 각도는 사람이 맞춥니다.'
        self.rotation_text.set(text)
        self.draw_angle(placement['angle_deg'])

    def draw_angle(self, angle):
        canvas = self.angle_canvas
        canvas.delete('all')
        cx, cy, radius = 90, 73, 48
        canvas.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,outline='#8aa0b3')
        for value in range(0,360,30):
            radians = math.radians(value)
            canvas.create_text(cx+65*math.sin(radians),cy-65*math.cos(radians),text=str(value),font=('맑은 고딕',-11))
        radians = math.radians(angle)
        canvas.create_line(cx,cy,cx+radius*math.sin(radians),cy-radius*math.cos(radians),arrow='last',width=3,fill='#146d94')
        canvas.create_text(cx,155,text=f'목표 {angle:03d}° · 시계 방향+',font=('맑은 고딕',-12))

    def draw_light(self, condition):
        c = self.light_canvas
        c.delete('all')
        c.create_rectangle(44, 38, 76, 56, fill='#9cacbc', outline='')
        if rotation_plan(self.plan):
            right = engine.engine_v1(self.plan) and self.collection and self.collection.info['station']['e02_lighting_id'] == 'RIGHT_DOMINANT'
            asymmetric = condition['id'] == 'ASYMMETRIC'
            for x, word in [(15, '좌70' if asymmetric and right else '좌100'), (100, '우70' if asymmetric and not right else '우100')]:
                c.create_oval(x-7,18,x+7,32,fill='#f6c947',outline='')
                c.create_line(x,32,60,47,arrow='last',fill='#b78011')
                c.create_text(x,65,text=word,font=('맑은 고딕',-11))
            return
        x, y = condition['lamp_xy']
        x, y = 60+x*40, 48+y*32
        c.create_line(x, y, 60, 47, arrow='last', fill='#b78011', width=2)
        c.create_oval(x-7, y-7, x+7, y+7, fill='#f6c947', outline='')
        c.create_text(58, 80, text='조명 위치 안내', font=('맑은 고딕', -12))

    def render_preview(self):
        frame = self.camera.latest
        if frame is None or not frame.fresh() or self.camera.state != 'connected':
            self.preview.delete('all')
            self.preview.create_text(max(1, self.preview.winfo_width())/2, max(1, self.preview.winfo_height())/2,
                text='실시간 영상 없음\n카메라 후보를 직접 연결하세요.', fill='#dce8f3', font=('맑은 고딕', -22), tags='no-signal')
            self.preview_box = None
            self.camera_text.set(self.camera.error or '미연결 · 다른 카메라로 자동 전환하지 않습니다.')
            return
        camera = frame.camera
        self.preview.delete('no-signal')
        mismatch = (camera['width'], camera['height']) != (camera['requested_width'], camera['requested_height'])
        self.camera_text.set(f"{camera['backend']} · 후보 {camera['index']} · 실제 {camera['width']}×{camera['height']}"
            +(' (요청 해상도와 다름)' if mismatch else '')+f" · 보고 FPS {camera['fps_reported'] or '미확인'} · 포맷 {camera['fourcc_reported'] or '미확인'}")
        show_overlay = self.roi and not self.future and (not self.setting_roi or self.region_kind == 'alignment')
        placement = self.placement()
        if self.setting_roi:
            placement = dict(placement, angle_deg=0)
        image = (overlay(frame.image, self.roi, placement, self.alignment_roi) if show_overlay
                 else Image.fromarray(cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)))
        width, height = max(1, self.preview.winfo_width()), max(1, self.preview.winfo_height())
        image.thumbnail((width, height))
        x, y = (width-image.width)//2, (height-image.height)//2
        self.preview_box = (x, y, image.width, image.height)
        self.preview_photo = ImageTk.PhotoImage(image, master=self.root)
        self.preview.delete('frame')
        self.preview.create_image(x, y, image=self.preview_photo, anchor='nw', tags='frame')
        self.preview.tag_lower('frame')

    def tick(self):
        if self.closed:
            return
        self.camera.poll()
        if self.future and self.future.done():
            future, callback = self.future, self.on_done
            self.future = self.on_done = None
            try:
                result = future.result()
                if callback:
                    callback(result)
                else:
                    self.message.set('원본과 기록 검증 완료. 다음 안내를 따라주세요. 실제 상태는 묶음 화면에서 사람이 확인합니다.')
            except Exception as exc:
                self.paused = True
                self.message.set(f'진행 중단: {exc}\n원본을 삭제하지 마세요. 기록을 다시 열어 검증하세요.')
            self.last_action_key = None
            self.refresh()
        if self.gate:
            try:
                frame = self.camera.snapshot()
                chosen = self.gate.observe(frame)
                if chosen is not None:
                    ticket = self.ticket
                    ticket.motion_mae = self.gate.last_motion_mae
                    self.gate = self.ticket = None
                    self.submit(lambda: self.collection.save_prepared(ticket, chosen))
            except Exception as exc:
                self.gate = self.ticket = None
                self.message.set(f'촬영하지 않았습니다: {exc} 손을 빼고 다시 준비하세요.')
                self.refresh()
        if self.closing and not self.future and self.camera.process is None:
            if self.collection:
                self.collection.close()
            self.executor.shutdown(wait=False)
            self.closed = True
            self.preview_photo = None
            self.root.destroy()
            return
        now = time.monotonic()
        if now-self.last_render > .10 and not self.closing:
            self.last_render = now
            self.render_preview()
        self.root.after(50, self.tick)

    def close(self):
        if self.closing:
            return
        if self.review_window:
            self.review_window.close()
        self.pause()
        self.closing = True
        self.camera.disconnect()
        self.refresh()

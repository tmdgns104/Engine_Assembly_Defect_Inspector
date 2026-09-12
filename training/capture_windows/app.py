"""Small product-driven Tk collection window. No inspection/model logic."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from training.scripts import capture_proxy as capture
from .camera import CameraClient, CameraSettings
from .session import CollectionSession, load_display

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = PROJECT_ROOT/'training/datasets/proxy/earbud_case_v0/profile.json'


class CaptureApp:
    def __init__(self, root, profile_path=DEFAULT_PROFILE, output_root=None, camera=None):
        self.root = root
        self.output_root = Path(output_root or PROJECT_ROOT/'data/proxy/raw')
        self.camera = camera or CameraClient()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='capture-storage')
        self.pending = None
        self.on_done = None
        self.closing = False
        self.closed = False
        self.session = None
        self.session_stream = None
        self.last_preview_token = None
        self.preview_photo = None
        self.recent_photo = None
        self.profile = None
        self.scenario_keys = []
        self.labels = {}
        self.busy_controls = []
        self.camera_controls = []
        self._build()
        self.load_product(Path(profile_path))
        self.update_controls()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(50, self.tick)

    def _build(self):
        root = self.root
        root.title('제품 데이터 촬영 | Windows Capture')
        root.geometry('1240x850')
        root.minsize(1040, 760)
        root.configure(bg='#eef2f6')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', -14))
        style.configure('TFrame', background='#eef2f6')
        style.configure('TLabel', background='#eef2f6')
        style.configure('TLabelframe', background='#eef2f6')
        style.configure('TLabelframe.Label', background='#eef2f6', font=('맑은 고딕', -14, 'bold'))
        style.configure('TButton', padding=(9, 4))
        style.configure('Save.TButton', font=('맑은 고딕', -18, 'bold'), padding=(12, 10))
        header = tk.Frame(root, bg='#173653', padx=22, pady=10)
        header.pack(fill='x')
        tk.Label(header, text='제품 데이터 촬영', bg='#173653', fg='white',
                 font=('맑은 고딕', -26, 'bold')).pack(anchor='w')
        tk.Label(header, text='선택한 상태는 촬영자가 기록한 정답이며 AI 판정 결과가 아닙니다.',
                 bg='#173653', fg='#dce8f3', font=('맑은 고딕', -14)).pack(anchor='w', pady=(5, 0))
        body = ttk.Frame(root, padding=16)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left_panel = ttk.Frame(body)
        left_panel.grid(row=0, column=0, sticky='ns', padx=(0, 16))
        self.left_canvas = tk.Canvas(left_panel, width=315, highlightthickness=0, bg='#eef2f6')
        left_scroll = ttk.Scrollbar(left_panel, orient='vertical', command=self.left_canvas.yview)
        left_scroll.pack(side='right', fill='y')
        self.left_canvas.pack(side='left', fill='both', expand=True)
        self.left_canvas.configure(yscrollcommand=left_scroll.set)
        left = ttk.Frame(self.left_canvas)
        left_window = self.left_canvas.create_window((0, 0), window=left, anchor='nw', width=315)
        left.bind('<Configure>', lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox('all')))
        self.left_canvas.bind('<Configure>', lambda e: self.left_canvas.itemconfigure(left_window, width=e.width))
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        product = ttk.LabelFrame(left, text='1  제품 설정', padding=10)
        product.pack(fill='x', pady=(0, 10))
        self.product_text = tk.StringVar()
        ttk.Label(product, textvariable=self.product_text, wraplength=290).pack(anchor='w')
        self.product_button = self.button(product, '제품 설정 선택…', self.choose_product)

        camera_box = ttk.LabelFrame(left, text='2  카메라 연결', padding=10)
        camera_box.pack(fill='x', pady=(0, 10))
        ttk.Label(camera_box, text='이름 매핑 미확인 · 화면으로 장치를 확인하세요.', wraplength=290).pack(anchor='w')
        row = ttk.Frame(camera_box)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text='후보 인덱스').pack(side='left')
        self.index = tk.StringVar(value='0')
        index = ttk.Spinbox(row, from_=0, to=99, textvariable=self.index, width=5)
        index.pack(side='left', padx=8)
        self.backend = tk.StringVar(value='DSHOW')
        backend = ttk.Combobox(row, textvariable=self.backend, values=['DSHOW', 'MSMF'], state='readonly', width=8)
        backend.pack(side='left')
        self.resolution = tk.StringVar(value='1280 × 720')
        resolution = ttk.Combobox(camera_box, textvariable=self.resolution,
            values=['1280 × 720', '640 × 480', '1920 × 1080'], state='readonly')
        resolution.pack(fill='x', pady=3)
        ttk.Label(camera_box, text='요청 해상도이며 지원 여부는 연결 후 확인합니다.', wraplength=290).pack(anchor='w')
        self.camera_controls = [(index, 'normal'), (backend, 'readonly'), (resolution, 'readonly')]
        row = ttk.Frame(camera_box)
        row.pack(fill='x', pady=(6, 0))
        self.connect_button = ttk.Button(row, text='연결', command=self.connect)
        self.connect_button.pack(side='left', expand=True, fill='x')
        self.disconnect_button = ttk.Button(row, text='연결 해제', command=self.disconnect)
        self.disconnect_button.pack(side='left', expand=True, fill='x', padx=(6, 0))

        group = ttk.LabelFrame(left, text='3  촬영 묶음 · 물체 배치', padding=10)
        group.pack(fill='x', pady=(0, 10))
        ttk.Label(group, text='조명·배경·높이 등 촬영 조건').pack(anchor='w')
        self.conditions = tk.StringVar()
        entry = ttk.Entry(group, textvariable=self.conditions, width=30)
        entry.pack(fill='x', pady=4)
        self.busy_controls.append((entry, 'normal'))
        self.new_button = self.button(group, '새 촬영 묶음', self.new_session)
        self.open_button = self.button(group, '기존 촬영 묶음 열기…', self.open_session)
        self.session_text = tk.StringVar(value='아직 촬영 묶음이 없습니다.')
        ttk.Label(group, textvariable=self.session_text, wraplength=290).pack(anchor='w', pady=5)
        self.scenario = tk.StringVar()
        self.scenario_combo = ttk.Combobox(group, textvariable=self.scenario, state='readonly')
        self.scenario_combo.pack(fill='x', pady=3)
        self.scenario_combo.bind('<<ComboboxSelected>>', self.change_scenario)
        self.busy_controls.append((self.scenario_combo, 'readonly'))
        self.episode_button = self.button(group, '물체를 다시 놓았어요 → 새 배치', self.new_episode)
        self.episode_text = tk.StringVar(value='배치: —')
        ttk.Label(group, textvariable=self.episode_text, wraplength=290).pack(anchor='w')

        counts_box = ttk.LabelFrame(left, text='현재 묶음의 검증된 저장 수량', padding=8)
        counts_box.pack(fill='x')
        self.counts = ttk.Treeview(counts_box, columns=('state', 'count'), show='headings', height=4)
        self.counts.heading('state', text='촬영 상태')
        self.counts.heading('count', text='사진')
        self.counts.column('state', width=210)
        self.counts.column('count', width=45, anchor='center')
        self.counts.pack(fill='x')

        self.camera_text = tk.StringVar(value='미연결 · 후보 선택 후 연결을 누르세요.')
        ttk.Label(right, textvariable=self.camera_text, wraplength=800).grid(row=0, column=0, sticky='ew', pady=(0, 8))
        viewport = tk.Frame(right, bg='#17212d', width=640, height=360)
        viewport.grid(row=1, column=0, sticky='nsew')
        viewport.grid_propagate(False)
        # Image requested size must not feed back into the window layout each tick.
        self.preview = tk.Label(viewport, text='카메라 미리보기\n연결 전에는 카메라를 열지 않습니다.',
            bg='#17212d', fg='#dce8f3', font=('맑은 고딕', -20))
        self.preview.place(x=0, y=0, relwidth=1, relheight=1)
        self.save_button = ttk.Button(right, text='한 장 저장', style='Save.TButton', command=self.save)
        self.save_button.grid(row=2, column=0, sticky='ew', pady=10)
        footer = ttk.Frame(right)
        footer.grid(row=3, column=0, sticky='ew')
        self.recent_label = tk.Label(footer, text='최근 저장 사진 없음', width=23, height=5,
                                     bg='#e0e7ee', fg='#405269')
        self.recent_label.pack(side='left', padx=(0, 12))
        actions = ttk.Frame(footer)
        actions.pack(side='left', fill='both', expand=True)
        self.last_text = tk.StringVar(value='원본 PNG와 촬영 기록은 검증 후 완료 표시됩니다.')
        ttk.Label(actions, textvariable=self.last_text, wraplength=500).pack(anchor='w')
        self.button(actions, '최근 저장 사진 보기', self.open_recent)
        self.button(actions, '저장 폴더 열기', self.open_folder)
        self.message = tk.StringVar(value='제품 → 카메라 연결 → 새 촬영 묶음 → 상태 선택 → 한 장 저장')
        status_label = tk.Label(root, textvariable=self.message, anchor='w', justify='left', wraplength=1180,
                 bg='#dce7f0', fg='#173653', padx=18, pady=8, font=('맑은 고딕', -14))
        status_label.pack(side='bottom', fill='x')
        status_label.bind('<Configure>', lambda e: status_label.configure(wraplength=max(200, e.width-40)))
        body.pack(fill='both', expand=True)

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        button.pack(fill='x', pady=3)
        self.busy_controls.append((button, 'normal'))
        return button

    def load_product(self, path):
        profile = capture.load_profile(path)
        name, labels = load_display(path, profile)
        self.profile, self.labels = profile, labels
        self.product_text.set(f"{name}\n{profile['product_id']} · 설정 v{profile['profile_version']}")
        self.scenario_keys = list(profile['scenarios'])
        self.scenario_combo.configure(values=[f'{labels[k]} ({k})' for k in self.scenario_keys])
        self.scenario_combo.current(0)
        self.clear_session()
        return True

    def clear_session(self):
        self.session, self.session_stream = None, None
        self.recent_label.configure(image='', text='최근 저장 사진 없음', width=23, height=5)
        self.recent_photo = None
        self.last_text.set('원본 PNG와 촬영 기록은 검증 후 완료 표시됩니다.')
        self.session_text.set('새 촬영 묶음을 만들거나 기존 묶음을 여세요.')
        self.episode_text.set('배치: —')
        self.refresh_counts()

    def choose_product(self):
        path = filedialog.askopenfilename(title='제품 profile.json 선택', initialdir=PROJECT_ROOT/'training/datasets/proxy',
                                          filetypes=[('제품 설정 JSON', '*.json')])
        if path:
            if self.guard(lambda: self.load_product(Path(path))):
                self.message.set('제품 설정 변경 시 새 촬영 묶음을 사용하세요.')

    def guard(self, action):
        try:
            return action()
        except Exception as exc:
            self.message.set(f'오류: {exc}')
            return None

    def connect(self):
        def action():
            w, h = [int(x.strip()) for x in self.resolution.get().split('×')]
            settings = CameraSettings(int(self.index.get()), self.backend.get(), w, h)
            self.camera.connect(settings)
            self.clear_session()
            self.message.set('선택한 카메라에 연결 중입니다. 화면에서 외부 USB 카메라인지 확인하세요.')
        self.guard(action)

    def disconnect(self):
        self.camera.disconnect()
        self.session_stream = None
        self.message.set('카메라 해제 중입니다. 재연결 후 새 묶음 또는 기존 묶음을 다시 확인하세요.')

    def job(self, operation, done):
        if self.pending is not None or self.closing:
            return False
        self.pending = self.executor.submit(operation)
        self.on_done = done
        self.update_controls()
        return True

    def selected_scenario(self):
        return self.scenario_keys[self.scenario_combo.current()]

    def new_session(self):
        def action():
            frame = self.camera.snapshot()
            profile, conditions = self.profile, self.conditions.get()
            self.message.set('새 촬영 묶음 정보를 저장 중입니다…')
            kind = self.camera.source_kind
            self.job(lambda: CollectionSession.create(self.output_root, profile, frame, conditions,
                                                      source_kind=kind), self.finish_session)
        self.guard(action)

    def finish_session(self, session):
        self.session = session
        self.session_stream = self.camera.latest.stream_id if self.camera.latest is not None else None
        session.set_scenario(self.selected_scenario())
        self.refresh_session()
        self.message.set('새 촬영 묶음 준비 완료. 실제 배치와 상태를 확인한 뒤 한 장 저장을 누르세요.')

    def open_session(self):
        path = filedialog.askdirectory(title='촬영 묶음 폴더 선택 (manifest.jsonl이 있는 폴더)', initialdir=self.output_root)
        if not path:
            return
        self.message.set('기존 이미지·기록·해시를 검증 중입니다…')
        self.job(lambda: CollectionSession.open(Path(path)), self.finish_open)

    def finish_open(self, session):
        self.session = session
        self.session_stream = None
        if session.profile is not None:
            matching = self.profile is not None and capture.profile_digest(self.profile) == capture.profile_digest(session.profile)
            self.profile = session.profile
            if not matching:
                self.labels = {k: k for k in session.profile['scenarios']}
            self.product_text.set(f"{session.profile['product_id']} · 저장된 설정 사본")
            self.scenario_keys = list(session.profile['scenarios'])
        else:
            self.profile = None
            self.scenario_keys = list(capture.SCENARIOS)
            self.labels = {k: k for k in self.scenario_keys}
            self.product_text.set('기존 schema v1 · 검증/열람 전용')
        self.scenario_combo.configure(values=[f'{self.labels[k]} ({k})' for k in self.scenario_keys])
        self.scenario_combo.current(0)
        if session.info:
            self.conditions.set(session.info['conditions'])
            frame = self.guard(self.camera.snapshot)
            if frame is not None:
                try:
                    session.can_continue(self.profile, frame, self.conditions.get(), self.camera.source_kind)
                    if messagebox.askyesno('동일 촬영 조건 확인',
                        '같은 실제 카메라·조명·배경·높이의 연속 촬영인가요?\n'
                        '장치 인덱스만으로 동일 카메라를 확인할 수 없습니다.\n'
                        '조건이 바뀌었다면 아니오를 누르고 새 묶음을 만드세요.'):
                        self.session_stream = frame.stream_id
                except Exception as exc:
                    self.message.set(f'검증/열람 완료. 계속 촬영 불가: {exc}')
        session.set_scenario(self.selected_scenario())
        self.refresh_session()
        self.show_recent()
        if self.session_stream is not None:
            self.message.set('기존 기록 검증 완료. 새 물체 배치로 이어서 촬영합니다.')
        else:
            self.message.set('기존 기록 검증/수량 복원 완료. 새 묶음으로 촬영하거나 연결·조건을 확인하고 다시 여세요.')

    def change_scenario(self, event=None):
        if self.session:
            self.guard(lambda: self.session.set_scenario(self.selected_scenario()))
            self.refresh_session()
        self.message.set('실제 물체 상태와 선택한 정답이 일치하는지 확인하세요. 상태 변경은 새 배치입니다.')

    def new_episode(self):
        if self.session:
            self.guard(self.session.new_episode)
            self.refresh_session()
            self.message.set('새 배치로 구분했습니다. 실제 재배치 후 한 장 저장을 누르세요.')
        else:
            self.message.set('촬영 묶음을 먼저 만드세요.')

    def refresh_session(self):
        self.session_text.set('묶음: '+self.session.session_id)
        self.episode_text.set('배치: '+self.session.episode_id)
        self.refresh_counts()

    def refresh_counts(self):
        for item in self.counts.get_children():
            self.counts.delete(item)
        count = self.session.counts if self.session else {}
        for key in dict.fromkeys([*self.scenario_keys, *count]):
            self.counts.insert('', 'end', values=(self.labels.get(key, key), count.get(key, 0)))

    def save(self):
        if self.pending is not None or self.closing:
            return
        def action():
            if self.session is None:
                raise capture.CaptureError('새 촬영 묶음을 먼저 만드세요.')
            frame = self.camera.snapshot()
            if self.session_stream != frame.stream_id:
                raise capture.CaptureError('연결이 바뀌었습니다. 묶음을 새로 만들거나 기존 조건을 확인하고 다시 여세요.')
            self.session.can_continue(self.profile, frame, self.conditions.get(), self.camera.source_kind)
            session = self.session
            self.message.set('한 장 저장 중… PNG·기록·재로드·해시를 확인합니다.')
            self.job(lambda: session.save(frame), self.saved)
        self.guard(action)

    def saved(self, path):
        self.refresh_session()
        self.show_recent()
        self.message.set(f'저장 완료 · 원본 PNG 및 기록 검증 성공: {path}')

    def show_recent(self):
        if self.session and self.session.last_path:
            with Image.open(self.session.last_path) as image:
                image.thumbnail((155, 95))
                self.recent_photo = ImageTk.PhotoImage(image.copy())
            self.recent_label.configure(image=self.recent_photo, text='', width=155, height=95)
            name = self.session.last_path.name
            self.last_text.set('최근 저장: '+(name if len(name) <= 58 else name[:28]+'…'+name[-25:]))

    def open_recent(self):
        if self.session and self.session.last_path:
            self.guard(lambda: os.startfile(str(self.session.last_path)))

    def open_folder(self):
        folder = self.session.folder if self.session else self.output_root
        if folder.is_dir():
            self.guard(lambda: os.startfile(str(folder)))
        else:
            self.message.set('촬영 묶음을 만들면 저장 폴더가 생성됩니다.')

    def update_controls(self):
        busy = self.pending is not None or self.closing
        for widget, normal in self.busy_controls:
            widget.configure(state='disabled' if busy else normal)
        for widget, normal in self.camera_controls:
            widget.configure(state='disabled' if busy or self.camera.process is not None else normal)
        self.connect_button.configure(state='normal' if not busy and self.camera.process is None else 'disabled')
        self.disconnect_button.configure(state='normal' if not busy and self.camera.process is not None else 'disabled')
        fresh = self.camera.state == 'connected' and self.camera.latest is not None and self.camera.latest.fresh()
        ready = self.session is not None and not self.session.failed and not self.session.read_only
        self.save_button.configure(state='normal' if fresh and ready and not busy and self.session_stream is not None else 'disabled')
        self.new_button.configure(state='normal' if fresh and self.profile is not None and not busy else 'disabled')

    def tick(self):
        self.camera.poll()
        if self.pending is not None and self.pending.done():
            future, done = self.pending, self.on_done
            self.pending = self.on_done = None
            self.guard(lambda: done(future.result()))
        if self.closing:
            if self.pending is None and self.camera.process is None:
                self.executor.shutdown(wait=False)
                self.closed = True
                self.root.destroy()
                return
        frame = self.camera.latest
        if self.camera.state == 'connected' and frame is not None:
            c = frame.camera
            mismatch = (c['width'], c['height']) != (c['requested_width'], c['requested_height'])
            fps = '미확인' if c['fps_reported'] is None else f"{c['fps_reported']:g}"
            age = '' if frame.fresh() else ' · 수신 지연: 저장 차단'
            self.camera_text.set(f"후보 {c['index']} / {c['backend']} · 실제 {c['width']}×{c['height']}"
                f" · 장치 보고 FPS {fps} · 포맷 {c['fourcc_reported'] or '미확인'}"
                f"{' · 요청 해상도와 다름 (원본 유지)' if mismatch else ''}{age}")
            token = (frame.stream_id, frame.sequence)
            if token != self.last_preview_token:
                image = Image.fromarray(cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB))
                image.thumbnail((max(100, self.preview.winfo_width()), max(100, self.preview.winfo_height())))
                self.preview_photo = ImageTk.PhotoImage(image)
                self.preview.configure(image=self.preview_photo, text='')
                self.last_preview_token = token
        else:
            states = {'connecting': '연결 중…', 'stopping': '카메라 해제 중…',
                      'disconnected': '미연결', 'error': '연결 오류'}
            text = states.get(self.camera.state, self.camera.state)
            self.camera_text.set(text + (' · '+self.camera.error if self.camera.error else ''))
            self.preview.configure(image='', text=text+'\n후보·backend를 선택하고 연결하세요.')
            self.last_preview_token = None
            if self.camera.state in ('error', 'disconnected'):
                self.session_stream = None
        self.update_controls()
        self.root.after(50, self.tick)

    def close(self):
        self.closing = True
        self.camera.disconnect()
        self.message.set('종료 중… 진행 중인 저장은 끝까지 확인하고 카메라를 해제합니다.')
        self.update_controls()

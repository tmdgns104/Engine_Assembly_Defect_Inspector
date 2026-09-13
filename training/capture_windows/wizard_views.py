"""Human review and progress windows. These views never write camera images."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


class ReviewWindow:
    def __init__(self, app, action):
        self.app, self.action = app, action
        self.window = tk.Toplevel(app.root)
        self.window.title('사진 묶음 확인 · AI 판정 아님')
        width, height = min(1180, app.root.winfo_screenwidth()-80), min(860, app.root.winfo_screenheight()-100)
        self.window.geometry(f'{width}x{height}+{max(0, (app.root.winfo_screenwidth()-width)//2)}+{max(0, (app.root.winfo_screenheight()-height)//2)}')
        self.window.minsize(780, 650)
        self.window.transient(app.root)
        self.window.grab_set()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.photos, self.selected, self.cards, self.select_buttons = [], [], [], []
        self.confirmed = tk.BooleanVar(value=False)
        self.rearranged = tk.BooleanVar(value=False)
        self.reason = tk.StringVar(value='흐림')
        is_setup = action['kind'] == 'setup_review'
        col = app.collection
        roles = col.reference_roles() if is_setup else [s['step_id'] for s in action['block']['steps']]
        self.ids = [col.current[role] for role in roles]
        header = ('기준 사진: 정상과 빈자리가 모두 보이는지 확인하세요.' if is_setup else
                  '각 사진의 실제 상태를 비교하세요. 사진을 누르면 크게 볼 수 있습니다.')
        ttk.Label(self.window, text=header, font=('맑은 고딕', -20, 'bold'), wraplength=1000).pack(fill='x', padx=18, pady=10)
        ttk.Label(self.window, text=col.guide['review_checks'], wraplength=1000).pack(fill='x', padx=18)
        # Scrollable grid supports products with a different number of states.
        viewport = ttk.Frame(self.window)
        viewport.pack(fill='both', expand=True, padx=16, pady=8)
        canvas = tk.Canvas(viewport, bg='#eef2f6', highlightthickness=0)
        self.canvas = canvas
        scroll = ttk.Scrollbar(viewport, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        grid = ttk.Frame(canvas)
        item = canvas.create_window(0, 0, window=grid, anchor='nw')
        def resize(event):
            canvas.itemconfigure(item, width=event.width)
            self.photos.clear()
            rows = min(2, (len(self.ids)+1)//2)
            size = (max(100, event.width//2-35), max(90, min(250, event.height//rows-95)))
            for button, original in self.cards:
                picture = original.copy()
                picture.thumbnail(size)
                photo = ImageTk.PhotoImage(picture, master=self.window)
                self.photos.append(photo)
                button.configure(image=photo)
        canvas.bind('<Configure>', resize)
        grid.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        grid.columnconfigure((0, 1), weight=1)
        for i, aid in enumerate(self.ids):
            a = col.attempts[aid]
            panel = ttk.LabelFrame(grid, text=app.label(a['scenario']), padding=6)
            panel.grid(row=i//2, column=i%2, sticky='nsew', padx=4, pady=4)
            path = col.folder/'sessions'/a['record']['image_path']
            with Image.open(path) as original:
                picture = original.copy()
            button = ttk.Button(panel, command=lambda p=path: self.expand(p))
            button.pack()
            self.cards.append((button, picture))
            selected = tk.BooleanVar(value=False)
            self.selected.append(selected)
            check = ttk.Checkbutton(panel, text='이 사진 다시 촬영', variable=selected)
            check.pack(anchor='w')
            self.select_buttons.append(check)
        bottom = ttk.Frame(self.window, padding=12)
        bottom.pack(fill='x')
        row = ttk.Frame(bottom)
        row.pack(fill='x')
        ttk.Label(row, text='재촬영 이유').pack(side='left')
        ttk.Combobox(row, textvariable=self.reason, values=['흐림', '반사', '손 가림', '잘못된 배치', '기타'],
                     width=18).pack(side='left', padx=8)
        ttk.Checkbutton(row, text='물체도 다시 배치함', variable=self.rearranged).pack(side='left')
        ttk.Button(row, text='선택한 사진 재촬영', command=self.retake).pack(side='right')
        check = ('두 기준 사진에서 검사 영역·양쪽 자리·실물 L/R 대응을 직접 확인했습니다.' if is_setup else
                 '모든 사진의 실제 상태·품질·같은 배치 유지를 직접 확인했습니다.')
        ttk.Checkbutton(bottom, text=check, variable=self.confirmed).pack(anchor='w', pady=8)
        self.accept_button = ttk.Button(bottom, text='묶음 확인 완료 · 계속', command=self.accept)
        self.accept_button.pack(fill='x')

    def expand(self, path):
        view = tk.Toplevel(self.window)
        view.title('원본 보기 · '+Path(path).name)
        view.transient(self.window)
        view.grab_set()
        view.protocol('WM_DELETE_WINDOW', lambda: (view.destroy(), self.window.grab_set()))
        with Image.open(path) as source:
            image = source.copy()
        image.thumbnail((min(1200, view.winfo_screenwidth()-100), min(800, view.winfo_screenheight()-130)))
        photo = ImageTk.PhotoImage(image, master=view)
        label = ttk.Label(view, image=photo)
        label.image = photo
        label.pack()

    def accept(self):
        if not self.confirmed.get():
            self.app.message.set('사진을 직접 비교하고 확인 체크를 표시하세요. 자동 확정하지 않습니다.')
            return
        if any(s.get() for s in self.selected):
            self.app.message.set('재촬영 선택이 남아 있습니다. 선택한 사진을 먼저 다시 촬영하세요.')
            return
        col = self.app.collection
        job = (lambda: col.confirm_setup(True)) if self.action['kind'] == 'setup_review' else (
            lambda: col.accept_batch(self.action['block']['block_id'], True))
        self.close()
        self.app.submit(job)

    def retake(self):
        ids = [aid for aid, selected in zip(self.ids, self.selected) if selected.get()]
        reason, rearranged = self.reason.get().strip(), self.rearranged.get()
        if not ids or not reason:
            self.app.message.set('다시 찍을 사진과 이유를 선택하세요.')
            return
        col = self.app.collection
        self.close()
        def job():
            for aid in ids:
                col.reject(aid, reason, rearranged)
        self.app.submit(job)

    def close(self):
        self.window.destroy()
        self.photos.clear()
        self.cards.clear()
        self.selected.clear()
        self.confirmed = self.rearranged = self.reason = None
        self.app.review_window = None


def progress_window(app):
    summary = app.collection.summary()
    window = tk.Toplevel(app.root)
    window.title('수집 현황 · 저장과 사람 확정은 다릅니다')
    window.geometry('1080x640')
    columns = ('phase', 'round', 'light', 'placement', 'state', 'target', 'saved', 'accepted', 'pending', 'held', 'retake', 'missing', 'skip')
    labels = ('단계', '회차', '조명', '배치', '상태', '목표', '저장', '확정', '검토 대기', '보류', '재촬영', '미수집', '생략 사유')
    tree = ttk.Treeview(window, columns=columns, show='headings')
    for key, label in zip(columns, labels):
        tree.heading(key, text=label)
        tree.column(key, width=72 if key not in ('state', 'skip') else 135, stretch=True)
    scroll = ttk.Scrollbar(window, command=tree.yview)
    scroll.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(fill='both', expand=True)
    for block in summary['by_condition']:
        for state in block['states']:
            values = [block[k] for k in ('phase', 'round_id', 'condition_id', 'placement_id')]
            values += [app.label(state['scenario'])]+[state[k] for k in ('target', 'saved', 'accepted', 'pending', 'held', 'retained_retake', 'missing', 'skip_reason')]
            tree.insert('', 'end', values=[v if v is not None else '' for v in values])
    ttk.Label(window, text=f"원본 해시 중복 묶음 {len(summary['exact_duplicate_groups'])}개 · 원본은 삭제하지 않습니다.").pack(fill='x', padx=12, pady=8)

"""Engine-specific human declarations over the shared Wizard controller."""
import tkinter as tk
from tkinter import ttk

from . import engine_dataset as engine
from .engine_contract import SCENARIO_LABELS, PRODUCT_NAME


class StationControls:
    def __init__(self, window):
        default = engine.station_settings()
        self.choice = tk.StringVar(value='STATION_A')
        self.custom = tk.StringVar(value='')
        self.pc = tk.StringVar(value=default['capture_pc_id'])
        self.camera = tk.StringVar(value=default['camera_id'])
        self.lighting = tk.StringVar(value=default['e02_lighting_id'])
        body = ttk.LabelFrame(window, text='Station · 촬영 PC와 카메라 식별', padding=10)
        body.pack(fill='x', padx=16)
        fields = [('Station', self.choice, ['STATION_A', 'STATION_B', 'CUSTOM']),
                  ('CUSTOM ID', self.custom, None), ('Capture PC ID', self.pc, None),
                  ('Camera ID (실물 식별 이름)', self.camera, None),
                  ('E02 조명 (변경 가능)', self.lighting, ['LEFT_DOMINANT', 'RIGHT_DOMINANT'])]
        for i, (title, variable, choices) in enumerate(fields):
            ttk.Label(body, text=title).grid(row=i, column=0, sticky='w', padx=5, pady=3)
            widget = (ttk.Combobox(body, textvariable=variable, values=choices, state='readonly', width=32)
                      if choices else ttk.Entry(body, textvariable=variable, width=34))
            widget.grid(row=i, column=1, sticky='ew')
        self.choice.trace_add('write', self.apply_default)

    def apply_default(self, *unused):
        self.lighting.set('RIGHT_DOMINANT' if self.choice.get() == 'STATION_B' else 'LEFT_DOMINANT')

    def value(self):
        station = self.custom.get().strip() if self.choice.get() == 'CUSTOM' else self.choice.get()
        return engine.station_settings(station, self.pc.get().strip(), self.camera.get().strip(), self.lighting.get())


def checklist_dialog(app, title, instruction, checks, confirmed):
    window = tk.Toplevel(app.root)
    window.title(title)
    window.transient(app.root)
    window.grab_set()
    app.engine_gate_window = window
    ttk.Label(window, text=instruction, wraplength=690, padding=16).pack(fill='x')
    variables = {key: tk.BooleanVar(value=False) for key in checks}
    for key, label in checks.items():
        ttk.Checkbutton(window, text=label, variable=variables[key]).pack(anchor='w', padx=16, pady=4)

    def close():
        window.destroy()
        app.engine_gate_window = None

    def confirm():
        values = {key: value.get() for key,value in variables.items()}
        engine.require_checks(values, checks)
        close()
        app.submit(lambda: confirmed(values))

    button = ttk.Button(window, text='모두 확인 · 다음 안내', command=confirm, state='disabled')
    button.pack(fill='x', padx=16, pady=12)
    def changed(*unused):
        button.configure(state='normal' if all(v.get() for v in variables.values()) else 'disabled')
    for value in variables.values():
        value.trace_add('write', changed)
    window.protocol('WM_DELETE_WINDOW', lambda: (close(), app.pause()))
    # Explicit controls are also useful for keyboard/accessibility/UI regression.
    window.checks, window.confirm_button = variables, button
    return window


def state_dialog(app, action):
    checks = engine.physical_checklist(app.collection.profile, action['scenario'])
    checks.update(repositioned='엔진을 치웠다가 회전 중심에 다시 놓음', camera_fixed='카메라 고정 유지')
    def confirmed(values):
        physical = {k:v for k,v in values.items() if k not in ('repositioned', 'camera_fixed')}
        app.collection.confirm_state_preparation(values['repositioned'], values['camera_fixed'], physical)
    return checklist_dialog(app, 'Scenario 물리 상태 확인',
        f"{SCENARIO_LABELS[action['scenario']]} [{action['scenario']}]\n모든 항목을 확인해야 촬영을 시작할 수 있습니다.", checks, confirmed)


def crank_dialog(app, action):
    phase = engine.crank_for_action(action)
    return checklist_dialog(app, 'Crank Phase · 사람 확인',
        f'손잡이 {int(phase[-3:])}도 [{phase}]\n0° 기준 손잡이 위치를 정해 표시한 뒤 상대 목표에 맞추세요.\nEncoder 없음 · crank_sensor_verified=false',
        engine.CRANK_CHECKS, app.collection.confirm_crank)


def challenge_dialog(app):
    if app.review_window or app.lighting_window or app.engine_gate_window:
        raise ValueError('현재 확인 창을 먼저 완료하세요.')
    window = tk.Toplevel(app.root)
    window.title('Challenge Capture · Main 288장과 별도')
    window.transient(app.root)
    window.grab_set()
    scenario = tk.StringVar(value='LIGHT_LEFT_WEAK')
    angle = tk.StringVar(value='ANGLE_000')
    crank = tk.StringVar(value='CRANK_000')
    lighting = tk.StringVar(value='BALANCED')
    notes = tk.StringVar(value='')
    for title, value, choices in [('Challenge', scenario, [k for k in engine.CHALLENGES if k != 'CONVEYOR_MOVING']),
        ('Engine 목표', angle, [p['id'] for p in app.plan['placements']]), ('Crank 목표', crank, engine.CRANK_PHASES),
        ('기준 조명', lighting, ['BALANCED', 'ASYMMETRIC'])]:
        ttk.Label(window, text=title, padding=(16,4)).pack(anchor='w')
        ttk.Combobox(window, textvariable=value, values=choices, state='readonly', width=40).pack(fill='x', padx=16)
    words = tk.StringVar()
    def update(*unused):
        words.set(SCENARIO_LABELS[scenario.get()]+'\n'+engine.CHALLENGES[scenario.get()])
    scenario.trace_add('write', update)
    update()
    ttk.Label(window, textvariable=words, wraplength=570, padding=16).pack()
    ttk.Label(window, text='실제 조명/가림/이탈/제거한 비검사 부품 설명 (필수)', padding=(16,4)).pack()
    ttk.Entry(window, textvariable=notes, width=65).pack(fill='x', padx=16)
    ttk.Label(window, text='capture_truth_result=REVIEW · exclude_from_training=true\nERROR는 이미지 Scenario가 아닙니다. CONVEYOR_MOVING은 향후 Pilot용 예약값입니다.', padding=16).pack()
    def begin():
        values = (scenario.get(), angle.get(), crank.get(), lighting.get(), notes.get().strip())
        if not values[-1]:
            app.message.set('실제 Challenge 조건 설명을 입력하세요.')
            return
        window.destroy()
        app.submit(lambda: app.collection.add_challenge(*values), lambda _: resume())
    def resume():
        app.paused = False
        app.last_action_key = None
    ttk.Button(window, text='Challenge 준비 시작', command=begin).pack(fill='x', padx=16, pady=12)


def rotation_status(app, action, placement):
    col = app.collection
    text = PRODUCT_NAME+' · '+(col.info['station']['station_id'] if col else 'Station 선택 후 Pilot 준비')
    text += '\n정상 기대 수량: 회색 파이프 2개 (gray_pipe) · 상단 배기구 1개 (exhaust_top) · 문양 모듈 1개 (symbol_module)'
    if not col:
        return text+'\nMain 288 / Train 144 · Validation 72 · Test Reserved 72 · Total 288 · E04 LOCKED'
    block = action.get('block')
    main_accepted = sum(len(group) for bid,group in col.accepted.items() if col.block_by_id[bid]['phase'] == 'main')
    text += f'\nMain Progress {main_accepted}/288 · E04 '+('LABELING UNLOCKED / 학습금지' if col.final_test_unlocked else 'LOCKED')
    if block:
        scenario = action.get('scenario', block['scenario'])
        phase = engine.crank_for_action(action)
        result = engine.truth_fields(col.profile, scenario)['capture_truth_result']
        light = engine.lighting_id(col, block['condition_id'], scenario)
        index = next((i for i,s in enumerate(block['steps']) if s['placement_id'] == placement['id']), 0)
        following = block['steps'][index+1]['placement_id'].removeprefix('ANGLE_')+'°' if index+1 < len(block['steps']) else '검토'
        ids = {aid for group in col.accepted.values() for aid in group.values()}
        scenario_count = sum(col.current.get(s['step_id']) in ids for s in block['steps'])
        round_count = sum(len(group) for bid,group in col.accepted.items() if col.block_by_id[bid]['round_id'] == block['round_id'])
        reference = 'SELF (NORMAL)' if scenario == 'NORMAL' else 'MISSING'
        for row in engine.metadata_rows(col):
            if (row['scenario'] == 'NORMAL' and row['human_review_status'] == 'ACCEPT' and row['setup_id'] == col.setup_id
                    and row['round_id'] == block['round_id'] and row['lighting_id'] == light
                    and row['engine_angle_target_deg'] == placement['angle_deg'] and row['crank_phase_id'] == phase):
                reference = 'AVAILABLE'
                break
        text += (f"\nRound {block['round_id']} {block['purpose']} · {SCENARIO_LABELS[scenario]} [{scenario}] · Expected Result {result}"
                 f"\n손잡이 {int(phase[-3:])}도 [{phase}] · Engine 목표 각도 {placement['angle_deg']:03d}° · Lighting {light}"
                 f"\nANGLE {index+1} / {len(block['steps'])} · 다음 {following} · Scenario Progress {scenario_count}/{len(block['steps'])}"
                 f" · Round Progress {round_count}/{'72' if block['phase']=='main' else '별도'} · Reference Normal: {reference}")
        if result == 'FAIL' and reference == 'MISSING':
            text += '\n경고: 같은 조건의 승인 NORMAL 없음 · labeling_ready=false'
    return text

"""Make guidance-only crops from supplied mixed-state photos with provenance."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps

source = Path('D:/OnDevice과정/팀프로젝트/엔진모형/잘못끼워진')
target = Path(__file__).parent
examples = {
    'pipe_left': ('_08', (250, 1950, 1400, 2950)),
    'pipe_left_up': ('_06', (700, 1850, 1300, 2950)),
    'pipe_right': ('_04', (1600, 1700, 2250, 2900)),
    'pipe_right_out': ('_07', (1450, 1350, 2450, 2300)),
    'exhaust': ('_02', (950, 780, 1900, 1730)),
    'exhaust_side': ('_01', (1000, 650, 2000, 1600)),
    'symbol': ('_03', (1200, 1750, 1730, 2260)),
}
provenance = {}
for part, (suffix, box) in examples.items():
    name = f'KakaoTalk_20260929_161913676{suffix}.jpg'
    source_file = source / name
    with Image.open(source_file) as original:
        upright = ImageOps.exif_transpose(original)
        crop = upright.crop(box)
        output = target / f'example_{part}.png'
        crop.save(output)
    provenance[part] = {
        'path': output.name, 'source_path': str(source_file),
        'source_sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'crop_box_after_exif_transpose': list(box),
        'crop_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'purpose': 'guidance_only_not_training_original',
        'mixed_state_source': True,
        'instruction': '대상 부품의 형상만 참고. 나머지 부품은 NORMAL 기준으로 유지.',
    }
(target / 'example-provenance.json').write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

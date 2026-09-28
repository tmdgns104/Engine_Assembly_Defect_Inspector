"""Run one explicit Windows GPU baseline, preserving inputs and checkpoint evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import traceback

import torch
import ultralytics
from ultralytics import YOLO
import yaml

from training.scripts.prepare_via_project import digest, read_json, write_json


def run(config_path):
    config_path = Path(config_path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    data_path = Path(config['data']).resolve()
    experiment = Path(config['project']).resolve()
    run_path = experiment / config['name']
    if run_path.exists() or (experiment / 'run_started.json').exists():
        raise ValueError('A baseline has already started here; do not duplicate or overwrite it.')
    for name, expected in read_json(data_path.parent / 'dataset_integrity.json').items():
        if digest(data_path.parent / name) != expected:
            raise ValueError(f'Dataset artifact changed: {name}')
    split = read_json(data_path.parent / 'split_manifest.json')
    if split['test']:
        raise ValueError('This baseline must not consume reserved test images.')
    for path, expected in split['sources'].items():
        if digest(path) != expected:
            raise ValueError('Candidate manifest changed after splitting.')
    model_path = Path(config['model']).resolve()
    if not model_path.is_file() or not torch.cuda.is_available():
        raise ValueError('Local pretrained weights and a working CUDA runtime are required.')
    gpu = torch.cuda.get_device_name(config['device'])
    sample = torch.ones((128, 128), device=f"cuda:{config['device']}")
    if (sample @ sample).sum().item() != 2097152.0:
        raise ValueError('GPU arithmetic verification failed.')
    model = YOLO(str(model_path))
    config.update(model=str(model_path), data=str(data_path), project=str(experiment))
    experiment.mkdir(parents=True, exist_ok=True)
    record = {
        'status': 'RUNNING', 'started_at': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
        'config_path': str(config_path), 'config_sha256': digest(config_path), 'requested_config': config,
        'pretrained_sha256': digest(model_path), 'pretrained_classes': model.names,
        'dataset_sha256': digest(data_path), 'split_sha256': digest(data_path.parent / 'split_manifest.json'),
        'counts': {key: len(split[key]) for key in ('train', 'val', 'test')},
        'torch': torch.__version__, 'ultralytics': ultralytics.__version__, 'cuda': torch.version.cuda,
        'gpu': gpu, 'gpu_matmul_verified': True, 'precision': 'FP32 (AMP disabled)',
        'reproducibility': 'Seed and deterministic flag fixed; cross-version/hardware bitwise reproducibility is not claimed.',
    }
    write_json(experiment / 'run_started.json', record)
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
    started = time.perf_counter()
    try:
        model.train(**config)
        torch.cuda.synchronize()
        duration = time.perf_counter() - started
        actual_device = str(next(model.trainer.model.parameters()).device)
        if not actual_device.startswith('cuda'):
            raise ValueError('Training did not use the required CUDA device.')
        checkpoints = {}
        for name in ('best.pt', 'last.pt'):
            path = run_path / 'weights' / name
            reloaded = YOLO(str(path)).to(f"cuda:{config['device']}")
            if reloaded.names != model.names:
                raise ValueError('Reloaded checkpoint class mapping differs.')
            checkpoints[name] = {'path': str(path), 'sha256': digest(path), 'reload_device': str(next(reloaded.model.parameters()).device)}
        record.update(status='COMPLETE', completed_at=datetime.now(timezone.utc).isoformat(),
                      training_wall_seconds=duration, training_device=actual_device, checkpoints=checkpoints,
                      metrics={key: float(value) for key, value in model.metrics.results_dict.items()},
                      actual_args_path=str(run_path / 'args.yaml'))
        write_json(experiment / 'baseline_result.json', record)
        print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
    except Exception:
        write_json(experiment / 'baseline_failure.json', {
            'status': 'FAILED', 'elapsed_seconds': time.perf_counter() - started, 'traceback': traceback.format_exc(),
        })
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    run(parser.parse_args().config)

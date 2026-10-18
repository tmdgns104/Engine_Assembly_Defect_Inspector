"""config.py에서 새 제품 복제본 생성. 원본/모델/해시 검증은 보존하며 배포하지 않는다."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'jetson'))
from src import config
from src.configuration import package_values, snapshot
from src.recipe.package import load_package


def write_changed(path, value):
    """값이 같으면 원래 byte를 보존해 기존 SHA도 유지한다."""
    if json.loads(path.read_text(encoding='utf-8')) != value:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, source_root=ROOT/'jetson'):
    settings=package_values()
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError('NEW_OUTPUT_DIRECTORY_REQUIRED')
    sources=[Path(source_root)/config.ENGINE_ENVELOPE_PACKAGE,Path(source_root)/config.ENGINE_PARTS_PACKAGE]
    originals=[load_package(path) for path in sources]
    pose_source=sources[1]/config.ENGINE_POSE_REFERENCE
    if digest(pose_source)!=config.ENGINE_POSE_REFERENCE_SHA256:
        raise ValueError('FROZEN_POSE_REFERENCE_MISMATCH')
    if any(path.is_symlink() for source in sources for path in source.rglob('*')):
        raise ValueError('SYMLINK_PACKAGE_NOT_SUPPORTED')
    output.mkdir(parents=True)
    results=[]
    for index,(source,original) in enumerate(zip(sources,originals)):
        destination=output/source.name
        shutil.copytree(source,destination)
        manifest=copy.deepcopy(original.manifest)
        preprocessing=copy.deepcopy(original.preprocessing)
        preprocessing.update(settings['preprocessing'])
        write_changed(destination/manifest['files']['preprocessing']['path'],preprocessing)
        if index==1:
            pose=json.loads(pose_source.read_text(encoding='utf-8'))
            pose['registration'].update(settings['registration'])
            pose['decision_policy'].update(settings['decision_policy'])
            write_changed(destination/config.ENGINE_POSE_REFERENCE,pose)
            recipe=copy.deepcopy(original.recipe)
            recipe.update(presence_confidence=config.ENGINE_PART_CONFIDENCE,
                reference_confidence=config.ENGINE_PRODUCT_CONFIDENCE,
                slot_overlap=config.ENGINE_SLOT_OVERLAP,observation_count=config.REQUIRED_OBSERVATIONS)
            recipe['engine_pose']['sha256']=digest(destination/config.ENGINE_POSE_REFERENCE)
            recipe['engine_pose']['envelope_manifest_sha256']=results[0]['manifest_sha256']
            write_changed(destination/manifest['files']['recipe']['path'],recipe)
        for item in manifest['files'].values():
            item['sha256']=digest(destination/item['path'])
        write_changed(destination/'manifest.json',manifest)
        verified=load_package(destination)
        results.append(dict(path=destination.name,manifest_sha256=verified.manifest_hash,
            source_manifest_sha256=original.manifest_hash,model_sha256=manifest['files']['model']['sha256']))
    receipt={'configuration':snapshot(),'products':results,'applied_to_device':False}
    (output/'CONFIGURATION_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(generate(args.output),ensure_ascii=False))

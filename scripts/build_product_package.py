"""Assemble explicit product documents and trusted local model into a new immutable release."""
import argparse
import json
from pathlib import Path
from src.recipe.package import canonical, load_package, sha256


def build(documents, model, self_test, output, identity):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    manifest=dict(identity,schema_version=1,enabled=True,
                  detector={'backend':'pytorch','task':'detect','output':'ultralytics_xyxy'},files={})
    sources={'model':Path(model),'self_test':Path(self_test)}
    sources.update({kind:Path(documents)/(kind+'.json') for kind in ('classes','preprocessing','recipe','capture')})
    for kind,source in sources.items():
        name='best.pt' if kind=='model' else 'self_test.png' if kind=='self_test' else kind+'.json'
        data=source.read_bytes()
        (output/name).write_bytes(data)
        manifest['files'][kind]={'path':name,'sha256':sha256(data)}
    (output/'manifest.json').write_text(canonical(manifest),encoding='utf-8')
    return load_package(output)


def main():
    parser=argparse.ArgumentParser()
    for name in ('documents','model','self-test','output','product','release','model-version'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    package=build(args.documents,args.model,args.self_test,args.output,
                  {'product_id':args.product,'release_id':args.release,'model_version':args.model_version})
    print(json.dumps({'package':str(package.root),'manifest_sha256':package.manifest_hash,'model_sha256':package.manifest['files']['model']['sha256']}))


if __name__=='__main__':main()

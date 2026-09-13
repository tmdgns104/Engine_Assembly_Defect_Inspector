"""CLI for the same authenticated local maintenance API used by the browser."""
import argparse,json,urllib.request


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8768')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status');sub.add_parser('packages')
    activate=sub.add_parser('activate');activate.add_argument('package_id')
    args=parser.parse_args()
    if not args.url.startswith('http://127.0.0.1:'):raise ValueError('Use the local SSH tunnel')
    base=args.url.rstrip('/')+'/api/v1/'
    path={'status':'health','packages':'packages','activate':'packages/activate'}[args.command]
    request=urllib.request.Request(base+path)
    if args.command=='activate':
        token=json.load(urllib.request.urlopen(base+'session'))['token']
        request=urllib.request.Request(base+path,data=json.dumps({'id':args.package_id}).encode(),
            headers={'Content-Type':'application/json','X-Inspection-Token':token})
    with urllib.request.urlopen(request,timeout=200) as response:print(json.dumps(json.load(response),ensure_ascii=False,indent=2))


if __name__=='__main__':main()

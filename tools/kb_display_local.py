"""Owner-local live Vault browser. Requires explicit local read authorization."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kb_core.local_vault_web import LocalWebError, authorize_current_scope, create_server


class Parser(argparse.ArgumentParser):
    def error(self, message): raise LocalWebError('local_arguments_invalid',400)


def main(argv=None):
    try:
        parser=Parser(description=__doc__)
        commands=parser.add_subparsers(dest='command',required=True)
        authorize=commands.add_parser('authorize')
        for name in ('instance','policy-root','catalog-config','authorization','authorization-document'):
            authorize.add_argument('--'+name,required=True,type=Path)
        authorize.add_argument('--authorization-ref',required=True,type=str)
        authorize.add_argument('--vault-id',required=True,type=str)
        authorize.add_argument('--offset',default=0,type=int)
        authorize.add_argument('--limit',default=255,type=int)
        authorize.add_argument('--path',type=str)
        serve=commands.add_parser('serve')
        for name in ('instance','policy-root','catalog-config','authorization','access-token-file'):
            serve.add_argument('--'+name,required=True,type=Path)
        serve.add_argument('--read-authorized',action='store_true')
        serve.add_argument('--port',required=True,type=int)
        args=parser.parse_args(argv)
        if args.command=='authorize':
            result=authorize_current_scope(instance=args.instance,policy_root=args.policy_root,
                catalog_config=args.catalog_config,authorization_path=args.authorization,
                authorization_document=args.authorization_document,authorization_ref=args.authorization_ref,
                vault_id=args.vault_id,offset=args.offset,limit=args.limit,path=args.path)
            print(json.dumps(result,ensure_ascii=False))
            return 0
        if args.read_authorized is not True: raise LocalWebError('local_read_unauthorized',403)
        server=create_server(instance=args.instance,policy_root=args.policy_root,catalog_config=args.catalog_config,
            authorization_path=args.authorization,access_token_file=args.access_token_file,
            read_authorized=True,port=args.port)
        print(json.dumps({'status':'owner_local_real_vault_web','host':'127.0.0.1','port':server.server_port,
            'sample_data':False,'vault_count':len(server.catalog.coordinator.members.snapshot()['records']),
            'visitor_auth':'bearer-per-request','vault_writes':False,'model_export':False},ensure_ascii=False),flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: return 0
        finally: server.server_close()
    except LocalWebError as error:
        print(json.dumps({'error':{'code':error.code}},ensure_ascii=False)); return 2
    except (OSError,ValueError,TypeError):
        print(json.dumps({'error':{'code':'local_runtime_unavailable'}},ensure_ascii=False)); return 2


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

"""Local create/register/STATE completion in explicit controlled directories."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.completion import Completion, CompletionError
from kb_core.operations import read_request, OperationError
from kb_core.contracts import local_root
from kb_core.contracts import LayerResult

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance',type=Path,required=True)
    parser.add_argument('--builder-state',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--finish',action='store_true',help='Finish an already placed/registered operation; do not create again')
    parser.add_argument('--domain-evidence',type=Path)
    parser.add_argument('--display-config',type=Path)
    args=parser.parse_args(argv)
    try:
        try: local_root(str(args.request))
        except ValueError: raise CompletionError('completion_request_path_invalid') from None
        if not args.finish and (args.domain_evidence is not None or args.display_config is not None):
            raise CompletionError('completion_finish_required')
        service=Completion(args.instance,args.builder_state,args.evidence)
        request=read_request(args.request)
        if args.finish:
            domain=None;sources=None
            if args.domain_evidence is not None:
                local_root(str(args.domain_evidence))
                proof=read_request(args.domain_evidence)
                if not isinstance(proof,dict) or set(proof)!={'result','sources'}:raise CompletionError('completion_domain_invalid')
                domain=LayerResult.model_validate(proof['result']);sources=proof['sources']
            config=None
            if args.display_config is not None:
                local_root(str(args.display_config));config=read_request(args.display_config)
            result=service.finish_create(request,domain_result=domain,domain_sources=sources,display_config=config)
        else:
            result=service.create(request)
        print(json.dumps(result,ensure_ascii=False))
        display=result['receipt']['display_result']['status']
        return 0 if not result.get('completion_evidence_error') and result['receipt']['system_result']['status']=='succeeded' and display!='failed' and (args.display_config is None or display=='succeeded') else 1
    except (CompletionError,OperationError,OSError,ValueError) as error:
        print(json.dumps({'error':{'code':getattr(error,'code','completion_io_failed'),'message':'Controlled local completion refused; inspect preserved evidence.'},'outcome':getattr(error,'outcome',None)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

"""Build one new offline K05 release from explicit controlled scope/approvals."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.display_projection import ProjectionBuilder,ProjectionError
from kb_core.bindings import BindingStore,BindingError
from kb_core.operations import read_request,OperationError

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['instance','descriptions','policies','output-parent','output','request']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        request=read_request(BindingStore(args.request).path)
        if not isinstance(request,dict) or set(request)!={'selected','projection_revision','state_inputs','approvals'}:raise ProjectionError('projection_input_invalid')
        result=ProjectionBuilder(args.instance,args.descriptions,args.policies,args.output_parent).build(args.output,**request)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ProjectionError,BindingError,OperationError,OSError) as error:
        print(json.dumps({'error':{'code':getattr(error,'code','projection_failed'),'message':'Offline projection refused; prior release and owned stage retained.'},'stage':getattr(error,'stage',None)},ensure_ascii=False));return 2

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');raise SystemExit(main())

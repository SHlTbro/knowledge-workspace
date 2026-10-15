"""Explicit offline display update; no service/session/discovery fallback."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.bindings import BindingStore
from kb_core.operations import read_request
from kb_core.display_update import DisplayUpdater,DisplayUpdateError

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['instance','descriptions','policies','output-parent','request']:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--expected-current-hash',required=True,help='Exact current-display raw SHA256, or explicit none for no existing choice')
    args=parser.parse_args(argv)
    try:
        request=read_request(BindingStore(args.request).path)
        expected=None if args.expected_current_hash=='none' else args.expected_current_hash
        result=DisplayUpdater(args.instance,args.descriptions,args.policies,args.output_parent).update(request,expected)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (DisplayUpdateError,ValueError,OSError,TypeError) as error:
        print(json.dumps({'error':{'code':getattr(error,'code','display_update_failed'),'message':'Offline display update incomplete; inspect retained release and prior selection.'},'artifact':getattr(error,'artifact',None)},ensure_ascii=False));return 2

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');raise SystemExit(main())

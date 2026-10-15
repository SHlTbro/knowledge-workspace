"""Explicit source-tree first Node deployment; does not promise all-six readiness."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.deployment import deploy,DeploymentError
from kb_core.python_deployment import MANIFEST,REQUIREMENTS,DeploymentError as PythonDeploymentError,deploy_python_tools
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--operation-id',required=True)
    parser.add_argument('--repo-file',type=Path,action='append');parser.add_argument('--html',type=Path)
    parser.add_argument('--python-tools',action='store_true',help='install the fixed offline SkillSpector/YARA tool bundle')
    parser.add_argument('--python',type=Path);parser.add_argument('--wheelhouse',type=Path)
    parser.add_argument('--timeout',type=float,default=120)
    parser.add_argument('--article-title',default='Controlled deployment article');parser.add_argument('--keep-text',action='append');parser.add_argument('--drop-text',action='append')
    args=parser.parse_args()
    try:
        if args.python_tools:
            if args.repo_file or args.html or not args.python or not args.wheelhouse:
                parser.error('--python-tools requires --python and --wheelhouse, and cannot be combined with Node inputs')
            if not args.timeout.is_integer():
                parser.error('--timeout must be a whole number of seconds in Python tools mode')
            result=deploy_python_tools(args.output_root,args.operation_id,args.python,MANIFEST,REQUIREMENTS,args.wheelhouse,
                                       timeout=int(args.timeout))
            summary={key:result.get(key) for key in ('operation_id','status','all_six_ready','package_count','python_version','python_sha256','venv')}
            summary['attempts']=[{'number':attempt['number'],'status':attempt['status'],'error_code':attempt.get('error_code'),
                                 'commands':[{'step':command['step'],'exit_code':command['exit_code']} for command in attempt['commands']]}
                                for attempt in result.get('attempts',[])]
            print(json.dumps(summary,ensure_ascii=False))
            return 0 if result['status']=='python_toolset_verified' else 1
        if not args.repo_file or not args.html or args.python or args.wheelhouse:
            parser.error('Node mode requires --repo-file and --html; --python/--wheelhouse require --python-tools')
        options={'article_title':args.article_title}
        if args.keep_text is not None:options['keep_text']=args.keep_text
        if args.drop_text is not None:options['drop_text']=args.drop_text
        result=deploy(args.output_root,args.operation_id,args.repo_file,args.html,timeout=args.timeout,**options)
        print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='node_subset_verified' else 1
    except (DeploymentError,PythonDeploymentError) as error:print(json.dumps({'error':{'code':error.code}}));return 2
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf-8');raise SystemExit(main())

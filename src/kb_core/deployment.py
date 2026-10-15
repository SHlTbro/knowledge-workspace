"""Fixed Node first deployment and local business probes; six-family status retained."""
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,re,stat,subprocess,tempfile
from .bindings import BindingStore,BindingError
from .contracts import validate_contract,relative_path
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/product-realignment-20261007/execution/T22/preparation-20261008'
REV=ROOT/'docs/product-realignment-20261007/execution/T22/node-stage-20261008/revision-02'
CATALOG=ROOT/'docs/product-realignment-20261007/execution/T21/revision-05/capability-lock.json'
NODE=Path('Z:/node/node.exe');NPM=Path('Z:/node/node_modules/npm/bin/npm-cli.js')
INPUTS={'repomix':[(PREP/'repomix-package.json','1985a864777c3b16ec8f76eaebc0928996fe1c9836fe608c0364f9a69179bba9'),(REV/'repomix-package-lock.json','97238870258c9f3bd61d2a0fb4aa831d0df6573a863316338e80c80eef7ed013')],
 'defuddle':[(PREP/'defuddle-package.json','dddc96d4321d1e98983032a577c06fb74fd946389e7f5923ceb45c4f5d786fc8'),(PREP/'defuddle-package-lock.json','45f6bba40b52a1238e28614865ea2bc2c6363fb16a7f068886395be7f7c7279d')]}
class DeploymentError(ValueError):
    def __init__(self,code):self.code=code;super().__init__('Controlled deployment refused.')
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _path(value):
    try:return BindingStore(Path(value)).path
    except (BindingError,ValueError,TypeError):raise DeploymentError('deploy_path_invalid') from None
def _io(path,*,checked_parent=False):
    # Caller roots use public validation. Only already-visited owned directory
    # children use the short fence, preserving ordinary/reparse checks without
    # re-resolving every ancestor for each of the 9k installed files.
    extended=Path('\\\\?\\'+str(path)) if os.name=='nt' and len(str(path))>=240 else path
    if checked_parent or extended!=path:
        for component in ((extended,) if checked_parent else (extended,*extended.parents)):
            try:info=component.lstat()
            except FileNotFoundError:continue
            if component.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:raise DeploymentError('deploy_path_invalid')
    return extended
def _bytes(path,limit=1024*1024,*,checked_parent=False):
    path=Path(path) if checked_parent else _path(path)
    try:
        io=_io(path,checked_parent=checked_parent);before=io.lstat();signature=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:raise DeploymentError('deploy_input_not_ordinary')
        with io.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            if signature(before)!=signature(opened):raise DeploymentError('deploy_input_changed')
            # Read the checked size plus one growth byte, not a 64MiB buffer
            # for each tiny installed file. Handle/path stat fences stay intact.
            raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
        current=_io(path if checked_parent else _path(path),checked_parent=checked_parent).lstat()
        if len(raw)>limit or signature(before)!=signature(opened) or signature(before)!=signature(after) or signature(before)!=signature(current):raise DeploymentError('deploy_input_changed')
        return raw
    except OSError:raise DeploymentError('deploy_input_unavailable') from None
def _write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    fd,name=tempfile.mkstemp(prefix='.d-',dir=path.parent)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(name,path)
def _json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise DeploymentError('deploy_state_invalid')
            result[key]=value
        return result
    try:return json.loads(raw,object_pairs_hook=pairs)
    except (ValueError,TypeError):raise DeploymentError('deploy_state_invalid') from None
def _relative(folder,key):
    try:
        if not isinstance(key,str) or relative_path(key)!=key:raise ValueError()
        path=_path(folder/key)
        if not path.is_relative_to(folder):raise ValueError()
        return path
    except (ValueError,TypeError):raise DeploymentError('deploy_artifact_path_invalid') from None
def _payload(folder,work):
    result={};total=0
    for short in ['r','d']:
        start=_path(work/short/'node_modules')
        walk_start=Path('\\\\?\\'+str(start)) if os.name=='nt' else start
        def walk_error(error):raise DeploymentError('deploy_payload_enumeration_failed') from error
        for directory,dirs,files in os.walk(walk_start,followlinks=False,onerror=walk_error):
            directory=Path(str(directory).removeprefix('\\\\?\\'))
            before=_io(directory,checked_parent=True).lstat()
            if not stat.S_ISDIR(before.st_mode):raise DeploymentError('deploy_path_invalid')
            for name in dirs:_io(directory/name,checked_parent=True).lstat() # Parent is the verified visited directory.
            for name in files:
                path=directory/name;raw=_bytes(path,64*1024*1024,checked_parent=True);total+=len(raw)
                if total>256*1024*1024 or len(result)>=20000:raise DeploymentError('deploy_payload_limit')
                result[path.relative_to(folder).as_posix()]=_sha(raw)
            after=_io(directory,checked_parent=True).lstat()
            if (before.st_dev,before.st_ino,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_mtime_ns):raise DeploymentError('deploy_input_changed') # Cooperative fence, not an OS sandbox.
    if not result:raise DeploymentError('deploy_payload_empty')
    return result
def _journal(state,operation_id,request_hash,signature,catalog):
    base={'operation_id','input_hash','input_proof','status','all_six_ready','capabilities','attempts'}
    complete=state.get('status')=='node_subset_verified' if isinstance(state,dict) else False
    if not isinstance(state,dict) or set(state)!=(base|{'verified_outputs','payload_manifest'} if complete else base):raise DeploymentError('deploy_state_invalid')
    if state['operation_id']!=operation_id or state['input_hash']!=request_hash or state['input_proof']!=signature:raise DeploymentError('deploy_operation_conflict')
    if state['all_six_ready'] is not False or state['status'] not in ['pending','node_subset_verified']:raise DeploymentError('deploy_state_invalid')
    attempts=state['attempts']
    if not isinstance(attempts,list) or not 1<=len(attempts)<=16 or any(not isinstance(a,dict) or a.get('number')!=i+1 or a.get('status') not in ['pending','node_subset_verified'] or not isinstance(a.get('commands'),list) for i,a in enumerate(attempts)):raise DeploymentError('deploy_state_invalid')
    if attempts[-1]['status']!=state['status']:raise DeploymentError('deploy_state_invalid')
    try:validate_contract('CapabilityLock',state['capabilities'])
    except ValueError:raise DeploymentError('deploy_state_invalid') from None
    current=state['capabilities']
    if current['release']!=catalog['release'] or len(current['capabilities'])!=6:raise DeploymentError('deploy_state_invalid')
    for row,original in zip(current['capabilities'],catalog['capabilities']):
        if {k:v for k,v in row.items() if k!='verification'}!={k:v for k,v in original.items() if k!='verification'}:raise DeploymentError('deploy_state_invalid')
        if row['id'] not in ['repo-distillation','article-session'] and row['verification']!=original['verification']:raise DeploymentError('deploy_state_invalid')
        if complete and row['id'] in ['repo-distillation','article-session'] and not all(row['verification'][k] for k in ['declared','installed','configured','runtime_verified']):raise DeploymentError('deploy_state_invalid')
    if complete:
        prefix='a'+str(attempts[-1]['number'])
        wanted={prefix+'/'+name for name in ['repo.xml','article-result.json','article.md','r/node_modules/repomix/bin/repomix.cjs','d/node_modules/defuddle/dist/cli.js','r/package-lock.json','d/package-lock.json']}
        outputs=state['verified_outputs'];manifest=state['payload_manifest']
        if not isinstance(outputs,dict) or set(outputs)!=wanted or not isinstance(manifest,dict) or set(manifest)!={'path','sha256'} or manifest['path']!=prefix+'/payload-manifest.json':raise DeploymentError('deploy_state_invalid')
        if any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in [*outputs.values(),manifest['sha256']]):raise DeploymentError('deploy_state_invalid')
        if [a.get('step') for a in attempts[-1]['commands']]!=['repomix-install','repomix-local-code','defuddle-install','defuddle-local-article'] or any(a.get('exit_code')!=0 for a in attempts[-1]['commands']):raise DeploymentError('deploy_state_invalid')
@contextmanager
def _lock(root):
    # ponytail: one cooperative lock for this bounded installer, no transaction platform.
    import msvcrt
    with _path(root/'.deploy-lock').open('a+b') as stream:
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise DeploymentError('deploy_busy') from None
        try:yield
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
def deploy(output_root,operation_id,repo_files,html_file,*,timeout=120,article_title='Controlled deployment article',keep_text=('FIRST_BODY_MARKER','LAST_BODY_MARKER'),drop_text=('UNWANTED_NAVIGATION_MARKER','UNWANTED_FOOTER_MARKER')):
    if not isinstance(operation_id,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}',operation_id):raise DeploymentError('deploy_operation_invalid')
    if not isinstance(timeout,(int,float)) or not 0<timeout<=180:raise DeploymentError('deploy_timeout_invalid')
    if not isinstance(article_title,str) or not 1<=len(article_title)<=128 or any(not isinstance(items,(tuple,list)) or not 1<=len(items)<=8 or any(not isinstance(x,str) or not 1<=len(x)<=128 for x in items) for items in [keep_text,drop_text]):raise DeploymentError('deploy_article_expectation_invalid')
    sources=[]
    if not isinstance(repo_files,list) or not 1<=len(repo_files)<=3:raise DeploymentError('deploy_source_scope_invalid')
    for value in repo_files:
        path=_path(value)
        if path.parent!=_path(ROOT/'src/kb_core') or path.suffix!='.py':raise DeploymentError('deploy_source_scope_invalid')
        sources.append((path.name,_bytes(path)))
    if len({name.casefold() for name,_ in sources})!=len(sources):raise DeploymentError('deploy_source_scope_invalid')
    article=_bytes(html_file,8*1024*1024);catalog_raw=_bytes(CATALOG);catalog=json.loads(catalog_raw);validate_contract('CapabilityLock',catalog)
    fixed={};signature={'catalog':_sha(catalog_raw),'repo':[(name,_sha(raw)) for name,raw in sources],'html':_sha(article),'node':_sha(_bytes(NODE,128*1024*1024)),'npm':_sha(_bytes(NPM)),'packages':{}}
    for family,entries in INPUTS.items():
        fixed[family]=[]
        for path,wanted in entries:
            raw=_bytes(path)
            if _sha(raw)!=wanted:raise DeploymentError('deploy_fixed_input_changed')
            fixed[family].append(raw)
        signature['packages'][family]=[wanted for _,wanted in entries]
    signature['article_expectation']={'title':article_title,'keep':list(keep_text),'drop':list(drop_text)}
    signature=json.loads(json.dumps(signature)) # JSON-stable proof: persisted arrays equal the request.
    if signature['node']!='9a4eb5f1c29c6a2e93852ead46b999e284a6a5ca8bab4d4e241d587d025a52de' or signature['npm']!='3ce7cba6f5128dd5f54c98b6a5036b0f850496878cc2e21044b675fe3c594e3e':raise DeploymentError('deploy_host_tool_changed')
    request_hash=_sha(json.dumps(signature,sort_keys=True,separators=(',',':')).encode('utf-8'))
    root=_path(output_root)
    if root==ROOT or ROOT.is_relative_to(root) or root.is_relative_to(ROOT/'src') or root.is_relative_to(ROOT/'.venv') or root.is_relative_to(ROOT/'.tools'):raise DeploymentError('deploy_output_scope_invalid')
    marker=root/'.deploy-root.json'
    if root.exists():
        if not marker.is_file() or json.loads(_bytes(marker))!={'format':'kb-node-deploy-1'}:raise DeploymentError('deploy_unowned_root')
    else:root.mkdir();_write(marker,{'format':'kb-node-deploy-1'})
    with _lock(root):
        folder=_path(root/('o-'+_sha(operation_id.encode('utf-8'))[:12]));folder.mkdir(exist_ok=True)
        journal=folder/'operation.json'
        if journal.exists():
            state=_json(_bytes(journal,4*1024*1024));_journal(state,operation_id,request_hash,signature,catalog)
            if state['status']=='node_subset_verified':
                for relative,wanted in state['verified_outputs'].items():
                    if _sha(_bytes(_relative(folder,relative),8*1024*1024))!=wanted:raise DeploymentError('deploy_completed_artifact_changed')
                proof=state['payload_manifest'];raw=_bytes(_relative(folder,proof['path']),8*1024*1024)
                if _sha(raw)!=proof['sha256']:raise DeploymentError('deploy_payload_changed')
                expected=_json(raw)
                if not isinstance(expected,dict) or not expected:raise DeploymentError('deploy_state_invalid')
                for key,digest in expected.items():
                    try:
                        if not isinstance(key,str) or relative_path(key)!=key:raise ValueError()
                    except ValueError:raise DeploymentError('deploy_artifact_path_invalid') from None
                    if not key.startswith(tuple('a'+str(len(state['attempts']))+'/'+short+'/node_modules/' for short in ['r','d'])) or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise DeploymentError('deploy_state_invalid')
                if _payload(folder,folder/('a'+str(len(state['attempts']))))!=expected:raise DeploymentError('deploy_payload_changed')
                return state
        else:state={'operation_id':operation_id,'input_hash':request_hash,'input_proof':signature,'status':'pending','all_six_ready':False,'capabilities':catalog,'attempts':[]}
        if len(state['attempts'])>=16:raise DeploymentError('deploy_attempt_limit')
        attempt={'number':len(state['attempts'])+1,'status':'pending','timeout':timeout,'commands':[]};state['attempts'].append(attempt);_write(journal,state)
        work=folder/('a'+str(attempt['number']));work.mkdir();sample=work/'sample';sample.mkdir()
        for name,raw in sources:(sample/name).write_bytes(raw)
        (work/'article.html').write_bytes(article)
        empty=work/'empty-user.npmrc';empty.write_bytes(b'');empty_global=work/'empty-global.npmrc';empty_global.write_bytes(b'');cache=_path(root/'cache');cache.mkdir(exist_ok=True)
        env={k:v for k,v in os.environ.items() if k.upper() in ['SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT','LOCALAPPDATA','APPDATA','USERPROFILE']}
        env.update(NO_COLOR='1',DO_NOT_TRACK='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
        def command(argv,cwd,label):
            try:
                p=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
                result={'step':label,'argv':[str(x) for x in argv],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
            except subprocess.TimeoutExpired:result={'step':label,'argv':[str(x) for x in argv],'exit_code':None,'timed_out':True}
            attempt['commands'].append(result);_write(journal,state)
            if result['exit_code']!=0:raise DeploymentError('deploy_step_pending')
            return result['stdout']
        try:
            for family in ['repomix','defuddle']:
                directory=work/('r' if family=='repomix' else 'd');directory.mkdir()
                for name,raw in zip(['package.json','package-lock.json'],fixed[family]):(directory/name).write_bytes(raw)
                command([NODE,NPM,'ci','--ignore-scripts','--no-audit','--no-fund','--registry=https://registry.npmjs.org','--cache',cache,'--userconfig',empty,'--globalconfig',empty_global,'--fetch-retries=0','--fetch-timeout=30000'],directory,family+'-install')
                row=next(r for r in state['capabilities']['capabilities'] if r['id']==('repo-distillation' if family=='repomix' else 'article-session'))
                row['verification'].update(installed=True,observed_at=datetime.now(timezone.utc).isoformat(),evidence_refs=[journal.relative_to(root).as_posix()])
                cli=directory/'node_modules'/family/('bin/repomix.cjs' if family=='repomix' else 'dist/cli.js');_bytes(cli)
                row['verification']['configured']=True;_write(journal,state)
                if family=='repomix':
                    output=work/'repo.xml';config=work/'repomix.json';config.write_text('{}',encoding='utf-8')
                    command([NODE,cli,sample,'--config',config,'--output',output,'--style','xml','--quiet'],directory,'repomix-local-code')
                    packed=_bytes(output,4*1024*1024).decode('utf-8')
                    entries=re.findall(r'<file path="([^"]+)">',packed)
                    if len(entries)!=len(sources) or set(entries)!={name for name,_ in sources} or not all(raw.decode('utf-8').splitlines()[0] in packed for _,raw in sources):raise DeploymentError('deploy_business_probe_failed')
                else:
                    raw=command([NODE,cli,'parse',work/'article.html','--json','--markdown'],directory,'defuddle-local-article');(work/'article-result.json').write_text(raw,encoding='utf-8')
                    extracted=json.loads(raw);content=extracted.get('content','')
                    visible=content.replace('\\_','_') # Markdown literal underscore escaping, not changed output.
                    if extracted.get('title')!=article_title or not all(x in visible for x in keep_text) or any(x in visible for x in drop_text):raise DeploymentError('deploy_business_probe_failed')
                    (work/'article.md').write_text(content,encoding='utf-8')
                row['verification']['runtime_verified']=True;_write(journal,state)
            artifacts=[work/'repo.xml',work/'article-result.json',work/'article.md',work/'r/node_modules/repomix/bin/repomix.cjs',work/'d/node_modules/defuddle/dist/cli.js',work/'r/package-lock.json',work/'d/package-lock.json']
            state['verified_outputs']={path.relative_to(folder).as_posix():_sha(_bytes(path,8*1024*1024)) for path in artifacts}
            payload=work/'payload-manifest.json';_write(payload,_payload(folder,work));state['payload_manifest']={'path':payload.relative_to(folder).as_posix(),'sha256':_sha(_bytes(payload,8*1024*1024))}
            validate_contract('CapabilityLock',state['capabilities']);attempt['status']='node_subset_verified';state['status']='node_subset_verified'
        except (DeploymentError,OSError,ValueError) as error:
            attempt['error_code']=getattr(error,'code','deploy_probe_error')
            for key in ['verified_outputs','payload_manifest']:
                if key in state:attempt[key+'_partial']=state.pop(key)
        _write(journal,state);_write(folder/'capability-state.json',state['capabilities']);return state

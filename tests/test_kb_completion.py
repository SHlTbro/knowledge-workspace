import hashlib
import importlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.builder import plan_hash
from kb_core.members import MemberStore
from kb_core.operations import Coordinator
from kb_core.writer import LocalWriter, Authorization

def api():
    try:return importlib.import_module('kb_core.completion')
    except ModuleNotFoundError:pytest.fail('T18 completion missing')

def setup(tmp_path):
    instance=tmp_path/'instance';instance.mkdir();MemberStore(instance/'members.json').create()
    build=tmp_path/'build';build.mkdir();evidence=tmp_path/'evidence';evidence.mkdir()
    target=tmp_path/'new-domain'
    raw=b'Native generic notes\n'
    plan={'operation_id':'build-one','target':str(target),'files':[{'path':'notes.txt','kind':'text','text':raw.decode(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}]}
    member={'schema_version':'kb-contracts-1.0','revision':1,'vault_id':'v1','aliases':['native'],'name':'Fixture','purpose_ref':'purpose.md','agents_ref':'AGENTS.md','navigation_refs':[],'core_version':'1.0','profiles':[],'location_ref':'b1','display_ref':None,'enabled':True}
    inputs={'capabilities':{'release':'fixture','capabilities':[]},'maintenance':{'status':'unknown','observed_at':None,'evidence_refs':[]},'display':{'status':'unknown','projection_revision':None,'observed_at':None}}
    request={'operation_id':'create-one','plan':plan,'expected_hash':plan_hash(plan),'authorized_target':str(target),'authorized_source_roots':[], 'allow_create':True,'allow_register':True,'registration':{'member':member,'root':str(target),'expected_collection_revision':1,'expected_binding_revision':0,'expected_generation':0},'state_inputs':inputs,'display_requested':True}
    return api().Completion(instance,build,evidence),request,target,instance,evidence

def test_actual_create_register_state_without_web_or_schema(tmp_path):
    service,request,target,instance,evidence=setup(tmp_path)
    out=service.create(request)
    assert target.joinpath('notes.txt').read_bytes()==b'Native generic notes\n'
    assert Coordinator(instance).resolve('native')['binding']['status']=='online'
    assert out['receipt']['system_result']['status']=='succeeded'
    assert out['receipt']['domain_result']['status']=='not_run'
    assert out['receipt']['display_result']['status']=='pending'
    assert out['state']['check_exit_code']==0
    assert out['state']['state']['display']['status']=='unknown'
    assert service.create(request)['replayed'] is True

def test_review_hash_and_authorization_before_placement(tmp_path):
    service,r,target,_,_=setup(tmp_path);r['allow_create']=False
    with pytest.raises(api().CompletionError):service.create(r)
    assert not target.exists()
    r['allow_create']=True;r['expected_hash']='0'*64
    with pytest.raises(api().CompletionError):service.create(r)
    assert not target.exists()

def test_registration_failure_preserves_new_content_and_reports_partial(tmp_path):
    service,r,target,instance,_=setup(tmp_path)
    (instance/'members.json.lock').write_bytes(b'')
    out=service.create(r)
    assert out['receipt']['system_result']['status']=='pending'
    assert target.joinpath('notes.txt').exists()
    assert out['registration_error']=='operation_partial'
    assert Coordinator(instance).operation_issues()
    with pytest.raises(api().CompletionError,match='completion_incomplete'):service.create(r)

def test_request_drift_and_source_drift_no_replay_success(tmp_path):
    service,r,target,_,_=setup(tmp_path);service.create(r)
    drift=json.loads(json.dumps(r));drift['registration']['member']['name']='Different'
    with pytest.raises(api().CompletionError,match='completion_conflict'):service.create(drift)
    target.joinpath('notes.txt').write_bytes(b'changed')
    with pytest.raises(api().CompletionError):service.create(r)

def test_finish_write_reuses_real_writer_native_evidence(tmp_path):
    service,r,target,instance,evidence=setup(tmp_path);service.create(r)
    co=Coordinator(instance)
    writer=LocalWriter(co.members,co.bindings,'v1',authorization=Authorization('v1','b1','native',True),evidence_root=evidence)
    writer.write('new.txt',b'new')
    out=service.finish_write(writer,state_inputs=r['state_inputs'],display_requested=False)
    assert out['receipt']['domain_result']['status']=='not_run'
    assert out['receipt']['system_result']['status']=='succeeded'
    assert out['receipt']['display_result']['status']=='not_run'
    assert target.joinpath('new.txt').read_bytes()==b'new'

def test_target_no_overwrite_and_bad_member_before_build(tmp_path):
    service,r,target,_,_=setup(tmp_path);r['registration']['member']['core_version']=None
    with pytest.raises(api().CompletionError):service.create(r)
    assert not target.exists()

def test_display_not_requested_stays_not_run(tmp_path):
    service,r,_,_,_=setup(tmp_path);r['display_requested']=False
    assert service.create(r)['receipt']['display_result']['status']=='not_run'

def test_native_finish_requires_exact_sources_and_real_external_evidence(tmp_path):
    from kb_core.contracts import LayerResult
    service,r,target,_,evidence=setup(tmp_path);service.create(r)
    log=evidence/'native-lint.txt'
    # Actual caller-side native check in this fixture; Completion never executes it.
    checked={'notes.txt':hashlib.sha256((target/'notes.txt').read_bytes()).hexdigest()}
    assert (target/'notes.txt').read_text(encoding='utf-8').startswith('Native generic')
    log.write_text('Caller native text check passed; sources pinned\n',encoding='utf-8')
    domain=LayerResult(status='succeeded',evidence_refs=['native-lint.txt'])
    with pytest.raises(api().CompletionError,match='completion_domain_unbound'):
        service.finish_create(r,domain_result=domain,domain_sources={'notes.txt':'0'*64})
    out=service.finish_create(r,domain_result=domain,domain_sources=checked)
    assert out['receipt']['domain_result']['status']=='succeeded'
    log.unlink()
    with pytest.raises(api().CompletionError,match='completion_domain_evidence_missing'):
        service.finish_create(r,domain_result=domain,domain_sources=checked)

def test_state_failure_after_registration_keeps_root_and_diagnostics(tmp_path):
    service,r,target,instance,_=setup(tmp_path);r['state_inputs']={}
    with pytest.raises(api().CompletionError) as error:service.create(r)
    assert error.value.outcome['root_preserved'] is True
    assert target.joinpath('notes.txt').exists() and Coordinator(instance).resolve('v1')['binding']['status']=='online'
    with pytest.raises(api().CompletionError,match='completion_incomplete'):service.create(r)

def test_replay_after_member_disable_rejects_old_success(tmp_path):
    service,r,target,instance,_=setup(tmp_path);service.create(r)
    store=MemberStore(instance/'members.json');member=store.resolve('v1').model_dump();member['enabled']=False;member['revision']=2
    store.update('v1',member,expected_collection_revision=2,expected_record_revision=1)
    with pytest.raises(api().CompletionError):service.create(r)
    assert target.joinpath('notes.txt').exists()

def test_real_cli_create_and_drift(tmp_path):
    import subprocess
    service,r,target,instance,evidence=setup(tmp_path)
    path=tmp_path/'request.json';path.write_text(json.dumps(r),encoding='utf-8')
    command=[sys.executable,'-B',str(Path(__file__).resolve().parents[1]/'tools/kb_complete.py'),'--instance',str(instance),'--builder-state',str(tmp_path/'build'),'--evidence',str(evidence),'--request',str(path)]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0 and json.loads(result.stdout)['receipt']['domain_result']['status']=='not_run'
    r['display_requested']=False;path.write_text(json.dumps(r),encoding='utf-8')
    refused=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    assert refused.returncode==2 and json.loads(refused.stdout)['error']['code']=='completion_conflict'

def test_writer_modify_delete_and_evidence_root_mismatch_is_pending(tmp_path):
    service,r,target,instance,evidence=setup(tmp_path);service.create(r)
    co=Coordinator(instance);grant=Authorization('v1','b1','native',True,True)
    other=tmp_path/'other-evidence';other.mkdir()
    writer=LocalWriter(co.members,co.bindings,'v1',authorization=grant,evidence_root=other)
    before=hashlib.sha256((target/'notes.txt').read_bytes()).hexdigest()
    writer.write('notes.txt',b'modified',expected_hash=before)
    writer.write('to-delete.txt',b'delete')
    writer.delete('to-delete.txt',expected_hash=hashlib.sha256(b'delete').hexdigest())
    out=service.finish_write(writer,state_inputs=r['state_inputs'])
    assert out['receipt']['system_result']['status']=='pending' and out['state_error']
    assert (target/'notes.txt').read_bytes()==b'modified' and not (target/'to-delete.txt').exists()
    assert out['receipt']['domain_result']['status']=='not_run'

def test_self_system_evidence_case_alias_is_not_native_validation(tmp_path):
    from kb_core.contracts import LayerResult
    service,r,target,_,evidence=setup(tmp_path);out=service.create(r)
    ref=out['receipt']['system_result']['evidence_refs'][0]
    alias=ref.upper()
    assert (evidence/alias).read_bytes()==(evidence/ref).read_bytes()
    sources={'notes.txt':hashlib.sha256((target/'notes.txt').read_bytes()).hexdigest()}
    with pytest.raises(api().CompletionError,match='completion_domain_unbound'):
        service.finish_create(r,domain_result=LayerResult(status='succeeded',evidence_refs=[alias]),domain_sources=sources)

def test_corrupt_history_builder_list_refuses_create_and_finish(tmp_path):
    service,r,target,_,evidence=setup(tmp_path);service.create(r)
    journal=evidence/'completion/create-one.json'
    row=json.loads(journal.read_text(encoding='utf-8'));row['outcome']['builder']['files']=[]
    journal.write_text(json.dumps(row),encoding='utf-8')
    with pytest.raises(api().CompletionError):service.create(r)
    with pytest.raises(api().CompletionError):service.finish_create(r)
    assert (target/'notes.txt').read_bytes()==b'Native generic notes\n'

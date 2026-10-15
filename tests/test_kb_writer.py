"""T17 behavior through real member/binding stores and temporary local bytes."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kb_core.members import MemberStore
from kb_core.bindings import BindingStore
from kb_core.contracts import LayerResult, validate_contract


def api():
    try:
        return importlib.import_module('kb_core.writer')
    except ModuleNotFoundError:
        pytest.fail('T17 LocalWriter is missing')


def digest(raw): return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def scope(tmp_path):
    root=tmp_path/'vault'; root.mkdir()
    state=tmp_path/'state'; state.mkdir()
    members=MemberStore(state/'members.json'); members.create()
    members.register({'schema_version':'kb-contracts-1.0','revision':1,'vault_id':'vault-a',
        'aliases':['native-a'],'name':'Example','purpose_ref':'purpose.md','agents_ref':'AGENTS.md',
        'navigation_refs':['index.md'],'core_version':'1.0','profiles':[],
        'location_ref':'binding-a','display_ref':None,'enabled':True},expected_collection_revision=1)
    bindings=BindingStore(state/'bindings.json')
    bindings.bind('binding-a','vault-a',root,expected_revision=0,expected_generation=0)
    evidence=tmp_path/'evidence'; evidence.mkdir()
    return root,members,bindings,evidence


def writer(scope, **permission):
    root,members,bindings,evidence=scope
    values={'vault_id':'vault-a','binding_id':'binding-a','source_kind':'managed',
            'allow_write':True,'allow_delete':True}
    values.update(permission)
    return api().LocalWriter(members,bindings,'native-a',authorization=api().Authorization(**values),evidence_root=evidence)


def refuses(code, operation):
    with pytest.raises(api().WriterError) as exc:
        operation()
    assert exc.value.code==code


def domain_check(scope, sources):
    root,_,_,evidence=scope
    # A real fixture-specific domain check; T17 does not execute this code.
    for name,value in sources.items():
        if value is None:
            assert not (root/name).exists()
        else:
            raw=(root/name).read_bytes()
            assert raw.startswith(b'knowledge:')
            assert digest(raw)==value
    target=evidence/'checks/domain.json'; target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({'fixture_domain':'knowledge-prefix-v1','sources':sources,'passed':True}),encoding='utf-8')
    return LayerResult(status='succeeded',evidence_refs=['checks/domain.json'])


def test_local_add_update_delete_and_three_layer_completion(scope):
    root,_,_,evidence=scope; w=writer(scope)
    first=b'knowledge: first'; w.write('notes/note.txt',first)
    second=b'knowledge: revised'; w.write('notes/note.txt',second,expected_hash=digest(first))
    w.write('notes/delete.txt',b'knowledge: disposable')
    w.delete('notes/delete.txt',expected_hash=digest(b'knowledge: disposable'))
    sources={'notes/note.txt':digest(second),'notes/delete.txt':None}
    result=w.complete(domain_result=domain_check(scope,sources),domain_sources=sources,display_requested=True)
    assert result.vault_id=='vault-a'
    assert result.domain_result.status=='succeeded'
    assert result.system_result.status=='succeeded'
    assert result.display_result.status=='pending'
    validate_contract('OperationReceipt',result.model_dump())
    assert (root/'notes/note.txt').read_bytes()==second and not (root/'notes/delete.txt').exists()
    saved=json.loads((evidence/w.operation_id/'receipt.json').read_text(encoding='utf-8'))
    assert saved['domain_result']['status']=='succeeded'


def test_no_domain_check_never_becomes_domain_success(scope):
    w=writer(scope); w.write('note.txt',b'knowledge: sample')
    result=w.complete()
    assert result.domain_result.status=='not_run'
    assert result.system_result.status=='succeeded'
    assert result.display_result.status=='not_run'


def test_failed_domain_result_is_preserved_separately(scope):
    w=writer(scope); w.write('note.txt',b'knowledge: sample')
    result=w.complete(domain_result=LayerResult(status='failed',evidence_refs=[]))
    assert result.domain_result.status=='failed' and result.system_result.status=='succeeded'


@pytest.mark.parametrize('permission',[{'allow_write':False},{'source_kind':'linked'}, {'vault_id':'other'}, {'binding_id':'other'}])
def test_member_enabled_and_binding_active_do_not_authorize_writes(scope,permission):
    root,_,_,_=scope; (root/'note.txt').write_bytes(b'unchanged')
    with pytest.raises(api().WriterError): writer(scope,**permission).write('note.txt',b'new',expected_hash=digest(b'unchanged'))
    assert (root/'note.txt').read_bytes()==b'unchanged'


def test_authorization_input_is_mandatory_and_not_coerced(scope):
    _,members,bindings,evidence=scope
    refuses('writer_unauthorized',lambda:api().LocalWriter(members,bindings,'native-a',authorization=None,evidence_root=evidence))
    refuses('writer_unauthorized',lambda:writer(scope,allow_write=1))


def test_native_source_kind_requires_same_explicit_grant(scope):
    w=writer(scope,source_kind='native'); w.write('note.txt',b'knowledge: native')
    assert w.complete().domain_result.status=='not_run'


def test_missing_or_disabled_member_preserves_source(scope):
    root,members,bindings,evidence=scope; (root/'note.txt').write_bytes(b'unchanged')
    grant=api().Authorization('vault-a','binding-a','managed',True,True)
    refuses('writer_member_unavailable',lambda:api().LocalWriter(members,bindings,'missing',authorization=grant,evidence_root=evidence))
    payload=members.resolve('vault-a').model_dump(); payload['revision']=2; payload['enabled']=False
    members.update('vault-a',payload,expected_collection_revision=2,expected_record_revision=1)
    refuses('writer_member_unavailable',lambda:writer(scope))
    assert (root/'note.txt').read_bytes()==b'unchanged'


def test_old_writer_is_rejected_after_rebind_and_member_revision_change(scope):
    root,members,bindings,evidence=scope; w=writer(scope)
    other=root.parent/'other'; other.mkdir()
    bindings.bind('binding-a','vault-a',other,expected_revision=1,expected_generation=1)
    refuses('writer_stale',lambda:w.write('note.txt',b'knowledge: no'))
    assert not (root/'note.txt').exists() and not (other/'note.txt').exists()
    current=writer(scope)
    payload=members.resolve('vault-a').model_dump(); payload['revision']=2
    members.update('vault-a',payload,expected_collection_revision=2,expected_record_revision=1)
    refuses('writer_stale',lambda:current.write('note.txt',b'knowledge: no'))


def test_fresh_claim_identity_is_checked(scope):
    root,members,bindings,evidence=scope
    value=json.loads(bindings.path.read_text(encoding='utf-8'))
    value['bindings'][0]['vault_id']='wrong-vault'
    bindings.path.write_text(json.dumps(value),encoding='utf-8')
    refuses('writer_identity_conflict',lambda:writer(scope))
    assert list(root.iterdir())==[]


def test_modify_and_delete_require_exact_reviewed_hash(scope):
    root,_,_,_=scope; w=writer(scope); (root/'note.txt').write_bytes(b'old')
    for expected in [None,'0'*64]:
        with pytest.raises(api().WriterError): w.write('note.txt',b'new',expected_hash=expected)
        with pytest.raises(api().WriterError): w.delete('note.txt',expected_hash=expected)
        assert (root/'note.txt').read_bytes()==b'old'
    refuses('writer_source_changed',lambda:w.write('missing.txt',b'new',expected_hash=digest(b'old')))
    assert not (root/'missing.txt').exists()


def test_completion_refuses_changed_sources_without_rewriting_them(scope):
    root,_,_,_=scope; w=writer(scope); w.write('note.txt',b'knowledge: expected')
    (root/'note.txt').write_bytes(b'raw editor changed source')
    refuses('writer_source_changed',lambda:w.complete())
    assert (root/'note.txt').read_bytes()==b'raw editor changed source'


def test_domain_success_requires_evidence_and_matching_checked_sources(scope):
    _,_,_,evidence=scope; w=writer(scope); raw=b'knowledge: expected'; w.write('note.txt',raw)
    result=LayerResult(status='succeeded',evidence_refs=['checks/domain.json'])
    refuses('writer_domain_unbound',lambda:w.complete(domain_result=result))
    refuses('writer_evidence_unavailable',lambda:w.complete(domain_result=result,domain_sources={'note.txt':digest(raw)}))
    result=domain_check(scope,{'note.txt':digest(raw)})
    refuses('writer_domain_unbound',lambda:w.complete(domain_result=result,domain_sources={'note.txt':'0'*64}))
    assert not (evidence/w.operation_id/'receipt.json').exists()


def test_empty_batch_cannot_claim_completion(scope):
    refuses('writer_no_changes',lambda:writer(scope).complete())


def test_delete_permission_is_separate(scope):
    root,_,_,_=scope; (root/'note.txt').write_bytes(b'old')
    w=writer(scope,allow_delete=False)
    refuses('writer_unauthorized',lambda:w.delete('note.txt',expected_hash=digest(b'old')))
    assert (root/'note.txt').read_bytes()==b'old'


@pytest.mark.parametrize('name',['../outside.txt','/absolute','C:/outside',r'notes\bad.txt','con','note.txt.'])
def test_dangerous_paths_do_not_change_source(scope,name):
    root,_,_,_=scope; w=writer(scope)
    refuses('writer_unsafe_path',lambda:w.write(name,b'knowledge: no'))
    assert list(root.iterdir())==[]


def test_symlink_and_hardlink_targets_do_not_modify_outside_bytes(scope):
    root,_,_,_=scope; w=writer(scope); outside=root.parent/'outside.txt'; outside.write_bytes(b'private outside')
    link=root/'linked.txt'; link.symlink_to(outside)
    refuses('writer_unsafe_path',lambda:w.write('linked.txt',b'new',expected_hash=digest(b'private outside')))
    hard=root/'hard.txt'; os.link(outside,hard)
    refuses('writer_unsafe_path',lambda:w.delete('hard.txt',expected_hash=digest(b'private outside')))
    assert outside.read_bytes()==b'private outside'


def test_linked_parent_and_evidence_overlap_are_rejected(scope):
    root,members,bindings,evidence=scope; w=writer(scope)
    outside=root.parent/'outside'; outside.mkdir()
    (root/'linkdir').symlink_to(outside,target_is_directory=True)
    refuses('writer_unsafe_path',lambda:w.write('linkdir/note.txt',b'knowledge: no'))
    grant=api().Authorization('vault-a','binding-a','managed',True,True)
    refuses('writer_evidence_scope',lambda:api().LocalWriter(members,bindings,'native-a',authorization=grant,evidence_root=root/'receipts'))
    assert list(outside.iterdir())==[]


def test_real_windows_replace_failure_preserves_source_and_pending_status(scope):
    root,_,_,evidence=scope; w=writer(scope); (root/'note.txt').write_bytes(b'old')
    with (root/'note.txt').open('rb'):
        refuses('writer_io_failed',lambda:w.write('note.txt',b'new',expected_hash=digest(b'old')))
    assert (root/'note.txt').read_bytes()==b'old'
    pending=json.loads((evidence/w.operation_id/'pending.json').read_text(encoding='utf-8'))
    assert pending['status']!='completed'


def test_failed_batch_cannot_complete_earlier_successes_optimistically(scope):
    root,_,_,_=scope; w=writer(scope); w.write('first.txt',b'knowledge: first')
    (root/'second.txt').write_bytes(b'existing second')
    with (root/'second.txt').open('rb'):
        refuses('writer_io_failed',lambda:w.write('second.txt',b'knowledge: replacement',expected_hash=digest(b'existing second')))
    refuses('writer_interrupted',lambda:w.complete())
    assert (root/'second.txt').read_bytes()==b'existing second'


def test_nontext_path_is_sanitized_before_source_changes(scope):
    root,_,_,_=scope; w=writer(scope)
    refuses('writer_unsafe_path',lambda:w.write(123,b'knowledge: no'))
    assert list(root.iterdir())==[]


def test_display_request_is_an_explicit_boolean(scope):
    w=writer(scope); w.write('note.txt',b'knowledge: sample')
    refuses('writer_display_invalid',lambda:w.complete(display_requested='false'))


def test_own_system_intent_is_not_native_domain_evidence(scope):
    w=writer(scope); raw=b'knowledge: sample'; w.write('note.txt',raw)
    result=LayerResult(status='succeeded',evidence_refs=[w.operation_id+'/pending.json'])
    refuses('writer_domain_unbound',lambda:w.complete(domain_result=result,domain_sources={'note.txt':digest(raw)}))


def test_malformed_source_kind_is_a_stable_refusal(scope):
    refuses('writer_source_readonly',lambda:writer(scope,source_kind=['managed']))


@pytest.mark.parametrize('sources',[[],object()])
def test_invalid_domain_source_map_is_a_stable_refusal(scope,sources):
    w=writer(scope); w.write('note.txt',b'knowledge: sample')
    refuses('writer_domain_unbound',lambda:w.complete(domain_sources=sources))


def test_validator_command_text_is_never_executed(scope):
    root,_,_,_=scope; w=writer(scope); w.write('note.txt',b'knowledge: sample')
    refuses('writer_domain_invalid',lambda:w.complete(domain_result="open('marker.txt','w').write('executed')"))
    assert not (root/'marker.txt').exists()


def test_member_change_between_claim_and_guard_is_rechecked_inside_guard(scope):
    root,members,bindings,evidence=scope
    class InterleavingBindings(BindingStore):
        armed=False
        def claim(self, binding_id):
            value=super().claim(binding_id)  # Real store and claim, not a fake return.
            if self.armed:
                payload=members.resolve('vault-a').model_dump()
                payload.update(revision=2,enabled=False)
                members.update('vault-a',payload,expected_collection_revision=2,expected_record_revision=1)
                self.armed=False
            return value
    interleaving=InterleavingBindings(bindings.path)
    grant=api().Authorization('vault-a','binding-a','managed',True,True)
    w=api().LocalWriter(members,interleaving,'native-a',authorization=grant,evidence_root=evidence)
    interleaving.armed=True
    refuses('writer_stale',lambda:w.write('note.txt',b'knowledge: refused'))
    assert not (root/'note.txt').exists()


def test_pending_then_real_member_update_is_busy_and_retry_revokes_old_writer(scope):
    root,members,_,evidence=scope; w=writer(scope)
    before=members.path.read_bytes()
    pending=evidence/w.operation_id/'pending.json'
    outcomes=[]
    def update_after_pending():
        deadline=time.monotonic()+10
        while not pending.is_file():
            if time.monotonic()>deadline:
                outcomes.append('pending_not_observed'); return
            time.sleep(.001)
        payload=members.resolve('vault-a').model_dump()
        payload.update(revision=2,enabled=False)
        try:
            members.update('vault-a',payload,expected_collection_revision=2,expected_record_revision=1)
            outcomes.append('unexpected_committed')
        except Exception as exc:
            outcomes.append(getattr(exc,'code',type(exc).__name__))
    worker=threading.Thread(target=update_after_pending)
    worker.start()
    raw=b'knowledge: '+b'x'*(32*1024*1024)
    w.write('large.txt',raw)
    worker.join(timeout=10)
    assert not worker.is_alive()
    assert outcomes==['store_busy']
    assert members.path.read_bytes()==before
    assert (root/'large.txt').read_bytes()==raw
    # The admitted I/O completed first; after guard release the owner retries.
    payload=members.resolve('vault-a').model_dump(); payload.update(revision=2,enabled=False)
    members.update('vault-a',payload,expected_collection_revision=2,expected_record_revision=1)
    refuses('writer_stale',lambda:w.write('after-revoke.txt',b'knowledge: no'))
    assert not (root/'after-revoke.txt').exists()

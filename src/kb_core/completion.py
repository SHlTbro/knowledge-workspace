"""Local Builder/Coordinator/Writer completion, without runtime or authority fallback."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .bindings import BindingError, BindingStore
from .builder import BuildError, LocalBuilder, plan_hash
from .contracts import ContractError, LayerResult, OperationReceipt, local_root, relative_path, validate_contract
from .members import MemberStoreError
from .operations import Coordinator, OperationError, read_request
from .state import StateError, StateService
from .writer import LocalWriter, WriterError


class CompletionError(ValueError):
    def __init__(self, code, outcome=None):
        self.code, self.outcome = code, outcome
        super().__init__(code)


def _path(value):
    try: local_root(str(value))
    except (ValueError, TypeError): raise CompletionError('completion_path_invalid') from None
    path = Path(value)
    for node in [path, *path.parents]:
        try: info = node.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise CompletionError('completion_path_invalid')
    return path


def _bytes(path):
    path = _path(path)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: raise CompletionError('completion_source_invalid')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while chunk := stream.read(1024 * 1024): digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError: return None


def _digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


class Completion:
    """Explicit controlled instance and evidence roots; caller owns grants/native validation.

    A placed root is never rolled back. Partial Coordinator operations retain its
    public diagnostic journal. STATE is derived evidence, not new source authority.
    """
    def __init__(self, instance, builder_state, evidence_root):
        try:
            self.instance, self.builder_state, self.evidence_root = map(_path, (instance,builder_state,evidence_root))
            roots = [self.instance,self.builder_state,self.evidence_root]
            if any(not root.is_dir() for root in roots) or any(a == b or a.is_relative_to(b) or b.is_relative_to(a) for index,a in enumerate(roots) for b in roots[index+1:]):
                raise CompletionError('completion_scope_invalid')
            self.coordinator = Coordinator(self.instance)
            self.builder = LocalBuilder(self.builder_state)
            self.state = StateService(self.instance)
            self.directory = self.evidence_root/'completion'
            _path(self.directory)
        except (BindingError, OperationError, BuildError, StateError, OSError):
            raise CompletionError('completion_instance_invalid') from None

    def _save(self, path, value, *, new=False):
        _path(path)
        raw = (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        temporary = path.parent/('.completion-'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            if new:
                os.link(temporary,path);temporary.unlink()
            else: os.replace(temporary,path)
        except OSError:
            raise CompletionError('completion_evidence_failed') from None
        finally:
            if temporary.exists(): temporary.unlink()

    @contextmanager
    def _lock(self):
        _path(self.directory)
        self.directory.mkdir(exist_ok=True)
        path=self.directory/'owner.lock'
        try:
            with path.open('xb') as stream: stream.write(b'cooperative completion lock\n')
        except FileExistsError: raise CompletionError('completion_busy') from None
        try: yield
        finally: path.unlink()

    def _request(self, request):
        fields={'operation_id','plan','expected_hash','authorized_target','authorized_source_roots','allow_create','allow_register','registration','state_inputs','display_requested'}
        if not isinstance(request,dict) or set(request)!=fields or type(request['display_requested']) is not bool:
            raise CompletionError('completion_input_invalid')
        if request['allow_create'] is not True or request['allow_register'] is not True:
            raise CompletionError('completion_unauthorized')
        try:
            OperationReceipt(operation_id=request['operation_id'],operation_type='register',vault_id=None,
                domain_result=LayerResult(status='not_run',evidence_refs=[]),system_result=LayerResult(status='pending',evidence_refs=[]),
                display_result=LayerResult(status='not_run',evidence_refs=[]),changes=[],evidence=[],observed_at=datetime.now(timezone.utc).isoformat())
            member=validate_contract('MemberRecord',request['registration']['member'])
            target=_path(request['authorized_target'])
            if target != _path(request['plan']['target']) or target != _path(request['registration']['root']):
                raise CompletionError('completion_scope_invalid')
            if any(target==root or target.is_relative_to(root) or root.is_relative_to(target) for root in [self.instance,self.builder_state,self.evidence_root]):
                raise CompletionError('completion_scope_invalid')
            if request['expected_hash']!=plan_hash(request['plan']): raise CompletionError('completion_confirmation_changed')
            if not member.enabled: raise CompletionError('completion_registration_disabled')
            return member,target
        except (ContractError,ValueError,TypeError,KeyError) as error:
            if isinstance(error,CompletionError): raise
            raise CompletionError('completion_input_invalid') from None

    def _sources(self, root, changes):
        sources={}
        for change in changes:
            try: relative_path(change['path'])
            except ValueError: raise CompletionError('completion_source_invalid') from None
            path=_path(root/change['path'])
            sources[change['path']]=_bytes(path)
            if sources[change['path']]!=change['sha256']: raise CompletionError('completion_source_changed')
        return sources

    def _domain(self, supplied, checked, sources):
        try:
            domain=LayerResult(status='not_run',evidence_refs=[]) if supplied is None else LayerResult.model_validate(supplied.model_dump())
        except (ValueError,AttributeError): raise CompletionError('completion_domain_invalid') from None
        if domain.status=='succeeded' and checked!=sources: raise CompletionError('completion_domain_unbound')
        pins=[]
        for ref in domain.evidence_refs:
            if ref.casefold().startswith('completion/'): raise CompletionError('completion_domain_unbound')
            path=_path(self.evidence_root/ref)
            if path.resolve(strict=False).is_relative_to(self.directory.resolve(strict=False)):
                raise CompletionError('completion_domain_unbound')
            digest=_bytes(path)
            if digest is None or path.stat().st_size==0: raise CompletionError('completion_domain_evidence_missing')
            pins.append({'path':ref,'sha256':digest,'bytes':path.stat().st_size})
        return domain,pins

    def _display(self, outcome, config, *, requested):
        """Offline display failure never rolls back a completed native operation."""
        if config is None: return outcome
        if not requested: raise CompletionError('completion_display_unrequested')
        receipt = outcome['receipt']
        if receipt['system_result']['status'] != 'succeeded': return outcome
        proof = {'status': 'failed', 'error': None, 'selection': None}
        try:
            from .display_update import DisplayUpdater, selected_release
            fields = {'descriptions_root','policy_root','output_parent','request','expected_current_hash'}
            if not isinstance(config,dict) or set(config) != fields:
                raise CompletionError('completion_display_input_invalid')
            request = config['request']
            if not isinstance(request,dict) or not isinstance(request.get('selected'),list) or receipt['vault_id'] not in request['selected']:
                raise CompletionError('completion_display_subject_mismatch')
            updater = DisplayUpdater(self.instance,config['descriptions_root'],config['policy_root'],config['output_parent'])
            updater.update(request,expected_current_hash=config['expected_current_hash'])
            current = selected_release(config['output_parent'])
            if current['selection']['operation_id'] != request['operation_id'] or receipt['vault_id'] not in {row['vault_id'] for row in current['projection']['vaults']}:
                raise CompletionError('completion_display_selection_changed')
            proof.update(status='succeeded',selection=current['selection'],selection_sha256=current['selection_sha256'])
        except (CompletionError,OSError,ValueError) as error:
            proof['error'] = getattr(error,'code','completion_display_failed')
            if proof['error']=='display_update_selection_uncertain': proof['status']='pending'
        except ModuleNotFoundError:
            proof['error'] = 'completion_display_unavailable'
        ref = 'completion/display-'+uuid.uuid4().hex+'.json'
        try:
            with self._lock(): self._save(self.evidence_root/ref,proof,new=True)
        except (CompletionError,OSError) as error:
            proof.update(status='pending',error=getattr(error,'code','completion_evidence_failed'))
            ref=None
        refs=[ref] if ref else []
        receipt = {**receipt,'display_result':{'status':proof['status'],'evidence_refs':refs},
                   'evidence':[*receipt['evidence'],*refs]}
        return {**outcome,'receipt':receipt,'display_update':proof}

    def _finish(self, request, built, registration, *, domain_result=None, domain_sources=None):
        member,target=self._request(request)
        try:
            fresh=self.coordinator.members.resolve(member.vault_id)
            claim=self.coordinator.bindings.claim(member.location_ref)
            if fresh.model_dump()!=member.model_dump() or Path(claim['root'])!=target or claim['vault_id']!=member.vault_id:
                raise CompletionError('completion_identity_changed')
            with self.coordinator.bindings.guard(claim):
                with self.coordinator.members.guard(member.model_dump()):
                    inspected=self.builder.inspect(request['plan']['operation_id'])
                    if inspected['status']!='consistent': raise CompletionError('completion_source_changed')
                    keys=('operation_id','target','phase','files')
                    if not isinstance(built,dict) or any(built.get(key)!=inspected.get(key) for key in keys):
                        raise CompletionError('completion_build_history_changed')
                    if inspected['operation_id']!=request['plan']['operation_id'] or inspected['phase']!='placed' or Path(inspected['target'])!=target:
                        raise CompletionError('completion_build_history_changed')
                    changes=[{'path':item['path'],'sha256':item['sha256'],'deleted':False} for item in built['files']]
                    sources=self._sources(target,changes)
                    domain,pins=self._domain(domain_result,domain_sources,sources)
                    state=self.state.generate(request['state_inputs'],scopes=[member.vault_id])
                    status='succeeded' if state['check_exit_code']==0 else 'pending'
                    ref='completion/'+request['operation_id']+'-'+uuid.uuid4().hex+'.json'
                    self._save(self.evidence_root/ref,{'builder':built,'registration':registration,'binding_claim':claim,'state':state,'sources':sources,'domain_sources':domain_sources,'domain_evidence_pins':pins,'scope':'system placement/registration/location/hash only; native domain supplied by caller'},new=True)
                    receipt=OperationReceipt(operation_id=request['operation_id'],operation_type='register',vault_id=member.vault_id,domain_result=domain,
                        system_result=LayerResult(status=status,evidence_refs=[ref]),display_result=LayerResult(status='pending' if request['display_requested'] else 'not_run',evidence_refs=[]),
                        changes=changes,evidence=[ref,*domain.evidence_refs],observed_at=datetime.now(timezone.utc).isoformat()).model_dump()
                    return {'receipt':receipt,'builder':built,'registration':registration,'state':state,'authority_effect':'controlled instance registration only'}
        except (BindingError,MemberStoreError,StateError) as error:
            raise CompletionError(getattr(error,'code','completion_postcheck_failed')) from None

    def create(self, request):
        member,target=self._request(request)
        signature=_digest(request)
        with self._lock():
            path=self.directory/(request['operation_id']+'.json')
            if path.exists():
                row=read_request(path)
                if row.get('request_hash')!=signature: raise CompletionError('completion_conflict')
                if row.get('phase')!='finished': raise CompletionError('completion_incomplete',row.get('outcome'))
                # Rehash/reobserve rather than replay a historical optimistic receipt.
                outcome=self._finish(request,row['outcome']['builder'],row['outcome']['registration'])
                return {**outcome,'replayed':True}
            row={'request_hash':signature,'phase':'prepared','outcome':None}
            self._save(path,row,new=True)
            try:
                built=self.builder.build(request['plan'],authorized_target=target,authorized_source_roots=request['authorized_source_roots'],expected_hash=request['expected_hash'])
                row.update(phase='placed',builder=built);self._save(path,row)
                try: registration=self.coordinator.execute(request['operation_id'],'register',request['registration'])
                except OperationError as error:
                    ref='completion/'+request['operation_id']+'.json'
                    receipt=OperationReceipt(operation_id=request['operation_id'],operation_type='register',vault_id=member.vault_id,
                        domain_result=LayerResult(status='not_run',evidence_refs=[]),system_result=LayerResult(status='pending',evidence_refs=[ref]),
                        display_result=LayerResult(status='pending' if request['display_requested'] else 'not_run',evidence_refs=[]),changes=[],evidence=[ref],observed_at=datetime.now(timezone.utc).isoformat()).model_dump()
                    outcome={'receipt':receipt,'builder':built,'registration_error':error.code,'registration_receipt':error.receipt,'state':None,'replayed':False}
                    row.update(phase='partial',outcome=outcome);self._save(path,row)
                    return outcome
                row.update(phase='registered',registration=registration);self._save(path,row)
                outcome=self._finish(request,built,registration)
                row.update(phase='finished',outcome=outcome);self._save(path,row)
                return {**outcome,'replayed':False}
            except (BuildError,CompletionError,OperationError,OSError) as error:
                row.update(phase='partial' if target.exists() else 'failed',error=getattr(error,'code','completion_io_failed'))
                ref='completion/'+request['operation_id']+'.json'
                partial_receipt=OperationReceipt(operation_id=request['operation_id'],operation_type='register',vault_id=member.vault_id,
                    domain_result=LayerResult(status='not_run',evidence_refs=[]),system_result=LayerResult(status='pending' if target.exists() else 'failed',evidence_refs=[ref]),
                    display_result=LayerResult(status='pending' if request['display_requested'] else 'not_run',evidence_refs=[]),changes=[],evidence=[ref],observed_at=datetime.now(timezone.utc).isoformat()).model_dump()
                row['outcome']={'phase':row['phase'],'receipt':partial_receipt,'builder':row.get('builder'),'registration':row.get('registration'),'root_preserved':target.exists()}
                self._save(path,row)
                raise CompletionError(row['error'],row['outcome']) from None

    def finish_create(self, request, *, domain_result=None, domain_sources=None, display_config=None):
        """Explicit later native validation after create; no validator command execution."""
        self._request(request)
        if display_config is not None and not request['display_requested']: raise CompletionError('completion_display_unrequested')
        with self._lock():
            row=read_request(self.directory/(request['operation_id']+'.json'))
            if row.get('request_hash')!=_digest(request): raise CompletionError('completion_conflict')
            if row.get('phase')!='finished': raise CompletionError('completion_incomplete',row.get('outcome'))
            outcome=self._finish(request,row['outcome']['builder'],row['outcome']['registration'],domain_result=domain_result,domain_sources=domain_sources)
            row['outcome']=outcome;self._save(self.directory/(request['operation_id']+'.json'),row)
        outcome = self._display(outcome,display_config,requested=request['display_requested'])
        try:
            with self._lock():
                row=read_request(self.directory/(request['operation_id']+'.json'))
                if row.get('request_hash')!=_digest(request): raise CompletionError('completion_conflict',outcome)
                row['outcome']=outcome;self._save(self.directory/(request['operation_id']+'.json'),row)
        except (CompletionError,OSError,OperationError) as error:
            return {**outcome,'completion_evidence_error':getattr(error,'code','completion_evidence_failed')}
        return outcome

    def finish_write(self, writer, *, state_inputs, domain_result=None, domain_sources=None, display_requested=False, display_config=None):
        """Writer owns native/source/permission fencing. STATE is separate derived evidence.

        Caller constructs Writer with this explicit evidence_root; original Writer
        receipt refs remain in that root. A STATE error never erases written bytes.
        """
        if not isinstance(writer,LocalWriter): raise CompletionError('completion_writer_invalid')
        if display_config is not None and not display_requested: raise CompletionError('completion_display_unrequested')
        try: receipt=writer.complete(domain_result=domain_result,domain_sources=domain_sources,display_requested=display_requested).model_dump()
        except WriterError as error: raise CompletionError(error.code) from None
        try:
            member=self.coordinator.members.resolve(receipt['vault_id'])
            claim=self.coordinator.bindings.claim(member.location_ref)
            if not member.enabled or claim['vault_id']!=member.vault_id: raise CompletionError('completion_identity_changed')
            with self.coordinator.bindings.guard(claim):
                with self.coordinator.members.guard(member.model_dump()):
                    sources=self._sources(Path(claim['root']),receipt['changes'])
                    for reference in receipt['system_result']['evidence_refs']:
                        proof=read_request(_path(self.evidence_root/reference))
                        if proof.get('binding_claim')!=claim or proof.get('sources')!=sources or proof.get('member_revision')!=member.revision:
                            raise CompletionError('completion_writer_evidence_mismatch')
                    state=self.state.generate(state_inputs,scopes=[receipt['vault_id']]);state_error=None
        except (StateError,BindingError,MemberStoreError,OperationError,CompletionError) as error:
            state=None;state_error=error.code
        ref='completion/write-'+receipt['operation_id']+'.json'
        with self._lock():self._save(self.evidence_root/ref,{'writer_receipt':receipt,'state':state,'state_error':state_error},new=True)
        receipt={**receipt,'system_result':{'status':'pending' if state_error or state['check_exit_code'] else receipt['system_result']['status'],
                     'evidence_refs':[*receipt['system_result']['evidence_refs'],ref]},'evidence':[*receipt['evidence'],ref]}
        return self._display({'receipt':receipt,'state':state,'state_error':state_error,'writer_complete_called':True},display_config,requested=display_requested)

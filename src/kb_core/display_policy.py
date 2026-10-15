"""Live exact-resource K06 policy checks; metadata declarations never grant access."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .bindings import BindingError, BindingStore
from .contracts import ContractError, DisplayPolicy, relative_path, validate_contract
from .members import MemberStoreError
from .operations import Coordinator, OperationError

MAX_BYTES=1024*1024
_UNSET=object()


class PolicyError(ValueError):
    def __init__(self,code,*,written=False):
        self.code,self.written=code,written
        self.status='needs_review' if written else 'refused'
        super().__init__(code)


def _hash(raw):return hashlib.sha256(raw).hexdigest()
def _encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode('utf-8')


def _path(value):
    try:return BindingStore(Path(value)).path
    except (BindingError,TypeError,ValueError):raise PolicyError('policy_path_invalid') from None


def _paths(values):
    if not isinstance(values,list) or len(values)>256:raise PolicyError('policy_invalid')
    seen=set()
    for path in values:
        try:relative_path(path)
        except (TypeError,ValueError,AttributeError):raise PolicyError('policy_path_invalid') from None
        if path.casefold() in seen:raise PolicyError('policy_conflict')
        seen.add(path.casefold())
    return list(values)


def _policy(value):
    try:
        policy=validate_contract('DisplayPolicy',value).model_dump()
        for field in ['allow','deny','revoked']:_paths(policy[field])
        return policy
    except ContractError:raise PolicyError('policy_invalid') from None


def _legacy(value):
    if value is None:return {'deny':[],'allow_limit':None,'source_ref':None,'source_sha256':None}
    if not isinstance(value,dict) or set(value)!={'deny','allow_limit','source_ref','source_sha256'}:raise PolicyError('policy_legacy_invalid')
    deny=_paths(value['deny'])
    limit=None if value['allow_limit'] is None else _paths(value['allow_limit'])
    try:relative_path(value['source_ref'])
    except (ValueError,TypeError,AttributeError):raise PolicyError('policy_legacy_invalid') from None
    digest=value['source_sha256']
    if not isinstance(digest,str) or len(digest)!=64 or any(char not in '0123456789abcdef' for char in digest):raise PolicyError('policy_legacy_invalid')
    return {**value,'deny':deny,'allow_limit':limit}


def proposal_hash(policy,*,legacy=None,release_legacy=False):
    """Caller reviews this exact proposal; hash is confirmation, not authentication."""
    if type(release_legacy) is not bool:raise PolicyError('policy_review_invalid')
    return _hash(_encoded({'policy':_policy(policy),'legacy':None if legacy is None else _legacy(legacy),'release_legacy':release_legacy}))


def _object(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise PolicyError('policy_invalid')
        out[key]=value
    return out


class PolicyService:
    """One explicit local policy store; members/bindings remain their sole authority.

    Caller owns reading and external disclosure grants. web/agent merely select
    policy channels, never authorize a third-party model. guard must remain held
    through consumer reading/sending; get is a sampled declaration, not a grant.
    Cooperating admitted reads finish before later revocation commits. No OS sandbox.
    """
    def __init__(self,instance,policy_root):
        self.instance,self.root=_path(instance),_path(policy_root)
        if not self.instance.is_dir() or not self.root.is_dir():raise PolicyError('policy_instance_invalid')
        try:self.coordinator=Coordinator(self.instance)
        except (BindingError,OperationError,OSError):raise PolicyError('policy_authority_invalid') from None

    @staticmethod
    def _channel(channel):
        if not isinstance(channel,str) or channel not in {'web','agent'}:raise PolicyError('policy_channel_invalid')

    def _scopes(self):
        return {'authority_scope':_hash(os.path.normcase(str(self.instance)).encode()),'metadata_scope':_hash(os.path.normcase(str(self.root)).encode())}

    def _context(self,identity):
        _path(self.instance);_path(self.root)
        if self.coordinator.operation_issues():raise PolicyError('policy_authority_incomplete')
        members=self.coordinator.members.snapshot();bindings=self.coordinator.bindings.snapshot()
        member=self.coordinator.members.resolve(identity)
        binding=self.coordinator.bindings.resolve(member.location_ref)
        if binding['binding'] and binding['binding']['vault_id']!=member.vault_id:raise PolicyError('policy_identity_conflict')
        return members,bindings,member,binding

    def _file(self,member,channel):return _path(self.root/('policy-'+member.vault_id.casefold()+'-'+channel+'.json'))

    def _row(self,path,member,channel):
        try:
            info=path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>MAX_BYTES:raise PolicyError('policy_source_invalid')
            with path.open('rb') as stream:
                current=os.fstat(stream.fileno())
                if not stat.S_ISREG(current.st_mode) or current.st_nlink!=1:raise PolicyError('policy_source_invalid')
                raw=stream.read(MAX_BYTES+1)
            _path(path);after=path.stat()
            if (info.st_ino,info.st_size,info.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise PolicyError('policy_source_changed')
            if len(raw)>MAX_BYTES:raise PolicyError('policy_source_invalid')
            row=json.loads(raw,object_pairs_hook=_object)
            keys={'policy','legacy_constraints','constraints_hash','review_ref','reviewed_proposal_hash','previous_hash','released_legacy_hash','proposal_input','authority_scope','metadata_scope'}
            if not isinstance(row,dict) or set(row)!=keys:raise PolicyError('policy_invalid')
            row['policy']=_policy(row['policy'])
            if row['policy']['vault_id']!=member.vault_id or row['policy']['channel']!=channel:raise PolicyError('policy_identity_conflict')
            if any(row[key]!=value for key,value in self._scopes().items()):raise PolicyError('policy_scope_conflict')
            proposal=row['proposal_input']
            if not isinstance(proposal,dict) or set(proposal)!={'legacy','release_legacy'}:raise PolicyError('policy_review_invalid')
            if proposal_hash(row['policy'],**proposal)!=row['reviewed_proposal_hash']:raise PolicyError('policy_review_invalid')
            # A persisted explicit no-legacy declaration is a valid empty constraint.
            constraints=row['legacy_constraints']
            if constraints!=_legacy(None):row['legacy_constraints']=_legacy(constraints)
            if _hash(_encoded(row['legacy_constraints']))!=row['constraints_hash']:raise PolicyError('policy_review_invalid')
            try:relative_path(row['review_ref'])
            except (ValueError,TypeError,AttributeError):raise PolicyError('policy_review_invalid') from None
            return row,_hash(raw)
        except FileNotFoundError:return None,None
        except (ValueError,UnicodeError,TypeError) as error:
            if isinstance(error,PolicyError):raise
            raise PolicyError('policy_invalid') from None

    def get(self,identity,channel):
        self._channel(channel)
        try:
            context=self._context(identity);members,bindings,member,binding=context
            path=self._file(member,channel);row,digest=self._row(path,member,channel)
            if self._context(member.vault_id)!=context:raise PolicyError('policy_source_changed')
            bound=binding['binding']
            source={'vault_id':member.vault_id,'channel':channel,'member_revision':member.revision,'collection_revision':members['collection_revision'],
                'binding_id':member.location_ref,'binding_revision':bound['revision'] if bound else None,'binding_generation':bound['generation'] if bound else None,
                'binding_status':binding['status'],'policy_revision':row['policy']['policy_revision'] if row else 0,'sha256':digest,
                **self._scopes()}
            return {'policy':row['policy'] if row else None,'legacy_constraints':row['legacy_constraints'] if row else None,'source':source,'metadata_path':str(path),
                    'privacy_grant':False,'partial_review':bool(row and row['legacy_constraints']['source_ref']),
                    'legacy_interpretation':'bounded deny/allow-limit facts only; accepted adapter/pins/visibility are not mapped into new grant; explicit reviewed replacement needed',
                    'review_ref':row['review_ref'] if row else None}
        except (MemberStoreError,BindingError,OperationError,OSError):raise PolicyError('policy_authority_invalid') from None

    @contextmanager
    def _lock(self,path):
        lock=_path(Path(str(path)+'.lock'))
        try:handle=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:raise PolicyError('policy_busy') from None
        try:yield
        finally:
            owned=os.fstat(handle);os.close(handle);_path(lock);current=lock.stat()
            if current.st_ino!=owned.st_ino or current.st_nlink!=1:raise PolicyError('policy_lock_changed')
            lock.unlink()

    def save(self,identity,policy,*,authorized_target,expected_source,reviewed_proposal_hash,review_ref,legacy=_UNSET,release_legacy=False):
        """All mutations require exact reviewed proposal and source CAS.

        First creation requires explicit legacy=None (reviewed no-applicable prior
        restrictions) or pinned restrictions. Existing constraints stay unchanged
        unless release_legacy=True is explicitly included in the reviewed hash.
        No old sidecar/projection is auto-adopted. Review_ref is caller provenance,
        not a signed approval or proof that an Agent performed a validation.
        """
        policy=_policy(policy);self._channel(policy['channel'])
        declared_legacy=None if legacy is _UNSET else legacy
        if proposal_hash(policy,legacy=declared_legacy,release_legacy=release_legacy)!=reviewed_proposal_hash:raise PolicyError('policy_review_invalid')
        try:relative_path(review_ref)
        except (ValueError,TypeError,AttributeError):raise PolicyError('policy_review_invalid') from None
        before=self.get(identity,policy['channel']);path=Path(before['metadata_path'])
        if _path(authorized_target)!=path:raise PolicyError('policy_target_unauthorized')
        member=self.coordinator.members.resolve(identity)
        if policy['vault_id']!=member.vault_id:raise PolicyError('policy_identity_conflict')
        if before['policy'] is None and legacy is _UNSET:raise PolicyError('policy_legacy_unconfirmed')
        if policy['policy_revision']!=before['source']['policy_revision']+1:raise PolicyError('policy_revision_conflict')
        constraints=before['legacy_constraints'] or _legacy(None)
        replacement=_legacy(declared_legacy)
        if release_legacy:constraints=replacement
        elif declared_legacy is not None:
            if before['policy'] and replacement!=constraints:raise PolicyError('policy_legacy_review_required')
            constraints=replacement
        written=False;temporary=None
        try:
            with self._lock(path),self.coordinator.members.guard(member.model_dump()):
                if self.get(identity,policy['channel'])['source']!=expected_source:raise PolicyError('policy_revision_conflict')
                bound=self.coordinator.bindings.resolve(member.location_ref)['binding']
                if bound and bound['root']:
                    root=Path(bound['root'])
                    if self.root==root or self.root.is_relative_to(root) or root.is_relative_to(self.root):raise PolicyError('policy_storage_scope_invalid')
                row={'policy':policy,'legacy_constraints':constraints,'constraints_hash':_hash(_encoded(constraints)),'review_ref':review_ref,'reviewed_proposal_hash':reviewed_proposal_hash,
                     'previous_hash':before['source']['sha256'],'released_legacy_hash':_hash(_encoded(before['legacy_constraints'])) if release_legacy and before['legacy_constraints'] else None,
                     'proposal_input':{'legacy':declared_legacy,'release_legacy':release_legacy},**self._scopes()}
                raw=_encoded(row)+b'\n'
                if len(raw)>MAX_BYTES:raise PolicyError('policy_source_invalid')
                temporary=self.root/('.policy-'+uuid.uuid4().hex+'.tmp');_path(temporary)
                with temporary.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                if self.get(identity,policy['channel'])['source']!=expected_source:raise PolicyError('policy_revision_conflict')
                _path(path);os.replace(temporary,path);temporary=None;written=True
                after=self.get(identity,policy['channel'])
                expected_after={**expected_source,'policy_revision':policy['policy_revision'],'sha256':_hash(raw)}
                if after['source']!=expected_after:raise PolicyError('policy_source_changed',written=True)
                return after
        except PolicyError as error:
            if written and not error.written:raise PolicyError(error.code,written=True) from None
            raise
        except (MemberStoreError,BindingError,OperationError,OSError):raise PolicyError('policy_write_failed',written=written) from None
        finally:
            if temporary is not None:
                _path(temporary)
                if temporary.exists():temporary.unlink()  # Only this call's exclusively created temp.

    @contextmanager
    def guard(self,identity,resource,channel,*,read_authorized=False,exporting=False,export_authorized=False,expected_source=None):
        """Consumer keeps guard held through sending; old projection never grants.

        Exact casefold resources only. No body reads, adapter execution, model
        dispatch or HTTP responses occur in this module. Live denial takes
        precedence over historical snapshot mismatch for reliable revocation.
        """
        self._channel(channel);_paths([resource])
        if type(exporting) is not bool:raise PolicyError('policy_operation_invalid')
        if read_authorized is not True:raise PolicyError('policy_read_unauthorized')
        if exporting and export_authorized is not True:raise PolicyError('policy_export_unauthorized')
        initial=self.get(identity,channel)
        try:
            with self._lock(Path(initial['metadata_path'])):
                current=self.get(identity,channel);policy=current['policy']
                if policy is None:raise PolicyError('policy_missing')
                key=resource.casefold()
                if key in {p.casefold() for p in policy['revoked']}:raise PolicyError('policy_revoked')
                if key in {p.casefold() for p in policy['deny']}:raise PolicyError('policy_denied')
                constraints=current['legacy_constraints']
                if key in {p.casefold() for p in constraints['deny']} or constraints['allow_limit'] is not None and key not in {p.casefold() for p in constraints['allow_limit']}:
                    raise PolicyError('policy_legacy_restricted')
                if current['partial_review']:raise PolicyError('policy_legacy_review_required')
                if not DisplayPolicy.model_validate(policy).permits(resource,channel=channel):raise PolicyError('policy_not_allowed')
                # K06 compares casefold keys; the physical locator must still be
                # the exact reviewed allow entry, not a different caller spelling.
                canonical=next(path for path in policy['allow'] if path.casefold()==key)
                if expected_source is not None and current['source']!=expected_source:raise PolicyError('policy_revision_conflict')
                member=self.coordinator.members.resolve(identity)
                if not member.enabled:raise PolicyError('policy_member_disabled')
                claim=self.coordinator.bindings.claim(member.location_ref)
                if claim['vault_id']!=member.vault_id:raise PolicyError('policy_identity_conflict')
                # Validate ordinary physical resource locator without opening its body.
                location=_path(Path(claim['root'])/canonical)
                if not location.is_relative_to(Path(claim['root'])):raise PolicyError('policy_path_invalid')
                with self.coordinator.bindings.guard(claim),self.coordinator.members.guard(member.model_dump()):
                    if self.get(identity,channel)['source']!=current['source']:raise PolicyError('policy_source_changed')
                    yield {'policy':policy,'source':current['source'],'binding_claim':claim,'resource':canonical,'locator':str(location),
                           'operation':'export' if exporting else 'local_read','export_authorized':bool(exporting and export_authorized is True),
                           'scope':'Approval applies to this caller operation only; local web/agent read is never third-party model disclosure permission'}
        except (BindingError,MemberStoreError,OperationError,OSError):raise PolicyError('policy_authority_invalid') from None

    @contextmanager
    def guard_many(self,identity,resources,channel,*,read_authorized=False,expected_source=None):
        """Hold one live policy/binding/member snapshot for a bounded read set."""
        resources=_paths(resources)
        if not resources:raise PolicyError('policy_operation_invalid')
        expected_sources={identity:expected_source} if expected_source is not None else None
        with self.guard_many_scoped({identity:resources},channel,read_authorized=read_authorized,
                                    expected_sources=expected_sources) as scoped:
            yield scoped['grants'][identity]

    @contextmanager
    def guard_many_scoped(self,scopes,channel,*,read_authorized=False,expected_sources=None):
        """Hold several Vault policy snapshots with one shared member/binding guard.

        Each Vault has its own policy lock, while all members share one Registry
        instance lock. Acquiring those shared locks once avoids self-contention
        when one Hub response must keep multiple Vault scopes live through send.
        """
        self._channel(channel)
        if read_authorized is not True:raise PolicyError('policy_read_unauthorized')
        if not isinstance(scopes,dict) or not scopes or len(scopes)>64:raise PolicyError('policy_invalid')
        if expected_sources is not None and (not isinstance(expected_sources,dict)
                or not set(expected_sources)<=set(scopes)):
            raise PolicyError('policy_invalid')
        normalized={};seen=set()
        for identity,resources in scopes.items():
            if not isinstance(identity,str) or not identity or identity.casefold() in seen:
                raise PolicyError('policy_invalid')
            seen.add(identity.casefold())
            normalized[identity]=_paths(resources)
        try:
            initial={identity:self.get(identity,channel) for identity in normalized}
            lock_order=sorted(normalized,key=lambda identity:os.path.normcase(initial[identity]['metadata_path']))
            with ExitStack() as stack:
                for identity in lock_order:
                    stack.enter_context(self._lock(Path(initial[identity]['metadata_path'])))
                prepared={}
                for identity,resources in normalized.items():
                    current=self.get(identity,channel);policy=current['policy']
                    expected=(expected_sources or {}).get(identity)
                    if expected is not None and current['source']!=expected:raise PolicyError('policy_revision_conflict')
                    if current['source']!=initial[identity]['source']:raise PolicyError('policy_source_changed')
                    if policy is None and resources:raise PolicyError('policy_missing')
                    canonical={}
                    if resources:
                        allowed={path.casefold():path for path in policy['allow']}
                        denied={path.casefold() for path in policy['deny']}
                        revoked={path.casefold() for path in policy['revoked']}
                        constraints=current['legacy_constraints']
                        limit=None if constraints is None or constraints['allow_limit'] is None else {path.casefold() for path in constraints['allow_limit']}
                        legacy_denied=set() if constraints is None else {path.casefold() for path in constraints['deny']}
                        if current['partial_review']:raise PolicyError('policy_legacy_review_required')
                        display_policy=DisplayPolicy.model_validate(policy)
                        for resource in resources:
                            key=resource.casefold()
                            if key in revoked:raise PolicyError('policy_revoked')
                            if key in denied:raise PolicyError('policy_denied')
                            if key in legacy_denied or limit is not None and key not in limit:raise PolicyError('policy_legacy_restricted')
                            if key not in allowed or not display_policy.permits(resource,channel=channel):raise PolicyError('policy_not_allowed')
                            canonical[resource]=allowed[key]
                    member=self.coordinator.members.resolve(identity)
                    if not member.enabled:raise PolicyError('policy_member_disabled')
                    claim=self.coordinator.bindings.claim(member.location_ref)
                    if claim['vault_id']!=member.vault_id:raise PolicyError('policy_identity_conflict')
                    root=Path(claim['root'])
                    locators={resource:_path(root/path) for resource,path in canonical.items()}
                    if any(not path.is_relative_to(root) for path in locators.values()):raise PolicyError('policy_path_invalid')
                    prepared[identity]={'current':current,'policy':policy,'member':member,'claim':claim,
                                        'resources':resources,'canonical':canonical,'locators':locators}
                first=prepared[sorted(prepared,key=str.casefold)[0]]
                with self.coordinator.bindings.guard(first['claim']),self.coordinator.members.guard(first['member'].model_dump()):
                    for identity,item in prepared.items():
                        if self.coordinator.members.resolve(identity)!=item['member']:
                            raise PolicyError('policy_source_changed')
                        latest_binding=self.coordinator.bindings.resolve(item['member'].location_ref)
                        if (latest_binding['status']!='online' or latest_binding['binding'] is None
                                or latest_binding['binding']['generation']!=item['claim']['generation']
                                or latest_binding['binding']['revision']!=item['claim']['revision']
                                or latest_binding['binding']['root']!=item['claim']['root']):
                            raise PolicyError('policy_source_changed')
                        if self.get(identity,channel)['source']!=item['current']['source']:
                            raise PolicyError('policy_source_changed')
                    grants={identity:{resource:{'policy':item['policy'],'source':item['current']['source'],
                        'binding_claim':item['claim'],'resource':item['canonical'][resource],
                        'locator':str(item['locators'][resource]),'operation':'local_read',
                        'export_authorized':False,
                        'scope':'Approval applies to this caller operation only; local web/agent read is never third-party model disclosure permission'}
                        for resource in item['resources']} for identity,item in prepared.items()}
                    yield {'grants':grants,'claims':{identity:item['claim'] for identity,item in prepared.items()}}
        except PolicyError:raise
        except (BindingError,MemberStoreError,OperationError,OSError):raise PolicyError('policy_authority_invalid') from None

"""Offline exact K05 publisher and bounded publication readers, never authority."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .bindings import BindingStore,BindingError
from .contracts import validate_contract,relative_path,ContractError
from .display_description import DescriptionService,DescriptionError
from .display_policy import PolicyService,PolicyError
from .operations import Coordinator,OperationError
from .members import MemberStoreError
from .state import StateService,StateError

MAX_JSON=4*1024*1024
MAX_RESOURCE=16*1024*1024
MAX_TOTAL=64*1024*1024
MAX_FILES=128

class ProjectionError(ValueError):
    def __init__(self,code,*,stage=None):
        self.code,self.stage=code,str(stage) if stage else None
        super().__init__(code)

def _hash(raw):return hashlib.sha256(raw).hexdigest()
def _folder(identity):return 'v-'+_hash(identity.casefold().encode('utf-8'))[:16]
def _path(value):
    try:return BindingStore(Path(value)).path
    except (ValueError,TypeError,BindingError):raise ProjectionError('projection_path_invalid') from None
def _ref(value):
    try:return relative_path(value)
    except (ValueError,TypeError,AttributeError):raise ProjectionError('projection_path_invalid') from None
def _digest(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ProjectionError('projection_input_invalid')
    return value
def _valid_stamp(value,size=None):
    keys={'dev','ino','size','mtime_ns','nlink'}
    if not isinstance(value,dict) or set(value)!=keys or any(type(value[key]) is not int for key in keys):raise ProjectionError('projection_invalid')
    if value['nlink']!=1 or not 0<=value['size']<=MAX_RESOURCE or size is not None and value['size']!=size:raise ProjectionError('projection_invalid')
    return value
def resource_source_stamp(locator):
    """Local ordinary-file metadata fence only; never open native body here."""
    try:
        path=_path(locator);info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ProjectionError('projection_resource_source_changed')
        return _valid_stamp({'dev':info.st_dev,'ino':info.st_ino,'size':info.st_size,'mtime_ns':info.st_mtime_ns,'nlink':info.st_nlink})
    except (OSError,ProjectionError):raise ProjectionError('projection_resource_source_changed') from None
def assert_resource_source(locator,expected):
    """Caller holds current live guard; stamp equality is not a native SHA claim."""
    _valid_stamp(expected)
    if resource_source_stamp(locator)!=expected:raise ProjectionError('projection_resource_source_changed')
def _object(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ProjectionError('projection_invalid')
        out[key]=value
    return out
def _read(path,limit):
    path=_path(path)
    try:
        before=path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:raise ProjectionError('projection_file_invalid')
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink!=1:raise ProjectionError('projection_file_invalid')
            raw=stream.read(limit+1);after=os.fstat(stream.fileno())
        current=_path(path).stat()
        signature=lambda info:(info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
        if signature(before)!=signature(opened) or signature(after)!=signature(current) or signature(before)!=signature(after) or len(raw)>limit:raise ProjectionError('projection_source_changed')
        return raw
    except OSError:raise ProjectionError('projection_file_unavailable') from None
def _json(path):
    try:return json.loads(_read(path,MAX_JSON),object_pairs_hook=_object)
    except (ValueError,UnicodeError,RecursionError) as error:
        if isinstance(error,ProjectionError):raise
        raise ProjectionError('projection_invalid') from None
def _write(path,raw):
    _path(path);path.parent.mkdir(parents=True,exist_ok=True);_path(path)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
def _json_bytes(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
def _entry(ref,raw):return {'artifact_ref':ref,'sha256':_hash(raw),'bytes':len(raw)}
def _checked(root,entry,limit):
    if not isinstance(entry,dict) or not {'artifact_ref','sha256','bytes'}<=set(entry):raise ProjectionError('projection_invalid')
    path=_path(root/_ref(entry['artifact_ref']))
    if not path.is_relative_to(root):raise ProjectionError('projection_path_invalid')
    _digest(entry['sha256'])
    if type(entry['bytes']) is not int or not 0<=entry['bytes']<=limit:raise ProjectionError('projection_file_invalid')
    raw=_read(path,limit)
    if len(raw)!=entry['bytes'] or _hash(raw)!=entry['sha256']:raise ProjectionError('projection_file_changed')
    return raw

def _load_release(output_dir):
    """Return projection/index/report. index/report are private diagnostics, not HTTP payloads."""
    root=_path(output_dir)
    if _path(root/'stale.json').exists():raise ProjectionError('projection_stale')
    index=_json(root/'release.json')
    if not isinstance(index,dict) or set(index)!={'format','projection','report','resources','metadata','selected'} or index['format']!='kb-display-release-1':raise ProjectionError('projection_invalid')
    if any(not isinstance(index[key],dict) or set(index[key])!={'artifact_ref','sha256','bytes'} for key in ['projection','report']):raise ProjectionError('projection_invalid')
    if not isinstance(index['selected'],list) or any(not isinstance(value,str) for value in index['selected']) or len(index['selected'])>64:raise ProjectionError('projection_invalid')
    if index['projection'].get('artifact_ref')!='projection.json' or index['report'].get('artifact_ref')!='source-report.json':raise ProjectionError('projection_invalid')
    try:
        projection=validate_contract('DisplayProjection',json.loads(_checked(root,index['projection'],MAX_JSON),object_pairs_hook=_object)).model_dump()
        report=json.loads(_checked(root,index['report'],MAX_JSON),object_pairs_hook=_object)
    except (ValueError,UnicodeError,ContractError):raise ProjectionError('projection_invalid') from None
    rows={row['vault_id']:row for row in projection['vaults']}
    if len(rows)!=len(projection['vaults']) or sorted(rows)!=sorted(index['selected']):raise ProjectionError('projection_invalid')
    if not isinstance(report,dict) or set(report)!={'kind','selected','state_report','members','status','authority_effect'} or report['kind']!='private_projection_source_report' or report['selected']!=index['selected'] or not isinstance(report['members'],list):raise ProjectionError('projection_invalid')
    try:
        source_state=validate_contract('InstanceState',report['state_report']['state'])
        if source_state.control_revision!=projection['source_member_revision']:raise ProjectionError('projection_invalid')
    except (TypeError,KeyError,ContractError):raise ProjectionError('projection_invalid') from None
    evidence={}
    for item in report['members']:
        if not isinstance(item,dict) or set(item)!={'vault_id','status','description_source','policy_source','metadata_snapshot_ref','counts_basis'}:raise ProjectionError('projection_invalid')
        identity=item['vault_id']
        if not isinstance(identity,str):raise ProjectionError('projection_invalid')
        if identity not in rows or identity in evidence or not isinstance(item['description_source'],dict) or not isinstance(item['policy_source'],dict):raise ProjectionError('projection_invalid')
        evidence[identity]=item
        if item['description_source'].get('vault_id')!=identity or item['description_source'].get('member_revision')!=rows[identity]['member_revision'] or item['description_source'].get('collection_revision')!=projection['source_member_revision'] or item['policy_source'].get('policy_revision')!=rows[identity]['policy_revision']:raise ProjectionError('projection_invalid')
    if set(evidence)!=set(rows):raise ProjectionError('projection_invalid')
    if not isinstance(index['resources'],list) or not isinstance(index['metadata'],list) or len(index['resources'])>MAX_FILES or len(index['metadata'])>64:raise ProjectionError('projection_invalid')
    seen=set();resources={identity:[] for identity in rows};total=0
    for entry in index['resources']:
        if not isinstance(entry,dict) or set(entry)!={'vault_id','source_resource','artifact_ref','sha256','bytes','policy_source','description_source','source_stamp'}:raise ProjectionError('projection_invalid')
        identity=entry['vault_id'];ref=_ref(entry['source_resource'])
        if not isinstance(identity,str):raise ProjectionError('projection_invalid')
        key=(identity,ref.casefold())
        if identity not in rows or key in seen or entry['artifact_ref']!='resources/'+_folder(identity)+'/'+ref:raise ProjectionError('projection_invalid')
        seen.add(key);resources[identity].append(ref);_digest(entry['sha256'])
        if type(entry['bytes']) is not int or not 0<=entry['bytes']<=MAX_RESOURCE:raise ProjectionError('projection_file_invalid')
        _valid_stamp(entry['source_stamp'],entry['bytes'])
        total+=entry['bytes']
        if total>MAX_TOTAL:raise ProjectionError('projection_file_invalid')
        if not isinstance(entry['policy_source'],dict) or not isinstance(entry['description_source'],dict) or entry['policy_source'].get('vault_id')!=identity or entry['policy_source'].get('policy_revision')!=rows[identity]['policy_revision'] or entry['policy_source'].get('channel')!='web' or entry['description_source'].get('vault_id')!=identity:raise ProjectionError('projection_invalid')
        if entry['policy_source']!=evidence[identity]['policy_source'] or entry['description_source']!=evidence[identity]['description_source']:raise ProjectionError('projection_invalid')
    if any(sorted(resources[identity])!=sorted(row['resources']) for identity,row in rows.items()):raise ProjectionError('projection_invalid')
    metadata_seen=set()
    for entry in index['metadata']:
        if not isinstance(entry,dict) or set(entry)!={'vault_id','artifact_ref','sha256','bytes','description_source'}:raise ProjectionError('projection_invalid')
        identity=entry['vault_id']
        if not isinstance(identity,str):raise ProjectionError('projection_invalid')
        if identity not in rows or identity in metadata_seen or entry['artifact_ref']!='descriptions/'+_folder(identity)+'.json':raise ProjectionError('projection_invalid')
        metadata_seen.add(identity);_digest(entry['sha256'])
        if type(entry['bytes']) is not int or not 0<=entry['bytes']<=1024*1024 or not isinstance(entry['description_source'],dict) or entry['description_source'].get('vault_id')!=identity or entry['description_source'].get('sha256')!=entry['sha256']:raise ProjectionError('projection_invalid')
        if entry['description_source']!=evidence[identity]['description_source'] or entry['artifact_ref']!=evidence[identity]['metadata_snapshot_ref']:raise ProjectionError('projection_invalid')
    if metadata_seen!=set(rows):raise ProjectionError('projection_invalid')
    return {'projection':projection,'index':index,'report':report}

def load_release(output_dir):
    """Public reader refuses owned in-progress staging; index/report stay private."""
    root=_path(output_dir)
    if root.name.casefold().startswith('.dp-'):raise ProjectionError('projection_incomplete')
    return _load_release(root)

def read_resource(output_dir,vault_id,canonical_source_resource):
    """Bounded artifact bytes only. Caller holds live T29 guard through read/send."""
    release=load_release(output_dir);ref=_ref(canonical_source_resource)
    entries=[entry for entry in release['index']['resources'] if entry['vault_id']==vault_id and entry['source_resource']==ref]
    if len(entries)!=1:raise ProjectionError('projection_resource_missing')
    return _checked(_path(output_dir),entries[0],MAX_RESOURCE)

def read_metadata(output_dir,vault_id,approved_sha256):
    """Approved local metadata snapshot, no native body grant. Scope is caller-owned."""
    _digest(approved_sha256);release=load_release(output_dir)
    entries=[entry for entry in release['index']['metadata'] if entry['vault_id']==vault_id and entry['sha256']==approved_sha256]
    if len(entries)!=1:raise ProjectionError('projection_metadata_unapproved')
    try:
        payload=json.loads(_checked(_path(output_dir),entries[0],1024*1024),object_pairs_hook=_object)
        if not isinstance(payload,dict) or payload.get('vault_id')!=vault_id or payload.get('description_version')!='1':raise ProjectionError('projection_invalid')
        return payload
    except (ValueError,UnicodeError):raise ProjectionError('projection_invalid') from None

class ProjectionBuilder:
    def __init__(self,instance,descriptions_root,policy_root,output_parent):
        self.instance,self.descriptions_root,self.policy_root,self.output_parent=map(_path,(instance,descriptions_root,policy_root,output_parent))
        if not all(root.is_dir() for root in [self.instance,self.descriptions_root,self.policy_root,self.output_parent]):raise ProjectionError('projection_root_unavailable')
        self.coordinator=Coordinator(self.instance);self.descriptions=DescriptionService(self.instance,self.descriptions_root)
        self.policies=PolicyService(self.instance,self.policy_root);self.state=StateService(self.instance)

    def build(self,output_dir,*,selected,projection_revision,state_inputs,approvals):
        """Explicit selected display scope; unrelated members remain Agent-usable.

        Metadata approval is its raw-byte hash, not a body grant. Sources are
        re-observed before and after same-parent atomic Windows rename. No live
        permission rollback; failed stage and any prior good release are retained.
        """
        target=_path(output_dir)
        if target.parent!=self.output_parent or target.exists() or target.name.casefold().startswith('.dp-'):raise ProjectionError('projection_target_unavailable')
        if os.name!='nt':raise ProjectionError('projection_platform_unsupported')
        if not isinstance(selected,list) or len(selected)>64 or not isinstance(approvals,dict):raise ProjectionError('projection_scope_invalid')
        if type(projection_revision) is not int or projection_revision<1:raise ProjectionError('projection_revision_invalid')
        stage=None;published=False
        try:
            snapshot=self.coordinator.members.snapshot();observed=self.state.generate(state_inputs,scopes=[])
            if observed['check_exit_code']!=0:raise ProjectionError('projection_authority_incomplete')
            protected=[self.instance,self.descriptions_root,self.policy_root]
            binding_snapshot=self.coordinator.bindings.snapshot()
            protected += [Path(row['root']) for row in binding_snapshot if row['root']]
            if any(target==root or target.is_relative_to(root) or root.is_relative_to(target) for root in protected):raise ProjectionError('projection_output_scope_invalid')
            members=[self.coordinator.members.resolve(identity) for identity in selected]
            ids=[member.vault_id for member in members]
            if len(set(ids))!=len(ids) or set(approvals)!=set(ids):raise ProjectionError('projection_scope_invalid')
            candidate=self.output_parent/('.dp-'+uuid.uuid4().hex[:12]);_path(candidate);candidate.mkdir()
            stage=candidate  # Assigned only after exclusive creation; never diagnose a foreign collision.
            _write(stage/'stage-report.json',_json_bytes({'phase':'building','target':str(target),'selected':ids,'authority_effect':'none'}))
            rows=[];reports=[];resources=[];metadata=[];total=0
            for member in members:
                if member.display_ref is None:raise ProjectionError('projection_display_not_declared')
                approval=approvals[member.vault_id]
                if not isinstance(approval,dict) or set(approval)!={'description_sha256','resources'} or not isinstance(approval['resources'],dict):raise ProjectionError('projection_input_invalid')
                description=self.descriptions.read(member.vault_id);policy=self.policies.get(member.vault_id,'web')
                if policy['policy'] is None:raise ProjectionError('projection_policy_missing')
                if description['description'] is None or description['source']['sha256']!=_digest(approval['description_sha256']):raise ProjectionError('projection_metadata_unapproved')
                raw=_read(Path(description['metadata_path']),1024*1024)
                if _hash(raw)!=approval['description_sha256']:raise ProjectionError('projection_source_changed')
                metadata_ref='descriptions/'+_folder(member.vault_id)+'.json';_write(stage/metadata_ref,raw)
                metadata.append({'vault_id':member.vault_id,**_entry(metadata_ref,raw),'description_source':description['source']})
                copied=[]
                if member.enabled and description['source']['binding_status']=='online':
                    for resource,approved in approval['resources'].items():
                        _ref(resource)
                        if not isinstance(approved,dict) or set(approved)!={'sha256','bytes','read_authorized'} or type(approved['bytes']) is not int or not 0<=approved['bytes']<=MAX_RESOURCE:raise ProjectionError('projection_input_invalid')
                        with self.policies.guard(member.vault_id,resource,'web',read_authorized=approved['read_authorized'],expected_source=policy['source']) as grant:
                            raw=_read(Path(grant['locator']),MAX_RESOURCE)
                            if len(raw)!=approved['bytes'] or _hash(raw)!=_digest(approved['sha256']):raise ProjectionError('projection_source_changed')
                            total+=len(raw)
                            if total>MAX_TOTAL or len(resources)>=MAX_FILES or grant['resource'].casefold() in {key.casefold() for key in copied}:raise ProjectionError('projection_resource_limit')
                            artifact_ref='resources/'+_folder(member.vault_id)+'/'+grant['resource'];_write(stage/artifact_ref,raw)
                            copied.append(grant['resource']);resources.append({'vault_id':member.vault_id,'source_resource':grant['resource'],**_entry(artifact_ref,raw),
                                'policy_source':grant['source'],'description_source':description['source'],'source_stamp':resource_source_stamp(grant['locator'])})
                elif approval['resources']:raise ProjectionError('projection_source_unavailable')
                counts=[{key:count[key] for key in ['value','count_unit','count_scope','observed_at']} for count in description['description']['counts']]
                row_state='restricted' if not member.enabled else 'offline' if description['source']['binding_status']!='online' else 'current'
                rows.append({'vault_id':member.vault_id,'member_revision':member.revision,'policy_revision':policy['policy']['policy_revision'],'name':member.name,'enabled':member.enabled,'resources':copied,'counts':counts,'state':row_state})
                reports.append({'vault_id':member.vault_id,'status':description['status'],'description_source':description['source'],'policy_source':policy['source'],'metadata_snapshot_ref':metadata_ref,
                                'counts_basis':'Caller-approved declared metadata; not new native count scan'})
            projection=validate_contract('DisplayProjection',{'display_schema_version':'kb-display-1.1','freshness':'current','projection_revision':projection_revision,'source_member_revision':snapshot['collection_revision'],'generated_at':datetime.now(timezone.utc).isoformat(),'vaults':rows}).model_dump()
            report={'kind':'private_projection_source_report','selected':ids,'state_report':observed,'members':reports,'status':'sampled_sources','authority_effect':'none'}
            projection_raw=_json_bytes(projection);report_raw=_json_bytes(report)
            if len(projection_raw)>MAX_JSON or len(report_raw)>MAX_JSON:raise ProjectionError('projection_resource_limit')
            _write(stage/'projection.json',projection_raw);_write(stage/'source-report.json',report_raw)
            index={'format':'kb-display-release-1','projection':_entry('projection.json',projection_raw),'report':_entry('source-report.json',report_raw),
                   'selected':ids,'resources':resources,'metadata':metadata}
            index_raw=_json_bytes(index)
            if len(index_raw)>MAX_JSON:raise ProjectionError('projection_resource_limit')
            _write(stage/'release.json',index_raw)
            def current():
                if self.coordinator.members.snapshot()!=snapshot:raise ProjectionError('projection_source_changed')
                if self.coordinator.bindings.snapshot()!=binding_snapshot:raise ProjectionError('projection_source_changed')
                latest=self.state.generate(state_inputs,scopes=[])
                if latest['check_exit_code']!=0:raise ProjectionError('projection_source_changed')
                for item in reports:
                    self.descriptions.assert_current(item['vault_id'],item['description_source'])
                    if self.policies.get(item['vault_id'],'web')['source']!=item['policy_source']:raise ProjectionError('projection_source_changed')
                for entry in resources:
                    with self.policies.guard(entry['vault_id'],entry['source_resource'],'web',read_authorized=True,expected_source=entry['policy_source']) as grant:
                        assert_resource_source(grant['locator'],entry['source_stamp'])
                        if _hash(_read(Path(grant['locator']),MAX_RESOURCE))!=entry['sha256']:raise ProjectionError('projection_source_changed')
            current();_load_release(stage);_path(target)
            if target.exists():raise ProjectionError('projection_target_unavailable')
            stage.rename(target);published=True
            current()
            return {'output_dir':str(target),'projection':projection,'status':'published','source_report':'private','authority_effect':'none'}
        except (ProjectionError,PolicyError,DescriptionError,OperationError,MemberStoreError,BindingError,StateError,ContractError,OSError,ValueError,TypeError,KeyError) as error:
            code=error.code if hasattr(error,'code') else 'projection_failed'
            diagnostic=target if published else stage
            if diagnostic and diagnostic.is_dir():
                try:_write(diagnostic/'stale.json',_json_bytes({'status':'stale' if published else 'failed_stage','error':code,'target':str(target),'authority_effect':'none','old_good_untouched':True}))
                except (OSError,ProjectionError):pass
            raise ProjectionError(code,stage=diagnostic) from None

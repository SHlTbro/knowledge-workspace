"""Offline immutable publication selection. This is not membership authority."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from .bindings import BindingStore
from .display_projection import ProjectionBuilder,load_release,read_resource,assert_resource_source

MAX_SELECTION=16*1024
MAX_REQUEST=1024*1024
SELECTION_KEYS={'format','release_ref','release_sha256','request_sha256','operation_id'}
JOURNAL_KEYS={'format','operation_id','request_sha256','base_sha256','release_ref','selection_sha256'}

class DisplayUpdateError(ValueError):
    def __init__(self,code,*,artifact=None):
        self.code,self.artifact=code,str(artifact) if artifact is not None else None
        super().__init__('Offline display update refused; inspect its retained local evidence.')

def _hash(raw):return hashlib.sha256(raw).hexdigest()
def _path(value):
    try:return BindingStore(value).path
    except (ValueError,TypeError,OSError):raise DisplayUpdateError('display_update_path_invalid') from None
def _digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
def _operation(value):
    return isinstance(value,str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',value) is not None
def _ref(value):
    return isinstance(value,str) and re.fullmatch('display-[0-9a-f]{16}',value) is not None
def _ordinary(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise DisplayUpdateError('display_update_file_invalid')
def _read(path,limit):
    path=_path(path)
    try:
        before=path.stat();_ordinary(before)
        if before.st_size>limit:raise DisplayUpdateError('display_update_file_invalid')
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno());_ordinary(opened)
            raw=stream.read(limit+1);after=os.fstat(stream.fileno());_ordinary(after)
        current=_path(path).stat();_ordinary(current)
        signature=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
        if len(raw)>limit or len({signature(info) for info in [before,opened,after,current]})!=1:raise DisplayUpdateError('display_update_file_changed')
        return raw
    except OSError:raise DisplayUpdateError('display_update_file_unavailable') from None
def _pairs(items):
    value={}
    for key,item in items:
        if key in value:raise DisplayUpdateError('display_update_record_invalid')
        value[key]=item
    return value
def _decode(raw):
    try:return json.loads(raw,object_pairs_hook=_pairs)
    except (ValueError,UnicodeError,RecursionError):raise DisplayUpdateError('display_update_record_invalid') from None
def _encoded(value):
    try:return (json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')
    except (ValueError,TypeError,RecursionError):raise DisplayUpdateError('display_update_request_invalid') from None

def selected_release(output_parent):
    """Read one exact chosen release; no mkdir/discovery/fallback or body grant."""
    try:
        parent=_path(output_parent)
        if not parent.is_dir():raise DisplayUpdateError('display_selection_unavailable')
        path=parent/'current-display.json';raw=_read(path,MAX_SELECTION);selection=_decode(raw)
        if (not isinstance(selection,dict) or set(selection)!=SELECTION_KEYS or selection['format']!='kb-display-selection-1'
                or not _ref(selection['release_ref']) or not _digest(selection['release_sha256'])
                or not _digest(selection['request_sha256']) or not _operation(selection['operation_id'])):
            raise DisplayUpdateError('display_selection_invalid')
        target=_path(parent/selection['release_ref'])
        if target.parent!=parent or not target.is_dir():raise DisplayUpdateError('display_selection_invalid')
        index=target/'release.json'
        if _hash(_read(index,4*1024*1024))!=selection['release_sha256']:raise DisplayUpdateError('display_selection_artifact_changed')
        loaded=load_release(target)
        # Only selection/index/metadata integrity here. T31 reads an exact body
        # through read_resource under its current live guard; one corrupt body
        # must not poison a safe overview or another library's cached metadata.
        if _hash(_read(index,4*1024*1024))!=selection['release_sha256'] or _read(path,MAX_SELECTION)!=raw:
            raise DisplayUpdateError('display_selection_changed')
        return {'output_dir':str(target),'selection':selection,'selection_sha256':_hash(raw),'projection':loaded['projection']}
    except DisplayUpdateError:raise
    except (ValueError,OSError,TypeError,KeyError):raise DisplayUpdateError('display_selection_invalid') from None

class DisplayUpdater:
    def __init__(self,instance,descriptions_root,policy_root,output_parent):
        try:
            self.instance,self.descriptions_root,self.policy_root,self.output_parent=map(_path,(instance,descriptions_root,policy_root,output_parent))
            self.builder=ProjectionBuilder(self.instance,self.descriptions_root,self.policy_root,self.output_parent)
            self._check_roots()
        except DisplayUpdateError:raise
        except (ValueError,OSError,TypeError):raise DisplayUpdateError('display_update_roots_invalid') from None

    def _check_roots(self):
        parent=_path(self.output_parent)
        protected=[self.instance,self.descriptions_root,self.policy_root]
        protected += [_path(row['root']) for row in self.builder.coordinator.bindings.snapshot() if row['root']]
        if any(parent==root or parent.is_relative_to(root) or root.is_relative_to(parent) for root in protected):
            raise DisplayUpdateError('display_update_output_scope_invalid')
        if not parent.is_dir():raise DisplayUpdateError('display_update_roots_invalid')

    @contextmanager
    def _lock(self):
        if os.name!='nt':raise DisplayUpdateError('display_update_platform_unsupported')
        import msvcrt
        path=_path(self.output_parent/'current-display.lock')
        stream=None;locked=False
        try:
            stream=path.open('a+b');_ordinary(os.fstat(stream.fileno()))
            if stream.seek(0,os.SEEK_END)==0:stream.write(b'\0');stream.flush()
            stream.seek(0)
            try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise DisplayUpdateError('display_update_busy') from None
            locked=True
            if path.stat().st_ino!=os.fstat(stream.fileno()).st_ino:raise DisplayUpdateError('display_update_lock_changed')
            yield
        finally:
            if stream is not None:
                if locked:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                stream.close()

    def _atomic(self,path,raw):
        path=_path(path);temporary=_path(self.output_parent/('.du-'+uuid.uuid4().hex[:16]+'.json'))
        with temporary.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        _path(path)
        if path.exists():_ordinary(path.stat())
        os.replace(temporary,path)  # Failed owned temp is retained, no cleanup of user paths.

    def _current(self):
        return selected_release(self.output_parent) if _path(self.output_parent/'current-display.json').exists() else None

    def _sources_current(self,loaded,artifact):
        if self.builder.coordinator.operation_issues():raise DisplayUpdateError('display_update_source_changed')
        if self.builder.coordinator.members.snapshot()['collection_revision']!=loaded['projection']['source_member_revision']:
            raise DisplayUpdateError('display_update_source_changed')
        for item in loaded['report']['members']:
            self.builder.descriptions.assert_current(item['vault_id'],item['description_source'])
            if self.builder.policies.get(item['vault_id'],'web')['source']!=item['policy_source']:
                raise DisplayUpdateError('display_update_source_changed')
        for entry in loaded['index']['resources']:
            with self.builder.policies.guard(entry['vault_id'],entry['source_resource'],'web',read_authorized=True,expected_source=entry['policy_source']) as grant:
                assert_resource_source(grant['locator'],entry['source_stamp'])
                read_resource(artifact,entry['vault_id'],entry['source_resource'])

    def update(self,request,expected_current_hash):
        """CAS selection, immutable release, same-op retry. Caller owns all grants."""
        artifact=None;published=False;committed=False
        try:
            if not isinstance(request,dict) or set(request)!={'operation_id','selected','projection_revision','state_inputs','approvals'} or not _operation(request['operation_id']):
                raise DisplayUpdateError('display_update_request_invalid')
            if expected_current_hash is not None and not _digest(expected_current_hash):raise DisplayUpdateError('display_update_cas_invalid')
            encoded=_encoded(request)
            if len(encoded)>MAX_REQUEST or not isinstance(request['selected'],list) or not 1<=len(request['selected'])<=64:
                raise DisplayUpdateError('display_update_request_invalid')
            # A private canonical copy prevents caller mutation during publication.
            request=_decode(encoded);request_hash=_hash(encoded)
            with self._lock():
                self._check_roots();current=self._current();current_hash=current['selection_sha256'] if current else None
                journal_path=_path(self.output_parent/('.display-op-'+_hash(request['operation_id'].casefold().encode('utf-8'))+'.json'))
                prior=_decode(_read(journal_path,MAX_SELECTION)) if journal_path.exists() else None
                if prior is not None:
                    if (not isinstance(prior,dict) or set(prior)!=JOURNAL_KEYS or prior['format']!='kb-display-update-1'
                            or not _operation(prior['operation_id']) or not _digest(prior['request_sha256'])
                            or not (prior['base_sha256'] is None or _digest(prior['base_sha256']))
                            or not _ref(prior['release_ref']) or not (prior['selection_sha256'] is None or _digest(prior['selection_sha256']))):
                        raise DisplayUpdateError('display_update_journal_invalid')
                    if prior['operation_id']!=request['operation_id'] or prior['request_sha256']!=request_hash:raise DisplayUpdateError('display_update_request_changed')
                    if current and current['selection']['operation_id']==request['operation_id']:
                        if current_hash!=prior['selection_sha256'] or current['selection']['request_sha256']!=request_hash or current['selection']['release_ref']!=prior['release_ref']:
                            raise DisplayUpdateError('display_update_journal_invalid')
                        return current
                    if prior['base_sha256']!=current_hash:raise DisplayUpdateError('display_update_superseded')
                elif current and current['selection']['operation_id']==request['operation_id']:
                    raise DisplayUpdateError('display_update_journal_missing')
                if current_hash!=expected_current_hash:raise DisplayUpdateError('display_update_cas_conflict')
                ref='display-'+uuid.uuid4().hex[:16];artifact=self.output_parent/ref
                journal={'format':'kb-display-update-1','operation_id':request['operation_id'],'request_sha256':request_hash,'base_sha256':current_hash,'release_ref':ref,'selection_sha256':None}
                self._atomic(journal_path,_encoded(journal))
                values={key:request[key] for key in ['selected','projection_revision','state_inputs','approvals']}
                self.builder.build(artifact,**values)
                published=True
                loaded=load_release(artifact);self._sources_current(loaded,artifact);self._check_roots()
                selection={'format':'kb-display-selection-1','operation_id':request['operation_id'],'request_sha256':request_hash,'release_ref':ref,'release_sha256':_hash(_read(artifact/'release.json',4*1024*1024))}
                raw=_encoded(selection);selection_hash=_hash(raw)
                journal['selection_sha256']=selection_hash;self._atomic(journal_path,_encoded(journal))
                latest=self._current()
                if (latest['selection_sha256'] if latest else None)!=current_hash:raise DisplayUpdateError('display_update_cas_conflict')
                self._sources_current(loaded,artifact)
                try:self._atomic(self.output_parent/'current-display.json',raw)
                except (DisplayUpdateError,OSError):
                    try:observed=_read(self.output_parent/'current-display.json',MAX_SELECTION)
                    except DisplayUpdateError:
                        if not _path(self.output_parent/'current-display.json').exists():
                            raise DisplayUpdateError('display_update_failed',artifact=artifact) from None
                        raise DisplayUpdateError('display_update_selection_uncertain',artifact=artifact) from None
                    if observed==raw:raise DisplayUpdateError('display_update_selection_uncertain',artifact=artifact) from None
                    raise
                committed=True
                # Selection replacement is the final mutating action. A later
                # lost response is recovered from this choice + prepared receipt.
                return {'output_dir':str(artifact),'selection':selection,'selection_sha256':selection_hash,'projection':loaded['projection']}
        except DisplayUpdateError as error:
            if published and error.artifact is None:error.artifact=str(artifact)
            raise
        except (ValueError,OSError,TypeError,KeyError) as error:
            raise DisplayUpdateError('display_update_selection_uncertain' if committed else 'display_update_failed',artifact=getattr(error,'stage',None) or (artifact if published else None)) from None

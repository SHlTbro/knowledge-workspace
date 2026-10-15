"""Machine-local declared display metadata, never membership or privacy authority."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from .bindings import BindingError
from .contracts import DisplayCount, local_root, relative_path
from .members import MemberStoreError
from .operations import Coordinator, OperationError

MAX_BYTES = 1024 * 1024

class DescriptionError(ValueError):
    def __init__(self, code, *, written=False):
        self.code, self.written = code, written
        self.status = 'needs_review' if written else 'refused'
        super().__init__('Declared display metadata refused; inspect its source and revision.')

def _safe(path):
    try: local_root(str(path))
    except ValueError: raise DescriptionError('description_path_unsafe') from None
    for part in path.parts[1:]:
        if (part.endswith((' ', '.')) or any(char in ':*?"<>|' or ord(char) < 32 for char in part)
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise DescriptionError('description_path_unsafe')
    for component in [*reversed(path.parents), path]:
        try: info = component.lstat()
        except FileNotFoundError: continue
        if component.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise DescriptionError('description_path_unsafe')

def _ordinary(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise DescriptionError('description_path_unsafe')

def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise DescriptionError('description_invalid')
        result[key] = value
    return result

def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000 or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise DescriptionError('description_invalid')
    return value

def _paths(values):
    if not isinstance(values, list) or len(values) > 256: raise DescriptionError('description_invalid')
    result = []
    for value in values:
        if not isinstance(value, str): raise DescriptionError('description_invalid')
        try: relative_path(value)
        except ValueError: raise DescriptionError('description_invalid') from None
        if value.casefold() in {path.casefold() for path in result}: raise DescriptionError('description_invalid')
        result.append(value)
    return result

def _validate(payload, identity):
    try:
        if (not isinstance(payload, dict) or set(payload) != {'description_version', 'revision', 'vault_id', 'purpose',
                'entry_points', 'structure', 'agent_prompt', 'preview_resources', 'counts'}
                or payload['description_version'] != '1' or payload['vault_id'] != identity
                or type(payload['revision']) is not int or payload['revision'] < 1):
            raise DescriptionError('description_invalid')
        if not isinstance(payload['purpose'], list) or not 1 <= len(payload['purpose']) <= 20: raise DescriptionError('description_invalid')
        for value in payload['purpose']: _text(value)
        _text(payload['agent_prompt']); _paths(payload['structure']); _paths(payload['preview_resources'])
        if not isinstance(payload['entry_points'], list) or not 1 <= len(payload['entry_points']) <= 30: raise DescriptionError('description_invalid')
        for entry in payload['entry_points']:
            if not isinstance(entry, dict) or set(entry) != {'label', 'path'}: raise DescriptionError('description_invalid')
            _text(entry['label']); _paths([entry['path']])
        if not isinstance(payload['counts'], list) or len(payload['counts']) > 30: raise DescriptionError('description_invalid')
        for count in payload['counts']:
            if not isinstance(count, dict) or set(count) != {'value', 'count_unit', 'count_scope', 'observed_at', 'source_ref'}:
                raise DescriptionError('description_invalid')
            DisplayCount.model_validate({key: value for key, value in count.items() if key != 'source_ref'})
            if count['value'] is not None and count['source_ref'] is None: raise DescriptionError('description_invalid')
            if count['source_ref'] is not None: _paths([count['source_ref']])
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(raw) > MAX_BYTES: raise DescriptionError('description_limit')
        return payload
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, DescriptionError): raise
        raise DescriptionError('description_invalid') from None

class DescriptionService:
    def __init__(self, instance, descriptions_root):
        try:
            instance = Path(instance); _safe(instance)
            self.root = Path(descriptions_root); _safe(self.root)
            self.coordinator = Coordinator(instance)
            if not self.root.is_dir(): raise DescriptionError('description_root_unavailable')
            self.root = self.root.resolve()
        except (OperationError, BindingError, OSError): raise DescriptionError('description_source_unavailable') from None

    def _context(self, identity):
        _safe(self.root)
        if not self.root.is_dir(): raise DescriptionError('description_root_unavailable')
        if self.coordinator.operation_issues(): raise DescriptionError('description_operation_incomplete')
        members = self.coordinator.members.snapshot()
        bindings = self.coordinator.bindings.snapshot()
        member = self.coordinator.members.resolve(identity)
        binding = self.coordinator.bindings.resolve(member.location_ref)
        if binding['binding'] is not None and binding['binding']['vault_id'] != member.vault_id:
            raise DescriptionError('description_identity_conflict')
        return members, bindings, member, binding

    def _file(self, member):
        return self.root / ('display-' + member.display_ref.casefold() + '.json') if member.display_ref is not None else None

    def _document(self, path, member):
        if path is None: return None, None, None
        _safe(path)
        try: before = path.stat()
        except FileNotFoundError: return None, None, None
        _ordinary(before)
        if before.st_size > MAX_BYTES: raise DescriptionError('description_limit')
        with path.open('rb') as stream:
            _ordinary(os.fstat(stream.fileno())); raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno()); _ordinary(after)
        _safe(path); current = path.stat(); _ordinary(current)
        signature = lambda info: (info.st_ino, info.st_size, info.st_mtime_ns)
        if signature(before) != signature(after) or signature(after) != signature(current): raise DescriptionError('description_source_changed')
        if len(raw) > MAX_BYTES: raise DescriptionError('description_limit')
        try: payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_object)
        except (UnicodeError, ValueError): raise DescriptionError('description_invalid') from None
        return _validate(payload, member.vault_id), hashlib.sha256(raw).hexdigest(), len(raw)

    def read(self, identity):
        try:
            context = self._context(identity)
            members, bindings, member, binding = context
            path = self._file(member); payload, digest, size = self._document(path, member)
            if self._context(member.vault_id) != context: raise DescriptionError('description_source_changed')
            record = binding['binding']
            source = {'vault_id': member.vault_id, 'member_revision': member.revision,
                'collection_revision': members['collection_revision'], 'display_ref': member.display_ref,
                'authority_scope': hashlib.sha256(os.path.normcase(str(self.coordinator.instance)).encode('utf-8')).hexdigest(),
                'metadata_scope': hashlib.sha256(os.path.normcase(str(self.root)).encode('utf-8')).hexdigest(),
                'binding_id': member.location_ref, 'binding_revision': record['revision'] if record else None,
                'binding_generation': record['generation'] if record else None, 'binding_status': binding['status'],
                'description_revision': payload['revision'] if payload else 0, 'sha256': digest, 'bytes': size}
            status = 'not_declared' if path is None else 'declared' if payload else 'missing'
            if not member.enabled: status = 'disabled'
            elif binding['status'] != 'online': status = binding['status']
            return {'identity': {'vault_id': member.vault_id, 'name': member.name, 'enabled': member.enabled,
                                'member_revision': member.revision}, 'status': status,
                'description_status': 'not_declared' if path is None else 'declared' if payload else 'missing',
                'description': payload, 'source': source, 'sampled_at': datetime.now(timezone.utc).isoformat(),
                'metadata_path': str(path) if path else None, 'privacy_grant': False, 'preview_status': 'candidate_requires_T29'}
        except (MemberStoreError, BindingError, OperationError): raise DescriptionError('description_authority_refused') from None
        except OSError: raise DescriptionError('description_source_unavailable') from None

    def assert_current(self, identity, expected_source):
        current = self.read(identity)['source']
        if current != expected_source: raise DescriptionError('description_revision_conflict')
        return current

    @contextmanager
    def _writer(self):
        lock = self.root / '.description-writer.lock'; _safe(lock)
        try: handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError: raise DescriptionError('description_busy') from None
        try: yield
        finally:
            owned = os.fstat(handle); os.close(handle); _safe(lock)
            current = lock.stat(); _ordinary(current)
            if current.st_ino != owned.st_ino: raise DescriptionError('description_lock_changed')
            lock.unlink()

    def save(self, identity, payload, *, authorized_target, expected_source):
        written = False; temporary = None
        try:
            report = self.read(identity)
            member = self.coordinator.members.resolve(report['identity']['vault_id'])
            path = self._file(member)
            if path is None: raise DescriptionError('description_not_declared')
            declared = Path(authorized_target); _safe(declared)
            if os.path.normcase(str(declared)) != os.path.normcase(str(path)): raise DescriptionError('description_target_not_authorized')
            _validate(payload, member.vault_id)
            if type(payload['revision']) is not int or payload['revision'] != report['source']['description_revision'] + 1:
                raise DescriptionError('description_revision_conflict')
            with self._writer(), self.coordinator.members.guard(member.model_dump()):
                self.assert_current(member.vault_id, expected_source)
                raw = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
                if len(raw) > MAX_BYTES: raise DescriptionError('description_limit')
                handle, name = tempfile.mkstemp(prefix='.description-', suffix='.tmp', dir=self.root)
                temporary = Path(name)
                with os.fdopen(handle, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                _safe(temporary); _ordinary(temporary.stat())
                self.assert_current(member.vault_id, expected_source)
                _safe(path); os.replace(temporary, path); temporary = None; written = True
                current = self.read(member.vault_id)
                expected_after = dict(expected_source, description_revision=payload['revision'],
                                      sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
                if current['source'] != expected_after: raise DescriptionError('description_source_changed_after_write', written=True)
                return current
        except DescriptionError as error:
            if written and not error.written: raise DescriptionError(error.code, written=True) from None
            raise
        except (MemberStoreError, BindingError, OperationError, OSError):
            raise DescriptionError('description_write_unavailable', written=written) from None
        finally:
            if temporary is not None:
                try:
                    _safe(temporary); _ordinary(temporary.stat()); temporary.unlink()  # Only this operation's exclusive temporary file.
                except OSError: raise DescriptionError('description_temporary_cleanup_unavailable', written=written) from None

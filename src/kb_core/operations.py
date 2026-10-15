"""Small local coordination journal; not a two-file transaction or domain runtime."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .bindings import BindingError, BindingStore
from .contracts import CONTRACT_VERSION, ContractError, validate_contract
from .members import MemberStore, MemberStoreError

MAX_OPERATIONS = 1000
MAX_JSON_BYTES = 1024 * 1024
MAX_JOURNAL_BYTES = 8 * MAX_JSON_BYTES


class OperationError(ValueError):
    def __init__(self, code, receipt=None):
        self.code, self.message, self.receipt = code, 'Local operation refused; inspect its saved state.', receipt
        super().__init__(self.message)


def read_request(path, *, limit=MAX_JSON_BYTES):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate key')
            value[key] = item
        return value
    try:
        path = Path(path)
        if path.stat().st_size > limit:
            raise ValueError('oversized input')
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)
    except (OSError, UnicodeError, ValueError):
        raise OperationError('operation_record_invalid') from None


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _cas(value, expected):
    if type(value) is not int or value != expected:
        raise OperationError('revision_conflict')


def _journal_path(path):
    try:
        attributes = path.lstat()
    except FileNotFoundError:
        return
    if path.is_symlink() or getattr(attributes, 'st_file_attributes', 0) & 0x400:
        raise OperationError('operation_record_invalid')


class Coordinator:
    def __init__(self, instance):
        path = Path(instance)
        if not path.is_absolute() or not path.is_dir():
            raise OperationError('operation_instance_invalid')
        # Public constructor validates the explicit instance's path ancestors.
        self.bindings = BindingStore(path / 'bindings.json')
        self.instance = self.bindings.path.parent
        self.members = MemberStore(self.instance / 'members.json')
        self.directory = self.instance / 'operations'

    def _check_instance(self):
        # Reuse the public binding path check before any local read/write.
        BindingStore(self.instance / 'bindings.json')
        if not self.instance.is_dir():
            raise OperationError('operation_instance_invalid')

    def _states(self):
        return {name: hashlib.sha256((self.instance / name).read_bytes()).hexdigest()
                if (self.instance / name).is_file() else None for name in ['members.json', 'bindings.json']}

    def _receipt(self, identifier, kind, vault_id, status, before, after):
        reference = 'operations/' + identifier + '.json'
        return validate_contract('OperationReceipt', {'operation_id': identifier, 'operation_type': kind,
            'vault_id': vault_id, 'domain_result': {'status': 'not_run', 'evidence_refs': []},
            'system_result': {'status': status, 'evidence_refs': [reference]},
            'display_result': {'status': 'not_run', 'evidence_refs': []},
            'changes': [{'path': path, 'sha256': digest, 'deleted': False}
                        for path, digest in after.items() if digest is not None and before.get(path) != digest],
            'evidence': [reference], 'observed_at': datetime.now(timezone.utc).isoformat()}).model_dump()

    @contextmanager
    def _writer(self):
        self._check_instance()
        path = self.instance / '.operations.lock'
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise OperationError('operation_busy') from None
        try:
            yield
        finally:
            os.close(descriptor)
            self._check_instance()
            path.unlink()

    def _save(self, path, value):
        self._check_instance()
        _journal_path(self.directory)
        _journal_path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=self.directory,
                                             prefix='operation.', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _journal(self, path):
        _journal_path(self.directory)
        _journal_path(path)
        value = read_request(path, limit=MAX_JOURNAL_BYTES)
        try:
            if (not isinstance(value, dict) or set(value) != {'schema_version', 'instance_path', 'request_hash',
                    'request', 'phase', 'before', 'after', 'receipt', 'error'}
                    or value['schema_version'] != CONTRACT_VERSION or value['instance_path'] != str(self.instance)
                    or value['phase'] not in {'prepared', 'committed', 'failed', 'partial'}
                    or value['request_hash'] != _hash(value['request'])):
                raise ValueError('invalid journal')
            receipt = validate_contract('OperationReceipt', value['receipt'])
            if receipt.operation_id + '.json' != path.name or receipt.operation_type != value['request']['kind']:
                raise ValueError('invalid operation identity')
            expected = {'prepared': 'pending', 'partial': 'pending', 'failed': 'failed', 'committed': 'succeeded'}[value['phase']]
            if receipt.system_result.status != expected or receipt.domain_result.status != 'not_run' or receipt.display_result.status != 'not_run':
                raise ValueError('invalid result layers')
            if value['phase'] in {'failed', 'partial'}:
                if not isinstance(value['error'], str) or not value['error'] or not value['error'].replace('_', '').isalnum():
                    raise ValueError('missing stable failure code')
            elif value['error'] is not None:
                raise ValueError('unexpected failure code')
            for states in [value['before'], value['after']]:
                if (not isinstance(states, dict) or set(states) != {'members.json', 'bindings.json'}
                        or any(digest is not None and (not isinstance(digest, str) or len(digest) != 64
                            or any(char not in '0123456789abcdef' for char in digest)) for digest in states.values())):
                    raise ValueError('invalid source-state fingerprint')
            expected_changes = {name: (digest, False) for name, digest in value['after'].items()
                                if digest is not None and value['before'][name] != digest}
            reference = 'operations/' + path.name
            if ({item.path: (item.sha256, item.deleted) for item in receipt.changes} != expected_changes
                    or receipt.evidence != [reference] or receipt.system_result.evidence_refs != [reference]
                    or receipt.domain_result.evidence_refs or receipt.display_result.evidence_refs):
                raise ValueError('receipt does not match historical evidence')
        except (ContractError, ValueError, TypeError, KeyError):
            raise OperationError('operation_record_invalid') from None
        return value

    def _journals(self):
        _journal_path(self.directory)
        paths = sorted(self.directory.glob('*.json')) if self.directory.exists() else []
        if len(paths) > MAX_OPERATIONS:
            raise OperationError('operation_limit')
        return [self._journal(path) for path in paths]

    def list(self):
        self._check_instance()
        snapshot = self.members.snapshot()
        return {'contract_version': CONTRACT_VERSION, 'collection_revision': snapshot['collection_revision'],
                'members': [{'member': member, 'binding': self.bindings.resolve(member['location_ref'])}
                            for member in snapshot['records']],
                'operation_issues': self.operation_issues()}

    def operation_issues(self):
        """Read validated coordination issues without resolving every binding."""
        self._check_instance()
        return [{'operation_id': row['receipt']['operation_id'], 'phase': row['phase']}
                for row in self._journals() if row['phase'] in {'prepared', 'partial'}]

    def resolve(self, identity):
        self._check_instance()
        member = self.members.resolve(identity)
        return {'contract_version': CONTRACT_VERSION, 'member': member.model_dump(),
                'binding': self.bindings.resolve(member.location_ref)}

    def _prepare(self, kind, payload):
        keys = {'member', 'root', 'expected_collection_revision', 'expected_binding_revision', 'expected_generation'}
        if kind != 'register':
            keys = {'identity', 'root', 'expected_collection_revision', 'expected_member_revision',
                    'expected_binding_revision', 'expected_generation'}
        if not isinstance(payload, dict) or set(payload) != keys:
            raise OperationError('operation_input_invalid')
        snapshot = self.members.snapshot()
        _cas(payload['expected_collection_revision'], snapshot['collection_revision'])
        if kind == 'register':
            member = validate_contract('MemberRecord', payload['member'])
            _cas(member.revision, 1)
            for identity in [member.vault_id, *member.aliases]:
                try:
                    self.members.resolve(identity)
                except MemberStoreError as error:
                    if error.code != 'member_not_found':
                        raise
                else:
                    raise OperationError('identity_conflict')
        else:
            member = self.members.resolve(payload['identity'])
            _cas(payload['expected_member_revision'], member.revision)
            if not member.enabled:
                raise OperationError('operation_member_disabled')
        resolved = self.bindings.resolve(member.location_ref)
        binding = resolved['binding']
        _cas(payload['expected_binding_revision'], binding['revision'] if binding else 0)
        _cas(payload['expected_generation'], binding['generation'] if binding else 0)
        if binding and binding['vault_id'] != member.vault_id:
            raise OperationError('operation_identity_conflict')
        if kind == 'register' and binding is not None:
            raise OperationError('operation_identity_conflict')
        root = payload['root']
        if not member.enabled and (kind != 'register' or root is not None):
            raise OperationError('operation_member_disabled')
        if root is not None and not isinstance(root, str):
            raise OperationError('operation_input_invalid')
        if kind in {'bind', 'rebind'} and root is None or kind == 'unbind' and root is not None:
            raise OperationError('operation_input_invalid')
        if kind == 'rebind' and binding is None or kind == 'unbind' and binding is None:
            raise OperationError('operation_kind_conflict')
        if kind == 'bind' and binding and os.path.normcase(str(Path(root).resolve())) != binding['root']:
            raise OperationError('operation_kind_conflict')
        return member, snapshot

    def execute(self, operation_id, kind, payload):
        if kind not in {'register', 'bind', 'rebind', 'unbind'}:
            raise OperationError('operation_kind_conflict')
        # Validate ID before deriving a journal file path.
        try:
            self._receipt(operation_id, kind, None, 'pending', {}, {})
            request = {'kind': kind, 'payload': payload}
            if len(json.dumps(request).encode()) > MAX_JSON_BYTES:
                raise OperationError('operation_input_invalid')
            with self._writer():
                _journal_path(self.directory)
                self.directory.mkdir(exist_ok=True)
                journals = self._journals()
                path = self.directory / (operation_id + '.json')
                if path.exists():
                    row = self._journal(path)
                    if row['request_hash'] != _hash(request):
                        raise OperationError('operation_conflict')
                    if row['phase'] == 'committed':
                        return {'contract_version': CONTRACT_VERSION, 'receipt': row['receipt'], 'replayed': True}
                    raise OperationError('operation_incomplete' if row['phase'] in {'partial', 'prepared'}
                                         else row['error'], row['receipt'])
                if any(row['phase'] in {'prepared', 'partial'} for row in journals):
                    raise OperationError('operation_incomplete')
                if len(journals) >= MAX_OPERATIONS:
                    raise OperationError('operation_limit')
                member, snapshot = self._prepare(kind, payload)
                before = self._states()
                row = {'schema_version': CONTRACT_VERSION, 'instance_path': str(self.instance),
                    'request_hash': _hash(request), 'request': request, 'phase': 'prepared', 'before': before,
                    'after': before, 'receipt': self._receipt(operation_id, kind, member.vault_id, 'pending', before, before), 'error': None}
                self._save(path, row)
                try:
                    binding = None
                    if kind == 'unbind':
                        binding = self.bindings.unbind(member.location_ref,
                            expected_revision=payload['expected_binding_revision'], expected_generation=payload['expected_generation'])
                    elif payload['root'] is not None:
                        binding = self.bindings.bind(member.location_ref, member.vault_id, payload['root'],
                            expected_revision=payload['expected_binding_revision'], expected_generation=payload['expected_generation'])
                    if kind == 'register':
                        snapshot = self.members.register(payload['member'],
                            expected_collection_revision=payload['expected_collection_revision'])
                    if self.members.snapshot() != snapshot:
                        raise OperationError('revision_conflict')
                    if binding is not None and self.bindings.resolve(member.location_ref)['binding'] != binding.model_dump():
                        raise OperationError('revision_conflict')
                except (MemberStoreError, BindingError, ContractError, OperationError, OSError) as error:
                    after = self._states()
                    changed = before != after
                    row.update(phase='partial' if changed else 'failed', after=after,
                        error='operation_partial' if changed else getattr(error, 'code', 'operation_io_error'),
                        receipt=self._receipt(operation_id, kind, member.vault_id, 'pending' if changed else 'failed', before, after))
                    self._save(path, row)
                    raise OperationError(row['error'], row['receipt']) from None
                after = self._states()
                row.update(phase='committed', after=after,
                    receipt=self._receipt(operation_id, kind, member.vault_id, 'succeeded', before, after))
                self._save(path, row)
                return {'contract_version': CONTRACT_VERSION, 'receipt': row['receipt'], 'replayed': False}
        except (MemberStoreError, BindingError, ContractError) as error:
            raise OperationError(error.code) from None
        except (OSError, TypeError, ValueError) as error:
            if isinstance(error, OperationError):
                raise
            raise OperationError('operation_io_error') from None

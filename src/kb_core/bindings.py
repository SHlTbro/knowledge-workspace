"""Explicit machine-local K02 bindings. No discovery, Registry or HTTP fallback."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .contracts import CONTRACT_VERSION, ContractError, validate_contract


class BindingError(ValueError):
    """Stable, sanitized boundary error; paths/private input are not echoed."""
    def __init__(self, code):
        self.code = code
        self.message = 'Machine binding operation refused.'
        super().__init__(self.message)


def _path(value):
    if not isinstance(value, (str, Path)):
        raise BindingError('binding_path_invalid')
    raw = str(value)
    path = Path(raw)
    if (not path.is_absolute() or raw != raw.strip() or raw.startswith(('\\\\', '//'))
            or path.parent == path):
        raise BindingError('binding_path_invalid')
    parts = raw.replace('\\', '/').split('/')
    for part in parts[1:]:
        if (part in {'.', '..'} or part.endswith((' ', '.'))
                or any(ord(c) < 32 or c in ':*?"<>|' for c in part)
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise BindingError('binding_path_invalid')
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise BindingError('binding_path_unavailable') from None
        if component.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise BindingError('binding_reparse_refused')
    # Resolve Windows short-name aliases only after rejecting reparse components.
    try:
        return Path(os.path.normcase(str(path.resolve(strict=False))))
    except OSError:
        raise BindingError('binding_path_unavailable') from None


def _overlaps(first, second):
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise BindingError('binding_store_invalid')
        value[key] = item
    return value


class BindingStore:
    """One explicit local JSON authority. Callers own authorization/member lookup.

    ponytail: one store-wide cooperative lock and linear collision scan; split
    only if measured contention warrants it. This is not an OS write sandbox.
    """
    def __init__(self, path):
        self.path = _path(path)
        self._store_id = None

    @contextmanager
    def _locked(self):
        if os.name != 'nt':
            raise BindingError('binding_platform_unsupported')
        import msvcrt
        _path(self.path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _path(self.path)
            lock = _path(self.path.with_name(self.path.name + '.lock'))
            stream = lock.open('a+b')
        except OSError:
            raise BindingError('binding_store_unavailable') from None
        with stream:
            stream.seek(0, 2)
            if not stream.tell():
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise BindingError('binding_busy') from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

    def _load(self):
        _path(self.path)
        if not self.path.exists():
            self._store_id = None
            return []
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=_pairs)
            if (not isinstance(value, dict) or set(value) != {'schema_version', 'store_id', 'bindings'}
                    or value['schema_version'] != CONTRACT_VERSION or not isinstance(value['bindings'], list)
                    or not isinstance(value['store_id'], str) or not re.fullmatch('[0-9a-f]{32}', value['store_id'])):
                raise BindingError('binding_store_invalid')
            self._store_id = value['store_id']
            records = [validate_contract('MachineBinding', item) for item in value['bindings']]
            for key in ('binding_id', 'vault_id'):
                ids = [getattr(record, key).casefold() for record in records]
                if len(ids) != len(set(ids)):
                    raise BindingError('binding_store_invalid')
            roots = [_path(record.root) for record in records if record.root is not None]
            if any(_overlaps(root, prior) for index, root in enumerate(roots) for prior in roots[:index]):
                raise BindingError('binding_store_invalid')
            return records
        except (ContractError, OSError, UnicodeError, json.JSONDecodeError, TypeError):
            raise BindingError('binding_store_invalid') from None

    def _save(self, records):
        store_id = self._store_id or uuid.uuid4().hex
        value = {'schema_version': CONTRACT_VERSION, 'store_id': store_id,
                 'bindings': [record.model_dump() for record in records]}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                             dir=self.path.parent, prefix=self.path.name + '.', suffix='.tmp',
                                             delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                stream.flush(); os.fsync(stream.fileno())
            _path(self.path)
            os.replace(temporary, self.path)
            self._store_id = store_id
        except OSError:
            raise BindingError('binding_write_failed') from None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    @staticmethod
    def _find(records, binding_id):
        return next((record for record in records if record.binding_id == binding_id), None)

    @staticmethod
    def _cas(record, revision, generation):
        if (type(revision) is not int or type(generation) is not int
                or revision != (record.revision if record else 0)
                or generation != (record.generation if record else 0)):
            raise BindingError('binding_conflict')

    def bind(self, binding_id, vault_id, root, *, expected_revision, expected_generation):
        root = _path(root)
        if not root.is_dir():
            raise BindingError('binding_root_offline')
        with self._locked():
            records = self._load()
            previous = self._find(records, binding_id)
            self._cas(previous, expected_revision, expected_generation)
            if previous and previous.vault_id != vault_id:
                raise BindingError('binding_identity_conflict')
            for record in records:
                if record is previous:
                    continue
                if (record.binding_id.casefold() == str(binding_id).casefold()
                        or record.vault_id.casefold() == str(vault_id).casefold()
                        or (record.root is not None and _overlaps(root, _path(record.root)))):
                    raise BindingError('binding_root_collision')
            if previous and previous.active and _path(previous.root) == root:
                return previous
            try:
                record = validate_contract('MachineBinding', {
                    'schema_version': CONTRACT_VERSION, 'revision': (previous.revision if previous else 0) + 1,
                    'binding_id': binding_id, 'vault_id': vault_id, 'root': str(root),
                    'generation': (previous.generation if previous else 0) + 1, 'active': True,
                    'observed_at': datetime.now(timezone.utc).isoformat()})
            except ContractError:
                raise BindingError('binding_input_invalid') from None
            _path(root)
            self._save([item for item in records if item is not previous] + [record])
            return record

    def unbind(self, binding_id, *, expected_revision, expected_generation):
        with self._locked():
            records = self._load()
            previous = self._find(records, binding_id)
            self._cas(previous, expected_revision, expected_generation)
            if previous is None:
                raise BindingError('binding_not_found')
            if not previous.active:
                return previous
            value = previous.model_dump()
            value.update(revision=previous.revision + 1, generation=previous.generation + 1,
                         active=False, observed_at=datetime.now(timezone.utc).isoformat())
            record = validate_contract('MachineBinding', value)
            self._save([record if item is previous else item for item in records])
            return record

    def resolve(self, binding_id):
        record = self._find(self._load(), binding_id)
        if record is None:
            return {'status': 'unbound', 'binding': None}
        status = 'unbound'
        if record.active:
            root = _path(record.root)
            status = 'online' if root.is_dir() else 'offline'
        return {'status': status, 'binding': record.model_dump()}

    def snapshot(self):
        """Read all validated K02 records, including inactive root reservations.

        A missing store is an unbound collection; a malformed store is an error.
        This read creates no files and is not a multi-source atomic snapshot.
        """
        return [record.model_dump() for record in self._load()]

    def claim(self, binding_id):
        with self._locked():
            resolved = self.resolve(binding_id)
            if resolved['status'] != 'online':
                raise BindingError('binding_root_unavailable')
            return {**{key: resolved['binding'][key] for key in ('binding_id', 'vault_id', 'revision', 'generation', 'root')},
                    'store_path': str(self.path), 'store_id': self._store_id}

    @contextmanager
    def guard(self, claim):
        """Fence cooperative writes during the caller's actual local operation."""
        with self._locked():
            if not isinstance(claim, dict) or set(claim) != {'binding_id', 'vault_id', 'revision', 'generation', 'root', 'store_path', 'store_id'}:
                raise BindingError('binding_claim_invalid')
            resolved = self.resolve(claim['binding_id'])
            current = resolved['binding']
            if (resolved['status'] != 'online' or claim['store_path'] != str(self.path) or claim['store_id'] != self._store_id
                    or not isinstance(claim['store_path'], str) or not isinstance(claim['store_id'], str)
                    or any(type(claim[key]) is not type(current[key]) or claim[key] != current[key]
                           for key in ('binding_id', 'vault_id', 'revision', 'generation', 'root'))):
                raise BindingError('binding_claim_stale')
            yield Path(current['root'])

    def assert_claim(self, claim):
        with self.guard(claim) as root:
            return root

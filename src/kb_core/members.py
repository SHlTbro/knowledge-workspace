"""Offline K01 member storage. The supplied JSON file is the only source.

Collection revision is an internal storage envelope, not a new public contract.
Locks coordinate these writers; they do not grant OS protection from editors.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile

from .contracts import ContractError, MemberRecord, validate_contract


class MemberStoreError(ValueError):
    """Public failures never echo private member data or machine paths."""
    def __init__(self, code):
        self.code = code
        self.message = {
            'store_missing': 'Member store is not initialized.',
            'store_exists': 'Member store already exists.',
            'store_invalid': 'Member store is invalid.',
            'store_busy': 'Member store writer lock is held; retry after review.',
            'store_io_error': 'Member store I/O failed; inspect the current revision.',
            'member_invalid': 'Member record is invalid.',
            'member_exists': 'Member ID is already registered.',
            'member_not_found': 'Member identity was not found.',
            'member_id_mismatch': 'Stable member ID cannot be changed by update.',
            'identity_conflict': 'Member ID or alias is already reserved.',
            'revision_conflict': 'Member or collection revision has changed.',
        }[code]
        super().__init__(self.message)


def _record(payload) -> MemberRecord:
    try:
        return validate_contract('MemberRecord', payload)
    except ContractError:
        raise MemberStoreError('member_invalid') from None


def _unique_namespace(records):
    seen = {'shared'}  # Shared capability references own the shared> namespace.
    for record in records:
        for identity in [record.vault_id, *record.aliases]:
            key = identity.casefold()
            if key in seen:
                raise MemberStoreError('identity_conflict')
            seen.add(key)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def _expected(value, actual):
    if type(value) is not int or value < 1 or value != actual:
        raise MemberStoreError('revision_conflict')


class MemberStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def _writer(self):
        lock = self.path.with_suffix(self.path.suffix + '.lock')
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise MemberStoreError('store_busy') from None
        except OSError:
            raise MemberStoreError('store_io_error') from None
        try:
            yield
        except OSError:
            raise MemberStoreError('store_io_error') from None
        finally:
            os.close(descriptor)
            try:
                lock.unlink()
            except OSError:
                raise MemberStoreError('store_io_error') from None

    def _load(self):
        if self.path.is_symlink():
            raise MemberStoreError('store_invalid')
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=_json_object)
        except FileNotFoundError:
            raise MemberStoreError('store_missing') from None
        except (UnicodeError, ValueError):
            raise MemberStoreError('store_invalid') from None
        except OSError:
            raise MemberStoreError('store_io_error') from None
        try:
            if (not isinstance(value, dict) or set(value) != {'collection_revision', 'records'}
                    or type(value['collection_revision']) is not int or value['collection_revision'] < 1
                    or not isinstance(value['records'], list)):
                raise ValueError('invalid storage envelope')
            records = [_record(record) for record in value['records']]
            _unique_namespace(records)
        except (ValueError, MemberStoreError):
            raise MemberStoreError('store_invalid') from None
        return value['collection_revision'], records

    def _save(self, revision, records, *, initial=False):
        value = {'collection_revision': revision, 'records': [record.model_dump() for record in records]}
        temporary = None
        try:
            descriptor, name = tempfile.mkstemp(prefix='.' + self.path.name + '.', suffix='.tmp', dir=self.path.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            if initial:
                # Atomic no-overwrite creation; no half-written first store.
                os.link(temporary, self.path)
            else:
                os.replace(temporary, self.path)
            return value
        except FileExistsError:
            raise MemberStoreError('store_exists') from None
        except OSError:
            raise MemberStoreError('store_io_error') from None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def create(self):
        """Explicit empty store initialization. Existing bytes are never replaced."""
        with self._writer():
            if self.path.exists() or self.path.is_symlink():
                raise MemberStoreError('store_exists')
            return self._save(1, [], initial=True)

    def snapshot(self):
        revision, records = self._load()
        return {'collection_revision': revision, 'records': [record.model_dump() for record in records]}

    def resolve(self, identity):
        _, records = self._load()
        if isinstance(identity, str):
            key = identity.casefold()
            for record in records:
                if key in {value.casefold() for value in [record.vault_id, *record.aliases]}:
                    return record
        raise MemberStoreError('member_not_found')

    @contextmanager
    def guard(self, expected):
        """Hold the existing cooperative writer lock during dependent I/O.

        The exact member must still match. Raw filesystem editors do not
        participate in this protocol; this is not OS-level authorization.
        """
        record = _record(expected)
        with self._writer():
            current = self.resolve(record.vault_id)
            if current != record:
                raise MemberStoreError('revision_conflict')
            yield current

    def register(self, payload, *, expected_collection_revision):
        record = _record(payload)
        if record.revision != 1:
            raise MemberStoreError('revision_conflict')
        with self._writer():
            revision, records = self._load()
            _expected(expected_collection_revision, revision)
            if any(member.vault_id == record.vault_id for member in records):
                raise MemberStoreError('member_exists')
            _unique_namespace([*records, record])
            return self._save(revision + 1, [*records, record])

    def update(self, vault_id, payload, *, expected_collection_revision, expected_record_revision):
        record = _record(payload)
        if record.vault_id != vault_id:
            raise MemberStoreError('member_id_mismatch')
        with self._writer():
            revision, records = self._load()
            _expected(expected_collection_revision, revision)
            for index, previous in enumerate(records):
                if previous.vault_id == vault_id:
                    _expected(expected_record_revision, previous.revision)
                    _expected(record.revision, previous.revision + 1)
                    records[index] = record
                    _unique_namespace(records)
                    return self._save(revision + 1, records)
            raise MemberStoreError('member_not_found')

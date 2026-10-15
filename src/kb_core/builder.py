"""Bounded local file plans: stage/validate/place, never domain/Registry logic."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unicodedata
import uuid

TEXT_LIMIT = 2 * 1024 * 1024
BLOB_LIMIT = 64 * 1024 * 1024
BLOB_TOTAL_LIMIT = 256 * 1024 * 1024
MAX_FILES = 256
OWNER_FILE = '.kb-build-owner.json'


class BuildError(ValueError):
    def __init__(self, code):
        self.code = code
        self.message = 'Local build refused; retain files and inspect the operation.'
        super().__init__(self.message)


def _relative(value):
    # Adapted from the existing Workspace safety.relative_path without runtime imports.
    if (not isinstance(value, str) or not value or len(value) > 220
            or value != unicodedata.normalize('NFC', value) or '\\' in value or value.startswith('/')
            or any(ord(c) < 32 or c in ':*?"<>|' for c in value)):
        raise BuildError('unsafe_path')
    parts = value.split('/')
    if len(parts) > 16:
        raise BuildError('unsafe_path')
    for part in parts:
        if (part in {'', '.', '..'} or part.endswith((' ', '.'))
                or part.casefold() in {'.git', '.hg', '.svn', OWNER_FILE}
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise BuildError('unsafe_path')
    return value


def _absolute(value):
    if not isinstance(value, (str, Path)):
        raise BuildError('unsafe_path')
    raw = str(value); path = Path(raw)
    if not path.is_absolute() or path.parent == path or raw != raw.strip() or raw.startswith(('\\\\', '//')):
        raise BuildError('unsafe_path')
    for part in raw.replace('\\', '/').split('/')[1:]:
        if (part in {'.', '..'} or part.endswith((' ', '.'))
                or any(ord(c) < 32 or c in ':*?"<>|' for c in part)
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise BuildError('unsafe_path')
    for component in (path, *path.parents):
        try: info = component.lstat()
        except FileNotFoundError: continue
        except OSError: raise BuildError('path_unavailable') from None
        if component.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise BuildError('reparse_refused')
    try: return Path(os.path.normcase(str(path.resolve(strict=False))))
    except OSError: raise BuildError('path_unavailable') from None


def _ordinary(path):
    _absolute(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise BuildError('unsafe_file')
    return info


def _digest(path):
    _ordinary(path)
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan_hash(plan):
    try:
        raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise BuildError('plan_invalid') from None
    if len(raw) > 10 * 1024 * 1024:
        raise BuildError('plan_invalid')
    return hashlib.sha256(raw).hexdigest()


def _id(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise BuildError('operation_invalid')
    return value


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise BuildError('journal_invalid')
        result[key] = value
    return result


class LocalBuilder:
    """Only this explicit operation directory is consulted, never old sessions.

    ponytail: one cooperative state lock, at most 256 files; separate queues only
    if real contention warrants it. Arbitrary OS mutation is outside this lock.
    """
    def __init__(self, state_dir):
        self.state_dir = _absolute(state_dir)
        if not self.state_dir.is_dir(): raise BuildError('state_unavailable')

    @contextmanager
    def _locked(self):
        if os.name != 'nt': raise BuildError('platform_unsupported')
        import msvcrt
        try:
            _absolute(self.state_dir)
            with _absolute(self.state_dir / 'builder.lock').open('a+b') as stream:
                stream.seek(0, 2)
                if not stream.tell(): stream.write(b'0'); stream.flush()
                stream.seek(0)
                try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError: raise BuildError('operation_busy') from None
                try: yield
                finally:
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            raise BuildError('build_io_error') from None

    def _read(self, operation_id):
        path = _absolute(self.state_dir / (_id(operation_id) + '.json'))
        if not path.exists(): return None
        try:
            if _ordinary(path).st_size > 1024 * 1024: raise BuildError('journal_invalid')
            record = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_object)
            if (set(record) != {'operation_id', 'signature', 'target', 'staging', 'owner', 'phase', 'files'}
                    or record['operation_id'] != operation_id or record['phase'] not in {'prepared', 'staged', 'validated', 'placed'}
                    or not re.fullmatch('[0-9a-f]{64}', record['signature']) or not re.fullmatch('[0-9a-f]{32}', record['owner'])
                    or not isinstance(record['files'], list) or not 1 <= len(record['files']) <= MAX_FILES):
                raise BuildError('journal_invalid')
            target, staging = _absolute(record['target']), _absolute(record['staging'])
            if staging.parent != target.parent or staging.name != '.kb-stage-' + record['owner']:
                raise BuildError('journal_invalid')
            text_total = blob_total = 0
            names = []
            for item in record['files']:
                if (set(item) != {'path', 'kind', 'bytes', 'sha256'} or item['kind'] not in {'text', 'blob'}
                        or type(item['bytes']) is not int or item['bytes'] < 0
                        or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                    raise BuildError('journal_invalid')
                _relative(item['path'])
                name = item['path'].casefold()
                if any(name == old or name.startswith(old + '/') or old.startswith(name + '/') for old in names):
                    raise BuildError('journal_invalid')
                names.append(name)
                if item['kind'] == 'text': text_total += item['bytes']
                else:
                    blob_total += item['bytes']
                    if item['bytes'] > BLOB_LIMIT: raise BuildError('journal_invalid')
            if text_total > TEXT_LIMIT or blob_total > BLOB_TOTAL_LIMIT: raise BuildError('journal_invalid')
            return record
        except (ValueError, TypeError, KeyError, OSError):
            raise BuildError('journal_invalid') from None

    def _save(self, record):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n', dir=self.state_dir,
                                             prefix='.journal-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n'); stream.flush(); os.fsync(stream.fileno())
            destination = _absolute(self.state_dir / (record['operation_id'] + '.json'))
            os.replace(temporary, destination)
        finally:
            if temporary is not None and temporary.exists(): temporary.unlink()

    def _compile(self, plan, authorized_target, authorized_source_roots, expected_hash):
        if not isinstance(plan, dict) or set(plan) != {'operation_id', 'target', 'files'}:
            raise BuildError('plan_invalid')
        operation_id = _id(plan['operation_id']); target = _absolute(plan['target'])
        if target != _absolute(authorized_target) or target.is_relative_to(self.state_dir) or self.state_dir.is_relative_to(target):
            raise BuildError('target_not_authorized')
        if not target.parent.is_dir(): raise BuildError('target_parent_unavailable')
        if expected_hash != plan_hash(plan): raise BuildError('confirmation_changed')
        if not isinstance(authorized_source_roots, (tuple, list)): raise BuildError('source_not_authorized')
        roots = [_absolute(root) for root in authorized_source_roots]
        if not isinstance(plan['files'], list) or not 1 <= len(plan['files']) <= MAX_FILES:
            raise BuildError('plan_invalid')
        files = []; names = []; text_total = 0; blob_total = 0
        for item in plan['files']:
            if not isinstance(item, dict) or not isinstance(item.get('kind'), str) or item['kind'] not in {'text', 'blob'}:
                raise BuildError('plan_invalid')
            kind = item['kind']; key = 'text' if kind == 'text' else 'source'
            if (set(item) != {'path', 'kind', key, 'bytes', 'sha256'} or type(item['bytes']) is not int
                    or item['bytes'] < 0 or not isinstance(item['sha256'], str)
                    or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                raise BuildError('plan_invalid')
            name = _relative(item['path']); normalized = name.casefold()
            if any(normalized == old or normalized.startswith(old + '/') or old.startswith(normalized + '/') for old in names):
                raise BuildError('plan_collision')
            names.append(normalized)
            if kind == 'text':
                if not isinstance(item[key], str) or len(item[key]) > TEXT_LIMIT: raise BuildError('text_limit')
                try: raw = item[key].encode('utf-8')
                except UnicodeError: raise BuildError('plan_invalid') from None
                text_total += len(raw)
                if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                    raise BuildError('payload_mismatch')
                if text_total > TEXT_LIMIT: raise BuildError('text_limit')
            else:
                source = _absolute(item[key])
                if not any(source.is_relative_to(root) for root in roots) or source.is_relative_to(self.state_dir):
                    raise BuildError('source_not_authorized')
                blob_total += item['bytes']
                if item['bytes'] > BLOB_LIMIT or blob_total > BLOB_TOTAL_LIMIT: raise BuildError('resource_limit')
            files.append({field: item[field] for field in ('path', 'kind', 'bytes', 'sha256')})
        signature = plan_hash({'plan': plan, 'target': str(target), 'source_roots': sorted(str(root) for root in roots)})
        return operation_id, target, signature, files

    @staticmethod
    def _owner(record):
        return {**{key: record[key] for key in ('operation_id', 'signature', 'owner')},
                'manifest_sha256': plan_hash(record['files'])}

    def _verify(self, root, record, *, partial=False):
        root = _absolute(root)
        if not root.is_dir(): raise BuildError('build_missing')
        marker = _absolute(root / OWNER_FILE)
        try:
            if (_ordinary(marker).st_size > 4096
                    or json.loads(marker.read_text(encoding='utf-8'), object_pairs_hook=_object) != self._owner(record)):
                raise BuildError('ownership_conflict')
        except (OSError, ValueError, UnicodeError):
            raise BuildError('ownership_conflict') from None
        expected = {item['path'].casefold(): item for item in record['files']}
        directories = {str(Path(item['path']).parent).replace('\\', '/').casefold() for item in record['files']}
        for item in record['files']:
            directories.update('/'.join(item['path'].split('/')[:index]).casefold() for index in range(1, len(item['path'].split('/'))))
        seen = set()
        for current, dirs, files in os.walk(root, followlinks=False):
            for name in dirs:
                path = _absolute(Path(current) / name)
                if path.relative_to(root).as_posix().casefold() not in directories: raise BuildError('build_conflict')
            for name in files:
                path = _absolute(Path(current) / name); rel = path.relative_to(root).as_posix().casefold()
                if path == marker: continue
                if rel not in expected or rel in seen: raise BuildError('build_conflict')
                item = expected[rel]
                if _ordinary(path).st_size != item['bytes'] or _digest(path) != item['sha256']: raise BuildError('build_conflict')
                seen.add(rel)
        if not partial and seen != set(expected): raise BuildError('build_conflict')
        return seen

    @staticmethod
    def _result(record, *, replayed=False):
        return {key: record[key] for key in ('operation_id', 'phase', 'target', 'staging', 'files')} | {'replayed': replayed}

    def stage(self, plan, *, authorized_target, authorized_source_roots, expected_hash):
        operation_id, target, signature, files = self._compile(plan, authorized_target, authorized_source_roots, expected_hash)
        with self._locked():
            record = self._read(operation_id)
            if record and record['signature'] != signature: raise BuildError('operation_conflict')
            if record and record['files'] != files: raise BuildError('operation_conflict')
            if record and record['phase'] == 'placed':
                self._verify(target, record); return self._result(record, replayed=True)
            if record and record['phase'] == 'validated' and target.exists() and not Path(record['staging']).exists():
                self._verify(target, record)
                record['phase'] = 'placed'; self._save(record)
                return self._result(record, replayed=True)
            if target.exists(): raise BuildError('target_exists')
            if record is None:
                owner = uuid.uuid4().hex
                record = {'operation_id': operation_id, 'signature': signature, 'target': str(target),
                          'staging': str(target.parent / ('.kb-stage-' + owner)), 'owner': owner,
                          'phase': 'prepared', 'files': files}
                self._save(record)
            staging = _absolute(record['staging'])
            if not staging.exists():
                if record['phase'] != 'prepared': raise BuildError('build_missing')
                staging.mkdir()
                with (staging / OWNER_FILE).open('x', encoding='utf-8', newline='\n') as stream:
                    stream.write(json.dumps(self._owner(record), sort_keys=True) + '\n'); stream.flush(); os.fsync(stream.fileno())
            self._verify(staging, record, partial=record['phase'] == 'prepared')
            for item in plan['files']:
                destination = _absolute(staging / item['path'])
                if destination.exists(): continue
                destination.parent.mkdir(parents=True, exist_ok=True); _absolute(destination)
                with destination.open('xb') as output:
                    if item['kind'] == 'text': output.write(item['text'].encode('utf-8'))
                    else:
                        source = _absolute(item['source'])
                        if _ordinary(source).st_size != item['bytes']: raise BuildError('payload_mismatch')
                        digest = hashlib.sha256(); count = 0
                        with source.open('rb') as stream:
                            while chunk := stream.read(min(1024 * 1024, item['bytes'] - count + 1)):
                                count += len(chunk)
                                if count > item['bytes']: raise BuildError('payload_mismatch')
                                output.write(chunk); digest.update(chunk)
                        if count != item['bytes'] or digest.hexdigest() != item['sha256']: raise BuildError('payload_mismatch')
                    output.flush(); os.fsync(output.fileno())
            self._verify(staging, record)
            record['phase'] = 'staged'; self._save(record)
            return self._result(record)

    def validate(self, operation_id):
        with self._locked():
            record = self._read(operation_id)
            if record is None: raise BuildError('operation_missing')
            if record['phase'] == 'placed':
                self._verify(Path(record['target']), record); return self._result(record, replayed=True)
            self._verify(Path(record['staging']), record)
            record['phase'] = 'validated'; self._save(record)
            return self._result(record)

    def place(self, operation_id, *, authorized_target):
        with self._locked():
            record = self._read(operation_id)
            if record is None: raise BuildError('operation_missing')
            target, staging = _absolute(record['target']), _absolute(record['staging'])
            if target != _absolute(authorized_target): raise BuildError('target_not_authorized')
            if record['phase'] == 'placed':
                self._verify(target, record); return self._result(record, replayed=True)
            if record['phase'] != 'validated': raise BuildError('not_validated')
            replayed = not staging.exists()
            if target.exists():
                if staging.exists(): raise BuildError('target_exists')
                self._verify(target, record)
            else:
                self._verify(staging, record)
                staging.rename(target)  # Windows same-parent-volume rename refuses any existing target.
                self._verify(target, record)
            record['phase'] = 'placed'; self._save(record)
            return self._result(record, replayed=replayed)

    def build(self, plan, *, authorized_target, authorized_source_roots, expected_hash):
        staged = self.stage(plan, authorized_target=authorized_target, authorized_source_roots=authorized_source_roots, expected_hash=expected_hash)
        if staged['phase'] == 'placed': return staged
        self.validate(staged['operation_id'])
        return self.place(staged['operation_id'], authorized_target=authorized_target)

    def inspect(self, operation_id):
        record = self._read(operation_id)
        if record is None: return {'phase': 'unknown', 'status': 'missing'}
        try:
            target, staging = _absolute(record['target']), _absolute(record['staging'])
            if target.exists():
                if staging.exists(): raise BuildError('target_exists')
                self._verify(target, record)
            else: self._verify(staging, record, partial=record['phase'] == 'prepared')
            return self._result(record) | {'status': 'consistent'}
        except (BuildError, OSError, ValueError):
            return self._result(record) | {'status': 'conflict'}

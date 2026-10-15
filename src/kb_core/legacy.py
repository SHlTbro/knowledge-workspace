"""Bounded explicit legacy metadata extraction; no registration or activation."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from .contracts import local_root
from .bindings import BindingError, BindingStore


class LegacyError(Exception):
    """Stable public codes without private path or SQLite diagnostics."""


KINDS = {'registry', 'creation', 'manifest', 'active', 'authority', 'sidecar', 'receipt'}
MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 1000
AUTH_FIELDS = {'version', 'authority_id', 'generation', 'data_root', 'state_dir', 'binding_sha256'}
POLICY = {'adapter_id': None, 'manifest_ref': None, 'manifest_sha256': None,
          'blocked_read_paths': [], 'allowed_read_paths': []}
DESCRIPTOR = {key: None for key in ['descriptor_version', 'vault_id', 'name', 'domain', 'description']}
DESCRIPTOR.update(purpose=[], formats=[], tags=[], content_types=[{'id': None, 'label': None, 'description': None}],
                  entry_points=[{'label': None, 'path': None}],
                  agent={'instructions_ref': None, 'requested_capabilities': []},
                  extensions={'workspace_source_reader': POLICY, 'workspace_visibility': {'adapter_id': None}})


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _local_path(value, code):
    # Pure contract validation before stat/open: UNC must never be probed.
    try:
        raw = str(value)
        local_root(raw)
        # Public constructor validates ordinary Windows components before I/O,
        # then checks reparse ancestors/canonical spelling. It does not read or
        # create a Binding store. No private validator or new authority is used.
        return BindingStore(Path(raw)).path
    except (TypeError, ValueError, BindingError):
        raise LegacyError(code) from None


def _file(path):
    path = _local_path(path, 'source_unsafe')
    if 'session' in path.name.casefold() or 'token' in path.name.casefold():
        raise LegacyError('source_forbidden')
    try:
        for node in [path, *path.parents]:
            info = node.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise LegacyError('source_unsafe')
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
            raise LegacyError('source_unsafe')
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            raise LegacyError('source_limit')
        return path, raw
    except OSError:
        raise LegacyError('source_unavailable') from None


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise LegacyError('source_invalid')
        out[key] = value
    return out


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise LegacyError('source_invalid') from None


def _select(value, schema, excluded, location):
    """Known shapes only. Opaque extensions are evidence, never credential values.

    This is a metadata projection, not a general secret scanner. Even recognized
    prose is caller-reviewed metadata; it must not contain embedded credentials.
    """
    if schema is None:
        if value is not None and type(value) not in (str, int, bool, float):
            raise LegacyError('source_invalid')
        return value
    if isinstance(schema, list):
        if not isinstance(value, list) or len(value) > MAX_ROWS: raise LegacyError('source_invalid')
        return [_select(item, schema[0] if schema else None, excluded, location + '/item') for item in value]
    if not isinstance(value, dict): raise LegacyError('source_invalid')
    out = {}
    for key, item in value.items():
        if key in schema:
            out[key] = _select(item, schema[key], excluded, location + '/' + key)
        else:
            raw = json.dumps(item, ensure_ascii=False, sort_keys=True).encode('utf-8')
            excluded.append({'reason': 'opaque_metadata_requires_review', 'location': location + '/' + key,
                             'sha256': _hash(raw), 'bytes': len(raw)})
    return out


def _descriptor(value, excluded):
    return _select(value, DESCRIPTOR, excluded, 'descriptor')


def _rows(db, table, columns):
    # Only actual tables and fixed SQL identifiers from this module.
    kind = db.execute('SELECT type FROM sqlite_schema WHERE name=?', (table,)).fetchone()
    if not kind or kind[0] != 'table':
        raise LegacyError('source_schema_invalid')
    rows = [dict(row) for row in db.execute(f'SELECT {columns} FROM {table} LIMIT {MAX_ROWS + 1}')]
    if len(rows) > MAX_ROWS:
        raise LegacyError('source_limit')
    return rows


def _companions(path):
    sizes = {}
    for suffix in ['-wal', '-shm', '-journal']:
        companion = Path(str(path) + suffix)
        if companion.exists():
            info = companion.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise LegacyError('source_unsafe')
            if suffix != '-shm' and info.st_size:
                raise LegacyError('snapshot_required')
            sizes[suffix] = info.st_size
    return sizes


def extract(sources):
    """Extract only pinned explicit files; output is incomplete candidates, never authority.

    SQLite inputs must be reviewed snapshots: mode=ro, immutable and query_only.
    Nonempty WAL/journal rejects the input; empty WAL/SHM are ignored metadata.
    The caller must pin a backup snapshot, never a live database main file.
    Body-bearing creation.plan is never selected. No credential/session fallback.
    """
    if not isinstance(sources, list) or not 1 <= len(sources) <= 64:
        raise LegacyError('source_set_invalid')
    result = {'contract_version': 'kb-contracts-1.0', 'authority_effect': 'none',
              'candidates': {key: [] for key in ['registry', 'local_bindings', 'creations', 'anchors', 'authorities', 'sidecars', 'receipts']},
              'cache': [], 'excluded': [], 'sources': [], 'conflicts': [],
              'missing': ['K01 reviewed aliases/purpose_ref/agents_ref/navigation_refs/core_version/profiles/location_ref/display_ref/revision',
                          'K02 reviewed per-binding revision/generation/observed_at',
                          'K06 reviewed policy_revision/channel/revoked mapping',
                          'K03 evidenced native domain completion'],
              'requires_review': True}
    seen = set()
    accepted = {}
    snapshot_companions = {}
    try:
        for source in sources:
            if not isinstance(source, dict) or set(source) != {'path', 'kind', 'sha256'} or source['kind'] not in KINDS:
                raise LegacyError('source_set_invalid')
            path, raw = _file(source['path'])
            identity = os.path.normcase(str(path))
            if identity in seen:
                raise LegacyError('source_duplicate')
            seen.add(identity)
            digest = _hash(raw)
            if digest != source['sha256']:
                raise LegacyError('source_drift')
            kind = source['kind']
            ref = len(result['sources'])
            result['sources'].append({'kind': kind, 'path': str(path), 'sha256': digest, 'bytes': len(raw)})
            excluded = result['excluded']
            excluded_start = len(excluded)
            candidate = result['candidates']
            if kind in {'registry', 'creation'}:
                snapshot_companions[str(path)] = _companions(path)
                for suffix, size in snapshot_companions[str(path)].items():
                    excluded.append({'reason': 'ignored_snapshot_companion', 'suffix': suffix, 'bytes': size})
                with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
                    db.row_factory = sqlite3.Row
                    db.execute('PRAGMA query_only=ON')
                    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise LegacyError('snapshot_invalid')
                    if kind == 'registry':
                        for row in _rows(db, 'vaults', 'vault_id,location,location_key,descriptor_path,bindings,descriptor,enabled,observation,descriptor_source'):
                            if row['enabled'] not in (0, 1): raise LegacyError('source_invalid')
                            row['enabled'] = bool(row['enabled'])
                            row['location'] = _select(_json(row['location']), {key: None for key in ['kind','path','anchor','binding_id']}, excluded, 'location')
                            row['bindings'] = _select(_json(row['bindings']), [{key: None for key in ['reader','root','type_key','entry_file','title_key']}], excluded, 'reader_bindings')
                            row['descriptor'] = _descriptor(_json(row['descriptor']), excluded)
                            observation = _json(row.pop('observation'))
                            result['cache'].append({'source_ref': ref, 'vault_id': row['vault_id'], 'observation': _select(observation, {key: None for key in ['state','asset_count','scanned_at']}, excluded, 'observation')})
                            row['source_ref'] = ref
                            candidate['registry'].append(row)
                            if row['vault_id'] in accepted:
                                result['conflicts'].append({'code': 'duplicate_registry_identity', 'vault_id': row['vault_id']})
                            else:
                                accepted[row['vault_id']] = row['descriptor']
                        for row in _rows(db, 'local_bindings', 'binding_id,root,is_bound'):
                            if row['is_bound'] not in (0, 1): raise LegacyError('source_invalid')
                            row['is_bound'] = bool(row['is_bound']); row['source_ref'] = ref
                            candidate['local_bindings'].append(row)
                    else:
                        for row in _rows(db, 'creations', 'request_id,signature,target,phase,vault_id,length(CAST(plan AS BLOB)) AS excluded_plan_bytes'):
                            row['source_ref'] = ref; candidate['creations'].append(row)
                            if row['phase'] != 'registered':
                                result['conflicts'].append({'code': 'creation_unresolved', 'request_id': row['request_id']})
                        excluded.append({'source_ref': ref, 'field': 'creations.plan', 'reason': 'private_body_not_authorized; bytes only, hash unavailable without reading body'})
            elif kind == 'manifest':
                lines = raw.decode('utf-8').splitlines()
                starts = [index for index, line in enumerate(lines) if line.startswith('## 控制面注册表')]
                if len(starts) != 1: raise LegacyError('manifest_section_unsupported')
                count = 0
                for index in range(starts[0] + 1, len(lines)):
                    line = lines[index]
                    if line.startswith('## '): break
                    match = re.fullmatch(r'- ([^:]+): (.+)', line)
                    if match:
                        known = match[1] in {'eng', 'vault①', 'vault②', 'vault③', 'vault④', 'vault⑤'}
                        candidate['anchors'].append({'scope': match[1], 'locator': match[2], 'source_ref': ref,
                                                     'line': index + 1, 'interpretation': 'control anchor only' if known else 'unknown scope; requires review'})
                        count += 1
                        if not known: result['conflicts'].append({'code': 'manifest_scope_unknown', 'scope': match[1], 'source_ref': ref})
                if not count: raise LegacyError('source_invalid')
            else:
                value = _json(raw)
                if not isinstance(value, dict): raise LegacyError('source_invalid')
                if kind in {'active', 'authority'}:
                    metadata = _select(value, {key: None for key in AUTH_FIELDS}, excluded, kind)
                    candidate['authorities'].append({'kind': kind, 'source_ref': ref, 'metadata': metadata})
                    if set(metadata) != AUTH_FIELDS:
                        result['conflicts'].append({'code': 'authority_fields_missing', 'source_ref': ref})
                elif kind == 'sidecar':
                    candidate['sidecars'].append({'source_ref': ref, 'descriptor': _descriptor(value, excluded)})
                else:
                    fields = {key: None for key in ['status','vault_id','authority_id','generation','receipt_ref','receipt_sha256','asset_count']}
                    fields['changes'] = [{key: None for key in ['path','source_hash','sha256','deleted','query']}]
                    fields['changes'][0].pop('query')
                    record = _select(value, fields, excluded, 'receipt')
                    record.update(source_ref=ref, domain_result={'status': 'not_run'}, completion_interpretation='historical only; never K03 success')
                    candidate['receipts'].append(record)
                    if value.get('status') != 'complete': result['conflicts'].append({'code': 'receipt_unresolved', 'source_ref': ref})
            if _hash(_file(path)[1]) != digest:
                raise LegacyError('source_drift')
            for item in excluded[excluded_start:]: item['source_ref'] = ref
        authorities = result['candidates']['authorities']
        if authorities and (len(authorities) != 2 or {x['kind'] for x in authorities} != {'active', 'authority'} or authorities[0]['metadata'] != authorities[1]['metadata']):
            result['conflicts'].append({'code': 'authority_pair_conflict'})
        for sidecar in result['candidates']['sidecars']:
            descriptor = sidecar['descriptor']; identity = descriptor.get('vault_id')
            if identity in accepted and descriptor != accepted[identity]:
                result['conflicts'].append({'code': 'live_descriptor_differs_from_accepted', 'vault_id': identity})
        for source in result['sources']:
            path = Path(source['path'])
            if _hash(_file(path)[1]) != source['sha256']:
                raise LegacyError('source_drift')
            if str(path) in snapshot_companions and _companions(path) != snapshot_companions[str(path)]:
                raise LegacyError('source_drift')
        present = {item['kind'] for item in result['sources']}
        result['coverage'] = {'present_source_kinds': sorted(present), 'not_supplied': sorted(KINDS - present)}
        return result
    except LegacyError:
        raise
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise LegacyError('source_invalid') from None


def write_candidate(path, result):
    """Explicit new output only; no mutation of any authority source."""
    path = _local_path(path, 'target_unsafe')
    try:
        for parent in path.parents:
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise LegacyError('target_unsafe')
        raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        with path.open('xb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
    except FileExistsError:
        raise LegacyError('target_exists') from None
    except OSError:
        raise LegacyError('target_unavailable') from None

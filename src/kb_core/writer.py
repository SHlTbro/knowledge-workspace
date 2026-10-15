"""Authorized local bytes + K03 evidence, without session/SQLite/HTTP fallback.

This is a cooperative filesystem writer, not an OS sandbox or domain validator.
Callers own approval of source kind, operations and native domain evidence.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

from .bindings import BindingError, BindingStore
from .contracts import Change, LayerResult, OperationReceipt, local_root, relative_path
from .members import MemberStore, MemberStoreError


class WriterError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Authorization:
    """Explicit caller-approved operation scope; never inferred from enabled."""
    vault_id: str
    binding_id: str
    source_kind: str
    allow_write: bool
    allow_delete: bool = False


def _safe(root, reference):
    if not isinstance(reference, str):
        raise WriterError('writer_unsafe_path')
    try:
        relative_path(reference)
    except (ValueError, TypeError):
        raise WriterError('writer_unsafe_path') from None
    path = root / reference
    for part in path.parts[1:]:
        if (part.endswith((' ', '.')) or any(c in ':*?"<>|' or ord(c) < 32 for c in part)
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise WriterError('writer_unsafe_path')
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise WriterError('writer_io_failed') from None
        if (item.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400
                or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
            raise WriterError('writer_unsafe_path')
    return path


def _hash(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise WriterError('writer_unsafe_path')
    try:
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    except OSError:
        raise WriterError('writer_io_failed') from None


def _atomic(path, raw, *, create=False):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.writer-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        if create:
            # Same-volume link creates a new name atomically and refuses races.
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    except OSError:
        raise WriterError('writer_io_failed') from None
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                raise WriterError('writer_io_failed') from None


def _json(path, value):
    _atomic(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


class LocalWriter:
    def __init__(self, members: MemberStore, bindings: BindingStore, namespace: str, *,
                 authorization: Authorization, evidence_root: Path):
        if (not isinstance(authorization, Authorization) or authorization.allow_write is not True
                or type(authorization.allow_delete) is not bool):
            raise WriterError('writer_unauthorized')
        if not isinstance(authorization.source_kind, str) or authorization.source_kind not in {'managed', 'native'}:
            raise WriterError('writer_source_readonly')
        self._members, self._bindings, self._authorization = members, bindings, authorization
        try:
            member = members.resolve(namespace)
        except MemberStoreError:
            raise WriterError('writer_member_unavailable') from None
        if not member.enabled:
            raise WriterError('writer_member_unavailable')
        if (authorization.vault_id != member.vault_id or authorization.binding_id != member.location_ref):
            raise WriterError('writer_scope_mismatch')
        self._member = member.model_dump()
        self._claim = self._fresh_claim(member)
        self.operation_id = uuid.uuid4().hex
        try:
            local_root(str(evidence_root))
        except (ValueError, TypeError):
            raise WriterError('writer_evidence_scope') from None
        self._evidence_root = Path(evidence_root)
        _safe(self._evidence_root, self.operation_id)
        root = Path(self._claim['root'])
        if (self._evidence_root == root or self._evidence_root.is_relative_to(root)
                or root.is_relative_to(self._evidence_root)):
            raise WriterError('writer_evidence_scope')
        self._changes = {}
        self._started = self._failed = self._closed = False

    def _fresh_claim(self, member):
        try:
            claim = self._bindings.claim(member.location_ref)
        except BindingError:
            raise WriterError('writer_binding_unavailable') from None
        if claim['vault_id'] != member.vault_id or claim['binding_id'] != member.location_ref:
            raise WriterError('writer_identity_conflict')
        return claim

    @contextmanager
    def _scope(self):
        if self._failed:
            raise WriterError('writer_interrupted')
        if self._closed:
            raise WriterError('writer_closed')
        try:
            member = self._members.resolve(self._member['vault_id'])
        except MemberStoreError:
            raise WriterError('writer_stale') from None
        if member.model_dump() != self._member:
            raise WriterError('writer_stale')
        fresh = self._fresh_claim(member)
        if fresh != self._claim:
            raise WriterError('writer_stale')
        try:
            with self._bindings.guard(fresh) as root:
                with self._members.guard(self._member):
                    yield root
        except (BindingError, MemberStoreError):
            raise WriterError('writer_stale') from None

    def _pending(self, change, before_hash):
        directory = _safe(self._evidence_root, self.operation_id)
        if not self._started:
            try:
                self._evidence_root.mkdir(parents=True, exist_ok=True)
                directory.mkdir(exist_ok=False)
            except OSError:
                raise WriterError('writer_evidence_scope') from None
            self._started = True
        _json(_safe(self._evidence_root, self.operation_id+'/pending.json'), {
            'status':'pending', 'operation_id':self.operation_id, 'binding_claim':self._claim,
            'source_kind':self._authorization.source_kind, 'intent':change.model_dump(),
            'before_sha256':before_hash, 'confirmed_changes':[c.model_dump() for c in self._changes.values()]})

    @staticmethod
    def _expected(current, expected, *, deletion=False):
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise WriterError('writer_expected_hash_invalid')
        if (current is not None or deletion) and expected is None:
            raise WriterError('writer_expected_hash_required')
        if expected != current:
            raise WriterError('writer_source_changed')

    def _target(self, root, reference):
        path = _safe(root, reference)
        if any(key.casefold() == reference.casefold() and key != reference for key in self._changes):
            raise WriterError('writer_unsafe_path')
        return path

    def write(self, reference, raw, *, expected_hash=None):
        if not isinstance(raw, bytes):
            raise WriterError('writer_bytes_required')
        with self._scope() as root:
            path = self._target(root, reference)
            before = _hash(path)
            self._expected(before, expected_hash)
            after = hashlib.sha256(raw).hexdigest()
            change = Change(path=reference, sha256=after, deleted=False)
            self._pending(change, before)
            try:
                _safe(root, reference)
                if _hash(path) != before:
                    raise WriterError('writer_source_changed')
                _atomic(path, raw, create=before is None)
                self._changes[reference] = change
            except WriterError:
                self._failed = True
                raise
            return after

    def delete(self, reference, *, expected_hash):
        if self._authorization.allow_delete is not True:
            raise WriterError('writer_unauthorized')
        with self._scope() as root:
            path = self._target(root, reference)
            before = _hash(path)
            self._expected(before, expected_hash, deletion=True)
            if before is None:
                raise WriterError('writer_source_changed')
            change = Change(path=reference, sha256=None, deleted=True)
            self._pending(change, before)
            try:
                _safe(root, reference)
                if _hash(path) != before:
                    raise WriterError('writer_source_changed')
                path.unlink()
                self._changes[reference] = change
            except OSError:
                self._failed = True
                raise WriterError('writer_io_failed') from None
            except WriterError:
                self._failed = True
                raise

    def complete(self, *, domain_result: LayerResult | None = None, domain_sources=None,
                 display_requested=False) -> OperationReceipt:
        if type(display_requested) is not bool:
            raise WriterError('writer_display_invalid')
        with self._scope() as root:
            if not self._changes:
                raise WriterError('writer_no_changes')
            sources = {key:_hash(_safe(root,key)) for key in self._changes}
            if sources != {key:c.sha256 for key,c in self._changes.items()}:
                raise WriterError('writer_source_changed')
            try:
                domain = LayerResult(status='not_run', evidence_refs=[]) if domain_result is None else LayerResult.model_validate(domain_result.model_dump())
            except (ValueError, AttributeError):
                raise WriterError('writer_domain_invalid') from None
            if domain_sources is not None:
                if not isinstance(domain_sources, dict):
                    raise WriterError('writer_domain_unbound')
                domain_sources = dict(domain_sources)
                try:
                    for key, value in domain_sources.items():
                        Change(path=key, sha256=value, deleted=value is None)
                except (ValueError, TypeError):
                    raise WriterError('writer_domain_unbound') from None
            if domain.status == 'succeeded' and domain_sources != sources:
                raise WriterError('writer_domain_unbound')
            pins = []
            for ref in domain.evidence_refs:
                if ref.casefold() in {self.operation_id+'/'+name for name in ['pending.json','system.json','receipt.json']}:
                    raise WriterError('writer_domain_unbound')
                evidence = _safe(self._evidence_root, ref)
                digest = _hash(evidence)
                if digest is None or evidence.stat().st_size == 0:
                    raise WriterError('writer_evidence_unavailable')
                pins.append({'path':ref,'sha256':digest,'bytes':evidence.stat().st_size})
            system_ref = self.operation_id+'/system.json'
            _json(_safe(self._evidence_root, system_ref), {
                'binding_claim':self._claim, 'member_revision':self._member['revision'],
                'sources':sources, 'domain_sources':domain_sources, 'domain_evidence_pins':pins,
                'scope':'Location/source-byte check only. Native domain outcome is supplied by its authorized caller.'})
            receipt = OperationReceipt(operation_id=self.operation_id,
                operation_type='write' if any(not c.deleted for c in self._changes.values()) else 'delete',
                vault_id=self._member['vault_id'], domain_result=domain,
                system_result=LayerResult(status='succeeded', evidence_refs=[system_ref]),
                display_result=LayerResult(status='pending' if display_requested else 'not_run', evidence_refs=[]),
                changes=list(self._changes.values()), evidence=[system_ref,*domain.evidence_refs],
                observed_at=datetime.now(timezone.utc).isoformat())
            _json(_safe(self._evidence_root, self.operation_id+'/receipt.json'), receipt.model_dump())
            self._closed = True
            return receipt

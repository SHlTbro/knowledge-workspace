"""Owner-local, read-only browser for content admitted by native Vault rules."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from .bindings import BindingError, BindingStore
from .contracts import relative_path
from .display_policy import PolicyError, PolicyService, proposal_hash
from .members import MemberStoreError
from .operations import Coordinator, OperationError
from . import video_visibility

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_READER_ROOT = _PROJECT_ROOT / 'tools' / 'vault-workspace' / 'src'
if str(_READER_ROOT) not in sys.path:
    sys.path.insert(0, str(_READER_ROOT))
from vault_workspace import reader as _reader  # Reuse the bounded Vault reader.
from vault_workspace import inspiration_visibility as _inspiration_visibility
from vault_workspace import search as _search
from vault_workspace import source_reader as _source_reader

_STATIC = Path(__file__).with_name('local_web_static')
_STATIC_FILES = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                 '/app.css': ('app.css', 'text/css'), '/safe_external_url.js': ('safe_external_url.js', 'text/javascript')}
_MAX_STATIC = 512 * 1024
_MAX_PAGE = 50
_MAX_AUTHORIZATION_BATCH = 256
_MAX_LOCAL_SEARCH_BYTES = 32 * 1024 * 1024
_MAX_QUERY = 4096
_NO_AUTHORIZATION = object()
_REQUEST_AUTHORIZATION = ContextVar('kb_local_web_authorization', default=_NO_AUTHORIZATION)
_INDEX_LINK = re.compile(r'\[\[([^\]]+)\]\]')
_VIDEO_INDEX_ROW = re.compile(r'^-\s+([A-Z]{3}-[A-Za-z0-9-]+)\s*\|\s*active\s*\|', re.MULTILINE)
_DRIVE_PATH = re.compile(r'(?<![\w])(?:[A-Za-z]:[\\/])[^\s\]\[()\"<>`]+')
_UNC_PATH = re.compile(r'(?<![\w:])(?:\\\\|//)[^\s\]\[()\"<>`]+')
_SECRET_VALUE = re.compile(r'(?i)(\b(?:api[_-]?key|principal[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|cookie)\b\s*[:=]\s*)([^\s,;]+)')
_ACCESS_TOKEN = re.compile(r'^[A-Za-z0-9_-]{43,128}$')
_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"


class LocalWebError(ValueError):
    def __init__(self, code: str, status: int = 503):
        self.code, self.status = code, status
        super().__init__(code)


def _authorization_fingerprint(authorization: dict, identity: str) -> str:
    scoped={'binding':authorization['bindings'].get(identity),
            'entries':authorization['entries'].get(identity,{})}
    raw=json.dumps(scoped,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def build_fingerprint(root: Path | None = None) -> str:
    """Identify the local Web code without disclosing source paths or runtime data."""
    project_root = Path(root).resolve() if root is not None else _PROJECT_ROOT
    reader_root = project_root / 'tools' / 'vault-workspace' / 'src'
    static_root = project_root / 'src' / 'kb_core' / 'local_web_static'
    roots = (project_root / 'src' / 'kb_core', reader_root / 'vault_workspace')
    files = [path for root in roots for path in root.rglob('*.py')]
    files.extend(static_root / name for name in sorted({name for name, _ in _STATIC_FILES.values()}))
    files.append(project_root / 'tools' / 'kb_display_local.py')
    digest = hashlib.sha256()
    for path in sorted(set(files), key=lambda item: item.relative_to(project_root).as_posix().casefold()):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise OSError
            raw = path.read_bytes()
        except OSError:
            raise LocalWebError('local_build_identity_unavailable') from None
        relative = path.relative_to(project_root).as_posix().encode('utf-8')
        digest.update(relative + b'\0' + hashlib.sha256(raw).digest())
    return digest.hexdigest()


def _descriptor_read_blocks(descriptor: dict) -> frozenset[str]:
    config = _source_reader.configuration(descriptor)
    if config is None:
        return frozenset()
    return frozenset(path.casefold() for path in config['blocked_read_paths'])


def _require_not_descriptor_blocked(path: str, blocked: frozenset[str]) -> None:
    if relative_path(path).casefold() in blocked:
        raise LocalWebError('local_source_read_blocked', 403)


def _read_json(path: Path, *, limit: int = 128 * 1024) -> dict:
    path = BindingStore(path).path
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
        raise LocalWebError('local_config_invalid')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno()); raw = stream.read(limit + 1); after = os.fstat(stream.fileno())
    current = path.stat()
    sig = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_nlink)
    if len(raw) > limit or sig(before) != sig(opened) or sig(before) != sig(after) or sig(after) != sig(current):
        raise LocalWebError('local_config_changed')
    try:
        value = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, UnicodeError, RecursionError):
        raise LocalWebError('local_config_invalid') from None
    if not isinstance(value, dict):
        raise LocalWebError('local_config_invalid')
    return value


def _read_access_token(path: Path) -> str:
    """Read a private bearer token as a stable regular file; never log its value."""
    path = BindingStore(Path(path)).path
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 256:
            raise LocalWebError('local_access_token_unavailable', 503)
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(257)
            after = os.fstat(stream.fileno())
        current = path.stat(follow_symlinks=False)
        signature = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_nlink)
        if len(raw) > 256 or signature(before) != signature(opened) or signature(before) != signature(after) or signature(after) != signature(current):
            raise LocalWebError('local_access_token_unavailable', 503)
        if raw.endswith(b'\n'):
            raw = raw[:-1]
        if raw.endswith(b'\r'):
            raw = raw[:-1]
        token = raw.decode('ascii')
        if not _ACCESS_TOKEN.fullmatch(token):
            raise LocalWebError('local_access_token_unavailable', 503)
        return token
    except LocalWebError:
        raise
    except (OSError, ValueError, UnicodeError):
        raise LocalWebError('local_access_token_unavailable', 503) from None


def _stable_read(root: Path, relative: str) -> tuple[bytes, str]:
    """Use the existing path fence, then bind bytes to a stable ordinary file handle."""
    relative_path(relative)
    path = _reader._safe_path(root, relative)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > _reader.MAX_FILE_BYTES:
        raise LocalWebError('local_file_unavailable', 403)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise LocalWebError('local_file_unavailable', 403)
        raw = stream.read(_reader.MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    current = path.stat(follow_symlinks=False)
    sig = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_nlink)
    if len(raw) > _reader.MAX_FILE_BYTES or sig(before) != sig(opened) or sig(before) != sig(after) or sig(after) != sig(current):
        raise LocalWebError('local_file_changed', 409)
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise LocalWebError('local_file_not_utf8', 415) from None
    return raw, text


def _redact(text: str) -> tuple[str, bool]:
    changed = False
    for pattern in (_DRIVE_PATH, _UNC_PATH):
        text, count = pattern.subn('[本机绝对路径已隐藏]', text)
        changed |= count > 0
    text, count = _SECRET_VALUE.subn(r'\1[敏感值已隐藏]', text)
    return text, changed or count > 0


def _clean_link(link: str) -> str | None:
    target = link.replace('\\|', '|').split('|', 1)[0].split('#', 1)[0].strip().replace('\\', '/')
    if not target or target.startswith(('http:', 'https:', 'mailto:')):
        return None
    if not PurePosixPath(target).suffix:
        target += '.md'
    try:
        return relative_path(target)
    except ValueError:
        return None


def _wiki_entries(root: Path, config: dict, indexed_text: str | None = None) -> tuple[str, list[str]]:
    index = config['index']
    if indexed_text is None:
        _, indexed_text = _stable_read(root, index)
    allowed_roots = config['content_roots']
    found = []
    for raw in _INDEX_LINK.findall(indexed_text):
        target = _clean_link(raw)
        name = PurePosixPath(target).name if target else ''
        if target is None or name.startswith('_') or PurePosixPath(name).stem.casefold() in {'readme','index','log','hot','overview'}:
            continue
        prior_count = len(found)
        candidates = []
        if target.startswith('wiki/'):
            candidates.append(target)
        else:
            candidates.append((PurePosixPath(index).parent / target).as_posix())
            candidates.extend((PurePosixPath(prefix) / target).as_posix() for prefix in allowed_roots)
        for candidate in candidates:
            try:
                candidate = relative_path(candidate)
                if not any(candidate.startswith(prefix.rstrip('/') + '/') for prefix in allowed_roots):
                    continue
                path = _reader._safe_path(root, candidate)
                if path.is_file() and path.suffix.lower() == '.md':
                    found.append(candidate)
                    break
            except (OSError, ValueError):
                continue
        if len(found) == prior_count:
            # Some native MOCs link by basename while their cards live in
            # categorized subfolders (for example F-C06/F-C06-001-mem0.md).
            # Search only the explicitly configured content roots and accept
            # a fallback only when its basename resolves uniquely.
            matches = []
            for prefix in allowed_roots:
                try:
                    base = _reader._safe_path(root, prefix)
                    if not base.is_dir():
                        continue
                    for candidate_path in base.rglob(PurePosixPath(target).name):
                        if candidate_path.is_symlink() or not candidate_path.is_file():
                            continue
                        relative = candidate_path.relative_to(root).as_posix()
                        safe = _reader._safe_path(root, relative)
                        if safe.suffix.lower() == '.md':
                            matches.append(relative)
                except (OSError, ValueError):
                    continue
            matches = list(dict.fromkeys(matches))
            if len(matches) == 1:
                found.append(matches[0])
    # A few native indexes list complete asset IDs in a table without making
    # them Obsidian links. Honor only exact first-column IDs from that index.
    listed_ids = set()
    for line in indexed_text.splitlines():
        match = re.match(r'^\s*\|\s*([A-Z]{1,3}-[A-Za-z0-9_-]+)\s*\|', line)
        if match:
            listed_ids.add(match.group(1))
    for prefix in allowed_roots:
        try:
            base = _reader._safe_path(root, prefix)
            if not base.is_dir():
                continue
            for candidate_path in base.rglob('*.md'):
                if candidate_path.is_symlink() or not candidate_path.is_file():
                    continue
                if candidate_path.stem not in listed_ids or candidate_path.stem.casefold() in {'readme','index','log','hot','overview'}:
                    continue
                relative = candidate_path.relative_to(root).as_posix()
                if relative not in found:
                    found.append(relative)
        except (OSError, ValueError):
            continue
    return index, list(dict.fromkeys(found))


def _video_integrity(_root: Path):
    """Return the shipped, data-only verifier; never import Vault-local code."""
    return video_visibility.check_card


def _video_check_card(root: Path, checker, card_id: str, read_text) -> list[str]:
    return checker(card_id, read_text)


def _video_entries(root: Path, index: str, indexed_text: str) -> list[str]:
    """Read only active IDs from Vault④'s native bullet index."""
    entries = []
    for card_id in _VIDEO_INDEX_ROW.findall(indexed_text):
        path = f'wiki/cards/{card_id[:3].lower()}/{card_id}.md'
        try:
            target = _reader._safe_path(root, path)
            if target.is_file() and not target.is_symlink():
                entries.append(path)
        except (OSError, ValueError):
            continue
    return list(dict.fromkeys(entries))


class NativeCatalog:
    """Small per-vault readers; each preserves its own published-entry rules."""
    def __init__(self, instance: Path, policy_root: Path, config_path: Path, authorization_path: Path):
        self.coordinator = Coordinator(instance)
        self.policy = PolicyService(instance, policy_root)
        self.config_path = BindingStore(config_path).path
        self.authorization_path = BindingStore(authorization_path).path
        self._read_success_counts = {}
        self._read_count_lock = Lock()

    def record_read_success(self, identity: str) -> None:
        with self._read_count_lock:
            self._read_success_counts[identity] = self._read_success_counts.get(identity, 0) + 1

    def read_success_count(self, identity: str) -> int:
        with self._read_count_lock:
            return self._read_success_counts.get(identity, 0)

    @contextmanager
    def request_scope(self):
        """Validate the owner grant once per request, never across requests."""
        token=_REQUEST_AUTHORIZATION.set(None)
        try: yield
        finally: _REQUEST_AUTHORIZATION.reset(token)

    def _config(self) -> dict:
        config = _read_json(self.config_path)
        if set(config) != {'vaults'} or not isinstance(config['vaults'], dict):
            raise LocalWebError('local_config_invalid')
        return config['vaults']

    def _authorization(self, *, force: bool = False) -> dict:
        cached=_REQUEST_AUTHORIZATION.get()
        if not force and cached is not _NO_AUTHORIZATION and cached is not None: return cached
        value = _read_json(self.authorization_path, limit=2 * 1024 * 1024)
        if set(value) != {'schema_version','authorization_ref','authorization_sha256','authorization_document_path','bindings','entries'} or value.get('schema_version') != 'local-vault-read-1':
            raise LocalWebError('local_authorization_invalid',403)
        for key in ('authorization_sha256',):
            digest=value.get(key)
            if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest): raise LocalWebError('local_authorization_invalid',403)
        if not isinstance(value['bindings'],dict) or not isinstance(value['entries'],dict): raise LocalWebError('local_authorization_invalid',403)
        document_path = value.get('authorization_document_path')
        if not isinstance(document_path,str) or not Path(document_path).is_absolute():
            raise LocalWebError('local_authorization_invalid',403)
        try:
            document = BindingStore(Path(document_path)).path
            before=document.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>2*1024*1024:
                raise LocalWebError('local_authorization_changed',403)
            with document.open('rb') as stream:
                opened=os.fstat(stream.fileno()); raw=stream.read(2*1024*1024+1); after=os.fstat(stream.fileno())
            current=document.stat(follow_symlinks=False)
            signature=lambda item:(item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns,item.st_nlink)
            if (len(raw)>2*1024*1024 or signature(before)!=signature(opened)
                    or signature(before)!=signature(after) or signature(after)!=signature(current)
                    or hashlib.sha256(raw).hexdigest()!=value['authorization_sha256']):
                raise LocalWebError('local_authorization_changed',403)
        except LocalWebError:
            raise
        except (OSError,ValueError):
            raise LocalWebError('local_authorization_changed',403) from None
        for identity, files in value['entries'].items():
            if not isinstance(identity,str) or not isinstance(files,dict): raise LocalWebError('local_authorization_invalid',403)
            for path,digest in files.items():
                try: relative_path(path)
                except (ValueError,TypeError): raise LocalWebError('local_authorization_invalid',403) from None
                if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest): raise LocalWebError('local_authorization_invalid',403)
        if cached is None or force: _REQUEST_AUTHORIZATION.set(value)
        return value

    def _context(self, identity: str):
        if self.coordinator.operation_issues():
            raise LocalWebError('local_authority_incomplete', 503)
        try:
            member = self.coordinator.members.resolve(identity)
            if not member.enabled:
                raise LocalWebError('local_member_disabled', 403)
            claim = self.coordinator.bindings.claim(member.location_ref)
            if claim['vault_id'] != member.vault_id:
                raise LocalWebError('local_binding_conflict', 403)
            return member, claim, Path(claim['root'])
        except (MemberStoreError, BindingError, OperationError):
            raise LocalWebError('local_binding_unavailable', 503) from None

    def _authorized_text(self, identity: str, root: Path, path: str) -> str:
        member,claim,current_root=self._context(identity)
        if current_root!=root: raise LocalWebError('local_binding_changed',409)
        authorization=self._authorization()
        if authorization['bindings'].get(identity)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        expected=authorization['entries'].get(identity,{}).get(path)
        if expected is None: raise LocalWebError('local_read_not_authorized',403)
        try:
            with self.policy.guard(identity,path,'web',read_authorized=True,exporting=False) as grant:
                raw,text=_stable_read(root,path)
                if hashlib.sha256(raw).hexdigest()!=expected: raise LocalWebError('local_source_changed_review_required',409)
                if self.coordinator.bindings.resolve(member.location_ref)['binding']['generation']!=claim['generation']:
                    raise LocalWebError('local_binding_changed',409)
                return text
        except PolicyError as error:
            status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict','policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
            raise LocalWebError(error.code,status) from None

    def _authorized_native_call(self, identity: str, root: Path, path: str, callback):
        """Pin one exact resource before reading it and keep its K06 guard through validation."""
        member,claim,current_root=self._context(identity)
        if current_root!=root: raise LocalWebError('local_binding_changed',409)
        authorization=self._authorization()
        if authorization['bindings'].get(identity)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        expected=authorization['entries'].get(identity,{}).get(path)
        if expected is None: raise LocalWebError('local_read_not_authorized',403)
        try:
            with self.policy.guard(identity,path,'web',read_authorized=True,exporting=False) as grant:
                raw,text=_stable_read(root,path)
                if hashlib.sha256(raw).hexdigest()!=expected:
                    raise LocalWebError('local_source_changed_review_required',409)
                result=callback(text)
                current_raw,_=_stable_read(root,path)
                if hashlib.sha256(current_raw).hexdigest()!=expected:
                    raise LocalWebError('local_source_changed_review_required',409)
                if self.coordinator.bindings.resolve(member.location_ref)['binding']['generation']!=claim['generation']:
                    raise LocalWebError('local_binding_changed',409)
                return result
        except PolicyError as error:
            status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict','policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
            raise LocalWebError(error.code,status) from None

    def _video_issues(self, identity: str, root: Path, path: str) -> list[str]:
        """Validate a video card against one stable, owner-authorized native snapshot."""
        path=relative_path(path)
        member,claim,current_root=self._context(identity)
        if current_root!=root:raise LocalWebError('local_binding_changed',409)
        authorization=self._authorization()
        if authorization['bindings'].get(member.vault_id)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        # The card's declared transaction/source IDs determine the exact native
        # evidence set. Read it once under its exact grant, then pin that complete
        # set under one live K06/member/binding guard before native validation.
        card_text=self._authorized_text(identity,root,path)
        resources=list(dict.fromkeys([path,*video_visibility.dependency_paths(card_text)]))
        approved=authorization['entries'].get(member.vault_id,{})
        expected={resource:approved.get(resource) for resource in resources}
        if any(digest is None for digest in expected.values()):
            raise LocalWebError('native_integrity_support_restricted',403)
        checker=_video_integrity(root)
        card_id=PurePosixPath(path).stem
        try:
            with self.policy.guard_many(identity,resources,'web',read_authorized=True) as grants:
                if any(grants[resource]['binding_claim']['generation']!=claim['generation']
                       for resource in resources):
                    raise LocalWebError('local_binding_changed',409)
                cache={}
                for resource in resources:
                    raw,text=_stable_read(root,resource)
                    if hashlib.sha256(raw).hexdigest()!=expected[resource]:
                        raise LocalWebError('local_source_changed_review_required',409)
                    cache[resource]=text
                issues=_video_check_card(root,checker,card_id,cache.__getitem__)
                for resource in resources:
                    current_raw,_=_stable_read(root,resource)
                    if hashlib.sha256(current_raw).hexdigest()!=expected[resource]:
                        raise LocalWebError('local_source_changed_review_required',409)
                latest=self.coordinator.bindings.resolve(member.location_ref)
                latest_member=self.coordinator.members.resolve(member.vault_id)
                if (latest['status']!='online' or latest['binding']['generation']!=claim['generation']
                        or latest_member!=member):
                    raise LocalWebError('local_authority_changed',409)
                return issues
        except PolicyError as error:
            status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict',
                'policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
            if status==403:
                raise LocalWebError('native_integrity_support_restricted',403) from None
            raise LocalWebError(error.code,status) from None

    def _native_paths(self, identity: str, root: Path, vault_config: dict, *, enforce_policy: bool = True,
                      snapshot: dict | None = None) -> tuple[str | None, list[str]]:
        kind = vault_config.get('kind')
        if kind == 'wiki-index':
            indexed=self._authorized_text(identity,root,vault_config['index']) if enforce_policy else None
            return _wiki_entries(root, vault_config,indexed)
        if kind == 'frontend-directory':
            base = relative_path(vault_config['root'])
            entry_name = vault_config.get('entry', 'index.md')
            if '/' in entry_name or entry_name != 'index.md':
                raise LocalWebError('local_config_invalid')
            directory = _reader._safe_path(root, base)
            entries = []
            for child in sorted(directory.iterdir(), key=lambda p: p.name.casefold()):
                if child.is_symlink() or not child.is_dir():
                    continue
                relative = f'{base}/{child.name}/{entry_name}'
                try:
                    target = _reader._safe_path(root, relative)
                    if target.is_file(): entries.append(relative)
                except (OSError, ValueError):
                    continue
            return None, entries
        if kind == 'video-active':
            index_text=self._authorized_text(identity,root,vault_config['index']) if enforce_policy else None
            if index_text is None:
                _, index_text = _stable_read(root, vault_config['index'])
            index = vault_config['index']
            # The native index defines browse candidates. The detail/read path
            # applies the full integrity gate once and can show a precise denial.
            return index, _video_entries(root,index,index_text)
        if kind == 'inspiration-active':
            descriptor = _read_json(Path(vault_config['descriptor_path']))
            if not _inspiration_visibility.enabled(descriptor):
                raise LocalWebError('native_publication_blocked',503)
            blocked=_descriptor_read_blocks(descriptor)
            _require_not_descriptor_blocked('wiki/index.md',blocked)
            try:
                if enforce_policy:
                    rows = self._authorized_native_call(identity,root,'wiki/index.md',
                        lambda index_text: _inspiration_visibility.published(root,index_text))
                else: rows = _inspiration_visibility.published(root)
            except (OSError, ValueError, PermissionError):
                raise LocalWebError('native_publication_blocked', 503) from None
            if snapshot is not None:
                snapshot.update({'inspiration_descriptor':descriptor,'inspiration_blocks':blocked,
                                 'inspiration_rows':rows})
            entries = []
            for card_id in rows:
                path = f"30-cards/{card_id.split('-')[0].lower()}/{card_id}.md"
                try:
                    if _reader._safe_path(root,path).is_file(): entries.append(path)
                except (OSError,ValueError):
                    continue
            return 'wiki/index.md', entries
        raise LocalWebError('local_catalog_unavailable', 503)

    def _overview_paths(self, identity: str, root: Path, vault_config: dict) -> tuple[str | None, list[str]]:
        """Use the native index for Hub counts; defer expensive per-card video checks to detail."""
        if vault_config.get('kind')=='video-active':
            index=vault_config['index']
            index_text=self._authorized_text(identity,root,index)
            return index,_video_entries(root,index,index_text)
        return self._native_paths(identity,root,vault_config)

    def _is_current_native_entry(self, identity: str, root: Path, config: dict, path: str) -> tuple[str | None, bool]:
        kind=config.get('kind')
        if kind=='wiki-index':
            index=config['index']; text=self._authorized_text(identity,root,index)
            if path==index:return index,True
            _,entries=_wiki_entries(root,config,text)
            return index,path in entries
        if kind=='video-active':
            index=config['index']; text=self._authorized_text(identity,root,index)
            candidates=_video_entries(root,index,text)
            if path==index:return index,True
            if path not in candidates:return index,False
            if self._video_issues(identity,root,path):
                raise LocalWebError('local_video_card_integrity_failed',403)
            return index,True
        if kind=='inspiration-active':
            index='wiki/index.md'
            descriptor=_read_json(Path(config['descriptor_path']))
            if not _inspiration_visibility.enabled(descriptor):
                raise LocalWebError('native_publication_blocked',403)
            blocked=_descriptor_read_blocks(descriptor)
            _require_not_descriptor_blocked(path,blocked)
            if path==index:
                try:
                    self._authorized_native_call(identity,root,index,
                        lambda index_text: _inspiration_visibility.published(root,index_text))
                except (OSError,ValueError,PermissionError):raise LocalWebError('native_publication_blocked',403) from None
                return index,True
            match=_inspiration_visibility.CARD.fullmatch(path)
            if not match:return index,False
            try:
                rows=self._authorized_native_call(identity,root,index,
                    lambda index_text: _inspiration_visibility.published(root,index_text))
                if match[2] not in rows:return index,False
                card_text=self._authorized_native_call(identity,root,path,
                    lambda card_text: (_inspiration_visibility.check_card(root,path,rows,card_text),card_text)[1])
                self._recheck_inspiration_publication(identity,root,descriptor,card_path=path,card_text=card_text)
                return index,True
            except LocalWebError:
                raise
            except (OSError,ValueError,PermissionError):
                raise LocalWebError('native_publication_blocked',403) from None
        if kind=='frontend-directory':
            base=relative_path(config['root']); entry=config.get('entry','index.md')
            if '/' in entry or entry!='index.md':raise LocalWebError('local_config_invalid')
            base_parts=PurePosixPath(base).parts; parts=PurePosixPath(path).parts
            if len(parts)!=len(base_parts)+2 or parts[:len(base_parts)]!=base_parts or parts[-1]!=entry:return None,False
            directory=_reader._safe_path(root,'/'.join(parts[:-1])); target=_reader._safe_path(root,path)
            if directory.is_symlink() or not directory.is_dir() or target.is_symlink() or not target.is_file():return None,False
            return None,True
        raise LocalWebError('local_catalog_unavailable',503)

    def _recheck_inspiration_publication(self, identity: str, root: Path, descriptor: dict,
                                         *, card_path: str | None = None,
                                         card_text: str | None = None) -> None:
        """Revalidate publication against a fresh authorized index/transaction snapshot."""
        blocked=_descriptor_read_blocks(descriptor)
        _require_not_descriptor_blocked('wiki/index.md',blocked)
        match=_inspiration_visibility.CARD.fullmatch(card_path) if card_path is not None else None
        if card_path is not None:
            _require_not_descriptor_blocked(card_path,blocked)
        if card_path is not None and not match:
            raise LocalWebError('native_publication_blocked',403)
        try:
            def validate(index_text):
                rows=_inspiration_visibility.published(root,index_text)
                if match is not None:
                    if match[2] not in rows:
                        raise PermissionError('Card is no longer present in the active index')
                    _inspiration_visibility.check_card(root,card_path,rows,card_text)
                return None
            self._authorized_native_call(identity,root,'wiki/index.md',validate)
        except LocalWebError:
            raise
        except (OSError,ValueError,PermissionError):
            raise LocalWebError('native_publication_blocked',403) from None

    def _checked_read(self, identity: str, path: str) -> dict:
        with self.request_scope(): return self._checked_read_in_request(identity,path)

    @contextmanager
    def guard_delivery(self, identity: str, resources: dict[str, str], *,
                       expected_policy_source: str | None = None,
                       expected_authorization_fingerprint: str | None = None):
        """Keep exact K06 grants live through the HTTP response write."""
        with self.request_scope():
            if not isinstance(resources,dict): raise LocalWebError('local_response_scope_invalid',500)
            normalized={}
            for path,digest in resources.items():
                try: path=relative_path(path)
                except (TypeError,ValueError): raise LocalWebError('local_response_scope_invalid',500) from None
                if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):
                    raise LocalWebError('local_response_scope_invalid',500)
                normalized[path]=digest
            member,claim,root=self._context(identity)
            before=self._authorization(force=True)
            if before['bindings'].get(member.vault_id)!=claim['generation']:
                raise LocalWebError('local_binding_changed',409)
            if (expected_authorization_fingerprint is not None
                    and _authorization_fingerprint(before,member.vault_id)!=expected_authorization_fingerprint):
                raise LocalWebError('local_authorization_changed',403)
            approved=before['entries'].get(member.vault_id,{})
            for path,digest in normalized.items():
                if approved.get(path)!=digest:
                    raise LocalWebError('local_authorization_changed',403)
            policy=self.policy.get(member.vault_id,'web')
            if normalized and policy['policy'] is None: raise LocalWebError('policy_missing',403)
            if expected_policy_source is not None and policy['source']!=expected_policy_source:
                raise LocalWebError('policy_revision_conflict',409)
            if not normalized:
                yield
                return
            try:
                with self.policy.guard_many(member.vault_id,list(normalized),'web',read_authorized=True,
                        expected_source=expected_policy_source or policy['source']):
                    current=self._authorization(force=True)
                    if current['bindings'].get(member.vault_id)!=claim['generation']:
                        raise LocalWebError('local_binding_changed',409)
                    if (expected_authorization_fingerprint is not None
                            and _authorization_fingerprint(current,member.vault_id)!=expected_authorization_fingerprint):
                        raise LocalWebError('local_authorization_changed',403)
                    latest=current['entries'].get(member.vault_id,{})
                    for path,digest in normalized.items():
                        if latest.get(path)!=digest: raise LocalWebError('local_authorization_changed',403)
                        raw,_=_stable_read(root,path)
                        if hashlib.sha256(raw).hexdigest()!=digest:
                            raise LocalWebError('local_source_changed_review_required',409)
                    yield
            except PolicyError as error:
                status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict',
                    'policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
                raise LocalWebError(error.code,status) from None

    @contextmanager
    def guard_deliveries(self, deliveries: dict[str,dict]):
        """Hold independent policy scopes plus one shared Registry lock through send."""
        if not isinstance(deliveries,dict):
            raise LocalWebError('local_response_scope_invalid',500)
        if not deliveries:
            yield
            return
        with self.request_scope():
            before=self._authorization(force=True); roots={}; normalized={}; sources={}
            for identity in sorted(deliveries):
                scope=deliveries[identity]
                if not isinstance(identity,str) or not isinstance(scope,dict) or not isinstance(scope.get('resources'),dict):
                    raise LocalWebError('local_response_scope_invalid',500)
                member,claim,root=self._context(identity)
                if before['bindings'].get(member.vault_id)!=claim['generation']:
                    raise LocalWebError('local_binding_changed',409)
                fingerprint=scope.get('authorization_fingerprint')
                if fingerprint is not None and _authorization_fingerprint(before,member.vault_id)!=fingerprint:
                    raise LocalWebError('local_authorization_changed',403)
                resources={}; seen=set(); approved=before['entries'].get(member.vault_id,{})
                for path,digest in scope['resources'].items():
                    try: path=relative_path(path)
                    except (TypeError,ValueError): raise LocalWebError('local_response_scope_invalid',500) from None
                    if (path.casefold() in seen or not isinstance(digest,str)
                            or not re.fullmatch(r'[0-9a-f]{64}',digest)):
                        raise LocalWebError('local_response_scope_invalid',500)
                    seen.add(path.casefold())
                    if approved.get(path)!=digest: raise LocalWebError('local_authorization_changed',403)
                    resources[path]=digest
                roots[identity]=(root,claim); normalized[identity]=resources
                sources[identity]=scope.get('policy_source')
            try:
                with self.policy.guard_many_scoped({identity:list(resources) for identity,resources in normalized.items()},
                        'web',read_authorized=True,expected_sources=sources) as live:
                    current=self._authorization(force=True)
                    for identity,resources in normalized.items():
                        claim=live['claims'][identity]; old_root,old_claim=roots[identity]
                        if claim!=old_claim or Path(claim['root'])!=old_root:
                            raise LocalWebError('local_binding_changed',409)
                        if (current['bindings'].get(identity)!=claim['generation']
                                or _authorization_fingerprint(current,identity)!=
                                _authorization_fingerprint(before,identity)):
                            raise LocalWebError('local_authorization_changed',403)
                        approved=current['entries'].get(identity,{})
                        for path,digest in resources.items():
                            if approved.get(path)!=digest: raise LocalWebError('local_authorization_changed',403)
                            raw,_=_stable_read(Path(claim['root']),path)
                            if hashlib.sha256(raw).hexdigest()!=digest:
                                raise LocalWebError('local_source_changed_review_required',409)
                    yield
            except PolicyError as error:
                status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict',
                    'policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
                raise LocalWebError(error.code,status) from None

    def _checked_read_in_request(self, identity: str, path: str, *, include_search_text: bool = False) -> dict:
        try:
            path = relative_path(path)
        except (TypeError, ValueError):
            raise LocalWebError('local_path_invalid',400) from None
        member, claim, root = self._context(identity)
        authorization=self._authorization()
        if authorization['bindings'].get(member.vault_id)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        config = self._config().get(member.vault_id)
        if not isinstance(config, dict):
            raise LocalWebError('local_catalog_unavailable', 503)
        # Native checks may inspect card bodies, so each such path is guarded
        # inside _is_current_native_entry before the helper can open it.
        index, is_current = self._is_current_native_entry(member.vault_id,root,config,path)
        is_index = path == index
        if not is_current:
            raise LocalWebError('local_resource_not_indexed', 404)
        approved_hash=authorization['entries'].get(member.vault_id,{}).get(path)
        if approved_hash is None:
            raise LocalWebError('local_read_not_authorized',403)
        try:
            with self.policy.guard(member.vault_id, path, 'web', read_authorized=True, exporting=False) as grant:
                if grant['binding_claim']['generation'] != claim['generation']:
                    raise LocalWebError('local_binding_changed', 409)
                raw, text = _stable_read(root, path)
                source_hash=hashlib.sha256(raw).hexdigest()
                if approved_hash!=source_hash:
                    raise LocalWebError('local_source_changed_review_required',409)
                latest = self.coordinator.bindings.resolve(member.location_ref)
                latest_member = self.coordinator.members.resolve(member.vault_id)
                if (latest['status'] != 'online' or latest['binding']['generation'] != claim['generation']
                        or latest_member != member or self.policy.get(member.vault_id, 'web')['source'] != grant['source']):
                    raise LocalWebError('local_authority_changed', 409)
                redacted, was_redacted = _redact(text)
                fmt = PurePosixPath(path).suffix.lower().lstrip('.') or 'text'
                title = _reader._title(text, path, fmt if fmt in {'markdown','json','text'} else 'markdown')
                if not include_search_text:
                    current_authorization=self._authorization(force=True)
                    if current_authorization['bindings'].get(member.vault_id)!=claim['generation']:
                        raise LocalWebError('local_binding_changed',409)
                    current_hash=current_authorization['entries'].get(member.vault_id,{}).get(path)
                    if current_hash is None:
                        raise LocalWebError('local_read_not_authorized',403)
                    if current_hash!=approved_hash:
                        raise LocalWebError('local_source_changed_review_required',409)
                index_hash=authorization['entries'].get(member.vault_id,{}).get(index) if index else None
                result = {'vault_id': member.vault_id, 'title': title, 'path': path, 'format': fmt,
                        'text': redacted[:20_000], 'source_sha256': source_hash,
                        'truncated': len(redacted) > 20_000, 'redacted': was_redacted,
                        'binding_generation': claim['generation'], 'index_path': index,'index_sha256':index_hash}
                if include_search_text:
                    result['search_text'] = redacted
            if not include_search_text and config.get('kind')=='inspiration-active':
                descriptor=_read_json(Path(config['descriptor_path']))
                if is_index:
                    self._recheck_inspiration_publication(member.vault_id,root,descriptor)
                else:
                    self._recheck_inspiration_publication(member.vault_id,root,descriptor,
                        card_path=path,card_text=text)
            return result
        except PolicyError as error:
            status = 503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict',
                'policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
            raise LocalWebError(error.code, status) from None

    def vaults(self) -> dict:
        result,_=self.vaults_with_delivery()
        return result

    def vaults_with_delivery(self) -> tuple[dict,dict]:
        with self.request_scope(): return self._vaults_in_request()

    def _vaults_in_request(self) -> tuple[dict,dict]:
        if self.coordinator.operation_issues(): raise LocalWebError('local_authority_incomplete', 503)
        config = self._config(); rows=[];delivery={}
        for member in self.coordinator.members.snapshot()['records']:
            identity = member['vault_id']
            binding = self.coordinator.bindings.resolve(member['location_ref'])
            status = binding['status'] if member['enabled'] else 'disabled'
            count = None; catalog_entry_count = None; count_basis='unavailable'; scope_entry_count = 0
            if status == 'online' and identity in config:
                try:
                    kind=config[identity].get('kind')
                    index, entries = self._overview_paths(identity, Path(binding['binding']['root']), config[identity])
                    catalog_entry_count=len(entries)
                    if kind=='video-active':
                        count_basis='active index candidates; integrity checked per-card on detail'
                    else:
                        count = len(entries)
                        count_basis='current native index and domain gate'
                    authorization=self._authorization()
                    auth=authorization['entries'].get(identity,{})
                    policy_snapshot=self.policy.get(identity,'web')
                    policy=policy_snapshot['policy']
                    if policy is None: raise LocalWebError('policy_missing',403)
                    allowed={p.casefold() for p in policy['allow']}
                    denied={p.casefold() for p in policy['deny']+policy['revoked']}
                    scope_entry_count=sum(1 for path in entries if path in auth and path.casefold() in allowed and path.casefold() not in denied)
                    resources={}
                    if index:
                        index_hash=auth.get(index)
                        if index_hash is None: raise LocalWebError('local_read_not_authorized',403)
                        resources[index]=index_hash
                    else:
                        resources={path:auth[path] for path in entries
                            if path in auth and path.casefold() in allowed and path.casefold() not in denied}
                        if len(resources)>_MAX_AUTHORIZATION_BATCH:
                            raise LocalWebError('local_authorization_batch_exceeds_policy_limit',503)
                    delivery[identity]={'resources':resources,'policy_source':policy_snapshot['source'],
                        'authorization_fingerprint':_authorization_fingerprint(authorization,identity)}
                except (LocalWebError, OSError, ValueError):
                    status = 'restricted'; catalog_entry_count=None; count_basis='unavailable'
            rows.append({'vault_id': identity, 'name': member['name'], 'status': status,
                         'asset_count': count, 'scope_entry_count': scope_entry_count,
                         'catalog_entry_count': catalog_entry_count, 'authorized_scope_count': scope_entry_count,
                         'successful_read_count': self.read_success_count(identity),
                         'count_basis': count_basis})
        return {'vaults': rows, 'data_kind': 'owner-local real Vaults', 'sample_data': False},delivery

    def catalog(self, identity: str, offset: int, limit: int) -> dict:
        result,_=self.catalog_with_delivery(identity,offset,limit)
        return result

    def catalog_with_delivery(self, identity: str, offset: int, limit: int) -> tuple[dict,dict]:
        with self.request_scope(): return self._catalog_in_request(identity,offset,limit)

    def search(self, identity: str, query: str, offset: int, limit: int) -> dict:
        result,_=self.search_with_delivery(identity,query,offset,limit)
        return result

    def search_with_delivery(self, identity: str, query: str, offset: int, limit: int) -> tuple[dict,dict[str,str]]:
        """Return public results plus the private exact read set needed to send them safely."""
        with self.request_scope(): return self._search_in_request(identity,query,offset,limit)

    def resolve_wikilink(self, identity: str, source_path: str, target: str) -> dict:
        result,_=self.resolve_wikilink_with_delivery(identity,source_path,target)
        return result

    def resolve_wikilink_with_delivery(self, identity: str, source_path: str, target: str) -> tuple[dict,dict]:
        with self.request_scope():
            member,claim,_=self._context(identity)
            policy_snapshot=self.policy.get(member.vault_id,'web')
            authorization=self._authorization(force=True)
            authorization_fingerprint=_authorization_fingerprint(authorization,member.vault_id)
            source=relative_path(source_path)
            source_document=self._checked_read_in_request(identity,source)
            if not isinstance(target,str) or not target or len(target)>512:
                raise LocalWebError('local_link_invalid',400)
            link_target=target.replace('\\|','|').split('|',1)[0].strip()
            fragment=link_target.split('#',1)[1].strip() if '#' in link_target else None
            anchor=fragment if fragment and not fragment.startswith('^') and len(fragment)<=128 else None
            clean=_clean_link(target)
            if clean is None:raise LocalWebError('local_link_not_found',404)
            member,claim,root=self._context(identity)
            config=self._config().get(member.vault_id)
            if not isinstance(config,dict):raise LocalWebError('local_catalog_unavailable',503)
            _,entries=self._native_paths(member.vault_id,root,config)
            by_case={path.casefold():path for path in entries}
            possible=[clean]
            index=config.get('index') or 'wiki/index.md'
            possible.append((PurePosixPath(source).parent/PurePosixPath(clean)).as_posix())
            possible.append((PurePosixPath(index).parent/PurePosixPath(clean)).as_posix())
            for prefix in config.get('content_roots',[]):
                possible.append((PurePosixPath(prefix)/PurePosixPath(clean)).as_posix())
            raw_target=link_target.split('#',1)[0].strip().replace('\\','/')
            if config.get('kind')=='frontend-directory' and not PurePosixPath(raw_target).suffix:
                base=relative_path(config['root'])
                possible.append((PurePosixPath(base)/PurePosixPath(raw_target)/'index.md').as_posix())
            matches={by_case[path.casefold()] for path in possible if path.casefold() in by_case}
            if not matches and '/' not in raw_target:
                stem=PurePosixPath(raw_target).stem.casefold()
                matches={path for path in entries if PurePosixPath(path).stem.casefold()==stem}
            if not matches:raise LocalWebError('local_link_not_found',404)
            if len(matches)!=1:raise LocalWebError('local_link_ambiguous',409)
            path=next(iter(matches))
            document=self._checked_read_in_request(member.vault_id,path)
            current_policy=self.policy.get(member.vault_id,'web')
            if current_policy['source']!=policy_snapshot['source']:
                raise LocalWebError('policy_revision_conflict',409)
            current_authorization=self._authorization(force=True)
            if _authorization_fingerprint(current_authorization,member.vault_id)!=authorization_fingerprint:
                raise LocalWebError('local_authorization_changed',403)
            result={'vault_id':member.vault_id,'source_path':source_document['path'],'path':path,
                'title':document['title'],'source_sha256':document['source_sha256'],
                'binding_generation':claim['generation'],'anchor':anchor}
            resources={source_document['path']:source_document['source_sha256'],path:document['source_sha256']}
            for item in (source_document,document):
                if item.get('index_path') and item.get('index_sha256'):
                    resources[item['index_path']]=item['index_sha256']
            return result,{'resources':resources,'policy_source':policy_snapshot['source'],
                'authorization_fingerprint':authorization_fingerprint}

    def _search_batched_native(self, identity: str, root: Path, config: dict, entries: list[str],
                               candidate_paths: list[str], authorization: dict, *,
                               partial_card_failures: bool = False) -> tuple[list[dict],list[dict],int,int]:
        """Search wiki/directory/⑤ notes under one cooperative live K06 snapshot."""
        kind=config.get('kind'); index=config.get('index') if kind=='wiki-index' else ('wiki/index.md' if kind=='inspiration-active' else None)
        descriptor=None; descriptor_blocks=frozenset(); blocked_issues=[]
        if kind=='inspiration-active':
            descriptor=_read_json(Path(config['descriptor_path']))
            if not _inspiration_visibility.enabled(descriptor):raise LocalWebError('native_publication_blocked',503)
            descriptor_blocks=_descriptor_read_blocks(descriptor)
            _require_not_descriptor_blocked('wiki/index.md',descriptor_blocks)
            remaining=[]
            for path in candidate_paths:
                if path.casefold() in descriptor_blocks:
                    blocked_issues.append({'path':path,'reason':'local_source_read_blocked'})
                else:
                    remaining.append(path)
            candidate_paths=remaining
        resources=set(candidate_paths)
        if index is not None:
            if index not in authorization:raise LocalWebError('local_read_not_authorized',403)
            resources.add(index)
        if len(resources)>_MAX_AUTHORIZATION_BATCH:raise LocalWebError('local_authorization_batch_exceeds_policy_limit',400)
        if not resources:return [],[],0,0
        expected={path:authorization.get(path) for path in resources}
        if any(digest is None for digest in expected.values()):raise LocalWebError('local_read_not_authorized',403)
        documents=[];issues=list(blocked_issues);restricted_count=len(blocked_issues);scanned_count=0;loaded={}
        try:
            with self.policy.guard_many(identity,sorted(resources,key=str.casefold),'web',read_authorized=True):
                for path in sorted(resources,key=str.casefold):
                    try:
                        raw,text=_stable_read(root,path)
                        if hashlib.sha256(raw).hexdigest()!=expected[path]:
                            if path==index:raise LocalWebError('local_source_changed_review_required',409)
                            raise LocalWebError('local_source_changed_review_required',409)
                        loaded[path]=(raw,text)
                    except LocalWebError as error:
                        if path==index:raise
                        restricted_count+=1;issues.append({'path':path,'reason':error.code})
                    except (OSError,ValueError):
                        if path==index:raise LocalWebError('local_source_changed_review_required',409) from None
                        restricted_count+=1;issues.append({'path':path,'reason':'local_file_unavailable'})
                if index is not None and index not in loaded:
                    raise LocalWebError('local_source_changed_review_required',409)
                if kind=='wiki-index':
                    _,latest_entries=_wiki_entries(root,config,loaded[index][1])
                    if latest_entries!=entries:raise LocalWebError('local_source_changed_review_required',409)
                elif kind=='inspiration-active':
                    published_rows=_inspiration_visibility.published(root,loaded[index][1])
                for path in candidate_paths:
                    if path not in loaded:continue
                    scanned_count+=1
                    raw,text=loaded[path]
                    try:
                        if kind=='frontend-directory':
                            _,is_current=self._is_current_native_entry(identity,root,config,path)
                            if not is_current:raise LocalWebError('local_resource_not_indexed',404)
                        elif kind=='inspiration-active':
                            _inspiration_visibility.check_card(root,path,published_rows,text)
                        redacted,was_redacted=_redact(text)
                        fmt=PurePosixPath(path).suffix.lower().lstrip('.') or 'text'
                        title=_reader._title(text,path,fmt if fmt in {'markdown','json','text'} else 'markdown')
                        documents.append({'vault_id':identity,'path':path,'title':title,'type_key':None,
                            'format':fmt,'source_hash':hashlib.sha256(raw).hexdigest(),'search_text':redacted})
                    except (OSError,ValueError,PermissionError,LocalWebError) as error:
                        restricted_count+=1
                        issues.append({'path':path,'reason':getattr(error,'code','native_publication_blocked')})
                # The index and every searched source must retain the bytes pinned
                # at the beginning of the same bounded search request.
                for path,(raw_before,_) in loaded.items():
                    raw_after,_=_stable_read(root,path)
                    if hashlib.sha256(raw_after).hexdigest()!=hashlib.sha256(raw_before).hexdigest():
                        if partial_card_failures and path!=index:
                            issues.append({'path':path,'reason':'local_source_changed_review_required'})
                            documents=[document for document in documents if document['path']!=path]
                            continue
                        raise LocalWebError('local_source_changed_review_required',409)
                if kind=='inspiration-active':
                    current_descriptor=_read_json(Path(config['descriptor_path']))
                    current_blocks=_descriptor_read_blocks(current_descriptor)
                    _require_not_descriptor_blocked(index,current_blocks)
                    blocked_now={path for path in candidate_paths if path.casefold() in current_blocks}
                    if blocked_now and not partial_card_failures:
                        raise LocalWebError('local_source_read_blocked',403)
                    if current_blocks!=descriptor_blocks and not partial_card_failures:
                        raise LocalWebError('local_source_changed_review_required',409)
                    if partial_card_failures:
                        for path in candidate_paths:
                            reason=('local_source_read_blocked' if path in blocked_now else
                                    'local_source_changed_review_required' if current_blocks!=descriptor_blocks else None)
                            if reason is not None:
                                issues.append({'path':path,'reason':reason})
                                documents=[document for document in documents if document['path']!=path]
                    raw_index,current_index_text=_stable_read(root,index)
                    if hashlib.sha256(raw_index).hexdigest()!=expected[index]:
                        raise LocalWebError('local_source_changed_review_required',409)
                    try:
                        latest_rows=_inspiration_visibility.published(root,current_index_text)
                        if latest_rows!=published_rows:
                            if not partial_card_failures:
                                raise LocalWebError('local_source_changed_review_required',409)
                            for path in candidate_paths:
                                if path not in blocked_now:
                                    issues.append({'path':path,'reason':'local_source_changed_review_required'})
                                    documents=[document for document in documents if document['path']!=path]
                        for path in candidate_paths:
                            if path in loaded and path not in blocked_now and (latest_rows==published_rows or not partial_card_failures):
                                try:
                                    _inspiration_visibility.check_card(root,path,latest_rows,loaded[path][1])
                                except (OSError,ValueError,PermissionError,LocalWebError):
                                    if not partial_card_failures:
                                        raise
                                    issues.append({'path':path,'reason':'native_publication_blocked'})
                                    documents=[document for document in documents if document['path']!=path]
                    except LocalWebError:
                        raise
                    except (OSError,ValueError,PermissionError):
                        if not partial_card_failures:
                            raise LocalWebError('native_publication_blocked',403) from None
                        for path in candidate_paths:
                            issues.append({'path':path,'reason':'native_publication_blocked'})
                            documents=[document for document in documents if document['path']!=path]
        except PolicyError as error:
            status=503 if error.code in {'policy_busy','policy_authority_incomplete','policy_revision_conflict',
                'policy_source_changed','policy_authority_invalid','policy_lock_changed'} else 403
            raise LocalWebError(error.code,status) from None
        return documents,issues,restricted_count,scanned_count

    def _search_in_request(self, identity: str, query: str, offset: int, limit: int) -> dict:
        if not isinstance(query,str) or len(query)>2000 or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=30:
            raise LocalWebError('local_search_invalid',400)
        member,claim,root=self._context(identity)
        config=self._config().get(member.vault_id)
        if not isinstance(config,dict):raise LocalWebError('local_catalog_unavailable',503)
        index_path,entries=self._native_paths(member.vault_id,root,config)
        descriptor_blocks=frozenset()
        if config.get('kind')=='inspiration-active':
            descriptor_blocks=_descriptor_read_blocks(_read_json(Path(config['descriptor_path'])))
        initial_authorization=self._authorization()
        if initial_authorization['bindings'].get(member.vault_id)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        authorization=initial_authorization['entries'].get(member.vault_id,{})
        index_source_hash=authorization.get(index_path) if index_path else None
        current_policy=self.policy.get(member.vault_id,'web')['policy']
        if current_policy is None:raise LocalWebError('policy_missing',403)
        allow={path.casefold() for path in current_policy['allow']}
        denied={path.casefold() for path in current_policy['deny']}
        revoked={path.casefold() for path in current_policy['revoked']}
        candidate_paths=[];restricted_count=0;byte_count=0;scan_complete=True;issues=[]
        for path in entries:
            key=path.casefold()
            if key in descriptor_blocks:
                restricted_count+=1; issues.append({'path':path,'reason':'local_source_read_blocked'}); continue
            if key in denied or key in revoked or key not in allow or path not in authorization:
                restricted_count+=1; continue
            try:
                target=_reader._safe_path(root,path)
                info=target.stat(follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                    scan_complete=False;restricted_count+=1; continue
                if info.st_size>_reader.MAX_FILE_BYTES:
                    scan_complete=False;issues.append({'path':path,'reason':'local_file_unavailable'}); continue
                if byte_count+info.st_size>_MAX_LOCAL_SEARCH_BYTES:
                    scan_complete=False; break
                byte_count+=info.st_size;candidate_paths.append(path)
            except (OSError,ValueError):
                scan_complete=False;restricted_count+=1; issues.append({'path':path,'reason':'local_file_unavailable'})
        if config.get('kind') in {'wiki-index','frontend-directory','inspiration-active'}:
            documents,batched_issues,batched_restricted,scanned_count=self._search_batched_native(
                member.vault_id,root,config,entries,candidate_paths,authorization)
            if any(issue.get('reason') not in {'local_source_read_blocked','native_publication_blocked'}
                   for issue in batched_issues):
                scan_complete=False
            issues.extend(batched_issues);restricted_count+=batched_restricted
        else:
            documents=[];scanned_count=0
            for path in candidate_paths:
                try:
                    document=self._checked_read_in_request(member.vault_id,path,include_search_text=True)
                    scanned_count+=1
                    documents.append({'vault_id':member.vault_id,'path':path,'title':document['title'],
                        'type_key':None,'format':document['format'],'source_hash':document['source_sha256'],
                        'search_text':document['search_text']})
                except LocalWebError as error:
                    scan_complete=False;restricted_count+=1;issues.append({'path':path,'reason':error.code})
                except (OSError,ValueError):
                    scan_complete=False;restricted_count+=1;issues.append({'path':path,'reason':'local_file_unavailable'})
        ranked=_search.rank_documents(query,documents,limit=max(1,len(documents)))
        page=ranked[offset:offset+limit]
        # Counts and ranking are derived from every scanned document, not only the
        # visible page. Keep that full private read set attached to the response
        # lifecycle so revoked non-page matches cannot affect count metadata.
        delivery_scope={item['path']:item['source_hash'] for item in documents}
        if index_path and index_source_hash:
            delivery_scope[index_path]=index_source_hash
        current_authorization=self._authorization(force=True)
        if current_authorization['bindings'].get(member.vault_id)!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        current_entries=current_authorization['entries'].get(member.vault_id,{})
        if index_path and (index_source_hash is None or current_entries.get(index_path)!=index_source_hash):
            raise LocalWebError('local_authorization_changed',403)
        for path,digest in delivery_scope.items():
            if current_entries.get(path)!=digest:
                raise LocalWebError('local_authorization_changed',403)
        for item in page:item['status']='in_scope'
        return {'vault_id':member.vault_id,'query':query,'offset':offset,'limit':limit,'total':len(ranked),
            'complete':scan_complete,
            'items':page,'next_offset':offset+limit if offset+limit<len(ranked) else None,
            'binding_generation':claim['generation'],'index_path':index_path,'index_sha256':index_source_hash,
            'search_basis':'live authorized native entries; request-scoped BM25 projection'},delivery_scope

    def _catalog_in_request(self, identity: str, offset: int, limit: int) -> tuple[dict,dict]:
        member, claim, root = self._context(identity)
        config = self._config().get(member.vault_id)
        if not isinstance(config, dict): raise LocalWebError('local_catalog_unavailable', 503)
        native_snapshot={}
        index, entries = self._native_paths(member.vault_id, root, config,snapshot=native_snapshot)
        page = entries[offset:offset+limit]; items_by_path={}; inspiration_cards={}
        inspiration_descriptor=native_snapshot.get('inspiration_descriptor')
        inspiration_blocks=native_snapshot.get('inspiration_blocks',frozenset())
        inspiration_rows=native_snapshot.get('inspiration_rows')
        policy_snapshot=self.policy.get(member.vault_id,'web')
        current_policy = policy_snapshot['policy']
        if current_policy is None: raise LocalWebError('policy_missing', 403)
        authorization=self._authorization()
        authorization_fingerprint=_authorization_fingerprint(authorization,member.vault_id)
        allowed = {p.casefold() for p in current_policy['allow']}
        denied = {p.casefold() for p in current_policy['deny']}
        revoked = {p.casefold() for p in current_policy['revoked']}
        resources={}
        if index:
            index_hash=authorization['entries'].get(member.vault_id,{}).get(index)
            if index_hash is None: raise LocalWebError('local_read_not_authorized',403)
            resources[index]=index_hash
        if inspiration_descriptor is not None:
            candidates=[]
            authorized=authorization['entries'].get(member.vault_id,{})
            for path in page:
                key=path.casefold()
                if key in revoked: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_revoked'}
                elif key in denied: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_denied'}
                elif key not in allowed: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_not_allowed'}
                elif path.casefold() in inspiration_blocks:
                    items_by_path[path]={'path':path,'status':'restricted','reason':'local_source_read_blocked'}
                elif path not in authorized:
                    items_by_path[path]={'path':path,'status':'restricted','reason':'local_read_not_authorized'}
                else:
                    candidates.append(path)
            if candidates:
                try:
                    documents,issues,_,_=self._search_batched_native(member.vault_id,root,config,entries,
                        candidates,authorized,partial_card_failures=True)
                except LocalWebError as error:
                    for path in candidates:
                        items_by_path[path]={'path':path,'status':'restricted','reason':error.code}
                else:
                    documents_by_path={document['path']:document for document in documents}
                    reasons={}
                    for issue in issues:
                        path=issue.get('path'); reason=issue.get('reason','native_publication_blocked')
                        priorities={'local_source_read_blocked':5,'native_publication_blocked':4,
                                    'local_source_changed_review_required':3,'local_authorization_changed':2}
                        if path not in reasons or priorities.get(reason,1)>priorities.get(reasons[path],1):
                            reasons[path]=reason
                    for path in candidates:
                        document=documents_by_path.get(path)
                        if document is None:
                            items_by_path[path]={'path':path,'status':'restricted',
                                'reason':reasons.get(path,'native_publication_blocked')}
                            continue
                        resources[path]=document['source_hash']
                        items_by_path[path]={'name':PurePosixPath(path).stem,'path':path,'status':'in_scope'}
        else:
            for path in page:
                key=path.casefold()
                if key in revoked: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_revoked'}; continue
                if key in denied: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_denied'}; continue
                if key not in allowed: items_by_path[path]={'path':path,'status':'restricted','reason':'policy_not_allowed'}; continue
                approved_hash=authorization['entries'].get(member.vault_id,{}).get(path)
                if approved_hash is None:
                    items_by_path[path]={'path':path,'status':'restricted','reason':'local_read_not_authorized'}; continue
                resources[path]=approved_hash
                if config.get('kind')=='video-active':
                    try:
                        issues=self._video_issues(member.vault_id,root,path)
                        if issues:
                            items_by_path[path]={'path':path,'status':'restricted',
                                                 'reason':'local_video_card_integrity_failed','details':issues}
                            continue
                    except LocalWebError as error:
                        items_by_path[path]={'path':path,'status':'restricted','reason':error.code}; continue
                    except (OSError,ValueError,TypeError):
                        items_by_path[path]={'path':path,'status':'restricted',
                                             'reason':'local_video_card_integrity_failed'}; continue
                items_by_path[path]={'name':PurePosixPath(path).stem,'path':path,'status':'in_scope'}
        items=[items_by_path[path] for path in page]
        end=min(offset+limit,len(entries))
        scope_entry_total=sum(1 for path in entries if path in authorization['entries'].get(member.vault_id,{})
            and path.casefold() in allowed and path.casefold() not in denied and path.casefold() not in revoked)
        result={'vault_id':member.vault_id,'index_path':index,'offset':offset,'limit':limit,'total':len(entries),
                'scope_entry_total':scope_entry_total,
                'catalog_entry_count':len(entries),'authorized_scope_count':scope_entry_total,
                'successful_read_count':self.read_success_count(member.vault_id),
                'items':items,'next_offset':end if end < len(entries) else None,
                'binding_generation':claim['generation'],'pagination':'offset'}
        return result,{'resources':resources,'policy_source':policy_snapshot['source'],
            'authorization_fingerprint':authorization_fingerprint}


def pending_authorization_changes(*, instance: Path, policy_root: Path, catalog_config: Path,
                                 authorization_path: Path, vault_id: str) -> list[dict]:
    """List only changed paths reachable from the current native publication for owner review."""
    catalog=NativeCatalog(instance,policy_root,catalog_config,authorization_path)
    member,claim,root=catalog._context(vault_id)
    config=catalog._config().get(vault_id)
    if not isinstance(config,dict): raise LocalWebError('local_catalog_unavailable',503)
    with catalog.request_scope():
        authorization=catalog._authorization(force=True)
        previous_generation=authorization['bindings'].get(vault_id)
        if previous_generation is not None and previous_generation!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        index,paths=catalog._native_paths(vault_id,root,config,enforce_policy=False)
        candidates=[]
        states={}
        if index is not None:
            candidates.append(index); states[index]='native-index'
        for path in paths:
            candidates.append(path); states[path]='active'
        if config.get('kind')=='video-active':
            for path in paths:
                _,card_text=_stable_read(root,path)
                for dependency in video_visibility.dependency_paths(card_text):
                    dependency=relative_path(dependency)
                    candidates.append(dependency); states[dependency]='pinned-source'
        old=authorization['entries'].get(vault_id,{})
        changes=[]
        for path in dict.fromkeys(candidates):
            raw,_=_stable_read(root,path)
            digest=hashlib.sha256(raw).hexdigest()
            if old.get(path)==digest:
                continue
            changes.append({'path':path,'native_state':states[path],
                            'previous_sha256':old.get(path),'current_sha256':digest})
        return changes


def authorize_current_scope(*, instance: Path, policy_root: Path, catalog_config: Path,
                            authorization_path: Path, authorization_document: Path,
                            authorization_ref: str, vault_id: str, offset: int = 0,
                            limit: int = 255, path: str | None = None,
                            expected_sha256: str | None = None) -> dict:
    """Grant one bounded native-index batch, or refresh one exact file hash."""
    try:
        relative_path(authorization_ref)
        selected_path = relative_path(path) if path is not None else None
    except (TypeError, ValueError):
        raise LocalWebError('local_authorization_ref_invalid', 400) from None
    if (not isinstance(vault_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', vault_id)
            or type(offset) is not int or offset < 0 or type(limit) is not int
            or not 1 <= limit < _MAX_AUTHORIZATION_BATCH or selected_path is not None and offset != 0
            or expected_sha256 is not None and (selected_path is None or
                not re.fullmatch(r'[0-9a-f]{64}',expected_sha256))):
        raise LocalWebError('local_authorization_batch_invalid', 400)
    coordinator=Coordinator(instance); policy_root=BindingStore(policy_root).path
    config_path=BindingStore(catalog_config).path; auth_path=BindingStore(authorization_path).path
    doc=BindingStore(authorization_document).path
    if policy_root.exists() and not policy_root.is_dir(): raise LocalWebError('local_policy_store_invalid')
    policy_root.mkdir(parents=True,exist_ok=True)
    if not doc.is_file() or doc.stat().st_size>2*1024*1024: raise LocalWebError('local_authorization_document_invalid')
    document_raw=doc.read_bytes(); document_hash=hashlib.sha256(document_raw).hexdigest()
    catalog=NativeCatalog(instance,policy_root,config_path,auth_path)
    configs=catalog._config(); members=coordinator.members.snapshot()['records']
    member_row=next((row for row in members if row['vault_id']==vault_id),None)
    if member_row is None or vault_id not in configs: raise LocalWebError('local_vault_not_found',404)
    member,claim,root=catalog._context(vault_id)
    config=configs[vault_id]
    index,paths=catalog._native_paths(vault_id,root,config,enforce_policy=False)
    video_dependencies=set()
    if config.get('kind')=='video-active' and selected_path is not None:
        for card_path in paths:
            _,card_text=_stable_read(root,card_path)
            video_dependencies.update(relative_path(item) for item in video_visibility.dependency_paths(card_text))
    if selected_path is not None:
        if selected_path!=path or selected_path!=index and selected_path not in paths and selected_path not in video_dependencies:
            raise LocalWebError('local_resource_not_indexed',404)
        content_paths=[selected_path] if selected_path in paths else []
        selected={selected_path}
        mode='exact-file'
    else:
        if offset >= len(paths) and paths:
            raise LocalWebError('local_authorization_batch_out_of_range',400)
        content_paths=paths[offset:offset+limit]
        if not content_paths and index is None: raise LocalWebError('local_resource_not_indexed',404)
        selected=set(content_paths)
        mode='replace-batch'
    if index is not None: selected.add(index)
    if auth_path.exists():
        previous=catalog._authorization()
        if previous['authorization_sha256']!=document_hash:
            raise LocalWebError('local_authorization_document_changed_requires_regrant',409)
        previous_generation=previous['bindings'].get(vault_id)
        if previous_generation is not None and previous_generation!=claim['generation']:
            raise LocalWebError('local_binding_changed',409)
        entries={identity:dict(files) for identity,files in previous['entries'].items()}
        bindings=dict(previous['bindings'])
    else:
        previous=None; entries={}; bindings={}
    old_entries=entries.get(vault_id,{})
    if mode=='exact-file' and index is not None and index not in old_entries:
        selected.add(index)
    if config.get('kind')=='video-active' and mode=='replace-batch':
        for card_path in content_paths:
            _,card_text=_stable_read(root,card_path)
            for dependency in video_visibility.dependency_paths(card_text):
                try: _stable_read(root,dependency)
                except LocalWebError: continue
                selected.add(dependency)
    if not selected or len(selected)>_MAX_AUTHORIZATION_BATCH:
        raise LocalWebError('local_authorization_batch_exceeds_policy_limit',400)
    hashes=dict(old_entries) if mode=='exact-file' else {}
    selected_hashes={}
    for resource in sorted(selected,key=str.casefold):
        if vault_id=='project-inspiration' and resource!='wiki/index.md':
            descriptor=_read_json(Path(config['descriptor_path']))
            if not _inspiration_visibility.enabled(descriptor): raise LocalWebError('native_publication_blocked',403)
            _source_reader.configuration(descriptor)
            if _inspiration_visibility.CARD.fullmatch(resource) is None: raise LocalWebError('local_resource_not_indexed',404)
        if mode=='exact-file' and resource!=selected_path and resource in old_entries:
            continue
        raw,_=_stable_read(root,resource)
        selected_hashes[resource]=hashlib.sha256(raw).hexdigest()
    if selected_path is not None and expected_sha256 is not None and selected_hashes.get(selected_path)!=expected_sha256:
        raise LocalWebError('local_source_changed_review_required',409)
    hashes.update(selected_hashes)
    existing=catalog.policy.get(vault_id,'web'); current=existing['policy']
    wanted=set(selected)
    if current is None:
        expanded=sorted(wanted,key=str.casefold)
        policy={'policy_revision':1,'vault_id':vault_id,'allow':expanded,'deny':[],'revoked':[],'channel':'web'}
        legacy=None
    else:
        if existing['partial_review']: raise LocalWebError('local_existing_policy_requires_review',409)
        if mode=='replace-batch':
            managed={name.casefold() for name in old_entries}
            allow={name for name in current['allow'] if name.casefold() not in managed}
        else:
            allow=set(current['allow'])
        expanded=sorted(allow|wanted,key=str.casefold)
        policy={**current,'policy_revision':current['policy_revision']+1,'allow':expanded}
        legacy=existing['legacy_constraints'] if existing['legacy_constraints']['source_ref'] else None
    if len(expanded)>_MAX_AUTHORIZATION_BATCH:
        raise LocalWebError('local_authorization_batch_exceeds_policy_limit',400)
    if current is None or expanded!=sorted(current['allow'],key=str.casefold):
        catalog.policy.save(vault_id,policy,authorized_target=existing['metadata_path'],expected_source=existing['source'],
            reviewed_proposal_hash=proposal_hash(policy,legacy=legacy),review_ref=authorization_ref,legacy=legacy)
    entries[vault_id]=hashes; bindings[vault_id]=claim['generation']
    manifest={'schema_version':'local-vault-read-1','authorization_ref':authorization_ref,
              'authorization_sha256':document_hash,'authorization_document_path':str(doc),
              'bindings':bindings,'entries':entries}
    roots=[Path(catalog._context(row['vault_id'])[1]['root']) for row in members]
    _write_private_json(auth_path,manifest,roots)
    batch_end=min(offset+len(content_paths),len(paths))
    return {'status':'authorized','vault_id':vault_id,'mode':mode,'catalog_entry_count':len(paths),
            'authorized_scope_count':len(content_paths),'authorized_content_count':len(content_paths),
            'manifest_path_count':len(hashes),'batch_offset':offset if mode=='replace-batch' else None,
            'batch_limit':limit if mode=='replace-batch' else None,
            'next_offset':batch_end if mode=='replace-batch' and batch_end<len(paths) else None,
            'reauthorized_paths':[selected_path] if mode=='exact-file' else [],
            'content_counts':{vault_id:len(content_paths)},'authorization_sha256':document_hash,
            'private_scope_sha256':hashlib.sha256(json.dumps({vault_id:hashes},sort_keys=True,separators=(',',':')).encode()).hexdigest()}


def _write_private_json(path: Path, value: dict, vault_roots: list[Path]) -> None:
    path=BindingStore(path).path
    for root in vault_roots:
        root=BindingStore(root).path
        if path==root or path.is_relative_to(root) or root.is_relative_to(path):
            raise LocalWebError('local_state_inside_vault_refused',400)
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    temporary=None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb',dir=path.parent,prefix='.'+path.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        BindingStore(path); os.replace(temporary,path); temporary=None
    except OSError:
        raise LocalWebError('local_state_write_failed') from None
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    def setup(self):
        super().setup(); self.request.settimeout(20); self._started=False
    def log_message(self, *_):
        pass
    def _send(self,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        raw=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self._started=True; self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store'); self.send_header('Pragma','no-cache'); self.send_header('X-Content-Type-Options','nosniff')
        for key,value in (headers or {}).items(): self.send_header(key,value)
        self.end_headers()
        if self.command!='HEAD': self.wfile.write(raw)
    def _error(self,error):
        if not self._started: self._send(error.status,{'error':{'code':error.code}})
    def _authenticate(self):
        expected = _read_access_token(self.server.access_token_file)
        scheme, separator, supplied = self.headers.get('Authorization', '').partition(' ')
        if (not separator or scheme.casefold() != 'bearer' or len(supplied) > 256
                or not _ACCESS_TOKEN.fullmatch(supplied) or not hmac.compare_digest(supplied, expected)):
            raise LocalWebError('local_session_unauthorized', 401)
    def _static(self,path):
        name,mime=_STATIC_FILES[path]; target=BindingStore(_STATIC/name).path
        before=target.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>_MAX_STATIC: raise LocalWebError('local_static_unavailable')
        with target.open('rb') as stream:
            opened=os.fstat(stream.fileno()); raw=stream.read(_MAX_STATIC+1); after=os.fstat(stream.fileno())
        current=target.stat(); sig=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_nlink)
        if len(raw)>_MAX_STATIC or sig(before)!=sig(opened) or sig(before)!=sig(after) or sig(after)!=sig(current): raise LocalWebError('local_static_changed')
        self._send(200,raw,mime=mime+'; charset=utf-8',headers={'Content-Security-Policy':_CSP,'Referrer-Policy':'no-referrer','X-Frame-Options':'DENY'})
    def do_GET(self):
        try:
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed: raise LocalWebError('local_request_not_local',403)
            origin=self.headers.get('Origin')
            if origin is not None and origin not in {'http://'+host for host in allowed}: raise LocalWebError('local_request_not_local',403)
            target=urlsplit(self.path)
            if target.scheme or target.netloc or target.fragment: raise LocalWebError('local_request_invalid',400)
            if target.path in _STATIC_FILES:
                if target.query: raise LocalWebError('local_route_not_found',404)
                self._static(target.path); return
            if target.path == '/healthz':
                if target.query: raise LocalWebError('local_request_invalid',400)
                self._send(200, {'status': 'ok', 'build_id': self.server.build_id,
                                 'port': self.server.server_port})
                return
            if target.path not in {'/api/vaults','/api/catalog','/api/search','/api/resolve','/api/read'}: raise LocalWebError('local_route_not_found',404)
            # Loopback and same-origin checks constrain the network boundary; the bearer is visitor authentication.
            self._authenticate()
            if len(target.query)>_MAX_QUERY: raise LocalWebError('local_request_invalid',400)
            if target.path=='/api/vaults':
                if target.query: raise LocalWebError('local_request_invalid',400)
                for attempt in range(2):
                    result,deliveries=self.server.catalog.vaults_with_delivery()
                    try:
                        with self.server.catalog.guard_deliveries(deliveries):
                            self._send(200,result)
                        return
                    except LocalWebError:
                        if attempt or self._started: raise
                return
            if target.path=='/api/catalog':
                query=parse_qs(target.query,keep_blank_values=True,max_num_fields=3)
                if set(query)-{'vault_id','offset','limit'} or set(query)<{'vault_id'} or any(len(v)!=1 for v in query.values()): raise LocalWebError('local_request_invalid',400)
                offset=int(query.get('offset',['0'])[0]); limit=int(query.get('limit',['30'])[0])
                if offset<0 or limit<1 or limit>_MAX_PAGE: raise LocalWebError('local_request_invalid',400)
                identity=query['vault_id'][0]
                result,scope=self.server.catalog.catalog_with_delivery(identity,offset,limit)
                with self.server.catalog.guard_delivery(identity,scope['resources'],
                        expected_policy_source=scope['policy_source'],
                        expected_authorization_fingerprint=scope['authorization_fingerprint']):
                    self._send(200,result)
                return
            if target.path=='/api/search':
                query=parse_qs(target.query,keep_blank_values=True,max_num_fields=4)
                if set(query)-{'vault_id','q','offset','limit'} or not {'vault_id','q'}<=set(query) or any(len(v)!=1 for v in query.values()): raise LocalWebError('local_request_invalid',400)
                offset=int(query.get('offset',['0'])[0]); limit=int(query.get('limit',['20'])[0])
                if offset<0 or offset>10_000 or limit<1 or limit>30: raise LocalWebError('local_search_invalid',400)
                identity=query['vault_id'][0]
                result,resources=self.server.catalog.search_with_delivery(identity,query['q'][0],offset,limit)
                with self.server.catalog.guard_delivery(identity,resources):
                    self._send(200,result)
                return
            if target.path=='/api/resolve':
                query=parse_qs(target.query,keep_blank_values=True,max_num_fields=3)
                if set(query)!={'vault_id','source_path','target'} or any(len(v)!=1 or not v[0] for v in query.values()): raise LocalWebError('local_request_invalid',400)
                identity=query['vault_id'][0]
                result,scope=self.server.catalog.resolve_wikilink_with_delivery(identity,query['source_path'][0],query['target'][0])
                with self.server.catalog.guard_delivery(identity,scope['resources'],
                        expected_policy_source=scope['policy_source'],
                        expected_authorization_fingerprint=scope['authorization_fingerprint']):
                    self._send(200,result)
                return
            query=parse_qs(target.query,keep_blank_values=True,max_num_fields=2)
            if set(query)!={'vault_id','path'} or any(len(v)!=1 or not v[0] for v in query.values()): raise LocalWebError('local_request_invalid',400)
            identity=query['vault_id'][0]
            document=self.server.catalog._checked_read(identity,query['path'][0])
            resources={document['path']:document['source_sha256']}
            if document.get('index_path') and document.get('index_sha256'):
                resources[document['index_path']]=document['index_sha256']
            with self.server.catalog.guard_delivery(identity,resources):
                self._send(200,document,headers={'X-KB-Source-SHA256':document['source_sha256'],'X-KB-Binding-Generation':str(document['binding_generation'])})
            self.server.catalog.record_read_success(query['vault_id'][0])
        except LocalWebError as error: self._error(error)
        except (PolicyError,BindingError,MemberStoreError,OperationError,OSError,ValueError,TypeError,KeyError):
            self._error(LocalWebError('local_request_failed',503))
        except (BrokenPipeError,ConnectionResetError): return
    def send_error(self,code,message=None,explain=None):
        self._error(LocalWebError('local_method_not_allowed' if code==501 else 'local_request_invalid',405 if code==501 else code))


def create_server(*,instance,policy_root,catalog_config,authorization_path,access_token_file,read_authorized=False,host='127.0.0.1',port):
    if host!='127.0.0.1': raise LocalWebError('local_host_not_loopback',400)
    if read_authorized is not True: raise LocalWebError('local_read_unauthorized',403)
    if type(port) is not int or not 0<=port<=65535: raise LocalWebError('local_port_invalid',400)
    instance=BindingStore(Path(instance)).path; policy_root=BindingStore(Path(policy_root)).path
    config_path=BindingStore(Path(catalog_config)).path
    auth_path=BindingStore(Path(authorization_path)).path
    token_path=BindingStore(Path(access_token_file)).path
    if not instance.is_dir() or not policy_root.is_dir() or not config_path.is_file() or not auth_path.is_file(): raise LocalWebError('local_authority_unavailable')
    _read_access_token(token_path)
    catalog=NativeCatalog(instance,policy_root,config_path,auth_path)
    if catalog.coordinator.operation_issues(): raise LocalWebError('local_authority_incomplete')
    try: server=ThreadingHTTPServer((host,port),_Handler)
    except OSError: raise LocalWebError('local_listener_unavailable') from None
    server.daemon_threads=True; server.catalog=catalog; server.access_token_file=token_path
    server.build_id=build_fingerprint()
    return server

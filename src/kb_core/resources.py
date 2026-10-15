"""Resolve declared references, without executing, copying or granting access.

K07 supplies a trusted catalog; callers supply actual machine install records and
the single member/binding authority lookups. Native locators remain opaque for
the target domain. File metadata proves discovery only, never provenance or use.
"""
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re

from .contracts import CapabilityLock, MemberRecord, local_root, relative_path


class ResourceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Installation:
    """Caller-owned machine-local observation, not a second capability catalog."""
    capability_id: str
    source: str
    version: str
    root: Path


@dataclass(frozen=True)
class ResolvedReference:
    namespace: str
    locator: str
    root: Path
    entry: Path | None
    source: str
    version: str | None
    role: str | None
    entry_bytes: int | None


def _safe_components(parts: Sequence[str]) -> None:
    for part in parts:
        if (part.endswith((' ', '.')) or any(c in ':*?"<>|' or ord(c) < 32 for c in part)
                or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', part, re.I)):
            raise ResourceError('unsafe_path')


def _no_links(path: Path) -> None:
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ResourceError('path_unavailable') from exc
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ResourceError('unsafe_path')


def _directory(value: Path | None, offline_code: str) -> Path:
    if value is None:
        raise ResourceError(offline_code)
    path = Path(value)
    try:
        local_root(str(path))
    except (ValueError, TypeError) as exc:
        raise ResourceError('unsafe_path') from exc
    _safe_components(path.parts[1:])
    _no_links(path)
    if not path.is_dir():
        raise ResourceError(offline_code)
    return path


def _parse(reference: str) -> tuple[str, str]:
    if (not isinstance(reference, str) or reference != reference.strip()
            or reference.count('>') != 1 or any(ord(c) < 32 for c in reference)):
        raise ResourceError('reference_invalid')
    namespace, locator = reference.split('>', 1)
    if (not namespace or namespace != namespace.strip() or not locator
            or locator != locator.strip() or re.search(r'[\s\\/:<>]', namespace)):
        raise ResourceError('reference_invalid')
    # Native syntax is preserved, not interpreted as a filename. Reject obvious
    # filesystem escapes without imposing a common card/Workflow schema.
    if ('\\' in locator or locator.startswith('/') or re.match(r'^[A-Za-z]:', locator)
            or any(p in {'.', '..'} for p in locator.split('/'))):
        raise ResourceError('unsafe_path')
    return namespace, locator


def resolve_reference(
    reference: str, *, capabilities: CapabilityLock,
    installations: Mapping[str, Installation],
    member_lookup: Callable[[str], Sequence[MemberRecord]],
    location_lookup: Callable[[MemberRecord], Path | None],
) -> ResolvedReference:
    """Resolve one explicit reference; lookup adapters keep authority upstream.

    Member lookup must return the matching records from the authoritative store;
    returning more than one is an ambiguity, never a first-match fallback. The
    caller must separately authorize any subsequent read/execute/write and use
    its binding fencing. This discovery result has no authorization semantics.
    """
    namespace, locator = _parse(reference)
    if namespace.casefold() != 'shared':
        members = list(member_lookup(namespace))
        if not members:
            raise ResourceError('member_unknown')
        if len(members) != 1:
            raise ResourceError('member_ambiguous')
        member = members[0]
        if not member.enabled:
            raise ResourceError('member_disabled')
        root = _directory(location_lookup(member), 'member_offline')
        return ResolvedReference(member.vault_id, locator, root, None,
                                 f'member:{member.vault_id}@revision:{member.revision}',
                                 None, None, None)
    matches = [c for c in capabilities.capabilities if c.id.casefold() == locator.casefold()]
    if not matches:
        raise ResourceError('capability_unknown')
    if len(matches) != 1:
        raise ResourceError('capability_ambiguous')
    capability = matches[0]
    if (capability.version.casefold() in {'latest', 'current', 'head', 'main', 'master', 'tip'}
            or any(c.isspace() or c in '*^~<>|' for c in capability.version)):
        raise ResourceError('catalog_version_unpinned')
    install = installations.get(capability.id)
    if install is None:
        raise ResourceError('capability_not_installed')
    if (install.capability_id != capability.id or install.version != capability.version
            or install.source != capability.source):
        raise ResourceError('installation_mismatch')
    root = _directory(install.root, 'capability_offline')
    if capability.runtime_entry is None:
        raise ResourceError('entry_missing')
    # Supported runtime_entry is an exact relative ordinary-file location.
    # Command descriptions are unsupported; do not tokenize or invoke a shell.
    if re.search(r'[\s`$|<>;&]', capability.runtime_entry):
        raise ResourceError('entry_unsupported')
    try:
        relative_path(capability.runtime_entry)
    except ValueError as exc:
        raise ResourceError('unsafe_path') from exc
    _safe_components(capability.runtime_entry.split('/'))
    entry = root / capability.runtime_entry
    _no_links(entry)
    if not entry.exists():
        raise ResourceError('entry_missing')
    if not entry.is_file():
        raise ResourceError('entry_not_file')
    return ResolvedReference('shared', capability.id, root, entry, capability.source,
                             capability.version, capability.role, entry.stat().st_size)

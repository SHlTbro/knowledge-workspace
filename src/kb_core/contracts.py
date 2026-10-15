"""K01–K08 freeze candidate. Pure validation, never source authority discovery."""
from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, model_validator

CONTRACT_VERSION = 'kb-contracts-1.0'


def relative_path(value: str) -> str:
    if (not value or value != value.strip() or '\\' in value or ':' in value or value.startswith('/')
            or any(part in {'', '.', '..'} for part in value.split('/'))
            or any(ord(char) < 32 for char in value)):
        raise ValueError('unsafe relative path')
    return value


def local_root(value: str) -> str:
    windows, posix = PureWindowsPath(value), PurePosixPath(value)
    if (value != value.strip() or '..' in windows.parts or '..' in posix.parts
            or any(ord(char) < 32 for char in value) or value.startswith(('\\\\', '//'))
            or not (windows.is_absolute() or posix.is_absolute())
            or value in {str(windows.anchor), str(posix.anchor)}
            or value.replace('\\', '/').rstrip('/') in {'', windows.drive}):
        raise ValueError('machine root must be an explicit local absolute directory')
    return value


def timestamp(value: str) -> str:
    if 'T' not in value:
        raise ValueError('timestamp requires explicit timezone')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp requires explicit timezone')
    return value


def exact_profile_version(value: str) -> str:
    if (value.casefold() in {'latest', 'current', 'head', 'main', 'master', 'tip'}
            or any(char.isspace() or char in '*^~<>|' for char in value)):
        raise ValueError('profile reference requires an exact version label')
    return value


Text = Annotated[str, Field(min_length=1, max_length=1000, pattern=r'^\S(?:[^\r\n]*\S)?$')]
Identity = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')]
Alias = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[^\s\\/:<>]+$')]
Revision = Annotated[int, Field(ge=1)]
RelativePath = Annotated[str, Field(min_length=1, max_length=1000), AfterValidator(relative_path)]
Timestamp = Annotated[str, Field(min_length=20, max_length=40), AfterValidator(timestamp)]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    @model_validator(mode='after')
    def unique_record_identities(self):
        for field, key in [('members', 'vault_id'), ('vaults', 'vault_id'),
                           ('capabilities', 'id'), ('files', 'path'), ('changes', 'path'), ('profiles', 'id')]:
            if hasattr(self, field):
                identities = [getattr(item, key).casefold() for item in getattr(self, field)]
                if len(identities) != len(set(identities)):
                    raise ValueError('duplicate identity')
        return self


class ProfileReference(Contract):
    id: Identity
    version: Annotated[Text, AfterValidator(exact_profile_version)]


class MemberRecord(Contract):
    schema_version: Literal['kb-contracts-1.0']
    revision: Revision
    vault_id: Identity
    aliases: list[Alias]
    name: Text
    purpose_ref: RelativePath
    agents_ref: RelativePath
    navigation_refs: list[RelativePath]
    core_version: Text
    profiles: list[ProfileReference]
    location_ref: Identity
    display_ref: Identity | None
    enabled: bool

    @model_validator(mode='after')
    def no_machine_paths(self):
        for value in [self.name, self.core_version]:
            if PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute():
                raise ValueError('member record cannot hold machine paths')
        if len(self.aliases) != len({alias.casefold() for alias in self.aliases}):
            raise ValueError('duplicate aliases')
        return self


class MachineBinding(Contract):
    schema_version: Literal['kb-contracts-1.0']
    revision: Revision
    binding_id: Identity
    vault_id: Identity
    root: Annotated[str, AfterValidator(local_root)] | None
    generation: Revision
    active: bool
    observed_at: Timestamp

    @model_validator(mode='after')
    def active_has_root(self):
        if self.active and self.root is None:
            raise ValueError('active binding needs explicit machine root')
        return self


class LayerResult(Contract):
    status: Literal['not_run', 'pending', 'succeeded', 'failed', 'unsupported']
    evidence_refs: list[RelativePath]

    @model_validator(mode='after')
    def success_has_evidence(self):
        if self.status == 'succeeded' and not self.evidence_refs:
            raise ValueError('success needs evidence')
        return self


class Change(Contract):
    path: RelativePath
    sha256: Digest | None
    deleted: bool

    @model_validator(mode='after')
    def exact_change_kind(self):
        if self.deleted != (self.sha256 is None):
            raise ValueError('delete requires null hash; write requires hash')
        return self


class OperationReceipt(Contract):
    operation_id: Identity
    operation_type: Literal['register', 'bind', 'rebind', 'unbind', 'enable', 'disable', 'write', 'delete',
                            'refresh', 'migrate', 'export', 'restore', 'activate', 'disconnect']
    vault_id: Identity | None
    domain_result: LayerResult
    system_result: LayerResult
    display_result: LayerResult
    changes: list[Change]
    evidence: list[RelativePath]
    observed_at: Timestamp


class Verification(Contract):
    declared: bool
    installed: bool
    configured: bool
    runtime_verified: bool
    observed_at: Timestamp | None
    evidence_refs: list[RelativePath]

    @model_validator(mode='after')
    def verified_is_observed(self):
        if self.runtime_verified and not (self.declared and self.installed and self.configured
                                          and self.observed_at and self.evidence_refs):
            raise ValueError('runtime verification needs all prerequisite states and observed evidence')
        return self


class Capability(Contract):
    id: Identity
    role: Literal['read', 'display', 'write', 'create', 'bind', 'migrate', 'model', 'restore', 'verify']
    source: Text
    version: Text
    license: Text
    install_entry: RelativePath | None
    runtime_entry: RelativePath | None
    verification: Verification

    @model_validator(mode='after')
    def verified_has_runtime_entry(self):
        if self.verification.runtime_verified and self.runtime_entry is None:
            raise ValueError('runtime verification requires a stable runtime entry')
        return self


class MemberRevision(Contract):
    vault_id: Identity
    revision: Revision


class Maintenance(Contract):
    status: Literal['unknown', 'pending', 'ready', 'failed']
    observed_at: Timestamp | None
    evidence_refs: list[RelativePath]


class DisplayState(Contract):
    status: Literal['unknown', 'pending', 'ready', 'failed']
    projection_revision: Revision | None
    observed_at: Timestamp | None

    @model_validator(mode='after')
    def ready_is_observed(self):
        if self.status == 'ready' and (self.projection_revision is None or self.observed_at is None):
            raise ValueError('ready display needs observed revision')
        return self


class InstanceState(Contract):
    generated_at: Timestamp
    control_revision: Revision
    members: list[MemberRevision]
    capabilities: list[Capability]
    maintenance: Maintenance
    display: DisplayState


class DisplayCount(Contract):
    value: Annotated[int, Field(ge=0)] | None
    count_unit: Literal['asset', 'card', 'file', 'directory', 'byte']
    count_scope: Text
    observed_at: Timestamp | None

    @model_validator(mode='after')
    def known_count_is_observed(self):
        if self.value is not None and self.observed_at is None:
            raise ValueError('known count needs observation time')
        return self


class DisplayVault(Contract):
    vault_id: Identity
    member_revision: Revision
    policy_revision: Revision
    name: Text
    enabled: bool
    resources: list[RelativePath]
    counts: list[DisplayCount]
    state: Literal['current', 'stale', 'offline', 'restricted']


class DisplayProjection(Contract):
    display_schema_version: Literal['kb-display-1.1']
    freshness: Literal['current', 'stale']
    projection_revision: Revision
    source_member_revision: Revision
    generated_at: Timestamp
    vaults: list[DisplayVault]


class DisplayPolicy(Contract):
    policy_revision: Revision
    vault_id: Identity
    allow: list[RelativePath]
    deny: list[RelativePath]
    revoked: list[RelativePath]
    channel: Literal['web', 'agent']

    def permits(self, path: str, *, channel: str) -> bool:
        """Exact relative resources only. Revocation survives stale projection failure."""
        try:
            normalized = relative_path(path).casefold()
        except (ValueError, TypeError, AttributeError):
            return False
        return (channel == self.channel and normalized in {p.casefold() for p in self.allow}
                and normalized not in {p.casefold() for p in self.deny + self.revoked})


class CapabilityLock(Contract):
    release: Text
    capabilities: list[Capability]


class RecoveryFile(Contract):
    path: RelativePath
    sha256: Digest
    bytes: Annotated[int, Field(ge=0)]


class RecoveryManifest(Contract):
    package_id: Identity
    kind: Literal['portable', 'machine-local']
    files: list[RecoveryFile]
    excluded: list[RelativePath]
    external_dependencies: list[Identity]
    restore_checks: Annotated[list[Text], Field(min_length=1)]

    @model_validator(mode='after')
    def portable_excludes_known_machine_state(self):
        secrets = {'session.json', '.env', 'credentials.json', 'tokens.json', 'cookies.txt'}
        if any(PurePosixPath(item.path).name.casefold() in secrets for item in self.files):
            raise ValueError('recovery cannot include credentials or old sessions')
        forbidden = {'active-workspace.json', 'authority.json', 'session.json', 'machine-bindings.json'}
        if self.kind == 'portable' and any(PurePosixPath(item.path).name.casefold() in forbidden for item in self.files):
            raise ValueError('portable payload cannot inherit machine authority')
        return self


MODELS = {model.__name__: model for model in (MemberRecord, MachineBinding, OperationReceipt,
          InstanceState, DisplayProjection, DisplayPolicy, CapabilityLock, RecoveryManifest)}


class ContractError(ValueError):
    """Stable public code/message. Never includes supplied paths or private input."""
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def validate_contract(name: str, payload: dict) -> Contract:
    if name not in MODELS:
        raise ContractError('contract_unknown', 'Unknown contract type.')
    try:
        return MODELS[name].model_validate(payload)
    except (ValidationError, ValueError, TypeError):
        raise ContractError('contract_invalid', 'Contract payload is invalid.') from None

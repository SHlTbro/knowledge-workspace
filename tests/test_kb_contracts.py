"""Public boundary tests: catch guessed defaults, coercion and unsafe authority."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
NOW = '2026-10-07T00:00:00Z'
RESULT = {'status': 'not_run', 'evidence_refs': []}
CAPABILITY = {'id': 'reader', 'role': 'read', 'source': 'repository', 'version': '1',
              'license': 'MIT', 'install_entry': 'tools/install', 'runtime_entry': 'tools/read',
              'verification': {'declared': True, 'installed': False, 'configured': False,
                               'runtime_verified': False, 'observed_at': None, 'evidence_refs': []}}
SAMPLES = {
    'MemberRecord': {'schema_version': 'kb-contracts-1.0', 'revision': 1, 'vault_id': 'vault-5',
                     'aliases': ['inspiration'], 'name': 'Inspiration', 'purpose_ref': 'purpose.md',
                     'agents_ref': 'AGENTS.md', 'navigation_refs': ['wiki/index.md'],
                     'core_version': '1.0', 'profiles': [{'id': 'publication', 'version': '1.0.0'}],
                     'location_ref': 'binding-5', 'display_ref': None, 'enabled': True},
    'MachineBinding': {'schema_version': 'kb-contracts-1.0', 'revision': 1, 'binding_id': 'binding-5',
                       'vault_id': 'vault-5', 'root': 'E:/vaults/inspiration', 'generation': 1,
                       'active': True, 'observed_at': NOW},
    'OperationReceipt': {'operation_id': 'operation-1', 'operation_type': 'write', 'vault_id': 'vault-5',
                         'domain_result': RESULT, 'system_result': RESULT, 'display_result': RESULT,
                         'changes': [{'path': 'wiki/index.md', 'sha256': 'a' * 64, 'deleted': False}],
                         'evidence': [], 'observed_at': NOW},
    'InstanceState': {'generated_at': NOW, 'control_revision': 1,
                      'members': [{'vault_id': 'vault-5', 'revision': 1}], 'capabilities': [CAPABILITY],
                      'maintenance': {'status': 'unknown', 'observed_at': None, 'evidence_refs': []},
                      'display': {'status': 'unknown', 'projection_revision': None, 'observed_at': None}},
    'DisplayProjection': {'display_schema_version': 'kb-display-1.1', 'freshness': 'current',
                          'projection_revision': 1, 'source_member_revision': 1, 'generated_at': NOW,
                          'vaults': [{'vault_id': 'vault-5', 'member_revision': 1, 'policy_revision': 1,
                                      'name': 'Inspiration', 'enabled': True, 'state': 'current',
                                      'resources': ['wiki/index.md'],
                                      'counts': [{'value': None, 'count_unit': 'asset',
                                                  'count_scope': 'accepted-visible-assets', 'observed_at': None}]}]},
    'DisplayPolicy': {'policy_revision': 1, 'vault_id': 'vault-5', 'allow': ['wiki/index.md'],
                      'deny': [], 'revoked': [], 'channel': 'web'},
    'CapabilityLock': {'release': '1.0', 'capabilities': [CAPABILITY]},
    'RecoveryManifest': {'package_id': 'pack-1', 'kind': 'portable',
                         'files': [{'path': 'vaults/vault-5/AGENTS.md', 'sha256': 'a' * 64, 'bytes': 0}],
                         'excluded': ['session.json'], 'external_dependencies': ['linked-vault-5'],
                         'restore_checks': ['original-byte-hashes', 'member-identity', 'accepted-policy']},
}


def contracts():
    assert importlib.util.find_spec('kb_core') is not None, 'T05 public contract module is missing'
    from kb_core import contracts as module
    return module


@pytest.mark.parametrize('name', SAMPLES)
def test_eight_contracts_round_trip_json_without_guessing_fields(name):
    model = getattr(contracts(), name)
    record = model.model_validate_json(json.dumps(SAMPLES[name]))
    assert json.loads(record.model_dump_json()) == SAMPLES[name]


@pytest.mark.parametrize('name', SAMPLES)
def test_every_field_is_required_and_unknown_fields_are_rejected(name):
    module = contracts()
    model = getattr(module, name)
    for field in SAMPLES[name]:
        payload = dict(SAMPLES[name])
        payload.pop(field)
        with pytest.raises(module.ContractError) as error:
            module.validate_contract(name, payload)
        assert error.value.code == 'contract_invalid'
    with pytest.raises(module.ContractError):
        module.validate_contract(name, dict(SAMPLES[name], unexpected=True))


@pytest.mark.parametrize('name,field,value', [
    ('MemberRecord', 'purpose_ref', 'C:/private/purpose.md'),
    ('MemberRecord', 'location_ref', '/private/root'),
    ('MemberRecord', 'navigation_refs', ['../private.md']),
    ('MemberRecord', 'enabled', 'false'),
    ('MemberRecord', 'revision', 0),
    ('MemberRecord', 'revision', True),
    ('MemberRecord', 'schema_version', 1),
    ('MachineBinding', 'generation', 0),
    ('MachineBinding', 'root', 'relative/vault'),
    ('MachineBinding', 'root', 'E:/'),
    ('MachineBinding', 'root', 'E:/vault/../private'),
    ('DisplayPolicy', 'channel', 'write'),
    ('RecoveryManifest', 'kind', 'implicit-restore'),
    ('RecoveryManifest', 'files', [{'path': '../private', 'sha256': 'a' * 64, 'bytes': 0}]),
    ('RecoveryManifest', 'files', [{'path': 'file', 'sha256': 'bad', 'bytes': -1}]),
])
def test_unsafe_values_and_coercion_fail_closed(name, field, value):
    module = contracts()
    with pytest.raises(module.ContractError) as error:
        module.validate_contract(name, dict(SAMPLES[name], **{field: value}))
    assert error.value.code == 'contract_invalid'
    assert 'private' not in error.value.message


def test_count_unknown_is_preserved_and_zero_requires_observation():
    module = contracts()
    count = module.DisplayCount.model_validate(SAMPLES['DisplayProjection']['vaults'][0]['counts'][0])
    assert count.value is None
    with pytest.raises(module.ContractError):
        module.validate_contract('DisplayProjection', dict(SAMPLES['DisplayProjection'], vaults=[
            dict(SAMPLES['DisplayProjection']['vaults'][0], counts=[
                {'value': 0, 'count_unit': 'asset', 'count_scope': 'visible', 'observed_at': None}])]))


def test_receipt_does_not_promote_system_success_to_domain_or_display_success():
    module = contracts()
    receipt = module.validate_contract('OperationReceipt', dict(SAMPLES['OperationReceipt'],
        system_result={'status': 'succeeded', 'evidence_refs': ['receipt-1']}))
    assert receipt.domain_result.status == 'not_run'
    assert receipt.display_result.status == 'not_run'


def test_success_and_runtime_verification_require_evidence():
    module = contracts()
    with pytest.raises(module.ContractError):
        module.validate_contract('OperationReceipt', dict(SAMPLES['OperationReceipt'],
            domain_result={'status': 'succeeded', 'evidence_refs': []}))
    invalid = dict(CAPABILITY, verification=dict(CAPABILITY['verification'], runtime_verified=True))
    with pytest.raises(module.ContractError):
        module.validate_contract('CapabilityLock', {'release': '1', 'capabilities': [invalid]})


def test_revocation_and_deny_override_allow_and_missing_allow_is_closed():
    module = contracts()
    policy = module.validate_contract('DisplayPolicy', dict(SAMPLES['DisplayPolicy'],
        allow=['a.md', 'b.md', 'c.md'], deny=['b.md'], revoked=['c.md']))
    assert policy.permits('a.md', channel='web') is True
    assert policy.permits('b.md', channel='web') is False
    assert policy.permits('c.md', channel='web') is False
    assert policy.permits('unknown.md', channel='web') is False
    assert policy.permits('a.md', channel='agent') is False


def test_duplicate_identity_and_case_alias_file_entries_rejected():
    module = contracts()
    with pytest.raises(module.ContractError):
        module.validate_contract('CapabilityLock', {'release': '1', 'capabilities': [CAPABILITY, CAPABILITY]})
    with pytest.raises(module.ContractError):
        module.validate_contract('RecoveryManifest', dict(SAMPLES['RecoveryManifest'], files=[
            {'path': 'File.md', 'sha256': 'a' * 64, 'bytes': 0},
            {'path': 'file.md', 'sha256': 'a' * 64, 'bytes': 0}]))


def test_unknown_contract_has_stable_sanitized_error():
    module = contracts()
    with pytest.raises(module.ContractError) as error:
        module.validate_contract('private-secret', {})
    assert error.value.code == 'contract_unknown'
    assert 'private-secret' not in error.value.message


def test_direct_models_reject_duplicates_and_unobserved_ready_display():
    from pydantic import ValidationError
    module = contracts()
    with pytest.raises(ValidationError):
        module.CapabilityLock.model_validate({'release': '1', 'capabilities': [CAPABILITY, CAPABILITY]})
    with pytest.raises(module.ContractError):
        module.validate_contract('InstanceState', dict(SAMPLES['InstanceState'],
            display={'status': 'ready', 'projection_revision': None, 'observed_at': None}))


def test_portable_manifest_cannot_carry_machine_authority_or_session():
    module = contracts()
    for path in ['.local/active-workspace.json', '.workspace-state/session.json',
                 '.workspace-state/authority.json', 'machine-bindings.json']:
        with pytest.raises(module.ContractError):
            module.validate_contract('RecoveryManifest', dict(SAMPLES['RecoveryManifest'], files=[
                {'path': path, 'sha256': 'a' * 64, 'bytes': 5}]))


@pytest.mark.parametrize('field', ['name', 'core_version'])
def test_member_text_fields_cannot_smuggle_absolute_machine_paths(field):
    module = contracts()
    with pytest.raises(module.ContractError):
        module.validate_contract('MemberRecord', dict(SAMPLES['MemberRecord'], **{field: 'E:/private/root'}))


def test_change_delete_hash_exclusivity_timestamp_and_nested_unknown_fields():
    module = contracts()
    for change in [{'path': 'a.md', 'sha256': None, 'deleted': False},
                   {'path': 'a.md', 'sha256': 'a' * 64, 'deleted': True},
                   {'path': 'a.md', 'sha256': 'a' * 64, 'deleted': False, 'extra': True}]:
        with pytest.raises(module.ContractError):
            module.validate_contract('OperationReceipt', dict(SAMPLES['OperationReceipt'], changes=[change]))
    with pytest.raises(module.ContractError):
        module.validate_contract('MachineBinding', dict(SAMPLES['MachineBinding'], observed_at='2026-10-07T00:00:00'))
    with pytest.raises(module.ContractError):
        module.validate_contract('DisplayProjection', dict(SAMPLES['DisplayProjection'], vaults=[
            dict(SAMPLES['DisplayProjection']['vaults'][0], counts=[
                {'value': False, 'count_unit': 'asset', 'count_scope': 'visible', 'observed_at': NOW}])]))


def test_historical_circle_alias_and_rebind_are_explicitly_supported():
    module = contracts()
    member = module.validate_contract('MemberRecord', dict(SAMPLES['MemberRecord'], aliases=['vault⑤', '项目灵感']))
    assert member.aliases == ['vault⑤', '项目灵感']
    receipt = module.validate_contract('OperationReceipt', dict(SAMPLES['OperationReceipt'], operation_type='rebind'))
    assert receipt.operation_type == 'rebind'


def test_unbound_root_is_explicit_null_and_active_null_is_invalid():
    module = contracts()
    binding = module.validate_contract('MachineBinding', dict(SAMPLES['MachineBinding'], root=None, active=False))
    assert binding.root is None
    with pytest.raises(module.ContractError):
        module.validate_contract('MachineBinding', dict(SAMPLES['MachineBinding'], root=None, active=True))


def test_session_and_credentials_are_never_recovery_payload():
    module = contracts()
    for kind in ['portable', 'machine-local']:
        for path in ['state/session.json', '.env', 'credentials.json', 'tokens.json', 'cookies.txt']:
            with pytest.raises(module.ContractError):
                module.validate_contract('RecoveryManifest', dict(SAMPLES['RecoveryManifest'], kind=kind,
                    files=[{'path': path, 'sha256': 'a' * 64, 'bytes': 5}]))


def test_review_revision_display_ref_null_is_explicit_and_still_required():
    module = contracts()
    member = module.validate_contract('MemberRecord', dict(SAMPLES['MemberRecord'], display_ref=None))
    assert member.display_ref is None
    missing = dict(SAMPLES['MemberRecord'])
    missing.pop('display_ref')
    with pytest.raises(module.ContractError):
        module.validate_contract('MemberRecord', missing)


def test_review_revision_profiles_pin_exact_versions_and_reject_ambiguous_entries():
    module = contracts()
    profile = {'id': 'publication', 'version': '1.0.0'}
    member = module.validate_contract('MemberRecord', dict(SAMPLES['MemberRecord'], profiles=[profile]))
    assert member.model_dump()['profiles'] == [profile]
    for profiles in [['publication'], [{'id': 'publication'}],
                     [{'id': 'publication', 'version': 'latest'}],
                     [{'id': 'publication', 'version': '^1.0'}],
                     [{'id': 'publication', 'version': '1.*'}],
                     [dict(profile, unexpected=True)],
                     [profile, {'id': 'PUBLICATION', 'version': '2.0.0'}]]:
        with pytest.raises(module.ContractError):
            module.validate_contract('MemberRecord', dict(SAMPLES['MemberRecord'], profiles=profiles))


def test_review_revision_verified_capability_requires_stable_runtime_entry():
    module = contracts()
    verified = {'declared': True, 'installed': True, 'configured': True,
                'runtime_verified': True, 'observed_at': NOW, 'evidence_refs': ['verification.md']}
    with pytest.raises(module.ContractError):
        module.validate_contract('CapabilityLock', {'release': '1.0', 'capabilities': [
            dict(CAPABILITY, runtime_entry=None, verification=verified)]})
    record = module.validate_contract('CapabilityLock', {'release': '1.0', 'capabilities': [
        dict(CAPABILITY, runtime_entry='shared/reader/SKILL.md', verification=verified)]})
    assert record.capabilities[0].runtime_entry == 'shared/reader/SKILL.md'

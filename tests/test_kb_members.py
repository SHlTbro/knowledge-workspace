"""Real temporary-file member behavior; no Web, Vault or mock dependency."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def members():
    assert importlib.util.find_spec('kb_core.members') is not None, 'T07 member store is missing'
    from kb_core import members as module
    return module


def record(vault_id='inspiration', aliases=None, revision=1, **changes):
    value = {'schema_version': 'kb-contracts-1.0', 'revision': revision, 'vault_id': vault_id,
             'aliases': ['vault⑤', 'vault5', '项目灵感'] if aliases is None else aliases,
             'name': '项目灵感', 'purpose_ref': 'purpose.md', 'agents_ref': 'AGENTS.md',
             'navigation_refs': ['wiki/index.md'], 'core_version': '1.0',
             'profiles': [{'id': 'inspiration-publication', 'version': '1.0'}],
             'location_ref': 'inspiration-origin', 'display_ref': None, 'enabled': True}
    return dict(value, **changes)


def prepared(tmp_path):
    module = members()
    store = module.MemberStore(tmp_path / 'members.json')
    store.create()
    store.register(record(), expected_collection_revision=1)
    return module, store


def test_public_guard_holds_member_authority_during_dependent_io(tmp_path):
    module, store = prepared(tmp_path)
    expected = store.resolve('vault⑤').model_dump()
    other = module.MemberStore(store.path)
    disabled = record(revision=2, enabled=False)
    before = store.path.read_bytes()
    with store.guard(expected) as current:
        assert current.model_dump() == expected
        with pytest.raises(module.MemberStoreError) as error:
            other.update('inspiration', disabled, expected_collection_revision=2,
                         expected_record_revision=1)
        assert error.value.code == 'store_busy'
        assert store.path.read_bytes() == before
    other.update('inspiration', disabled, expected_collection_revision=2, expected_record_revision=1)
    assert not store.resolve('inspiration').enabled


def test_public_guard_refuses_changed_member_and_releases_lock(tmp_path):
    module, store = prepared(tmp_path)
    expected = store.resolve('inspiration').model_dump()
    store.update('inspiration', record(revision=2, enabled=False), expected_collection_revision=2,
                 expected_record_revision=1)
    with pytest.raises(module.MemberStoreError) as error:
        with store.guard(expected):
            pytest.fail('Stale member entered dependent I/O.')
    assert error.value.code == 'revision_conflict'
    store.update('inspiration', record(revision=3), expected_collection_revision=3,
                 expected_record_revision=2)


def test_constructor_does_not_initialize_or_fallback_when_missing(tmp_path):
    module = members()
    store = module.MemberStore(tmp_path / 'members.json')
    assert not store.path.exists()
    with pytest.raises(module.MemberStoreError) as error:
        store.snapshot()
    assert error.value.code == 'store_missing'
    assert store.create() == {'collection_revision': 1, 'records': []}


def test_register_offline_member_and_resolve_circle_ascii_casefold_after_restart(tmp_path):
    module, store = prepared(tmp_path)
    restarted = module.MemberStore(store.path)
    for identity in ['inspiration', 'INSPIRATION', 'vault⑤', 'VAULT5', '项目灵感']:
        member = restarted.resolve(identity)
        assert member.vault_id == 'inspiration'
        assert member.display_ref is None
        assert member.location_ref == 'inspiration-origin'
        assert member.profiles[0].version == '1.0'
    assert restarted.snapshot()['collection_revision'] == 2
    assert len(restarted.snapshot()['records']) == 1


@pytest.mark.parametrize('payload', [record('shared', aliases=[]), record(aliases=['ShArEd'])])
def test_shared_resource_namespace_cannot_be_registered_as_vault_identity(tmp_path, payload):
    module = members()
    store = module.MemberStore(tmp_path / 'members.json')
    store.create()
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as error:
        store.register(payload, expected_collection_revision=1)
    assert error.value.code == 'identity_conflict'
    assert store.path.read_bytes() == before


def test_shared_resource_namespace_cannot_be_added_by_update(tmp_path):
    module, store = prepared(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as error:
        store.update('inspiration', record(aliases=['SHARED'], revision=2),
                     expected_collection_revision=2, expected_record_revision=1)
    assert error.value.code == 'identity_conflict'
    assert store.path.read_bytes() == before


def test_loading_member_store_with_shared_alias_fails_closed(tmp_path):
    module = members()
    path = tmp_path / 'members.json'
    path.write_text(json.dumps({'collection_revision': 1,
                                'records': [record(aliases=['shared'])]}), encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(module.MemberStoreError) as error:
        module.MemberStore(path).snapshot()
    assert error.value.code == 'store_invalid'
    assert path.read_bytes() == before


def test_sixth_and_future_members_are_not_filtered_by_fixed_scope_enumeration(tmp_path):
    module = members()
    store = module.MemberStore(tmp_path / 'members.json')
    store.create()
    for index in range(1, 8):
        store.register(record(f'vault-{index}', aliases=[f'legacy-{index}']),
                       expected_collection_revision=index)
    assert len(store.snapshot()['records']) == 7
    assert store.resolve('LEGACY-7').vault_id == 'vault-7'


@pytest.mark.parametrize('payload,code', [
    (record(), 'member_exists'),
    (record('INSPIRATION', aliases=[]), 'identity_conflict'),
    (record('other', aliases=['VAULT5']), 'identity_conflict'),
    (record('other', aliases=['INSPIRATION']), 'identity_conflict'),
    (record('vault5', aliases=[]), 'identity_conflict'),
    (record('other', aliases=['other']), 'identity_conflict'),
    (record('other', aliases=['a', 'A']), 'member_invalid'),
])
def test_duplicate_ids_aliases_and_cross_namespace_collisions_do_not_overwrite(tmp_path, payload, code):
    module, store = prepared(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as error:
        store.register(payload, expected_collection_revision=2)
    assert error.value.code == code
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('changes', [
    {'unexpected': True}, {'root': 'E:/private'}, {'revision': True}, {'revision': 0},
    {'revision': 2}, {'enabled': 'false'}, {'purpose_ref': '../private'},
])
def test_invalid_registration_never_mutates_file(tmp_path, changes):
    module, store = prepared(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError):
        store.register(record('new-vault', aliases=[], **changes), expected_collection_revision=2)
    assert store.path.read_bytes() == before


def test_update_requires_both_collection_and_member_cas_and_exact_next_revision(tmp_path):
    module, store = prepared(tmp_path)
    updated = record(revision=2, name='更新名称', enabled=False)
    snapshot = store.update('inspiration', updated, expected_collection_revision=2, expected_record_revision=1)
    assert snapshot['collection_revision'] == 3
    assert store.resolve('VAULT5').revision == 2
    assert store.resolve('vault⑤').enabled is False
    before = store.path.read_bytes()
    for collection, member, replacement in [(2, 1, updated), (3, 1, record(revision=3)),
                                             (3, 2, record(revision=4))]:
        with pytest.raises(module.MemberStoreError) as error:
            store.update('inspiration', replacement, expected_collection_revision=collection,
                         expected_record_revision=member)
        assert error.value.code == 'revision_conflict'
        assert store.path.read_bytes() == before


def test_update_cannot_rename_stable_id_or_take_another_alias(tmp_path):
    module, store = prepared(tmp_path)
    store.register(record('other', aliases=['reserved']), expected_collection_revision=2)
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as mismatch:
        store.update('inspiration', record('renamed', revision=2),
                     expected_collection_revision=3, expected_record_revision=1)
    assert mismatch.value.code == 'member_id_mismatch'
    with pytest.raises(module.MemberStoreError) as conflict:
        store.update('inspiration', record(aliases=['RESERVED'], revision=2),
                     expected_collection_revision=3, expected_record_revision=1)
    assert conflict.value.code == 'identity_conflict'
    assert store.path.read_bytes() == before


@pytest.mark.parametrize('raw', [b'{', b'{}', b'null', b'\xff',
    b'{"collection_revision":true,"records":[]}',
    b'{"collection_revision":0,"records":[]}',
    b'{"collection_revision":1,"records":[],"unknown":0}',
    b'{"collection_revision":1,"collection_revision":2,"records":[]}',
    json.dumps({'collection_revision': 1, 'records': [record(), record()]}).encode('utf-8'),
    json.dumps({'collection_revision': 1, 'records': [dict(record(), unexpected=True)]}).encode('utf-8')])
def test_corrupt_store_is_not_replaced_or_treated_as_empty(tmp_path, raw):
    module = members()
    path = tmp_path / 'members.json'
    path.write_bytes(raw)
    store = module.MemberStore(path)
    with pytest.raises(module.MemberStoreError) as error:
        store.snapshot()
    assert error.value.code == 'store_invalid'
    with pytest.raises(module.MemberStoreError):
        store.register(record(), expected_collection_revision=1)
    with pytest.raises(module.MemberStoreError) as exists:
        store.create()
    assert exists.value.code == 'store_exists'
    assert path.read_bytes() == raw


def test_existing_creation_and_busy_lock_cannot_overwrite(tmp_path):
    module, store = prepared(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as exists:
        store.create()
    assert exists.value.code == 'store_exists'
    lock = store.path.with_suffix(store.path.suffix + '.lock')
    lock.write_text('an interrupted writer owns this lock', encoding='utf-8')
    with pytest.raises(module.MemberStoreError) as busy:
        store.register(record('other', aliases=[]), expected_collection_revision=2)
    assert busy.value.code == 'store_busy'
    assert lock.read_text(encoding='utf-8') == 'an interrupted writer owns this lock'
    assert store.path.read_bytes() == before


def test_unknown_lookup_and_invalid_cas_have_stable_sanitized_errors(tmp_path):
    module, store = prepared(tmp_path)
    with pytest.raises(module.MemberStoreError) as error:
        store.resolve('private-secret')
    assert error.value.code == 'member_not_found'
    assert 'private-secret' not in error.value.message
    for revision in [True, 0, '2', None]:
        with pytest.raises(module.MemberStoreError) as conflict:
            store.register(record('other', aliases=[]), expected_collection_revision=revision)
        assert conflict.value.code == 'revision_conflict'


def test_successful_writes_leave_parseable_utf8_and_no_transaction_debris(tmp_path):
    _, store = prepared(tmp_path)
    raw = store.path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')
    assert b'\r\n' not in raw
    assert json.loads(raw)['records'][0]['name'] == '项目灵感'
    assert sorted(path.name for path in tmp_path.iterdir()) == ['members.json']


def test_modified_model_instance_cannot_bypass_frozen_payload_validation(tmp_path):
    from kb_core.contracts import validate_contract
    module, store = prepared(tmp_path)
    model = validate_contract('MemberRecord', record('other', aliases=[]))
    model.name = 'E:/private/root'
    before = store.path.read_bytes()
    with pytest.raises(module.MemberStoreError) as error:
        store.register(model, expected_collection_revision=2)
    assert error.value.code == 'member_invalid'
    assert store.path.read_bytes() == before


def test_two_real_concurrent_writers_cannot_both_commit_the_same_collection_revision(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    module, store = prepared(tmp_path)
    barrier = Barrier(2)

    def attempt(identifier):
        independent = module.MemberStore(store.path)
        barrier.wait(timeout=5)
        try:
            independent.register(record(identifier, aliases=[]), expected_collection_revision=2)
            return 'committed'
        except module.MemberStoreError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['other-a', 'other-b']))
    assert results.count('committed') == 1
    assert next(result for result in results if result != 'committed') in {'store_busy', 'revision_conflict'}
    snapshot = store.snapshot()
    assert snapshot['collection_revision'] == 3
    assert len(snapshot['records']) == 2
    assert store.resolve('vault⑤').vault_id == 'inspiration'

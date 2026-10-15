"""Real machine-local fixtures; no Registry, HTTP or production roots."""
import importlib.util
import json
import os
import multiprocessing
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

def module():
    assert importlib.util.find_spec('kb_core.bindings') is not None, 'T08 bindings implementation is missing'
    from kb_core import bindings
    return bindings

def create(store, root, *, vault='vault-a', binding='binding-a'):
    return store.bind(binding, vault, str(root), expected_revision=0, expected_generation=0)


def test_public_snapshot_checks_whole_authority_without_creating_files(tmp_path):
    m = module()
    path = tmp_path / 'bindings.json'
    store = m.BindingStore(path)
    assert store.snapshot() == []
    assert list(tmp_path.iterdir()) == []
    path.write_bytes(b'not-json')
    with pytest.raises(m.BindingError) as error:
        store.snapshot()
    assert error.value.code == 'binding_store_invalid'
    assert path.read_bytes() == b'not-json'


def test_public_snapshot_returns_frozen_records_and_preserves_inactive_reservations(tmp_path):
    m = module()
    path = tmp_path / 'bindings.json'
    root = tmp_path / 'vault'; root.mkdir()
    store = m.BindingStore(path)
    active = create(store, root)
    assert store.snapshot() == [active.model_dump()]
    inactive = store.unbind('binding-a', expected_revision=1, expected_generation=1)
    before = path.read_bytes()
    rows = store.snapshot()
    assert rows == [inactive.model_dump()]
    rows[0]['active'] = True
    assert store.snapshot() == [inactive.model_dump()]
    assert path.read_bytes() == before

def test_binding_persists_as_frozen_k02_and_same_root_does_not_advance(tmp_path):
    m = module()
    root = tmp_path / '知识库'; root.mkdir()
    path = tmp_path / 'machine-bindings.json'
    store = m.BindingStore(path)
    first = create(store, root)
    assert (first.revision, first.generation, first.active) == (1, 1, True)
    again = store.bind('binding-a', 'vault-a', str(root).upper(), expected_revision=1, expected_generation=1)
    assert again.model_dump() == first.model_dump()
    from kb_core.contracts import validate_contract
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_contract('MachineBinding', data['bindings'][0])
    assert m.BindingStore(path).resolve('binding-a')['status'] == 'online'

def test_stale_cas_never_overwrites_and_generation_is_required(tmp_path):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    a = tmp_path / 'a'; a.mkdir(); b = tmp_path / 'b'; b.mkdir()
    create(store, a)
    before = store.path.read_bytes()
    for revision, generation in [(0, 1), (1, 0), (True, 1)]:
        with pytest.raises(m.BindingError):
            store.bind('binding-a', 'vault-a', str(b), expected_revision=revision, expected_generation=generation)
        assert store.path.read_bytes() == before

def test_rebind_and_unbind_fence_old_claim_and_reserve_old_root(tmp_path):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    a = tmp_path / 'a'; a.mkdir(); b = tmp_path / 'b'; b.mkdir()
    create(store, a); old = store.claim('binding-a')
    moved = store.bind('binding-a', 'vault-a', str(b), expected_revision=1, expected_generation=1)
    assert (moved.revision, moved.generation) == (2, 2)
    with pytest.raises(m.BindingError): store.assert_claim(old)
    current = store.claim('binding-a')
    inactive = store.unbind('binding-a', expected_revision=2, expected_generation=2)
    assert (inactive.revision, inactive.generation, inactive.active) == (3, 3, False)
    assert inactive.root == moved.root
    assert store.resolve('binding-a')['status'] == 'unbound'
    with pytest.raises(m.BindingError): store.assert_claim(current)
    with pytest.raises(m.BindingError): create(store, b, vault='vault-b', binding='binding-b')
    assert store.unbind('binding-a', expected_revision=3, expected_generation=3).revision == 3

@pytest.mark.parametrize('shape', ['same', 'child', 'parent'])
def test_same_and_parent_child_roots_cannot_have_different_owners(tmp_path, shape):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    a = tmp_path / 'a'; a.mkdir(); child = a / 'child'; child.mkdir()
    initial, other = (child, a) if shape == 'parent' else (a, child if shape == 'child' else a)
    create(store, initial)
    before = store.path.read_bytes()
    with pytest.raises(m.BindingError): create(store, other, vault='vault-b', binding='binding-b')
    assert store.path.read_bytes() == before

def test_offline_root_and_missing_binding_never_search_sibling_copy(tmp_path):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    root = tmp_path / 'original'; root.mkdir(); create(store, root)
    root.rmdir(); (tmp_path / 'copy').mkdir()
    state = store.resolve('binding-a')
    assert state['status'] == 'offline' and state['binding']['active'] is True
    assert store.resolve('missing') == {'status': 'unbound', 'binding': None}
    with pytest.raises(m.BindingError): store.claim('binding-a')

def test_inactive_null_k02_record_is_unbound_without_fallback(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'
    path.write_text(json.dumps({'schema_version': 'kb-contracts-1.0', 'store_id': '1' * 32, 'bindings': [{
        'schema_version': 'kb-contracts-1.0', 'revision': 1, 'binding_id': 'binding-a', 'vault_id': 'vault-a',
        'root': None, 'generation': 1, 'active': False, 'observed_at': '2026-10-07T00:00:00Z'}]}), encoding='utf-8')
    assert m.BindingStore(path).resolve('binding-a')['status'] == 'unbound'

@pytest.mark.parametrize('root', ['relative/root', 'C:/', 'C:/a/../b', 'C:/a.', 'C:/a:stream', '//server/share'])
def test_ambiguous_or_unsafe_root_is_rejected_before_store_creation(tmp_path, root):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    with pytest.raises(m.BindingError): create(store, root)
    assert not store.path.exists()

def test_corrupt_store_is_not_replaced_by_empty_state(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; path.write_bytes(b'{broken')
    root = tmp_path / 'root'; root.mkdir()
    with pytest.raises(m.BindingError): create(m.BindingStore(path), root)
    assert path.read_bytes() == b'{broken'

def test_same_revision_competing_real_writers_have_only_one_winner(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; root = tmp_path / 'root'; root.mkdir()
    barrier = Barrier(2)
    def writer(number):
        barrier.wait()
        try:
            create(m.BindingStore(path), root, binding=f'binding-{number}', vault=f'vault-{number}')
            return 'success'
        except m.BindingError:
            return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(writer, [1, 2]))
    assert sorted(outcomes) == ['refused', 'success']
    assert len(json.loads(path.read_text(encoding='utf-8'))['bindings']) == 1

@pytest.mark.parametrize('kind', ['junction', 'symlink'])
def test_actual_reparse_root_and_ancestor_are_rejected(tmp_path, kind):
    m = module(); real = tmp_path / 'real'; real.mkdir(); (real / 'child').mkdir()
    link = tmp_path / 'linked'
    if kind == 'junction':
        if os.name != 'nt': pytest.skip('junction requires Windows')
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(real)], capture_output=True)
        if result.returncode: pytest.skip('junction capability unavailable')
    else:
        try: link.symlink_to(real, target_is_directory=True)
        except OSError as error: pytest.skip(f'symlink capability unavailable: winerror={getattr(error, "winerror", None)}')
    store = m.BindingStore(tmp_path / 'bindings.json')
    for root in [link, link / 'child']:
        with pytest.raises(m.BindingError): create(store, root)
    assert not store.path.exists()


def test_guard_fences_cooperative_rebind_during_real_local_operation(tmp_path):
    m = module(); store = m.BindingStore(tmp_path / 'bindings.json')
    a = tmp_path / 'a'; a.mkdir(); b = tmp_path / 'b'; b.mkdir()
    create(store, a); claim = store.claim('binding-a')
    with store.guard(claim) as root:
        (root / 'evidence.txt').write_bytes(b'actual local operation')
        with pytest.raises(m.BindingError) as error:
            store.bind('binding-a', 'vault-a', str(b), expected_revision=1, expected_generation=1)
        assert error.value.code == 'binding_busy'
    assert (a / 'evidence.txt').read_bytes() == b'actual local operation'
    assert store.assert_claim(claim) == Path(claim['root'])


def test_same_record_concurrent_cas_preserves_single_winner(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'
    roots = [tmp_path / name for name in ['original', 'one', 'two']]
    for root in roots: root.mkdir()
    create(m.BindingStore(path), roots[0])
    barrier = Barrier(2)
    def writer(root):
        barrier.wait()
        try:
            m.BindingStore(path).bind('binding-a', 'vault-a', str(root), expected_revision=1, expected_generation=1)
            return 'success'
        except m.BindingError:
            return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(writer, roots[1:]))
    assert sorted(outcomes) == ['refused', 'success']
    binding = m.BindingStore(path).resolve('binding-a')['binding']
    assert binding['revision'] == binding['generation'] == 2


def test_inactive_reserved_root_with_ambiguous_windows_name_is_not_trusted(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'
    root = tmp_path / 'root'; root.mkdir(); store = m.BindingStore(path)
    create(store, root); store.unbind('binding-a', expected_revision=1, expected_generation=1)
    value = json.loads(path.read_text(encoding='utf-8'))
    value['bindings'][0]['root'] = str(root) + '.'
    path.write_text(json.dumps(value), encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(m.BindingError): store.resolve('binding-a')
    assert path.read_bytes() == before


def test_existing_k02_case_spelling_is_same_root_idempotent(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'
    root = tmp_path / 'Root'; root.mkdir(); store = m.BindingStore(path)
    create(store, root)
    value = json.loads(path.read_text(encoding='utf-8'))
    value['bindings'][0]['root'] = str(root).upper()
    path.write_text(json.dumps(value), encoding='utf-8')
    before = path.read_bytes()
    record = store.bind('binding-a', 'vault-a', str(root), expected_revision=1, expected_generation=1)
    assert (record.revision, record.generation) == (1, 1)
    assert path.read_bytes() == before


def _separate_process_rebind(path, root, queue):
    m = module()
    try:
        m.BindingStore(Path(path)).bind('binding-a', 'vault-a', root, expected_revision=1, expected_generation=1)
        queue.put('unexpected_success')
    except m.BindingError as error:
        queue.put(error.code)


def test_os_lock_blocks_a_separate_process_during_guard(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; store = m.BindingStore(path)
    a = tmp_path / 'a'; a.mkdir(); b = tmp_path / 'b'; b.mkdir(); create(store, a)
    context = multiprocessing.get_context('spawn'); queue = context.Queue()
    with store.guard(store.claim('binding-a')):
        process = context.Process(target=_separate_process_rebind, args=(str(path), str(b), queue))
        process.start(); process.join(timeout=15)
        if process.is_alive():
            process.terminate(); process.join(); pytest.fail('isolated worker did not exit')
        assert process.exitcode == 0
        assert queue.get(timeout=2) == 'binding_busy'
    queue.close(); queue.join_thread()
    assert store.resolve('binding-a')['binding']['generation'] == 1


def test_os_sharing_failure_preserves_previous_json_and_claim(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; store = m.BindingStore(path)
    a = tmp_path / 'a'; a.mkdir(); b = tmp_path / 'b'; b.mkdir(); create(store, a)
    before = path.read_bytes(); claim = store.claim('binding-a')
    with path.open('rb'):
        with pytest.raises(m.BindingError) as error:
            store.bind('binding-a', 'vault-a', str(b), expected_revision=1, expected_generation=1)
        assert error.value.code == 'binding_write_failed'
    assert path.read_bytes() == before
    assert store.assert_claim(claim) == Path(claim['root'])


def test_unusable_lock_location_is_explicit_failure_without_new_authority(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; root = tmp_path / 'root'; root.mkdir()
    (tmp_path / 'bindings.json.lock').mkdir()
    with pytest.raises(m.BindingError) as error:
        create(m.BindingStore(path), root)
    assert error.value.code == 'binding_store_unavailable'
    assert not path.exists()


def test_old_claim_is_not_authority_for_a_copied_store(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; root = tmp_path / 'root'; root.mkdir()
    store = m.BindingStore(path); create(store, root); claim = store.claim('binding-a')
    copy = tmp_path / 'copied-bindings.json'; copy.write_bytes(path.read_bytes())
    with pytest.raises(m.BindingError): m.BindingStore(copy).assert_claim(claim)


def test_store_recreation_cannot_resurrect_old_claim(tmp_path):
    m = module(); path = tmp_path / 'bindings.json'; root = tmp_path / 'root'; root.mkdir()
    store = m.BindingStore(path); create(store, root); old = store.claim('binding-a')
    path.unlink(); create(store, root)
    with pytest.raises(m.BindingError): store.assert_claim(old)

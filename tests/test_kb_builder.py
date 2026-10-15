"""Explicit disposable local Builder plans, real text/blob/path failures."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

def api():
    assert importlib.util.find_spec('kb_core.builder') is not None, 'T16 local Builder is missing'
    from kb_core import builder
    return builder

def text(path='AGENTS.md', content='Generic fixture instructions\n'):
    raw = content.encode('utf-8')
    return {'path': path, 'kind': 'text', 'text': content, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def setup(tmp_path, files=None):
    m = api(); state = tmp_path / 'state'; state.mkdir()
    target = tmp_path / 'independent'; sources = tmp_path / 'sources'; sources.mkdir()
    plan = {'operation_id': 'create-1', 'target': str(target), 'files': files or [text(), text('purpose.md'), text('notes/start.md')]}
    return m, m.LocalBuilder(state), plan, target, sources

def stage(builder, plan, target, sources):
    return builder.stage(plan, authorized_target=target, authorized_source_roots=[sources], expected_hash=api().plan_hash(plan))

def build(builder, plan, target, sources):
    return builder.build(plan, authorized_target=target, authorized_source_roots=[sources], expected_hash=api().plan_hash(plan))

def test_generic_skeleton_stage_validate_place_and_replay_are_real(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    staged = stage(builder, plan, target, sources)
    assert staged['phase'] == 'staged' and not target.exists()
    assert builder.validate('create-1')['phase'] == 'validated'
    placed = builder.place('create-1', authorized_target=target)
    assert placed['phase'] == 'placed' and placed['replayed'] is False
    assert (target / 'notes/start.md').read_bytes() == b'Generic fixture instructions\n'
    before = (target / 'AGENTS.md').read_bytes()
    assert build(builder, plan, target, sources)['replayed'] is True
    assert (target / 'AGENTS.md').read_bytes() == before

def test_blob_above_legacy_text_limit_is_streamed_and_hashed(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    raw = bytes(range(256)) * 12288
    source = sources / 'asset.bin'; source.write_bytes(raw)
    plan['files'].append({'path': 'resources/asset.bin', 'kind': 'blob', 'source': str(source),
                          'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    result = build(builder, plan, target, sources)
    assert result['phase'] == 'placed'
    assert (target / 'resources/asset.bin').read_bytes() == raw
    assert source.read_bytes() == raw

@pytest.mark.parametrize('path', ['../outside', '/absolute', 'C:/outside', 'a\\b', 'a:stream', 'a.', 'CON.txt', '.git/config'])
def test_unsafe_relative_names_never_create_target_or_operation(tmp_path, path):
    m, builder, plan, target, sources = setup(tmp_path)
    plan['files'][0]['path'] = path
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not target.exists() and list(builder.state_dir.iterdir()) == []

def test_duplicate_and_parent_file_collisions_are_preflight_failures(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    for files in [[text('A.md'), text('a.md')], [text('a'), text('a/b')]]:
        plan['files'] = files
        with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not target.exists()

def test_explicit_authorization_and_reviewed_hash_cannot_be_guessed(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    for allowed, digest in [(tmp_path / 'other', m.plan_hash(plan)), (target, '0' * 64)]:
        with pytest.raises(m.BuildError):
            builder.build(plan, authorized_target=allowed, authorized_source_roots=[sources], expected_hash=digest)
    assert not target.exists() and list(builder.state_dir.iterdir()) == []

def test_blob_outside_source_scope_is_not_copied(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    outside = tmp_path / 'private.bin'; outside.write_bytes(b'private fixture')
    plan['files'] = [{'path': 'asset.bin', 'kind': 'blob', 'source': str(outside), 'bytes': 15, 'sha256': '0' * 64}]
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not target.exists() and outside.read_bytes() == b'private fixture'

def test_declared_size_hash_and_independent_resource_budget_fail_closed(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    for entry in [dict(text(), sha256='0' * 64), dict(text(), bytes=True), text(content='x' * (2 * 1024 * 1024 + 1)),
                  {'path': 'large.bin', 'kind': 'blob', 'source': str(sources / 'missing'),
                   'bytes': 64 * 1024 * 1024 + 1, 'sha256': 'a' * 64}]:
        plan['files'] = [entry]
        with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not target.exists()

def test_existing_empty_or_user_target_is_never_overwritten(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    target.mkdir()
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    (target / 'user.txt').write_bytes(b'user content')
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert (target / 'user.txt').read_bytes() == b'user content'

def test_interrupted_staged_operation_retries_without_recopied_sources(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    stage(builder, plan, target, sources)
    restarted = m.LocalBuilder(builder.state_dir)
    assert restarted.inspect('create-1')['phase'] == 'staged'
    assert build(restarted, plan, target, sources)['phase'] == 'placed'

def test_new_target_after_validation_stops_and_preserves_stage_and_user_content(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    stage(builder, plan, target, sources); builder.validate('create-1')
    target.mkdir(); (target / 'user.txt').write_bytes(b'user content')
    with pytest.raises(m.BuildError): builder.place('create-1', authorized_target=target)
    assert (target / 'user.txt').read_bytes() == b'user content'
    assert builder.inspect('create-1')['status'] == 'conflict'

def test_changed_staged_or_completed_files_are_not_overwritten_on_retry(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    result = stage(builder, plan, target, sources)
    staged = Path(result['staging'])
    (staged / 'AGENTS.md').write_bytes(b'later user edit')
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert (staged / 'AGENTS.md').read_bytes() == b'later user edit' and not target.exists()
    assert builder.inspect('create-1')['status'] == 'conflict'

def test_operation_reuse_with_changed_plan_or_unrecognized_stage_is_refused(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    stage(builder, plan, target, sources)
    plan['files'].append(text('extra.md'))
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not target.exists()

@pytest.mark.parametrize('kind', ['junction', 'symlink'])
def test_real_linked_source_and_target_ancestor_are_refused(tmp_path, kind):
    m, builder, plan, target, sources = setup(tmp_path)
    real = tmp_path / 'real'; real.mkdir(); (real / 'asset.bin').write_bytes(b'fixture')
    link = tmp_path / 'linked'
    if kind == 'junction':
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(real)], capture_output=True)
        if result.returncode: pytest.skip('actual junction unavailable')
    else:
        try: link.symlink_to(real, target_is_directory=True)
        except OSError: pytest.skip('actual symlink unavailable')
    plan['files'] = [{'path': 'asset.bin', 'kind': 'blob', 'source': str(link / 'asset.bin'),
                      'bytes': 7, 'sha256': hashlib.sha256(b'fixture').hexdigest()}]
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    plan['files'] = [text()]; plan['target'] = str(link / 'new')
    with pytest.raises(m.BuildError): build(builder, plan, link / 'new', sources)
    assert not (real / 'new').exists()


def test_rename_then_interrupted_journal_recovers_same_operation(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    staged = stage(builder, plan, target, sources); builder.validate('create-1')
    Path(staged['staging']).rename(target)  # Actual completed placement before journal update.
    restarted = m.LocalBuilder(builder.state_dir)
    result = build(restarted, plan, target, sources)
    assert result['phase'] == 'placed' and result['replayed'] is True
    assert (target / 'AGENTS.md').read_bytes() == b'Generic fixture instructions\n'


def test_deleted_file_after_staged_phase_is_conflict_not_automatic_repair(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    staged = stage(builder, plan, target, sources)
    file = Path(staged['staging']) / 'AGENTS.md'; file.unlink()
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not file.exists() and not target.exists()


def test_bad_blob_hash_preserves_diagnostic_stage_without_placing(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    source = sources / 'blob'; source.write_bytes(b'ordinary fixture')
    plan['files'] = [{'path': 'blob', 'kind': 'blob', 'source': str(source), 'bytes': 16, 'sha256': '0' * 64}]
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    result = builder.inspect('create-1')
    assert result['phase'] == 'prepared' and result['status'] == 'conflict' and not target.exists()
    assert (Path(result['staging']) / 'blob').read_bytes() == b'ordinary fixture'


def test_unknown_stage_file_is_retained_and_blocks_validation(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    staged = stage(builder, plan, target, sources)
    user = Path(staged['staging']) / 'user-unrecognized'; user.write_bytes(b'do not delete')
    with pytest.raises(m.BuildError): builder.validate('create-1')
    assert user.read_bytes() == b'do not delete' and not target.exists()


def test_actual_journal_replace_failure_after_placement_can_be_reconciled(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    stage(builder, plan, target, sources); builder.validate('create-1')
    journal = builder.state_dir / 'create-1.json'; before = journal.read_bytes()
    with journal.open('rb'):
        with pytest.raises(m.BuildError): builder.place('create-1', authorized_target=target)
    assert target.is_dir() and journal.read_bytes() == before
    assert builder.inspect('create-1')['phase'] == 'validated'
    assert build(builder, plan, target, sources)['replayed'] is True


def test_two_operation_ids_never_merge_or_replace_same_target(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    first = stage(builder, plan, target, sources); builder.validate('create-1')
    second = dict(plan, operation_id='create-2')
    other = stage(builder, second, target, sources); builder.validate('create-2')
    builder.place('create-1', authorized_target=target)
    before = (target / 'AGENTS.md').read_bytes()
    with pytest.raises(m.BuildError): builder.place('create-2', authorized_target=target)
    assert (target / 'AGENTS.md').read_bytes() == before and Path(other['staging']).is_dir()


def test_corrupt_journal_and_duplicate_keys_are_not_optimistic_success(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    stage(builder, plan, target, sources)
    journal = builder.state_dir / 'create-1.json'
    data = journal.read_text(encoding='utf-8')
    data = data.replace('"phase": "staged"', '"phase": "prepared", "phase": "staged"')
    journal.write_text(data, encoding='utf-8')
    before = journal.read_bytes()
    with pytest.raises(m.BuildError): builder.inspect('create-1')
    assert journal.read_bytes() == before and not target.exists()


def test_missing_validated_stage_is_not_recreated_or_searched_elsewhere(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    staged = stage(builder, plan, target, sources); builder.validate('create-1')
    original = Path(staged['staging']); relocated = tmp_path / 'user-relocated'
    original.rename(relocated)
    with pytest.raises(m.BuildError): build(builder, plan, target, sources)
    assert not original.exists() and not target.exists()
    assert (relocated / 'AGENTS.md').read_bytes() == b'Generic fixture instructions\n'


def test_wrong_kind_type_has_stable_error_before_any_write(tmp_path):
    m, builder, plan, target, sources = setup(tmp_path)
    plan['files'][0]['kind'] = ['text']
    with pytest.raises(m.BuildError) as error: build(builder, plan, target, sources)
    assert error.value.code == 'plan_invalid'
    assert not target.exists() and list(builder.state_dir.iterdir()) == []

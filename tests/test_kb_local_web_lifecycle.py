import hashlib
import http.client
from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from kb_core import local_web_lifecycle
import kb_local_web_lifecycle as lifecycle_cli
from kb_core.local_web_lifecycle import (
    LocalLifecycleError, config_from_legacy_argv, process_matches, process_matches_command,
    reusable_process_matches,
)


def legacy_argv(tmp_path):
    values = {}
    for name in ('instance', 'policy-root', 'catalog-config', 'authorization', 'access-token-file'):
        path = tmp_path / name
        if name in {'instance', 'policy-root'}:
            path.mkdir()
        else:
            path.write_text('private fixture', encoding='utf-8')
        values[name] = str(path.resolve())
    return [
        r'C:\Python\python.exe', 'tools/kb_display_local.py', 'serve',
        '--instance', values['instance'], '--policy-root', values['policy-root'],
        '--catalog-config', values['catalog-config'], '--authorization', values['authorization'],
        '--access-token-file', values['access-token-file'], '--read-authorized', '--port', '5210',
    ], values


def test_adoption_extracts_private_file_references_without_copying_secret_values(tmp_path):
    argv, values = legacy_argv(tmp_path)
    config = config_from_legacy_argv(argv, source_root=ROOT, python_path=Path(argv[0]),
                                     rollback_source_root=ROOT)
    assert config['schema_version'] == 'local-web-1'
    assert config['port'] == 5210
    assert config['instance'] == values['instance']
    assert config['access_token_file'] == values['access-token-file']
    assert 'token_value' not in config and 'bearer' not in config
    assert config['access_token_file'] == values['access-token-file']
    assert 'private fixture' not in str(config)


@pytest.mark.parametrize('mutation', [
    lambda argv: argv.__setitem__(1, 'other.py'),
    lambda argv: argv.__setitem__(2, 'authorize'),
    lambda argv: argv.__setitem__(-1, '9999'),
    lambda argv: argv.remove('--read-authorized'),
])
def test_adoption_rejects_unrecognized_or_unsafe_listener_arguments(tmp_path, mutation):
    argv, _ = legacy_argv(tmp_path)
    mutation(argv)
    with pytest.raises(LocalLifecycleError):
        config_from_legacy_argv(argv, source_root=ROOT, python_path=Path(argv[0]),
                                rollback_source_root=ROOT)


def test_process_receipt_requires_exact_creation_executable_and_command_fingerprint():
    command = '"C:\\Python\\python.exe" tools/kb_display_local.py serve --port 5210'
    receipt = {
        'pid': 1234,
        'created': '20261012001707.123456+480',
        'executable': r'C:\Python\python.exe',
        'command_sha256': hashlib.sha256(command.encode('utf-16le')).hexdigest(),
    }
    current = {'pid': 1234, 'created': receipt['created'], 'executable': receipt['executable'],
               'command_line': command}
    assert process_matches(receipt, current)
    assert not process_matches(receipt, {**current, 'pid': 1235})
    assert not process_matches(receipt, {**current, 'created': 'later'})
    assert not process_matches(receipt, {**current, 'executable': r'C:\Other\python.exe'})
    assert not process_matches(receipt, {**current, 'command_line': command + ' --different'})


def test_process_receipt_accepts_only_the_verified_windows_venv_child_process():
    import datetime as dt

    expected = [r'C:\candidate\.venv\Scripts\python.exe', r'C:\candidate\tools\kb_display_local.py',
                'serve', '--port', '5211']
    runtime_image = r'C:\Python\python.exe'
    started_at = dt.datetime(2026, 10, 12, 12, 0, 0, tzinfo=dt.timezone.utc).timestamp()
    child = {
        'pid': 5001,
        'parent_pid': 5000,
        'created': '20261012120000.026000+000',
        'executable': runtime_image,
        # Windows venv launchers may report the base image as argv[0].
        'command_line': '"C:\\Python\\python.exe" '
                        '"C:\\candidate\\tools\\kb_display_local.py" '
                        'serve --port 5211',
    }
    is_owned_child = getattr(local_web_lifecycle, 'process_matches_launch', None)
    assert callable(is_owned_child), 'must recognize the verified venv child process'
    assert is_owned_child(5000, started_at, child, expected_executable=runtime_image, expected_argv=expected)
    assert not is_owned_child(5002, started_at, child, expected_executable=runtime_image, expected_argv=expected)
    assert not is_owned_child(5000, started_at, {**child, 'created': '20261012120006.000000+000'},
                              expected_executable=runtime_image, expected_argv=expected)
    assert not is_owned_child(5000, started_at, {**child, 'command_line': child['command_line'] + ' --evil'},
                              expected_executable=runtime_image, expected_argv=expected)


def test_process_command_match_accepts_base_executable_as_venv_argv_zero():
    expected = [r'C:\candidate\.venv\Scripts\python.exe',
                r'C:\candidate\tools\kb_display_local.py', 'serve', '--port', '5211']
    current = {'executable': r'C:\Python\python.exe',
               'command_line': '"C:\\Python\\python.exe" '
                               '"C:\\candidate\\tools\\kb_display_local.py" '
                               'serve --port 5211'}
    assert process_matches_command(current, expected_executable=r'C:\Python\python.exe',
                                   expected_argv=expected)
    assert not process_matches_command({**current, 'command_line': current['command_line'] + ' --other'},
                                       expected_executable=r'C:\Python\python.exe',
                                       expected_argv=expected)


def test_process_command_match_compares_windows_executable_paths_canonically():
    expected = [r'C:\candidate\.venv\Scripts\python.exe',
                r'C:\candidate\tools\kb_display_local.py', 'serve', '--port', '5211']
    current = {'executable': r'C:\Python\..\Python\python.exe',
               'command_line': '"C:\\Python\\python.exe" '
                               '"C:\\candidate\\tools\\kb_display_local.py" '
                               'serve --port 5211'}
    assert process_matches_command(current, expected_executable=r'C:\Python\python.exe',
                                   expected_argv=expected)


def test_python_image_uses_the_selected_interpreter_runtime_identity(tmp_path, monkeypatch):
    selected = tmp_path / 'venv' / 'Scripts' / 'python.exe'
    base_image = tmp_path / 'runtime' / 'python.exe'
    base_image.parent.mkdir()
    base_image.write_bytes(b'python image')
    selected.parent.mkdir(parents=True)
    (selected.parent.parent / 'pyvenv.cfg').write_text(
        f'home = {tmp_path / "wrong-runtime"}\n', encoding='utf-8')
    calls = []

    def report_selected_python(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, str(base_image.resolve()), '')

    monkeypatch.setattr(lifecycle_cli.subprocess, 'run', report_selected_python)
    assert lifecycle_cli._python_image(selected) == str(base_image.resolve())
    assert calls[0][0] == [str(selected.resolve()), '-c',
                           'import sys;print(sys._base_executable or sys.executable)']


def test_handoff_can_start_when_the_previous_local_service_is_already_offline(tmp_path, monkeypatch):
    legacy_receipt = tmp_path / 'legacy-process.json'
    legacy_receipt.write_text('{"old":true}', encoding='utf-8')
    starts = []
    monkeypatch.setattr(lifecycle_cli, '_load_config', lambda: {'rollback_source_root': str(ROOT)})
    monkeypatch.setattr(lifecycle_cli, '_validate_runtime', lambda _config: None)
    monkeypatch.setattr(lifecycle_cli, 'build_fingerprint', lambda _root: 'b' * 64)
    monkeypatch.setattr(lifecycle_cli, '_health', lambda port: {'build_id': 'b' * 64} if port == 5211 else None)
    monkeypatch.setattr(lifecycle_cli, '_legacy_path', lambda: legacy_receipt)
    monkeypatch.setattr(lifecycle_cli, '_listener', lambda _port: None)

    def start(config, port, *, source_root, fallback=False):
        starts.append((port, source_root, fallback))
        return {'status': 'started', 'port': port, 'build_id': 'b' * 64}

    monkeypatch.setattr(lifecycle_cli, '_start_service', start)
    result = lifecycle_cli._handoff()

    assert result['status'] == 'handed_off'
    assert starts == [(5210, ROOT, False)]
    assert not legacy_receipt.exists()


def test_handoff_stops_only_the_matching_owned_previous_candidate_receipt(tmp_path, monkeypatch):
    process_receipt = tmp_path / 'process-5210.json'
    process_receipt.write_text('{"pid":5000}', encoding='utf-8')
    legacy_receipt = tmp_path / 'legacy-process.json'
    stopped = []
    starts = []
    monkeypatch.setattr(lifecycle_cli, '_load_config', lambda: {'rollback_source_root': str(ROOT)})
    monkeypatch.setattr(lifecycle_cli, '_validate_runtime', lambda _config: None)
    monkeypatch.setattr(lifecycle_cli, 'build_fingerprint', lambda _root: 'b' * 64)
    monkeypatch.setattr(lifecycle_cli, '_health', lambda port: {'build_id': 'b' * 64} if port == 5211 else None)
    monkeypatch.setattr(lifecycle_cli, '_receipt_path', lambda _port: process_receipt)
    monkeypatch.setattr(lifecycle_cli, '_legacy_path', lambda: legacy_receipt)
    monkeypatch.setattr(lifecycle_cli, '_listener', lambda port: {'address': '127.0.0.1', 'pid': 5000} if port == 5210 else None)
    monkeypatch.setattr(lifecycle_cli, '_stop_exact', lambda path, *, require_health: stopped.append((path, require_health)))
    monkeypatch.setattr(lifecycle_cli, '_start_service', lambda config, port, *, source_root, fallback=False:
                        starts.append((port, source_root, fallback)) or
                        {'status': 'started', 'port': port, 'build_id': 'b' * 64})

    result = lifecycle_cli._handoff()

    assert result['status'] == 'handed_off'
    assert stopped == [(process_receipt, True)]
    assert starts == [(5210, ROOT, False)]


def test_locate_token_opens_only_the_configured_file_location_without_printing_secret(monkeypatch, capsys):
    token_path = Path(r'C:\Users\owner\AppData\Local\KnowledgeWorkspace\access-token.txt')
    config = {'access_token_file': str(token_path)}
    calls = []
    from types import SimpleNamespace
    monkeypatch.setattr(lifecycle_cli, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(lifecycle_cli, '_load_config', lambda: config)
    monkeypatch.setattr(lifecycle_cli, '_read_access_token', lambda path: 'test-secret-value')
    monkeypatch.setattr(lifecycle_cli.subprocess, 'Popen', lambda command, **kwargs: calls.append((command, kwargs)))

    exit_code = lifecycle_cli.main(['locate-token'])

    assert exit_code == 0
    assert calls == [(['explorer.exe', f'/select,{token_path}'], {'close_fds': True})]
    output = capsys.readouterr().out
    assert 'token_location_opened' in output
    assert 'test-secret-value' not in output


def test_locate_token_refuses_missing_or_invalid_credential_file(monkeypatch):
    monkeypatch.setattr(lifecycle_cli, '_load_config', lambda: {'access_token_file': r'C:\missing\token.txt'})

    def reject(_path):
        from kb_core.local_vault_web import LocalWebError
        raise LocalWebError('local_access_token_unavailable')

    monkeypatch.setattr(lifecycle_cli, '_read_access_token', reject)
    with pytest.raises(LocalLifecycleError, match='local_access_token_unavailable'):
        lifecycle_cli._locate_token()


def test_reuse_requires_matching_receipt_build_and_exact_current_command(monkeypatch):
    expected_argv = [r'C:\candidate\.venv\Scripts\python.exe',
                     r'C:\candidate\tools\kb_display_local.py', 'serve', '--port', '5211']
    command = 'verified launch command'
    current = {'pid': 5001, 'created': '20261012120000.026000+000',
               'executable': r'C:\Python\python.exe', 'command_line': command}
    receipt = {'pid': 5001, 'created': current['created'], 'executable': current['executable'],
               'command_sha256': hashlib.sha256(command.encode('utf-16le')).hexdigest(),
               'port': 5211, 'build_id': 'b' * 64}
    monkeypatch.setattr(local_web_lifecycle, 'split_windows_command_line', lambda _: expected_argv)
    kwargs = {'port': 5211, 'build_id': 'b' * 64, 'expected_executable': current['executable'],
              'expected_argv': expected_argv}
    assert reusable_process_matches(receipt, current, **kwargs)
    assert not reusable_process_matches({**receipt, 'build_id': 'c' * 64}, current, **kwargs)
    assert not reusable_process_matches(receipt, {**current, 'pid': 5002}, **kwargs)
    assert not reusable_process_matches(receipt, current,
        **{**kwargs, 'expected_argv': [*expected_argv, '--unexpected']})


def test_local_probes_use_only_fixed_loopback_host_and_allowlisted_paths(monkeypatch):
    calls = []

    class Response:
        status = 200

        @staticmethod
        def read(limit):
            calls.append(('read', limit))
            return b'{"status":"ok"}'

    class Connection:
        def __init__(self, host, port, timeout):
            calls.append(('connect', host, port, timeout))

        def request(self, method, path, *, headers):
            calls.append(('request', method, path, headers))

        @staticmethod
        def getresponse():
            return Response()

        @staticmethod
        def close():
            calls.append(('close',))

    monkeypatch.setattr(http.client, 'HTTPConnection', Connection)
    assert local_web_lifecycle.loopback_get(5211, '/healthz', maximum=64) == (200, b'{"status":"ok"}')
    assert calls == [
        ('connect', '127.0.0.1', 5211, 1),
        ('request', 'GET', '/healthz', {'Host': '127.0.0.1:5211'}),
        ('read', 65), ('close',),
    ]
    calls.clear()
    with pytest.raises(LocalLifecycleError, match='local_probe_target_invalid'):
        local_web_lifecycle.loopback_get(5212, '/healthz', maximum=64)
    with pytest.raises(LocalLifecycleError, match='local_probe_target_invalid'):
        local_web_lifecycle.loopback_get(5211, '/api/private', maximum=64)
    assert calls == []


@pytest.mark.skipif(os.name != 'nt' or not shutil.which('powershell.exe'),
                    reason='requires Windows PowerShell 5 parser')
def test_windows_launcher_is_readable_by_windows_powershell_5():
    launcher = ROOT / 'scripts' / 'KnowledgeWorkspace.ps1'
    command = (
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile($env:KB_LAUNCHER,[ref]$tokens,[ref]$errors) | Out-Null; "
        "if($errors.Count){$errors | ForEach-Object { Write-Error $_.Message }; exit 1}"
    )
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
        env={**os.environ, 'KB_LAUNCHER': str(launcher)},
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert result.returncode == 0, result.stderr

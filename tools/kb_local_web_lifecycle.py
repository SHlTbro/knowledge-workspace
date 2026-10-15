"""Start and manage the owner-local, read-only Vault Web on Windows."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools' / 'vault-workspace' / 'src'))

from kb_core.local_vault_web import (
    LocalWebError, _read_access_token, _read_json as _read_web_json,
    authorize_current_scope, build_fingerprint, pending_authorization_changes,
)
from kb_core.local_web_lifecycle import (
    LocalLifecycleError, config_from_legacy_argv, loopback_get, process_creation_timestamp,
    process_matches, process_matches_launch, reusable_process_matches, split_windows_command_line,
)


def _state_dir() -> Path:
    base = os.environ.get('LOCALAPPDATA')
    if os.name != 'nt' or not base:
        raise LocalLifecycleError('local_user_config_unavailable')
    return Path(base) / 'KnowledgeWorkspace'


def _run(command: list[str], *, timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise LocalLifecycleError('local_runtime_unavailable') from None


def _protect_acl(path: Path, *, directory: bool) -> None:
    sid_result = _run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                       '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'])
    sid = sid_result.stdout.strip()
    if sid_result.returncode or not sid.startswith('S-1-'):
        raise LocalLifecycleError('local_config_acl_failed')
    rights = '(OI)(CI)F' if directory else 'F'
    result = _run(['icacls.exe', str(path), '/inheritance:r', '/grant:r',
                   f'*{sid}:{rights}', f'*S-1-5-18:{rights}'])
    if result.returncode:
        raise LocalLifecycleError('local_config_acl_failed')


def _private_dir() -> Path:
    path = _state_dir()
    path.mkdir(parents=True, exist_ok=True)
    _protect_acl(path, directory=True)
    return path


def _private_json(path: Path, value: dict) -> None:
    state = _private_dir()
    if path.parent.resolve() != state.resolve():
        raise LocalLifecycleError('local_config_path_invalid')
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=state, prefix='.local-web-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _protect_acl(temporary, directory=False)
        os.replace(temporary, path)
        temporary = None
        _protect_acl(path, directory=False)
    except OSError:
        raise LocalLifecycleError('local_config_write_failed') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path, *, maximum: int = 64 * 1024) -> dict:
    try:
        info = path.lstat()
        if not path.is_file() or path.is_symlink() or info.st_nlink != 1 or info.st_size > maximum:
            raise OSError
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise LocalLifecycleError('local_config_invalid') from None


def _config_path() -> Path:
    return _state_dir() / 'local-web.json'


def _receipt_path(port: int) -> Path:
    return _state_dir() / f'process-{port}.json'


def _legacy_path() -> Path:
    return _state_dir() / 'legacy-process.json'


def _load_config() -> dict:
    config = _read_json(_config_path())
    expected = {'schema_version', 'source_root', 'rollback_source_root', 'python_path',
                'instance', 'policy_root', 'catalog_config', 'authorization',
                'access_token_file', 'port'}
    if set(config) != expected or config.get('schema_version') != 'local-web-1':
        raise LocalLifecycleError('local_config_invalid')
    if type(config.get('port')) is not int or config['port'] != 5210:
        raise LocalLifecycleError('local_config_invalid')
    for key in expected - {'schema_version', 'port'}:
        if not isinstance(config[key], str) or not Path(config[key]).is_absolute():
            raise LocalLifecycleError('local_config_invalid')
    if Path(config['source_root']).resolve() != ROOT.resolve():
        raise LocalLifecycleError('local_source_mismatch')
    return config


def _listener(port: int) -> dict | None:
    result = _run(['netstat.exe', '-ano', '-p', 'tcp'])
    if result.returncode:
        raise LocalLifecycleError('local_runtime_unavailable')
    matches = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[-2].upper() != 'LISTENING':
            continue
        local = fields[1]
        if not local.endswith(':' + str(port)):
            continue
        try:
            pid = int(fields[-1])
        except ValueError:
            continue
        address = local.rsplit(':', 1)[0].strip('[]')
        matches.append({'address': address, 'pid': pid})
    if len(matches) > 1:
        raise LocalLifecycleError('local_port_conflict')
    return matches[0] if matches else None


def _process(pid: int) -> dict | None:
    if type(pid) is not int or pid <= 0:
        return None
    script = (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; "
              "if($p){$created=$p.CreationDate.ToUniversalTime().ToString('yyyyMMddHHmmss.ffffff') + '+000';"
              "[pscustomobject]@{ProcessId=$p.ProcessId;ParentProcessId=$p.ParentProcessId;CreationDate=$created;"
              "ExecutablePath=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p.ExecutablePath));"
              "CommandLine=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p.CommandLine))} "
              "| ConvertTo-Json -Compress}")
    result = _run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script])
    if result.returncode or not result.stdout.strip():
        return None
    try:
        row = json.loads(result.stdout)
        if not isinstance(row, dict) or not row.get('CommandLine') or not row.get('ExecutablePath'):
            return None
        import base64
        executable = base64.b64decode(row['ExecutablePath'], validate=True).decode('utf-8')
        command_line = base64.b64decode(row['CommandLine'], validate=True).decode('utf-8')
        return {'pid': int(row['ProcessId']), 'created': str(row['CreationDate']),
                'parent_pid': int(row['ParentProcessId']),
                'executable': executable, 'command_line': command_line}
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None


def _identity(process: dict, *, port: int, build_id: str, source_root: Path) -> dict:
    command = process['command_line']
    try:
        commit = subprocess.run(['git', '-C', str(source_root), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, timeout=5, check=False).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        commit = ''
    return {'pid': process['pid'], 'created': process['created'], 'executable': process['executable'],
            'command_sha256': hashlib.sha256(command.encode('utf-16le')).hexdigest(),
            'port': port, 'build_id': build_id, 'source_commit': commit}


def _health(port: int) -> dict | None:
    try:
        status, raw = loopback_get(port, '/healthz', maximum=2048)
        if status != 200 or len(raw) > 2048:
            return None
        value = json.loads(raw)
        if (isinstance(value, dict) and value.get('status') == 'ok'
                and value.get('port') == port and isinstance(value.get('build_id'), str)
                and len(value['build_id']) == 64):
            return value
    except (OSError, ValueError, LocalLifecycleError, http.client.HTTPException):
        return None
    return None


def _probe_previous_web(port: int) -> bool:
    try:
        status, raw = loopback_get(port, '/api/vaults', maximum=1024)
        return status == 401 and len(raw) <= 1024
    except (OSError, LocalLifecycleError, http.client.HTTPException):
        return False


def _service_argv(config: dict, *, port: int, source_root: Path) -> list[str]:
    script = source_root / 'tools' / 'kb_display_local.py'
    return [config['python_path'], str(script), 'serve', '--instance', config['instance'],
            '--policy-root', config['policy_root'], '--catalog-config', config['catalog_config'],
            '--authorization', config['authorization'], '--access-token-file', config['access_token_file'],
            '--read-authorized', '--port', str(port)]


def _python_image(python_path: str | Path) -> str:
    """Resolve the Windows venv shim to its configured base interpreter image."""
    path = Path(python_path).resolve()
    try:
        result = subprocess.run([str(path), '-c', 'import sys;print(sys._base_executable or sys.executable)'],
                                capture_output=True, text=True, timeout=5, check=False)
        image = Path(result.stdout.strip())
        if result.returncode == 0 and image.is_absolute() and image.is_file():
            return str(image.resolve())
    except (OSError, subprocess.TimeoutExpired):
        pass
    cfg = path.parent.parent / 'pyvenv.cfg'
    try:
        for line in cfg.read_text(encoding='utf-8').splitlines():
            key, separator, value = line.partition('=')
            if separator and key.strip().casefold() == 'home':
                base = Path(value.strip()) / 'python.exe'
                if base.is_file():
                    return str(base.resolve())
    except (OSError, UnicodeError):
        pass
    return str(path)


def _adopt_child_receipt(port: int, listener: dict, expected: str, argv: list[str],
                         source_root: Path) -> bool:
    """Upgrade a prior venv-shim receipt only when its exact child is still serving."""
    path = _receipt_path(port)
    if not path.exists():
        return False
    try:
        prior = _read_json(path)
    except LocalLifecycleError:
        return False
    health = _health(port)
    if not health or health.get('build_id') != prior.get('build_id'):
        return False
    current = _process(listener['pid'])
    launch_time = process_creation_timestamp(prior.get('created'))
    command_hash = (hashlib.sha256(current['command_line'].encode('utf-16le')).hexdigest()
                    if current else None)
    if (not current or launch_time is None or prior.get('command_sha256') != command_hash
            or not process_matches_launch(prior.get('pid'), launch_time, current,
                                          expected_executable=expected, expected_argv=argv)):
        return False
    receipt = _identity(current, port=port, build_id=prior.get('build_id', ''), source_root=source_root)
    if prior.get('fallback') is True:
        receipt['fallback'] = True
    _private_json(path, receipt)
    return True


def _validate_runtime(config: dict) -> None:
    for key in ('instance', 'policy_root'):
        if not Path(config[key]).is_dir():
            raise LocalLifecycleError('local_binding_offline')
    for key in ('catalog_config', 'authorization', 'access_token_file'):
        if not Path(config[key]).is_file():
            raise LocalLifecycleError('local_configuration_missing')
    if not Path(config['python_path']).is_file():
        raise LocalLifecycleError('local_python_environment_missing')
    if not (Path(config['source_root']) / 'tools' / 'kb_display_local.py').is_file():
        raise LocalLifecycleError('local_source_unavailable')
    try:
        _read_access_token(Path(config['access_token_file']))
    except (LocalWebError, OSError, ValueError):
        raise LocalLifecycleError('local_access_token_unavailable') from None


def _start_service(config: dict, port: int, *, source_root: Path, fallback: bool = False) -> dict:
    if port not in {5210, 5211}:
        raise LocalLifecycleError('local_port_invalid')
    _validate_runtime(config)
    expected = build_fingerprint(source_root)
    argv = _service_argv(config, port=port, source_root=source_root)
    expected_image = _python_image(config['python_path'])
    existing = _listener(port)
    if existing:
        if existing['address'] != '127.0.0.1':
            raise LocalLifecycleError('local_non_loopback_listener_refused')
        healthy = _health(port)
        if healthy:
            if healthy['build_id'] != expected:
                raise LocalLifecycleError('local_port_in_use')
            _adopt_child_receipt(port, existing, expected_image, argv, source_root)
            try:
                receipt = _read_json(_receipt_path(port))
            except LocalLifecycleError:
                raise LocalLifecycleError('local_port_in_use') from None
            current = _process(existing['pid'])
            if reusable_process_matches(receipt, current, port=port, build_id=expected,
                                        expected_executable=expected_image, expected_argv=argv):
                return {'status': 'reused', 'port': port, 'build_id': expected}
        raise LocalLifecycleError('local_port_in_use')
    state = _private_dir()
    logs = state / 'logs'
    logs.mkdir(exist_ok=True)
    _protect_acl(logs, directory=True)
    log_path = logs / f'local-web-{port}.log'
    started_at = time.time()
    try:
        with log_path.open('ab') as log:
            _protect_acl(log_path, directory=False) if log_path.exists() else None
            process = subprocess.Popen(
                argv,
                cwd=source_root, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), close_fds=True,
            )
    except (OSError, ValueError):
        raise LocalLifecycleError('local_service_start_failed') from None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LocalLifecycleError('local_service_start_failed')
        health = _health(port)
        ready = (_probe_previous_web(port) if fallback else bool(health and health['build_id'] == expected))
        if ready:
            listener = _listener(port)
            current = _process(listener['pid']) if listener and listener['address'] == '127.0.0.1' else None
            if not process_matches_launch(process.pid, started_at, current,
                                          expected_executable=expected_image, expected_argv=argv):
                raise LocalLifecycleError('local_process_identity_unavailable')
            receipt = _identity(current, port=port, build_id=expected, source_root=source_root)
            if fallback:
                receipt['fallback'] = True
            _private_json(_receipt_path(port), receipt)
            return {'status': 'started' if not fallback else 'rollback_started',
                    'port': port, 'build_id': expected, 'source_commit': receipt['source_commit']}
        time.sleep(0.25)
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    raise LocalLifecycleError('local_health_check_timeout')


def _adopt() -> dict:
    state = _private_dir()
    if _config_path().exists():
        return _load_config()
    listener = _listener(5210)
    if not listener or listener['address'] != '127.0.0.1':
        raise LocalLifecycleError('local_existing_service_not_found')
    process = _process(listener['pid'])
    if process is None:
        raise LocalLifecycleError('local_process_identity_unavailable')
    argv = split_windows_command_line(process['command_line'])
    python_path = ROOT / '.venv' / 'Scripts' / 'python.exe'
    fallback = ROOT.parent / 'v11-real-vault-web-final-20261011'
    if not fallback.is_dir():
        fallback = ROOT
    config = config_from_legacy_argv(argv, source_root=ROOT, python_path=python_path,
                                     rollback_source_root=fallback)
    _private_json(_config_path(), config)
    legacy = _identity(process, port=5210, build_id='legacy-unidentified', source_root=ROOT)
    _private_json(_legacy_path(), legacy)
    return config


def _stop_exact(receipt_path: Path, *, require_health: bool) -> None:
    receipt = _read_json(receipt_path)
    port = receipt.get('port')
    if port not in {5210, 5211}:
        raise LocalLifecycleError('local_process_receipt_invalid')
    listener = _listener(port)
    if not listener:
        receipt_path.unlink(missing_ok=True)
        return
    current = _process(listener['pid'])
    if listener['address'] != '127.0.0.1' or not process_matches(receipt, current):
        raise LocalLifecycleError('local_stop_refused_process_mismatch')
    if require_health and receipt.get('fallback') is True:
        if not _probe_previous_web(port):
            raise LocalLifecycleError('local_stop_refused_health_mismatch')
    elif require_health:
        health = _health(port)
        if not health or health['build_id'] != receipt.get('build_id'):
            raise LocalLifecycleError('local_stop_refused_health_mismatch')
    try:
        os.kill(listener['pid'], signal.SIGTERM)
    except OSError:
        raise LocalLifecycleError('local_stop_failed') from None
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if _listener(port) is None:
            receipt_path.unlink(missing_ok=True)
            return
        time.sleep(0.25)
    raise LocalLifecycleError('local_stop_timeout')


def _handoff() -> dict:
    config = _load_config()
    _validate_runtime(config)
    expected = build_fingerprint(ROOT)
    candidate = _health(5211)
    if not candidate or candidate['build_id'] != expected:
        raise LocalLifecycleError('local_handoff_candidate_not_ready')
    listener = _listener(5210)
    if listener:
        process_receipt = _receipt_path(5210)
        if process_receipt.is_file():
            _stop_exact(process_receipt, require_health=True)
        else:
            legacy = _read_json(_legacy_path())
            current = _process(listener['pid'])
            if listener['address'] != '127.0.0.1' or not process_matches(legacy, current):
                raise LocalLifecycleError('local_handoff_legacy_identity_mismatch')
            try:
                os.kill(listener['pid'], signal.SIGTERM)
            except OSError:
                raise LocalLifecycleError('local_handoff_stop_failed') from None
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and _listener(5210) is not None:
                time.sleep(0.25)
            if _listener(5210) is not None:
                raise LocalLifecycleError('local_handoff_port_not_released')
    try:
        result = _start_service(config, 5210, source_root=ROOT)
    except LocalLifecycleError:
        rollback = Path(config['rollback_source_root'])
        if rollback.resolve() == ROOT.resolve():
            raise LocalLifecycleError('local_handoff_rollback_unavailable') from None
        result = _start_service(config, 5210, source_root=rollback, fallback=True)
    _legacy_path().unlink(missing_ok=True)
    result['status'] = 'handed_off' if result['status'] == 'started' else 'rolled_back_to_e598'
    return result


def _status(port: int) -> dict:
    listener = _listener(port)
    if not listener:
        return {'status': 'offline', 'port': port}
    if listener['address'] != '127.0.0.1':
        return {'status': 'non_loopback_conflict', 'port': port}
    health = _health(port)
    if health:
        return {'status': 'healthy', 'port': port, 'build_id': health['build_id']}
    try:
        receipt = _read_json(_receipt_path(port))
        process = _process(listener['pid'])
        if (receipt.get('fallback') is True and process_matches(receipt, process)
                and _probe_previous_web(port)):
            return {'status': 'rollback_e598', 'port': port, 'build_id': receipt['build_id']}
    except LocalLifecycleError:
        pass
    return {'status': 'unidentified_listener', 'port': port}


def _locate_token() -> dict:
    """Open Explorer with the configured token file selected; never print its contents."""
    config = _load_config()
    path = Path(config['access_token_file'])
    try:
        _read_access_token(path)
    except LocalWebError as error:
        raise LocalLifecycleError('local_access_token_unavailable') from error
    if os.name != 'nt':
        raise LocalLifecycleError('local_token_location_unavailable')
    try:
        subprocess.Popen(['explorer.exe', f'/select,{path}'], close_fds=True)
    except OSError:
        raise LocalLifecycleError('local_token_location_unavailable') from None
    return {'status': 'token_location_opened'}


def _review_scope(config: dict, vault_id: str) -> dict:
    if not isinstance(vault_id, str) or not vault_id:
        raise LocalLifecycleError('local_vault_id_required')
    auth_path = Path(config['authorization'])
    authorization = _read_web_json(auth_path, limit=2 * 1024 * 1024)
    document = authorization.get('authorization_document_path')
    reference = authorization.get('authorization_ref')
    if not isinstance(document, str) or not Path(document).is_absolute() or not isinstance(reference, str):
        raise LocalLifecycleError('local_authorization_invalid')
    arguments = {'instance': Path(config['instance']), 'policy_root': Path(config['policy_root']),
                 'catalog_config': Path(config['catalog_config']), 'authorization_path': auth_path,
                 'authorization_document': Path(document), 'authorization_ref': reference,
                 'vault_id': vault_id}
    changes = pending_authorization_changes(**{key: arguments[key] for key in
        ('instance', 'policy_root', 'catalog_config', 'authorization_path', 'vault_id')})
    if not changes:
        print(json.dumps({'status': 'current', 'vault_id': vault_id, 'pending': 0}, ensure_ascii=False))
        return {'status': 'current', 'pending': 0}
    index = next((item for item in changes if item['native_state'] == 'native-index'), None)
    ordered = ([index] if index else []) + [item for item in changes if item is not index]
    approved = 0
    for item in ordered:
        previous = item['previous_sha256'] or '未授权'
        print(f"待复核 {item['native_state']}  {item['path']}\n旧 SHA256: {previous}\n新 SHA256: {item['current_sha256']}")
        answer = input('仅授权此相对路径的当前 SHA256？输入 y 确认，其它输入跳过: ').strip().casefold()
        if answer != 'y':
            if index is item:
                print('原生索引未批准，跳过依赖该索引的其余文件。')
                break
            continue
        try:
            authorize_current_scope(**arguments, path=item['path'], expected_sha256=item['current_sha256'])
        except LocalWebError as error:
            print(f"未授权 {item['path']}: {error.code}")
            if index is item:
                break
            continue
        approved += 1
        print(f"已按原生可见性与精确路径授权: {item['path']}")
    result = {'status': 'reviewed', 'vault_id': vault_id, 'pending': len(changes), 'approved': approved}
    print(json.dumps(result, ensure_ascii=False))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('adopt', 'start', 'status', 'stop', 'handoff', 'review', 'locate-token'))
    parser.add_argument('--port', type=int, choices=(5210, 5211), default=5210)
    parser.add_argument('--vault-id')
    args = parser.parse_args(argv)
    try:
        if args.action == 'adopt':
            _adopt()
            result = {'status': 'configured', 'config_location': '%LOCALAPPDATA%\\KnowledgeWorkspace'}
        elif args.action == 'status':
            result = _status(args.port)
        elif args.action == 'stop':
            _stop_exact(_receipt_path(args.port), require_health=True)
            result = {'status': 'stopped', 'port': args.port}
        elif args.action == 'handoff':
            result = _handoff()
        elif args.action == 'review':
            config = _load_config()
            result = _review_scope(config, args.vault_id)
        elif args.action == 'locate-token':
            result = _locate_token()
        else:
            config = _load_config() if _config_path().is_file() else _adopt()
            result = _start_service(config, args.port, source_root=ROOT)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (LocalLifecycleError, LocalWebError) as error:
        print(json.dumps({'error': {'code': error.code}}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

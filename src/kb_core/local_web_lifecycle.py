"""Small, local-only lifecycle helpers for the owner Vault Web."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import os
from pathlib import Path
import re
from typing import Sequence


class LocalLifecycleError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def loopback_get(port: int, path: str, *, maximum: int) -> tuple[int, bytes]:
    """Make a bounded HTTP probe to one fixed loopback service and route."""
    if port not in {5210, 5211} or path not in {'/healthz', '/api/vaults'} or type(maximum) is not int or maximum < 1:
        raise LocalLifecycleError('local_probe_target_invalid')
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
    try:
        connection.request('GET', path, headers={'Host': f'127.0.0.1:{port}'})
        response = connection.getresponse()
        return response.status, response.read(maximum + 1)
    finally:
        connection.close()


def split_windows_command_line(command_line: str) -> list[str]:
    """Use Windows' own argv parser when adopting an existing process."""
    if os.name != 'nt' or not isinstance(command_line, str) or not command_line:
        raise LocalLifecycleError('process_command_line_unavailable')
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    command_line_to_argv = shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    command_line_to_argv.restype = ctypes.POINTER(ctypes.c_wchar_p)
    local_free = kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p
    argc = ctypes.c_int()
    argv = command_line_to_argv(command_line, ctypes.byref(argc))
    if not argv:
        raise LocalLifecycleError('process_command_line_unavailable')
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        local_free(argv)


def config_from_legacy_argv(argv: Sequence[str], *, source_root: Path,
                            python_path: Path, rollback_source_root: Path) -> dict:
    """Adopt only the already-running, explicitly read-authorized local service."""
    if not isinstance(argv, (list, tuple)) or len(argv) < 4:
        raise LocalLifecycleError('legacy_service_unrecognized')
    script = str(argv[1]).replace('\\', '/').casefold()
    if not (script == 'tools/kb_display_local.py' or script.endswith('/tools/kb_display_local.py')):
        raise LocalLifecycleError('legacy_service_unrecognized')
    if argv[2] != 'serve':
        raise LocalLifecycleError('legacy_service_unrecognized')
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    for name in ('instance', 'policy-root', 'catalog-config', 'authorization', 'access-token-file'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--read-authorized', action='store_true')
    parser.add_argument('--port', required=True, type=int)
    try:
        args = parser.parse_args(list(argv[3:]))
    except (argparse.ArgumentError, SystemExit, ValueError):
        raise LocalLifecycleError('legacy_service_unrecognized') from None
    if args.read_authorized is not True or args.port != 5210:
        raise LocalLifecycleError('legacy_service_unrecognized')
    values = {
        'instance': Path(args.instance),
        'policy_root': Path(args.policy_root),
        'catalog_config': Path(args.catalog_config),
        'authorization': Path(args.authorization),
        'access_token_file': Path(args.access_token_file),
        'source_root': Path(source_root),
        'python_path': Path(python_path),
        'rollback_source_root': Path(rollback_source_root),
    }
    for path in values.values():
        if not path.is_absolute():
            raise LocalLifecycleError('legacy_service_unrecognized')
    if not values['instance'].is_dir() or not values['policy_root'].is_dir():
        raise LocalLifecycleError('legacy_service_unrecognized')
    if any(not values[name].is_file() for name in
           ('catalog_config', 'authorization', 'access_token_file')):
        raise LocalLifecycleError('legacy_service_unrecognized')
    if (not values['source_root'].is_dir() or not values['rollback_source_root'].is_dir()
            or not (values['source_root'] / 'tools' / 'kb_display_local.py').is_file()
            or not (values['rollback_source_root'] / 'tools' / 'kb_display_local.py').is_file()):
        raise LocalLifecycleError('local_source_unavailable')
    return {
        'schema_version': 'local-web-1',
        'source_root': str(values['source_root'].resolve()),
        'rollback_source_root': str(values['rollback_source_root'].resolve()),
        'python_path': str(values['python_path'].resolve()),
        'instance': str(values['instance'].resolve()),
        'policy_root': str(values['policy_root'].resolve()),
        'catalog_config': str(values['catalog_config'].resolve()),
        'authorization': str(values['authorization'].resolve()),
        'access_token_file': str(values['access_token_file'].resolve()),
        'port': 5210,
    }


def process_matches(receipt: dict, current: dict | None) -> bool:
    """Fail closed on PID reuse, executable changes, or command-line drift."""
    if not isinstance(receipt, dict) or not isinstance(current, dict):
        return False
    command = current.get('command_line')
    if not isinstance(command, str):
        return False
    fingerprint = hashlib.sha256(command.encode('utf-16le')).hexdigest()
    return (
        type(receipt.get('pid')) is int and receipt['pid'] == current.get('pid')
        and isinstance(receipt.get('created'), str) and receipt['created'] == current.get('created')
        and isinstance(receipt.get('executable'), str)
        and receipt['executable'].casefold() == str(current.get('executable', '')).casefold()
        and re.fullmatch(r'[0-9a-f]{64}', str(receipt.get('command_sha256', ''))) is not None
        and receipt['command_sha256'] == fingerprint
    )


def process_matches_command(current: dict | None, *, expected_executable: str,
                            expected_argv: Sequence[str]) -> bool:
    """Verify a live listener still runs the exact configured Web command."""
    if not isinstance(current, dict) or not isinstance(expected_executable, str):
        return False
    if not _same_path(str(current.get('executable', '')), expected_executable):
        return False
    try:
        actual_argv = split_windows_command_line(current.get('command_line', ''))
    except LocalLifecycleError:
        return False
    return _launch_argv_matches(actual_argv, expected_argv, expected_executable)


def _launch_argv_matches(actual: Sequence[str], expected: Sequence[str], executable: str) -> bool:
    if len(actual) != len(expected) or not actual:
        return False
    # Windows can normalize a venv shim's argv[0] to the process image path.
    first_matches = (actual[0].casefold() == str(expected[0]).casefold()
                     or _same_path(actual[0], executable))
    return (first_matches
            and all(left.casefold() == str(right).casefold()
                    for left, right in zip(actual[1:], expected[1:])))


def _same_path(left: str, right: str) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    if left.casefold() == right.casefold():
        return True
    try:
        return Path(left).resolve() == Path(right).resolve()
    except (OSError, RuntimeError):
        return False


def reusable_process_matches(receipt: dict, current: dict | None, *, port: int, build_id: str,
                             expected_executable: str, expected_argv: Sequence[str]) -> bool:
    """Require receipt, live PID identity, build, and exact launch command to agree."""
    return (isinstance(receipt, dict) and receipt.get('port') == port
            and receipt.get('build_id') == build_id and process_matches(receipt, current)
            and process_matches_command(current, expected_executable=expected_executable,
                                        expected_argv=expected_argv))


def process_creation_timestamp(value: str) -> float | None:
    """Parse the stable DMTF timestamp emitted by Win32_Process."""
    if not isinstance(value, str):
        return None
    legacy = re.fullmatch(r'/Date\((\d{10,16})\)/', value)
    if legacy:
        try:
            return int(legacy.group(1)) / 1000
        except (ValueError, OverflowError):
            return None
    match = re.fullmatch(r'(\d{14})\.(\d{6})([+-])(\d{3})', value)
    if not match:
        return None
    try:
        offset = int(match.group(4)) * (1 if match.group(3) == '+' else -1)
        instant = datetime.strptime(match.group(1) + '.' + match.group(2), '%Y%m%d%H%M%S.%f')
        return instant.replace(tzinfo=timezone(timedelta(minutes=offset))).timestamp()
    except (ValueError, OverflowError):
        return None


def process_matches_launch(launcher_pid: int, started_at: float, current: dict | None, *,
                           expected_executable: str, expected_argv: Sequence[str],
                           max_age_seconds: float = 5.0) -> bool:
    """Prove a listener is the exact process launched by this invocation or its venv shim child."""
    if (type(launcher_pid) is not int or launcher_pid <= 0 or not isinstance(current, dict)
            or type(current.get('pid')) is not int or not isinstance(current.get('parent_pid'), int)
            or current.get('pid') == launcher_pid and current.get('parent_pid') == launcher_pid
            or (current.get('pid') != launcher_pid and current.get('parent_pid') != launcher_pid)):
        return False
    if (not isinstance(started_at, (int, float)) or not isinstance(max_age_seconds, (int, float))
            or max_age_seconds <= 0):
        return False
    created = process_creation_timestamp(current.get('created'))
    if created is None or not -0.5 <= created - started_at <= max_age_seconds:
        return False
    if not _same_path(str(current.get('executable', '')), expected_executable):
        return False
    try:
        actual_argv = split_windows_command_line(current.get('command_line', ''))
    except LocalLifecycleError:
        return False
    return _launch_argv_matches(actual_argv, expected_argv, expected_executable)

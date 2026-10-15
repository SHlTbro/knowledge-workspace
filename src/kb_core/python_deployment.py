"""Install the fixed local Python tool bundle into a recoverable isolated root."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from .bindings import BindingError, _path as _safe_path
from .deployment import _io as _safe_io

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/product-realignment-20261007/execution/T22/skillspector-cp314-20261010/artifact-manifest.json"
REQUIREMENTS = ROOT / "docs/product-realignment-20261007/execution/T22/skillspector-cp314-20261010/requirements-hashed.txt"
MANIFEST_SHA256 = "494dce75cc633e50d576afe4329f49b0a64f76f4125945561dab040c5bd92b23"
REQUIREMENTS_SHA256 = "408d4925c4bef02eec9929a6b11a1b3a91b8952e75131726d7b9d6714e2236ee"
PYTHON_SHA256 = "03168c01b7b7491423350e82c26fee71f35b43694d1319d3c668bda6903a0c38"
PACKAGE_COUNT = 65
MAX_TIMEOUT = 900
MAX_WHEEL_BYTES = 128 * 1024 * 1024
MAX_TREE_BYTES = 1024 * 1024 * 1024
MAX_TREE_FILES = 100_000


class DeploymentError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("Controlled Python deployment refused.")


@dataclass(frozen=True)
class Bundle:
    package_count: int
    python_tag: str
    manifest_sha256: str
    requirements_sha256: str
    wheel_hashes: dict[str, str]
    packages: tuple[tuple[str, str], ...]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _regular_bytes(path: Path, limit: int, *, checked_parent: bool = False) -> bytes:
    try:
        path = Path(path) if checked_parent else _safe_path(Path(path))
        io_path = _safe_io(path, checked_parent=checked_parent)
        before = io_path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit or io_path.is_symlink():
            raise DeploymentError("python_deploy_input_not_ordinary")
        with io_path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_nlink)
            if signature(before) != signature(opened):
                raise DeploymentError("python_deploy_input_changed")
            # Bound the allocation by the already-checked file size, not the
            # global limit (the runtime tree may contain thousands of tiny files).
            raw = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
        if len(raw) > limit or signature(before) != signature(after) or signature(before) != signature(_safe_io(path, checked_parent=checked_parent).lstat()):
            raise DeploymentError("python_deploy_input_changed")
        return raw
    except DeploymentError:
        raise
    except BindingError:
        raise DeploymentError("python_deploy_path_invalid") from None
    except OSError:
        raise DeploymentError("python_deploy_input_unavailable") from None


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def validate_bundle(manifest_path: Path, requirements_path: Path, wheelhouse: Path) -> Bundle:
    manifest_raw = _regular_bytes(Path(manifest_path), 256 * 1024)
    requirements_raw = _regular_bytes(Path(requirements_path), 64 * 1024)
    if _sha(manifest_raw) != MANIFEST_SHA256 or _sha(requirements_raw) != REQUIREMENTS_SHA256:
        raise DeploymentError("python_deploy_fixed_input_changed")
    try:
        rows = json.loads(manifest_raw)
    except (ValueError, TypeError):
        raise DeploymentError("python_deploy_manifest_invalid") from None
    if not isinstance(rows, list) or len(rows) != PACKAGE_COUNT:
        raise DeploymentError("python_deploy_manifest_invalid")

    expected: dict[str, tuple[str, str, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise DeploymentError("python_deploy_manifest_invalid")
        name, version, filename = row.get("name"), row.get("version"), row.get("filename")
        digest, size = row.get("sha256"), row.get("bytes")
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name)
                or not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", version)
                or not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".whl")
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not isinstance(size, int) or not 0 < size <= MAX_WHEEL_BYTES):
            raise DeploymentError("python_deploy_manifest_invalid")
        key = _canonical_name(name)
        if key in expected or filename in {entry[0] for entry in expected.values()}:
            raise DeploymentError("python_deploy_manifest_invalid")
        expected[key] = (filename, digest, size)

    parsed: dict[str, tuple[str, str]] = {}
    for raw_line in requirements_raw.decode("utf-8").splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})", raw_line)
        if not match:
            raise DeploymentError("python_deploy_requirements_invalid")
        name, version, digest = match.groups()
        key = _canonical_name(name)
        if key in parsed:
            raise DeploymentError("python_deploy_requirements_invalid")
        parsed[key] = (version, digest)
    if set(parsed) != set(expected) or any(parsed[name] != (next(row["version"] for row in rows if _canonical_name(row["name"]) == name), expected[name][1]) for name in expected):
        raise DeploymentError("python_deploy_requirements_manifest_mismatch")

    wheelhouse = Path(wheelhouse)
    try:
        wheelhouse = _safe_path(wheelhouse)
        info = _safe_io(wheelhouse).lstat()
        if not stat.S_ISDIR(info.st_mode) or _safe_io(wheelhouse).is_symlink():
            raise DeploymentError("python_deploy_wheelhouse_invalid")
        actual_names = {item.name for item in wheelhouse.iterdir()}
    except DeploymentError:
        raise
    except (BindingError, OSError):
        raise DeploymentError("python_deploy_wheelhouse_invalid") from None
    expected_names = {value[0] for value in expected.values()}
    if actual_names != expected_names:
        raise DeploymentError("python_deploy_wheelhouse_incomplete")
    wheel_hashes: dict[str, str] = {}
    for filename, digest, size in expected.values():
        raw = _regular_bytes(wheelhouse / filename, MAX_WHEEL_BYTES)
        if len(raw) != size or _sha(raw) != digest:
            raise DeploymentError("python_deploy_wheel_hash_mismatch")
        wheel_hashes[filename] = digest
    yara = expected.get("yara-python")
    if not yara or "cp314-cp314-win_amd64" not in yara[0]:
        raise DeploymentError("python_deploy_native_wheel_abi_mismatch")
    return Bundle(PACKAGE_COUNT, "cp314", MANIFEST_SHA256, REQUIREMENTS_SHA256,
                  wheel_hashes, tuple(sorted((row["name"], row["version"]) for row in rows)))


def _atomic_json(path: Path, value: dict) -> None:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=".deploy-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(_regular_bytes(path, 4 * 1024 * 1024))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise DeploymentError("python_deploy_state_invalid") from None


@contextmanager
def _locked(path: Path):
    import msvcrt
    try:
        path = _safe_path(path)
        before = _safe_io(path).lstat() if path.exists() else None
        if before is not None and (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1):
            raise DeploymentError("python_deploy_lock_path_invalid")
        with path.open("a+b") as stream:
            opened = os.fstat(stream.fileno())
            current = _safe_io(path).lstat()
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or opened.st_dev != current.st_dev or opened.st_ino != current.st_ino
                    or (before is not None and (before.st_dev != opened.st_dev or before.st_ino != opened.st_ino))):
                raise DeploymentError("python_deploy_lock_path_invalid")
            if stream.seek(0, os.SEEK_END) == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise DeploymentError("python_deploy_busy") from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    except DeploymentError:
        raise
    except BindingError:
        raise DeploymentError("python_deploy_lock_path_invalid") from None
    except OSError:
        raise DeploymentError("python_deploy_lock_failed") from None


def _tree_manifest(root: Path) -> dict[str, str]:
    try:
        root = _safe_path(root)
    except BindingError:
        raise DeploymentError("python_deploy_runtime_path_invalid") from None
    result: dict[str, str] = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        folder = Path(directory)
        before = _safe_io(folder, checked_parent=True).lstat()
        if not stat.S_ISDIR(before.st_mode):
            raise DeploymentError("python_deploy_runtime_link_detected")
        for name in dirs:
            child = folder / name
            info = _safe_io(child, checked_parent=True).lstat()
            if child.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400 or not stat.S_ISDIR(info.st_mode):
                raise DeploymentError("python_deploy_runtime_link_detected")
        for name in files:
            path = folder / name
            raw = _regular_bytes(path, MAX_TREE_BYTES, checked_parent=True)
            total += len(raw)
            if total > MAX_TREE_BYTES or len(result) >= MAX_TREE_FILES:
                raise DeploymentError("python_deploy_runtime_limit")
            result[path.relative_to(root).as_posix()] = _sha(raw)
        after = _safe_io(folder, checked_parent=True).lstat()
        if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
            raise DeploymentError("python_deploy_runtime_changed")
    if not result:
        raise DeploymentError("python_deploy_runtime_empty")
    return result


def _run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, attempt: Path, label: str) -> dict:
    process = None
    interrupted = False
    timed_out = False
    try:
        process = subprocess.Popen([str(value) for value in argv], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding="utf-8", errors="replace")
        try:
            stdout_text, stderr_text = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout_text, stderr_text = process.communicate()
        except KeyboardInterrupt:
            interrupted = True
            process.kill()
            stdout_text, stderr_text = process.communicate()
    except OSError:
        raise DeploymentError("python_deploy_process_start_failed") from None
    stdout = stdout_text.encode("utf-8")
    stderr = stderr_text.encode("utf-8")
    if len(stdout) + len(stderr) > 16 * 1024 * 1024:
        raise DeploymentError("python_deploy_log_limit")
    out_path, err_path = attempt / f"{label}.stdout.txt", attempt / f"{label}.stderr.txt"
    out_path.write_bytes(stdout)
    err_path.write_bytes(stderr)
    return {"step": label, "argv": [str(value) for value in argv], "exit_code": process.returncode,
            "timed_out": timed_out, "interrupted": interrupted, "reaped": process.poll() is not None,
            "stdout": out_path.name, "stdout_sha256": _sha(stdout), "stderr": err_path.name,
            "stderr_sha256": _sha(stderr)}


def _environment() -> dict[str, str]:
    allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT", "LOCALAPPDATA", "APPDATA"}
    result = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", PIP_CONFIG_FILE="NUL",
                  PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INDEX="1")
    return result


def _runtime_smoke(python: Path, packages: tuple[tuple[str, str], ...]) -> list[str]:
    expected = json.dumps(dict(packages), separators=(",", ":"))
    program = (
        "import importlib.metadata as m,json,re,yara; from skillspector.cli import app; "
        f"expected=json.loads({expected!r}); "
        "norm=lambda s:re.sub(r'[-_.]+','-',s).lower(); expected={norm(k):v for k,v in expected.items()}; "
        "installed={norm(d.metadata['Name']):d.version for d in m.distributions() if d.metadata.get('Name') and norm(d.metadata['Name'])!='pip'}; "
        "assert installed==expected,(sorted(set(installed)^set(expected)),installed); "
        "rule=yara.compile(source='rule kbs_smoke { condition: true }'); "
        "assert rule.match(data=b'x'); "
        "print(json.dumps({'python':__import__('sys').version.split()[0],'skillspector':m.version('skillspector'),"
        "'yara_python':m.version('yara-python'),'packages':len(installed),'yara_rule':'matched'}))"
    )
    return [str(python), "-I", "-B", "-c", program]


def deploy_python_tools(output_root: Path, operation_id: str, python_executable: Path,
                        manifest_path: Path, requirements_path: Path, wheelhouse: Path,
                        *, timeout: int = 600) -> dict:
    if not isinstance(operation_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", operation_id):
        raise DeploymentError("python_deploy_operation_invalid")
    if not isinstance(timeout, int) or not 1 <= timeout <= MAX_TIMEOUT:
        raise DeploymentError("python_deploy_timeout_invalid")
    bundle = validate_bundle(manifest_path, requirements_path, wheelhouse)
    python_executable = Path(python_executable)
    python_raw = _regular_bytes(python_executable, 128 * 1024 * 1024)
    if _sha(python_raw) != PYTHON_SHA256:
        raise DeploymentError("python_deploy_host_python_changed")
    try:
        version = subprocess.run([str(python_executable), "-I", "-B", "-c",
                                  "import platform,sys; print(platform.python_implementation()+' '+'.'.join(map(str,sys.version_info[:3])))"],
                                 capture_output=True, text=True, timeout=10, env=_environment(), check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise DeploymentError("python_deploy_host_python_unavailable") from None
    if version != "CPython 3.14.6":
        raise DeploymentError("python_deploy_host_python_version_mismatch")

    raw_root = Path(output_root)
    try:
        root = _safe_path(raw_root)
        parent = _safe_path(root.parent)
    except BindingError:
        raise DeploymentError("python_deploy_output_path_invalid") from None
    if root == Path(root.anchor) or root == ROOT or ROOT.is_relative_to(root) or root.is_relative_to(ROOT):
        raise DeploymentError("python_deploy_output_scope_invalid")
    if not parent.exists() or not stat.S_ISDIR(_safe_io(parent).lstat().st_mode):
        raise DeploymentError("python_deploy_output_parent_invalid")
    marker = root / ".kb-python-deploy.json"
    if root.exists():
        if not stat.S_ISDIR(_safe_io(root).lstat().st_mode) or not marker.is_file() or _read_json(marker) != {"format": "kb-python-deploy-1"}:
            raise DeploymentError("python_deploy_unowned_root")
    else:
        root.mkdir()
        root = _safe_path(root)
        marker = root / ".kb-python-deploy.json"
        _atomic_json(marker, {"format": "kb-python-deploy-1"})

    signature = {"manifest": bundle.manifest_sha256, "requirements": bundle.requirements_sha256,
                 "wheels": bundle.wheel_hashes, "python": PYTHON_SHA256, "python_version": version}
    input_hash = _sha(json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    try:
        folder = _safe_path(root / ("o-" + _sha(operation_id.encode("utf-8"))[:12]))
    except BindingError:
        raise DeploymentError("python_deploy_operation_path_invalid") from None
    if folder.exists():
        if not stat.S_ISDIR(_safe_io(folder).lstat().st_mode):
            raise DeploymentError("python_deploy_operation_path_invalid")
    else:
        folder.mkdir()
        folder = _safe_path(folder)
    journal = folder / "operation.json"
    env = _environment()
    with _locked(root / ".deploy-lock"):
        if journal.exists():
            state = _read_json(journal)
            if state.get("operation_id") != operation_id or state.get("input_hash") != input_hash:
                raise DeploymentError("python_deploy_operation_conflict")
            if state.get("status") == "python_toolset_verified":
                recorded_venv = state.get("venv")
                parts = PurePosixPath(recorded_venv).parts if isinstance(recorded_venv, str) else ()
                if (len(parts) != 3 or parts[0] != folder.name
                        or not re.fullmatch(r"a[1-8]", parts[1]) or parts[2] != "venv"):
                    raise DeploymentError("python_deploy_completed_runtime_changed")
                attempt_number = int(parts[1][1:])
                matching_attempts = [item for item in state.get("attempts", [])
                                     if item.get("number") == attempt_number
                                     and item.get("status") == "python_toolset_verified"]
                if len(matching_attempts) != 1:
                    raise DeploymentError("python_deploy_completed_runtime_changed")
                venv_python = root.joinpath(*parts, "Scripts", "python.exe")
                try:
                    venv_python = _safe_path(venv_python)
                except BindingError:
                    raise DeploymentError("python_deploy_completed_runtime_changed") from None
                actual_manifest = _tree_manifest(venv_python.parent.parent)
                if actual_manifest != state.get("runtime_manifest"):
                    raise DeploymentError("python_deploy_completed_runtime_changed")
                check = subprocess.run([str(venv_python), "-I", "-B", "-m", "pip", "check"],
                                       capture_output=True, text=True, timeout=timeout, env=env)
                if check.returncode != 0:
                    raise DeploymentError("python_deploy_completed_runtime_changed")
                smoke = subprocess.run(_runtime_smoke(venv_python, bundle.packages), capture_output=True,
                                       text=True, timeout=timeout, env=env)
                if smoke.returncode != 0:
                    raise DeploymentError("python_deploy_completed_runtime_changed")
                return state
            if state.get("status") != "pending" or not isinstance(state.get("attempts"), list) or len(state["attempts"]) >= 8:
                raise DeploymentError("python_deploy_state_invalid")
        else:
            orphan_attempt_dirs = []
            for child in folder.iterdir():
                if not re.fullmatch(r"a[1-9][0-9]*", child.name):
                    raise DeploymentError("python_deploy_unowned_operation")
                try:
                    child = _safe_path(child)
                except BindingError:
                    raise DeploymentError("python_deploy_unowned_operation") from None
                if not stat.S_ISDIR(_safe_io(child).lstat().st_mode):
                    raise DeploymentError("python_deploy_unowned_operation")
                orphan_attempt_dirs.append(int(child.name[1:]))
            state = {"operation_id": operation_id, "input_hash": input_hash, "status": "pending",
                     "all_six_ready": False, "package_count": PACKAGE_COUNT, "attempts": [],
                     "orphan_attempt_dirs": sorted(orphan_attempt_dirs)}

        known_numbers = [item["number"] for item in state["attempts"]]
        known_numbers.extend(state.get("orphan_attempt_dirs", []))
        number = max(known_numbers, default=0) + 1
        while True:
            candidate = folder / f"a{number}"
            try:
                candidate = _safe_path(candidate)
            except BindingError:
                raise DeploymentError("python_deploy_attempt_path_invalid") from None
            if not candidate.exists():
                break
            if not stat.S_ISDIR(_safe_io(candidate).lstat().st_mode):
                raise DeploymentError("python_deploy_attempt_path_invalid")
            state.setdefault("orphan_attempt_dirs", []).append(number)
            state["orphan_attempt_dirs"] = sorted(set(state["orphan_attempt_dirs"]))
            number += 1
        if number > 8:
            raise DeploymentError("python_deploy_attempt_limit")
        attempt = folder / f"a{number}"
        record = {"number": number, "status": "preparing", "commands": [], "started_at": datetime.now(timezone.utc).isoformat()}
        state["attempts"].append(record)
        _atomic_json(journal, state)
        try:
            attempt.mkdir()
            attempt = _safe_path(attempt)
        except (OSError, BindingError):
            record.update(status="pending", error_code="python_deploy_attempt_path_invalid",
                          finished_at=datetime.now(timezone.utc).isoformat())
            _atomic_json(journal, state)
            raise DeploymentError("python_deploy_attempt_path_invalid") from None
        venv = attempt / "venv"
        record["status"] = "pending"
        _atomic_json(journal, state)
        try:
            create = _run([python_executable, "-I", "-B", "-m", "venv", "--copies", venv],
                          attempt, env, timeout, attempt, "create-venv")
            record["commands"].append(create)
            _atomic_json(journal, state)
            if create["exit_code"] != 0 or create["timed_out"] or create["interrupted"]:
                raise DeploymentError("python_deploy_step_failed")
            venv_python = venv / "Scripts/python.exe"
            install = _run([venv_python, "-I", "-B", "-m", "pip", "--isolated", "install", "--no-index",
                            "--find-links", wheelhouse, "--no-deps", "--require-hashes", "--disable-pip-version-check",
                            "-r", requirements_path], attempt, env, timeout, attempt, "install-wheels")
            record["commands"].append(install)
            _atomic_json(journal, state)
            if install["exit_code"] != 0 or install["timed_out"] or install["interrupted"]:
                raise DeploymentError("python_deploy_step_failed")
            check = _run([venv_python, "-I", "-B", "-m", "pip", "check"], attempt,
                         env, timeout, attempt, "pip-check")
            record["commands"].append(check)
            _atomic_json(journal, state)
            if check["exit_code"] != 0 or check["timed_out"] or check["interrupted"]:
                raise DeploymentError("python_deploy_dependency_check_failed")
            smoke = _run(_runtime_smoke(venv_python, bundle.packages), attempt,
                         env, timeout, attempt, "runtime-smoke")
            record["commands"].append(smoke)
            _atomic_json(journal, state)
            if smoke["exit_code"] != 0 or smoke["timed_out"] or smoke["interrupted"]:
                raise DeploymentError("python_deploy_runtime_smoke_failed")
            runtime_manifest = _tree_manifest(venv)
            _atomic_json(attempt / "runtime-manifest.json", runtime_manifest)
            record.update(status="python_toolset_verified", finished_at=datetime.now(timezone.utc).isoformat())
            state.update(status="python_toolset_verified", python_version=version, python_sha256=PYTHON_SHA256,
                         manifest_sha256=MANIFEST_SHA256, requirements_sha256=REQUIREMENTS_SHA256,
                         runtime_manifest=runtime_manifest, runtime_manifest_sha256=_sha(json.dumps(runtime_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")),
                         venv=venv.relative_to(root).as_posix())
        except (DeploymentError, OSError, ValueError) as error:
            record.update(status="pending", error_code=getattr(error, "code", "python_deploy_step_failed"),
                          finished_at=datetime.now(timezone.utc).isoformat())
        _atomic_json(journal, state)
        if state["status"] != "python_toolset_verified":
            _atomic_json(folder / "capability-state.json", {"all_six_ready": False, "python_toolset": state["status"]})
            return state
        _atomic_json(folder / "capability-state.json", {"all_six_ready": False, "python_toolset": "installed-and-runtime-verified"})
        return state

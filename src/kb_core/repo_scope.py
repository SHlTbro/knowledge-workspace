"""Run Repomix only over a hash-pinned, explicitly approved file list."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import stat
import tempfile

from .bindings import BindingError, _path as _safe_path
from .contracts import relative_path

MAX_SCOPE_BYTES = 1024 * 1024
MAX_FILES = 2500
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024 * 1024


class RepoScopeError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("Approved repository scope was refused.")


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise RepoScopeError("repo_scope_document_invalid")
        result[key] = value
    return result


def _scope(raw: bytes, expected_sha256: str) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(raw, bytes) or not raw:
        raise RepoScopeError("repo_scope_input_empty")
    if len(raw) > MAX_SCOPE_BYTES:
        raise RepoScopeError("repo_scope_input_limit")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise RepoScopeError("repo_scope_hash_invalid")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise RepoScopeError("repo_scope_hash_mismatch")
    try:
        document = json.loads(raw, object_pairs_hook=_pairs)
    except RepoScopeError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise RepoScopeError("repo_scope_document_invalid") from None
    if (not isinstance(document, dict) or set(document) != {"schema_version", "files"}
            or document.get("schema_version") != "kb-repo-scope-1"
            or not isinstance(document.get("files"), list)
            or not 1 <= len(document["files"]) <= MAX_FILES):
        raise RepoScopeError("repo_scope_document_invalid")
    files = []
    seen = set()
    for row in document["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise RepoScopeError("repo_scope_document_invalid")
        path, file_hash = row["path"], row["sha256"]
        try:
            if not isinstance(path, str) or relative_path(path) != path:
                raise ValueError()
        except (TypeError, ValueError):
            raise RepoScopeError("repo_scope_path_invalid") from None
        if not isinstance(file_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", file_hash):
            raise RepoScopeError("repo_scope_document_invalid")
        key = path.casefold()
        if key in seen:
            raise RepoScopeError("repo_scope_document_invalid")
        seen.add(key)
        files.append({"path": path, "sha256": file_hash})
    return digest, sorted(files, key=lambda row: row["path"].casefold())


def _directory(path: Path) -> Path:
    try:
        resolved = _safe_path(path)
        info = resolved.lstat()
        if not stat.S_ISDIR(info.st_mode) or resolved.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise RepoScopeError("repo_scope_directory_invalid")
        return resolved
    except RepoScopeError:
        raise
    except (BindingError, OSError, TypeError, ValueError):
        raise RepoScopeError("repo_scope_directory_invalid") from None


def _read_file(path: Path, limit: int) -> bytes:
    try:
        path = _safe_path(path)
        before = path.lstat()
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit
                or path.is_symlink() or getattr(before, "st_file_attributes", 0) & 0x400):
            raise RepoScopeError("repo_scope_file_invalid")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if signature(before) != signature(opened):
                raise RepoScopeError("repo_scope_source_changed")
            raw = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
        current = _safe_path(path).lstat()
        if (len(raw) > limit or signature(before) != signature(after)
                or signature(before) != signature(current)):
            raise RepoScopeError("repo_scope_source_changed")
        return raw
    except RepoScopeError:
        raise
    except (BindingError, OSError, TypeError, ValueError):
        raise RepoScopeError("repo_scope_file_unavailable") from None


def _file_path(root: Path, relative: str) -> Path:
    candidate = root.joinpath(*relative.split("/"))
    try:
        for parent in reversed(candidate.parents):
            if parent == root.parent:
                break
            info = parent.lstat()
            if parent.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                raise RepoScopeError("repo_scope_path_invalid")
        if not candidate.resolve(strict=True).is_relative_to(root):
            raise RepoScopeError("repo_scope_path_invalid")
        return candidate
    except RepoScopeError:
        raise
    except (OSError, RuntimeError):
        raise RepoScopeError("repo_scope_file_unavailable") from None


def _output_target(path: Path, source: Path) -> Path:
    try:
        if not isinstance(path, Path) or not path.is_absolute():
            raise RepoScopeError("repo_scope_output_path_invalid")
        parent = _directory(path.parent)
        target = parent / path.name
        if (not path.name or path.name in {".", ".."} or target.exists()
                or target.is_symlink() or target.is_relative_to(source)):
            raise RepoScopeError("repo_scope_output_path_invalid")
        return target
    except RepoScopeError:
        raise
    except (OSError, TypeError, ValueError):
        raise RepoScopeError("repo_scope_output_path_invalid") from None


def _read_output(path: Path, expected: set[str]) -> bytes:
    raw = _read_file(path, MAX_OUTPUT_BYTES)
    try:
        report = json.loads(raw, object_pairs_hook=_pairs)
    except RepoScopeError:
        raise RepoScopeError("repo_scope_output_invalid") from None
    except (UnicodeDecodeError, ValueError, TypeError):
        raise RepoScopeError("repo_scope_output_invalid") from None
    files = report.get("files") if isinstance(report, dict) else None
    if (not isinstance(report, dict) or set(report) != {"fileSummary", "directoryStructure", "files"}
            or not isinstance(report["fileSummary"], dict)
            or not isinstance(report["directoryStructure"], str)
            or not isinstance(files, dict)
            or set(files) != expected or any(not isinstance(content, str) for content in files.values())):
        raise RepoScopeError("repo_scope_output_mismatch")
    return raw


def _publish_exclusive(target: Path, raw: bytes) -> None:
    fd = None
    created = False
    identity = None
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        opened = os.fstat(fd)
        identity = (opened.st_dev, opened.st_ino)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        if created:
            try:
                current = target.lstat()
                if identity == (current.st_dev, current.st_ino):
                    target.unlink()
            except OSError:
                pass
        raise RepoScopeError("repo_scope_output_write_failed") from None
    finally:
        if fd is not None:
            os.close(fd)
        if created:
            try:
                info = target.lstat()
                if ((info.st_dev, info.st_ino) != identity or not stat.S_ISREG(info.st_mode)
                        or info.st_nlink != 1):
                    raise RepoScopeError("repo_scope_output_write_failed")
            except OSError:
                raise RepoScopeError("repo_scope_output_write_failed") from None


def distill(scope_bytes: bytes, expected_scope_sha256: str, source_root: Path,
            output_path: Path, runner) -> dict:
    """Validate, stage, run and publish one exact scope; runner receives only the stage."""
    scope_hash, files = _scope(scope_bytes, expected_scope_sha256)
    source = _directory(Path(source_root))
    target = _output_target(Path(output_path), source)
    originals = {}
    total = 0
    for row in files:
        original = _read_file(_file_path(source, row["path"]), MAX_FILE_BYTES)
        digest = hashlib.sha256(original).hexdigest()
        if digest != row["sha256"]:
            raise RepoScopeError("repo_scope_file_hash_mismatch")
        total += len(original)
        if total > MAX_TOTAL_BYTES:
            raise RepoScopeError("repo_scope_total_limit")
        originals[row["path"]] = original

    try:
        with tempfile.TemporaryDirectory(prefix="kb-repo-scope-") as temp_name:
            temp_root = Path(temp_name)
            stage = temp_root / "input"
            stage.mkdir()
            for relative, raw in originals.items():
                destination = stage.joinpath(*relative.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(raw)
                try:
                    destination.chmod(0o444)
                except OSError:
                    pass
            result_path = temp_root / "repomix.json"
            runner(stage, result_path)
            output = _read_output(result_path, set(originals))
            for row in files:
                current = _read_file(_file_path(source, row["path"]), MAX_FILE_BYTES)
                if hashlib.sha256(current).hexdigest() != row["sha256"]:
                    raise RepoScopeError("repo_scope_source_changed")
            _publish_exclusive(target, output)
    except RepoScopeError:
        raise
    except Exception:
        raise RepoScopeError("repo_scope_runner_failed") from None
    # The temporary stage contains user-approved source text; the context
    # manager removes it whether Repomix succeeds, fails, or times out.
    return {"status": "scoped_distillation_complete", "scope_sha256": scope_hash,
            "files": [row["path"] for row in files], "file_count": len(files),
            "output_sha256": hashlib.sha256(output).hexdigest(), "output_bytes": len(output)}

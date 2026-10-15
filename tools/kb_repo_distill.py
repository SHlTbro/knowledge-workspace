"""Hash-pinned Repomix entry for explicitly authorized repository files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kb_core import deployment
from kb_core.contracts import relative_path
from kb_core.repo_scope import MAX_SCOPE_BYTES, RepoScopeError, _directory, _read_file, distill

REPOMIX_PACKAGE_SHA256 = "1985a864777c3b16ec8f76eaebc0928996fe1c9836fe608c0364f9a69179bba9"
REPOMIX_LOCK_SHA256 = "97238870258c9f3bd61d2a0fb4aa831d0df6573a863316338e80c80eef7ed013"
NODE_SHA256 = "9a4eb5f1c29c6a2e93852ead46b999e284a6a5ca8bab4d4e241d587d025a52de"
REPOMIX_VERSION = "1.18.0"
MAX_TIMEOUT = 600
MAX_PAYLOAD_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_PAYLOAD_FILES = 20000
MAX_PAYLOAD_BYTES = 256 * 1024 * 1024
MAX_PAYLOAD_FILE_BYTES = 64 * 1024 * 1024


def _unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise RepoScopeError("repo_scope_tool_manifest_invalid")
        result[key] = value
    return result


def _verify_payload_tree(package_root: Path, manifest_path: Path,
                         expected_manifest_sha256: str) -> None:
    """Verify the installed Repomix tree against T22's separately pinned payload manifest."""
    if not isinstance(expected_manifest_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256):
        raise RepoScopeError("repo_scope_tool_manifest_mismatch")
    root = _directory(package_root)
    manifest_parent = _directory(manifest_path.parent)
    operation_root = _directory(manifest_parent.parent)
    try:
        attempt_name = manifest_parent.relative_to(operation_root).as_posix()
        install_prefix = root.relative_to(operation_root).as_posix()
    except ValueError:
        raise RepoScopeError("repo_scope_tool_manifest_invalid") from None
    if (manifest_path.name != "payload-manifest.json"
            or not re.fullmatch(r"a[1-9][0-9]*", attempt_name)
            or install_prefix != attempt_name + "/r"):
        raise RepoScopeError("repo_scope_tool_manifest_invalid")
    raw = _read_file(manifest_path, MAX_PAYLOAD_MANIFEST_BYTES)
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise RepoScopeError("repo_scope_tool_manifest_mismatch")
    try:
        manifest = json.loads(raw, object_pairs_hook=_unique_object)
    except RepoScopeError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise RepoScopeError("repo_scope_tool_manifest_invalid") from None
    if not isinstance(manifest, dict) or not 1 <= len(manifest) <= MAX_PAYLOAD_FILES:
        raise RepoScopeError("repo_scope_tool_manifest_invalid")

    prefix = install_prefix + "/node_modules/"
    sibling_prefix = attempt_name + "/d/node_modules/"
    expected = {}
    for relative, digest in manifest.items():
        try:
            if not isinstance(relative, str) or relative_path(relative) != relative:
                raise ValueError()
        except (TypeError, ValueError):
            raise RepoScopeError("repo_scope_tool_manifest_invalid") from None
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RepoScopeError("repo_scope_tool_manifest_invalid")
        if relative.startswith(prefix):
            expected[relative[len(install_prefix) + 1:]] = digest
        elif not relative.startswith(sibling_prefix):
            raise RepoScopeError("repo_scope_tool_manifest_invalid")
    cli_relative = "node_modules/repomix/bin/repomix.cjs"
    if cli_relative not in expected:
        raise RepoScopeError("repo_scope_tool_manifest_invalid")

    node_modules = root / "node_modules"
    node_root = _directory(node_modules)
    actual = {}
    total = 0
    try:
        for directory, dirs, names in os.walk(node_root, followlinks=False):
            current = Path(directory)
            current_info = current.lstat()
            if (not current_info or not current.is_dir() or current.is_symlink()
                    or getattr(current_info, "st_file_attributes", 0) & 0x400):
                raise RepoScopeError("repo_scope_tool_payload_mismatch")
            for name in dirs:
                child = current / name
                info = child.lstat()
                if (not stat.S_ISDIR(info.st_mode) or child.is_symlink()
                        or getattr(info, "st_file_attributes", 0) & 0x400):
                    raise RepoScopeError("repo_scope_tool_payload_mismatch")
            for name in names:
                child = current / name
                content = _read_file(child, MAX_PAYLOAD_FILE_BYTES)
                relative = child.relative_to(root).as_posix()
                actual[relative] = hashlib.sha256(content).hexdigest()
                total += len(content)
                if total > MAX_PAYLOAD_BYTES or len(actual) > MAX_PAYLOAD_FILES:
                    raise RepoScopeError("repo_scope_tool_payload_limit")
    except RepoScopeError:
        raise
    except OSError:
        raise RepoScopeError("repo_scope_tool_payload_mismatch") from None
    if actual != expected:
        raise RepoScopeError("repo_scope_tool_payload_mismatch")


def _tool_paths(package_root: Path, manifest_path: Path,
                expected_manifest_sha256: str) -> tuple[Path, Path]:
    root = _directory(package_root)
    package_raw = _read_file(root / "package.json", 64 * 1024)
    lock_raw = _read_file(root / "package-lock.json", 4 * 1024 * 1024)
    if (hashlib.sha256(package_raw).hexdigest() != REPOMIX_PACKAGE_SHA256
            or hashlib.sha256(lock_raw).hexdigest() != REPOMIX_LOCK_SHA256):
        raise RepoScopeError("repo_scope_tool_lock_mismatch")
    cli = root / "node_modules/repomix/bin/repomix.cjs"
    cli_raw = _read_file(cli, 32 * 1024 * 1024)
    del cli_raw
    _verify_payload_tree(root, manifest_path, expected_manifest_sha256)
    node_raw = _read_file(deployment.NODE, 128 * 1024 * 1024)
    if hashlib.sha256(node_raw).hexdigest() != NODE_SHA256:
        raise RepoScopeError("repo_scope_node_runtime_mismatch")
    return deployment.NODE, cli


def _runner(package_root: Path, manifest_path: Path,
            expected_manifest_sha256: str, timeout: int):
    def run(staged_root: Path, output_path: Path) -> None:
        node, cli = _tool_paths(package_root, manifest_path, expected_manifest_sha256)
        allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update(NO_COLOR="1", DO_NOT_TRACK="1", PYTHONDONTWRITEBYTECODE="1")
        config = output_path.with_name("repomix-config.json")
        config.write_text("{}", encoding="utf-8")
        try:
            result = subprocess.run(
                [str(node), str(cli), str(staged_root), "--config", str(config),
                 "--output", str(output_path),
                 "--style", "json", "--quiet"],
                cwd=staged_root, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RepoScopeError("repo_scope_runner_timeout") from None
        except OSError:
            raise RepoScopeError("repo_scope_runner_unavailable") from None
        if result.returncode != 0:
            raise RepoScopeError("repo_scope_runner_failed")
    return run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repomix-root", type=Path, required=True,
                        help="the isolated T22 install root containing package.json, lockfile and node_modules")
    parser.add_argument("--payload-manifest", type=Path, required=True,
                        help="T22 payload-manifest.json for the operation containing this install")
    parser.add_argument("--expected-payload-manifest-sha256", required=True,
                        help="manifest hash pinned separately from the manifest file")
    parser.add_argument("--scope-file", type=Path,
                        help="read exact scope bytes from an ordinary local file instead of stdin")
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= MAX_TIMEOUT:
        print(json.dumps({"error": {"code": "repo_scope_timeout_invalid"}}))
        return 2
    try:
        scope = (_read_file(args.scope_file, MAX_SCOPE_BYTES) if args.scope_file
                 else sys.stdin.buffer.read(MAX_SCOPE_BYTES + 1))
        if not scope:
            raise RepoScopeError("repo_scope_input_empty")
        # distill validates the owner-pinned scope and all file hashes before
        # invoking this runner or inspecting the installed package.
        result = distill(scope, args.expected_scope_sha256, args.source_root,
                         args.output, _runner(args.repomix_root, args.payload_manifest,
                                              args.expected_payload_manifest_sha256,
                                              args.timeout))
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except RepoScopeError as error:
        print(json.dumps({"error": {"code": error.code}}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

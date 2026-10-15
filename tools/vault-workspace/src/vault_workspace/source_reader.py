"""Read explicitly pinned source evidence; never import or execute its contents.

Opt-in adapter configuration comes from the accepted Registry snapshot. This
keeps a live Vault metadata edit from silently removing an operator read block.
It adds no indexed assets, new Binding shape or Factory behavior.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from . import reader, inspiration_visibility
from .safety import relative_path

ADAPTER_ID = "inspiration-pinned-v1"
_CODE = {".py", ".ts", ".tsx", ".js", ".c", ".h", ".sol"}
_TEXT = {".md": "markdown", ".json": "json", ".txt": "text", ".toml": "text"}


def configuration(descriptor: dict) -> dict | None:
    value = descriptor.get("extensions", {}).get("workspace_source_reader")
    if value is None:
        return None
    required = {"adapter_id", "manifest_ref", "manifest_sha256", "blocked_read_paths"}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - {'allowed_read_paths'}:
        raise ValueError("Invalid pinned-source adapter configuration")
    if value["adapter_id"] != ADAPTER_ID:
        raise ValueError("Pinned-source adapter is not installed")
    relative_path(value["manifest_ref"])
    if not isinstance(value["manifest_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["manifest_sha256"]):
        raise ValueError("Invalid accepted source manifest fingerprint")
    blocked = value["blocked_read_paths"]
    if not isinstance(blocked, list) or len(blocked) > reader.MAX_SCAN_FILES:
        raise ValueError("Invalid pinned-source read blocks")
    for path in blocked:
        relative_path(path)
    if 'allowed_read_paths' in value:
        allowed = value['allowed_read_paths']
        if not isinstance(allowed, list) or len(allowed) > reader.MAX_SCAN_FILES:
            raise ValueError('Invalid pinned-source allowlist')
        seen = set()
        for path in allowed:
            normalized = relative_path(path).casefold()
            if normalized in seen:
                raise ValueError('Duplicate pinned-source allowlist path')
            seen.add(normalized)
    return value


def _pins(root: Path, config: dict) -> tuple[dict, str]:
    raw, text = reader._load(root, config["manifest_ref"])
    if hashlib.sha256(raw).hexdigest() != config["manifest_sha256"]:
        raise ValueError("Accepted source manifest changed; review before reading")
    try:
        manifest = json.loads(text)
    except (ValueError, RecursionError):
        raise ValueError("Invalid pinned-source manifest") from None
    if not isinstance(manifest, dict) or len(manifest) > 1000:
        raise ValueError("Invalid pinned-source manifest")
    base = PurePosixPath(config["manifest_ref"]).parent
    pins = {}
    for slug, project in manifest.items():
        relative_path(slug)
        if "/" in slug or not isinstance(project, dict):
            raise ValueError("Invalid source project")
        commit, repo = project.get("commit"), project.get("repo")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid source commit")
        if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Invalid source repository")
        files = project.get("files")
        if not isinstance(files, dict):
            raise ValueError("Invalid pinned file list")
        for original, item in files.items():
            relative_path(original)
            path = relative_path((base / slug / commit[:10] / original).as_posix())
            if not isinstance(item, dict):
                raise ValueError("Invalid source fingerprint")
            size, digest = item.get("bytes"), item.get("sha256")
            if type(size) is not int or not 0 <= size <= reader.MAX_FILE_BYTES or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Invalid source fingerprint")
            if path.casefold() in pins or len(pins) >= reader.MAX_SCAN_FILES:
                raise ValueError("Duplicate or excessive pinned files")
            pins[path.casefold()] = {"path": path, "repo": repo, "commit": commit, "original": original,
                                    "size": size, "sha256": digest}
    if 'allowed_read_paths' in config:
        allowed = {path.casefold() for path in config['allowed_read_paths']}
        if not allowed <= pins.keys():
            raise ValueError('Reviewed source allowlist is not contained in the accepted manifest')
        pins = {path: pin for path, pin in pins.items() if path in allowed}
    return pins, hashlib.sha256(raw).hexdigest()


def check_read_path(path: str, descriptor: dict, root: Path | None = None) -> None:
    config = configuration(descriptor)
    if config is not None and relative_path(path).casefold() in {value.casefold() for value in config["blocked_read_paths"]}:
        raise PermissionError("This source path is blocked by the accepted private-content review")
    if config is not None and 'allowed_read_paths' in config and path.casefold().startswith('sources/') and path not in inspiration_visibility.NAVIGATION:
        if relative_path(path).casefold() not in {value.casefold() for value in config['allowed_read_paths']}:
            raise PermissionError('Source is outside the accepted read allowlist')
    if inspiration_visibility.enabled(descriptor):
        if root is None:
            raise ValueError('Visibility adapter requires the current Vault root')
        inspiration_visibility.check_path(root, path, descriptor)
        if path.startswith('sources/') and path not in inspiration_visibility.NAVIGATION:
            if config is None or relative_path(path).casefold() not in _pins(root, config)[0]:
                raise PermissionError('Source is not in the accepted pinned manifest')


def filter_scan(scan: dict, descriptor: dict, root: Path | None = None) -> dict:
    if inspiration_visibility.enabled(descriptor):
        if root is None:
            raise ValueError('Visibility adapter requires the current Vault root')
        scan = inspiration_visibility.filter_scan(root, scan, descriptor)
    config = configuration(descriptor)
    if config is None:
        return scan
    blocked = {value.casefold() for value in config["blocked_read_paths"]}
    documents, issues = [], list(scan["issues"])
    for original in scan["documents"]:
        if original["path"].casefold() in blocked:
            issues.append({"code": "private_read_block", "path": original["path"], "message": "Excluded by accepted private-content review"})
            continue
        if ('allowed_read_paths' in config and original['path'].casefold().startswith('sources/')
                and original['path'] not in inspiration_visibility.NAVIGATION
                and original['path'].casefold() not in {path.casefold() for path in config['allowed_read_paths']}):
            issues.append({'code': 'source_not_reviewed', 'path': original['path'], 'message': 'Excluded by accepted source allowlist'})
            continue
        item = dict(original)
        if "annotations" in item:
            item["annotations"] = dict(item["annotations"], attachments=[path for path in item["annotations"].get("attachments", []) if path.casefold() not in blocked])
        documents.append(item)
    return {"documents": documents, "issues": issues}


def read_resource(root: Path, path: str, descriptor: dict, budget: int = 6000, *, full_document=False) -> dict | None:
    """Return a pinned projection or None for the existing generic Reader.

    Explicit read blocks run before fallback, including Markdown/document reads.
    Unlisted code remains unsupported. No heading, offset or execution is added.
    """
    path = relative_path(path)
    check_read_path(path, descriptor, root)
    config = configuration(descriptor)
    if config is None:
        return _published_generic(root, path, descriptor, budget, full_document)
    if not full_document and (type(budget) is not int or not 1 <= budget <= reader.MAX_READ_CHARACTERS):
        raise ValueError("Read budget must be between 1 and 20000 characters")
    pins, manifest_hash = _pins(root, config)
    pin = pins.get(path.casefold())
    if pin is None:
        return _published_generic(root, path, descriptor, budget, full_document)
    path = pin["path"]
    extension = PurePosixPath(path).suffix.lower()
    format_name = "code" if extension in _CODE else _TEXT.get(extension)
    if format_name is None:
        raise ValueError("Pinned source format is not installed")
    raw, text = reader._load(root, path)
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != pin["size"] or digest != pin["sha256"]:
        raise ValueError("Pinned source bytes changed; review the manifest before reading")
    value = {"path": path, "title": PurePosixPath(path).name, "format": format_name,
             "text": text if full_document else text[:budget], "source_hash": digest,
             "source_locator": {"kind": "pinned-source", "path": path, "repo": pin["repo"],
                                "pinned_commit": pin["commit"], "original_path": pin["original"],
                                "manifest_path": config["manifest_ref"], "manifest_hash": manifest_hash},
             "truncated": False if full_document else len(text) > budget, "budget_unit": "characters"}
    if full_document:
        value["total_characters"] = len(text)
    return value


def _published_generic(root, path, descriptor, budget, full_document):
    if not inspiration_visibility.enabled(descriptor):
        return None
    value = reader.read_document(root, path) if full_document else reader.read(root, path, budget)
    # A writer may start between the initial gate and the byte fetch. Never
    # return newly unpublished content on the strength of a previous check.
    check_read_path(path, descriptor, root)
    raw, _ = reader._load(root, path)
    if hashlib.sha256(raw).hexdigest() != value['source_hash']:
        raise PermissionError('Publication changed during read; retry after refresh')
    return value

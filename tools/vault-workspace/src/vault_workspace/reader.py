"""Read-only, domain-neutral projections of explicitly bound local content."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

import yaml

from vault_workspace.safety import relative_path

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_SCAN_FILES = 10_000
MAX_READ_CHARACTERS = 20_000
_TEXT_EXTENSIONS = {".md": "markdown", ".json": "json", ".txt": "text"}


def _relative(value: str, *, allow_root: bool = False) -> str:
    return relative_path(value, allow_dot=allow_root)


def _linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_path(root: Path, relative: str, *, allow_root: bool = False) -> Path:
    relative = _relative(relative, allow_root=allow_root)
    root = Path(root).absolute()
    try:
        if _linked(root):
            raise ValueError("Vault root must not be a link")
        if not root.is_dir():
            raise ValueError("Vault root must be a directory")
        target = root
        for component in ([] if relative == "." else relative.split("/")):
            target = target / component
            if _linked(target):
                raise ValueError("Links and reparse points are not readable")
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError("Path escapes the Vault")
        return target
    except FileNotFoundError:
        raise FileNotFoundError(f"Path not found: {relative}") from None
    except PermissionError:
        raise ValueError(f"Path is not readable: {relative}") from None


def _load(root: Path, relative: str) -> tuple[bytes, str]:
    target = _safe_path(root, relative)
    if not target.is_file():
        raise ValueError("Expected a regular text file")
    try:
        # A bounded read also handles files growing after their size check.
        with target.open("rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except OSError:
        raise ValueError(f"File is not readable: {relative}") from None
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("File exceeds the 2 MiB reader limit")
    try:
        return raw, raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File is not UTF-8 text") from None


def _title(text: str, relative: str, format_name: str, title_key: str = "title") -> str:
    fallback = PurePosixPath(relative).stem
    if format_name == "json":
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, RecursionError):
            raise ValueError("Invalid JSON document") from None
        if isinstance(value, dict):
            title = value.get(title_key) or value.get("name")
            if isinstance(title, (str, int, float)):
                return str(title)[:500]
        return fallback
    # Frontmatter is optional metadata, never a domain-schema requirement.
    if text.startswith("---\n") or text.startswith("---\r\n"):
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
        if match and len(match.group(1)) <= 16_384:
            try:
                metadata = yaml.safe_load(match.group(1))
            except (yaml.YAMLError, RecursionError):
                metadata = None
            if isinstance(metadata, dict) and isinstance(metadata.get("title"), str):
                return metadata["title"][:500]
    heading = re.search(r"^#\s+(.+?)\s*#*\s*$", text, re.MULTILINE)
    return heading.group(1)[:500] if heading else fallback


def _document(root: Path, relative: str, binding: dict, *, directory: bool = False) -> dict:
    raw, text = _load(root, relative)
    extension = PurePosixPath(relative).suffix.lower()
    format_name = _TEXT_EXTENSIONS.get(extension)
    if format_name is None:
        raise ValueError("Unsupported text format")
    title = _title(text, relative, format_name, binding.get("title_key") or "title")
    # JSON escape spelling is a storage choice, not a searchable domain fact.
    # Keep the hash bound to original bytes while indexing decoded field values.
    search_text = json.dumps(json.loads(text), ensure_ascii=False, indent=2) if format_name == "json" else text
    locator = {"kind": "file", "path": relative}
    if directory:
        locator.update(kind="directory-entry", entity_path=PurePosixPath(relative).parent.as_posix())
    return {"path": relative, "title": title, "type_key": binding.get("type_key"),
            "format": "directory" if directory else format_name, "search_text": search_text,
            "source_hash": hashlib.sha256(raw).hexdigest(), "source_locator": locator}


def scan(root: Path, bindings: list[dict]) -> dict:
    """Return known documents and explicit coverage issues, without source writes.

    A directory containing its configured entry file is one entity; descendant
    files are attachments, not additional knowledge assets. Overlapping bindings
    are reported rather than silently double-counted.
    """
    root = Path(root).absolute()
    _safe_path(root, ".", allow_root=True)
    documents: dict[str, dict] = {}
    issues: list[dict] = []
    visited_files = 0

    def issue(code: str, path: str, message: str) -> None:
        issues.append({"code": code, "path": path, "message": message})

    def enumerate_files(base: Path):
        nonlocal visited_files
        pending = [base]
        while pending:
            current = pending.pop()
            rel = current.relative_to(root).as_posix()
            try:
                _safe_path(root, rel, allow_root=True)
                children = sorted(current.iterdir(), key=lambda p: p.name.casefold())
            except (OSError, ValueError):
                issue("unreadable_path", rel, "Directory could not be enumerated safely")
                continue
            for child in children:
                child_rel = child.relative_to(root).as_posix()
                try:
                    if _linked(child):
                        issue("unsafe_path", child_rel, "Links and reparse points are excluded")
                    elif child.is_dir():
                        pending.append(child)
                    elif child.is_file():
                        visited_files += 1
                        if visited_files > MAX_SCAN_FILES:
                            raise ValueError("Scan exceeds the 10000-file limit")
                        yield child
                except OSError:
                    issue("unreadable_path", child_rel, "File could not be inspected")

    def add(relative: str, binding: dict, *, directory=False) -> dict | None:
        if relative in documents:
            issue("overlapping_binding", relative, "This content is already covered by another binding")
            return None
        try:
            document = _document(root, relative, binding, directory=directory)
        except (ValueError, FileNotFoundError) as exc:
            code = "invalid_json" if str(exc) == "Invalid JSON document" else "unreadable_document"
            issue(code, relative, str(exc))
            return None
        documents[relative] = document
        return document

    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError("Reader bindings must be objects")
        relative = _relative(binding.get("root"), allow_root=True)
        reader = binding.get("reader")
        if reader not in {"markdown", "json", "directory"}:
            issue("unsupported_reader", relative, "No installed Reader supports this binding")
            continue
        try:
            base = _safe_path(root, relative, allow_root=True)
            if not base.is_dir():
                issue("invalid_root", relative, "Reader root is not a directory")
                continue
        except FileNotFoundError:
            issue("missing_root", relative, "Reader root does not exist")
            continue
        except ValueError:
            issue("unsafe_path", relative, "Reader root is not safe to enumerate")
            continue
        files = list(enumerate_files(base))
        if reader != "directory":
            extension = ".md" if reader == "markdown" else ".json"
            for path in files:
                rel = path.relative_to(root).as_posix()
                if path.suffix.lower() == extension:
                    add(rel, binding)
                else:
                    issue("unsupported_format", rel, f"The {reader} Reader does not index this file format")
            continue
        entry_name = _relative(binding.get("entry_file") or "index.md")
        if len(PurePosixPath(entry_name).parts) != 1 or PurePosixPath(entry_name).suffix.lower() not in {".md", ".json"}:
            raise ValueError("Directory entry_file must be one Markdown or JSON file name")
        entries = sorted((p for p in files if p.name == entry_name), key=lambda p: (len(p.parts), p.as_posix()))
        entity_roots: list[Path] = []
        for entry in entries:
            if any(entry.is_relative_to(parent) for parent in entity_roots):
                continue
            entity_roots.append(entry.parent)
            document = add(entry.relative_to(root).as_posix(), binding, directory=True)
            if document is not None:
                document["annotations"] = {"attachments": sorted(
                    p.relative_to(root).as_posix() for p in files if p != entry and p.is_relative_to(entry.parent)
                )}
        for path in files:
            if not any(path.is_relative_to(parent) for parent in entity_roots):
                issue("missing_directory_entry", path.relative_to(root).as_posix(), "File has no containing directory entity entry")
    return {"documents": [documents[key] for key in sorted(documents)], "issues": issues}


def read(root: Path, path: str, budget: int = 6000) -> dict:
    """Read current source bytes with an explicit character budget and hash."""
    if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= MAX_READ_CHARACTERS:
        raise ValueError("Read budget must be between 1 and 20000 characters")
    path = _relative(path)
    format_name = _TEXT_EXTENSIONS.get(PurePosixPath(path).suffix.lower())
    if format_name is None:
        raise ValueError("Unsupported text format")
    raw, text = _load(Path(root), path)
    return {"path": path, "title": _title(text, path, format_name), "format": format_name,
            "text": text[:budget], "source_hash": hashlib.sha256(raw).hexdigest(),
            "source_locator": {"kind": "file", "path": path}, "truncated": len(text) > budget,
            "budget_unit": "characters"}


def read_document(root: Path, path: str) -> dict:
    """Human document view, bounded by the same 2 MiB file/path protections.

    This does not change the public Agent read budget or add chapter/offset read.
    """
    path = _relative(path)
    format_name = _TEXT_EXTENSIONS.get(PurePosixPath(path).suffix.lower())
    if format_name is None:
        raise ValueError("Unsupported text format")
    raw, text = _load(Path(root), path)
    return {"path": path, "title": _title(text, path, format_name), "format": format_name,
            "text": text, "source_hash": hashlib.sha256(raw).hexdigest(),
            "source_locator": {"kind": "file", "path": path}, "truncated": False,
            "total_characters": len(text), "budget_unit": "characters"}

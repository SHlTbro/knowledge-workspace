"""Build an explicitly approved offline public snapshot; never reads a Vault root.

The approval hash binds a human-reviewed input; it is not a digital signature or
a substitute for permission review. No private input is included in this repo.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/kb_core/display_static"
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".toml", ".py", ".js", ".css"}
NOTICE = "真实内容的获准公开快照｜非实时｜仅本范围"


class BuildError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value)


def _strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _path(value: object, *, directory: bool = False) -> str:
    if not isinstance(value, str):
        raise BuildError("resource_path_invalid")
    candidate = value.removesuffix("/") if directory else value
    if (not candidate or re.search(r"[\\:\x00-\x1f?#%]", candidate)
            or any(part in {"", ".", "..", ".git", ".runtime"} for part in candidate.split("/"))
            or any(part.endswith((".", " ")) for part in candidate.split("/"))):
        raise BuildError("resource_path_invalid")
    if not directory and Path(candidate).suffix.lower() not in TEXT_EXTENSIONS:
        raise BuildError("resource_format_not_text")
    return value


def _read(path: Path, limit: int) -> tuple[bytes, dict]:
    try:
        if path.is_symlink() or path.stat().st_size > limit:
            raise BuildError("input_not_bounded_regular_file")
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BuildError("input_unreadable_or_invalid_json") from error
    if not isinstance(value, dict):
        raise BuildError("input_object_required")
    return raw, value


def _validate(source: Path, approval: Path) -> tuple[dict, dict]:
    raw, snapshot = _read(source, 64 * 1024 * 1024)
    _, receipt = _read(approval, 4 * 1024 * 1024)
    if (set(receipt) != {"status", "scope", "snapshot_sha256", "approved_files", "approval_hash"}
            or receipt["status"] != "APPROVED_FOR_PUBLIC"
            or receipt["scope"] != "public-real-vault-snapshot"):
        raise BuildError("explicit_public_approval_required")
    unsigned = {key: value for key, value in receipt.items() if key != "approval_hash"}
    if receipt["approval_hash"] != _sha(_canonical(unsigned)):
        raise BuildError("approval_hash_mismatch")
    if receipt["snapshot_sha256"] != _sha(raw):
        raise BuildError("snapshot_hash_mismatch")
    if (set(snapshot) != {"format", "generated_at", "vaults"}
            or snapshot["format"] != "kb-public-snapshot-1"
            or not isinstance(snapshot["vaults"], list) or len(snapshot["vaults"]) != 6):
        raise BuildError("snapshot_contract_invalid")
    timestamp = snapshot["generated_at"]
    if not isinstance(timestamp, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", timestamp):
        raise BuildError("snapshot_time_invalid")
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as error:
        raise BuildError("snapshot_time_invalid") from error
    # A conservative leak tripwire, in addition to the human content/rights review.
    all_text = "\n".join(_strings(snapshot))
    if re.search(r"(?:(?<![A-Za-z0-9_])[A-Za-z]:[\\/](?!>)|\\\\[^\\]+\\|(?<![A-Za-z0-9_])/(?:Users|home|private|mnt)/)", all_text):
        raise BuildError("machine_path_forbidden")
    if re.search(r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:gh[pousr]_[A-Za-z0-9]{16,})|"
                 r"github_pat_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_-]{16,}|"
                 r"(?:api[_-]?key|principal[_-]?key|access[_-]?token|password|authorization)"
                 r"\s*[\"']?\s*[:=]\s*[\"']?\S{8,})", all_text, re.I):
        raise BuildError("possible_credential_forbidden")
    ids, approved = set(), []
    for vault in snapshot["vaults"]:
        if not isinstance(vault, dict) or set(vault) != {"vault_id", "name", "purpose", "entry_points", "structure", "agent_prompt", "resources"}:
            raise BuildError("vault_contract_invalid")
        identity = vault["vault_id"]
        if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in ids:
            raise BuildError("vault_id_invalid")
        ids.add(identity)
        if (not _text(vault["name"]) or not _text(vault["agent_prompt"])
                or not isinstance(vault["purpose"], list) or not vault["purpose"]
                or not all(_text(item) for item in vault["purpose"])
                or not isinstance(vault["structure"], list)
                or not isinstance(vault["entry_points"], list)
                or not isinstance(vault["resources"], list) or len(vault["resources"]) > 10000):
            raise BuildError("vault_fields_invalid")
        for value in vault["structure"]:
            _path(value, directory=True)
        for entry in vault["entry_points"]:
            if not isinstance(entry, dict) or set(entry) != {"label", "path"} or not _text(entry["label"]):
                raise BuildError("entry_invalid")
            _path(entry["path"], directory=True)
        paths = set()
        for resource in vault["resources"]:
            if not isinstance(resource, dict) or set(resource) != {"path", "content", "source_sha256", "export_sha256"}:
                raise BuildError("resource_contract_invalid")
            relative = _path(resource["path"])
            if relative.casefold() in paths:
                raise BuildError("duplicate_resource")
            paths.add(relative.casefold())
            if (not _text(resource["content"]) or len(resource["content"].encode("utf-8")) > 256 * 1024
                    or not all(isinstance(resource[key], str) and SHA.fullmatch(resource[key]) for key in ("source_sha256", "export_sha256"))):
                raise BuildError("resource_content_invalid")
            if _sha(resource["content"].encode("utf-8")) != resource["export_sha256"]:
                raise BuildError("export_hash_mismatch")
            approved.append({"vault_id": identity, **{key: resource[key] for key in ("path", "source_sha256", "export_sha256")}})
    if not isinstance(receipt["approved_files"], list) or sorted(approved, key=_canonical) != sorted(receipt["approved_files"], key=_canonical):
        raise BuildError("approved_file_scope_mismatch")
    return snapshot, receipt


def _replace(source: str, old: str, new: str, count: int = 1) -> str:
    if source.count(old) != count:
        raise BuildError("static_source_contract_changed")
    return source.replace(old, new)


def _static(snapshot: dict) -> dict[str, bytes]:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = _replace(html, '<html lang="zh-CN">', '<html lang="zh-CN" data-kb-public-snapshot="true">')
    html = _replace(html, '<div class="sample-banner" id="sample-banner" hidden><strong>Public Preview · Sample Data</strong><span>以下内容为演示样例，不连接生产 Vault，也不代表真实库状态。</span></div>',
                    f'<div class="sample-banner"><strong>{NOTICE}</strong><span>只包含逐项获准的公开内容，不连接原库，不代表完整私人库或当前生产状态。</span></div>')
    html = html.replace("需要启用 JavaScript 才能读取本机只读 API。", "需要启用 JavaScript 才能读取这份静态公开快照。")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    begin, end = js.index("  function apiURL("), js.index("  async function request(")
    js = js[:begin] + '''  function apiURL(kind, id, path, options = {}) {
    const base = new URL('./snapshot-data/', options.baseURL || document.baseURI);
    if (kind === 'projection') return new URL('projection.json', base).href;
    if (!['descriptions','resources'].includes(kind) || !text(id)) throw new Error('公开快照请求无效');
    if (kind === 'descriptions') return new URL(`descriptions/${encodeURIComponent(id)}.json`, base).href;
    if (!safePath(path)) throw new Error('资源路径无效');
    return new URL(`resources/${encodeURIComponent(id)}/${path.split('/').map(encodeURIComponent).join('/')}`, base).href;
  }
''' + js[end:]
    marker = "const sample = typeof document !== 'undefined' && document.documentElement.dataset.kbPublicSample === 'true';"
    js = _replace(js, marker, "const sample = true; // Explicit offline snapshot build; never falls back to an API.", 2)
    js = _replace(js, "binding:'sample',declared:'sample'", "binding:'公开快照',declared:'逐项获准范围'")
    js = _replace(js, "'当前概览'", "'公开快照'")
    js = _replace(js, "'启用状态不代表正文当前可读；正文权限由每次资源请求单独裁决。'", "'这是获准范围的静态快照，不连接原始 Vault，也不追踪后续撤权或内容变化。'")
    js = _replace(js, "'仅向服务器请求发布白名单中的精确资源；权限由当前 live policy 再次裁决。HTML、SVG、未知格式与二进制不预览。'", "'仅提供本次明确批准的公开文件。下载内容校验公开字节 SHA；原始 SHA 仅用于来源对账。HTML、SVG 与二进制不预览。'")
    js = _replace(js, "const value = previewText(path,new Uint8Array(await response.arrayBuffer()));", "const bytes = new Uint8Array(await response.arrayBuffer()); const value = previewText(path,bytes);")
    js = _replace(js, "preview.replaceChildren(element('h3',path),element('pre',value));", "await showSnapshot(preview,row.vault_id,path,value,next,bytes);")
    evidence = {v["vault_id"]: {r["path"]: {key: r[key] for key in ("source_sha256", "export_sha256")} for r in v["resources"]} for v in snapshot["vaults"]}
    helper = '''
  const snapshotEvidence = EVIDENCE;
  async function showSnapshot(preview,id,path,value,ticket,bytes) {
    const info = snapshotEvidence[id]?.[path];
    if (!info) throw new Error('资源不在获准快照中');
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const actual = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2,'0')).join('');
    if (actual !== info.export_sha256) throw new Error('公开资源 SHA 校验失败');
    if (!gate.current(ticket)) return;
    preview.replaceChildren(element('h3',path),element('p','公开字节 SHA256 '+actual,'muted snapshot-sha'),element('p','原始来源 SHA256 '+info.source_sha256,'muted snapshot-sha'),element('pre',value));
  }
'''.replace("EVIDENCE", json.dumps(evidence, ensure_ascii=False).replace("<", "\\u003c"))
    js = _replace(js, "  async function load() {", helper + "  async function load() {")
    css = (STATIC / "app.css").read_bytes() + b'\nhtml[data-kb-public-snapshot] .resource-list { max-height:18rem; overflow:auto; }\nhtml[data-kb-public-snapshot] .snapshot-sha { overflow-wrap:anywhere; }\n'
    return {"index.html": html.encode("utf-8"), "app.js": js.encode("utf-8"), "app.css": css}


def build(source: Path, approval: Path, output: Path) -> dict:
    snapshot, receipt = _validate(Path(source), Path(approval))
    output = Path(os.path.abspath(output))
    if output.exists() or output.is_symlink():
        raise BuildError("output_exists_refused")
    if not output.parent.is_dir():
        raise BuildError("output_parent_missing")
    output = output.parent.resolve() / output.name
    for name in (".git", "src", "vaults", "workspace-data"):
        protected = (ROOT / name).resolve()
        if output == protected or protected in output.parents:
            raise BuildError("output_in_protected_source_tree")
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    hashes = {}

    def write(relative: str, raw: bytes) -> None:
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        hashes[relative] = _sha(raw)

    try:
        for name, raw in _static(snapshot).items():
            write(name, raw)
        projection = {"display_schema_version": "kb-display-1.1", "freshness": "current", "projection_revision": 1,
                      "source_member_revision": 1, "generated_at": snapshot["generated_at"], "vaults": []}
        for vault in snapshot["vaults"]:
            counts = [{"value": len(vault["resources"]), "count_unit": "file", "count_scope": "本次获准公开文件（非全库资产数）", "observed_at": snapshot["generated_at"]}]
            paths = [r["path"] for r in vault["resources"]]
            projection["vaults"].append({"vault_id": vault["vault_id"], "member_revision": 1, "policy_revision": 1,
                                         "name": vault["name"], "enabled": True, "resources": paths, "counts": counts, "state": "current"})
            description = {"description_version": "1", "revision": 1, "vault_id": vault["vault_id"],
                           **{key: vault[key] for key in ("purpose", "entry_points", "structure", "agent_prompt")},
                           "preview_resources": paths, "counts": [{**c, "source_ref": None} for c in counts]}
            description["structure"] = [path.removesuffix("/") for path in vault["structure"]]
            description["entry_points"] = [{**entry, "path": entry["path"].removesuffix("/")} for entry in vault["entry_points"]]
            write(f"snapshot-data/descriptions/{vault['vault_id']}.json", _json(description))
            for resource in vault["resources"]:
                write(f"snapshot-data/resources/{vault['vault_id']}/{resource['path']}", resource["content"].encode("utf-8"))
        write("snapshot-data/projection.json", _json(projection))
        manifest = {"format": "kb-public-snapshot-manifest-1", "notice": NOTICE, "generated_at": snapshot["generated_at"],
                    "snapshot_sha256": receipt["snapshot_sha256"], "approval_hash": receipt["approval_hash"],
                    "resources": receipt["approved_files"], "files": hashes}
        raw = _json(manifest)
        (stage / "public-snapshot-manifest.json").write_bytes(raw)
        if output.exists() or output.is_symlink():
            raise BuildError("output_exists_refused")
        stage.rename(output)
        return {"status": "built", "vault_count": len(snapshot["vaults"]), "resource_count": len(receipt["approved_files"]),
                "approval_hash": receipt["approval_hash"], "manifest_sha256": _sha(raw)}
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.input, args.approval, args.output), ensure_ascii=False))
        return 0
    except (BuildError, OSError) as error:
        # Never echo private input, local paths or unapproved content to stdout.
        print(json.dumps({"error": str(error) if isinstance(error, BuildError) else "snapshot_io_error"}))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

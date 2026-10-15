"""Public snapshot tests use invented text; no private Vault is accessed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools.kb_display_public_snapshot import BuildError, build


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inputs(tmp_path, *, content="# Approved fixture\n", path="knowledge/entry.md", generated_at="2026-10-15T12:00:00Z"):
    sha = digest(content.encode())
    snapshot = {"format": "kb-public-snapshot-1", "generated_at": generated_at, "vaults": [
        {"vault_id": f"reviewed-{i}", "name": f"Test {i}", "purpose": ["Build validation only"],
         "entry_points": [{"label": "Index", "path": path}], "structure": ["knowledge/"],
         "agent_prompt": "Use your own native entry; this is an offline public snapshot.",
         "resources": [{"path": path, "content": content, "source_sha256": sha, "export_sha256": sha}]}
        for i in range(6)]}
    source = tmp_path / "input.json"
    source.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    receipt = {"status": "APPROVED_FOR_PUBLIC", "scope": "public-real-vault-snapshot",
               "snapshot_sha256": digest(source.read_bytes()), "approved_files": [
                   {"vault_id": v["vault_id"], "path": r["path"], "source_sha256": r["source_sha256"],
                    "export_sha256": r["export_sha256"]} for v in snapshot["vaults"] for r in v["resources"]]}
    receipt["approval_hash"] = digest(json.dumps(receipt, ensure_ascii=False, sort_keys=True,
                                                separators=(",", ":")).encode())
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps(receipt), encoding="utf-8")
    return source, approval


def test_build_is_explicit_hash_bound_relative_and_non_overwriting(tmp_path):
    source, approval = inputs(tmp_path)
    site = tmp_path / "real-vaults"
    result = build(source, approval, site)
    assert result["vault_count"] == 6
    assert result["resource_count"] == 6
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'data-kb-public-snapshot="true"' in html
    assert "真实内容的获准公开快照" in html and "非实时" in html
    assert "Sample Data" not in html and "data-kb-public-sample" not in html
    js = (site / "app.js").read_text(encoding="utf-8")
    assert "./snapshot-data/" in js
    assert "当前 live policy" not in js
    manifest = json.loads((site / "public-snapshot-manifest.json").read_text(encoding="utf-8"))
    for path, expected in manifest["files"].items():
        assert digest((site / path).read_bytes()) == expected
    assert not (site / "sample-data").exists()
    with pytest.raises(BuildError, match="output_exists_refused"):
        build(source, approval, site)


def test_approval_is_required_and_tampering_rejected(tmp_path):
    source, approval = inputs(tmp_path)
    with pytest.raises(BuildError):
        build(source, tmp_path / "missing.json", tmp_path / "not-created")
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(BuildError, match="snapshot_hash_mismatch"):
        build(source, approval, tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("content,path", [
    ("fine", "../outside.md"), ("fine", "a/../outside.md"), ("fine", "a//b.md"),
    ("fine", "C:/secret.md"), ("fine", "index.html"),
    ("C:\\Users\\someone\\vault", "entry.md"),
    ("Source C:/private/vault.md", "entry.md"),
    ("file:///C:/private/vault.md", "entry.md"),
    (r"\\server\share\private.md", "entry.md"),
    ("/home/person/private.md", "entry.md"),
    ("api_key = " + "sk-live-" + "1234567890" * 3, "entry.md"),
    ("-----BEGIN " + "PRIVATE KEY-----", "entry.md"),  # Invalid header-only dummy; no key material.
    ("https://example.test/?access_token=privatevalue123456789", "entry.md"),
])
def test_private_literals_and_unsafe_paths_never_build(tmp_path, content, path):
    source, approval = inputs(tmp_path, content=content, path=path)
    with pytest.raises(BuildError):
        build(source, approval, tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()


def test_changed_approval_and_export_hash_are_rejected(tmp_path):
    source, approval = inputs(tmp_path)
    receipt = json.loads(approval.read_text())
    receipt["approved_files"][0]["path"] = "different.md"
    approval.write_text(json.dumps(receipt))
    with pytest.raises(BuildError, match="approval_hash_mismatch"):
        build(source, approval, tmp_path / "not-created")


@pytest.mark.parametrize("timestamp", ["2026-10-15 12:00:00+00:00", "20261015T120000Z", "2026-10-15T12:00:00", "2026-02-30T12:00:00Z"])
def test_timestamp_rejected_before_build_if_browser_cannot_consume_it(tmp_path, timestamp):
    source, approval = inputs(tmp_path, generated_at=timestamp)
    with pytest.raises(BuildError, match="snapshot_time_invalid"):
        build(source, approval, tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()


def test_normal_public_source_url_is_not_a_machine_drive_path(tmp_path):
    source, approval = inputs(tmp_path, content="Source: https://example.test/reference\n")
    result = build(source, approval, tmp_path / "out")
    assert result["resource_count"] == 6


@pytest.mark.parametrize("content", [r"Markdown a\b\c", r"Public terminal prompt C:\> dir", "https://example.test/home/reference"])
def test_valid_markdown_prompt_and_public_url_do_not_become_machine_paths(tmp_path, content):
    source, approval = inputs(tmp_path, content=content)
    result = build(source, approval, tmp_path / "out")
    assert result["resource_count"] == 6
    assert "max-height:18rem" in (tmp_path / "out/app.css").read_text(encoding="utf-8")
    assert ".snapshot-sha { overflow-wrap:anywhere; }" in (tmp_path / "out/app.css").read_text(encoding="utf-8")


def test_does_not_change_static_source(tmp_path):
    from tools.kb_display_public_snapshot import STATIC
    before = {p.name: digest(p.read_bytes()) for p in STATIC.iterdir() if p.is_file()}
    source, approval = inputs(tmp_path)
    build(source, approval, tmp_path / "out")
    assert before == {p.name: digest(p.read_bytes()) for p in STATIC.iterdir() if p.is_file()}


def test_built_js_uses_subpath_and_validates_generated_metadata(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required only for this JavaScript regression check")
    source, approval = inputs(tmp_path)
    site = tmp_path / "out"
    build(source, approval, site)
    script = """
      const fs = require('node:fs');
      const api = require(process.argv[1]);
      const projection = api.validateProjection(JSON.parse(fs.readFileSync(process.argv[2])));
      const description = api.validateDescription(JSON.parse(fs.readFileSync(process.argv[3])), 'reviewed-0');
      if (description.structure[0] !== 'knowledge') throw new Error('directory normalization');
      for (const kind of ['projection','descriptions','resources']) {
        const url = api.apiURL(kind,'reviewed-0','knowledge/entry.md',{baseURL:'https://example.test/project/real-vaults/'});
        if (!url.startsWith('https://example.test/project/real-vaults/snapshot-data/')) throw new Error(url);
        if (url.includes('/api/')) throw new Error('API fallback');
      }
      if (projection.vaults[0].counts[0].value !== 1) throw new Error('scope count');
    """
    result = subprocess.run([node, "-e", script, str(site / "app.js"),
                             str(site / "snapshot-data/projection.json"),
                             str(site / "snapshot-data/descriptions/reviewed-0.json")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr

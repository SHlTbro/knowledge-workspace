import json
from pathlib import Path

import pytest

import tools.kb_display_public_sample as public_sample
from tools.kb_display_public_sample import BuildError, build


def test_public_sample_build_is_explicit_relative_and_non_overwriting(tmp_path):
    site = tmp_path / "repo" / "docs"
    site.parent.mkdir()
    result = build(site)
    assert result["status"] == "built"
    assert result["sample_data"] is True
    assert result["vault_count"] == 6
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'data-kb-public-sample="true"' in html
    assert 'href="./app.css"' in html and 'src="./app.js"' in html
    assert not (site / "api").exists()

    projection = json.loads((site / "sample-data/projection.json").read_text(encoding="utf-8"))
    assert len(projection["vaults"]) == 6
    assert all(row["vault_id"].startswith("sample-") for row in projection["vaults"])
    assert (site / "sample-data/NOTICE.txt").is_file()
    assert result["manifest_sha256"]
    before = (site / "index.html").read_bytes()
    with pytest.raises(BuildError, match="output_exists_refused"):
        build(site)
    assert (site / "index.html").read_bytes() == before


def test_public_sample_does_not_write_into_product_or_vault_source(tmp_path):
    with pytest.raises(BuildError, match="output_in_protected_source_tree"):
        build(Path(__file__).resolve().parents[1] / "src/kb_core/display_static/should-not-exist")


@pytest.mark.parametrize("path", ["/outside.md", "//server/share.md"])
def test_public_sample_rejects_rooted_resource_paths(path):
    sample = json.loads(public_sample.SAMPLE.read_text(encoding="utf-8"))
    resources = sample["vaults"][0]["resources"]
    resources.pop(next(iter(resources)))
    resources[path] = "sample only"

    with pytest.raises(BuildError, match="sample_resource_path_invalid"):
        public_sample._validate_sample(sample)

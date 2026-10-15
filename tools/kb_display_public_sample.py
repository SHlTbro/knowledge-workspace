"""Build the explicitly selected, offline GitHub Pages sample display."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/kb_core/display_static"
SAMPLE = ROOT / "examples/public-sample/sample-data.json"
STATIC_FILES = ("index.html", "app.css", "app.js")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class BuildError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise BuildError("sample_data_too_large")
    return json.loads(raw.decode("utf-8"))


def _write_json(path: Path, value: object) -> bytes:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or ":" in value:
        raise BuildError("sample_resource_path_invalid")
    parts = PurePosixPath(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise BuildError("sample_resource_path_invalid")
    return "/".join(parts)


def _count_rows(vault: dict) -> tuple[list[dict], list[dict]]:
    projection, description = [], []
    for count in vault["counts"]:
        row = {key: count[key] for key in ("value", "count_unit", "count_scope", "observed_at")}
        projection.append(row)
        description.append({**row, "source_ref": None})
    return projection, description


def _validate_sample(sample: dict) -> list[dict]:
    if (set(sample) != {"sample_notice", "generated_at", "vaults"}
            or sample["sample_notice"] != "Fictional public-preview sample data. No production Vault is represented."
            or not isinstance(sample["vaults"], list) or len(sample["vaults"]) != 6):
        raise BuildError("sample_data_contract_invalid")
    ids, result = set(), []
    for vault in sample["vaults"]:
        required = {"vault_id", "name", "purpose", "entry_points", "structure", "agent_prompt", "counts", "resources"}
        if not isinstance(vault, dict) or set(vault) != required:
            raise BuildError("sample_vault_contract_invalid")
        identity = vault["vault_id"]
        if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in ids:
            raise BuildError("sample_vault_id_invalid")
        ids.add(identity)
        if not isinstance(vault["name"], str) or not vault["name"].strip():
            raise BuildError("sample_vault_name_invalid")
        for key in ("purpose", "entry_points", "structure", "counts"):
            if not isinstance(vault[key], list):
                raise BuildError("sample_vault_field_invalid")
        if (not vault["purpose"] or not isinstance(vault["agent_prompt"], str)
                or not vault["agent_prompt"].strip() or not isinstance(vault["resources"], dict)
                or not vault["resources"]):
            raise BuildError("sample_vault_content_invalid")
        for count in vault["counts"]:
            if (set(count) != {"value", "count_unit", "count_scope", "observed_at"}
                    or count["count_unit"] not in {"asset", "card", "file", "directory", "byte"}
                    or not isinstance(count["count_scope"], str)
                    or not (count["value"] is None or isinstance(count["value"], int) and count["value"] >= 0)
                    or (count["value"] is not None and not count["observed_at"])):
                raise BuildError("sample_count_invalid")
        for entry in vault["entry_points"]:
            if set(entry) != {"label", "path"} or not isinstance(entry["label"], str):
                raise BuildError("sample_entry_invalid")
            _safe_relative(entry["path"])
        for path, content in vault["resources"].items():
            _safe_relative(path)
            if not isinstance(content, str) or len(content.encode("utf-8")) > 256 * 1024:
                raise BuildError("sample_resource_invalid")
            if re.search(r"(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\|/Users/|/home/)", content):
                raise BuildError("sample_resource_machine_path_forbidden")
        result.append(vault)
    return result


def build(output: Path) -> dict:
    sample = _read_json(SAMPLE)
    vaults = _validate_sample(sample)
    output = Path(os.path.abspath(output))
    if not output.parent.is_dir():
        raise BuildError("output_parent_missing")
    output = output.parent.resolve() / output.name
    if output.exists() or output.is_symlink():
        raise BuildError("output_exists_refused")
    for protected in (ROOT / ".git", ROOT / "src", ROOT / "vaults", ROOT / "workspace-data"):
        protected = protected.resolve()
        if output == protected or protected in output.parents:
            raise BuildError("output_in_protected_source_tree")
    parent = output.parent

    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=parent))
    hashes = {}
    try:
        for name in STATIC_FILES:
            source = STATIC / name
            raw = source.read_bytes()
            if name == "index.html":
                html = raw.decode("utf-8")
                match = re.search(r"<html\b([^>]*)>", html, flags=re.IGNORECASE)
                if not match or "data-kb-public-sample" in match.group(0):
                    raise BuildError("source_html_marker_invalid")
                html = html[:match.start()] + match.group(0)[:-1] + ' data-kb-public-sample="true">' + html[match.end():]
                raw = html.encode("utf-8")
            (stage / name).write_bytes(raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()

        data_root = stage / "sample-data"
        data_root.mkdir()
        projection = {
            "display_schema_version": "kb-display-1.1",
            "freshness": "current",
            "projection_revision": 1,
            "source_member_revision": 1,
            "generated_at": sample["generated_at"],
            "vaults": [],
        }
        for vault in vaults:
            counts, description_counts = _count_rows(vault)
            projection["vaults"].append({
                "vault_id": vault["vault_id"], "member_revision": 1, "policy_revision": 1,
                "name": vault["name"], "enabled": True, "resources": list(vault["resources"]),
                "counts": counts, "state": "current",
            })
            description = {
                "description_version": "1", "revision": 1, "vault_id": vault["vault_id"],
                "purpose": vault["purpose"], "entry_points": vault["entry_points"],
                "structure": vault["structure"], "agent_prompt": vault["agent_prompt"],
                "preview_resources": list(vault["resources"]), "counts": description_counts,
            }
            raw = _write_json(data_root / "descriptions" / f"{vault['vault_id']}.json", description)
            hashes[f"sample-data/descriptions/{vault['vault_id']}.json"] = hashlib.sha256(raw).hexdigest()
            for relative, content in vault["resources"].items():
                target = data_root / "resources" / vault["vault_id"] / Path(*PurePosixPath(relative).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                raw = content.encode("utf-8")
                target.write_bytes(raw)
                hashes[f"sample-data/resources/{vault['vault_id']}/{relative}"] = hashlib.sha256(raw).hexdigest()

        raw = _write_json(data_root / "projection.json", projection)
        hashes["sample-data/projection.json"] = hashlib.sha256(raw).hexdigest()
        notice = (sample["sample_notice"] + "\nAll six Vault records and all preview text are fictional.\n").encode("utf-8")
        (data_root / "NOTICE.txt").write_bytes(notice)
        hashes["sample-data/NOTICE.txt"] = hashlib.sha256(notice).hexdigest()
        manifest = {"format": "kb-public-sample-1", "sample_notice": sample["sample_notice"], "files": hashes}
        raw = _write_json(stage / "public-sample-manifest.json", manifest)
        if output.exists():
            raise BuildError("output_raced")
        stage.rename(output)
        return {"status": "built", "sample_data": True, "vault_count": len(vaults),
                "output": str(output), "manifest_sha256": hashlib.sha256(raw).hexdigest()}
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.output)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (BuildError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": getattr(error, "args", ["public_sample_build_failed"])[0]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

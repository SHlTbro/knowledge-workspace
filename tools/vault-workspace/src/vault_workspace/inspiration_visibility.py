"""Vault⑤'s existing active/index/body-digest publication contract, opt-in only.

This domain adapter does not prescribe schemas for other Vaults. Unknown pending
transaction formats fail closed; the carried contract defines no receipt parser.
SQLite is only a projection and never the publication authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import yaml

from . import reader
from .safety import relative_path, under

ADAPTER_ID = 'inspiration-active-index-v1'
NAVIGATION = {'AGENTS.md', 'README.md', 'purpose.md', 'wiki/index.md',
              'sources/_l1-anchors.json', 'sources/_l2-manifest.json'}
CARD = re.compile(r'30-cards/(prj|ptn|exp|risk)/((?:PRJ|PTN|EXP|RISK)-\d+)\.md\Z')
ROW = re.compile(r'^\|\s*\[\[((?:PRJ|PTN|EXP|RISK)-\d+)\]\]\s*\|\s*([^|]+?)\s*\|\s*(sha256:[0-9a-f]{16})\s*\|', re.M)


def enabled(descriptor: dict) -> bool:
    config = descriptor.get('extensions', {}).get('workspace_visibility')
    if config is None:
        return False
    if config != {'adapter_id': ADAPTER_ID}:
        raise ValueError('Invalid Vault⑤ visibility adapter configuration')
    return True


def published(root: Path, indexed_text: str | None = None) -> dict:
    transactions = under(root, '.transactions')
    if transactions.exists():
        if transactions.is_symlink() or not transactions.is_dir():
            raise PermissionError('Publication blocked: unsafe transaction directory')
        # No known transaction schema was carried. Do not infer commit from a
        # filename or phase label and accidentally expose an unfinished write.
        if any(p.name != '.gitkeep' or not p.is_file() or p.is_symlink() or p.stat().st_size
               for p in transactions.iterdir()):
            raise PermissionError('Publication blocked: pending or unrecognized transaction')
    if indexed_text is None:
        _, indexed_text = reader._load(root, 'wiki/index.md')
    rows = {}
    for identifier, version, digest in ROW.findall(indexed_text):
        if identifier in rows:
            raise PermissionError('Publication blocked: duplicate active index identity')
        rows[identifier] = (version.strip(), digest)
    return rows


def check_card(root: Path, path: str, rows: dict, card_text: str | None = None) -> None:
    match = CARD.fullmatch(path)
    if not match or match[1].upper() != match[2].split('-')[0]:
        raise PermissionError('Card is outside the published domain structure')
    if card_text is None:
        _, card_text = reader._load(root, path)
    header = re.match(r'\A---\r?\n(.*?)\r?\n---\r?\n', card_text, re.S)
    if not header or len(header[1]) > 16384:
        raise PermissionError('Card has no bounded domain envelope')
    try:
        meta = yaml.safe_load(header[1])
    except (yaml.YAMLError, RecursionError):
        raise PermissionError('Card envelope is invalid') from None
    body = card_text[header.end():]
    digest = 'sha256:' + hashlib.sha256(body.encode('utf8')).hexdigest()[:16]
    if (not isinstance(meta, dict) or meta.get('id') != match[2]
            or meta.get('type') != match[1].upper() or meta.get('status') != 'active'
            or meta.get('digest') != digest
            or rows.get(match[2]) != (str(meta.get('version')), digest)):
        raise PermissionError('Card is not active and committed in the current index')


def check_path(root: Path, path: str, descriptor: dict) -> None:
    if not enabled(descriptor):
        return
    path = relative_path(path)
    if CARD.fullmatch(path):
        check_card(root, path, published(root))
    elif path == 'wiki/index.md':
        rows = published(root)
        try:
            for identifier in rows:
                check_card(root, f'30-cards/{identifier.split("-")[0].lower()}/{identifier}.md', rows)
        except (OSError, ValueError):
            raise PermissionError('Index summaries are not all currently published; repair the domain index') from None
    elif path in NAVIGATION or path.startswith('sources/'):
        # The source adapter checks accepted pins and operator blocks afterwards.
        return
    else:
        raise PermissionError('Path is outside published cards and domain entry points')


def filter_scan(root: Path, scan: dict, descriptor: dict) -> dict:
    if not enabled(descriptor):
        return scan
    issues = list(scan['issues'])
    try:
        rows = published(root)
    except (OSError, ValueError) as exc:
        return {'documents': [], 'issues': issues + [{'code': 'domain_publication_blocked', 'message': str(exc)}]}
    documents = []
    for item in scan['documents']:
        try:
            check_card(root, item['path'], rows)
            documents.append(item)
        except (OSError, ValueError) as exc:
            issues.append({'code': 'domain_unpublished', 'path': item['path'], 'message': str(exc)})
    return {'documents': documents, 'issues': issues}

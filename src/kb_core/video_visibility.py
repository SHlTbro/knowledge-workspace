"""Read-only implementation of Vault④'s published-card integrity contract.

This adapter mirrors the native ``vault_integrity.check_card`` checks but
receives every file through a caller-provided, permission-checked reader. It
never imports or executes code from a bound Vault.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Callable

CARD_ID = re.compile(r'^[A-Z]{3}-[A-Za-z0-9-]+$')
INDEX_ROW = re.compile(r'^-\s+([A-Z]{3}-[A-Za-z0-9-]+)\s*\|\s*(\w+)\s*\|(?P<rest>.*)$')
_FIELD = re.compile(r'(\w+)=([^\s|]+)')


def _frontmatter(text: str) -> dict[str, str]:
    text = text.replace('\r\n', '\n')
    if not text.startswith('---\n'):
        raise ValueError('frontmatter_invalid')
    end = text.find('\n---', 4)
    if end < 0:
        raise ValueError('frontmatter_invalid')
    values = {}
    for line in text[4:end].splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def dependency_paths(card_text: str) -> list[str]:
    """Return native data files needed to validate this indexed card."""
    try:
        meta = _frontmatter(card_text)
    except ValueError:
        return []
    result = ['wiki/index.md', '00-system/registries/cards.md', 'wiki/log.md']
    card_id = meta.get('card_id', '')
    transaction = meta.get('transaction_id', '')
    source = meta.get('source_record_id', '')
    if CARD_ID.fullmatch(card_id):
        result.append(f'wiki/cards/{card_id[:3].lower()}/{card_id}.mg_receipt.json')
    if re.fullmatch(r'[A-Za-z0-9_-]+', transaction):
        result.append(f'.transactions/committed/{transaction}.json')
    if re.fullmatch(r'[A-Za-z0-9_-]+', source):
        result.append(f'sources/{source}.json')
    return list(dict.fromkeys(result))


def _rows(text: str) -> dict[str, list[dict[str, str]]]:
    found: dict[str, list[dict[str, str]]] = {}
    for line in text.splitlines():
        match = INDEX_ROW.match(line)
        if match:
            fields = {key: value for key, value in _FIELD.findall(match['rest'])}
            found.setdefault(match[1], []).append({'status': match[2], **fields})
    return found


def _registry(text: str) -> dict[str, list[dict[str, str]]]:
    found: dict[str, list[dict[str, str]]] = {}
    for line in text.splitlines():
        cols = [part.strip() for part in line.strip().strip('|').split('|')]
        if len(cols) == 5 and CARD_ID.fullmatch(cols[0]):
            found.setdefault(cols[0], []).append(dict(zip(('id', 'version', 'status', 'path', 'updated'), cols)))
    return found


def _committed(read_text: Callable[[str], str], transaction_id: str) -> dict | None:
    if not transaction_id or not re.fullmatch(r'[A-Za-z0-9_-]+', transaction_id):
        return None
    try:
        record = json.loads(read_text(f'.transactions/committed/{transaction_id}.json'))
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None
    if isinstance(record, dict) and record.get('status') == 'COMMITTED' and record.get('transaction_id') == transaction_id:
        return record
    return None


def check_card(card_id: str, read_text: Callable[[str], str]) -> list[str]:
    """Return issues equivalent to the native production-visibility check."""
    if not CARD_ID.fullmatch(card_id):
        return ['invalid_card_id']
    note_path = f'wiki/cards/{card_id[:3].lower()}/{card_id}.md'
    try:
        note = read_text(note_path).replace('\r\n', '\n')
        meta = _frontmatter(note)
    except (OSError, UnicodeError, ValueError, RecursionError):
        return ['frontmatter_invalid']
    issues = []
    if meta.get('card_id') != card_id:
        issues.append('note_id_mismatch')
    if meta.get('status') != 'active':
        issues.append('note_not_active')
    try:
        indexed = _rows(read_text('wiki/index.md')).get(card_id, [])
    except (OSError, UnicodeError, ValueError):
        indexed = []
    if len(indexed) != 1:
        issues.append('index_missing_or_duplicate')
    elif indexed[0].get('status') != meta.get('status'):
        issues.append('index_status_mismatch')
    try:
        registered = _registry(read_text('00-system/registries/cards.md')).get(card_id, [])
    except (OSError, UnicodeError, ValueError):
        registered = []
    if len(registered) != 1:
        issues.append('registry_missing_or_duplicate')
    else:
        row = registered[0]
        if row['status'] != meta.get('status') or row['version'] != meta.get('version'):
            issues.append('registry_state_mismatch')
        if row['path'] != note_path:
            issues.append('registry_path_mismatch')
    digest = meta.get('payload_digest')
    if not digest or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        issues.append('payload_digest_missing')
    elif len(indexed) == 1 and indexed[0].get('digest') != digest:
        issues.append('index_digest_mismatch')
    transaction_id = meta.get('transaction_id')
    source_id = meta.get('source_record_id')
    if len(indexed) == 1:
        if indexed[0].get('transaction') != transaction_id:
            issues.append('index_transaction_mismatch')
        if indexed[0].get('source') != source_id:
            issues.append('index_source_mismatch')
    record = _committed(read_text, transaction_id or '')
    cards = record.get('cards') if record else None
    record_card = next((item for item in cards if isinstance(item, dict) and item.get('card_id') == card_id), None) if isinstance(cards, list) else None
    if (record_card is None or record_card.get('payload_digest') != digest or record_card.get('version') != meta.get('version')
            or record_card.get('path') != note_path):
        issues.append('committed_transaction_missing')
    if record:
        source_path = f'sources/{source_id}.json' if source_id and re.fullmatch(r'[A-Za-z0-9_-]+', source_id) else None
        if source_path is None:
            issues.append('source_record_missing')
        else:
            try:
                source = json.loads(read_text(source_path))
                if (not isinstance(source, dict) or source.get('source_id') != source_id or source.get('status') != 'verified'
                        or source.get('content_sha256') != record.get('source_content_sha256')
                        or meta.get('source_record_id') != source_id):
                    issues.append('source_record_mismatch')
            except (OSError, UnicodeError, ValueError, AttributeError, RecursionError):
                issues.append('source_record_invalid')
    receipt_path = str(PurePosixPath(note_path).with_suffix('.mg_receipt.json'))
    try:
        receipt = json.loads(read_text(receipt_path))
        if not isinstance(receipt, dict):
            issues.append('stored_receipt_invalid')
            receipt = {}
        if (receipt.get('card_id') != card_id or receipt.get('payload_digest') != digest
                or (record_card and receipt.get('receipt_id') != record_card.get('receipt_id'))):
            issues.append('stored_receipt_mismatch')
        marker = '\n```json\n'
        if marker not in note or '\n```' not in note.split(marker, 1)[1]:
            raise ValueError('projection missing')
        projection = json.loads(note.split(marker, 1)[1].split('\n```', 1)[0])
        if (not isinstance(projection, dict) or projection.get('card_id') != card_id
                or projection.get('status') != meta.get('status') or projection.get('version') != meta.get('version')
                or projection.get('payload_digest') != digest):
            issues.append('projection_metadata_mismatch')
        elif digest and projection.get('payload_digest') == digest:
            canonical = {key: value for key, value in projection.items() if key != 'payload_digest'}
            actual = 'sha256:' + hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
            if actual != digest:
                issues.append('stored_receipt_invalid')
        gates = receipt.get('gates') if isinstance(receipt, dict) else None
        if (not isinstance(receipt, dict) or not all(receipt.get(field) for field in
                ('schema_version', 'receipt_id', 'card_id', 'payload_digest', 'producer', 'timestamp'))
                or receipt.get('card_id') != projection.get('card_id')
                or receipt.get('payload_digest') != projection.get('payload_digest')
                or not isinstance(gates, dict) or any(gates.get(f'MG{i:02d}') != 'PASS' for i in range(1, 10))):
            issues.append('stored_receipt_invalid')
    except FileNotFoundError:
        issues.append('stored_receipt_missing')
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError, RecursionError):
        issues.append('stored_receipt_invalid')
    if transaction_id:
        try:
            if not any(f'| promote_active | {card_id} (transaction={transaction_id})' in line
                       for line in read_text('wiki/log.md').splitlines()):
                issues.append('promotion_log_missing')
        except (OSError, UnicodeError, ValueError):
            issues.append('promotion_log_missing')
    return issues
